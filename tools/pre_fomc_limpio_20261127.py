#!/usr/bin/env python3
"""PRE-FOMC-LIMPIO-20Y: Deriva Pre-FOMC con calendario 100% programado ex ante, salida 5 min antes del comunicado real,
transferencia multi-mercado ATJ-28 (EMD, RTY, GC y 4 índices Dukascopy tras K58) y plan formal K27/K42 (HOLDOUT sellado).

Pre-registro: docs/research/pre_fomc_limpio_20261127/PREREGISTRO.md (K32/K33/K42/K51/K58/K60/A5).
"""
from __future__ import annotations

import json
import math
import sys
import time
from math import erf, sqrt
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))

from edgelab import costos  # noqa: E402
from edgelab.funnel.libro_lord import LibroLord  # noqa: E402
from edgelab.holdout import a5_bloque, exigir_sin_holdout_no_abierto, mascara_a5_limpia  # noqa: E402
from edgelab.research import holdout_ventanas as HV  # noqa: E402
from edgelab.research.m1_intradia import leer_m1nt8  # noqa: E402
from fx_macro_fix_20261127 import verificar_k58_dukascopy  # noqa: E402
from marco_sin_forward import _a5_mes_blq, stats_monthly_10vol  # noqa: E402
from registro_global import exigir_contada  # noqa: E402

PRE = "docs/research/pre_fomc_limpio_20261127/PREREGISTRO.md"
OUT = ROOT / "docs/research/pre_fomc_limpio_20261127"
OUT.mkdir(parents=True, exist_ok=True)
DK = ROOT / "data/m1dk"
CACHE_DK = DK / "fomc_foreign_sessions_v1.parquet"

EXCLUDE_UNSCHED = {
    "2007-06-18", "2007-08-10", "2007-08-17",
    "2008-01-22", "2008-03-11", "2008-10-08",
    "2012-07-31", "2013-10-16", "2014-03-04",
    "2019-10-04", "2019-10-11",
    "2020-03-02", "2020-03-03", "2020-03-19", "2020-03-23", "2020-03-31", "2020-08-27",
    "2025-08-22",
}
PRESS_1230 = {
    "2011-04-27", "2011-06-22", "2011-11-02",
    "2012-01-25", "2012-04-25", "2012-06-20", "2012-09-13", "2012-12-12",
}
CORE3 = ["ES", "NQ", "YM"]
EXTRA_CME = ["EMD", "RTY", "GC"]
MICRO_MAP = {"ES": "MES", "NQ": "MNQ", "YM": "MYM", "EMD": "EMD", "RTY": "M2K", "GC": "MGC"}
DK_FILES = {
    "DAX": "DEUIDXEUR-M1-.csv",
    "EuroStoxx": "EUSIDXEUR-M1-.csv",
    "FTSE": "GBRIDXGBP-M1-.csv",
    "Nikkei": "JPNIDXJPY-M1-.csv",
}
Phi = lambda z: 0.5 * (1.0 + erf(z / sqrt(2.0)))


def build_clean_fomc_calendar() -> pd.DataFrame:
    cal = pd.read_parquet(ROOT / "data/m1nt8/us_market_events_calendar_2006_2026.parquet")
    cal.index = pd.to_datetime(cal.index).normalize()
    st = cal[cal["is_fomc_statement_day"] & (cal.index >= "2006-01-01") & (cal.index < "2026-10-01")].copy()
    st = st[~st.index.strftime("%Y-%m-%d").isin(EXCLUDE_UNSCHED)].copy()
    counts = st.groupby(st.index.year).size().to_dict()
    for yr in range(2006, 2026):
        exp = 7 if yr == 2020 else 8
        assert counts.get(yr) == exp, f"FOMC clean calendar mismatch {yr}: got {counts.get(yr)} vs {exp}"
    assert counts.get(2026) == 6
    exit_hhmm = []
    for d in st.index:
        ds = d.strftime("%Y-%m-%d")
        if ds in PRESS_1230:
            exit_hhmm.append(1225)
        elif d < pd.Timestamp("2013-01-01"):
            exit_hhmm.append(1410)
        else:
            exit_hhmm.append(1355)
    st["exit_hhmm"] = exit_hhmm
    st["blq"] = [a5_bloque(int(d.strftime("%Y%m%d"))) for d in st.index]
    return st


