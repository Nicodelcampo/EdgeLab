#!/usr/bin/env python3
"""ESPIRAL-FASE2-SINTESIS: Síntesis descriptiva Multi-Frente Fase 1 + Fase 2 (estrictamente DESC+REP; HOLDOUT A5 sellado).

Cero pruebas nuevas: agrega métricas DESC+REP ya publicadas y evalúa correlación y potencia K27 en 63m sellados.
"""
from __future__ import annotations

import json
import sys
from math import erf, sqrt
from pathlib import Path
from statistics import NormalDist

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))

from marco_sin_forward import _a5_mes_blq, stats_monthly_10vol  # noqa: E402

OUT = ROOT / "docs/research/espiral_fase2_sintesis_20261127"
OUT.mkdir(parents=True, exist_ok=True)
Phi = lambda z: 0.5 * (1.0 + erf(z / sqrt(2.0)))


def _monthly_scale(s: pd.Series, target_ann_vol: float = 0.10) -> pd.Series:
    sd = float(s.std(ddof=1) * sqrt(12.0))
    return s * (target_ann_vol / sd) if sd > 0 else s


def _combo_metrics(df_m: pd.DataFrame, weights: dict[str, float]) -> dict:
    s = sum(df_m[k] * w for k, w in weights.items())
    s = _monthly_scale(s, 0.10)
    bl = pd.Series([_a5_mes_blq(p) for p in s.index], index=s.index)
    st_d = stats_monthly_10vol(s[bl == "DESC"])
    st_r = stats_monthly_10vol(s[bl == "REP"])
    st_dr = stats_monthly_10vol(s)
    sr_dr = st_dr["sharpe"]
    return {
        "weights": weights,
        "DESC": st_d,
        "REP": st_r,
        "DESC_REP": st_dr,
        "K27_power_63m_0_7x": round(Phi(0.7 * sr_dr * sqrt(63.0 / 12.0) - 1.645), 3),
        "K27_power_63m_1_0x": round(Phi(1.0 * sr_dr * sqrt(63.0 / 12.0) - 1.645), 3),
    }


