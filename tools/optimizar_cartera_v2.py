#!/usr/bin/env python3
"""Paso 6: Optimizacion de Carteras OOS (Walk-Forward Expandido 2021-07 -> 2026-09) + Generacion Kernel Kaggle MC 20K.

Combina:
  - SERIES_EXPANDIDAS_DIARIAS.csv.gz & SERIES_EXPANDIDAS_MIN_INTRADIA.csv.gz (CME base + mejoras causales)
  - KAGGLE_M1_DAILY_DR.csv.gz & KAGGLE_M1_MIN_DR.csv.gz (15 activos x 6 mecanismos, SOLO DESC+REP A5!)
  - SERIES_CRIPTO_DESC_REP.csv.gz & SERIES_CRIPTO_MIN_DESC_REP.csv.gz (Binance Futures USDT-M, SOLO DESC+REP A5!)

Evalua 3 Universos x 7 Asignadores en Walk-Forward Expandido estricto (reajuste trimestral con t < Q):
  1. Actual_Base (pesos uniformes en base)
  2. Claude_Regla (greedy paso2 corr<=0.4 + 1/sd)
  3. Regla_V2_Clean (fix paso2 <=3 pairwise, sin F/C, w acotados [0.5, 2.0])
  4. HRP (Hierarchical Risk Parity con covarianza Ledoit-Wolf)
  5. ERC (Equal Risk Contribution / Paridad de Riesgo, pesos [0.04, 0.25])
  6. MaxDiv (Maximizacion de Ratio de Diversificacion w'sd / sqrt(w' Sigma w), pesos [0.03, 0.25])
  7. Discrete_Micro_Opt (cuantizacion entera 0..3 micros/unidad manteniendo ERC/HRP objetivo)

Genera ademas el paquete autoejecutable para Kaggle Kernel 2 (MC 20,000 trayectorias Numba Multi-Prop).
Uso:
  python -u tools/optimizar_cartera_v2.py
"""
from __future__ import annotations

import base64
import gzip
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
try:
    from scipy.cluster.hierarchy import leaves_list, linkage
    from scipy.optimize import minimize
    from scipy.spatial.distance import squareform
    from sklearn.covariance import LedoitWolf
except ImportError:
    leaves_list = linkage = minimize = squareform = LedoitWolf = None

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))

from edgelab.holdout import a5_bloque
from audit_regla_cartera import INTRA8, INTER3, regla_param, stats_serie

OUT = ROOT / "docs/research/auditoria_cartera_20261126"
MC_DIR = OUT / "kaggle_mc20k"
MC_DIR.mkdir(parents=True, exist_ok=True)
CUTOFF_STR = "2026-09-29"


def _lw_cov(X: pd.DataFrame) -> np.ndarray:
    arr = X.fillna(0.0).to_numpy(float)
    if len(arr) < 15 or arr.shape[1] < 2:
        return np.eye(arr.shape[1])
    lw = LedoitWolf().fit(arr)
    cov = lw.covariance_.copy()
    # Ensure PD
    vals, vecs = np.linalg.eigh(cov)
    vals = np.maximum(vals, 1e-6 * np.mean(np.maximum(vals, 1e-6)))
    return vecs @ np.diag(vals) @ vecs.T


