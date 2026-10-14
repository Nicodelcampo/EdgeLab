#!/usr/bin/env python3
"""
GATE recreate — motor de micro-regímenes (sin créditos de Build).
Sesión sintética ES 1m + features causales + detector sticky + overlay VPIN
+ hipótesis con costos + triangulación de métricas.
Seed alineable: 20260312
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 20260312
RNG = np.random.default_rng(SEED)

# --- Sesión RTH ES 1m ---
START = "09:30"
END = "16:00"
HOLDOUT_START = "14:30"
BARS_PER_DAY = 390  # 6.5h * 60

# Costos (ticks ES aprox; 1 punto = 4 ticks en modelo simplificado)
TICK_VALUE = 0.25  # puntos por tick de precio en ES simplificado
SPREAD_TICKS = 1.0
FEE_TICKS = 0.5
SLIP_TICKS = 0.5
FLIP_COST_TICKS = SPREAD_TICKS + FEE_TICKS  # costo extra al cambiar régimen de gate

REGIME_NAMES = {0: "calmo", 1: "normal", 2: "volatil", 3: "toxico"}


def session_index() -> pd.DatetimeIndex:
    # Día ficticio; solo importa el reloj intradía
    base = pd.Timestamp("2026-03-12 09:30:00")
    return pd.date_range(base, periods=BARS_PER_DAY, freq="1min")


def generate_latent_regimes(n: int) -> np.ndarray:
    """Genera estados latentes con persistencia realista (minutos)."""
    # Persistencias medias objetivo ~ 10-20 min
    mean_dur = {0: 18, 1: 22, 2: 12, 3: 8}
    # Transiciones: desde cada estado, preferir quedarse
    P = np.array(
        [
            [0.0, 0.55, 0.30, 0.15],  # desde calmo (se rellena diag)
            [0.35, 0.0, 0.40, 0.25],
            [0.20, 0.40, 0.0, 0.40],
            [0.25, 0.35, 0.40, 0.0],
        ]
    )
    # Convertir a probs de salto por barra vía duración geométrica aproximada
    # Simulación por episodios
    states = []
    s = 1  # empieza normal
    while len(states) < n:
        dur = max(3, int(RNG.exponential(mean_dur[s])))
        states.extend([s] * dur)
        # siguiente
        probs = P[s].copy()
        probs = probs / probs.sum()
        s = int(RNG.choice(4, p=probs))
    return np.array(states[:n], dtype=int)


def generate_prices(latent: np.ndarray) -> pd.DataFrame:
    """Mid, spread, volumen, signed flow sintéticos condicionados al latente."""
    n = len(latent)
    mid = np.zeros(n)
    spread = np.zeros(n)
    volume = np.zeros(n)
    signed = np.zeros(n)
    ofi = np.zeros(n)

    mid[0] = 5240.0
    vol_scale = {0: 0.15, 1: 0.35, 2: 0.90, 3: 1.20}
    spread_base = {0: 0.25, 1: 0.50, 2: 0.75, 3: 1.25}
    flow_bias = {0: 0.0, 1: 0.05, 2: 0.0, 3: -0.15}  # tóxico: flujo adverso

    for t in range(1, n):
        s = latent[t]
        ret = RNG.normal(flow_bias[s] * 0.02, vol_scale[s] * 0.25)
        mid[t] = mid[t - 1] + ret
        spread[t] = max(0.25, spread_base[s] + RNG.normal(0, 0.1))
        volume[t] = max(50, RNG.lognormal(6.5 if s < 2 else 7.2, 0.4))
        # signed aggressive volume
        imb = RNG.normal(flow_bias[s], 0.35 if s != 3 else 0.55)
        signed[t] = np.clip(imb, -1, 1) * volume[t]
        # OFI proxy (event-like): correlación con signed + ruido de libro
        ofi[t] = signed[t] * 0.6 + RNG.normal(0, volume[t] * 0.15)

    times = session_index()
    return pd.DataFrame(
        {
            "time": times,
            "mid": mid,
            "spread": spread,
            "volume": volume,
            "signed": signed,
            "ofi_raw": ofi,
            "latent": latent,
        }
    )


# --- Features causales (solo pasado) ---

def rolling_z(x: np.ndarray, win: int) -> np.ndarray:
    out = np.full_like(x, np.nan, dtype=float)
    for i in range(win, len(x)):
        w = x[i - win : i]  # excluye i → causal
        mu, sd = w.mean(), w.std()
        out[i] = 0.0 if sd < 1e-12 else (x[i] - mu) / sd
    return out


def efficiency_ratio(mid: np.ndarray, win: int = 10) -> np.ndarray:
    out = np.full(len(mid), np.nan)
    for i in range(win, len(mid)):
        net = abs(mid[i] - mid[i - win])
        path = np.sum(np.abs(np.diff(mid[i - win : i + 1])))
        out[i] = net / path if path > 1e-12 else 0.0
    return out


def hurst_rs(mid: np.ndarray, win: int = 32) -> np.ndarray:
    """Hurst simplificado por R/S en ventana causal."""
    out = np.full(len(mid), np.nan)
    for i in range(win, len(mid)):
        r = np.diff(np.log(np.maximum(mid[i - win : i + 1], 1e-6)))
        if len(r) < 8:
            continue
        mean = r.mean()
        y = np.cumsum(r - mean)
        R = y.max() - y.min()
        S = r.std()
        if S < 1e-12:
            out[i] = 0.5
        else:
            # H ~ log(R/S) / log(n)
            out[i] = float(np.clip(np.log(R / S + 1e-12) / np.log(len(r)), 0.0, 1.0))
    return out


def vpin_proxy(signed: np.ndarray, volume: np.ndarray, bucket_vol: float = 5000.0) -> np.ndarray:
    """VPIN-like: imbalance en buckets de volumen (causal al cerrar bucket)."""
    n = len(signed)
    out = np.full(n, np.nan)
    acc_buy = acc_sell = acc_v = 0.0
    last_vpin = 0.5
    for i in range(n):
        v = volume[i]
        if signed[i] >= 0:
            acc_buy += abs(signed[i])
        else:
            acc_sell += abs(signed[i])
        acc_v += v
        if acc_v >= bucket_vol:
            tot = acc_buy + acc_sell
            last_vpin = abs(acc_buy - acc_sell) / tot if tot > 0 else 0.0
            acc_buy = acc_sell = acc_v = 0.0
        out[i] = last_vpin
    return out


def kyle_lambda(mid: np.ndarray, signed: np.ndarray, win: int = 20) -> np.ndarray:
    """λ causal: regresión Δmid ~ signed en ventana pasada."""
    out = np.full(len(mid), np.nan)
    for i in range(win + 1, len(mid)):
        dy = np.diff(mid[i - win : i + 1])
        x = signed[i - win + 1 : i + 1]
        if len(x) != len(dy):
            continue
        # solo pasado estricto para coef: usa hasta i-1 en práctica simplificada
        x = x[:-1]
        dy = dy[:-1]
        if len(x) < 5:
            continue
        varx = np.var(x)
        if varx < 1e-12:
            out[i] = 0.0
        else:
            out[i] = float(np.cov(x, dy)[0, 1] / varx)
    return out


def shannon_entropy(probs: np.ndarray, eps: float = 1e-12) -> float:
    p = np.clip(probs, eps, 1.0)
    p = p / p.sum()
    return float(-np.sum(p * np.log(p)))


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    mid = df["mid"].values
    signed = df["signed"].values
    vol = df["volume"].values
    ofi = df["ofi_raw"].values

    df = df.copy()
    df["ret"] = np.concatenate([[0.0], np.diff(mid)])
    df["ofi_z"] = rolling_z(ofi, 20)
    df["tape_imb"] = signed / np.maximum(vol, 1.0)
    df["er"] = efficiency_ratio(mid, 10)
    df["hurst"] = hurst_rs(mid, 32)
    df["vpin"] = vpin_proxy(signed, vol, bucket_vol=8000.0)
    df["kyle_l"] = kyle_lambda(mid, signed, 20)
    df["rvol"] = (
        pd.Series(df["ret"]).rolling(15, min_periods=15).std().shift(1).values
    )  # causal
    return df


# --- Detector: HMM gaussiano simplificado forward + sticky ---

@dataclass
class HMMParams:
    means: np.ndarray  # (K, F)
    covs: np.ndarray  # (K, F)
    log_trans: np.ndarray  # (K, K)
    log_start: np.ndarray  # (K,)


def fit_simple_hmm(X: np.ndarray, labels_init: np.ndarray, K: int = 3) -> HMMParams:
    """Ajuste ingenuo por clusters iniciales (solo train). K estados no tóxicos."""
    F = X.shape[1]
    means = np.zeros((K, F))
    covs = np.ones((K, F))
    for k in range(K):
        mask = labels_init == k
        if mask.sum() < 5:
            means[k] = X.mean(axis=0)
            covs[k] = X.std(axis=0) + 1e-3
        else:
            means[k] = X[mask].mean(axis=0)
            covs[k] = X[mask].std(axis=0) + 1e-3
    # sticky transitions
    trans = np.full((K, K), 0.05 / (K - 1))
    np.fill_diagonal(trans, 0.90)
    log_trans = np.log(trans)
    log_start = np.log(np.ones(K) / K)
    return HMMParams(means, covs, log_trans, log_start)


def log_emission(x: np.ndarray, params: HMMParams) -> np.ndarray:
    """log N(x | mean_k, diag cov_k) para cada k."""
    K, F = params.means.shape
    out = np.zeros(K)
    for k in range(K):
        v = params.covs[k] ** 2
        diff = x - params.means[k]
        out[k] = -0.5 * np.sum(diff**2 / v + np.log(2 * np.pi * v))
    return out


def forward_filter(X: np.ndarray, params: HMMParams) -> tuple[np.ndarray, np.ndarray]:
    """Filtro forward causal. Returns posteriors (T,K), hard path sticky."""
    T, K = X.shape[0], params.means.shape[0]
    post = np.zeros((T, K))
    log_alpha = np.zeros((T, K))
    log_alpha[0] = params.log_start + log_emission(X[0], params)
    log_alpha[0] -= np.logaddexp.reduce(log_alpha[0])
    post[0] = np.exp(log_alpha[0])

    for t in range(1, T):
        emis = log_emission(X[t], params)
        for k in range(K):
            log_alpha[t, k] = emis[k] + np.logaddexp.reduce(
                log_alpha[t - 1] + params.log_trans[:, k]
            )
        log_alpha[t] -= np.logaddexp.reduce(log_alpha[t])
        post[t] = np.exp(log_alpha[t])
    hard = post.argmax(axis=1)
    return post, hard


def apply_hysteresis(hard: np.ndarray, post: np.ndarray, min_bars: int = 3, pmin: float = 0.45) -> np.ndarray:
    """Sticky: no cambia hasta min_bars y posterior del nuevo > pmin."""
    out = hard.copy()
    current = out[0]
    hold = 0
    for t in range(1, len(out)):
        cand = hard[t]
        hold += 1
        if cand != current:
            if hold >= min_bars and post[t, cand] >= pmin:
                current = cand
                hold = 0
            else:
                out[t] = current
        else:
            out[t] = current
            if hold > 1000:
                hold = min_bars
    return out


def toxic_overlay(regime: np.ndarray, vpin: np.ndarray, thr: float = 0.55) -> np.ndarray:
    """Tóxico = overlay VPIN, no 4º estado HMM."""
    out = regime.copy()
    for t in range(len(out)):
        if not np.isnan(vpin[t]) and vpin[t] >= thr:
            out[t] = 3
    return out


# --- Hipótesis por régimen + costos ---

def run_hypotheses(df: pd.DataFrame, regime: np.ndarray) -> dict:
    """
    Reglas simples por régimen (tesis económica).
    Retornos en puntos de mid; costos en ticks convertidos a puntos.
    """
    mid = df["mid"].values
    ret = np.concatenate([[0.0], np.diff(mid)])
    n = len(mid)
    cost_point = (SPREAD_TICKS + FEE_TICKS + SLIP_TICKS) * TICK_VALUE / 4.0
    # simplificación: 1 tick de precio ES = 0.25 pt; cost total ~ cost_point por trade

    trades = []
    position = 0
    entry_px = 0.0
    equity_gross = [0.0]
    equity_net = [0.0]
    prev_reg = regime[0]

    for t in range(1, n):
        r = regime[t]
        # flip de régimen: costo de salida si había posición
        if r != prev_reg and position != 0:
            pnl = position * (mid[t] - entry_px)
            trades.append({"t": t, "pnl_gross": pnl, "pnl_net": pnl - cost_point, "reason": "regime_flip"})
            position = 0
        prev_reg = r

        signal = 0
        if r == 0:  # calmo → mean reversion corta
            if df["er"].iloc[t] < 0.25 and df["tape_imb"].iloc[t] > 0.2:
                signal = -1
            elif df["er"].iloc[t] < 0.25 and df["tape_imb"].iloc[t] < -0.2:
                signal = 1
        elif r == 1:  # normal → continuidad suave
            if df["er"].iloc[t] > 0.45 and df["tape_imb"].iloc[t] > 0.15:
                signal = 1
            elif df["er"].iloc[t] > 0.45 and df["tape_imb"].iloc[t] < -0.15:
                signal = -1
        elif r == 2:  # volátil → momentum
            if df["hurst"].iloc[t] > 0.55 and ret[t] > 0:
                signal = 1
            elif df["hurst"].iloc[t] > 0.55 and ret[t] < 0:
                signal = -1
        else:  # tóxico → no operar
            signal = 0
            if position != 0:
                pnl = position * (mid[t] - entry_px)
                trades.append({"t": t, "pnl_gross": pnl, "pnl_net": pnl - cost_point, "reason": "toxic_flat"})
                position = 0

        if signal != 0 and position == 0:
            position = signal
            entry_px = mid[t]
            # cobra entrada
            equity_net.append(equity_net[-1] - cost_point * 0.5)
            equity_gross.append(equity_gross[-1])
        elif signal != 0 and position == signal:
            equity_gross.append(equity_gross[-1] + position * ret[t])
            equity_net.append(equity_net[-1] + position * ret[t])
        elif signal != 0 and position == -signal:
            pnl = position * (mid[t] - entry_px)
            trades.append({"t": t, "pnl_gross": pnl, "pnl_net": pnl - cost_point, "reason": "reverse"})
            position = signal
            entry_px = mid[t]
            equity_gross.append(equity_gross[-1] + pnl)
            equity_net.append(equity_net[-1] + pnl - cost_point)
        else:
            if position != 0:
                equity_gross.append(equity_gross[-1] + position * ret[t])
                equity_net.append(equity_net[-1] + position * ret[t])
            else:
                equity_gross.append(equity_gross[-1])
                equity_net.append(equity_net[-1])

    # flatten EOD
    if position != 0:
        pnl = position * (mid[-1] - entry_px)
        trades.append({"t": n - 1, "pnl_gross": pnl, "pnl_net": pnl - cost_point, "reason": "eod"})
        equity_gross.append(equity_gross[-1] + pnl)
        equity_net.append(equity_net[-1] + pnl - cost_point)

    gross = sum(tr["pnl_gross"] for tr in trades)
    net = sum(tr["pnl_net"] for tr in trades)
    return {
        "n_trades": len(trades),
        "gross": round(gross, 2),
        "net": round(net, 2),
        "trades": trades,
        "equity_gross": equity_gross,
        "equity_net": equity_net,
    }


# --- Métricas de calidad del detector ---

def persistence_minutes(regime: np.ndarray) -> float:
    durs = []
    run = 1
    for i in range(1, len(regime)):
        if regime[i] == regime[i - 1]:
            run += 1
        else:
            durs.append(run)
            run = 1
    durs.append(run)
    return float(np.mean(durs))  # 1 bar = 1 min


def flip_flop_rate(regime: np.ndarray) -> float:
    changes = np.sum(regime[1:] != regime[:-1])
    return float(changes / max(len(regime) - 1, 1))


def accuracy_vs_latent(pred: np.ndarray, latent: np.ndarray, mask: np.ndarray | None = None) -> float:
    """Latente 0-2 mapea a HMM; tóxico latente (3) vs overlay se evalúa aparte."""
    if mask is None:
        mask = np.ones(len(pred), dtype=bool)
    # solo donde latente no es tóxico puro para estados HMM
    m = mask & (latent < 3) & (pred < 3)
    if m.sum() == 0:
        return float("nan")
    return float((pred[m] == latent[m]).mean())


def toxic_precision_recall(pred: np.ndarray, latent: np.ndarray, vpin: np.ndarray, thr: float) -> tuple[float, float]:
    # ground: latente==3 OR (definir tóxico latente por VPIN alto en generador)
    # Aquí latente 3 es ground de toxicidad estructural
    true = latent == 3
    det = pred == 3
    tp = (true & det).sum()
    fp = (~true & det).sum()
    fn = (true & ~det).sum()
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    return float(prec), float(rec)


# --- TRIANGULACIÓN ---

@dataclass
class TriangleResult:
    instrument: str
    via_a: str
    via_b: str
    value_a: float
    value_b: float
    tolerance: float
    status: str  # CONVERGE | DIVERGE | INSUFFICIENT
    note: str


def triangulate(df: pd.DataFrame, regime: np.ndarray, post: np.ndarray, hyp: dict) -> list[TriangleResult]:
    results = []

    # 1) Persistencia: duración empírica vs 1 / (1 - diag transición empírica)
    pers_a = persistence_minutes(regime)
    changes = regime[1:] != regime[:-1]
    # tasa de salida media
    exit_rate = changes.mean() if len(changes) else 0.0
    pers_b = 1.0 / exit_rate if exit_rate > 1e-9 else 1e9
    tol = max(3.0, 0.35 * pers_a)
    status = "CONVERGE" if abs(pers_a - pers_b) <= tol else "DIVERGE"
    results.append(
        TriangleResult(
            "persistencia_min",
            "duración media de rachas",
            "1 / tasa_cambio_empírica",
            round(pers_a, 2),
            round(pers_b, 2),
            tol,
            status,
            "Ambas miden estabilidad del label sticky",
        )
    )

    # 2) Flip-flop: tasa de cambios vs 1 - autocorrelación lag-1 del estado
    ff_a = flip_flop_rate(regime)
    # correlación de estados codificados
    r0, r1 = regime[:-1].astype(float), regime[1:].astype(float)
    if r0.std() > 0 and r1.std() > 0:
        ac = float(np.corrcoef(r0, r1)[0, 1])
    else:
        ac = 1.0
    ff_b = 1.0 - max(ac, 0.0)
    tol2 = 0.08
    status = "CONVERGE" if abs(ff_a - ff_b) <= tol2 else "DIVERGE"
    results.append(
        TriangleResult(
            "flip_flop",
            "cambios/barra",
            "1 - autocorr(estado, lag1)",
            round(ff_a, 4),
            round(ff_b, 4),
            tol2,
            status,
            "Dos lecturas de inestabilidad del detector",
        )
    )

    # 3) OFI vs tape imbalance: correlación debe ser positiva (mismo constructo de presión)
    ofi = df["ofi_z"].values
    tape = df["tape_imb"].values
    m = ~np.isnan(ofi) & ~np.isnan(tape)
    if m.sum() > 30:
        corr = float(np.corrcoef(ofi[m], tape[m])[0, 1])
        # vía A: corr; vía B: fracción de signos alineados
        sign_align = float(np.mean(np.sign(ofi[m]) == np.sign(tape[m])))
        # consenso: corr > 0.3 y sign_align > 0.55
        status = "CONVERGE" if (corr > 0.25 and sign_align > 0.55) else "DIVERGE"
        results.append(
            TriangleResult(
                "ofi_vs_tape",
                "corr(ofi_z, tape_imb)",
                "fracción signos alineados",
                round(corr, 3),
                round(sign_align, 3),
                0.0,
                status,
                "Presión de libro proxy vs agresores; deben co-moverse",
            )
        )
    else:
        results.append(
            TriangleResult("ofi_vs_tape", "corr", "sign_align", float("nan"), float("nan"), 0, "INSUFFICIENT", "")
        )

    # 4) Régimen vs volatilidad realizada: estado volátil debe tener mayor rvol
    rvol = df["rvol"].values
    m2 = ~np.isnan(rvol)
    means = {}
    for k, name in [(0, "calmo"), (1, "normal"), (2, "volatil")]:
        mk = m2 & (regime == k)
        means[name] = float(np.nanmean(rvol[mk])) if mk.sum() else float("nan")
    # vía A: mean_rvol(volatil) > mean_rvol(calmo)
    # vía B: mean_rvol(volatil) > mean_rvol(normal)
    ok_a = means["volatil"] > means["calmo"] if not np.isnan(means["volatil"]) else False
    ok_b = means["volatil"] > means["normal"] if not np.isnan(means["volatil"]) else False
    status = "CONVERGE" if (ok_a and ok_b) else "DIVERGE"
    results.append(
        TriangleResult(
            "regimen_vs_rvol",
            f"rvol_vol>rvol_calmo ({means['volatil']:.4f}>{means['calmo']:.4f})",
            f"rvol_vol>rvol_norm ({means['volatil']:.4f}>{means['normal']:.4f})",
            1.0 if ok_a else 0.0,
            1.0 if ok_b else 0.0,
            0.0,
            status,
            "Semántica del estado volátil debe reflejarse en rvol",
        )
    )

    # 5) Equity bruta vs neta: gap debe ≈ costos por trade * n_trades (orden de magnitud)
    gross, net, nt = hyp["gross"], hyp["net"], hyp["n_trades"]
    gap_a = gross - net
    cost_per = (SPREAD_TICKS + FEE_TICKS + SLIP_TICKS) * TICK_VALUE / 4.0
    gap_b = cost_per * max(nt, 1)
    # tolerancia amplia: factor 0.3–3x
    ratio = gap_a / gap_b if gap_b > 1e-9 else float("inf")
    status = "CONVERGE" if 0.25 <= ratio <= 4.0 else "DIVERGE"
    results.append(
        TriangleResult(
            "cost_gap",
            "gross - net observado",
            "costo_unitario * n_trades",
            round(gap_a, 3),
            round(gap_b, 3),
            0.0,
            status,
            f"ratio gap_obs/gap_esp={ratio:.2f}; valida contabilidad de costos",
        )
    )

    # 6) Entropía de posteriors vs confianza del hard label
    ent = np.array([shannon_entropy(post[t]) for t in range(len(post))])
    conf = post.max(axis=1)
    # alta conf ↔ baja entropía
    m3 = np.ones(len(ent), dtype=bool)
    corr_ec = float(np.corrcoef(ent[m3], conf[m3])[0, 1])
    status = "CONVERGE" if corr_ec < -0.5 else "DIVERGE"
    results.append(
        TriangleResult(
            "entropy_vs_confidence",
            "corr(entropía, max posterior)",
            "esperado < -0.5",
            round(corr_ec, 3),
            -0.5,
            0.0,
            status,
            "Invariante de probabilidad: más confianza ⇒ menos entropía",
        )
    )

    return results


def main():
    print("=== GATE recreate · seed", SEED, "===\n")

    latent = generate_latent_regimes(BARS_PER_DAY)
    df = generate_prices(latent)
    df = add_features(df)

    # Train solo pre-holdout
    times = df["time"]
    holdout_mask = times >= pd.Timestamp("2026-03-12 14:30:00")
    train_mask = ~holdout_mask

    # Features para HMM (3 estados): rvol, er, ofi_z
    feat_cols = ["rvol", "er", "ofi_z"]
    X_all = df[feat_cols].values.copy()
    # imputación causal simple
    for j in range(X_all.shape[1]):
        col = X_all[:, j]
        idx = np.where(~np.isnan(col))[0]
        if len(idx):
            first = idx[0]
            col[:first] = col[first]
            for i in range(1, len(col)):
                if np.isnan(col[i]):
                    col[i] = col[i - 1]
        X_all[:, j] = col

    # init labels en train por cuantiles de rvol
    rvol_train = df.loc[train_mask, "rvol"].values
    rvol_train = np.nan_to_num(rvol_train, nan=np.nanmedian(rvol_train))
    q1, q2 = np.quantile(rvol_train, [0.33, 0.66])
    init = np.zeros(train_mask.sum(), dtype=int)
    rt = df.loc[train_mask, "rvol"].values
    init[rt > q1] = 1
    init[rt > q2] = 2

    params = fit_simple_hmm(X_all[train_mask.values], init, K=3)
    post, hard = forward_filter(X_all, params)
    sticky = apply_hysteresis(hard, post, min_bars=3, pmin=0.40)
    regime = toxic_overlay(sticky, df["vpin"].values, thr=0.55)

    # Métricas
    pers = persistence_minutes(regime)
    ff = flip_flop_rate(regime)
    acc_all = accuracy_vs_latent(regime, df["latent"].values)
    acc_ho = accuracy_vs_latent(regime, df["latent"].values, holdout_mask.values)
    prec, rec = toxic_precision_recall(regime, df["latent"].values, df["vpin"].values, 0.55)

    hyp = run_hypotheses(df, regime)

    # Tiempo por régimen
    mins = {REGIME_NAMES[k]: int((regime == k).sum()) for k in range(4)}

    print("--- KPIs ---")
    print(f"Persistencia:     {pers:.1f} min")
    print(f"Flip-flop:        {ff*100:.1f}%")
    print(f"Acierto vs latente: {acc_all*100:.0f}%  holdout {acc_ho*100:.0f}%")
    print(f"Tóxico P/R:       {prec*100:.0f}% · {rec*100:.0f}%")
    print(f"Equity bruta:     {hyp['gross']:+.2f}")
    print(f"Equity neta:      {hyp['net']:+.2f}  ({hyp['n_trades']} trades)")
    print(f"Minutos:          {mins}")

    tris = triangulate(df, regime, post, hyp)
    print("\n--- TRIANGULACIÓN ---")
    for tr in tris:
        print(
            f"[{tr.status}] {tr.instrument}: A={tr.value_a} | B={tr.value_b} | tol={tr.tolerance} — {tr.note}"
        )

    # Export
    out = {
        "seed": SEED,
        "kpis": {
            "persistencia_min": round(pers, 2),
            "flip_flop": round(ff, 4),
            "acierto_all": round(acc_all, 4),
            "acierto_holdout": round(acc_ho, 4),
            "toxic_precision": round(prec, 4),
            "toxic_recall": round(rec, 4),
            "equity_gross": hyp["gross"],
            "equity_net": hyp["net"],
            "n_trades": hyp["n_trades"],
            "minutes": mins,
        },
        "triangulation": [asdict(t) for t in tris],
        "notes": [
            "Motor recreado offline; no es el binario del Build GATE.",
            "Datos sintéticos con el mismo seed conceptual 20260312.",
            "Comparar KPIs y status de triangulación cuando haya créditos.",
            "Tóxico es overlay VPIN, no 4º estado HMM.",
            "HMM forward + histéresis; features causales.",
        ],
    }
    path = Path("/home/workdir/artifacts/gate_recreate_report.json")
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nReporte: {path}")

    # CSV de sesión para inspección
    df_out = df.copy()
    df_out["regime"] = regime
    df_out["post_quiet"] = post[:, 0]
    df_out["post_normal"] = post[:, 1]
    df_out["post_volatil"] = post[:, 2]
    csv_path = Path("/home/workdir/artifacts/gate_recreate_session.csv")
    df_out.to_csv(csv_path, index=False)
    print(f"Sesión:  {csv_path}")


if __name__ == "__main__":
    main()
