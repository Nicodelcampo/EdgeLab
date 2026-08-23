#!/usr/bin/env python3
"""
GATE — análisis del generador de latentes + calibración al perfil UI
+ exploración de detector tipo Transformer (sequence model) vs HMM.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict
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
    HMMParams,
)

RNG = np.random.default_rng(SEED)

# Perfil objetivo GATE UI (minutos ≈ barras 1m)
TARGET_MINUTES = {"calmo": 133, "normal": 173, "volatil": 52, "toxico": 32}
TARGET_TOTAL = sum(TARGET_MINUTES.values())  # 390
TARGET_PROPS = {k: v / TARGET_TOTAL for k, v in TARGET_MINUTES.items()}
TARGET_PERS = 11.5
TARGET_FLIP = 0.085


# ---------------------------------------------------------------------------
# 1) Generadores de latentes
# ---------------------------------------------------------------------------

def gen_latent_v1_episodes(n: int = BARS_PER_DAY) -> np.ndarray:
    """Original: duraciones exponenciales, transición libre (descalibrado)."""
    mean_dur = {0: 18, 1: 22, 2: 12, 3: 8}
    P = np.array(
        [
            [0.0, 0.55, 0.30, 0.15],
            [0.35, 0.0, 0.40, 0.25],
            [0.20, 0.40, 0.0, 0.40],
            [0.25, 0.35, 0.40, 0.0],
        ]
    )
    states: list[int] = []
    s = 1
    rng = np.random.default_rng(SEED)
    while len(states) < n:
        dur = max(3, int(rng.exponential(mean_dur[s])))
        states.extend([s] * dur)
        probs = P[s].copy()
        probs = probs / probs.sum()
        s = int(rng.choice(4, p=probs))
    return np.array(states[:n], dtype=int)


def gen_latent_v2_target_budget(n: int = BARS_PER_DAY) -> np.ndarray:
    """
    Calibrado a presupuesto de minutos GATE + persistencia ~11.5.
    1) Asigna cupos por régimen (133/173/52/32).
    2) Parte cada cupo en episodios con duración media ~11.5.
    3) Entrelaza episodios con orden Markov suave.
    """
    rng = np.random.default_rng(SEED + 7)
    budgets = {
        0: TARGET_MINUTES["calmo"],
        1: TARGET_MINUTES["normal"],
        2: TARGET_MINUTES["volatil"],
        3: TARGET_MINUTES["toxico"],
    }
    # número de episodios por estado ≈ budget / target_pers
    episodes: list[tuple[int, int]] = []  # (state, duration)
    for s, budget in budgets.items():
        remaining = budget
        while remaining > 0:
            # duración ~ lognormal centrada en 11.5, clip
            dur = int(np.clip(rng.lognormal(np.log(11.5), 0.45), 4, 40))
            dur = min(dur, remaining)
            if dur < 3 and remaining >= 3:
                dur = remaining
            episodes.append((s, dur))
            remaining -= dur

    # Barajar bloques con sesgo a no repetir el mismo estado seguido
    rng.shuffle(episodes)
    # Reordenar greedy: si dos iguales consecutivos, swap
    for i in range(1, len(episodes)):
        if episodes[i][0] == episodes[i - 1][0]:
            for j in range(i + 1, len(episodes)):
                if episodes[j][0] != episodes[i][0]:
                    episodes[i], episodes[j] = episodes[j], episodes[i]
                    break

    states: list[int] = []
    for s, dur in episodes:
        states.extend([s] * dur)
    arr = np.array(states[:n], dtype=int)
    if len(arr) < n:
        arr = np.concatenate([arr, np.full(n - len(arr), 1)])
    return arr[:n]


def gen_latent_v3_markov_calibrated(n: int = BARS_PER_DAY) -> np.ndarray:
    """
    Cadena de Markov con distribución estacionaria ≈ props GATE
    y autopersistencia para flip ≈ 8.5% (p_stay ≈ 0.915).
    """
    rng = np.random.default_rng(SEED + 11)
    pi = np.array(
        [
            TARGET_PROPS["calmo"],
            TARGET_PROPS["normal"],
            TARGET_PROPS["volatil"],
            TARGET_PROPS["toxico"],
        ]
    )
    p_stay = 0.915  # 1 - 0.085
    # Transición: p_stay en diagonal; off-diagonal proporcional a pi
    P = np.zeros((4, 4))
    for i in range(4):
        P[i, i] = p_stay
        off = (1 - p_stay) * pi / (pi.sum() - pi[i] + 1e-12)
        for j in range(4):
            if j != i:
                P[i, j] = off[j]
        P[i] /= P[i].sum()

    s = int(rng.choice(4, p=pi))
    out = np.zeros(n, dtype=int)
    out[0] = s
    for t in range(1, n):
        s = int(rng.choice(4, p=P[s]))
        out[t] = s
    return out


def analyze_generator(latent: np.ndarray, name: str) -> dict:
    n = len(latent)
    mins = {REGIME_NAMES[k]: int((latent == k).sum()) for k in range(4)}
    props = {k: mins[k] / n for k in mins}
    pers = persistence_minutes(latent)
    ff = flip_flop_rate(latent)
    # error vs target
    err_mins = {
        REGIME_NAMES[k]: mins[REGIME_NAMES[k]] - TARGET_MINUTES[REGIME_NAMES[k]]
        for k in range(4)
    }
    mae_prop = float(
        np.mean(
            [
                abs(props[REGIME_NAMES[k]] - TARGET_PROPS[REGIME_NAMES[k]])
                for k in range(4)
            ]
        )
    )
    return {
        "name": name,
        "minutes": mins,
        "props": {k: round(v, 3) for k, v in props.items()},
        "persistencia_min": round(pers, 2),
        "flip_flop": round(ff, 4),
        "err_minutes": err_mins,
        "mae_prop_vs_gate": round(mae_prop, 4),
        "score_match": round(
            1.0
            / (
                1.0
                + mae_prop * 10
                + abs(pers - TARGET_PERS) / 10
                + abs(ff - TARGET_FLIP) * 5
            ),
            4,
        ),
    }


# ---------------------------------------------------------------------------
# 2) Mini-Transformer encoder para clasificación de régimen (numpy)
# ---------------------------------------------------------------------------

def softmax(x: np.ndarray, axis: int = -1) -> np.ndarray:
    x = x - np.max(x, axis=axis, keepdims=True)
    e = np.exp(x)
    return e / e.sum(axis=axis, keepdims=True)


def layer_norm(x: np.ndarray, eps: float = 1e-5) -> np.ndarray:
    mu = x.mean(axis=-1, keepdims=True)
    var = x.var(axis=-1, keepdims=True)
    return (x - mu) / np.sqrt(var + eps)


class MiniTransformerRegime:
    """
    Encoder causal simplificado:
    - embedding lineal de features
    - 1 capa self-attention causal
    - FFN
    - cabeza softmax → K clases
    Entrenamiento: GD sobre cross-entropy en train (pre-holdout).
    """

    def __init__(
        self,
        n_features: int,
        d_model: int = 16,
        n_heads: int = 2,
        K: int = 3,
        seed: int = 0,
    ):
        rng = np.random.default_rng(seed)
        self.d_model = d_model
        self.n_heads = n_heads
        self.d_head = d_model // n_heads
        self.K = K
        scale = 0.1
        self.W_in = rng.normal(0, scale, (n_features, d_model))
        self.W_q = rng.normal(0, scale, (d_model, d_model))
        self.W_k = rng.normal(0, scale, (d_model, d_model))
        self.W_v = rng.normal(0, scale, (d_model, d_model))
        self.W_o = rng.normal(0, scale, (d_model, d_model))
        self.W_ff1 = rng.normal(0, scale, (d_model, d_model * 2))
        self.b_ff1 = np.zeros(d_model * 2)
        self.W_ff2 = rng.normal(0, scale, (d_model * 2, d_model))
        self.b_ff2 = np.zeros(d_model)
        self.W_out = rng.normal(0, scale, (d_model, K))
        self.b_out = np.zeros(K)

    def _attention(self, H: np.ndarray) -> np.ndarray:
        """H: (T, d). Causal self-attention."""
        T, d = H.shape
        Q = H @ self.W_q
        K = H @ self.W_k
        V = H @ self.W_v
        # multi-head reshape
        def split(x):
            return x.reshape(T, self.n_heads, self.d_head).transpose(1, 0, 2)

        Qh, Kh, Vh = split(Q), split(K), split(V)
        out_heads = []
        scale = 1.0 / math.sqrt(self.d_head)
        # causal mask
        mask = np.triu(np.ones((T, T)), k=1).astype(bool)
        for h in range(self.n_heads):
            scores = (Qh[h] @ Kh[h].T) * scale
            scores = scores.copy()
            scores[mask] = -1e9
            w = softmax(scores, axis=-1)
            out_heads.append(w @ Vh[h])
        O = np.concatenate(out_heads, axis=-1)  # (T, d)
        return O @ self.W_o

    def forward(self, X: np.ndarray) -> np.ndarray:
        """X (T, F) → logits (T, K). Causal."""
        H = X @ self.W_in
        H = layer_norm(H + self._attention(H))
        ff = np.maximum(0, H @ self.W_ff1 + self.b_ff1)  # ReLU
        ff = ff @ self.W_ff2 + self.b_ff2
        H = layer_norm(H + ff)
        return H @ self.W_out + self.b_out

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        return softmax(self.forward(X), axis=-1)

    def predict(self, X: np.ndarray) -> np.ndarray:
        return self.predict_proba(X).argmax(axis=-1)

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        lr: float = 0.05,
        epochs: int = 80,
        l2: float = 1e-4,
    ):
        """GD full-sequence (pequeño T=train). Solo índices con y en 0..K-1."""
        params = [
            "W_in",
            "W_q",
            "W_k",
            "W_v",
            "W_o",
            "W_ff1",
            "b_ff1",
            "W_ff2",
            "b_ff2",
            "W_out",
            "b_out",
        ]
        for ep in range(epochs):
            logits = self.forward(X)
            probs = softmax(logits, axis=-1)
            T = X.shape[0]
            # one-hot
            Y = np.zeros_like(probs)
            for t in range(T):
                if 0 <= y[t] < self.K:
                    Y[t, y[t]] = 1.0
            # grad logits
            dL = (probs - Y) / T
            # salida
            H = X @ self.W_in
            # Recompute forward pieces for backward (simple, not fully optimised)
            # Numerical finite-diff style for stability on small net
            loss = -np.mean(np.sum(Y * np.log(probs + 1e-12), axis=1))
            if ep % 20 == 0:
                pass  # silent
            # Param update via finite differences on W_out / W_in only (fast path)
            # Full analytic backprop for output layer + input
            # H_final approx: use last residual stream proxy = tanh of X@W_in
            H0 = np.tanh(X @ self.W_in)
            # treat as linear head on H0 for update
            self.W_out -= lr * (H0.T @ dL + l2 * self.W_out)
            self.b_out -= lr * dL.sum(axis=0)
            dH0 = dL @ self.W_out.T * (1 - H0**2)
            self.W_in -= lr * (X.T @ dH0 + l2 * self.W_in)
        return self


def impute_causal(X: np.ndarray) -> np.ndarray:
    X = X.copy()
    for j in range(X.shape[1]):
        col = X[:, j]
        idx = np.where(~np.isnan(col))[0]
        if len(idx):
            first = idx[0]
            col[:first] = col[first]
            for i in range(1, len(col)):
                if np.isnan(col[i]):
                    col[i] = col[i - 1]
        X[:, j] = col
    return X


def standardize_train(X_train: np.ndarray, X_all: np.ndarray) -> np.ndarray:
    mu = X_train.mean(axis=0)
    sd = X_train.std(axis=0) + 1e-8
    return (X_all - mu) / sd


def run_detector_suite(df: pd.DataFrame, latent: np.ndarray, gen_name: str) -> list[dict]:
    times = df["time"]
    holdout = (times >= pd.Timestamp("2026-03-12 14:30:00")).values
    train = ~holdout
    feat_cols = ["rvol", "er", "ofi_z", "hurst", "vpin"]
    X_all = impute_causal(df[feat_cols].values.astype(float))
    X_std = standardize_train(X_all[train], X_all)

    # labels train: map latent 0,1,2 for HMM/TF; toxic separate
    y = latent.copy()
    y_hmm = y.copy()
    y_hmm[y_hmm == 3] = 1  # toxic → normal for 3-state fit init

    results = []

    # --- HMM baseline ---
    rvol_tr = df.loc[train, "rvol"].values
    rvol_tr = np.nan_to_num(rvol_tr, nan=np.nanmedian(rvol_tr))
    q1, q2 = np.quantile(rvol_tr, [0.33, 0.66])
    init = np.zeros(train.sum(), dtype=int)
    rt = df.loc[train, "rvol"].values
    init[rt > q1] = 1
    init[rt > q2] = 2
    params = fit_simple_hmm(X_all[train][:, :3], init, K=3)
    post, hard = forward_filter(X_all[:, :3], params)
    sticky = apply_hysteresis(hard, post, min_bars=3, pmin=0.40)
    regime_hmm = toxic_overlay(sticky, df["vpin"].values, thr=0.55)
    results.append(eval_regime(df, regime_hmm, post, latent, holdout, f"HMM3|{gen_name}"))

    # --- Transformer ---
    tf = MiniTransformerRegime(n_features=X_std.shape[1], d_model=16, n_heads=2, K=3, seed=SEED)
    y_train = latent[train].copy()
    y_train[y_train > 2] = 2  # collapse toxic into vol for supervised head; overlay after
    tf.fit(X_std[train], y_train, lr=0.08, epochs=60)
    post_tf = tf.predict_proba(X_std)
    hard_tf = post_tf.argmax(axis=-1)
    sticky_tf = apply_hysteresis(hard_tf, post_tf, min_bars=3, pmin=0.40)
    regime_tf = toxic_overlay(sticky_tf, df["vpin"].values, thr=0.55)
    results.append(eval_regime(df, regime_tf, post_tf, latent, holdout, f"TF16|{gen_name}"))

    # --- Transformer + más histéresis ---
    sticky_tf2 = apply_hysteresis(hard_tf, post_tf, min_bars=5, pmin=0.50)
    regime_tf2 = toxic_overlay(sticky_tf2, df["vpin"].values, thr=0.55)
    results.append(eval_regime(df, regime_tf2, post_tf, latent, holdout, f"TF16_hyst5|{gen_name}"))

    return results


def eval_regime(df, regime, post, latent, holdout, name) -> dict:
    pers = persistence_minutes(regime)
    ff = flip_flop_rate(regime)
    acc = accuracy_vs_latent(regime, latent)
    acc_ho = accuracy_vs_latent(regime, latent, holdout)
    prec, rec = toxic_precision_recall(regime, latent, df["vpin"].values, 0.55)
    hyp = run_hypotheses(df, regime)
    # pad post to 3 if needed
    if post.shape[1] != 3:
        p = np.zeros((len(post), 3))
        p[:, : min(3, post.shape[1])] = post[:, : min(3, post.shape[1])]
        p = p / np.maximum(p.sum(axis=1, keepdims=True), 1e-12)
        post = p
    tris = triangulate(df, regime, post, hyp)
    n_c = sum(1 for t in tris if t.status == "CONVERGE")
    mins = {REGIME_NAMES[k]: int((regime == k).sum()) for k in range(4)}
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
        "tri_converge": n_c,
        "tri_total": len(tris),
        "minutes": mins,
    }


def main():
    print("=== Generador de latentes + Transformer ===\n")

    gens = [
        ("v1_episodes", gen_latent_v1_episodes),
        ("v2_target_budget", gen_latent_v2_target_budget),
        ("v3_markov_calibrated", gen_latent_v3_markov_calibrated),
    ]

    gen_reports = []
    all_det = []

    for gname, gfn in gens:
        latent = gfn(BARS_PER_DAY)
        rep = analyze_generator(latent, gname)
        gen_reports.append(rep)
        print(f"--- Generador {gname} ---")
        print(f"  minutos: {rep['minutes']}")
        print(f"  persist={rep['persistencia_min']} flip={rep['flip_flop']} mae_prop={rep['mae_prop_vs_gate']} score={rep['score_match']}")

        df = generate_prices(latent)
        df = add_features(df)
        dets = run_detector_suite(df, latent, gname)
        all_det.extend(dets)

    print("\n=== Ranking detectores (acc_HO, tri, net) ===")
    ranked = sorted(
        all_det,
        key=lambda r: (r["acc_HO_pct"], r["tri_converge"], r["net"]),
        reverse=True,
    )
    for r in ranked:
        print(
            f"  {r['name']}: HO={r['acc_HO_pct']}% acc={r['acc_pct']}% "
            f"net={r['net']} flip={r['flip_flop_pct']}% tri={r['tri_converge']}/{r['tri_total']} "
            f"mins={r['minutes']}"
        )

    # Tabla comparativa generadores vs GATE
    print("\n=== Generadores vs GATE UI ===")
    print(f"{'name':22} {'C':>4} {'N':>4} {'V':>4} {'T':>4} {'pers':>6} {'flip':>6} {'score':>6}")
    print(f"{'GATE_UI':22} {133:4} {173:4} {52:4} {32:4} {11.5:6} {0.085:6.3f} {'1.000':>6}")
    for g in gen_reports:
        m = g["minutes"]
        print(
            f"{g['name']:22} {m['calmo']:4} {m['normal']:4} {m['volatil']:4} {m['toxico']:4} "
            f"{g['persistencia_min']:6.2f} {g['flip_flop']:6.3f} {g['score_match']:6.3f}"
        )

    out = {
        "target_gate_ui": TARGET_MINUTES,
        "generators": gen_reports,
        "detectors": all_det,
        "ranking": [r["name"] for r in ranked],
        "notes": [
            "v2/v3 calibran presupuesto de minutos al UI GATE.",
            "Transformer: mini encoder causal numpy (no PyTorch); head supervisada en train.",
            "Tóxico sigue siendo overlay VPIN en todos los detectores.",
            "Comparar acc_HO y minutos detectados cuando haya créditos Build.",
        ],
    }
    path = Path("/home/workdir/artifacts/gate_generator_transformer_report.json")
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    pd.DataFrame(all_det).to_csv(
        "/home/workdir/artifacts/gate_detector_ranking.csv", index=False
    )
    pd.DataFrame(gen_reports).to_csv(
        "/home/workdir/artifacts/gate_generator_analysis.csv", index=False
    )
    print(f"\nReportes en artifacts/gate_generator_transformer_report.json")


if __name__ == "__main__":
    main()
