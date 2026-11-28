#!/usr/bin/env python3
"""MACRO-CTA-VRP-20Y: Tendencia Multi-Horizonte No-Equity, Term Structure VIX/VIX3M, Tasas Reales y Vol-Managed (2006-2026-09).

Pre-registro: docs/research/macro_cta_vrp_20261127/PREREGISTRO.md (K51).
Evalua ESTRICTAMENTE sobre DESC (144m) y REP (42m); HOLDOUT A5 (63m) y >=2026-10-01 SELLADOS (NaN).
Uso:
  python -u tools/macro_cta_vrp_20261127.py
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
from marco_sin_forward import _a5_mes_blq, stats_monthly_10vol  # noqa: E402
import macro_risk_premia_20261127 as MRP  # noqa: E402
from registro_global import exigir_contada  # noqa: E402

OUT = ROOT / "docs/research/macro_cta_vrp_20261127"
OUT.mkdir(parents=True, exist_ok=True)
NONEQ_15 = ["SHY", "IEI", "IEF", "TLT", "TIP", "LQD", "HYG", "GLD", "SLV", "USO", "DBC", "UUP", "FXE", "FXY", "FXB", "FXA"]
MM_5 = ["TLT", "IEF", "GLD", "DBC", "HYG"]


def compute_mvc_daily() -> dict:
    # Load cached ETFs + yields, plus fetch ^VIX3M (strictly < 2026-10-01)
    syms = sorted(set(MRP.ALL_SYMS + ["^VIX3M"]))
    series_map = {}
    for s in syms:
        _, ser, _ = MRP._fetch_one(s)
        if ser is not None and len(ser) > 0:
            series_map[s] = ser
    P = pd.DataFrame(series_map).sort_index()
    P = P[P.index < MRP.CORTE]

    cboe = pd.read_parquet(ROOT / "data/m1nt8/cboe_volatility_daily.parquet")
    vix = cboe["vix_close"].reindex(P.index).ffill()
    vix3m = P["^VIX3M"].reindex(P.index).ffill()

    px_cols = [c for c in P.columns if not c.startswith("^")]
    PX = P[px_cols].copy()
    R = PX.pct_change()
    vol21 = (R.rolling(21, min_periods=15).std() * np.sqrt(252.0)).clip(lower=0.025)

    # MVC1: Multi-horizon CTA trend (21, 63, 126, 252) strictly in non-equity ETFs
    sig1 = pd.DataFrame(0.0, index=PX.index, columns=NONEQ_15)
    for h in (21, 63, 126, 252):
        z = (PX[NONEQ_15] / PX[NONEQ_15].shift(h) - 1.0) / (vol21[NONEQ_15] * np.sqrt(h / 252.0)).clip(lower=0.01)
        sig1 = sig1 + np.tanh(z.fillna(0.0) / 1.5) / 4.0
    w1_raw = sig1 / vol21[NONEQ_15]
    w1 = MRP._stagger_weights(w1_raw.div(w1_raw.abs().sum(axis=1).replace(0.0, np.nan).fillna(1.0), axis=0), 5)

    # MVC2: VIX / VIX3M term-structure Risk-On (SPY+HYG) vs Safe-Haven (TLT+GLD)
    ts = (vix / vix3m).rolling(3, min_periods=1).mean()
    # Contango (<0.96) -> +1 (long Risk-On / short Safe-Haven); Backwardation (>1.02) -> -1 (long Safe-Haven / short SPY)
    sc_ts = ((0.99 - ts) / 0.04).clip(-1.0, 1.0).fillna(0.0)
    w2_raw = pd.DataFrame(0.0, index=PX.index, columns=PX.columns)
    for dt_i, v in sc_ts.items():
        if v >= 0.0:
            w2_raw.loc[dt_i, ["SPY", "HYG"]] = 0.25 * v
            w2_raw.loc[dt_i, ["TLT", "GLD"]] = -0.25 * v
        else:
            w2_raw.loc[dt_i, ["TLT", "GLD"]] = 0.25 * (-v)
            w2_raw.loc[dt_i, "SPY"] = -0.50 * (-v)
    w2 = MRP._stagger_weights(w2_raw, 5)

    # MVC3: Rates slope (^TNX - ^IRX) + Real-yield proxy (TIP/IEF -> GLD vs UUP)
    slope = (P["^TNX"] - P["^IRX"]).ffill()
    tip_ief = (PX["TIP"] / PX["IEF"]).pct_change(63).fillna(0.0)
    w3_raw = pd.DataFrame(0.0, index=PX.index, columns=PX.columns)
    up_sl = slope > 0.25
    inv_sl = slope < 0.0
    w3_raw.loc[up_sl, ["IEF", "TLT"]] += 0.125
    w3_raw.loc[up_sl, "SHY"] -= 0.25
    w3_raw.loc[inv_sl, "SHY"] += 0.25
    w3_raw.loc[inv_sl, ["IEF", "TLT"]] -= 0.125
    infl_up = tip_ief > 0.0
    w3_raw.loc[infl_up, "GLD"] += 0.25
    w3_raw.loc[infl_up, "UUP"] -= 0.25
    w3_raw.loc[~infl_up, "UUP"] += 0.25
    w3_raw.loc[~infl_up, "GLD"] -= 0.25
    gs3 = w3_raw.abs().sum(axis=1).replace(0.0, np.nan).fillna(1.0)
    w3 = MRP._stagger_weights(w3_raw.div(gs3, axis=0), 5)

    # MVC4: Moreira-Muir Vol-Managed Non-Equity Risk Parity (1/var_21d scaled relative to rolling mean 252d)
    var21 = (R[MM_5].rolling(21, min_periods=15).var() * 252.0).clip(lower=0.001)
    inv_var = 1.0 / var21
    rel_scale = (inv_var / inv_var.rolling(252, min_periods=63).mean()).clip(0.25, 2.0).fillna(1.0)
    inv_v5 = 1.0 / vol21[MM_5]
    w4_base = (inv_v5 * rel_scale)
    w4 = MRP._stagger_weights(w4_base.div(w4_base.abs().sum(axis=1).replace(0.0, np.nan).fillna(1.0), axis=0), 5)

    # Static 1/vol reference for comparison
    w4_stat = MRP._stagger_weights(inv_v5.div(inv_v5.abs().sum(axis=1).replace(0.0, np.nan).fillna(1.0), axis=0), 5)

    w_map = {
        "MVC1_CTA_NonEq_MultiHorizon": w1,
        "MVC2_VIX_TermStruct_FTQ": w2,
        "MVC3_Rates_RealYield_Carry": w3,
        "MVC4_MoreiraMuir_VolManaged": w4,
    }
    idx_eval = PX.index[(PX.index >= "2006-01-01") & (PX.index < MRP.CORTE)]
    blq = pd.Series([a5_bloque(int(d.strftime("%Y%m%d"))) for d in idx_eval], index=idx_eval)
    assert not blq.isin(["TERMINAL"]).any(), "TERMINAL breach!"

    raw_1x = pd.DataFrame(index=idx_eval)
    raw_2x = pd.DataFrame(index=idx_eval)
    turn_map = {}
    for name, W in w_map.items():
        s1, s2, tm = MRP._eval_weights(R, W, tx_bps=5.0, eq_borrow_bps=100.0, noneq_borrow_bps=50.0)
        raw_1x[name] = s1.reindex(idx_eval).fillna(0.0)
        raw_2x[name] = s2.reindex(idx_eval).fillna(0.0)
        turn_map[name] = tm

    s_stat, _, _ = MRP._eval_weights(R, w4_stat, tx_bps=5.0, eq_borrow_bps=100.0, noneq_borrow_bps=50.0)
    return {
        "idx_eval": idx_eval,
        "blq": blq,
        "spy": R["SPY"].reindex(idx_eval).fillna(0.0),
        "raw_1x": raw_1x,
        "raw_2x": raw_2x,
        "turn_map": turn_map,
        "mvc4_static_1vol": s_stat.reindex(idx_eval).fillna(0.0),
    }


def main() -> None:
    exigir_contada("docs/research/macro_cta_vrp_20261127/PREREGISTRO.md")
    t0 = time.time()
    core = compute_mvc_daily()
    idx_eval, blq, raw_1x, raw_2x = core["idx_eval"], core["blq"], core["raw_1x"], core["raw_2x"]
    mask_dr = blq.isin(["DESC", "REP"])
    print(f"Loaded Macro CTA/VRP ({idx_eval.min().date()} -> {idx_eval.max().date()}) in {time.time()-t0:.1f}s", flush=True)

    ho_m = pd.read_csv(ROOT / "docs/research/holdout_a5_nocme_20261127/SERIES_HOLDOUT_A5_NOCME_MENSUAL.csv.gz", index_col=0)
    ho_dr = ho_m[ho_m["bloque"].isin(["DESC", "REP"])].copy()
    ho_dr.index = pd.PeriodIndex(ho_dr.index, freq="M")

    res = {"rules": {}}
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
            "corr_SPY_DR": round(float(s1[mask_dr].corr(core["spy"][mask_dr])), 3),
        }
        v = res["rules"][c]
        print(
            f"  {c:28s} | turn={v['turn_ann_x']:4.1f}x | DESC Sh={v['DESC']['sharpe']:5.3f} | "
            f"REP Sh={v['REP']['sharpe']:5.3f} | DR Sh={v['DESC_REP']['sharpe']:5.3f} (t={v['DESC_REP']['t']:4.2f}) | "
            f"2x={v['DESC_REP_stress2x']['sharpe']:5.3f} | corrC2={v['corr_Carril2_DR']:+.3f} corrRP4={v['corr_MacroRP4_DR']:+.3f}"
        )

    m_stat = core["mvc4_static_1vol"][mask_dr].groupby(lambda d: d.to_period("M")).sum()
    res["mvc4_static_1vol_DR"] = stats_monthly_10vol(m_stat)

    rule_names = list(raw_1x.columns)
    alive = [c for c in rule_names if res["rules"][c]["DESC"]["sharpe"] > 0.25]
    if not alive:
        alive = [c for c in rule_names if res["rules"][c]["DESC"]["sharpe"] > 0.0]
    if alive:
        m_d = daily_dr.loc[blq == "DESC", alive].groupby(lambda d: d.to_period("M")).sum()
        sd_d = m_d.std(ddof=1).replace(0.0, np.nan).fillna(1.0)
        w_c = (1.0 / sd_d) / (1.0 / sd_d).sum()
        b1 = (raw_1x[alive] * w_c).sum(axis=1)
        b2 = (raw_2x[alive] * w_c).sum(axis=1)
        daily_dr["MVC_Canasta_InvVol"] = b1.where(mask_dr, np.nan)
        mb = b1[mask_dr].groupby(lambda d: d.to_period("M")).sum()
        mb2 = b2[mask_dr].groupby(lambda d: d.to_period("M")).sum()
        bmb = pd.Series([_a5_mes_blq(p) for p in mb.index], index=mb.index)
        res["MVC_Canasta_InvVol"] = {
            "alive_DESC": alive,
            "weights_DESC": {k: round(float(v), 4) for k, v in w_c.items()},
            "DESC": stats_monthly_10vol(mb[bmb == "DESC"]),
            "REP": stats_monthly_10vol(mb[bmb == "REP"]),
            "DESC_REP": stats_monthly_10vol(mb),
            "DESC_REP_stress2x": stats_monthly_10vol(mb2),
            "corr_Carril2_DR": round(float(mb.corr(ho_dr["Carril2_Sell16"].dropna())), 3),
            "corr_MacroRP4_DR": round(float(mb.corr(ho_dr["Macro_RP_Canasta"].dropna())), 3),
        }
        print("  CANASTA MVC:", res["MVC_Canasta_InvVol"]["DESC_REP"], "weights:", res["MVC_Canasta_InvVol"]["weights_DESC"])
    else:
        res["MVC_Canasta_InvVol"] = {"alive_DESC": [], "veredicto_DR": "SIN_CANDIDATAS"}

    daily_dr["bloque"] = blq
    daily_dr.where(mask_dr, np.nan).to_csv(OUT / "SERIES_DESC_REP.csv.gz")
    (OUT / "RESULTADO.json").write_text(json.dumps(res, indent=2, ensure_ascii=False, default=float), encoding="utf-8")

    md = [
        "# MACRO-CTA-VRP-20Y: CTA No-Equity, Term Structure VIX/VIX3M y Vol-Managed (`2006–2026-09`, resultado 2026-11-27)",
        "",
        "Estado: RESULTADO — EF2 pre-registrado en [PREREGISTRO.md](PREREGISTRO.md) (`5` pruebas, `MACRO_CTA_VRP_20Y`). **`HOLDOUT A5` (`63m`) y `>= 2026-10-01` SELLADOS (`NaN`).**",
        "",
        "| Mecanismo (`5 bps RT`, `@10% vol`) | Rot/año | `DESC Sh` | `REP Sh` | `DR Sh / t` | `2x Stress Sh` | `corr C2` | `corr RP4` |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]
    for c in rule_names:
        v = res["rules"][c]
        md.append(f"| `{c}` | `{v['turn_ann_x']}x` | `{v['DESC']['sharpe']}` | `{v['REP']['sharpe']}` | **`{v['DESC_REP']['sharpe']} / {v['DESC_REP']['t']}`** | `{v['DESC_REP_stress2x']['sharpe']}` | `{v['corr_Carril2_DR']:+.3f}` | `{v['corr_MacroRP4_DR']:+.3f}` |")
    if alive:
        cv = res["MVC_Canasta_InvVol"]
        md.append(f"| **`MVC_Canasta_InvVol`** ({len(alive)} patas) | — | `{cv['DESC']['sharpe']}` | `{cv['REP']['sharpe']}` | **`{cv['DESC_REP']['sharpe']} / {cv['DESC_REP']['t']}`** | `{cv['DESC_REP_stress2x']['sharpe']}` | `{cv['corr_Carril2_DR']:+.3f}` | `{cv['corr_MacroRP4_DR']:+.3f}` |")
    md += [
        "",
        f"- Referencia estática `1/vol` en `MM_5` (`DR`): `Sh={res['mvc4_static_1vol_DR']['sharpe']}` vs vol-managed `{res['rules']['MVC4_MoreiraMuir_VolManaged']['DESC_REP']['sharpe']}`.",
        "Diagnóstico de grilla: cero grilla paramétrica (`4` reglas estándar escalonadas `5d` con `shift(1)`).",
        "Episodios: evaluado en `DESC` (`144m`) + `REP` (`42m`); `HOLDOUT A5` sellado.",
        "",
        "Aporte al referente: suma mecanismos macro no-equity y de estructura temporal de volatilidad con `20+` años de historia y `63m` de holdout intactos.",
    ]
    (OUT / "RESULTADO.md").write_text("\n".join(md) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
