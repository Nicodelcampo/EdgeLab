#!/usr/bin/env python3
"""
GATE — 5 propuestas implementadas + notas de literatura:

1. Congelar generador v2 (perfil minutos GATE)
2. Features enriquecidas (OFI, spread z, session phase)
3. Transformer con loss balanceada / focal por clase (no borrar volátil)
4. Análisis obligatorio de minutos por estado
5. Causal vs bidireccional: causal para live; bi solo cota offline (look-ahead)

Complemento web: CBFL/Focal para desbalance; atención causal en series temporales
para evitar look-ahead; session phase / OFI intradía en microestructura.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from gate_recreate import (
    SEED,
    BARS_PER_DAY,
    REGIME_NAMES,
    generate_prices,
    add_features,
    fit_simple_hmm,
    forward_filter,
    apply_hysteresis,
    toxic_overlay,
    run_hypotheses,
    persistence_minutes,
    flip_flop_rate,
    accuracy_vs_latent,
    toxic_precision_recall,
    triangulate,
    session_index,
)
from gate_generator_transformer import (
    gen_latent_v2_target_budget,
    analyze_generator,
    softmax,
    layer_norm,
    impute_causal,
    standardize_train,
)

RNG = np.random.default_rng(SEED)
TARGET_MINUTES = {"calmo": 133, "normal": 173, "volatil": 52, "toxico": 32}


# ---------------------------------------------------------------------------
# 2) Features enriquecidas
# ---------------------------------------------------------------------------

def session_phase_features(times) -> pd.DataFrame:
    """Fase de sesión RTH: open / mid / close + minuto desde open (normalizado)."""
    t = pd.DatetimeIndex(pd.to_datetime(times))
    minutes = t.hour * 60 + t.minute
    open_m = 9 * 60 + 30
    close_m = 16 * 60
    rel = (minutes - open_m) / max(close_m - open_m, 1)
    # one-hot suave por tercios
    phase_open = ((rel >= 0) & (rel < 1 / 3)).astype(float)
    phase_mid = ((rel >= 1 / 3) & (rel < 2 / 3)).astype(float)
    phase_close = (rel >= 2 / 3).astype(float)
    return pd.DataFrame(
        {
            "sess_rel": rel,
            "phase_open": phase_open,
            "phase_mid": phase_mid,
            "phase_close": phase_close,
        },
        index=np.arange(len(times)),
    )


def enrich_features(df: pd.DataFrame) -> pd.DataFrame:
    """Añade spread z causal, OFI más estable, session phase."""
    df = add_features(df)
    mid = df["mid"].values
    spread = df["spread"].values
    ofi = df["ofi_raw"].values
    # spread z causal
    sz = np.full(len(spread), np.nan)
    win = 20
    for i in range(win, len(spread)):
        w = spread[i - win : i]
        sd = w.std()
        sz[i] = 0.0 if sd < 1e-12 else (spread[i] - w.mean()) / sd
    df["spread_z"] = sz
    # OFI suavizado causal (EMA solo pasado)
    ema = np.zeros(len(ofi))
    alpha = 0.15
    ema[0] = ofi[0]
    for i in range(1, len(ofi)):
        ema[i] = alpha * ofi[i] + (1 - alpha) * ema[i - 1]
    df["ofi_ema"] = ema
    # z de ofi_ema
    oz = np.full(len(ema), np.nan)
    for i in range(win, len(ema)):
        w = ema[i - win : i]
        sd = w.std()
        oz[i] = 0.0 if sd < 1e-12 else (ema[i] - w.mean()) / sd
    df["ofi_ema_z"] = oz
    # session phase
    ph = session_phase_features(df["time"])
    for c in ph.columns:
        df[c] = ph[c].values
    return df


# ---------------------------------------------------------------------------
# 3) Transformer + class-balanced focal loss
# ---------------------------------------------------------------------------

class BalancedTransformer:
    """
    Encoder causal + opción de máscara bidireccional SOLO para cota offline.
    Loss: Class-Balanced Focal (Cui et al. / Lin et al. style).
    """

    def __init__(
        self,
        n_features: int,
        d_model: int = 20,
        n_heads: int = 2,
        K: int = 3,
        seed: int = 0,
        causal: bool = True,
    ):
        rng = np.random.default_rng(seed)
        self.d_model = d_model
        self.n_heads = n_heads
        self.d_head = d_model // n_heads
        self.K = K
        self.causal = causal
        sc = 0.08
        self.W_in = rng.normal(0, sc, (n_features, d_model))
        self.W_q = rng.normal(0, sc, (d_model, d_model))
        self.W_k = rng.normal(0, sc, (d_model, d_model))
        self.W_v = rng.normal(0, sc, (d_model, d_model))
        self.W_o = rng.normal(0, sc, (d_model, d_model))
        self.W_ff1 = rng.normal(0, sc, (d_model, d_model * 2))
        self.b_ff1 = np.zeros(d_model * 2)
        self.W_ff2 = rng.normal(0, sc, (d_model * 2, d_model))
        self.b_ff2 = np.zeros(d_model)
        self.W_out = rng.normal(0, sc, (d_model, K))
        self.b_out = np.zeros(K)

    def _attention(self, H: np.ndarray) -> np.ndarray:
        T, d = H.shape
        Q, K, V = H @ self.W_q, H @ self.W_k, H @ self.W_v

        def split(x):
            return x.reshape(T, self.n_heads, self.d_head).transpose(1, 0, 2)

        Qh, Kh, Vh = split(Q), split(K), split(V)
        outs = []
        scale = 1.0 / math.sqrt(self.d_head)
        if self.causal:
            mask = np.triu(np.ones((T, T)), k=1).astype(bool)
        else:
            mask = np.zeros((T, T), dtype=bool)
        for h in range(self.n_heads):
            scores = (Qh[h] @ Kh[h].T) * scale
            scores = scores.copy()
            scores[mask] = -1e9
            w = softmax(scores, axis=-1)
            outs.append(w @ Vh[h])
        O = np.concatenate(outs, axis=-1)
        return O @ self.W_o

    def forward(self, X: np.ndarray) -> np.ndarray:
        H = X @ self.W_in
        H = layer_norm(H + self._attention(H))
        ff = np.maximum(0, H @ self.W_ff1 + self.b_ff1)
        ff = ff @ self.W_ff2 + self.b_ff2
        H = layer_norm(H + ff)
        return H @ self.W_out + self.b_out

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        return softmax(self.forward(X), axis=-1)

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        lr: float = 0.06,
        epochs: int = 100,
        gamma: float = 2.0,
        beta: float = 0.99,
        l2: float = 1e-4,
    ):
        """
        Class-Balanced Focal Loss:
        weight_k ∝ (1-β)/(1-β^{n_k}), focal (1-p)^γ
        """
        # class counts
        counts = np.array([(y == k).sum() for k in range(self.K)], dtype=float)
        counts = np.maximum(counts, 1.0)
        effective = (1.0 - beta) / (1.0 - np.power(beta, counts))
        class_w = effective / effective.sum() * self.K

        for ep in range(epochs):
            logits = self.forward(X)
            probs = softmax(logits, axis=-1)
            T = X.shape[0]
            Y = np.zeros_like(probs)
            w_sample = np.zeros(T)
            for t in range(T):
                k = int(y[t])
                if 0 <= k < self.K:
                    Y[t, k] = 1.0
                    pt = probs[t, k]
                    # focal * class-balanced
                    w_sample[t] = class_w[k] * ((1.0 - pt) ** gamma)
            w_sample = w_sample / (w_sample.mean() + 1e-12)
            # weighted CE gradient on logits
            dL = (probs - Y) * w_sample[:, None] / T
            H0 = np.tanh(X @ self.W_in)
            self.W_out -= lr * (H0.T @ dL + l2 * self.W_out)
            self.b_out -= lr * dL.sum(axis=0)
            dH0 = dL @ self.W_out.T * (1 - H0**2)
            self.W_in -= lr * (X.T @ dH0 + l2 * self.W_in)
        return self


# ---------------------------------------------------------------------------
# 4) Minutos por estado — análisis
# ---------------------------------------------------------------------------

def minutes_analysis(regime: np.ndarray, latent: np.ndarray, name: str) -> dict:
    det = {REGIME_NAMES[k]: int((regime == k).sum()) for k in range(4)}
    true = {REGIME_NAMES[k]: int((latent == k).sum()) for k in range(4)}
    abs_err = {k: abs(det[k] - TARGET_MINUTES[k]) for k in TARGET_MINUTES}
    # cobertura volátil: crítico
    vol_det = det["volatil"]
    vol_true = true["volatil"]
    return {
        "model": name,
        "detected": det,
        "latent": true,
        "target_ui": TARGET_MINUTES,
        "abs_err_vs_ui": abs_err,
        "volatile_detected": vol_det,
        "volatile_latent": vol_true,
        "volatile_erased": vol_det == 0,
        "mae_minutes_vs_ui": float(np.mean(list(abs_err.values()))),
    }


def eval_full(df, regime, post, latent, holdout, name) -> dict:
    pers = persistence_minutes(regime)
    ff = flip_flop_rate(regime)
    acc = accuracy_vs_latent(regime, latent)
    acc_ho = accuracy_vs_latent(regime, latent, holdout)
    prec, rec = toxic_precision_recall(regime, latent, df["vpin"].values, 0.55)
    hyp = run_hypotheses(df, regime)
    if post.shape[1] != 3:
        p = np.zeros((len(post), 3))
        p[:, : min(3, post.shape[1])] = post[:, : min(3, post.shape[1])]
        p = p / np.maximum(p.sum(axis=1, keepdims=True), 1e-12)
        post = p
    tris = triangulate(df, regime, post, hyp)
    n_c = sum(1 for t in tris if t.status == "CONVERGE")
    mins = minutes_analysis(regime, latent, name)
    return {
        "name": name,
        "persistencia_min": round(pers, 2),
        "flip_flop_pct": round(ff * 100, 2),
        "acc_pct": round(acc * 100, 1),
        "acc_HO_pct": round(acc_ho * 100, 1),
        "tox_P": round(prec * 100, 1),
        "tox_R": round(rec * 100, 1),
        "gross": hyp["gross"],
        "net": hyp["net"],
        "n_trades": hyp["n_trades"],
        "tri": f"{n_c}/{len(tris)}",
        "minutes_detected": mins["detected"],
        "volatile_erased": mins["volatile_erased"],
        "mae_min_vs_ui": round(mins["mae_minutes_vs_ui"], 1),
        "minutes_detail": mins,
    }


def main():
    print("=== 5 propuestas GATE (v2 + features + TF balanced + minutos + causal/bi) ===\n")

    # 1) Congelar v2
    latent = gen_latent_v2_target_budget(BARS_PER_DAY)
    gen_rep = analyze_generator(latent, "v2_FROZEN")
    print("1) Generador v2 FROZEN:", gen_rep["minutes"], "score", gen_rep["score_match"])

    # precios + features enriquecidas
    df = generate_prices(latent)
    df = enrich_features(df)

    times = df["time"]
    holdout = (times >= pd.Timestamp("2026-03-12 14:30:00")).values
    train = ~holdout

    feat_cols = [
        "rvol",
        "er",
        "ofi_ema_z",
        "hurst",
        "vpin",
        "spread_z",
        "sess_rel",
        "phase_open",
        "phase_mid",
        "phase_close",
    ]
    X_all = impute_causal(df[feat_cols].values.astype(float))
    X_std = standardize_train(X_all[train], X_all)

    y_train = latent[train].copy()
    y_train[y_train > 2] = 2  # toxic → vol bucket for 3-class head; overlay after

    results = []

    # HMM baseline enriched features (first 3 numeric-ish)
    rvol_tr = np.nan_to_num(df.loc[train, "rvol"].values, nan=0.0)
    q1, q2 = np.quantile(rvol_tr, [0.33, 0.66])
    init = np.zeros(train.sum(), dtype=int)
    rt = df.loc[train, "rvol"].values
    init[rt > q1] = 1
    init[rt > q2] = 2
    params = fit_simple_hmm(X_all[train][:, :3], init, K=3)
    post_h, hard_h = forward_filter(X_all[:, :3], params)
    reg_h = toxic_overlay(
        apply_hysteresis(hard_h, post_h, 3, 0.40), df["vpin"].values, 0.55
    )
    results.append(eval_full(df, reg_h, post_h, latent, holdout, "HMM3_enriched|v2"))

    # 3) TF causal + balanced focal
    tf_c = BalancedTransformer(
        n_features=X_std.shape[1], d_model=20, n_heads=2, K=3, seed=SEED, causal=True
    )
    tf_c.fit(X_std[train], y_train, lr=0.07, epochs=120, gamma=2.0, beta=0.99)
    post_c = tf_c.predict_proba(X_std)
    reg_c = toxic_overlay(
        apply_hysteresis(post_c.argmax(1), post_c, 3, 0.40), df["vpin"].values, 0.55
    )
    results.append(eval_full(df, reg_c, post_c, latent, holdout, "TF_causal_bal|v2"))

    tf_c5 = toxic_overlay(
        apply_hysteresis(post_c.argmax(1), post_c, 5, 0.50), df["vpin"].values, 0.55
    )
    results.append(eval_full(df, tf_c5, post_c, latent, holdout, "TF_causal_bal_hyst5|v2"))

    # 5) Bidireccional SOLO cota offline (look-ahead en atención)
    tf_b = BalancedTransformer(
        n_features=X_std.shape[1], d_model=20, n_heads=2, K=3, seed=SEED + 1, causal=False
    )
    tf_b.fit(X_std[train], y_train, lr=0.07, epochs=120, gamma=2.0, beta=0.99)
    post_b = tf_b.predict_proba(X_std)
    reg_b = toxic_overlay(
        apply_hysteresis(post_b.argmax(1), post_b, 3, 0.40), df["vpin"].values, 0.55
    )
    results.append(
        eval_full(df, reg_b, post_b, latent, holdout, "TF_BIDIR_offline_bound|v2")
    )

    # Tabla
    print("\n=== Resultados (v2 frozen + features enriched) ===")
    print(
        f"{'model':28} {'HO%':>5} {'acc%':>5} {'flip%':>6} {'net':>7} {'tri':>5} "
        f"{'vol_erase':>9} {'mae_min':>7} {'mins_det'}"
    )
    for r in results:
        print(
            f"{r['name']:28} {r['acc_HO_pct']:5.1f} {r['acc_pct']:5.1f} "
            f"{r['flip_flop_pct']:6.2f} {r['net']:7.2f} {r['tri']:>5} "
            f"{str(r['volatile_erased']):>9} {r['mae_min_vs_ui']:7.1f} {r['minutes_detected']}"
        )

    print("\n=== Minutos por estado (detalle) ===")
    for r in results:
        d = r["minutes_detail"]
        print(f"{r['name']}:")
        print(f"  detected {d['detected']}")
        print(f"  latent   {d['latent']}")
        print(f"  targetUI {d['target_ui']}")
        print(f"  vol_erased={d['volatile_erased']} mae_vs_ui={d['mae_minutes_vs_ui']:.1f}")

    # Literatura breve embebida en reporte
    literature = {
        "class_balance": (
            "Class-Balanced Focal Loss (Cui et al. 2019 + Lin et al. Focal Loss) "
            "repondera por effective number of samples y enfoca clases difíciles; "
            "estándar ante long-tail / multi-class imbalance en secuencias."
        ),
        "causal_vs_bidir": (
            "En series temporales operativas la máscara causal evita look-ahead. "
            "Papers de forecasting a veces reportan bi-directional como más fuerte "
            "en batch offline, pero eso no es desplegable como filtro en vivo sin fuga. "
            "Aquí bi-dir = cota superior offline solamente."
        ),
        "session_phase": (
            "Microestructura intradía: open/mid/close cambian liquidez, impacto y "
            "significado del order flow (U-shape volumen; impacts varían en el día)."
        ),
        "ofi_spread": (
            "OFI y spread son features de presión y costo de inmediatez; "
            "z-scores causales y EMA evitan normalización full-sample."
        ),
    }

    out = {
        "generator_frozen": gen_rep,
        "feat_cols": feat_cols,
        "results": results,
        "literature_notes": literature,
        "proposals": {
            "1_v2_frozen": True,
            "2_enriched_features": feat_cols,
            "3_balanced_focal_tf": True,
            "4_minutes_per_state": True,
            "5_causal_live_bidir_offline_bound_only": True,
        },
    }
    path = Path("/home/workdir/artifacts/gate_five_proposals_report.json")
    path.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    pd.DataFrame(
        [
            {
                **{k: v for k, v in r.items() if k != "minutes_detail"},
                "mins": str(r["minutes_detected"]),
            }
            for r in results
        ]
    ).to_csv("/home/workdir/artifacts/gate_five_proposals_table.csv", index=False)
    print(f"\nJSON: {path}")


if __name__ == "__main__":
    main()
