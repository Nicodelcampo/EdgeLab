#!/usr/bin/env python3
"""Auditoria forense completa de REGLA-CARTERA / ESTABILIDAD-CARTERA / FS-NFCO-A5 / EdgeLabCartera (Claude 709ef588).

Verifica y cuantifica:
1. Cobertura real de motores NT8 C# (EdgeLabFundedSyncCore.cs, EdgeLabCarteraEngines.cs, EdgeLabCartera.cs).
2. Bug #1: artefacto de orden en regla_cartera.py (len(sel)==1 usa corr_port<=0.4 y expulsa a R_NQ).
3. Bug #2: FS_O_NQ muerta desde 2025-10-13 (~11.5 meses de ceros) vs O_qty1_NQ real (y variante noWed / con swap CFD).
4. Bug #3: FS_F_NQ y FS_C_NQ entraron pese a fallar A5 (FS-NFCO-A5), y 1/sd premio con 2x a F por colapso de n_ops.
5. Bug #4: Un solo corte (2023-06) vs Walk-Forward Expandido 2021-07->2026-09 y todos los cortes alternativos + bloques A5.
6. Bug #5: Comparacion a igual volatilidad (vol-matched) y Drawdown Intradia real + Monte Carlo LucidFlex 150K/50K.

Uso:
  python tools/audit_regla_cartera.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))

from edgelab import costos
from edgelab.holdout import HOLDOUT_APERTURA_UTC_NS, a5_bloque
from edgelab.research.fundedsyncstack import build_multi_series, load_m1_data, run_o

OUT = ROOT / "docs/research/auditoria_cartera_20261126"
OUT.mkdir(parents=True, exist_ok=True)

NOCHE = ("SOMSF", "C2VZ", "C2EVRP", "FS_O", "O_qty1")
INTRA8 = ["T_NQ", "R_NQ", "Z_NQ", "V_NQ", "RQ5_NQ", "FR_NQ", "RQ5_ES", "ES5N_ES"]
INTER3 = ["SOMSF_NQ", "C2VZ_NQ", "C2VZ_ES"]

MICRO_PV = {"NQ": 2.0, "ES": 5.0, "YM": 0.5, "RTY": 5.0, "GC": 10.0}
MICRO_SYM = {"NQ": "MNQ", "ES": "MES", "YM": "MYM", "GC": "MGC"}


def audit_nt8_engines() -> dict:
    core = (ROOT / "nt8/strategies/EdgeLabFundedSyncCore.cs").read_text(encoding="utf-8", errors="ignore")
    eng = (ROOT / "nt8/strategies/EdgeLabCarteraEngines.cs").read_text(encoding="utf-8", errors="ignore")
    cart = (ROOT / "nt8/strategies/EdgeLabCartera.cs").read_text(encoding="utf-8", errors="ignore")

    core_classes = re.findall(r"class\s+(\w+)\s*:\s*ModuleEngineBase", core)
    eng_classes = re.findall(r"class\s+(\w+)\s*:\s*ModuleEngineBase", eng)
    preset_lines = re.findall(r"case\s+CarteraPreset\.\w+\s*:\s*return\s+\"([^\"]+)\"", cart)
    fs_codes = re.findall(r'\{\s*"(\w+)"\s*,\s*"([^"]+)"\s*\}', cart)
    return {
        "EdgeLabFundedSyncCore_engines": core_classes,
        "EdgeLabCarteraEngines_engines": eng_classes,
        "EdgeLabCartera_FsIds_mapping": dict(fs_codes),
        "EdgeLabCartera_presets": preset_lines,
        "missing_in_NT8_for_REGLA_CARTERA": ["FS_F_NQ (FabioOrb)", "FS_C_NQ (CapstoneGap)", "FS_O_NQ (Overnight)"],
        "present_in_Core_cs_not_in_default_presets": ["N (NDayLong)", "W (VwapCross)", "SOMEOD"],
    }


def _mes(x: pd.Series) -> pd.Series:
    return x.groupby(x.index.to_period("M")).sum()


def stats_serie(x: pd.Series, xmin: pd.Series | None = None) -> dict:
    x = x.dropna()
    m = _mes(x)
    eq = x.cumsum()
    a = x.groupby(x.index.year).sum()
    dd_eod = eq - eq.cummax()
    dd_intra_min = float(dd_eod.min())
    worst_day_intra = float(x.min())
    if xmin is not None:
        xm = xmin.reindex(x.index).fillna(0.0)
        xm = np.minimum(xm, np.minimum(x, 0.0))
        eq_prev = eq.shift(1, fill_value=0.0)
        peak_prev = eq.cummax().shift(1, fill_value=0.0)
        intra_eq = eq_prev + xm
        dd_intra_min = float(min((intra_eq - peak_prev).min(), dd_eod.min()))
        worst_day_intra = float(xm.min())
    sd_m = float(m.std(ddof=1)) if len(m) > 1 else 0.0
    sd_d = float(x.std(ddof=1)) if len(x) > 1 else 0.0
    mu_m = float(m.mean()) if len(m) else 0.0
    t_m = float(mu_m / (sd_m / np.sqrt(len(m)))) if sd_m > 0 and len(m) > 1 else 0.0
    sh = float(mu_m / sd_m * np.sqrt(12)) if sd_m > 0 else 0.0
    downside = m[m < 0]
    sortino = float(mu_m / downside.std(ddof=1) * np.sqrt(12)) if len(downside) > 1 and downside.std(ddof=1) > 0 else sh
    calmar_eod = float((mu_m * 12.0) / abs(dd_eod.min())) if dd_eod.min() < 0 else 0.0
    calmar_intra = float((mu_m * 12.0) / abs(dd_intra_min)) if dd_intra_min < 0 else 0.0
    return {
        "usd_mes": mu_m,
        "sd_mes": sd_m,
        "sd_dia": sd_d,
        "t_mes": t_m,
        "sharpe": sh,
        "sortino": sortino,
        "calmar_eod": calmar_eod,
        "calmar_intra": calmar_intra,
        "pct_meses_pos": float((m > 0).mean()) if len(m) else 0.0,
        "pct_anios_pos": float((a > 0).mean()) if len(a) else 0.0,
        "caida_max_eod": float(dd_eod.min()),
        "caida_max_intra": dd_intra_min,
        "peor_dia_eod": float(x.min()),
        "peor_dia_intra": worst_day_intra,
        "peor_mes": float(m.min()) if len(m) else 0.0,
        "meses": int(len(m)),
    }


def regla_param(
    X: pd.DataFrame,
    *,
    fix_step2: bool = False,
    excluded: Tuple[str, ...] = (),
    w_clip: Tuple[float, float] | None = None,
    cp_thr: float = 0.40,
    cm_thr: float = 0.60,
    t_thr: float = 1.50,
    yr_thr: float = 0.60,
) -> Tuple[List[str], Dict[str, float], List[dict]]:
    cols = [c for c in X.columns if c not in excluded]
    st = {c: stats_serie(X[c]) for c in cols}
    eleg = sorted(
        [c for c in cols if st[c]["t_mes"] >= t_thr and st[c]["pct_anios_pos"] >= yr_thr],
        key=lambda c: -st[c]["t_mes"],
    )
    M = _mes(X[cols])
    sel: List[str] = []
    trace: List[dict] = []
    for c in eleg:
        if not sel:
            sel.append(c)
            trace.append({"cand": c, "t": round(st[c]["t_mes"], 3), "cp": 0.0, "cm": 0.0, "kept": True, "reason": "seed"})
            continue
        cp = float(M[c].corr(M[sel].sum(axis=1)))
        cm = float(max(M[c].corr(M[s]) for s in sel))
        if fix_step2 and len(sel) < 3:
            keep = cm <= cm_thr
            reason = "ok_pairwise_small_n" if keep else f"cm={cm:.3f}>{cm_thr}"
        else:
            keep = (cp <= cp_thr) and (cm <= cm_thr)
            reason = "ok" if keep else (f"cp={cp:.3f}>{cp_thr}" if cp > cp_thr else f"cm={cm:.3f}>{cm_thr}")
        trace.append({"cand": c, "t": round(st[c]["t_mes"], 3), "n_before": len(sel), "cp": round(cp, 3), "cm": round(cm, 3), "kept": bool(keep), "reason": reason})
        if keep:
            sel.append(c)
    sd = M[sel].std(ddof=1).replace(0.0, np.nan)
    w = (1.0 / sd).fillna(1.0)
    w = w / w.mean()
    if w_clip is not None:
        w = w.clip(lower=w_clip[0], upper=w_clip[1])
        w = w / w.mean()
    return sel, w.to_dict(), trace


def compute_real_o_qty1_and_ymin(idx: pd.DatetimeIndex) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Corre O con qty=1 (sin tope de margen 25k) en NQ M1NT8 <= 2026-09-30 y construye minimos intradia."""
    cache_o = OUT / "cache_O_qty1_nq.pkl"
    if cache_o.exists():
        o_df = pd.read_pickle(cache_o)
    else:
        raw = pd.read_parquet(ROOT / "data/m1nt8/NQ_M1_nonadj_utc.parquet")
        df_m1 = load_m1_data(raw.reset_index(), start="2018-01-01", end="2026-10-01", tz_input="UTC", allow_sellado=False)
        ms_nq = build_multi_series(df_m1, tick_size=0.25, point_value=20.0, tz_input="UTC", allow_sellado=False)
        o_df = run_o(ms_nq, qty=1)
        o_df.to_pickle(cache_o)

    fr_mnq_pts = float(costos.friccion_rt_puntos("MNQ", "base"))  # 1.9775 pts
    pv_mnq = 2.0
    o_df = o_df.copy()
    ex_ny = pd.to_datetime(o_df["exit_time_utc"], unit="ns", utc=True).dt.tz_convert("America/New_York")
    en_ny = pd.to_datetime(o_df["entry_time_utc"], unit="ns", utc=True).dt.tz_convert("America/New_York")
    o_df["dia"] = ex_ny.dt.tz_localize(None).dt.normalize()
    o_df["entry_dow"] = en_ny.dt.dayofweek
    o_df["usd_1m"] = (o_df["pnl_pts"] - fr_mnq_pts) * pv_mnq
    o_df["mae_usd_1m"] = -(o_df["mae_usd"].abs() / 20.0) * pv_mnq  # mae_usd is positive in O? Wait: let's check sign!
    # Wait: in modulos_p_c_v_o.py line 219: mae_pts = max(0.0, pos.entry_price - min_low) -> mae_usd >= 0!
    # So intraday worst pnl = -abs(mae_usd)/10 - fr_mnq_pts*2
    o_df["min_1m"] = np.minimum(-(o_df["mae_usd"].abs() / 10.0) - fr_mnq_pts * pv_mnq, o_df["usd_1m"])

    # Also compute swap 8% annualized (triple Wednesday -> 3x on Wed entry)
    swap_annual = 0.08
    mult_days = np.where(o_df["entry_dow"] == 2, 3.0, 1.0)
    o_df["swap_usd_1m"] = o_df["entry_price"] * pv_mnq * (swap_annual / 365.0) * mult_days
    o_df["usd_1m_swap8"] = o_df["usd_1m"] - o_df["swap_usd_1m"]

    extra_close = pd.DataFrame(index=idx)
    extra_min = pd.DataFrame(index=idx)
    extra_close["O_qty1_NQ"] = o_df.groupby("dia")["usd_1m"].sum().reindex(idx, fill_value=0.0)
    extra_min["O_qty1_NQ"] = o_df.groupby("dia")["min_1m"].sum().reindex(idx, fill_value=0.0)

    o_nw = o_df[o_df["entry_dow"] != 2]
    extra_close["O_qty1_noWed_NQ"] = o_nw.groupby("dia")["usd_1m"].sum().reindex(idx, fill_value=0.0)
    extra_min["O_qty1_noWed_NQ"] = o_nw.groupby("dia")["min_1m"].sum().reindex(idx, fill_value=0.0)

    extra_close["O_qty1_swap8_NQ"] = o_df.groupby("dia")["usd_1m_swap8"].sum().reindex(idx, fill_value=0.0)
    extra_min["O_qty1_swap8_NQ"] = (o_df["min_1m"] - o_df["swap_usd_1m"]).groupby(o_df["dia"]).sum().reindex(idx, fill_value=0.0)
    return extra_close, extra_min


