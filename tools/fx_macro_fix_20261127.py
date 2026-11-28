#!/usr/bin/env python3
"""FX-MACRO-FIX-20Y: Reloj de Sesión FX (K58), Oro Asia/Londres vs NY, Rebalanceo Treasury Fin de Mes y XS-Momentum No-Equity (2006–2026-09).

Pre-registro: docs/research/fx_macro_fix_20261127/PREREGISTRO.md (K32/K51/K58/K64).
Evalúa ESTRICTAMENTE sobre DESC + REP (< 2026-10-01); HOLDOUT A5 (63m) y TERMINAL SELLADOS (NaN).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))

from edgelab.holdout import a5_bloque  # noqa: E402
from edgelab.research.alineacion_horaria import exigir_alineada  # noqa: E402
from marco_sin_forward import _a5_mes_blq, stats_monthly_10vol  # noqa: E402
import macro_risk_premia_20261127 as MRP  # noqa: E402
from registro_global import exigir_contada  # noqa: E402

PRE = "docs/research/fx_macro_fix_20261127/PREREGISTRO.md"
OUT = ROOT / "docs/research/fx_macro_fix_20261127"
OUT.mkdir(parents=True, exist_ok=True)
DK = ROOT / "data/m1dk"
CACHE_SESS = DK / "daily_sessions_v1.parquet"
NONEQ_12 = ["TLT", "IEF", "SHY", "TIP", "LQD", "HYG", "GLD", "SLV", "DBC", "USO", "FXE", "FXY"]


def verificar_k58_dukascopy() -> dict:
    """Compuerta K58 obligatoria: verifica XAUUSD Dukascopy (-7h -> NY -> UTC) contra GC NT8 UTC en invierno, DST US-UE y verano."""
    gc = pd.read_parquet(ROOT / "data/m1nt8/GC_M1_nonadj_utc.parquet")["close"]
    if gc.index.tz is not None:
        gc.index = gc.index.tz_convert("UTC").tz_localize(None)
    prefixes = ("202401", "2024031", "2024032", "202407")
    rows: list[tuple[str, float]] = []
    with (DK / "XAUUSD_M1_dukas-M1-.csv").open("r", encoding="utf-8") as fh:
        fh.readline()
        for line in fh:
            if line.startswith(prefixes):
                p = line.split(",")
                rows.append((p[0] + " " + p[1], float(p[5])))
    idx_ny = pd.to_datetime([r[0] for r in rows], format="%Y%m%d %H:%M:%S") - pd.Timedelta(hours=7)
    idx_utc = idx_ny.tz_localize("America/New_York", ambiguous="NaT", nonexistent="NaT").tz_convert("UTC").tz_localize(None)
    dk = pd.Series([r[1] for r in rows], index=idx_utc)
    dk = dk[dk.index.notna()]
    dk = dk[~dk.index.duplicated(keep="last")].sort_index()

    res_k58 = {}
    for tag, sl in [("invierno_2024_01", slice("2024-01-02", "2024-01-31")),
                    ("gap_dst_us_eu_2024_03", slice("2024-03-18", "2024-03-22")),
                    ("verano_2024_07", slice("2024-07-01", "2024-07-31"))]:
        c0 = exigir_alineada(dk.loc[sl], gc.loc[sl], corr_min=0.80, desfases_min=range(-180, 181, 30), etiqueta=f"XAUUSD_DK:{tag}")
        res_k58[tag] = {"desfase_min": 0, "corr": round(float(c0), 4)}
    return res_k58


def _extract_sessions(csv_name: str, targets_ny_min: dict[str, int]) -> pd.DataFrame:
    """Streaming vectorized extraction of NY session snapshot prices from Dukascopy M1 (t_ny = t_dukas - 7h)."""
    # Pre-filter by Dukascopy minute window around target NY minutes (target + 7h)
    valid_dk_mins: set[int] = set()
    for m_ny in targets_ny_min.values():
        m_dk = (m_ny + 420) % 1440
        for d in range(-5, 1):
            valid_dk_mins.add((m_dk + d) % 1440)

    chunks = []
    for ch in pd.read_csv(DK / csv_name, usecols=["Date", "Time", "Close"], dtype={"Date": str, "Time": str, "Close": float}, chunksize=800_000):
        ch = ch[ch["Date"] <= "20260930"]
        if not len(ch):
            continue
        hhmm = ch["Time"].str.slice(0, 2).astype(int) * 60 + ch["Time"].str.slice(3, 5).astype(int)
        sub = ch[hhmm.isin(valid_dk_mins)].copy()
        if not len(sub):
            continue
        dt_ny = pd.to_datetime(sub["Date"] + " " + sub["Time"], format="%Y%m%d %H:%M:%S") - pd.Timedelta(hours=7)
        sub["ny_date"] = dt_ny.dt.normalize()
        sub["ny_min"] = dt_ny.dt.hour * 60 + dt_ny.dt.minute
        chunks.append(sub[["ny_date", "ny_min", "Close"]])

    raw = pd.concat(chunks, ignore_index=True).sort_values(["ny_date", "ny_min"])
    out = pd.DataFrame(index=pd.DatetimeIndex(sorted(raw["ny_date"].unique())))
    for col, tgt in targets_ny_min.items():
        m_ok = raw[(raw["ny_min"] <= tgt) & (raw["ny_min"] >= tgt - 5)]
        out[col] = m_ok.groupby("ny_date")["Close"].last().reindex(out.index)
    return out


def load_dukas_sessions() -> pd.DataFrame:
    if CACHE_SESS.exists():
        df = pd.read_parquet(CACHE_SESS)
        if df.index.max() < pd.Timestamp("2026-10-01") and len(df) > 4000:
            return df
    print("Extrayendo snapshots horarios NY desde CSVs Dukascopy...", flush=True)
    eur = _extract_sessions("EURUSD_M1_dukas-M1-.csv", {"eur_0300": 180, "eur_1100": 660, "eur_1700": 1020})
    jpy = _extract_sessions("USDJPY_M1_dukas-M1-.csv", {"jpy_1900": 1140, "jpy_0300": 180, "jpy_0800": 480, "jpy_1600": 960})
    xau = _extract_sessions("XAUUSD_M1_dukas-M1-.csv", {"xau_1700": 1020, "xau_1800": 1080, "xau_0830": 510, "xau_1600": 960})

    idx = eur.index.union(jpy.index).union(xau.index).sort_values()
    S = pd.DataFrame(index=idx)
    for d in (eur, jpy, xau):
        for c in d.columns:
            S[c] = d[c].reindex(idx)

    # Carry Sunday 18:00/19:00 open to previous available date for Monday overnight
    S["jpy_1900_prev"] = S["jpy_1900"].ffill().shift(1)
    # Gold overnight starts at previous trading day 17:00 NY, or Sunday 18:00 NY when opening Monday
    gold_anchor = S["xau_1700"].combine_first(S["xau_1800"])
    S["xau_ovn_start"] = gold_anchor.ffill().shift(1)

    S = S[(S.index >= "2006-01-01") & (S.index < "2026-10-01") & (S.index.dayofweek < 5)].copy()
    S.to_parquet(CACHE_SESS)
    return S


def compute_fxf_daily() -> dict:
    k58 = verificar_k58_dukascopy()
    print(f"K58 OK: {k58}", flush=True)
    S = load_dukas_sessions()

    # Load ETF data for FXF3 & FXF4 + common index (< 2026-10-01)
    etfs = {}
    for sym in sorted(set(NONEQ_12 + ["SPY"])):
        _, ser, _ = MRP._fetch_one(sym)
        if ser is not None and len(ser) > 0:
            etfs[sym] = ser
    PX = pd.DataFrame(etfs).sort_index()
    PX = PX[(PX.index >= "2006-01-01") & (PX.index < MRP.CORTE)]
    R = PX.pct_change()
    idx_eval = PX.index
    blq = pd.Series([a5_bloque(int(d.strftime("%Y%m%d"))) for d in idx_eval], index=idx_eval)
    assert not blq.isin(["TERMINAL"]).any()

    # Align Dukascopy intraday session returns onto trading days
    eur_eu = np.log(S["eur_1100"] / S["eur_0300"]).reindex(idx_eval).fillna(0.0)
    eur_us = np.log(S["eur_1700"] / S["eur_1100"]).reindex(idx_eval).fillna(0.0)
    jpy_tk = np.log(S["jpy_0300"] / S["jpy_1900_prev"]).reindex(idx_eval).fillna(0.0)
    jpy_us = np.log(S["jpy_1600"] / S["jpy_0800"]).reindex(idx_eval).fillna(0.0)

    # FXF1: EUR short EU + long US (2 legs); JPY long Tokyo + short US (2 legs), causal 1/vol_21d scaled
    r_eur_raw = (-eur_eu + eur_us).clip(-0.08, 0.08)
    r_jpy_raw = (jpy_tk - jpy_us).clip(-0.08, 0.08)
    act_eur = ((eur_eu != 0) & (eur_us != 0)).astype(float)
    act_jpy = ((jpy_tk != 0) & (jpy_us != 0)).astype(float)
    v_eur = (r_eur_raw.rolling(21, min_periods=15).std().shift(1) * np.sqrt(252)).clip(lower=0.025).fillna(0.10)
    v_jpy = (r_jpy_raw.rolling(21, min_periods=15).std().shift(1) * np.sqrt(252)).clip(lower=0.025).fillna(0.10)
    lev_eur = (0.10 / v_eur).clip(0.25, 2.5) * 0.5
    lev_jpy = (0.10 / v_jpy).clip(0.25, 2.5) * 0.5

    def _fxf1(bps: float) -> pd.Series:
        c_eur = act_eur * lev_eur * 2.0 * (bps / 10_000.0)
        c_jpy = act_jpy * lev_jpy * 2.0 * (bps / 10_000.0)
        return (lev_eur * r_eur_raw - c_eur) + (lev_jpy * r_jpy_raw - c_jpy)

    # FXF2: Gold Asian/London Overnight long vs COMEX RTH short (zero static net beta)
    xau_ovn = np.log(S["xau_0830"] / S["xau_ovn_start"]).reindex(idx_eval).fillna(0.0).clip(-0.10, 0.10)
    xau_rth = np.log(S["xau_1600"] / S["xau_0830"]).reindex(idx_eval).fillna(0.0).clip(-0.10, 0.10)
    r_xau_raw = xau_ovn - xau_rth
    act_xau = ((xau_ovn != 0) & (xau_rth != 0)).astype(float)
    v_xau = (r_xau_raw.rolling(21, min_periods=15).std().shift(1) * np.sqrt(252)).clip(lower=0.04).fillna(0.15)
    lev_xau = (0.10 / v_xau).clip(0.25, 2.0)

    def _fxf2(bps: float) -> pd.Series:
        return lev_xau * r_xau_raw - act_xau * lev_xau * 2.0 * (bps / 10_000.0)

    # FXF3: Treasury Month-End Rebalance (TLT, IEF): long last 3 trading days of month, short first 3 trading days
    ym = idx_eval.to_period("M")
    pos_from_ini = pd.Series(0, index=idx_eval)
    pos_from_fin = pd.Series(0, index=idx_eval)
    for m in ym.unique():
        ix = np.flatnonzero(ym == m)
        pos_from_ini.iloc[ix] = np.arange(1, len(ix) + 1)
        pos_from_fin.iloc[ix] = np.arange(len(ix), 0, -1)
    sig_tr = pd.Series(0.0, index=idx_eval)
    sig_tr[pos_from_fin <= 3] = 1.0
    sig_tr[pos_from_ini <= 3] = -1.0
    tr_cols = ["TLT", "IEF"]
    vol_tr = (R[tr_cols].rolling(21, min_periods=15).std() * np.sqrt(252)).clip(lower=0.03)
    w_tr_raw = (0.5 * sig_tr).to_numpy()[:, None] / vol_tr
    w3 = w_tr_raw.div(w_tr_raw.abs().sum(axis=1).replace(0.0, np.nan).fillna(1.0), axis=0).where(sig_tr != 0, 0.0)
    w3_pad = w3.reindex(PX.columns).fillna(0.0) if set(w3.columns) == set(PX.columns) else pd.DataFrame(0.0, index=idx_eval, columns=PX.columns)
    for c in tr_cols:
        w3_pad[c] = w3[c]

    # FXF4: 12-ETF Non-Equity Cross-Sectional 12m-1m Momentum (top-3 vs bottom-3, 5d staggered)
    PX12 = PX[NONEQ_12]
    R12 = R[NONEQ_12]
    vol12 = (R12.rolling(21, min_periods=15).std() * np.sqrt(252)).clip(lower=0.025)
    mom12_1 = (PX12.shift(21) / PX12.shift(252) - 1.0) / vol12
    rk12 = mom12_1.rank(axis=1, ascending=False, method="first")
    n_av = mom12_1.notna().sum(axis=1).to_numpy()[:, None]
    w4_raw = pd.DataFrame(0.0, index=idx_eval, columns=NONEQ_12)
    w4_raw[(rk12 <= 3) & (n_av >= 8)] = 1.0
    w4_raw[(rk12 >= n_av - 2) & (n_av >= 8)] = -1.0
    w4_norm = w4_raw.div(vol12.replace(0.0, np.nan))
    pos_l = w4_norm.clip(lower=0.0)
    pos_s = (-w4_norm).clip(lower=0.0)
    w4_net = 0.5 * pos_l.div(pos_l.sum(axis=1).replace(0.0, np.nan), axis=0).fillna(0.0) - 0.5 * pos_s.div(pos_s.sum(axis=1).replace(0.0, np.nan), axis=0).fillna(0.0)
    w4 = MRP._stagger_weights(w4_net, 5)
    w4_pad = pd.DataFrame(0.0, index=idx_eval, columns=PX.columns)
    for c in NONEQ_12:
        w4_pad[c] = w4[c]

    s3_1, s3_2, tm3 = MRP._eval_weights(R, w3_pad, tx_bps=5.0, eq_borrow_bps=100.0, noneq_borrow_bps=50.0)
    s4_1, s4_2, tm4 = MRP._eval_weights(R, w4_pad, tx_bps=5.0, eq_borrow_bps=100.0, noneq_borrow_bps=50.0)

    raw_1x = pd.DataFrame({
        "FXF1_FX_Clock_Session_EURJPY": _fxf1(1.0),
        "FXF2_Gold_AsianOvn_vs_NY": _fxf2(2.0),
        "FXF3_Treasury_MonthEnd_Rebal": s3_1.reindex(idx_eval).fillna(0.0),
        "FXF4_NonEq_XS_Mom_12ETFs": s4_1.reindex(idx_eval).fillna(0.0),
    }, index=idx_eval)
    raw_2x = pd.DataFrame({
        "FXF1_FX_Clock_Session_EURJPY": _fxf1(2.0),
        "FXF2_Gold_AsianOvn_vs_NY": _fxf2(4.0),
        "FXF3_Treasury_MonthEnd_Rebal": s3_2.reindex(idx_eval).fillna(0.0),
        "FXF4_NonEq_XS_Mom_12ETFs": s4_2.reindex(idx_eval).fillna(0.0),
    }, index=idx_eval)
    turn_map = {
        "FXF1_FX_Clock_Session_EURJPY": round(float(act_eur.mean() * 252 * 2 + act_jpy.mean() * 252 * 2), 1),
        "FXF2_Gold_AsianOvn_vs_NY": round(float(act_xau.mean() * 252 * 2), 1),
        "FXF3_Treasury_MonthEnd_Rebal": tm3,
        "FXF4_NonEq_XS_Mom_12ETFs": tm4,
    }
    return {
        "k58": k58,
        "idx_eval": idx_eval,
        "blq": blq,
        "spy": R["SPY"].reindex(idx_eval).fillna(0.0),
        "raw_1x": raw_1x,
        "raw_2x": raw_2x,
        "turn_map": turn_map,
        "xau_ovn": (lev_xau * xau_ovn).reindex(idx_eval).fillna(0.0),
        "xau_rth_short": (-lev_xau * xau_rth).reindex(idx_eval).fillna(0.0),
    }


def main() -> int:
    exigir_contada(PRE)
    t0 = time.time()
    core = compute_fxf_daily()
    idx_eval, blq, raw_1x, raw_2x = core["idx_eval"], core["blq"], core["raw_1x"], core["raw_2x"]
    mask_dr = blq.isin(["DESC", "REP"])

    ho_m = pd.read_csv(ROOT / "docs/research/holdout_a5_nocme_20261127/SERIES_HOLDOUT_A5_NOCME_MENSUAL.csv.gz", index_col=0)
    ho_dr = ho_m[ho_m["bloque"].isin(["DESC", "REP"])].copy()
    ho_dr.index = pd.PeriodIndex(ho_dr.index, freq="M")

    mvc_m = pd.read_csv(ROOT / "docs/research/macro_cta_vrp_20261127/SERIES_DESC_REP.csv.gz", index_col=0, parse_dates=True)
    mvc_can = mvc_m["MVC_Canasta_InvVol"].dropna().groupby(lambda d: d.to_period("M")).sum()
    mrv_m = pd.read_csv(ROOT / "docs/research/m1_relval_eventos_20261127/SERIES_DESC_REP.csv.gz", index_col=0, parse_dates=True)
    mrv_can = mrv_m["MRV_Canasta_InvVol"].dropna().groupby(lambda d: d.to_period("M")).sum()

    res = {"k58_verificado": core["k58"], "rules": {}}
    daily_dr = pd.DataFrame(index=idx_eval)
    for c in raw_1x.columns:
        s1, s2 = raw_1x[c], raw_2x[c]
        daily_dr[c] = s1.where(mask_dr, np.nan)
        m1 = s1[mask_dr].groupby(lambda d: d.to_period("M")).sum()
        m2 = s2[mask_dr].groupby(lambda d: d.to_period("M")).sum()
        bm = pd.Series([_a5_mes_blq(p) for p in m1.index], index=m1.index)
        res["rules"][c] = {
            "turn_ann_x": core["turn_map"][c],
            "DESC": stats_monthly_10vol(m1[bm == "DESC"]),
            "REP": stats_monthly_10vol(m1[bm == "REP"]),
            "DESC_REP": stats_monthly_10vol(m1),
            "DESC_REP_stress2x": stats_monthly_10vol(m2),
            "corr_Carril2_DR": round(float(m1.corr(ho_dr["Carril2_Sell16"].dropna())), 3),
            "corr_MacroRP4_DR": round(float(m1.corr(ho_dr["Macro_RP_Canasta"].dropna())), 3),
            "corr_MVC_DR": round(float(m1.corr(mvc_can)), 3),
            "corr_MRV3_DR": round(float(m1.corr(mrv_can)), 3),
            "corr_SPY_DR": round(float(s1[mask_dr].corr(core["spy"][mask_dr])), 3),
        }

    # Gold leg breakdown (overnight vs short NY RTH)
    res["fxf2_legs_DR"] = {
        "xau_overnight_long": stats_monthly_10vol(core["xau_ovn"][mask_dr].groupby(lambda d: d.to_period("M")).sum()),
        "xau_rth_short": stats_monthly_10vol(core["xau_rth_short"][mask_dr].groupby(lambda d: d.to_period("M")).sum()),
    }

    rule_names = list(raw_1x.columns)
    alive = [c for c in rule_names if res["rules"][c]["DESC"]["sharpe"] >= 0.25]
    if not alive:
        alive = [max(rule_names, key=lambda c: res["rules"][c]["DESC"]["sharpe"])]

    m_desc_alive = pd.DataFrame({c: raw_1x.loc[blq == "DESC", c].groupby(lambda d: d.to_period("M")).sum() for c in alive})
    inv_sd = 1.0 / m_desc_alive.std(ddof=1).clip(lower=1e-6)
    w_can = (inv_sd / inv_sd.sum()).to_dict()

    can1 = sum(raw_1x[c] * w_can[c] for c in alive)
    can2 = sum(raw_2x[c] * w_can[c] for c in alive)
    sd_desc = float(can1[blq == "DESC"].groupby(lambda d: d.to_period("M")).sum().std(ddof=1) * np.sqrt(12.0))
    scale_10 = 0.10 / sd_desc if sd_desc > 0 else 1.0
    can1 = can1 * scale_10
    can2 = can2 * scale_10

    mc1 = can1[mask_dr].groupby(lambda d: d.to_period("M")).sum()
    mc2 = can2[mask_dr].groupby(lambda d: d.to_period("M")).sum()
    bm_c = pd.Series([_a5_mes_blq(p) for p in mc1.index], index=mc1.index)

    res["FXF_Canasta_InvVol"] = {
        "elegidas_DESC": alive,
        "pesos_InvVol": {k: round(float(v), 4) for k, v in w_can.items()},
        "DESC": stats_monthly_10vol(mc1[bm_c == "DESC"]),
        "REP": stats_monthly_10vol(mc1[bm_c == "REP"]),
        "DESC_REP": stats_monthly_10vol(mc1),
        "DESC_REP_stress2x": stats_monthly_10vol(mc2),
        "corr_Carril2_DR": round(float(mc1.corr(ho_dr["Carril2_Sell16"].dropna())), 3),
        "corr_MacroRP4_DR": round(float(mc1.corr(ho_dr["Macro_RP_Canasta"].dropna())), 3),
        "corr_MVC_DR": round(float(mc1.corr(mvc_can)), 3),
        "corr_MRV3_DR": round(float(mc1.corr(mrv_can)), 3),
        "corr_SPY_DR": round(float(can1[mask_dr].corr(core["spy"][mask_dr])), 3),
    }

    daily_dr["FXF_Canasta_InvVol"] = can1.where(mask_dr, np.nan)
    daily_dr["bloque"] = blq
    assert daily_dr.loc[~mask_dr, rule_names + ["FXF_Canasta_InvVol"]].isna().all().all(), "Leak in HOLDOUT/EMBARGO!"
    daily_dr.to_csv(OUT / "SERIES_DESC_REP.csv.gz")
    (OUT / "RESULTADO.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")

    k58 = core["k58"]
    md = [
        "# FX-MACRO-FIX-20Y: Reloj FX (K58), Oro Overnight vs NY, Treasury Fin de Mes y XS-Momentum Non-Equity (`2006–2026-09`)",
        "",
        f"Estado: RESULTADO — EF2 pre-registrado en [PREREGISTRO.md](PREREGISTRO.md) (`5` pruebas, `FX_MACRO_FIX_20Y`). **`HOLDOUT A5` (`63m`) y `>= 2026-10-01` SELLADOS (`NaN`).** Compuerta K58 superada (`corr` `2024-01={k58['invierno_2024_01']['corr']}`, `DST Mar={k58['gap_dst_us_eu_2024_03']['corr']}`, `2024-07={k58['verano_2024_07']['corr']}` en desfase `0`).",
        "",
        "| Mecanismo (`@10% vol`) | Rot/año | `DESC Sh` | `REP Sh` | `DR Sh / t` | `2x Stress` | `corr C2` | `corr MVC` | `corr MRV3` |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]
    for nm, v in res["rules"].items():
        md.append(
            f"| `{nm}` | `{v['turn_ann_x']}x` | `{v['DESC']['sharpe']}` | `{v['REP']['sharpe']}` | "
            f"**`{v['DESC_REP']['sharpe']} / {v['DESC_REP']['t']}`** | `{v['DESC_REP_stress2x']['sharpe']}` | "
            f"`{v['corr_Carril2_DR']:+.3f}` | `{v['corr_MVC_DR']:+.3f}` | `{v['corr_MRV3_DR']:+.3f}` |"
        )
    fc = res["FXF_Canasta_InvVol"]
    md.append(
        f"| **`FXF_Canasta_InvVol`** (`{len(alive)}` patas) | — | `{fc['DESC']['sharpe']}` | `{fc['REP']['sharpe']}` | "
        f"**`{fc['DESC_REP']['sharpe']} / {fc['DESC_REP']['t']}`** | `{fc['DESC_REP_stress2x']['sharpe']}` | "
        f"`{fc['corr_Carril2_DR']:+.3f}` | `{fc['corr_MVC_DR']:+.3f}` | `{fc['corr_MRV3_DR']:+.3f}` |"
    )
    md.extend([
        "",
        f"- **Desglose `FXF2` Oro (`DR`):** pierna Overnight Asia/Londres `Sh={res['fxf2_legs_DR']['xau_overnight_long']['sharpe']}` | pierna Corto COMEX RTH `Sh={res['fxf2_legs_DR']['xau_rth_short']['sharpe']}`.",
        "Diagnóstico de grilla: cero grilla paramétrica (`4` mecanismos fijos sin optimización por Sharpe).",
        "Episodios: evaluado en `DESC` (`144m`) + `REP` (`42m`) = `186m`; `HOLDOUT A5` (`63m`) sellado.",
        "",
        f"Aporte al referente: valida mecanismos macro/FX sin equity ni beta direccional de `20` años en `{round(time.time()-t0, 1)}s` con `63m` de holdout intactos.",
    ])
    (OUT / "RESULTADO.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps({"FXF_Canasta_InvVol": fc, "rules_DR": {k: (v["DESC_REP"]["sharpe"], v["DESC_REP"]["t"]) for k, v in res["rules"].items()}}, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