def main() -> int:
    ho_m = pd.read_csv(ROOT / "docs/research/holdout_a5_nocme_20261127/SERIES_HOLDOUT_A5_NOCME_MENSUAL.csv.gz", index_col=0)
    ho_dr = ho_m[ho_m["bloque"].isin(["DESC", "REP"])].copy()
    ho_dr.index = pd.PeriodIndex(ho_dr.index, freq="M")

    mvc = pd.read_csv(ROOT / "docs/research/macro_cta_vrp_20261127/SERIES_DESC_REP.csv.gz", index_col=0, parse_dates=True)
    mrv = pd.read_csv(ROOT / "docs/research/m1_relval_eventos_20261127/SERIES_DESC_REP.csv.gz", index_col=0, parse_dates=True)
    fxf = pd.read_csv(ROOT / "docs/research/fx_macro_fix_20261127/SERIES_DESC_REP.csv.gz", index_col=0, parse_dates=True)

    M = pd.DataFrame({
        "Carril2_Sell16": ho_dr["Carril2_Sell16"],
        "Macro_RP4": ho_dr["Macro_RP_Canasta"],
        "MVC_CTA_VRP": mvc["MVC_Canasta_InvVol"].dropna().groupby(lambda d: d.to_period("M")).sum(),
        "MRV_PreFOMC": mrv["MRV_Canasta_InvVol"].dropna().groupby(lambda d: d.to_period("M")).sum(),
        "FXF3_TreasuryME": fxf["FXF3_Treasury_MonthEnd_Rebal"].dropna().groupby(lambda d: d.to_period("M")).sum(),
        "FXF_Canasta": fxf["FXF_Canasta_InvVol"].dropna().groupby(lambda d: d.to_period("M")).sum(),
    }).dropna()

    M_std = pd.DataFrame({c: _monthly_scale(M[c], 0.10) for c in M.columns}, index=M.index)
    corr = M_std.corr().round(3)

    # PCA effective independent sources on Carril2, RP4, MVC, MRV, FXF3
    cols5 = ["Carril2_Sell16", "Macro_RP4", "MVC_CTA_VRP", "MRV_PreFOMC", "FXF3_TreasuryME"]
    eig = np.linalg.eigvalsh(M_std[cols5].corr().to_numpy())
    n_eff5 = round(float((eig.sum() ** 2) / (eig ** 2).sum()), 2)

    combos = {
        "Pool_Sellado_2F_EQ (MVC+MRV)": _combo_metrics(M_std, {"MVC_CTA_VRP": 0.5, "MRV_PreFOMC": 0.5}),
        "Pool_Sellado_3F_EQ (MVC+MRV+FXF3)": _combo_metrics(M_std, {"MVC_CTA_VRP": 1 / 3, "MRV_PreFOMC": 1 / 3, "FXF3_TreasuryME": 1 / 3}),
        "Pool_Sellado_40_40_20 (MVC+MRV+FXF3)": _combo_metrics(M_std, {"MVC_CTA_VRP": 0.4, "MRV_PreFOMC": 0.4, "FXF3_TreasuryME": 0.2}),
        "Arquitectura_5F_20y (C2+RP4+MVC+MRV+FXF3)": _combo_metrics(M_std, {c: 0.2 for c in cols5}),
    }

    res = {
        "meses_comunes_DR": int(len(M_std)),
        "N_eff_PCA_5F": n_eff5,
        "corr_matrix": json.loads(corr.to_json()),
        "combos": combos,
        "pilares_fase2": {
            "FX_MACRO_FIX_20Y": json.loads((ROOT / "docs/research/fx_macro_fix_20261127/RESULTADO.json").read_text(encoding="utf-8"))["FXF_Canasta_InvVol"]["DESC_REP"],
            "CARRIL2_EMD": json.loads((ROOT / "docs/research/carril2_emd_20261127/RESULTADO.json").read_text(encoding="utf-8"))["veredicto_primario"],
            "CRIPTO_XSMOM_SPOT_PRE": json.loads((ROOT / "docs/research/cripto_xsmom_spot_2017_2019_20261127/RESULTADO.json").read_text(encoding="utf-8"))["veredicto_primario"],
            "CARRIL2_VOL_LOCAL": json.loads((ROOT / "docs/research/carril2_vol_local_20261127/RESULTADO.json").read_text(encoding="utf-8"))["resumen_reglas"],
            "CARRIL2_CANONICA_H3": json.loads((ROOT / "docs/research/canasta_amplia_20261127/SERIE_CANONICA_H3.json").read_text(encoding="utf-8"))["comparacion"]["DESC_REP"],
        },
    }
    (OUT / "RESUMEN.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")

    md = [
        "# Espiral Fase 2 — Síntesis Integrada (DESC+REP; HOLDOUT A5 del Pool Nuevo Sellado)",
        "",
        f"Estado: VIGENTE — análisis descriptivo sobre `{len(M_std)}m` comunes `DESC+REP` (`N_eff PCA 5F = {n_eff5} / 5,00`).",
        "",
        "## 1. Pools en `167m` DESC+REP y proyección K27 (`63m` sellados)",
        "| Pool | `DESC Sh` | `REP Sh` | `DR Sh (t)` | `MDD@10%` | `K27 @0.7x` | `K27 @1.0x` |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]
    for nm, c in combos.items():
        dr = c["DESC_REP"]
        md.append(f"| `{nm}` | `{c['DESC']['sharpe']}` | `{c['REP']['sharpe']}` | **`{dr['sharpe']} ({dr['t']})`** | `{dr['mdd_at_10pct_vol']}%` | `{c['K27_power_63m_0_7x']}` | `{c['K27_power_63m_1_0x']}` |")

    md.extend(["", "## 2. Matriz de correlación mensual `DESC+REP`", corr.to_markdown(), "", "Aporte al referente: integra los 4 pilares de Fase 2 con los frentes de Fase 1 sin abrir ningún holdout sellado."])
    (OUT / "RESUMEN.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps({"n_eff5": n_eff5, "combos": {k: (v["DESC_REP"]["sharpe"], v["DESC_REP"]["t"], v["K27_power_63m_0_7x"], v["K27_power_63m_1_0x"]) for k, v in combos.items()}}, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