def build_daily_min_matrix(X: pd.DataFrame, extra_min: pd.DataFrame) -> pd.DataFrame:
    M_min = pd.read_csv(ROOT / "docs/research/cartera_nt8_20261125/MATRIZ_DIARIA_MIN_1MICRO.csv.gz", index_col=0, parse_dates=True)
    FS = pd.read_csv(ROOT / "docs/research/remedicion_fs_il_20261121/FS_OPS_NQ_IL.csv.gz", parse_dates=["dia"])
    fr_nq = float(costos.friccion_rt_puntos("NQ", "base"))
    fr_mnq = float(costos.friccion_rt_puntos("MNQ", "base"))

    Ymin = pd.DataFrame(index=X.index)
    # 1) Direct intraday minimums from MATRIZ_DIARIA_MIN_1MICRO
    for c in X.columns:
        if c in extra_min.columns:
            Ymin[c] = extra_min[c].reindex(X.index).fillna(0.0)
        elif c in M_min.columns:
            # NT8 intraday strategies: use recorded intraday minimum
            Ymin[c] = np.minimum(M_min[c].reindex(X.index).fillna(0.0), np.minimum(X[c], 0.0))
        elif c.startswith("FS_") and c.endswith("_NQ"):
            mod = c.split("_")[1]
            g = FS[FS["modulo"] == mod].copy()
            if len(g):
                # mae_pts >= 0 in FS_OPS_NQ_IL (verify sign)
                mae = g["mae_pts"].abs()
                g["min_usd_1m"] = -(mae + fr_mnq) * 2.0
                g["pnl_usd_1m"] = (g["neto"] + fr_nq - fr_mnq) * 2.0
                g["worst"] = np.minimum(g["min_usd_1m"], np.minimum(g["pnl_usd_1m"], 0.0))
                Ymin[c] = g.groupby("dia")["worst"].sum().reindex(X.index, fill_value=0.0)
            else:
                Ymin[c] = np.minimum(X[c], 0.0)
        else:
            # Multi-day or external series without intraday log: conservative min(0, close)
            Ymin[c] = np.minimum(X[c], 0.0)
    return Ymin