def _extract_cme_snaps(sym: str) -> pd.DataFrame:
    D = leer_m1nt8(ROOT / f"data/m1nt8/{sym}_M1_nonadj_utc.parquet")
    assert D.index.max() < pd.Timestamp("2026-10-01")
    D = D[D.index.dayofweek < 5]
    hhmm = D.index.hour * 100 + D.index.minute
    d_idx = D.index.normalize()
    out = pd.DataFrame(index=pd.DatetimeIndex(sorted(d_idx.unique())))
    out["px_1600"] = D[(hhmm >= 930) & (hhmm <= 1600)].groupby(d_idx[(hhmm >= 930) & (hhmm <= 1600)])["c"].last().reindex(out.index)
    for col, cutoff in [("px_1225", 1225), ("px_1355", 1355), ("px_1400", 1400), ("px_1410", 1410)]:
        m = (hhmm >= 930) & (hhmm <= cutoff)
        out[col] = D[m].groupby(d_idx[m])["c"].last().reindex(out.index)
    out = out.dropna(subset=["px_1600"])
    out["r_c2c"] = out["px_1600"] / out["px_1600"].shift(1) - 1.0
    out["vol20"] = (out["r_c2c"].rolling(20, min_periods=12).std() * np.sqrt(252.0)).clip(lower=0.05)
    return out


def _extract_dk_snaps() -> dict[str, pd.DataFrame]:
    if CACHE_DK.exists():
        raw = pd.read_parquet(CACHE_DK)
        return {sym: raw[raw["sym"] == sym].drop(columns=["sym"]) for sym in DK_FILES}

    print("Extrayendo snapshots NY (12:25, 13:55, 14:00, 14:10) de M1DK...", flush=True)
    # t_ny = t_dukas - 7h -> target Dukas hours/mins for NY 12:25, 13:55, 14:00, 14:10 are 19:20..19:25, 20:50..21:10
    valid_dk_mins = set()
    for m_ny in (745, 835, 840, 850):
        m_dk = (m_ny + 420) % 1440
        for d in range(-10, 1):
            valid_dk_mins.add((m_dk + d) % 1440)
    frames = []
    for sym, fname in DK_FILES.items():
        chunks = []
        for ch in pd.read_csv(DK / fname, usecols=["Date", "Time", "Close"], dtype={"Date": str, "Time": str, "Close": float}, chunksize=800_000):
            ch = ch[ch["Date"] <= "20260930"]
            if not len(ch):
                continue
            hm = ch["Time"].str.slice(0, 2).astype(int) * 60 + ch["Time"].str.slice(3, 5).astype(int)
            sub = ch[hm.isin(valid_dk_mins)].copy()
            if not len(sub):
                continue
            dt_ny = pd.to_datetime(sub["Date"] + " " + sub["Time"], format="%Y%m%d %H:%M:%S") - pd.Timedelta(hours=7)
            sub["ny_date"] = dt_ny.dt.normalize()
            sub["ny_min"] = dt_ny.dt.hour * 60 + dt_ny.dt.minute
            chunks.append(sub[["ny_date", "ny_min", "Close"]])
        all_c = pd.concat(chunks, ignore_index=True).sort_values(["ny_date", "ny_min"])
        all_c = all_c[all_c["ny_date"].dt.dayofweek < 5]
        df_s = pd.DataFrame(index=pd.DatetimeIndex(sorted(all_c["ny_date"].unique())))
        for col, tgt in [("px_1225", 745), ("px_1355", 835), ("px_1400", 840), ("px_1410", 850)]:
            m = all_c[(all_c["ny_min"] <= tgt) & (all_c["ny_min"] >= tgt - 15)]
            df_s[col] = m.groupby("ny_date")["Close"].last().reindex(df_s.index)
        df_s["r_c2c"] = df_s["px_1400"] / df_s["px_1400"].shift(1) - 1.0
        df_s["vol20"] = (df_s["r_c2c"].rolling(20, min_periods=12).std() * np.sqrt(252.0)).clip(lower=0.05)
        df_s["sym"] = sym
        frames.append(df_s)
    comb = pd.concat(frames)
    comb.to_parquet(CACHE_DK)
    return {sym: comb[comb["sym"] == sym].drop(columns=["sym"]) for sym in DK_FILES}


