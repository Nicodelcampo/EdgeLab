#!/usr/bin/env python3
"""Espiral Fase 1 — Síntesis de correlación, N_eff y potencia K27 en DESC+REP (HOLDOUT A5 100% sellado).

Descriptivo: 0 pruebas nuevas (no lee HOLDOUT ni >= 2026-10-01).
Salida: docs/research/espiral_sintesis_20261127/{RESUMEN.json, RESUMEN.md}.
Uso:
  python -u tools/espiral_sintesis_20261127.py
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from statistics import NormalDist

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))

from edgelab.holdout import a5_bloque  # noqa: E402
from marco_sin_forward import _a5_mes_blq, stats_monthly_10vol  # noqa: E402

OUT = ROOT / "docs/research/espiral_sintesis_20261127"
OUT.mkdir(parents=True, exist_ok=True)
PHI = NormalDist().cdf


def _k27_power(sh_annual: float, n_months: int, mult: float = 0.70) -> float:
    """Potencia K27 (una cola alpha=0.05 -> z_crit=1.6449) con factor de contraccion `mult` sobre Sharpe DR."""
    z_crit = 1.6448536
    mu_m = (sh_annual * mult) / math.sqrt(12.0)
    ncp = mu_m * math.sqrt(n_months)
    return round(float(1.0 - PHI(z_crit - ncp)), 3)


def _load_daily_dr_monthly(csv_path: Path, col: str) -> pd.Series:
    df = pd.read_csv(csv_path, index_col=0, parse_dates=True)
    df = df[df["bloque"].isin(["DESC", "REP"])].copy()
    assert not df["bloque"].isin(["HOLDOUT", "TERMINAL", "EMBARGO"]).any(), f"Holdout/Terminal leak in {csv_path}"
    s = df[col].dropna()
    idx = pd.DatetimeIndex(s.index)
    if idx.tz is not None:
        idx = idx.tz_localize(None)
    s.index = idx
    return s.groupby(lambda d: d.to_period("M")).sum()


def main() -> None:
    ho_m = pd.read_csv(ROOT / "docs/research/holdout_a5_nocme_20261127/SERIES_HOLDOUT_A5_NOCME_MENSUAL.csv.gz", index_col=0)
    ho_dr = ho_m[ho_m["bloque"].isin(["DESC", "REP"])].copy()
    assert not ho_dr["bloque"].isin(["HOLDOUT", "TERMINAL"]).any()
    ho_dr.index = pd.PeriodIndex(ho_dr.index, freq="M")

    # Load 3 new spiral families (strictly DESC + REP only)
    m_mvc = _load_daily_dr_monthly(ROOT / "docs/research/macro_cta_vrp_20261127/SERIES_DESC_REP.csv.gz", "MVC_Canasta_InvVol")
    m_mvc1 = _load_daily_dr_monthly(ROOT / "docs/research/macro_cta_vrp_20261127/SERIES_DESC_REP.csv.gz", "MVC1_CTA_NonEq_MultiHorizon")
    m_mvc4 = _load_daily_dr_monthly(ROOT / "docs/research/macro_cta_vrp_20261127/SERIES_DESC_REP.csv.gz", "MVC4_MoreiraMuir_VolManaged")
    m_mrv = _load_daily_dr_monthly(ROOT / "docs/research/m1_relval_eventos_20261127/SERIES_DESC_REP.csv.gz", "MRV_Canasta_InvVol")
    m_cfc = _load_daily_dr_monthly(ROOT / "docs/research/cripto_funding_carry_20261127/SERIES_DESC_REP.csv.gz", "CFC_Canasta_InvVol")

    # Normalize each series to 10% annualized vol on its DESC months cleanly
    def _norm_10(s: pd.Series) -> pd.Series:
        bm = pd.Series([_a5_mes_blq(p) for p in s.index], index=s.index)
        sd_d = float(s[bm == "DESC"].std(ddof=1))
        return s / (sd_d * math.sqrt(12.0)) * 10.0

    # Pool 20y (186m DESC+REP): New Untouched (MVC + MRV)
    p_20y = pd.DataFrame({
        "Carril2_Sell16": _norm_10(ho_dr["Carril2_Sell16"].dropna()),
        "Macro_RP4": _norm_10(ho_dr["Macro_RP_Canasta"].dropna()),
        "MVC_CTA_VRP": _norm_10(m_mvc),
        "MVC1_CTA_NonEq": _norm_10(m_mvc1),
        "MVC4_VolManaged": _norm_10(m_mvc4),
        "MRV_PreFOMC": _norm_10(m_mrv),
    }).dropna()

    bm20 = pd.Series([_a5_mes_blq(p) for p in p_20y.index], index=p_20y.index)

    # New untouched 20y families only: MVC + MRV (HOLDOUT A5 63m 100% sealed in BOTH!)
    s_new2_eq = 0.5 * p_20y["MVC_CTA_VRP"] + 0.5 * p_20y["MRV_PreFOMC"]
    # 3 orthogonal new 20y mechanisms (CTA non-eq + Vol-Managed + Pre-FOMC) weighted inv-var in DESC
    cols3_new = ["MVC1_CTA_NonEq", "MVC4_VolManaged", "MRV_PreFOMC"]
    s_new3_eq = p_20y[cols3_new].mean(axis=1)

    # Full 4-front 20y architecture (Carril2 + MacroRP4 + MVC + MRV) strictly in DESC+REP
    cols4_20y = ["Carril2_Sell16", "Macro_RP4", "MVC_CTA_VRP", "MRV_PreFOMC"]
    s_all4_eq = p_20y[cols4_20y].mean(axis=1)

    # Multi-asset 51m (2021-01..2026-09 DESC+REP): add Cripto XSMOM + OFI + CFC
    p_51m = pd.DataFrame({
        **{c: p_20y[c] for c in cols4_20y},
        "Cripto_v3": _norm_10(ho_dr["Cripto_v3_Canasta"].dropna()),
        "Cripto_OFI": _norm_10(ho_dr["Cripto_OFI_Canasta"].dropna()),
        "Cripto_CFC": _norm_10(m_cfc),
    }).dropna()
    bm51 = pd.Series([_a5_mes_blq(p) for p in p_51m.index], index=p_51m.index)
    s_all6_eq = p_51m[["Carril2_Sell16", "Macro_RP4", "MVC_CTA_VRP", "MRV_PreFOMC", "Cripto_v3", "Cripto_OFI"]].mean(axis=1)

    def _pack(s: pd.Series, bm: pd.Series, n_ho: int) -> dict:
        st_dr = stats_monthly_10vol(s)
        return {
            "DESC": stats_monthly_10vol(s[bm == "DESC"]),
            "REP": stats_monthly_10vol(s[bm == "REP"]),
            "DESC_REP": st_dr,
            "K27_pot_n_HO_07x": _k27_power(st_dr["sharpe"], n_ho, 0.70),
            "K27_pot_n_HO_10x": _k27_power(st_dr["sharpe"], n_ho, 1.00),
            "n_HO_sellado": n_ho,
        }

    corr20 = p_20y[cols4_20y].corr().round(3).to_dict()
    corr51 = p_51m.corr().round(3).to_dict()

    # Effective number of independent bets N_eff = N^2 / sum(corr_ij) or eigenvalue entropy on 20y 4-front
    cmat = p_20y[cols4_20y].corr().to_numpy()
    eigvals = np.maximum(np.linalg.eigvalsh(cmat), 0.0)
    pr = eigvals / eigvals.sum()
    n_eff_pca = round(float(1.0 / np.sum(pr ** 2)), 2)

    out = {
        "meses_20y_DR": int(len(p_20y)),
        "meses_51m_DR": int(len(p_51m)),
        "frentes_20y_individuales": {c: _pack(p_20y[c], bm20, 63) for c in p_20y.columns},
        "frentes_cripto_51m": {c: _pack(p_51m[c], bm51, 18) for c in ("Cripto_v3", "Cripto_OFI", "Cripto_CFC")},
        "combinaciones": {
            "Pool_Nuevo_Sellado_2F_EQ (MVC+MRV, 63m HO intacto)": _pack(s_new2_eq, bm20, 63),
            "Pool_Nuevo_Sellado_3M_EQ (CTA+MM+PreFOMC, 63m HO intacto)": _pack(s_new3_eq, bm20, 63),
            "Arquitectura_20y_4F_EQ (Carril2+RP4+MVC+MRV, solo DR)": _pack(s_all4_eq, bm20, 63),
            "Arquitectura_Multi_6F_EQ_51m (4F_20y+Cripto_v3+OFI, solo DR)": _pack(s_all6_eq, bm51, 18),
        },
        "n_eff_4F_20y": n_eff_pca,
        "corr_20y_DR": corr20,
        "corr_51m_DR": corr51,
    }
    (OUT / "RESUMEN.json").write_text(json.dumps(out, indent=2, ensure_ascii=False, default=float), encoding="utf-8")

    md = [
        "# Espiral Fase 1 — Síntesis Multi-Frente y Potencia K27 (DESC+REP; HOLDOUT A5 Sellado)",
        "",
        "Estado: VIGENTE — análisis descriptivo exclusivamente sobre `DESC+REP` (`0` pruebas nuevas, `HOLDOUT A5` 100 % sellado).",
        "",
        "## 1. Frentes y combinaciones en `20` años (`186m` DESC+REP; proyección K27 a `63m` sellados)",
        "| Frente / Pool | `DESC Sh` | `REP Sh` | `DR Sh (t)` | `MDD@10%` | `Calmar` | `K27 @0.7x (63m)` | `K27 @1.0x (63m)` |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]
    for k, v in {**out["frentes_20y_individuales"], **out["combinaciones"]}.items():
        if v["DESC_REP"]["meses"] < 100:
            continue
        dr = v["DESC_REP"]
        md.append(
            f"| `{k}` | `{v['DESC']['sharpe']}` | `{v['REP']['sharpe']}` | **`{dr['sharpe']} ({dr['t']})`** | "
            f"`{dr['mdd_at_10pct_vol']}%` | `{dr['calmar_at_10pct_vol']}` | `{v['K27_pot_n_HO_07x']}` | `{v['K27_pot_n_HO_10x']}` |"
        )
    md += [
        "",
        f"- **Número efectivo de fuentes independientes (`N_eff` PCA sobre `Carril2, RP4, MVC, MRV` en 186m):** **`{n_eff_pca}` de `4,00`**.",
        "",
        "## 2. Correlación mensual `DESC+REP` (`186m`, `2006–2026-09`)",
    ]
    hdr = "| | " + " | ".join(cols4_20y) + " |"
    sep = "| :--- | " + " | ".join([":---:"] * len(cols4_20y)) + " |"
    md.extend([hdr, sep])
    for r in cols4_20y:
        vals = " | ".join(f"`{corr20[r][c]:+.3f}`" for c in cols4_20y)
        md.append(f"| **{r}** | {vals} |")
    (OUT / "RESUMEN.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps({
        "frentes_20y": {k: (v["DESC"]["sharpe"], v["REP"]["sharpe"], v["DESC_REP"]["sharpe"], v["DESC_REP"]["t"]) for k, v in out["frentes_20y_individuales"].items()},
        "combinaciones": {k: (v["DESC_REP"]["sharpe"], v["DESC_REP"]["t"], v["DESC_REP"]["mdd_at_10pct_vol"], v["K27_pot_n_HO_07x"], v["K27_pot_n_HO_10x"]) for k, v in out["combinaciones"].items()},
        "n_eff_4F_20y": n_eff_pca,
        "corr_20y_DR": corr20,
    }, indent=2))


if __name__ == "__main__":
    main()