def mc_lucid_fast(y: np.ndarray, ymin: np.ndarray, nsum: float, cta: str = "150K", mean_mult: float = 0.5, n_paths: int = 3000, seed: int = 2026) -> dict:
    # Rules matching kaggle_cartera_gestion_kernel.py CUENTAS
    cuentas = {
        "50K": (95.2, 3000.0, 2000.0, 2100.0, 1200.0, 2000.0, 150.0, 40, 0.4),
        "150K": (214.25, 9000.0, 4500.0, 4600.0, 2700.0, 3000.0, 250.0, 100, 0.4),
    }
    precio, obj, mll, lock, dll, cap, dmin, tope, cons = cuentas[cta]
    if nsum > tope:
        return {"pasa": 0.0, "cobra": 0.0, "ev": -precio, "p_ganar": 0.0, "quiebra_eval": 1.0, "retiros": 0.0, "dias": 0.0, "blocked_cap": True}
    rng = np.random.default_rng(seed)
    L = len(y)
    sh = (mean_mult - 1.0) * float(np.mean(y))
    ys = y + sh
    yms = np.minimum(ymin + sh, np.minimum(ys, 0.0))

    pasa = 0
    quiebra = 0
    pagos = np.zeros(n_paths)
    cob = np.zeros(n_paths)
    dias = np.zeros(n_paths)

    for k in range(n_paths):
        pos = int(rng.integers(0, L))
        paso = 0
        bal = 0.0
        piso = -mll
        maxc = 0.0
        mayor = 0.0
        d = 0
        ok = False
        while d < 250:
            if paso % 10 == 0:
                pos = int(rng.integers(0, L))
            j = (pos + paso % 10) % L
            paso += 1
            p = float(ys[j])
            pm = float(yms[j])
            if dll > 0 and pm <= -dll:
                p = -dll
                pm = -dll
            if bal + pm <= piso:
                quiebra += 1
                break
            bal += p
            d += 1
            if p > mayor:
                mayor = p
            if bal > maxc:
                maxc = bal
            piso = min(max(piso, maxc - mll), 100.0)
            if bal >= obj and mayor <= cons * bal:
                ok = True
                break
        dias[k] = d
        if not ok:
            continue
        pasa += 1
        bal = 0.0
        piso = -mll
        maxc = 0.0
        c0 = 0.0
        dok = 0
        f = 0
        npg = 0
        tot = 0.0
        while f < 250 and npg < 5:
            if paso % 10 == 0:
                pos = int(rng.integers(0, L))
            j = (pos + paso % 10) % L
            paso += 1
            p = float(ys[j])
            pm = float(yms[j])
            if dll > 0 and pm <= -dll:
                p = -dll
                pm = -dll
            if bal + pm <= piso:
                break
            bal += p
            f += 1
            if p >= dmin:
                dok += 1
            if bal > maxc:
                maxc = bal
            if piso < 100.0:
                piso = 100.0 if maxc > lock else max(piso, maxc - mll)
            monto = min(cap, 0.5 * bal)
            if dok >= 5 and bal > c0 and monto >= 500.0:
                tot += 0.9 * monto
                bal -= monto
                npg += 1
                piso = 100.0
                c0 = bal
                dok = 0
        cob[k] = tot
        pagos[k] = npg
        dias[k] += f

    return {
        "pasa": round(pasa / n_paths, 4),
        "cobra": round(float((pagos > 0).mean()), 4),
        "quiebra_eval": round(quiebra / n_paths, 4),
        "ev": round(float(cob.mean() - precio), 1),
        "p_ganar": round(float((cob > precio).mean()), 4),
        "retiros": round(float(pagos.mean()), 3),
        "dias": round(float(dias.mean()), 1),
    }