def weights_hrp(X: pd.DataFrame) -> np.ndarray:
    cov = _lw_cov(X)
    sd = np.sqrt(np.clip(np.diag(cov), 1e-8, None))
    corr = cov / np.outer(sd, sd)
    np.fill_diagonal(corr, 1.0)
    dist = np.sqrt(np.clip(0.5 * (1.0 - corr), 0.0, 1.0))
    np.fill_diagonal(dist, 0.0)
    order = leaves_list(linkage(squareform(dist, checks=False), "single"))
    w = np.ones(len(sd))
    clusters = [list(order)]
    while clusters:
        c = clusters.pop()
        if len(c) <= 1:
            continue
        a, b = c[: len(c) // 2], c[len(c) // 2 :]
        def v_c(ix):
            cc = cov[np.ix_(ix, ix)]
            iv = 1.0 / np.clip(np.diag(cc), 1e-8, None)
            iv /= iv.sum()
            return float(iv @ cc @ iv)
        va, vb = v_c(a), v_c(b)
        al = 1.0 - va / (va + vb) if (va + vb) > 0 else 0.5
        w[a] *= al
        w[b] *= 1.0 - al
        clusters += [a, b]
    return w / w.sum()


def weights_erc(X: pd.DataFrame, lo: float = 0.03, hi: float = 0.28) -> np.ndarray:
    cov = _lw_cov(X)
    n = cov.shape[0]
    lo_eff = min(lo, 0.8 / n)
    hi_eff = max(hi, 1.5 / n)
    x0 = np.ones(n) / n

    def obj(w):
        pvar = float(w @ cov @ w)
        if pvar <= 1e-12:
            return 1e6
        mrc = cov @ w
        rc = w * mrc
        tgt = pvar / n
        return float(np.sum((rc - tgt) ** 2)) / (pvar ** 2)

    res = minimize(
        obj, x0, method="SLSQP",
        bounds=[(lo_eff, hi_eff)] * n,
        constraints=[{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}],
        options={"maxiter": 300, "ftol": 1e-10},
    )
    w = np.clip(res.x if res.success else x0, lo_eff, hi_eff)
    return w / w.sum()


def weights_maxdiv(X: pd.DataFrame, lo: float = 0.02, hi: float = 0.28) -> np.ndarray:
    cov = _lw_cov(X)
    sd = np.sqrt(np.clip(np.diag(cov), 1e-8, None))
    n = len(sd)
    lo_eff = min(lo, 0.8 / n)
    hi_eff = max(hi, 1.5 / n)
    x0 = np.ones(n) / n

    def obj(w):
        vol = float(np.sqrt(max(1e-12, w @ cov @ w)))
        return -float((w @ sd) / vol)

    res = minimize(
        obj, x0, method="SLSQP",
        bounds=[(lo_eff, hi_eff)] * n,
        constraints=[{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}],
        options={"maxiter": 300, "ftol": 1e-10},
    )
    w = np.clip(res.x if res.success else x0, lo_eff, hi_eff)
    return w / w.sum()


def discrete_micro_opt(X: pd.DataFrame, w_cont: np.ndarray, total_micros: int | None = None) -> np.ndarray:
    """Convierte pesos continuos (ERC/HRP sobre dolares diarios) a contratos enteros 0..3 micros por estrategia.
    Usa greedy coordinate ascent sobre Diversification Ratio / tracking error de contribucion de riesgo.
    """
    n = len(w_cont)
    if total_micros is None:
        total_micros = n  # misma escala agregada que 1 micro x estrategia
    cov = _lw_cov(X)
    sd = np.sqrt(np.clip(np.diag(cov), 1e-8, None))
    # Initial integer allocation proportional to w_cont
    m = np.clip(np.round(w_cont * total_micros).astype(int), 0, 3)
    # Greedy repair to match target budget while maximizing Sharpe-proxy / DR penalty for single-asset concentration
    while m.sum() > total_micros:
        idx_pos = np.where(m > 0)[0]
        best_j, best_val = idx_pos[0], -1e9
        for j in idx_pos:
            cand = m.copy(); cand[j] -= 1
            if cand.sum() == 0: continue
            vol = float(np.sqrt(max(1e-12, cand @ cov @ cand)))
            dr = float((cand @ sd) / vol)
            if dr > best_val:
                best_val, best_j = dr, j
        m[best_j] -= 1
    while m.sum() < total_micros:
        idx_add = np.where(m < 3)[0]
        if len(idx_add) == 0:
            break
        best_j, best_val = idx_add[0], -1e9
        for j in idx_add:
            cand = m.copy(); cand[j] += 1
            vol = float(np.sqrt(max(1e-12, cand @ cov @ cand)))
            dr = float((cand @ sd) / vol)
            if dr > best_val:
                best_val, best_j = dr, j
        m[best_j] += 1
    return m.astype(float)


def portfolio_extra_metrics(daily: pd.Series, min_s: pd.Series, X: pd.DataFrame, W_mat: np.ndarray) -> dict:
    st = stats_serie(daily, min_s)
    # Average N_eff and Diversification Ratio over OOS window
    cov = _lw_cov(X.loc[daily.index])
    sd = np.sqrt(np.clip(np.diag(cov), 1e-8, None))
    w_mean = np.mean(np.abs(W_mat), axis=0)
    w_norm = w_mean / np.sum(w_mean) if np.sum(w_mean) > 0 else np.ones(len(w_mean)) / len(w_mean)
    n_eff = float(1.0 / np.sum(w_norm ** 2))
    pvol = float(np.sqrt(max(1e-12, w_norm @ cov @ w_norm)))
    div_ratio = float((w_norm @ sd) / pvol)
    st26 = float(daily[(daily.index >= "2026-05-01") & (daily.index <= "2026-09-30")].sum())
    st.update({"n_eff": round(n_eff, 2), "div_ratio": round(div_ratio, 3), "tramo_may_sep_2026": round(st26, 1)})
    return st


def walk_forward_7_methods(
    X: pd.DataFrame,
    Xmin: pd.DataFrame,
    base_cols: List[str],
    claude_pool: List[str],
    clean_pool: List[str],
    wf_start: str = "2021-07-01",
    mask_dates: pd.Series | None = None,
) -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    """Ejecuta Walk-Forward Expandido trimestral estricto (t < Q) comparando los 7 asignadores."""
    cols = list(dict.fromkeys(base_cols + claude_pool + clean_pool))
    X = X[cols].fillna(0.0)
    Xmin = Xmin[cols].fillna(0.0)
    oos_mask = X.index >= wf_start
    if mask_dates is not None:
        oos_mask = oos_mask & mask_dates.reindex(X.index, fill_value=False).to_numpy()
    quarters = pd.date_range(wf_start, CUTOFF_STR, freq="QS")

    methods = ["Actual_Base", "Claude_Regla", "Regla_V2_Clean", "HRP", "ERC", "MaxDiv", "Discrete_Micro_Opt"]
    W = {m: np.zeros((len(X), len(cols))) for m in methods}
    col_idx = {c: i for i, c in enumerate(cols)}
    base_w = np.array([1.0 if c in base_cols else 0.0 for c in cols])

    last_w = {}
    for q in quarters:
        hist = X[X.index < q]
        q_end = q + pd.DateOffset(months=3)
        sel_rows = (X.index >= q) & (X.index < q_end)
        if mask_dates is not None:
            hist = hist[mask_dates.reindex(hist.index, fill_value=False).to_numpy()]

        # 1) Actual_Base: 1 micro each in base_cols
        W["Actual_Base"][sel_rows] = base_w

        if len(hist) < 200:
            for m in methods[1:]:
                W[m][sel_rows] = base_w
            continue

        # Scale all continuous allocators to match average base monthly notional risk (~sum(sd_pool) -> scaled to base sum at end)
        # 2) Claude_Regla (on claude_pool)
        try:
            sel_cl, w_cl, _ = regla_param(hist[claude_pool], fix_step2=False, w_clip=None)
            vec_cl = np.zeros(len(cols))
            for k, v in w_cl.items():
                vec_cl[col_idx[k]] = v
            W["Claude_Regla"][sel_rows] = vec_cl
        except Exception:
            W["Claude_Regla"][sel_rows] = base_w

        # 3) Regla_V2_Clean (on clean_pool, fix_step2=True, bounded [0.5, 2.0])
        try:
            sel_v2, w_v2, _ = regla_param(hist[clean_pool], fix_step2=True, w_clip=(0.5, 2.0))
            vec_v2 = np.zeros(len(cols))
            for k, v in w_v2.items():
                vec_v2[col_idx[k]] = v
            W["Regla_V2_Clean"][sel_rows] = vec_v2
        except Exception:
            W["Regla_V2_Clean"][sel_rows] = base_w

        # Active clean pool filtered gently on history (mean > 0) for risk-based allocators so pure dead series don't get forced min weight
        hist_clean = hist[clean_pool]
        # Keep strategies with positive expanding mean in history (or top half if <4)
        means = hist_clean.mean()
        act_cols = [c for c in clean_pool if means[c] > 0]
        if len(act_cols) < 4:
            act_cols = list(means.sort_values(ascending=False).index[: max(4, len(clean_pool) // 2)])

        # Normalize dollar weights to 1/sd * N scaling so portfolio notional is comparable to 1-micro-per-strategy scale
        sub_h = hist_clean[act_cols]
        sd_h = sub_h.std(ddof=1).replace(0.0, np.nan).fillna(1.0).to_numpy()
        ref_scale = float(np.mean(sd_h))

        def _place(w_prob: np.ndarray) -> np.ndarray:
            # Convert risk/dollar weights into micro multipliers matching base scale
            vec = np.zeros(len(cols))
            # w_prob sum=1 over act_cols; scale by len(base_cols) * (ref_scale / sd_h) capped at [0.25, 2.5]
            raw_mult = w_prob * len(act_cols) * (ref_scale / sd_h)
            raw_mult = np.clip(raw_mult, 0.2, 2.5)
            for c, val in zip(act_cols, raw_mult):
                vec[col_idx[c]] = val
            return vec

        w_hrp_p = weights_hrp(sub_h)
        w_erc_p = weights_erc(sub_h)
        w_md_p = weights_maxdiv(sub_h)

        W["HRP"][sel_rows] = _place(w_hrp_p)
        W["ERC"][sel_rows] = _place(w_erc_p)
        W["MaxDiv"][sel_rows] = _place(w_md_p)

        # Discrete_Micro_Opt: integer micros matching base count budget
        m_int = discrete_micro_opt(sub_h, w_erc_p, total_micros=max(len(base_cols), len(act_cols)))
        vec_disc = np.zeros(len(cols))
        for c, val in zip(act_cols, m_int):
            vec_disc[col_idx[c]] = val
        W["Discrete_Micro_Opt"][sel_rows] = vec_disc

        last_w = {
            "Claude_Regla": {c: round(float(W["Claude_Regla"][sel_rows][0, col_idx[c]]), 3) for c in cols if W["Claude_Regla"][sel_rows][0, col_idx[c]] > 0},
            "Regla_V2_Clean": {c: round(float(W["Regla_V2_Clean"][sel_rows][0, col_idx[c]]), 3) for c in cols if W["Regla_V2_Clean"][sel_rows][0, col_idx[c]] > 0},
            "HRP": {c: round(float(W["HRP"][sel_rows][0, col_idx[c]]), 3) for c in cols if W["HRP"][sel_rows][0, col_idx[c]] > 0},
            "ERC": {c: round(float(W["ERC"][sel_rows][0, col_idx[c]]), 3) for c in cols if W["ERC"][sel_rows][0, col_idx[c]] > 0},
            "MaxDiv": {c: round(float(W["MaxDiv"][sel_rows][0, col_idx[c]]), 3) for c in cols if W["MaxDiv"][sel_rows][0, col_idx[c]] > 0},
            "Discrete_Micro_Opt": {c: int(W["Discrete_Micro_Opt"][sel_rows][0, col_idx[c]]) for c in cols if W["Discrete_Micro_Opt"][sel_rows][0, col_idx[c]] > 0},
        }

    X_arr = X.to_numpy()
    Xm_arr = np.minimum(Xmin.to_numpy(), np.minimum(X_arr, 0.0))
    oos_d = pd.DataFrame(index=X.index[oos_mask])
    oos_m = pd.DataFrame(index=X.index[oos_mask])

    summary = {"last_quarter_weights": last_w, "raw_oos": {}, "vol_matched_to_actual": {}}
    base_sd_m = None
    for m in methods:
        d_s = pd.Series((X_arr * W[m]).sum(axis=1), index=X.index)[oos_mask]
        m_s = pd.Series((Xm_arr * W[m]).sum(axis=1), index=X.index)[oos_mask]
        oos_d[m] = d_s
        oos_m[m] = m_s
        met = portfolio_extra_metrics(d_s, m_s, X, W[m][oos_mask])
        met["avg_gross_units"] = round(float(W[m][oos_mask].sum(axis=1).mean()), 2)
        summary["raw_oos"][m] = met
        if m == "Actual_Base":
            base_sd_m = met["sd_mes"]

    for m in methods:
        sc = base_sd_m / summary["raw_oos"][m]["sd_mes"] if summary["raw_oos"][m]["sd_mes"] > 0 else 1.0
        vm = stats_serie(oos_d[m] * sc, oos_m[m] * sc)
        vm["scale"] = round(sc, 3)
        vm["tramo_may_sep_2026"] = round(float(oos_d[m][(oos_d.index >= "2026-05-01") & (oos_d.index <= "2026-09-30")].sum() * sc), 1)
        summary["vol_matched_to_actual"][m] = vm

    return summary, oos_d, oos_m


def generate_kaggle_mc20k_kernel(payload_dict: Dict[str, tuple[pd.Series, pd.Series, float]]) -> None:
    """Genera script autoejecutable para Kaggle con 20,000 trayectorias Numba Multi-Prop + Broker."""
    # Pack series compactly as base64 gzipped JSON
    packed = {}
    for key, (d_s, m_s, nsum) in payload_dict.items():
        packed[key] = {
            "y": np.round(d_s.to_numpy(float), 2).tolist(),
            "ymin": np.round(np.minimum(m_s.to_numpy(float), np.minimum(d_s.to_numpy(float), 0.0)), 2).tolist(),
            "nsum": round(float(nsum), 2),
        }
    b64 = base64.b64encode(gzip.compress(json.dumps(packed).encode("utf-8"))).decode("ascii")

    script = f'''#!/usr/bin/env python3
"""Kaggle Kernel 2: Monte Carlo 20,000 trayectorias (bloques de 10 sesiones) Multi-Prop + Broker Multi-Frente."""
import base64, gzip, json, os, time
from pathlib import Path
import numpy as np
from numba import njit

PAYLOAD_B64 = "{b64}"
DATA = json.loads(gzip.decompress(base64.b64decode(PAYLOAD_B64)).decode("utf-8"))
N_PATHS = 20000


@njit
def sim_lucid_or_tradeify(y, ymin, nsum, precio, obj, mll, lock, dll, cap, dmin, tope, cons, mean_mult, dyn_mode, n_paths, seed):
    # dyn_mode: 0=Fixed, 1=GrossmanZhou, 2=LockStep(1.25x after lock)
    if nsum > tope:
        return 0.0, 0.0, -precio, 0.0, 1.0, 0.0, 0.0
    L = len(y)
    mu = np.mean(y)
    sh = (mean_mult - 1.0) * mu
    pasa = 0
    quiebra = 0
    cob_sum = 0.0
    pago_tot = 0.0
    dias_sum = 0.0
    wins = 0

    for k in range(n_paths):
        # LCG pseudo-random deterministic per path for numba speed
        s = (seed + k * 2654435761) & 0xFFFFFFFF
        eq = 0.0
        peak = 0.0
        piso = -mll
        locked = False
        best_day = 0.0
        paso = 0
        ok = True
        dias = 0
        tot_ret = 0.0
        cob_n = 0
        c_buenos = 0
        bal_ret = 0.0

        s = (1664525 * s + 1013904223) & 0xFFFFFFFF
        pos = int(s % L)
        rem = 0

        for step in range(500):
            if rem == 0:
                s = (1664525 * s + 1013904223) & 0xFFFFFFFF
                pos = int(s % L)
                rem = 10
            idx = (pos + (10 - rem)) % L
            rem -= 1

            mult = 1.0
            if paso == 1:
                if dyn_mode == 1:
                    cushion = eq - piso
                    mult = max(0.35, min(1.5, cushion / mll))
                elif dyn_mode == 2 and locked:
                    mult = 1.25

            dy = (y[idx] + sh) * mult
            dm = min((ymin[idx] + sh) * mult, min(dy, 0.0))

            if paso == 0:
                if dm < -dll and dll < 1e8:
                    dy = -dll
                if eq + dm <= piso:
                    ok = False
                    quiebra += 1
                    break
                eq += dy
                if eq > peak: peak = eq
                piso = max(piso, peak - mll)
                if dy > best_day: best_day = dy
                dias += 1
                if eq >= obj and best_day <= cons * eq + 1e-6:
                    paso = 1
                    eq = 0.0; peak = 0.0; piso = -mll; locked = False
            else:
                if dm < -dll and dll < 1e8:
                    dy = -dll
                if eq + dm <= piso:
                    ok = False
                    break
                eq += dy
                bal_ret += dy
                if dy >= dmin:
                    c_buenos += 1
                if not locked:
                    if eq > peak: peak = eq
                    piso = max(piso, min(100.0, peak - mll))
                    if eq >= lock:
                        locked = True
                        piso = max(piso, 100.0)
                if c_buenos >= 5 and bal_ret >= 500.0:
                    pay = min(cap, max(0.0, eq - max(piso, 0.0) - 500.0))
                    if pay >= 250.0:
                        tot_ret += pay
                        eq -= pay
                        bal_ret = 0.0
                        c_buenos = 0
                        cob_n += 1
                        if cob_n >= 4:
                            break
        if paso == 1:
            pasa += 1
            dias_sum += dias
        if cob_n > 0:
            cob_sum += 1.0
        pago_tot += tot_ret
        if tot_ret - precio > 0:
            wins += 1

    ev = pago_tot / n_paths - precio
    return pasa / n_paths, cob_sum / n_paths, ev, wins / n_paths, quiebra / n_paths, pago_tot / n_paths, dias_sum / max(1, pasa)


@njit
def sim_ftmo_100k(y, ymin, scale_w, mean_mult, n_paths, seed):
    # FTMO 100K: Fee ~$580 (refunded on 1st payout), Phase 1 +10k, Phase 2 +5k, DLL -5k intraday, MaxLoss -10k fixed initial!
    L = len(y)
    mu = np.mean(y)
    sh = (mean_mult - 1.0) * mu
    p1_pass = 0
    p2_pass = 0
    pay_tot = 0.0
    wins = 0
    fee = 580.0

    for k in range(n_paths):
        s = (seed + k * 2654435761) & 0xFFFFFFFF
        s = (1664525 * s + 1013904223) & 0xFFFFFFFF
        pos = int(s % L)
        rem = 0
        phase = 1
        eq = 0.0
        days_in_phase = 0
        ok = True
        tot_ret = 0.0
        payouts = 0

        for step in range(550):
            if rem == 0:
                s = (1664525 * s + 1013904223) & 0xFFFFFFFF
                pos = int(s % L)
                rem = 10
            idx = (pos + (10 - rem)) % L
            rem -= 1
            dy = (y[idx] + sh) * scale_w
            dm = min((ymin[idx] + sh) * scale_w, min(dy, 0.0))

            if dm <= -5000.0 or eq + dm <= -10000.0:
                ok = False
                break
            eq += dy
            days_in_phase += 1
            if phase == 1 and eq >= 10000.0 and days_in_phase >= 4:
                p1_pass += 1
                phase = 2
                eq = 0.0
                days_in_phase = 0
            elif phase == 2 and eq >= 5000.0 and days_in_phase >= 4:
                p2_pass += 1
                phase = 3
                eq = 0.0
                days_in_phase = 0
            elif phase == 3 and days_in_phase >= 14:
                if eq > 1000.0:
                    # 80% split + refund on 1st payout
                    tot_ret += 0.80 * eq + (fee if payouts == 0 else 0.0)
                    eq = 0.0
                    payouts += 1
                days_in_phase = 0
                if payouts >= 4:
                    break
        pay_tot += tot_ret
        if tot_ret - fee > 0:
            wins += 1

    ev = pay_tot / n_paths - fee
    return p1_pass / n_paths, p2_pass / n_paths, ev, wins / n_paths, pay_tot / n_paths


@njit
def sim_broker_tails(y, ymin, mean_mult, n_paths, seed):
    # 252 trading days (1 year) bootstrap -> distribution of annual return and max intraday DD
    L = len(y)
    mu = np.mean(y)
    sh = (mean_mult - 1.0) * mu
    rets = np.zeros(n_paths)
    dds = np.zeros(n_paths)
    for k in range(n_paths):
        s = (seed + k * 2654435761) & 0xFFFFFFFF
        eq = 0.0
        pk = 0.0
        mdd = 0.0
        pos = 0
        rem = 0
        for step in range(252):
            if rem == 0:
                s = (1664525 * s + 1013904223) & 0xFFFFFFFF
                pos = int(s % L)
                rem = 10
            idx = (pos + (10 - rem)) % L
            rem -= 1
            dy = y[idx] + sh
            dm = min(ymin[idx] + sh, min(dy, 0.0))
            if eq + dm - pk < mdd:
                mdd = eq + dm - pk
            eq += dy
            if eq > pk:
                pk = eq
        rets[k] = eq
        dds[k] = mdd
    return rets, dds


def main():
    t0 = time.time()
    out = {{"n_paths": N_PATHS, "lucid_150k": {{}}, "lucid_50k": {{}}, "tradeify_150k": {{}}, "ftmo_100k": {{}}, "broker_1yr_tails": {{}}}}

    for key, obj in DATA.items():
        y = np.asarray(obj["y"], dtype=np.float64)
        ym = np.asarray(obj["ymin"], dtype=np.float64)
        ns = float(obj["nsum"])

        if key.startswith("INTRA_") or key.startswith("MIXTO_"):
            for mm in (0.5, 1.0):
                tag = f"m{{int(mm*100)}}"
                if key.startswith("INTRA_"):
                    for dmode, dname in ((0, "Fixed"), (1, "GrossmanZhou"), (2, "LockStep")):
                        p, c, ev, pw, q, ret, d = sim_lucid_or_tradeify(y, ym, ns, 214.25, 9000.0, 4500.0, 4600.0, 2700.0, 3000.0, 250.0, 100.0, 0.4, mm, dmode, N_PATHS, 2026)
                        out["lucid_150k"][f"{{key}}_{{dname}}_{{tag}}"] = {{"pasa": round(p,4), "cobra": round(c,4), "ev": round(ev,1), "p_ganar": round(pw,4), "quiebra_eval": round(q,4), "retiros": round(ret,1), "dias_pase": round(d,1)}}
                    p, c, ev, pw, q, ret, d = sim_lucid_or_tradeify(y, ym, ns, 95.2, 3000.0, 2000.0, 2100.0, 1200.0, 2000.0, 150.0, 40.0, 0.4, mm, 0, N_PATHS, 2027)
                    out["lucid_50k"][f"{{key}}_Fixed_{{tag}}"] = {{"pasa": round(p,4), "cobra": round(c,4), "ev": round(ev,1), "p_ganar": round(pw,4), "quiebra_eval": round(q,4), "retiros": round(ret,1), "dias_pase": round(d,1)}}
                    p, c, ev, pw, q, ret, d = sim_lucid_or_tradeify(y, ym, ns, 250.0, 9000.0, 4500.0, 4600.0, 1e9, 3000.0, 250.0, 100.0, 0.4, mm, 0, N_PATHS, 2028)
                    out["tradeify_150k"][f"{{key}}_Fixed_{{tag}}"] = {{"pasa": round(p,4), "cobra": round(c,4), "ev": round(ev,1), "p_ganar": round(pw,4), "quiebra_eval": round(q,4), "retiros": round(ret,1), "dias_pase": round(d,1)}}

                # FTMO 100K CFD normalized to ~$2,200/mo risk scale (so both continuous & discrete test fair sizing vs $5k DLL/$10k ML)
                sd_m = float(np.std(y) * np.sqrt(21.0)) if np.std(y) > 0 else 1.0
                sc_ftmo = 2200.0 / sd_m
                p1, p2, ev_f, pw_f, ret_f = sim_ftmo_100k(y, ym, sc_ftmo, mm, N_PATHS, 2029)
                out["ftmo_100k"][f"{{key}}_{{tag}}"] = {{"p1": round(p1,4), "p2": round(p2,4), "ev": round(ev_f,1), "p_ganar": round(pw_f,4), "retiros": round(ret_f,1), "scale_to_2200sd": round(sc_ftmo,3)}}

        rets, dds = sim_broker_tails(y, ym, 0.5, N_PATHS, 2030)
        out["broker_1yr_tails"][key] = {{
            "mean_1yr_m50": round(float(np.mean(rets)), 1),
            "p_yr_pos_m50": round(float(np.mean(rets > 0)), 4),
            "dd_p50": round(float(np.percentile(dds, 50)), 1),
            "dd_p95": round(float(np.percentile(dds, 5)), 1),
            "dd_p99": round(float(np.percentile(dds, 1)), 1),
        }}

    out_path = Path("/kaggle/working/KAGGLE_MC20K_RESUMEN.json") if os.path.isdir("/kaggle/working") else Path("KAGGLE_MC20K_RESUMEN.json")
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"DONE MC20K in {{time.time() - t0:.1f}}s -> {{out_path}}", flush=True)


if __name__ == "__main__":
    main()
'''
    (MC_DIR / "kaggle_mc20k.py").write_text(script, encoding="utf-8")
    meta = {
        "id": "nicolasbuttaro/edgelab-cartera-mc20k-20261126",
        "title": "EdgeLab Cartera MC20K MultiProp 20261126",
        "code_file": "kaggle_mc20k.py",
        "language": "python",
        "kernel_type": "script",
        "is_private": True,
        "enable_gpu": False,
        "enable_internet": False,
        "dataset_sources": [],
        "competition_sources": [],
        "kernel_sources": [],
        "model_sources": [],
    }
    (MC_DIR / "kernel-metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print("Generated Kaggle MC20K kernel:", MC_DIR / "kaggle_mc20k.py", f"({len(script)//1024} KB)")


def main() -> None:
    exp_d = pd.read_csv(OUT / "SERIES_EXPANDIDAS_DIARIAS.csv.gz", index_col=0, parse_dates=True)
    exp_m = pd.read_csv(OUT / "SERIES_EXPANDIDAS_MIN_INTRADIA.csv.gz", index_col=0, parse_dates=True)
    assert (exp_d.index <= CUTOFF_STR).all(), "Holdout leak in exp_d!"

    # Merge Kaggle M1 expansion surviving streams (DESC+REP only!) if present
    kg_json_p = OUT / "kaggle_m1_out/KAGGLE_M1_EXPANSION.json"
    kg_d_p = OUT / "kaggle_m1_out/KAGGLE_M1_DAILY_DR.csv.gz"
    kg_m_p = OUT / "kaggle_m1_out/KAGGLE_M1_MIN_DR.csv.gz"
    kg_alive: List[str] = []
    if kg_json_p.exists() and kg_d_p.exists():
        kg_meta = json.loads(kg_json_p.read_text(encoding="utf-8"))
        kg_d = pd.read_csv(kg_d_p, index_col=0, parse_dates=True).reindex(exp_d.index)
        kg_m = pd.read_csv(kg_m_p, index_col=0, parse_dates=True).reindex(exp_d.index)
        for col in kg_meta.get("alive_candidates", []):
            # Keep orthogonal non-US-index / non-duplicate strategies (exclude CME_NQ/CME_ES which duplicate EdgeLab NT8)
            if col.startswith(("CME_NQ_", "CME_ES_")):
                continue
            exp_d[f"KG_{col}"] = kg_d[col]
            exp_m[f"KG_{col}"] = kg_m[col]
            kg_alive.append(f"KG_{col}")
        print(f"Merged {len(kg_alive)} Kaggle surviving M1 streams (DESC+REP only):", kg_alive)

    # Fallback: add local M1DK surviving streams if Kaggle output wasn't downloaded
    if not kg_alive and (OUT / "EXPANSION_MULTIACTIVO.json").exists():
        loc_meta = json.loads((OUT / "EXPANSION_MULTIACTIVO.json").read_text(encoding="utf-8"))
        for col in loc_meta.get("alive_m1dk", []):
            if col in exp_d.columns:
                kg_alive.append(col)
        print(f"Using {len(kg_alive)} local M1DK alive streams:", kg_alive)

    # Merge Crypto DESC+REP
    cr_d = pd.read_csv(OUT / "SERIES_CRIPTO_DESC_REP.csv.gz", index_col=0, parse_dates=True)
    cr_m = pd.read_csv(OUT / "SERIES_CRIPTO_MIN_DESC_REP.csv.gz", index_col=0, parse_dates=True)
    # Map crypto 7-day calendar onto business-day index by summing weekend crypto days into Monday cleanly (preserving exact equity & monthly stats!)
    bidx = exp_d.index
    cr_mapped_d = pd.DataFrame(index=bidx)
    cr_mapped_m = pd.DataFrame(index=bidx)
    # Only fill on DESC+REP dates!
    ses_int = pd.Series([int(d.strftime("%Y%m%d")) for d in bidx], index=bidx)
    blq = ses_int.map(a5_bloque)
    mask_dr = blq.isin(["DESC", "REP"])

    # Assign each calendar date in cr_d to next valid date in bidx (Friday+Sat+Sun -> Monday if business day, strictly within A5 DESC+REP)
    cr_sub = cr_d.dropna(subset=["CR_HRP_PORT"])
    cr_m_sub = cr_m.reindex(cr_sub.index)
    # Reindex to union then group weekend days into next business day
    pos_b = np.searchsorted(bidx.to_numpy(), cr_sub.index.to_numpy(), side="left")
    valid_pos = pos_b < len(bidx)
    target_b = pd.Series(bidx[pos_b[valid_pos]], index=cr_sub.index[valid_pos])
    for c in ["CR_HRP_PORT", "CR_Donchian_1D", "CR_Trend_4H_EMA", "CR_XSMOM_Neutral"]:
        s_agg = cr_sub.iloc[valid_pos][c].groupby(target_b).sum().reindex(bidx)
        m_agg = cr_m_sub.iloc[valid_pos][c].groupby(target_b).min().reindex(bidx)
        exp_d[c] = np.where(mask_dr, s_agg.fillna(0.0), np.nan)
        exp_m[c] = np.where(mask_dr, m_agg.fillna(0.0), np.nan)

    # Scale Crypto HRP cleanly once on DESC+REP or causally? Scale in Super-Cartera cleanly inside WF!
    # Define Universes:
    claude_intra_pool = [c for c in exp_d.columns if c.startswith(("T_", "R_", "Z_", "V_", "RQ5_", "FR_", "ES5N_", "FS_")) and "ATR" not in c and "tp1400" not in c and not c.startswith("FS_O") and not c.endswith("_adapt")]
    # Better: use the exact candidate pool Claude evaluated in regla_cartera.py!
    claude_intra_exact = [c for c in ["T_NQ", "R_NQ", "Z_NQ", "V_NQ", "RQ5_NQ", "FR_NQ", "ES5N_NQ", "RQ5_ES", "ES5N_ES", "T_ES", "R_ES", "RQ5_YM", "FR_YM", "ES5N_YM", "RQ5_RTY", "FR_RTY", "ES5N_RTY", "RQ5_GC", "FR_GC", "ES5N_GC", "FS_A1_NQ", "FS_A20_NQ", "FS_C_NQ", "FS_E_NQ", "FS_F_NQ", "FS_N_NQ", "FS_P_NQ", "FS_Q_NQ", "FS_S_NQ", "FS_W_NQ"] if c in exp_d.columns]
    claude_mixto_exact = claude_intra_exact + [c for c in ["SOMSF_NQ", "C2VZ_NQ", "C2VZ_ES", "FS_O_NQ"] if c in exp_d.columns]

    # Clean Expanded Intraday Prop-Compatible Pool (NO F, NO C, NO overnight, includes causal ATR improvements + SOM_eod + T_ES_adapt!)
    clean_intra_pool = [c for c in [
        "T_NQ", "R_ATR50_NQ", "Z_ATR50_NQ", "V_nm30_tp1400_NQ", "RQ5_NQ", "FR_NQ", "ES5N_NQ",
        "W_eod_ATR25_NQ", "N_ATR25_NQ", "SOM_eod_NQ",
        "RQ5_ES", "ES5N_ES", "T_ES_adapt",
    ] if c in exp_d.columns]
    clean_mixto_pool = clean_intra_pool + [c for c in ["SOMSF_NQ", "C2VZ_NQ", "C2VZ_ES", "O_qty1_ATR50"] if c in exp_d.columns]

    print("\n=== UNIVERSO A: INTRADIA PROP-COMPATIBLE (WF 2021-07 -> 2026-09) ===")
    res_intra, intra_d, intra_m = walk_forward_7_methods(exp_d, exp_m, INTRA8, claude_intra_exact, clean_intra_pool, wf_start="2021-07-01")
    for m, v in res_intra["raw_oos"].items():
        vm = res_intra["vol_matched_to_actual"][m]
        print(f"  {m:18s} | Sh={v['sharpe']:5.2f} Sort={v['sortino']:5.2f} CalEOD={v['calmar_eod']:4.2f} CalInt={v['calmar_intra']:4.2f} | Neff={v['n_eff']:4.1f} DR={v['div_ratio']:4.2f} | DD_i={v['caida_max_intra']:7.0f} | VM_DDi={vm['caida_max_intra']:7.0f} VM_Tr26={vm['tramo_may_sep_2026']:+6.0f}")

    print("\n=== UNIVERSO B: MIXTO CME (Con Overnight verificado, WF 2021-07 -> 2026-09) ===")
    res_mixto, mixto_d, mixto_m = walk_forward_7_methods(exp_d, exp_m, INTRA8 + INTER3, claude_mixto_exact, clean_mixto_pool, wf_start="2021-07-01")
    for m, v in res_mixto["raw_oos"].items():
        vm = res_mixto["vol_matched_to_actual"][m]
        print(f"  {m:18s} | Sh={v['sharpe']:5.2f} Sort={v['sortino']:5.2f} CalEOD={v['calmar_eod']:4.2f} CalInt={v['calmar_intra']:4.2f} | Neff={v['n_eff']:4.1f} DR={v['div_ratio']:4.2f} | DD_i={v['caida_max_intra']:7.0f} | VM_DDi={vm['caida_max_intra']:7.0f} VM_Tr26={vm['tramo_may_sep_2026']:+6.0f}")

    print("\n=== UNIVERSO C: MULTI-FRENTE (CME + Ortogonales M1/Kaggle + Cripto Binance, SOLO A5 DESC+REP 2021-07 -> 2026-09) ===")
    # Select top orthogonal non-CME-US-equity additions up to 6 so optimization is clean and non-singular
    ortho_intraday_or_global = [c for c in kg_alive if "_DON" in c or "_ORB" in c or "_OVN" in c or "_FADE" in c or "_VOLBRK" in c or "_PRECLOSE" in c]
    # Keep only diverse top candidates (at most 12 best Sharpe on DESC+REP)
    if len(ortho_intraday_or_global) > 12:
        sc_dr = {}
        for c in ortho_intraday_or_global:
            st = stats_serie(exp_d.loc[mask_dr, c])
            sc_dr[c] = st["sharpe"]
        ortho_intraday_or_global = sorted(ortho_intraday_or_global, key=lambda c: -sc_dr[c])[:12]

    multi_pool = clean_mixto_pool + ortho_intraday_or_global + ["CR_Donchian_1D", "CR_Trend_4H_EMA", "CR_XSMOM_Neutral"]
    multi_pool = [c for c in multi_pool if c in exp_d.columns]
    res_multi, multi_d, multi_m = walk_forward_7_methods(
        exp_d, exp_m, INTRA8 + INTER3, claude_mixto_exact, multi_pool, wf_start="2021-07-01", mask_dates=mask_dr
    )
    for m, v in res_multi["raw_oos"].items():
        vm = res_multi["vol_matched_to_actual"][m]
        print(f"  {m:18s} | Sh={v['sharpe']:5.2f} Sort={v['sortino']:5.2f} CalEOD={v['calmar_eod']:4.2f} CalInt={v['calmar_intra']:4.2f} | Neff={v['n_eff']:4.1f} DR={v['div_ratio']:4.2f} | DD_i={v['caida_max_intra']:7.0f} | VM_DDi={vm['caida_max_intra']:7.0f}")

    # Save OOS portfolio daily & min series
    intra_d.to_csv(OUT / "OOS_INTRADIA_7M.csv.gz")
    mixto_d.to_csv(OUT / "OOS_MIXTO_7M.csv.gz")
    multi_d.to_csv(OUT / "OOS_MULTIFRENTE_7M.csv.gz")

    # Prepare Kaggle Kernel 2 (20,000-path Numba Monte Carlo across Lucid 150K, Lucid 50K, Tradeify 150K, FTMO 100K, Broker)
    mc_payload = {}
    for m in ("Actual_Base", "Claude_Regla", "Regla_V2_Clean", "HRP", "ERC", "MaxDiv", "Discrete_Micro_Opt"):
        mc_payload[f"INTRA_{m}"] = (intra_d[m], intra_m[m], res_intra["raw_oos"][m]["avg_gross_units"])
        mc_payload[f"MIXTO_{m}"] = (mixto_d[m], mixto_m[m], res_mixto["raw_oos"][m]["avg_gross_units"])
    for m in ("Actual_Base", "HRP", "ERC", "MaxDiv"):
        mc_payload[f"MULTI_{m}"] = (multi_d[m], multi_m[m], res_multi["raw_oos"][m]["avg_gross_units"])
    generate_kaggle_mc20k_kernel(mc_payload)

    summary = {
        "kg_alive_used": ortho_intraday_or_global,
        "universo_A_intradia": res_intra,
        "universo_B_mixto": res_mixto,
        "universo_C_multifrente_DESC_REP": res_multi,
    }
    (OUT / "OPTIMIZACION_CARTERAS.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False, default=float), encoding="utf-8")
    print("\nSaved:", OUT / "OPTIMIZACION_CARTERAS.json")


if __name__ == "__main__":
    main()