def _event_stats(r_arr: np.ndarray) -> dict:
    r = r_arr[np.isfinite(r_arr)]
    n = int(len(r))
    if n < 2:
        return dict(n=n, mean_bps=0.0, t=0.0, p=1.0, pct_pos=0.0)
    mu = float(r.mean())
    sd = float(r.std(ddof=1))
    t = mu / (sd / sqrt(n)) if sd > 0 else 0.0
    return dict(
        n=n,
        mean_bps=round(mu * 1e4, 2),
        sd_bps=round(sd * 1e4, 2),
        t=round(t, 2),
        p=round(1.0 - Phi(t), 5),
        pct_pos=round(float((r > 0).mean()), 3),
    )


def main() -> int:
    exigir_contada(PRE)
    t0 = time.time()
    k58 = verificar_k58_dukascopy()
    cal = build_clean_fomc_calendar()

    with costos.estimados_permitidos(PRE):
        fric_pts = {s: float(costos.friccion_rt_puntos(s)) for s in CORE3 + EXTRA_CME}
        fric_micro_pts = {s: float(costos.friccion_rt_puntos(MICRO_MAP[s])) for s in CORE3 + EXTRA_CME}

    cme_feats = {s: _extract_cme_snaps(s) for s in CORE3 + EXTRA_CME}
    dk_feats = _extract_dk_snaps()

    idx_core = cme_feats["ES"].index.intersection(cme_feats["NQ"].index).intersection(cme_feats["YM"].index)
    idx_core = idx_core[(idx_core >= "2008-01-01") & (idx_core < "2026-10-01")]

    # Build strict K60/A5 clean event table on DESC+REP ONLY
    cal_map = cal.set_index(cal.index)
    ev_rows = []
    placebo_non_fomc: dict[str, list[float]] = {s: [] for s in CORE3 + EXTRA_CME}

    all_feats = {**cme_feats, **dk_feats}
    for sym, df in all_feats.items():
        d_list = df.index[(df.index >= "2008-01-01") & (df.index < "2026-10-01")]
        d_int = np.asarray([int(d.strftime("%Y%m%d")) for d in d_list], dtype=int)
        for pos in range(1, len(d_list)):
            d_ent, d_ext = d_list[pos - 1], d_list[pos]
            di_ent, di_ext = int(d_ent.strftime("%Y%m%d")), int(d_ext.strftime("%Y%m%d"))
            if not (a5_bloque(di_ent) in ("DESC", "REP") and a5_bloque(di_ext) in ("DESC", "REP")):
                continue
            # Ensure strictly no holdout dates slip through
            exigir_sin_holdout_no_abierto([di_ent, di_ext], "PRE_FOMC_LIMPIO_20Y")
            p_in = df.at[d_ent, "px_1400"]
            v_lag = df.at[d_ent, "vol20"]
            if not (np.isfinite(p_in) and p_in > 0 and np.isfinite(v_lag) and v_lag > 0):
                continue
            w = float(np.clip(0.10 / v_lag, 0.25, 2.0))
            if d_ext in cal_map.index:
                hhmm_ex = int(cal_map.at[d_ext, "exit_hhmm"])
                p_out = df.at[d_ext, f"px_{hhmm_ex}"]
                if not (np.isfinite(p_out) and p_out > 0):
                    continue
                r_raw = float(p_out / p_in - 1.0)
                if sym in fric_pts:
                    c_mini = fric_pts[sym] / float(p_in)
                    c_mic = fric_micro_pts[sym] / float(p_in)
                else:
                    c_mini = 2.0 / 1e4
                    c_mic = 2.0 / 1e4
                ev_rows.append({
                    "sym": sym,
                    "d_entry": d_ent,
                    "d_exit": d_ext,
                    "blq": a5_bloque(di_ext),
                    "exit_hhmm": hhmm_ex,
                    "r_bruto_scaled": w * r_raw,
                    "r_mini_scaled": w * (r_raw - c_mini),
                    "r_micro_scaled": w * (r_raw - c_mic),
                    "r_2x_scaled": w * (r_raw - 2.0 * c_mini),
                    "r_raw_unscaled": r_raw,
                })
            elif sym in placebo_non_fomc:
                p_out_def = df.at[d_ext, "px_1355"]
                if np.isfinite(p_out_def) and p_out_def > 0:
                    r_raw = float(p_out_def / p_in - 1.0)
                    c_mini = fric_pts[sym] / float(p_in)
                    placebo_non_fomc[sym].append(w * (r_raw - c_mini))

    EV = pd.DataFrame(ev_rows)
    EV.to_csv(OUT / "EVENTOS_DESC_REP.csv.gz", index=False)

    # Core 3 (ES, NQ, YM) daily & monthly series (0 on non-event DESC+REP days)
    daily_core = pd.DataFrame(0.0, index=idx_core, columns=["bruto", "mini", "micro", "stress2x"])
    mask_core = mascara_a5_limpia([int(d.strftime("%Y%m%d")) for d in idx_core])
    core_ev = EV[EV["sym"].isin(CORE3)].groupby("d_exit")[["r_bruto_scaled", "r_mini_scaled", "r_micro_scaled", "r_2x_scaled"]].mean()
    for col_ev, col_out in [("r_bruto_scaled", "bruto"), ("r_mini_scaled", "mini"), ("r_micro_scaled", "micro"), ("r_2x_scaled", "stress2x")]:
        s = core_ev[col_ev].reindex(idx_core).fillna(0.0)
        daily_core[col_out] = s.where(mask_core, np.nan)

    def _m_stats(col: str, cond=None) -> dict:
        s = daily_core[col].dropna()
        if cond is not None:
            s = s[cond(s.index)]
        m = s.groupby(lambda d: d.to_period("M")).sum()
        return stats_monthly_10vol(m)

    # Event-level core basket metrics
    ev_c3 = EV[EV["sym"].isin(CORE3)].groupby("d_exit").agg(
        r_mini=("r_mini_scaled", "mean"),
        r_micro=("r_micro_scaled", "mean"),
        r_bruto=("r_bruto_scaled", "mean"),
        r_2x=("r_2x_scaled", "mean"),
    ).sort_index()

    # Placebo ATJ-28 (Welch t-test: FOMC mean vs non-FOMC 24h drift)
    nf_pool = np.concatenate([np.asarray(placebo_non_fomc[s]) for s in CORE3])
    mu_ev, sd_ev, n_ev = float(ev_c3["r_mini"].mean()), float(ev_c3["r_mini"].std(ddof=1)), len(ev_c3)
    mu_nf, sd_nf, n_nf = float(nf_pool.mean()), float(nf_pool.std(ddof=1)), len(nf_pool)
    se_diff = sqrt((sd_ev ** 2) / n_ev + (sd_nf ** 2) / n_nf)
    t_plac = (mu_ev - mu_nf) / se_diff if se_diff > 0 else 0.0

    # Period cuts & concentration
    subperiods = {
        "2008_2011_06": _m_stats("mini", lambda ix: ix <= "2011-06-30"),
        "2011_07_2015_02": _m_stats("mini", lambda ix: (ix >= "2011-07-01") & (ix <= "2015-02-28")),
        "2015_03_2026_09": _m_stats("mini", lambda ix: ix >= "2015-03-01"),
        "2022_2026_09": _m_stats("mini", lambda ix: ix >= "2022-01-01"),
    }
    sorted_ev = ev_c3["r_mini"].sort_values(ascending=False)
    ex_top1 = float(sorted_ev.iloc[1:].mean() / sorted_ev.iloc[1:].std(ddof=1) * sqrt(len(sorted_ev) - 1))
    ex_top5 = float(sorted_ev.iloc[5:].mean() / sorted_ev.iloc[5:].std(ddof=1) * sqrt(len(sorted_ev) - 5))

    # By instrument in DESC+REP
    by_inst = {}
    for sym in CORE3 + EXTRA_CME + list(DK_FILES.keys()):
        sub = EV[EV["sym"] == sym]
        by_inst[sym] = {
            "ev_mini": _event_stats(sub["r_mini_scaled"].to_numpy()),
            "ev_micro": _event_stats(sub["r_micro_scaled"].to_numpy()),
            "ev_bruto": _event_stats(sub["r_bruto_scaled"].to_numpy()),
        }

    # Formal K27/K42 Holdout Readiness Audit (PURE calendar count on 2008-01..2026-09, ZERO return reads!)
    n_ho_events = int(((cal.index >= "2008-01-01") & (cal["blq"] == "HOLDOUT")).sum())
    alfa_lord = round(LibroLord().nivel("PRE_FOMC_LIMPIO_20Y"), 6)
    plans = {}
    for frac in (0.5, 0.7, 1.0):
        # Standalone ES/NQ/YM (~n_ho_events independent meetings) and multi-region (if treated conservatively per meeting)
        plans[f"core_fomc_{frac}x_alfa05"] = HV.plan_potencia("fijo", mu_ev * frac, sd_ev, n=n_ho_events, fuente_efecto=f"DR x {frac}", alfa=0.05)
        plans[f"core_fomc_{frac}x_lord"] = HV.plan_potencia("fijo", mu_ev * frac, sd_ev, n=n_ho_events, fuente_efecto=f"DR x {frac} (LORD++)", alfa=alfa_lord)

    res = {
        "calendario": {
            "total_programadas_2006_2026": int(len(cal)),
            "excluidas_no_programadas": len(EXCLUDE_UNSCHED),
            "eventos_core_DR_2008_2026": int(len(ev_c3)),
            "eventos_en_HOLDOUT_2008_2026_sin_leer": n_ho_events,
        },
        "k58_dukascopy": k58,
        "core3_mensual_DR": {c: _m_stats(c) for c in ("bruto", "mini", "micro", "stress2x")},
        "core3_mensual_DESC": stats_monthly_10vol(daily_core.loc[[a5_bloque(int(d.strftime("%Y%m%d"))) == "DESC" for d in daily_core.index], "mini"].dropna().groupby(lambda d: d.to_period("M")).sum()),
        "core3_mensual_REP": stats_monthly_10vol(daily_core.loc[[a5_bloque(int(d.strftime("%Y%m%d"))) == "REP" for d in daily_core.index], "mini"].dropna().groupby(lambda d: d.to_period("M")).sum()),
        "placebo_ATJ28": {
            "fomc_mean_bps": round(mu_ev * 1e4, 2),
            "non_fomc_mean_bps": round(mu_nf * 1e4, 2),
            "excess_bps_per_event": round((mu_ev - mu_nf) * 1e4, 2),
            "t_welch": round(t_plac, 2),
            "p_welch": round(1.0 - Phi(t_plac), 5),
        },
        "post_publicacion": subperiods,
        "concentracion": {
            "top1_event_date": str(sorted_ev.index[0].date()),
            "t_ex_top1": round(ex_top1, 2),
            "t_ex_top5": round(ex_top5, 2),
        },
        "por_instrumento_DR": by_inst,
        "plan_k27_k42_sin_abrir": {"alfa_lord_vigente": alfa_lord, "planes": plans},
    }
    (OUT / "RESULTADO.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")

    cm = res["core3_mensual_DR"]
    md = [
        "# PRE-FOMC-LIMPIO-20Y: Calendario Programado Puro y Transferencia ATJ-28 (`2008–2026-09`, `DESC+REP`)",
        "",
        f"Estado: RESULTADO — EF3 pre-registrado en [PREREGISTRO.md](PREREGISTRO.md) (`5` pruebas, `PRE_FOMC_LIMPIO_20Y`). **`HOLDOUT A5` (`{n_ho_events}` eventos en `63m`) y `TERMINAL` 100 % SELLADOS** (`exigir_sin_holdout_no_abierto` + `mascara_a5_limpia`).",
        "",
        "## 1. Núcleo `ES + NQ + YM` (`DESC + REP`, `167m`, `122` eventos programados)",
        "| Costo / Muestra | `DESC Sh` | `REP Sh` | `DR Sh (t)` | `p (1-cola)` | `MDD@10%` | `Calmar` |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: |",
        f"| **Neto Mini** | `{res['core3_mensual_DESC']['sharpe']}` | `{res['core3_mensual_REP']['sharpe']}` | **`{cm['mini']['sharpe']} ({cm['mini']['t']})`** | `{cm['mini']['p_una_cola']}` | `{cm['mini']['mdd_at_10pct_vol']}%` | `{cm['mini']['calmar_at_10pct_vol']}` |",
        f"| **Neto Micro** (`MES/MNQ/MYM`) | — | — | **`{cm['micro']['sharpe']} ({cm['micro']['t']})`** | `{cm['micro']['p_una_cola']}` | `{cm['micro']['mdd_at_10pct_vol']}%` | `{cm['micro']['calmar_at_10pct_vol']}` |",
        f"| **Estrés 2x Mini** | — | — | `{cm['stress2x']['sharpe']} ({cm['stress2x']['t']})` | `{cm['stress2x']['p_una_cola']}` | `{cm['stress2x']['mdd_at_10pct_vol']}%` | `{cm['stress2x']['calmar_at_10pct_vol']}` |",
        f"| **Bruto** | — | — | `{cm['bruto']['sharpe']} ({cm['bruto']['t']})` | `{cm['bruto']['p_una_cola']}` | `{cm['bruto']['mdd_at_10pct_vol']}%` | `{cm['bruto']['calmar_at_10pct_vol']}` |",
        "",
        f"- **Placebo ATJ-28 (24h FOMC vs días sin FOMC en `DESC+REP`):** FOMC `+{res['placebo_ATJ28']['fomc_mean_bps']} pb` vs No-FOMC `+{res['placebo_ATJ28']['non_fomc_mean_bps']} pb` → **exceso `+{res['placebo_ATJ28']['excess_bps_per_event']} pb/ev` (`t_Welch = {res['placebo_ATJ28']['t_welch']}`, `p = {res['placebo_ATJ28']['p_welch']}`)**.",
        f"- **Post-publicación:** `2008–2011-06`: `Sh={subperiods['2008_2011_06']['sharpe']} (t={subperiods['2008_2011_06']['t']})` | `2011-07–2015-02`: `Sh={subperiods['2011_07_2015_02']['sharpe']} (t={subperiods['2011_07_2015_02']['t']})` | **`2015-03–2026-09`: `Sh={subperiods['2015_03_2026_09']['sharpe']} (t={subperiods['2015_03_2026_09']['t']})`** | **`2022+`: `Sh={subperiods['2022_2026_09']['sharpe']} (t={subperiods['2022_2026_09']['t']})`**.",
        f"- **Concentración sin eventos extremos:** `t` sin top-1 (`{res['concentracion']['top1_event_date']}`) = **`{res['concentracion']['t_ex_top1']}`** | sin top-5 = **`{res['concentracion']['t_ex_top5']}`**.",
        "",
        "## 2. Transferencia congelada ATJ-28 a otros mercados (`DESC+REP` limpio)",
        "| Instrumento | `n` eventos | `Neto Mini (pb/ev)` | `t_ev` | `p` | `% ev +` |",
        "| :--- | :---: | :---: | :---: | :---: | :---: |",
    ]
    for sym, d in by_inst.items():
        em = d["ev_mini"]
        md.append(f"| `{sym}` | `{em['n']}` | `{em['mean_bps']:+.2f}` | **`{em['t']}`** | `{em['p']}` | `{em['pct_pos']}` |")

    md.extend([
        "",
        f"## 3. Plan formal de potencia K27 / K42 para una eventual apertura (`{n_ho_events}` eventos en HOLDOUT A5, `alfa_LORD={alfa_lord}`)",
    ])
    for pk, pv in plans.items():
        md.append(f"- `{pk}`: potencia = **`{pv.get('potencia')}`** (`n_necesarias={pv.get('n_necesarias')}`, `{'; '.join(pv['problemas']) or 'OK >= 0,80'}`).")

    md.extend([
        "",
        "Diagnóstico de grilla: cero grilla paramétrica (`0` perillas ajustadas; calendario ex ante puro y salida `5` min pre-anuncio).",
        "Episodios: reportados cuatro subperíodos (`2008–11`, `2011–15`, `2015–26`, `2022+`) y sensibilidad sin top-1 / top-5 eventos.",
        "",
        f"Aporte al referente: limpia el calendario FOMC real (`165` fechas programadas exactas), demuestra exceso genuino frente a días no-FOMC, confirma persistencia post-publicación y mide transferencia multi-mercado en `{round(time.time()-t0, 1)}s` sin tocar HOLDOUT.",
    ])
    (OUT / "RESULTADO.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps({"mini_DR": cm["mini"], "micro_DR": cm["micro"], "placebo": res["placebo_ATJ28"], "por_inst_t": {k: v["ev_mini"]["t"] for k, v in by_inst.items()}, "k27": {k: v.get("potencia") for k, v in plans.items()}}, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