def eval_portfolio(name: str, cols: List[str], weights: Dict[str, float], X: pd.DataFrame, Ymin: pd.DataFrame, target_sd_m: float | None = None) -> dict:
    w = pd.Series(weights, dtype=float)
    s = (X[cols] * w).sum(axis=1)
    smin = (Ymin[cols] * w).sum(axis=1)
    st = stats_serie(s, smin)
    out = {"name": name, "n_strat": len(cols), "sum_weights": round(float(w.sum()), 3), "weights": {k: round(float(v), 3) for k, v in weights.items()}, "raw": st}
    if target_sd_m and st["sd_mes"] > 0:
        scale = target_sd_m / st["sd_mes"]
        out["vol_matched_scale"] = round(float(scale), 3)
        out["vol_matched"] = stats_serie(s * scale, smin * scale)
    # A5 blocks (excluding TERMINAL >= 2026-10-01 already excluded)
    ses = pd.Series([int(d.strftime("%Y%m%d")) for d in s.index], index=s.index)
    blq = ses.map(a5_bloque)
    out["a5_usd_mes"] = {b: round(float(stats_serie(s[blq == b])["usd_mes"]), 1) for b in ("DESC", "REP", "HOLDOUT") if (blq == b).any()}
    tramo = s[s.index >= "2026-05-01"]
    tramo_min = smin[smin.index >= "2026-05-01"]
    out["tramo_2026_05_09"] = {
        "usd_total": round(float(tramo.sum()), 1),
        "dd_intra": round(float(stats_serie(tramo, tramo_min)["caida_max_intra"]), 1),
    }
    return out


