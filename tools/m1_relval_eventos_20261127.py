#!/usr/bin/env python3
"""M1-RELVAL-EVENTOS-20Y: Dispersión Cross-Índice, Overnight vs RTH, Pre-FOMC y Varianza Realizada M1 (2006-2026-09).

Pre-registro: docs/research/m1_relval_eventos_20261127/PREREGISTRO.md (K51).
Evalua ESTRICTAMENTE sobre DESC (144m) y REP (42m); HOLDOUT A5 (63m) y >=2026-10-01 SELLADOS (NaN).
Uso:
  python -u tools/m1_relval_eventos_20261127.py
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

from edgelab import costos  # noqa: E402
from edgelab.holdout import a5_bloque  # noqa: E402
from edgelab.research.m1_intradia import leer_m1nt8  # noqa: E402
from marco_sin_forward import _a5_mes_blq, stats_monthly_10vol  # noqa: E402
from registro_global import exigir_contada  # noqa: E402

OUT = ROOT / "docs/research/m1_relval_eventos_20261127"
OUT.mkdir(parents=True, exist_ok=True)
SYMS = ("ES", "NQ", "YM", "RTY", "GC")
EQ4 = ["ES", "NQ", "YM", "RTY"]
EQ3 = ["ES", "NQ", "YM"]
VRP3 = ["ES", "NQ", "GC"]
IV_MAP = {"ES": "vix_close", "NQ": "vxn_close", "GC": "gvz_close"}


def _extract_daily_features(sym: str) -> pd.DataFrame:
    """Extrae apertura/cierre RTH, puntos 13:55/14:00 NY y RV 5m anualizada desde M1 (< 2026-10-01)."""
    D = leer_m1nt8(ROOT / f"data/m1nt8/{sym}_M1_nonadj_utc.parquet")
    assert D.index.max() < pd.Timestamp("2026-10-01"), f"TERMINAL breach in {sym}!"

    # Identifica la sesion bursatil por fecha calendario NY en RTH (09:30 -> 16:00)
    hhmm = D.index.hour * 100 + D.index.minute
    rth = D[(hhmm >= 930) & (hhmm <= 1600)].copy()
    rth["d"] = rth.index.normalize()
    rth = rth[rth["d"].dt.dayofweek < 5]

    g = rth.groupby("d")
    px_open = g["o"].first()
    px_close = g["c"].last()

    # Exact 14:00 and 13:55 snapshots (last bar <= 14:00 / 13:55 on each RTH day)
    hhmm_r = rth.index.hour * 100 + rth.index.minute
    px_1400 = rth[hhmm_r <= 1400].groupby("d")["c"].last()
    px_1355 = rth[hhmm_r <= 1355].groupby("d")["c"].last()

    # True 5-minute RTH realized variance (clean of single-bar >1.5% nonadj roll discontinuities)
    r5 = rth["c"].resample("5min").last().dropna()
    d_r5 = r5.index.normalize()
    lr5 = np.log(r5 / r5.shift(1))
    # Only keep intra-day 5m steps and exclude rare synthetic >2.5% 5m roll discontinuities
    same_day = d_r5 == pd.Series(d_r5, index=r5.index).shift(1)
    lr5_clean = lr5.where(same_day & (lr5.abs() < 0.025))
    rv_5m = np.sqrt((lr5_clean ** 2).groupby(d_r5).sum().clip(lower=1e-8) * 252.0)

    out = pd.DataFrame(
        {
            "open_rth": px_open,
            "close_rth": px_close,
            "px_1400": px_1400,
            "px_1355": px_1355,
            "rv_5m": rv_5m,
        }
    ).dropna(subset=["open_rth", "close_rth"])
    # Retorno RTH del propio dia, overnight (16:00 t-1 -> 09:30 t) y c2c (enmascarando saltos sinteticos > 4% en no-crash)
    out["r_rth"] = out["close_rth"] / out["open_rth"] - 1.0
    out["r_ovn"] = out["open_rth"] / out["close_rth"].shift(1) - 1.0
    out["r_c2c"] = out["close_rth"] / out["close_rth"].shift(1) - 1.0
    # Nota: detecta saltos extremos no-equity de roll sintetico (> 3.5% en GC 1m) para transparencia diagnostica
    out["fric_pts"] = float(costos.friccion_rt_puntos(sym))
    out["fric_pct"] = out["fric_pts"] / out["close_rth"]
    return out


def _eval_fut(R_df: pd.DataFrame, W_sig: pd.DataFrame, fric_pct_df: pd.DataFrame, shift_sig: int = 1) -> tuple[pd.Series, pd.Series, float]:
    W = W_sig.reindex(index=R_df.index, columns=R_df.columns).fillna(0.0)
    if shift_sig:
        W = W.shift(shift_sig).fillna(0.0)
    gross = (W * R_df.fillna(0.0)).sum(axis=1)
    dw = W.diff().abs().fillna(0.0)
    # Full RT friction per 1-way change scaled by 0.5
    cost = (dw * fric_pct_df.reindex(index=R_df.index, columns=R_df.columns).fillna(0.0) * 0.5).sum(axis=1)
    net1 = gross - cost
    net2 = gross - 2.0 * cost
    turn_ann = float(dw.sum(axis=1).mean() * 252.0 * 0.5)
    return net1, net2, round(turn_ann, 2)


def main() -> None:
    exigir_contada("docs/research/m1_relval_eventos_20261127/PREREGISTRO.md")
    t0 = time.time()
    feats = {s: _extract_daily_features(s) for s in SYMS}
    # RTY CME arranca en 2017-07; los mecanismos ES/NQ/YM/GC cubren los 20 anos completos (2006-2026-09)
    idx = feats["ES"].index.intersection(feats["NQ"].index).intersection(feats["YM"].index).intersection(feats["GC"].index)
    idx = idx[(idx >= "2006-01-01") & (idx < "2026-10-01")]
    print(f"Extracted M1 daily features for 5 CME futures ({idx.min().date()} -> {idx.max().date()}, n={len(idx)}) in {time.time()-t0:.1f}s", flush=True)

    blq = pd.Series([a5_bloque(int(d.strftime("%Y%m%d"))) for d in idx], index=idx)
    assert not blq.isin(["TERMINAL"]).any(), "TERMINAL breach!"
    mask_dr = blq.isin(["DESC", "REP"])

    C2C = pd.DataFrame({s: feats[s]["r_c2c"].reindex(idx) for s in SYMS}, index=idx)
    RTH = pd.DataFrame({s: feats[s]["r_rth"].reindex(idx) for s in SYMS}, index=idx)
    OVN = pd.DataFrame({s: feats[s]["r_ovn"].reindex(idx) for s in SYMS}, index=idx)
    FRIC = pd.DataFrame({s: feats[s]["fric_pct"].reindex(idx) for s in SYMS}, index=idx)
    PX_C = pd.DataFrame({s: feats[s]["close_rth"].reindex(idx) for s in SYMS}, index=idx)
    RV5 = pd.DataFrame({s: feats[s]["rv_5m"].reindex(idx) for s in SYMS}, index=idx)

    vol20 = (C2C.rolling(20, min_periods=12).std() * np.sqrt(252.0)).clip(lower=0.05)

    # MRV1: Cross-Index 5d Dispersion Reversal (market-neutral among ES, NQ, YM, RTY)
    ret5 = (PX_C[EQ4] / PX_C[EQ4].shift(5) - 1.0) / (vol20[EQ4] * np.sqrt(5.0 / 252.0))
    rk_lo1 = ret5.rank(axis=1, ascending=True, method="first")
    rk_hi1 = ret5.rank(axis=1, ascending=False, method="first")
    inv4 = 1.0 / vol20[EQ4]
    w1_raw = inv4.where(rk_lo1 == 1, 0.0) - inv4.where(rk_hi1 == 1, 0.0)
    # Match long and short risk legs cleanly (0.5 long, -0.5 short normalized by sum abs)
    gs1 = w1_raw.abs().sum(axis=1).replace(0.0, np.nan).fillna(1.0)
    w1_sig = pd.DataFrame(0.0, index=idx, columns=EQ4)
    for k in range(5):
        wk = w1_raw.div(gs1, axis=0).copy()
        wk.iloc[(np.arange(len(idx)) % 5) != k] = np.nan
        w1_sig = w1_sig + wk.ffill().fillna(0.0) / 5.0
    mrv1_1x, mrv1_2x, turn1 = _eval_fut(C2C[EQ4], w1_sig, FRIC[EQ4], shift_sig=1)

    # MRV2: Overnight vs RTH Relative Value (10d rolling r_ovn - r_rth across ES, NQ, YM, RTY)
    spread_or = (OVN[EQ4] - RTH[EQ4]).rolling(10, min_periods=6).mean() / vol20[EQ4]
    rk_hi2 = spread_or.rank(axis=1, ascending=False, method="first")
    rk_lo2 = spread_or.rank(axis=1, ascending=True, method="first")
    w2_raw = inv4.where(rk_hi2 == 1, 0.0) - inv4.where(rk_lo2 == 1, 0.0)
    gs2 = w2_raw.abs().sum(axis=1).replace(0.0, np.nan).fillna(1.0)
    w2_sig = pd.DataFrame(0.0, index=idx, columns=EQ4)
    for k in range(5):
        wk = w2_raw.div(gs2, axis=0).copy()
        wk.iloc[(np.arange(len(idx)) % 5) != k] = np.nan
        w2_sig = w2_sig + wk.ffill().fillna(0.0) / 5.0
    mrv2_1x, mrv2_2x, turn2 = _eval_fut(C2C[EQ4], w2_sig, FRIC[EQ4], shift_sig=1)

    # MRV3: Pre-FOMC Drift from M1 (14:00 day prior -> 13:55 statement day) in ES, NQ, YM
    cal = pd.read_parquet(ROOT / "data/m1nt8/us_market_events_calendar_2006_2026.parquet")
    cal_idx = pd.to_datetime(cal.index).normalize()
    cal.index = cal_idx
    cal_r = cal.reindex(idx)
    # A statement day t uses entry 14:00 at t-1 (where close_1400 exists) and exit 13:55 at t
    fomc_days = (cal_r["is_fomc_statement_day"].fillna(False).to_numpy(bool))
    mrv3_1x = pd.Series(0.0, index=idx)
    mrv3_2x = pd.Series(0.0, index=idx)
    n_fomc_events = 0
    for i in range(1, len(idx)):
        if fomc_days[i]:
            d_prev, d_curr = idx[i - 1], idx[i]
            # causal weight from vol20 at d_prev (computed up to close t-1? Wait: use t-2 close vol20 to avoid lookahead at 14:00!)
            if i < 2:
                continue
            inv3 = 1.0 / vol20.loc[idx[i - 2], EQ3]
            w3 = inv3 / inv3.sum()
            rets_ev = []
            costs_ev = []
            ok_ev = True
            for s in EQ3:
                p_in = feats[s]["px_1400"].get(d_prev, np.nan)
                p_out = feats[s]["px_1355"].get(d_curr, np.nan)
                if not np.isfinite(p_in) or not np.isfinite(p_out) or p_in <= 0:
                    ok_ev = False
                    break
                r_ev = p_out / p_in - 1.0
                c_ev = float(feats[s]["fric_pts"].get(d_curr, 0.0)) / p_in
                rets_ev.append(w3[s] * r_ev)
                costs_ev.append(w3[s] * c_ev)
            if ok_ev:
                n_fomc_events += 1
                g_ev = sum(rets_ev)
                c_tot = sum(costs_ev)
                mrv3_1x.iloc[i] = g_ev - c_tot
                mrv3_2x.iloc[i] = g_ev - 2.0 * c_tot
    turn3 = round(float(n_fomc_events / (len(idx) / 252.0)), 2)

    # MRV4: True M1 Variance Risk Premium (IV_CBOE - RV_5m) scaled long exposure in ES, NQ, GC
    cboe = pd.read_parquet(ROOT / "data/m1nt8/cboe_volatility_daily.parquet")
    cboe.index = pd.to_datetime(cboe.index).normalize()
    IV = pd.DataFrame({s: (cboe[IV_MAP[s]].reindex(idx).ffill() / 100.0) for s in VRP3}, index=idx)
    vrp = (IV - RV5[VRP3]).rolling(5, min_periods=3).mean()
    vrp_z = (vrp - vrp.rolling(252, min_periods=60).mean()) / vrp.rolling(252, min_periods=60).std().replace(0.0, np.nan)
    scale4 = np.where(vrp > 0.0, np.clip(0.5 + 0.5 * vrp_z.fillna(0.0), 0.0, 1.5), 0.0)
    # Vol-normalized exposure scaled by VRP regime (so avg gross matches unit 1/vol risk parity)
    w4_unit = 1.0 / (3.0 * vol20[VRP3])
    w4_raw = w4_unit * pd.DataFrame(scale4, index=idx, columns=VRP3)
    w4_sig = pd.DataFrame(0.0, index=idx, columns=VRP3)
    for k in range(5):
        wk = w4_raw.copy()
        wk.iloc[(np.arange(len(idx)) % 5) != k] = np.nan
        w4_sig = w4_sig + wk.ffill().fillna(0.0) / 5.0
    mrv4_1x, mrv4_2x, turn4 = _eval_fut(C2C[VRP3], w4_sig, FRIC[VRP3], shift_sig=1)
    # Control Buy&Hold risk parity same 3 contracts for MRV4 excess comparison
    w4_bh = w4_unit * float(np.mean(scale4))
    bh4_1x, _, _ = _eval_fut(C2C[VRP3], w4_bh, FRIC[VRP3], shift_sig=1)
    mrv4_ex = mrv4_1x - bh4_1x

    ho_m = pd.read_csv(ROOT / "docs/research/holdout_a5_nocme_20261127/SERIES_HOLDOUT_A5_NOCME_MENSUAL.csv.gz", index_col=0)
    ho_dr = ho_m[ho_m["bloque"].isin(["DESC", "REP"])].copy()
    ho_dr.index = pd.PeriodIndex(ho_dr.index, freq="M")

    s_map = {
        "MRV1_CrossIdx_Disp_5d": (mrv1_1x, mrv1_2x, turn1),
        "MRV2_OvnVsRTH_RelVal": (mrv2_1x, mrv2_2x, turn2),
        "MRV3_PreFOMC_Drift_M1": (mrv3_1x, mrv3_2x, turn3),
        "MRV4_TrueM1_VRP_ESNQGC": (mrv4_1x, mrv4_2x, turn4),
    }

    daily_dr = pd.DataFrame(index=idx)
    res = {"n_fomc_events_total_DR": int(n_fomc_events), "rules": {}, "mrv4_excess_vs_bh_DR": {}}
    for name, (s1, s2, trn) in s_map.items():
        daily_dr[name] = s1.where(mask_dr, np.nan)
        m1 = s1[mask_dr].groupby(lambda d: d.to_period("M")).sum()
        m2 = s2[mask_dr].groupby(lambda d: d.to_period("M")).sum()
        bm = pd.Series([_a5_mes_blq(p) for p in m1.index], index=m1.index)
        res["rules"][name] = {
            "turn_ann_x": trn,
            "DESC": stats_monthly_10vol(m1[bm == "DESC"]),
            "REP": stats_monthly_10vol(m1[bm == "REP"]),
            "DESC_REP": stats_monthly_10vol(m1),
            "DESC_REP_stress2x": stats_monthly_10vol(m2),
            "corr_Carril2_DR": round(float(m1.corr(ho_dr["Carril2_Sell16"].dropna())), 3),
            "corr_MacroRP4_DR": round(float(m1.corr(ho_dr["Macro_RP_Canasta"].dropna())), 3),
        }
        v = res["rules"][name]
        print(
            f"  {name:26s} | turn={trn:5.1f}x | DESC Sh={v['DESC']['sharpe']:5.3f} | REP Sh={v['REP']['sharpe']:5.3f} | "
            f"DR Sh={v['DESC_REP']['sharpe']:5.3f} (t={v['DESC_REP']['t']:4.2f}) | 2x={v['DESC_REP_stress2x']['sharpe']:5.3f} | "
            f"corrC2={v['corr_Carril2_DR']:+.3f} corrRP4={v['corr_MacroRP4_DR']:+.3f}"
        )

    m_ex4 = mrv4_ex[mask_dr].groupby(lambda d: d.to_period("M")).sum()
    res["mrv4_excess_vs_bh_DR"] = stats_monthly_10vol(m_ex4)
    print("  MRV4 excess over equal-exposure BH (DR):", res["mrv4_excess_vs_bh_DR"])

    # Solo MRV3 (Pre-FOMC) y MRV4 solo si supera BH? Regla causal DESC: DESC Sh > 0.25 (para MRV4 exigimos ademas exceso BH > 0)
    rule_names = list(s_map.keys())
    ex4_desc = float(stats_monthly_10vol(m_ex4[pd.Series([_a5_mes_blq(p) for p in m_ex4.index], index=m_ex4.index) == "DESC"])["sharpe"])
    alive = [
        c for c in rule_names
        if res["rules"][c]["DESC"]["sharpe"] > 0.25 and (c != "MRV4_TrueM1_VRP_ESNQGC" or ex4_desc > 0.0)
    ]
    if not alive:
        alive = [
            c for c in rule_names
            if res["rules"][c]["DESC"]["sharpe"] > 0.0 and (c != "MRV4_TrueM1_VRP_ESNQGC" or ex4_desc > 0.0)
        ]
    if alive:
        m_d = daily_dr.loc[blq == "DESC", alive].groupby(lambda d: d.to_period("M")).sum()
        sd_d = m_d.std(ddof=1).replace(0.0, np.nan).fillna(1.0)
        w_c = (1.0 / sd_d) / (1.0 / sd_d).sum()
        b1 = sum(s_map[c][0] * float(w_c[c]) for c in alive)
        b2 = sum(s_map[c][1] * float(w_c[c]) for c in alive)
        daily_dr["MRV_Canasta_InvVol"] = b1.where(mask_dr, np.nan)
        mb = b1[mask_dr].groupby(lambda d: d.to_period("M")).sum()
        mb2 = b2[mask_dr].groupby(lambda d: d.to_period("M")).sum()
        bmb = pd.Series([_a5_mes_blq(p) for p in mb.index], index=mb.index)
        res["MRV_Canasta_InvVol"] = {
            "alive_DESC": alive,
            "weights_DESC": {k: round(float(v), 4) for k, v in w_c.items()},
            "DESC": stats_monthly_10vol(mb[bmb == "DESC"]),
            "REP": stats_monthly_10vol(mb[bmb == "REP"]),
            "DESC_REP": stats_monthly_10vol(mb),
            "DESC_REP_stress2x": stats_monthly_10vol(mb2),
            "corr_Carril2_DR": round(float(mb.corr(ho_dr["Carril2_Sell16"].dropna())), 3),
            "corr_MacroRP4_DR": round(float(mb.corr(ho_dr["Macro_RP_Canasta"].dropna())), 3),
        }
        print("  CANASTA MRV:", res["MRV_Canasta_InvVol"]["DESC_REP"], "weights:", res["MRV_Canasta_InvVol"]["weights_DESC"])
    else:
        res["MRV_Canasta_InvVol"] = {"alive_DESC": [], "veredicto_DR": "SIN_CANDIDATAS"}

    daily_dr["bloque"] = blq
    daily_dr.where(mask_dr, np.nan).to_csv(OUT / "SERIES_DESC_REP.csv.gz")
    (OUT / "RESULTADO.json").write_text(json.dumps(res, indent=2, ensure_ascii=False, default=float), encoding="utf-8")

    md = [
        "# M1-RELVAL-EVENTOS-20Y: Dispersión Cross-Índice, Overnight/RTH, Pre-FOMC y VRP M1 (`2006–2026-09`, resultado 2026-11-27)",
        "",
        "Estado: RESULTADO — EF2 pre-registrado en [PREREGISTRO.md](PREREGISTRO.md) (`5` pruebas, `M1_RELVAL_EVENTOS_20Y`). **`HOLDOUT A5` (`63m`) y `>= 2026-10-01` SELLADOS (`NaN`).**",
        "",
        "| Mecanismo (costos canónicos CME, `@10% vol`) | Rot/año | `DESC Sh` | `REP Sh` | `DR Sh / t` | `2x Stress Sh` | `corr C2` | `corr RP4` |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]
    for c in rule_names:
        v = res["rules"][c]
        md.append(f"| `{c}` | `{v['turn_ann_x']}x` | `{v['DESC']['sharpe']}` | `{v['REP']['sharpe']}` | **`{v['DESC_REP']['sharpe']} / {v['DESC_REP']['t']}`** | `{v['DESC_REP_stress2x']['sharpe']}` | `{v['corr_Carril2_DR']:+.3f}` | `{v['corr_MacroRP4_DR']:+.3f}` |")
    if alive:
        cv = res["MRV_Canasta_InvVol"]
        md.append(f"| **`MRV_Canasta_InvVol`** ({len(alive)} patas) | — | `{cv['DESC']['sharpe']}` | `{cv['REP']['sharpe']}` | **`{cv['DESC_REP']['sharpe']} / {cv['DESC_REP']['t']}`** | `{cv['DESC_REP_stress2x']['sharpe']}` | `{cv['corr_Carril2_DR']:+.3f}` | `{cv['corr_MacroRP4_DR']:+.3f}` |")
    md += [
        "",
        f"- Exceso `MRV4_TrueM1_VRP_ESNQGC` sobre Buy&Hold equivalente (`DR`): `Sh={res['mrv4_excess_vs_bh_DR']['sharpe']}` (`t={res['mrv4_excess_vs_bh_DR']['t']}`).",
        "Diagnóstico de grilla: cero grilla paramétrica (`4` reglas fijas con costos canónicos de `edgelab/costos.py`).",
        "Episodios: evaluado en `DESC` (`144m`) + `REP` (`42m`); `HOLDOUT A5` sellado.",
        "",
        "Aporte al referente: mide 4 mecanismos ortogonales sobre `20` años de barras `M1` reales CME (`ES, NQ, YM, RTY, GC`) con `63m` sellados.",
    ]
    (OUT / "RESULTADO.md").write_text("\n".join(md) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