def expanding_walk_forward(X: pd.DataFrame, Ymin: pd.DataFrame, cols: List[str], mode_cfg: dict, min_months: int = 24) -> Tuple[pd.Series, pd.Series, List[dict]]:
    """Walk-forward trimestral expandido estrictamente causal (usa solo t < trimestre)."""
    months = sorted(X.index.to_period("M").unique())
    start_p = months[min_months]
    quarters = sorted(set(p.asfreq("Q") for p in months if p >= start_p))
    rets = []
    mins = []
    hist_sel = []
    for q in quarters:
        q_start = q.start_time
        q_end = q.end_time
        train = X.loc[X.index < q_start, cols]
        test_x = X.loc[(X.index >= q_start) & (X.index <= q_end), cols]
        test_min = Ymin.loc[test_x.index, cols]
        if len(test_x) == 0:
            continue
        sel, w, _ = regla_param(train, **mode_cfg)
        ws = pd.Series(w)
        rets.append((test_x[sel] * ws).sum(axis=1))
        mins.append((test_min[sel] * ws).sum(axis=1))
        hist_sel.append({"quarter": str(q), "n": len(sel), "sel": sel})
    return pd.concat(rets), pd.concat(mins), hist_sel


def main() -> None:
    print("=== 1. AUDITORIA NT8 ENGINES ===")
    nt8_audit = audit_nt8_engines()
    print(json.dumps(nt8_audit, indent=2))

    S = pd.read_csv(ROOT / "docs/research/estabilidad_cartera_20261126/SERIES_DIARIAS.csv.gz", index_col=0, parse_dates=True)
    S = S.loc[:, S.notna().all()]
    extra_close, extra_min = compute_real_o_qty1_and_ymin(S.index)
    X = pd.concat([S, extra_close], axis=1)
    Ymin = build_daily_min_matrix(X, extra_min)

    # Check FS_O_NQ zero days and FS_F_NQ yearly stats
    o_post = S.loc["2025-10-14":"2026-09-30", "FS_O_NQ"]
    o_real_post = X.loc["2025-10-14":"2026-09-30", "O_qty1_NQ"]
    o_real_nw_post = X.loc["2025-10-14":"2026-09-30", "O_qty1_noWed_NQ"]
    o_audit = {
        "FS_O_NQ_active_days_post_20251014": int((o_post != 0).sum()),
        "FS_O_NQ_usd_post_20251014": round(float(o_post.sum()), 2),
        "O_qty1_NQ_active_days_post_20251014": int((o_real_post != 0).sum()),
        "O_qty1_NQ_usd_post_20251014": round(float(o_real_post.sum()), 2),
        "O_qty1_NQ_dd_intra_post_20251014": round(float(stats_serie(o_real_post, extra_min.loc[o_real_post.index, "O_qty1_NQ"])["caida_max_intra"]), 2),
        "O_qty1_noWed_NQ_usd_post_20251014": round(float(o_real_nw_post.sum()), 2),
        "O_qty1_swap8_full_2019_2026_usd_mes": round(float(stats_serie(X["O_qty1_swap8_NQ"])["usd_mes"]), 2),
    }
    print("\n=== 2. AUDITORIA FS_O_NQ MUERTA vs O_qty1_NQ REAL ===")
    print(json.dumps(o_audit, indent=2))

    # FS_F_NQ & FS_C_NQ yearly breakdown from FS_OPS_NQ_IL
    FS = pd.read_csv(ROOT / "docs/research/remedicion_fs_il_20261121/FS_OPS_NQ_IL.csv.gz", parse_dates=["dia"])
    fr_nq = float(costos.friccion_rt_puntos("NQ", "base"))
    fr_mnq = float(costos.friccion_rt_puntos("MNQ", "base"))
    fc_audit = {}
    for mod in ("F", "C", "N", "O", "R", "T", "Z", "V"):
        g = FS[(FS["modulo"] == mod) & (FS["dia"] >= "2012-01-01") & (FS["dia"] <= "2026-09-30")].copy()
        g["usd_1m"] = (g["neto"] + fr_nq - fr_mnq) * 2.0
        g["y"] = g["dia"].dt.year
        s_d = g.groupby("dia")["usd_1m"].sum().reindex(pd.date_range("2012-01-01", "2026-09-30", freq="B"), fill_value=0.0)
        m_12 = _mes(s_d)
        fc_audit[mod] = {
            "n_2012_2026": int(len(g)),
            "sharpe_2012_2026": round(float(m_12.mean() / m_12.std(ddof=1) * np.sqrt(12)), 3),
            "pct_anios_pos_2012_2026": round(float((g.groupby("y")["usd_1m"].sum() > 0).mean()), 3),
            "ops_por_anio": {int(k): int(v) for k, v in g.groupby("y").size().items()},
        }
    print("\n=== 3. HISTORIA COMPLETA 2012-2026 DE MODULOS ELEGIDOS POR CLAUDE ===")
    for k, v in fc_audit.items():
        print(f"  {k}: sharpe_12_26={v['sharpe_2012_2026']}, yr+={v['pct_anios_pos_2012_2026']}, ops_2024_2026={{2024:{v['ops_por_anio'].get(2024,0)}, 2025:{v['ops_por_anio'].get(2025,0)}, 2026:{v['ops_por_anio'].get(2026,0)}}}")

    # Trace Claude step-by-step on 2019-07 -> 2023-06 (INTRADIA and MIXTO)
    cols_claude_intra = [c for c in S.columns if not c.startswith(NOCHE)]
    cols_claude_mix = list(S.columns)
    sel_ini, ev_ini = ("2019-07-01", "2023-06-30"), ("2023-07-01", "2026-09-30")

    _, _, trace_intra = regla_param(S.loc[sel_ini[0]:sel_ini[1], cols_claude_intra], fix_step2=False)
    print("\n=== 4. TRAZA PASO A PASO DE REGLA_CARTERA (INTRADIA 2019-23 -> POR QUE EXPULSO A R_NQ) ===")
    for row in trace_intra[:10]:
        print(" ", row)

    # Ablation on Claude split (2019-07..2023-06 -> 2023-07..2026-09)
    print("\n=== 5. MATRIZ DE ABLACION OOS (2023-07 -> 2026-09) + VOL-MATCHED + DD INTRADIA ===")
    ablation = {}
    for univ_name, is_mix in (("INTRADIA", False), ("MIXTO", True)):
        base_cols = INTRA8 + INTER3 if is_mix else INTRA8
        actual_ev = eval_portfolio(f"{univ_name}_Actual", base_cols, {c: 1.0 for c in base_cols}, X.loc[ev_ini[0]:ev_ini[1]], Ymin.loc[ev_ini[0]:ev_ini[1]])
        target_sd = actual_ev["raw"]["sd_mes"]

        pool_claude = cols_claude_mix if is_mix else cols_claude_intra
        pool_clean_o = [c for c in X.columns if c not in ("FS_O_NQ", "O_qty1_noWed_NQ", "O_qty1_swap8_NQ")] if is_mix else cols_claude_intra

        configs = {
            "0_Actual_Base": (pool_claude, base_cols, {c: 1.0 for c in base_cols}),
        }
        sel_c, w_c, _ = regla_param(S.loc[sel_ini[0]:sel_ini[1], pool_claude], fix_step2=False)
        configs["1_Claude_Original_1sd"] = (pool_claude, sel_c, w_c)
        configs["1b_Claude_Original_1micro"] = (pool_claude, sel_c, {c: 1.0 for c in sel_c})

        sel_f1, w_f1, _ = regla_param(S.loc[sel_ini[0]:sel_ini[1], pool_claude], fix_step2=True)
        configs["2_Fix1_Paso2_R"] = (pool_claude, sel_f1, w_f1)

        sel_f2, w_f2, _ = regla_param(X.loc[sel_ini[0]:sel_ini[1], pool_clean_o], fix_step2=True)
        configs["3_Fix2_O_Real_qty1"] = (pool_clean_o, sel_f2, w_f2)

        sel_f3, w_f3, _ = regla_param(
            X.loc[sel_ini[0]:sel_ini[1], pool_clean_o],
            fix_step2=True,
            excluded=("FS_F_NQ", "FS_C_NQ"),
            w_clip=(0.5, 2.0),
        )
        configs["4_Fix3_NoFC_BoundedW"] = (pool_clean_o, sel_f3, w_f3)

        ablation[univ_name] = {}
        print(f"\n-- {univ_name} (target actual sd_mes=${target_sd:.1f}) --")
        for cfg_name, (_, scols, sw) in configs.items():
            ev_r = eval_portfolio(cfg_name, scols, sw, X.loc[ev_ini[0]:ev_ini[1]], Ymin.loc[ev_ini[0]:ev_ini[1]], target_sd_m=target_sd)
            ablation[univ_name][cfg_name] = ev_r
            raw = ev_r["raw"]
            vm = ev_r["vol_matched"]
            print(
                f"  {cfg_name:26s} | n={len(scols):2d} {scols} | "
                f"RAW: $/m={raw['usd_mes']:6.1f} Sh={raw['sharpe']:4.2f} ddEOD={raw['caida_max_eod']:7.0f} ddINTRA={raw['caida_max_intra']:7.0f} | "
                f"VOL-MATCH(x{ev_r['vol_matched_scale']:.2f}): $/m={vm['usd_mes']:6.1f} ddINTRA={vm['caida_max_intra']:7.0f} Tr26={ev_r['tramo_2026_05_09']['usd_total']:6.0f}"
            )

    # Multi-split sensitivity + Expanding Walk-Forward (2021-07 -> 2026-09)
    print("\n=== 6. SENSIBILIDAD A MULTIPLES CORTES Y WALK-FORWARD EXPANDIDO (2021-07 -> 2026-09) ===")
    multi_splits = {}
    for cut in ("2021-12-31", "2022-06-30", "2022-12-31", "2023-06-30", "2023-12-31", "2024-06-30"):
        ev_start = (pd.Timestamp(cut) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        row = {}
        for u, is_mix, bcols in (("INTRADIA", False, INTRA8), ("MIXTO", True, INTRA8 + INTER3)):
            p_cl = cols_claude_mix if is_mix else cols_claude_intra
            p_ok = [c for c in X.columns if c not in ("FS_O_NQ", "O_qty1_noWed_NQ", "O_qty1_swap8_NQ")] if is_mix else cols_claude_intra
            s_c, w_c, _ = regla_param(S.loc[:cut, p_cl], fix_step2=False)
            s_3, w_3, _ = regla_param(X.loc[:cut, p_ok], fix_step2=True, excluded=("FS_F_NQ", "FS_C_NQ"), w_clip=(0.5, 2.0))
            st_act = stats_serie(X.loc[ev_start:, bcols].sum(axis=1), Ymin.loc[ev_start:, bcols].sum(axis=1))
            st_cl = stats_serie((S.loc[ev_start:, s_c] * pd.Series(w_c)).sum(axis=1), (Ymin.loc[ev_start:, s_c] * pd.Series(w_c)).sum(axis=1))
            st_f3 = stats_serie((X.loc[ev_start:, s_3] * pd.Series(w_3)).sum(axis=1), (Ymin.loc[ev_start:, s_3] * pd.Series(w_3)).sum(axis=1))
            row[u] = {"actual_sh": round(st_act["sharpe"], 2), "claude_sh": round(st_cl["sharpe"], 2), "fix3_sh": round(st_f3["sharpe"], 2),
                      "actual_ddI": round(st_act["caida_max_intra"]), "claude_ddI": round(st_cl["caida_max_intra"]), "fix3_ddI": round(st_f3["caida_max_intra"]),
                      "meses": st_act["meses"]}
        multi_splits[cut] = row
        print(f"  cut={cut} (eval={row['INTRADIA']['meses']}m) | INTRA Sh(act/cl/f3)={row['INTRADIA']['actual_sh']}/{row['INTRADIA']['claude_sh']}/{row['INTRADIA']['fix3_sh']} | MIX Sh={row['MIXTO']['actual_sh']}/{row['MIXTO']['claude_sh']}/{row['MIXTO']['fix3_sh']}")

    wf_results = {}
    for u, is_mix, bcols in (("INTRADIA", False, INTRA8), ("MIXTO", True, INTRA8 + INTER3)):
        p_cl = cols_claude_mix if is_mix else cols_claude_intra
        p_ok = [c for c in X.columns if c not in ("FS_O_NQ", "O_qty1_noWed_NQ", "O_qty1_swap8_NQ")] if is_mix else cols_claude_intra
        r_cl, rm_cl, h_cl = expanding_walk_forward(S, Ymin, p_cl, dict(fix_step2=False))
        r_f3, rm_f3, h_f3 = expanding_walk_forward(X, Ymin, p_ok, dict(fix_step2=True, excluded=("FS_F_NQ", "FS_C_NQ"), w_clip=(0.5, 2.0)))
        r_act = X.loc[r_cl.index, bcols].sum(axis=1)
        rm_act = Ymin.loc[r_cl.index, bcols].sum(axis=1)
        st_act = stats_serie(r_act, rm_act)
        st_cl = stats_serie(r_cl, rm_cl)
        st_f3 = stats_serie(r_f3, rm_f3)
        wf_results[u] = {
            "actual": st_act,
            "claude_wf": st_cl,
            "fix3_wf": st_f3,
            "wf_series_sample": {"from": str(r_cl.index.min().date()), "to": str(r_cl.index.max().date()), "days": len(r_cl)},
        }
        print(f"  WF {u} ({r_cl.index.min().date()}->{r_cl.index.max().date()}):")
        print(f"    Actual  : Sh={st_act['sharpe']:.2f}, $/m={st_act['usd_mes']:.1f}, ddEOD={st_act['caida_max_eod']:.0f}, ddINTRA={st_act['caida_max_intra']:.0f}")
        print(f"    ClaudeWF: Sh={st_cl['sharpe']:.2f}, $/m={st_cl['usd_mes']:.1f}, ddEOD={st_cl['caida_max_eod']:.0f}, ddINTRA={st_cl['caida_max_intra']:.0f}")
        print(f"    Fix3_WF : Sh={st_f3['sharpe']:.2f}, $/m={st_f3['usd_mes']:.1f}, ddEOD={st_f3['caida_max_eod']:.0f}, ddINTRA={st_f3['caida_max_intra']:.0f}")

    # Monte Carlo LucidFlex 150K & 50K for Intraday strategies (integer micros on Eval 2023-07->2026-09 & Full)
    print("\n=== 7. SIMULACION MONTE CARLO LUCIDFLEX (MINIMO INTRADIA REAL, MICROS ENTEROS) ===")
    sel_cl_in, w_cl_in, _ = regla_param(S.loc[sel_ini[0]:sel_ini[1], cols_claude_intra], fix_step2=False)
    sel_f3_in, w_f3_in, _ = regla_param(X.loc[sel_ini[0]:sel_ini[1], cols_claude_intra], fix_step2=True, excluded=("FS_F_NQ", "FS_C_NQ"), w_clip=(0.5, 2.0))
    mic_cl_1 = {c: 1 for c in sel_cl_in}
    mic_cl_r = {c: int(max(1, round(v))) for c, v in w_cl_in.items()}
    mic_f3_1 = {c: 1 for c in sel_f3_in}
    mic_f3_r = {c: int(max(1, round(v))) for c, v in w_f3_in.items()}

    mc_res = {}
    for cta in ("150K", "50K"):
        mc_res[cta] = {}
        for label, cols, mic in (
            ("Actual_INTRA8_1m", INTRA8, {c: 1 for c in INTRA8}),
            ("Claude_1m", sel_cl_in, mic_cl_1),
            ("Claude_1sd_round", sel_cl_in, mic_cl_r),
            ("Fix3_1m", sel_f3_in, mic_f3_1),
            ("Fix3_1sd_round", sel_f3_in, mic_f3_r),
        ):
            mw = pd.Series(mic, dtype=float)
            y_ev = (X.loc[ev_ini[0]:ev_ini[1], cols] * mw).sum(axis=1).to_numpy()
            ym_ev = (Ymin.loc[ev_ini[0]:ev_ini[1], cols] * mw).sum(axis=1).to_numpy()
            nsum = float(mw.sum())
            r50 = mc_lucid_fast(y_ev, ym_ev, nsum, cta=cta, mean_mult=0.5, n_paths=3000)
            r100 = mc_lucid_fast(y_ev, ym_ev, nsum, cta=cta, mean_mult=1.0, n_paths=3000)
            mc_res[cta][label] = {"micros": mic, "eval_50pct": r50, "eval_100pct": r100}
            print(f"  Lucid {cta:4s} | {label:18s} (sum_m={int(nsum):2d}) | 50%: pasa={r50['pasa']*100:4.1f}%, EV=${r50['ev']:6.0f}, pg={r50['p_ganar']*100:4.1f}% | 100%: EV=${r100['ev']:6.0f}")

    # Save enriched daily series & minimums for downstream portfolio optimization
    X.to_csv(OUT / "SERIES_AUDITORIA_DIARIAS.csv.gz")
    Ymin.to_csv(OUT / "SERIES_AUDITORIA_MIN_INTRADIA.csv.gz")

    summary = {
        "nt8_audit": nt8_audit,
        "o_qty1_audit": o_audit,
        "fc_2012_2026_audit": fc_audit,
        "trace_regla_intradia_2019_2023": trace_intra,
        "ablation_2023_2026": ablation,
        "multi_splits": multi_splits,
        "expanding_walk_forward": wf_results,
        "lucid_mc_2023_2026": mc_res,
    }
    (OUT / "AUDITORIA_RESUMEN.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False, default=float), encoding="utf-8")
    print("\nSaved:", OUT / "AUDITORIA_RESUMEN.json")


if __name__ == "__main__":
    main()
