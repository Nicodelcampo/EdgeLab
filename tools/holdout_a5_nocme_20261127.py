#!/usr/bin/env python3
"""HOLDOUT-A5-NOCME (EF4, 2026-11-27): Apertura unica conjunta de 4 frentes No-CME (< 2026-10-01) con K27 levantado por Nico.

Pre-registro inmutable: docs/research/holdout_a5_nocme_20261127/PREREGISTRO.md (K51).
  python -u tools/holdout_a5_nocme_20261127.py verificar_paridad   # verifica DESC+REP sin leer HOLDOUT
  python -u tools/holdout_a5_nocme_20261127.py abrir               # registra aperturas K27 y ejecuta lectura unica HOLDOUT A5
"""
from __future__ import annotations

import json
import sys
from math import erf, log, sqrt
from pathlib import Path

import numpy as np
import pandas as pd
import math


def _chi2_sf_par(x: float, df: int) -> float:
    """Cola superior de una chi² con df par (Fisher: df = 2k): exp(-x/2)·Σ_{i<k} (x/2)^i / i!. Exacta; evita depender de scipy."""
    k, h = df // 2, x / 2.0
    return math.exp(-h) * sum(h ** i / math.factorial(i) for i in range(k))

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ImportError:
    plt = None

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))

from edgelab.holdout import a5_bloque  # noqa: E402
from edgelab.research import holdout_ventanas as HV  # noqa: E402
from canasta_amplia import (  # noqa: E402
    AUTORIZACION_K27,
    _ops_carril2_holdout,
    verificar_motor as _verificar_c2_motor,
)
from cripto_ofi_20261127 import compute_cripto_ofi_daily  # noqa: E402
from cripto_pit_v2 import stats_serie  # noqa: E402
from cripto_pit_v3 import compute_cripto_v3_daily  # noqa: E402
from generar_graficos_audit_20261127 import _save_and_copy  # noqa: E402
from generar_graficos_frentes_20261127 import (  # noqa: E402
    BG,
    CYAN,
    GREEN,
    GRID,
    MUTED,
    ORANGE,
    PANEL,
    PURPLE,
    RED,
    TEAL,
    TEXT,
    _style,
)
from macro_risk_premia_20261127 import compute_macro_rp_daily  # noqa: E402
from marco_sin_forward import _a5_mes_blq, stats_monthly_10vol  # noqa: E402
from registro_global import exigir_contada  # noqa: E402

PREREG_REL = "docs/research/holdout_a5_nocme_20261127/PREREGISTRO.md"
OUT = ROOT / "docs/research/holdout_a5_nocme_20261127"
OUT.mkdir(parents=True, exist_ok=True)


def _phi_local(z: float) -> float:
    return 0.5 * (1.0 + erf(z / sqrt(2.0)))


def _veredicto(st: dict, mean_raw: float) -> str:
    if mean_raw <= 0.0 or st.get("meses", 0) < 3:
        return "EN_CONTRA"
    return "CONFIRMA" if float(st.get("t", 0.0)) >= 1.645 else "NO_CONCLUYENTE"


def _frozen_invvol_weights(df_daily: pd.DataFrame, blq: pd.Series, cols: list[str]) -> pd.Series:
    m_d = df_daily.loc[blq == "DESC", cols].groupby(lambda d: d.to_period("M")).sum()
    sd = m_d.std(ddof=1).replace(0.0, np.nan).fillna(1.0)
    return (1.0 / sd) / (1.0 / sd).sum()


def _carril2_monthly_from_ops(blocks: tuple[str, ...]) -> tuple[pd.Series, pd.DataFrame]:
    T = _ops_carril2_holdout(blocks)
    assert not (T["fecha"] >= 20261001).any(), "TERMINAL breach in Carril 2!"
    w = json.loads((ROOT / "docs/research/canasta_amplia_20261127/PESOS_CARRIL2_SELLADA.json").read_text(encoding="utf-8"))
    T["Rw"] = T["R"] * T["k"].map(w)
    T["mes"] = pd.to_datetime(T["fecha"].astype(str)).dt.to_period("M")
    all_p = pd.period_range("2006-01", "2026-09", freq="M")
    target_p = pd.PeriodIndex([p for p in all_p if _a5_mes_blq(p) in set(blocks)], freq="M")
    m_rw = T.groupby("mes")["Rw"].sum().reindex(target_p, fill_value=0.0)
    m_ind = T.pivot_table(index="mes", columns="k", values="R", aggfunc="sum").reindex(target_p, fill_value=0.0)
    return m_rw, m_ind


def verificar_paridad(cores: dict | None = None) -> dict:
    """Verifica paridad numerica exacta en DESC+REP de los 4 motores SIN tocar meses HOLDOUT."""
    print("=== PAS0 PARIDAD DESC+REP (ZERO HOLDOUT) ===")
    rc_c2 = _verificar_c2_motor()
    if rc_c2 != 0:
        raise RuntimeError("Fallo verificar_motor de Carril 2")

    mrp = cores["mrp"] if cores else compute_macro_rp_daily()
    cr3 = cores["cr3"] if cores else compute_cripto_v3_daily()
    ofi = cores["ofi"] if cores else compute_cripto_ofi_daily()

    # 1. Macro RP parity against SERIES_MACRO_RP_DR.csv.gz
    ref_mrp = pd.read_csv(ROOT / "docs/research/macro_risk_premia_20261127/SERIES_MACRO_RP_DR.csv.gz", index_col=0, parse_dates=True)
    m_mrp_dr = mrp["blq_d"].isin(["DESC", "REP"])
    cols_m = ["RP1_Sector_XSMOM_Neut", "RP2_Sector_BAB_LowBeta", "RP3_Country_XSMOM_Neut", "RP4_Rates_Curve_Credit", "RP5_NonEq_MultiSpeed_Trend"]
    diff_mrp = float((mrp["raw_1x"].loc[m_mrp_dr, cols_m] - ref_mrp.loc[m_mrp_dr, cols_m]).abs().max().max())

    # 2. Cripto v3 parity against SERIES_CRIPTO_PIT_V3_DR.csv.gz
    ref_cr3 = pd.read_csv(ROOT / "docs/research/cripto_pit_v3_20261127/SERIES_CRIPTO_PIT_V3_DR.csv.gz", index_col=0, parse_dates=True)
    m_cr3_dr = cr3["blq"].isin(["DESC", "REP"])
    cols_c = ["CR3_XSMOM_21d_Stag5d", "CR3_XSMOM_BetaNeut_Stag5d", "CR3_Basis_Carry_Stag5d", "CR3_BAB_LowVol_Stag5d", "CR3_ResidMom_21d_2F_Stag5d"]
    diff_cr3 = float((cr3["daily_by_bps"][20].loc[m_cr3_dr, cols_c] - ref_cr3.loc[m_cr3_dr, cols_c]).abs().max().max())

    # 3. Cripto OFI parity against SERIES_CRIPTO_OFI_DR.csv.gz
    ref_ofi = pd.read_csv(ROOT / "docs/research/cripto_ofi_20261127/SERIES_CRIPTO_OFI_DR.csv.gz", index_col=0, parse_dates=True)
    m_ofi_dr = ofi["blq"].isin(["DESC", "REP"])
    cols_o = ["OFI1_TakerFlow_21d_Stag5d", "OFI2_FlowReturn_Div_14d_Stag5d", "OFI3_WhaleFlow_14d_Stag5d"]
    diff_ofi = float((ofi["daily_by_bps"][20].loc[m_ofi_dr, cols_o] - ref_ofi.loc[m_ofi_dr, cols_o]).abs().max().max())

    print(f"  Paridad MACRO_RP max_abs_diff = {diff_mrp:.2e}")
    print(f"  Paridad CRIPTO_V3 max_abs_diff = {diff_cr3:.2e}")
    print(f"  Paridad CRIPTO_OFI max_abs_diff = {diff_ofi:.2e}")
    assert diff_mrp < 1e-8 and diff_cr3 < 1e-6 and diff_ofi < 1e-6, "Parity mismatch!"
    return {"carril2_ok": True, "diff_mrp": diff_mrp, "diff_cr3": diff_cr3, "diff_ofi": diff_ofi}


def _registrar_aperturas_k27() -> list[dict]:
    if not AUTORIZACION_K27:
        raise SystemExit("BLOQUEADO (K27): falta AUTORIZACION_K27 escrita de Nico.")
    # Verificar que CARRIL2_A5 ya fue abierto en HOLDOUT_VENTANAS.jsonl
    c2_v = HV.aperturas_vigentes("CARRIL2_A5")
    if not c2_v:
        raise SystemExit("Falta apertura previa de CARRIL2_A5: ejecutar primero `python tools/canasta_amplia.py holdout_carril2`.")

    specs = [
        ("MACRO_RISK_PREMIA", "MACRO_RISK_PREMIA::holdout_a5_rp_canasta_20261127", 20060101, 63, 0.001143 / 2.0, 0.010838, "mitad DESC+REP RP_Canasta_InvVol (186m DR)"),
        ("CRIPTO_BINANCE", "CRIPTO_BINANCE::holdout_a5_cr3_canasta_20261127", 20210101, 18, 211.8 / 2.0, 568.5, "mitad DESC+REP CR3_Canasta_InvVol (51m DR, REP iterada v1-v3)"),
        ("CRIPTO_ORDERFLOW_PIT", "CRIPTO_ORDERFLOW_PIT::holdout_a5_ofi_canasta_20261127", 20210101, 18, 167.5 / 2.0, 971.0, "mitad DESC+REP OFI_Canasta_InvVol (51m DR)"),
        ("CANASTA_AMPLIA", "CANASTA_AMPLIA::holdout_a5_pool_nocme_20261127", 20060101, 63, 0.183827 / 2.0, 0.647191, "mitad DESC+REP Pool_NoCME_Dyn_4F_63m (Super_v3 + Clean63m)"),
    ]
    rows = []
    for fam, cid, desde, nf, ef, sd, fuente in specs:
        p = HV.plan_potencia("fijo", ef, sd, n=nf, fuente_efecto=fuente)
        p["problemas_levantados_por_humano"] = p.pop("problemas") + [x for x in HV.problemas(fam, desde, cid) if "ya tiene" not in x]
        p.update(problemas=[], autorizacion=AUTORIZACION_K27, hasta=20260930, preregistro=PREREG_REL)
        rows.append(HV.registrar_apertura(fam, cid, desde, nf, plan=p))
    return rows


def _chart_holdout_nocme(df_m: pd.DataFrame, res: dict) -> None:
    if plt is None:
        return
    h63 = df_m[df_m["bloque"] == "HOLDOUT"].copy()
    h18 = h63.loc[h63.index >= "2021-01"].copy()

    def _eq10(s: pd.Series) -> np.ndarray:
        x = s.dropna()
        sd = float(x.std(ddof=1))
        if sd <= 0:
            return np.zeros(len(x))
        return ((x / (sd * sqrt(12.0)) * 10.0)).cumsum().to_numpy(float)

    fig, axes = plt.subplots(2, 2, figsize=(15.5, 10.2), facecolor=BG)
    fig.suptitle(
        "HOLDOUT A5 Sellado (< 2026-10-01) — Apertura Conjunta K27 (4 Frentes Limpios No-CME; TERMINAL Sellado)",
        color=TEXT, fontsize=12.5, fontweight="bold", y=0.98,
    )

    # Panel 1: Equity curves @ 10% vol in 63m HOLDOUT A5
    ax = axes[0, 0]
    _style(ax)
    xi = np.arange(len(h63))
    xl = [str(p) for p in h63.index]
    p1_specs = [
        ("Pool_NoCME_Dyn_4F_63m", "Pool NoCME Dyn 4F (Sh={:.2f}, t={:.2f})".format(res["primarios"]["Pool_NoCME_Dyn_4F_63m"]["HOLDOUT"]["sharpe"], res["primarios"]["Pool_NoCME_Dyn_4F_63m"]["HOLDOUT"]["t"]), TEAL, 2.7),
        ("Super_v3_Clean63m_EQ", "Clean63m EQ C2+RP4 (Sh={:.2f}, t={:.2f})".format(res["primarios"]["Super_v3_Clean63m_EQ"]["HOLDOUT"]["sharpe"], res["primarios"]["Super_v3_Clean63m_EQ"]["HOLDOUT"]["t"]), CYAN, 2.1),
        ("Carril2_Sell16", "Carril 2 Sell16 (Sh={:.2f}, t={:.2f})".format(res["primarios"]["Carril2_Sell16"]["HOLDOUT"]["sharpe"], res["primarios"]["Carril2_Sell16"]["HOLDOUT"]["t"]), ORANGE, 1.8),
        ("Macro_RP_Canasta", "Macro RP4 (Sh={:.2f}, t={:.2f})".format(res["primarios"]["Macro_RP_Canasta"]["HOLDOUT"]["sharpe"], res["primarios"]["Macro_RP_Canasta"]["HOLDOUT"]["t"]), PURPLE, 1.8),
    ]
    for col, lbl, c, lw in p1_specs:
        ax.plot(xi, _eq10(h63[col]), label=lbl, color=c, linewidth=lw)
    ax.axhline(0, color=MUTED, linewidth=0.8)
    step = max(1, len(xi) // 7)
    ax.set_xticks(xi[::step]); ax.set_xticklabels(xl[::step], color=TEXT, fontsize=8)
    ax.set_ylabel("Retorno acumulado (% a 10% vol propia)", color=TEXT, fontsize=9)
    ax.set_title("1. HOLDOUT A5 Largo (63 meses sellados, 2006–2026-09)", color=TEXT, fontsize=10.5, fontweight="bold")
    ax.legend(facecolor=PANEL, edgecolor=GRID, labelcolor=TEXT, fontsize=7.8)

    # Panel 2: Equity curves @ 10% vol in 18m HOLDOUT A5 (2021-2026)
    ax = axes[0, 1]
    _style(ax)
    xi2 = np.arange(len(h18))
    xl2 = [str(p) for p in h18.index]
    p2_specs = [
        ("Super_v3_NoCME_HRP", "NoCME HRP 21-26 (Sh={:.2f}, t={:.2f})".format(res["primarios"]["Super_v3_NoCME_HRP"]["HOLDOUT"]["sharpe"], res["primarios"]["Super_v3_NoCME_HRP"]["HOLDOUT"]["t"]), TEAL, 2.7),
        ("Super_v3_NoCME_EQ", "NoCME EQ 21-26 (Sh={:.2f}, t={:.2f})".format(res["primarios"]["Super_v3_NoCME_EQ"]["HOLDOUT"]["sharpe"], res["primarios"]["Super_v3_NoCME_EQ"]["HOLDOUT"]["t"]), GREEN, 1.9),
        ("Cripto_v3_Canasta", "Cripto v3 (Sh={:.2f}, t={:.2f})".format(res["primarios"]["Cripto_v3_Canasta"]["HOLDOUT"]["sharpe"], res["primarios"]["Cripto_v3_Canasta"]["HOLDOUT"]["t"]), CYAN, 1.8),
        ("Cripto_OFI_Canasta", "Cripto OFI (Sh={:.2f}, t={:.2f})".format(res["primarios"]["Cripto_OFI_Canasta"]["HOLDOUT"]["sharpe"], res["primarios"]["Cripto_OFI_Canasta"]["HOLDOUT"]["t"]), ORANGE, 1.8),
        ("Carril2_Sell16", "Carril 2 21-26 (Sh={:.2f})".format(stats_monthly_10vol(h18["Carril2_Sell16"])["sharpe"]), RED, 1.4),
    ]
    for col, lbl, c, lw in p2_specs:
        ax.plot(xi2, _eq10(h18[col]), label=lbl, color=c, linewidth=lw)
    ax.axhline(0, color=MUTED, linewidth=0.8)
    step2 = max(1, len(xi2) // 6)
    ax.set_xticks(xi2[::step2]); ax.set_xticklabels(xl2[::step2], color=TEXT, fontsize=8)
    ax.set_ylabel("Retorno acumulado (% a 10% vol propia)", color=TEXT, fontsize=9)
    ax.set_title("2. HOLDOUT A5 Reciente (18 meses sellados, 2021–2026-09)", color=TEXT, fontsize=10.5, fontweight="bold")
    ax.legend(facecolor=PANEL, edgecolor=GRID, labelcolor=TEXT, fontsize=7.8)

    # Panel 3: Grouped bars DESC vs REP vs HOLDOUT Sharpe
    ax = axes[1, 0]
    _style(ax)
    keys = ["Carril2_Sell16", "Macro_RP_Canasta", "Cripto_v3_Canasta", "Cripto_OFI_Canasta", "Super_v3_Clean63m_EQ", "Pool_NoCME_Dyn_4F_63m", "Super_v3_NoCME_HRP"]
    lbls = ["Carril2\n(63m)", "MacroRP\n(63m)", "CriptoV3\n(18m)", "CriptoOFI\n(18m)", "Clean63m\n(63m)", "PoolDyn\n(63m)", "NoCME_HRP\n(18m)"]
    x3 = np.arange(len(keys))
    w = 0.25
    ax.bar(x3 - w, [res["primarios"][k]["DESC"]["sharpe"] for k in keys], width=w, color=CYAN, label="DESC")
    ax.bar(x3, [res["primarios"][k]["REP"]["sharpe"] for k in keys], width=w, color=ORANGE, label="REP")
    h_vals = [res["primarios"][k]["HOLDOUT"]["sharpe"] for k in keys]
    bars_h = ax.bar(x3 + w, h_vals, width=w, color=TEAL, label="HOLDOUT A5")
    for b, hv in zip(bars_h, h_vals):
        ax.text(b.get_x() + b.get_width() / 2, hv + (0.04 if hv >= 0 else -0.14), f"{hv:.2f}", ha="center", color=TEXT, fontsize=7.5, fontweight="bold")
    ax.axhline(0, color=MUTED, linewidth=0.8)
    ax.set_xticks(x3); ax.set_xticklabels(lbls, color=TEXT, fontsize=8)
    ax.set_ylabel("Sharpe anualizado", color=TEXT, fontsize=9)
    ax.set_title("3. Retencion Fuera de Muestra: DESC vs REP vs HOLDOUT A5", color=TEXT, fontsize=10.5, fontweight="bold")
    ax.legend(facecolor=PANEL, edgecolor=GRID, labelcolor=TEXT, fontsize=8)

    # Panel 4: Correlation matrix inside HOLDOUT A5 (18m)
    ax = axes[1, 1]
    _style(ax)
    ax.grid(False)
    fcols = ["Carril2_Sell16", "Macro_RP_Canasta", "Cripto_v3_Canasta", "Cripto_OFI_Canasta"]
    fshort = ["Carril2", "MacroRP", "CriptoV3", "CriptoOFI"]
    cmat = h18[fcols].corr().fillna(0.0).to_numpy(float)
    ax.imshow(cmat, cmap="coolwarm", vmin=-0.6, vmax=1.0, aspect="auto")
    ax.set_xticks(range(4)); ax.set_yticks(range(4))
    ax.set_xticklabels(fshort, color=TEXT, fontsize=8.5, rotation=15, ha="right")
    ax.set_yticklabels(fshort, color=TEXT, fontsize=8.5)
    for i in range(4):
        for j in range(4):
            ax.text(j, i, f"{cmat[i, j]:+.2f}", ha="center", va="center", color="#111111" if abs(cmat[i, j]) < 0.45 else TEXT, fontsize=9.5, fontweight="bold")
    f_all = res["combinaciones"]["fisher_4_frentes_HOLDOUT"]
    f_c63 = res["combinaciones"]["fisher_clean_63m_HOLDOUT"]
    ax.set_title(f"4. Correlaciones en HOLDOUT A5 (18m) | Fisher 4F p={f_all['p']:.4f} | Clean63m p={f_c63['p']:.4f}", color=TEXT, fontsize=9.8, fontweight="bold")

    fig.tight_layout(rect=[0, 0, 1, 0.95])
    _save_and_copy(fig, "holdout_a5_nocme_20261127.png", out=OUT)


def abrir() -> int:
    exigir_contada(PREREG_REL)
    mrp = compute_macro_rp_daily()
    cr3 = compute_cripto_v3_daily()
    ofi = compute_cripto_ofi_daily()
    cores = {"mrp": mrp, "cr3": cr3, "ofi": ofi}
    par = verificar_paridad(cores)
    _registrar_aperturas_k27()

    print("\n=== EJECUTANDO LECTURA UNICA HOLDOUT A5 (< 2026-10-01) ===", flush=True)
    c2_dr, c2_ind_dr = _carril2_monthly_from_ops(("DESC", "REP"))
    c2_ho, c2_ind_ho = _carril2_monthly_from_ops(("HOLDOUT",))

    # Sanity check against HOLDOUT_CARRIL2.json
    c2_json_p = ROOT / "docs/research/canasta_amplia_20261127/HOLDOUT_CARRIL2.json"
    c2_json = json.loads(c2_json_p.read_text(encoding="utf-8"))

    # Aggregate Macro RP, Cripto v3, Cripto OFI across ALL valid A5 months (DESC + REP + HOLDOUT; zero EMBARGO/TERMINAL)
    all_p = pd.period_range("2006-01", "2026-09", freq="M")
    valid_p63 = pd.PeriodIndex([p for p in all_p if _a5_mes_blq(p) in ("DESC", "REP", "HOLDOUT")], freq="M")
    blq_63 = pd.Series([_a5_mes_blq(p) for p in valid_p63], index=valid_p63)

    # 1. Carril 2 combined monthly (R weighted)
    m_c2 = pd.concat([c2_dr, c2_ho]).reindex(valid_p63).fillna(0.0)
    m_c2_ind = pd.concat([c2_ind_dr, c2_ind_ho]).reindex(valid_p63).fillna(0.0)

    # 2. Macro RP monthly (1x and 2x), strict block filtering before aggregation
    mrp_m_mask = mrp["blq_d"].isin(["DESC", "REP", "HOLDOUT"])
    assert not mrp["blq_d"].isin(["TERMINAL"]).any()
    mrp_1x_m = mrp["raw_1x"].loc[mrp_m_mask].groupby(lambda d: d.to_period("M")).sum().reindex(valid_p63)
    mrp_2x_m = mrp["raw_2x"].loc[mrp_m_mask].groupby(lambda d: d.to_period("M")).sum().reindex(valid_p63)
    m_mrp_bask = mrp_1x_m["RP4_Rates_Curve_Credit"].copy()
    m_mrp_bask_2x = mrp_2x_m["RP4_Rates_Curve_Credit"].copy()

    mrp_diag_cols = ["RP2_Sector_BAB_LowBeta", "RP4_Rates_Curve_Credit", "RP5_NonEq_MultiSpeed_Trend"]
    w_mrp_3pos = _frozen_invvol_weights(mrp["raw_1x"], mrp["blq_d"], mrp_diag_cols)
    m_mrp_diag3 = (mrp_1x_m[mrp_diag_cols] * w_mrp_3pos).sum(axis=1)

    # 3. Cripto v3 monthly (DESC+REP+HOLDOUT in 2021-01..2026-09)
    cr3_m_mask = cr3["blq"].isin(["DESC", "REP", "HOLDOUT"])
    assert not cr3["blq"].isin(["TERMINAL"]).any()
    cr3_20_m = cr3["daily_by_bps"][20].loc[cr3_m_mask].groupby(lambda d: d.to_period("M")).sum()
    cr3_alive = ["CR3_XSMOM_21d_Stag5d", "CR3_XSMOM_BetaNeut_Stag5d", "CR3_BAB_LowVol_Stag5d"]
    w_cr3 = _frozen_invvol_weights(cr3["daily_by_bps"][20], cr3["blq"], cr3_alive)
    m_cr3_bask = (cr3_20_m[cr3_alive] * w_cr3).sum(axis=1)

    cr3_2_cols = ["CR3_XSMOM_21d_Stag5d", "CR3_BAB_LowVol_Stag5d"]
    w_cr3_2 = _frozen_invvol_weights(cr3["daily_by_bps"][20], cr3["blq"], cr3_2_cols)
    m_cr3_diag2 = (cr3_20_m[cr3_2_cols] * w_cr3_2).sum(axis=1)

    # 4. Cripto OFI monthly
    ofi_m_mask = ofi["blq"].isin(["DESC", "REP", "HOLDOUT"])
    assert not ofi["blq"].isin(["TERMINAL"]).any()
    ofi_20_m = ofi["daily_by_bps"][20].loc[ofi_m_mask].groupby(lambda d: d.to_period("M")).sum()
    ofi_alive = ["OFI1_TakerFlow_21d_Stag5d", "OFI3_WhaleFlow_14d_Stag5d"]
    w_ofi = _frozen_invvol_weights(ofi["daily_by_bps"][20], ofi["blq"], ofi_alive)
    m_ofi_bask = (ofi_20_m[ofi_alive] * w_ofi).sum(axis=1)

    # Assemble master monthly frame (DESC + REP + HOLDOUT, strictly < 2026-10-01)
    df_m = pd.DataFrame(index=valid_p63)
    df_m["bloque"] = blq_63
    df_m["Carril2_Sell16"] = m_c2
    df_m["Macro_RP_Canasta"] = m_mrp_bask
    df_m["Macro_RP_Diag_3Pos"] = m_mrp_diag3
    df_m["Cripto_v3_Canasta"] = m_cr3_bask.reindex(valid_p63)
    df_m["Cripto_v3_XSMOM_BAB"] = m_cr3_diag2.reindex(valid_p63)
    df_m["Cripto_OFI_Canasta"] = m_ofi_bask.reindex(valid_p63)
    df_m["OFI1_TakerFlow_21d_Stag5d"] = ofi_20_m["OFI1_TakerFlow_21d_Stag5d"].reindex(valid_p63)

    # Frozen DESC SDs (computed ONLY on blq == 'DESC', matched to PREREGISTRO & SUPERCARTERA_V3)
    sd_c2_06 = float(df_m.loc[blq_63 == "DESC", "Carril2_Sell16"].std(ddof=1))
    sd_mrp_06 = float(df_m.loc[blq_63 == "DESC", "Macro_RP_Canasta"].std(ddof=1))
    sd_mrp3_06 = float(df_m.loc[blq_63 == "DESC", "Macro_RP_Diag_3Pos"].std(ddof=1))

    m21_idx = valid_p63[valid_p63 >= "2021-01"]
    b21 = blq_63.reindex(m21_idx)
    sd_21 = {
        c: float(df_m.loc[m21_idx[b21 == "DESC"], c].std(ddof=1))
        for c in ("Carril2_Sell16", "Macro_RP_Canasta", "Cripto_v3_Canasta", "Cripto_OFI_Canasta")
    }

    # Frozen HRP weights from SUPERCARTERA_V3.json
    sv3 = json.loads((ROOT / "docs/research/supercartera_v3_20261127/SUPERCARTERA_V3.json").read_text(encoding="utf-8"))
    w_hrp_63 = sv3["hrp_63m_weights"]
    w_hrp_nc = sv3["hrp_nocme_weights"]

    df_m["Super_v3_Clean63m_EQ"] = 0.5 * (df_m["Carril2_Sell16"] / sd_c2_06) + 0.5 * (df_m["Macro_RP_Canasta"] / sd_mrp_06)
    df_m["Super_v3_Clean63m_HRP"] = w_hrp_63["Carril2_Sell16"] * (df_m["Carril2_Sell16"] / sd_c2_06) + w_hrp_63["Macro_RP_Canasta"] * (df_m["Macro_RP_Canasta"] / sd_mrp_06)
    df_m["Super_v3_Clean63m_Diag3Pos_EQ"] = 0.5 * (df_m["Carril2_Sell16"] / sd_c2_06) + 0.5 * (df_m["Macro_RP_Diag_3Pos"] / sd_mrp3_06)

    norm_dyn = pd.DataFrame({
        "Carril2_Sell16": df_m["Carril2_Sell16"] / sd_c2_06,
        "Macro_RP_Canasta": df_m["Macro_RP_Canasta"] / sd_mrp_06,
        "Cripto_v3_Canasta": df_m["Cripto_v3_Canasta"] / sd_21["Cripto_v3_Canasta"],
        "Cripto_OFI_Canasta": df_m["Cripto_OFI_Canasta"] / sd_21["Cripto_OFI_Canasta"],
    }, index=valid_p63)
    df_m["Pool_NoCME_Dyn_4F_63m"] = norm_dyn.mean(axis=1)

    n21 = pd.DataFrame({c: df_m.loc[m21_idx, c] / sd_21[c] for c in sd_21}, index=m21_idx)
    df_m["Super_v3_NoCME_EQ"] = n21.mean(axis=1).reindex(valid_p63)
    df_m["Super_v3_NoCME_HRP"] = sum(n21[c] * w_hrp_nc[c] for c in sd_21).reindex(valid_p63)

    # Diagnostic post-hoc pruned portfolio (21-26, 4 fronts)
    sd_poda = {
        c: float(df_m.loc[m21_idx[b21 == "DESC"], c].std(ddof=1))
        for c in ("Carril2_Sell16", "Macro_RP_Diag_3Pos", "Cripto_v3_XSMOM_BAB", "OFI1_TakerFlow_21d_Stag5d")
    }
    df_m["Pool_NoCME_Poda_Diag_18m"] = pd.DataFrame({c: df_m.loc[m21_idx, c] / sd_poda[c] for c in sd_poda}, index=m21_idx).mean(axis=1).reindex(valid_p63)

    df_m.to_csv(OUT / "SERIES_HOLDOUT_A5_NOCME_MENSUAL.csv.gz")

    def _summarize(col: str, p_start: str | None = None) -> dict:
        s = df_m[col].dropna()
        if p_start:
            s = s[s.index >= p_start]
        b = blq_63.reindex(s.index)
        d, r, dr, h = s[b == "DESC"], s[b == "REP"], s[b.isin(["DESC", "REP"])], s[b == "HOLDOUT"]
        st_d, st_r, st_dr, st_h = stats_monthly_10vol(d), stats_monthly_10vol(r), stats_monthly_10vol(dr), stats_monthly_10vol(h)
        stf = round((st_r["t"] + st_h["t"]) / sqrt(2.0), 2)
        sr_dr = max(st_dr["sharpe"], 1e-6)
        epochs_h = {
            lbl: stats_monthly_10vol(h[(h.index >= p0) & (h.index <= p1)])
            for lbl, p0, p1 in [("06_12", "2006-01", "2012-12"), ("13_18", "2013-01", "2018-12"), ("19_26", "2019-01", "2026-09"), ("21_26", "2021-01", "2026-09")]
            if len(h[(h.index >= p0) & (h.index <= p1)]) >= 3
        }
        return {
            "DESC": st_d,
            "REP": st_r,
            "DESC_REP": st_dr,
            "HOLDOUT": st_h,
            "veredicto": _veredicto(st_h, float(h.mean())),
            "stouffer_REP_HOLDOUT": stf,
            "p_stouffer": round(1.0 - _phi_local(stf), 4),
            "retencion_vs_DR": round(st_h["sharpe"] / sr_dr, 3),
            "epochs_HOLDOUT": epochs_h,
        }

    primarios = {
        "Carril2_Sell16": _summarize("Carril2_Sell16"),
        "Macro_RP_Canasta": _summarize("Macro_RP_Canasta"),
        "Cripto_v3_Canasta": _summarize("Cripto_v3_Canasta", "2021-01"),
        "Cripto_OFI_Canasta": _summarize("Cripto_OFI_Canasta", "2021-01"),
        "Super_v3_Clean63m_EQ": _summarize("Super_v3_Clean63m_EQ"),
        "Super_v3_Clean63m_HRP": _summarize("Super_v3_Clean63m_HRP"),
        "Pool_NoCME_Dyn_4F_63m": _summarize("Pool_NoCME_Dyn_4F_63m"),
        "Super_v3_NoCME_EQ": _summarize("Super_v3_NoCME_EQ", "2021-01"),
        "Super_v3_NoCME_HRP": _summarize("Super_v3_NoCME_HRP", "2021-01"),
    }
    diagnosticos = {
        "Macro_RP_Diag_3Pos": _summarize("Macro_RP_Diag_3Pos"),
        "Super_v3_Clean63m_Diag3Pos_EQ": _summarize("Super_v3_Clean63m_Diag3Pos_EQ"),
        "Cripto_v3_XSMOM_BAB": _summarize("Cripto_v3_XSMOM_BAB", "2021-01"),
        "OFI1_TakerFlow_21d_Stag5d": _summarize("OFI1_TakerFlow_21d_Stag5d", "2021-01"),
        "Pool_NoCME_Poda_Diag_18m": _summarize("Pool_NoCME_Poda_Diag_18m", "2021-01"),
    }

    # Detailed per-rule diagnostics in HOLDOUT A5
    diag_mrp_rules = {}
    for c in mrp_1x_m.columns:
        hm1, hm2 = mrp_1x_m.loc[blq_63 == "HOLDOUT", c], mrp_2x_m.loc[blq_63 == "HOLDOUT", c]
        diag_mrp_rules[c] = {"HOLDOUT_1x": stats_monthly_10vol(hm1), "HOLDOUT_2x": stats_monthly_10vol(hm2)}

    diag_cr3_bps = {}
    for name in cr3["daily_by_bps"][20].columns:
        diag_cr3_bps[name] = {}
        for bps in (10, 20, 30, 40):
            s_d = cr3["daily_by_bps"][bps][name]
            sh_s = s_d[cr3["blq"] == "HOLDOUT"]
            st_h = stats_serie(sh_s)
            diag_cr3_bps[name][f"bps_{bps}"] = st_h

    diag_ofi_bps = {}
    for name in ofi["daily_by_bps"][20].columns:
        diag_ofi_bps[name] = {}
        for bps in (10, 20, 30, 40):
            s_d = ofi["daily_by_bps"][bps][name]
            diag_ofi_bps[name][f"bps_{bps}"] = stats_serie(s_d[ofi["blq"] == "HOLDOUT"])

    c2_ind_ho_stats = {}
    for k in sorted(m_c2_ind.columns):
        st_k = stats_monthly_10vol(m_c2_ind[k])
        c2_ind_ho_stats[k] = {"sharpe": st_k["sharpe"], "t": st_k["t"], "mean_R_mes": round(float(m_c2_ind[k].mean()), 4)}

    # Fisher combinations in pure HOLDOUT A5 (never zero p)
    def _fisher(cols: list[str]) -> dict:
        ps = [max(float(primarios[c]["HOLDOUT"]["p_una_cola"]), 1e-12) for c in cols]
        stat = -2.0 * sum(log(p) for p in ps)
        return {"frentes": cols, "p_individuales": dict(zip(cols, ps)), "chi2": round(stat, 3), "df": 2 * len(cols), "p": round(float(_chi2_sf_par(stat, 2 * len(cols))), 6)}

    combinaciones = {
        "fisher_clean_63m_HOLDOUT": _fisher(["Carril2_Sell16", "Macro_RP_Canasta"]),
        "fisher_4_frentes_HOLDOUT": _fisher(["Carril2_Sell16", "Macro_RP_Canasta", "Cripto_v3_Canasta", "Cripto_OFI_Canasta"]),
    }

    h63_df = df_m[df_m["bloque"] == "HOLDOUT"]
    h18_df = h63_df.loc[h63_df.index >= "2021-01"]
    corr_h63 = h63_df[["Carril2_Sell16", "Macro_RP_Canasta", "Macro_RP_Diag_3Pos"]].corr().round(3).to_dict()
    corr_h18 = h18_df[["Carril2_Sell16", "Macro_RP_Canasta", "Cripto_v3_Canasta", "Cripto_OFI_Canasta"]].corr().round(3).to_dict()

    res = {
        "autorizacion_k27": AUTORIZACION_K27,
        "terminal_sellado": True,
        "paridad": par,
        "carril2_json_ref": c2_json.get("canasta"),
        "primarios": primarios,
        "diagnosticos": diagnosticos,
        "combinaciones": combinaciones,
        "correlaciones_HOLDOUT_63m": corr_h63,
        "correlaciones_HOLDOUT_18m": corr_h18,
        "detalle_mrp_rules": diag_mrp_rules,
        "detalle_cr3_bps": diag_cr3_bps,
        "detalle_ofi_bps": diag_ofi_bps,
        "detalle_carril2_16": c2_ind_ho_stats,
    }
    (OUT / "HOLDOUT_NOCME_RESULTADO.json").write_text(json.dumps(res, indent=2, ensure_ascii=False, default=float), encoding="utf-8")

    # Save reports + chart
    _write_reports(res)
    _chart_holdout_nocme(df_m, res)
    print("\n=== VEREDICTOS HOLDOUT A5 ===")
    for k, v in primarios.items():
        h = v["HOLDOUT"]
        print(f"  {k:24s} | n={h['meses']:2d} | DR Sh={v['DESC_REP']['sharpe']:5.3f} | H Sh={h['sharpe']:6.3f} t={h['t']:5.2f} p={h['p_una_cola']:6.4f} | MDD={h.get('mdd_at_10pct_vol', 0):6.2f}% | Stf={v['stouffer_REP_HOLDOUT']:5.2f} | {v['veredicto']}")
    print("  Fisher Clean63m p =", combinaciones["fisher_clean_63m_HOLDOUT"]["p"], "| Fisher 4F p =", combinaciones["fisher_4_frentes_HOLDOUT"]["p"])
    return 0


def _write_reports(res: dict) -> None:
    p = res["primarios"]
    d = res["diagnosticos"]
    f4 = res["combinaciones"]["fisher_4_frentes_HOLDOUT"]
    f2 = res["combinaciones"]["fisher_clean_63m_HOLDOUT"]

    md = [
        "# HOLDOUT-A5-NOCME: Veredicto de Apertura Única Conjunta (4 Frentes Limpios, `< 2026-10-01`)",
        "",
        "Estado: RESULTADO — confirmación **Etapa EF4** pre-registrada en [PREREGISTRO.md](PREREGISTRO.md) (`TRIAL_REGISTRY_GLOBAL.jsonl` + [HOLDOUT_VENTANAS.jsonl](../HOLDOUT_VENTANAS.jsonl)) con compuerta K27 levantada por autorización escrita de Nico (`2026-11-27`). **`TERMINAL` (`>= 2026-10-01`) permanece 100% sellado.**",
        "",
        "## 1. Veredicto Primario en `HOLDOUT A5` (`< 2026-10-01`)",
        "| Frente / Cartera | `N_H` | `DESC Sh` | `REP Sh` | `DR Sh` | **`HOLDOUT Sh / t`** | `p` (1-cola) | `MDD@10%` | `Stouffer(R,H)` | Veredicto |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]
    for k in ["Carril2_Sell16", "Macro_RP_Canasta", "Cripto_v3_Canasta", "Cripto_OFI_Canasta", "Super_v3_Clean63m_EQ", "Super_v3_Clean63m_HRP", "Pool_NoCME_Dyn_4F_63m", "Super_v3_NoCME_EQ", "Super_v3_NoCME_HRP"]:
        v = p[k]
        h = v["HOLDOUT"]
        md.append(
            f"| `{k}` | `{h['meses']}` | `{v['DESC']['sharpe']}` | `{v['REP']['sharpe']}` | `{v['DESC_REP']['sharpe']}` | "
            f"**`{h['sharpe']} / {h['t']}`** | `{h['p_una_cola']}` | `{h.get('mdd_at_10pct_vol', 0)}%` | `{v['stouffer_REP_HOLDOUT']}` (`p={v['p_stouffer']}`) | **`{v['veredicto']}`** |"
        )

    md += [
        "",
        f"- **Fisher combinado limpio (`63m`, `Carril2 + Macro_RP`):** `chi2 = {f2['chi2']}` (`df={f2['df']}`), **`p = {f2['p']}`**.",
        f"- **Fisher combinado `4` frentes (`Carril2 + Macro_RP + Cripto_v3 + Cripto_OFI`):** `chi2 = {f4['chi2']}` (`df={f4['df']}`), **`p = {f4['p']}`**.",
        f"- **Correlación mensual en `HOLDOUT A5` (`18m`):** `{res['correlaciones_HOLDOUT_18m']}`.",
        "",
        "## 2. Diagnósticos Secundarios y Sensibilidad (`NO deciden veredicto primario`)",
        "| Diagnóstico / Regla | `N_H` | `DR Sh` | **`HOLDOUT Sh / t`** | `p` | `MDD@10%` | Lectura |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :--- |",
    ]
    for k, v in d.items():
        h = v["HOLDOUT"]
        md.append(f"| `{k}` | `{h['meses']}` | `{v['DESC_REP']['sharpe']}` | **`{h['sharpe']} / {h['t']}`** | `{h['p_una_cola']}` | `{h.get('mdd_at_10pct_vol', 0)}%` | `{v['veredicto']}` |")

    md += [
        "",
        "Diagnóstico de grilla: sin grilla paramétrica — todas las reglas, ponderaciones `1/sd_DESC` y pesos `HRP` se congelaron antes de leer `HOLDOUT A5` tras verificar paridad exacta en `DESC+REP` (`diff_mrp={:.1e}`, `diff_cr3={:.1e}`, `diff_ofi={:.1e}`).".format(res["paridad"]["diff_mrp"], res["paridad"]["diff_cr3"], res["paridad"]["diff_ofi"]),
        f"Episodios: en `HOLDOUT A5` (`63m` / `18m`), `Pool_NoCME_Dyn_4F_63m` registra `Sh={p['Pool_NoCME_Dyn_4F_63m']['HOLDOUT']['sharpe']}` (`t={p['Pool_NoCME_Dyn_4F_63m']['HOLDOUT']['t']}`, `{p['Pool_NoCME_Dyn_4F_63m']['HOLDOUT'].get('pct_anios_pos', 0):.1%}` años+) y `Super_v3_NoCME_HRP` `Sh={p['Super_v3_NoCME_HRP']['HOLDOUT']['sharpe']}` (`t={p['Super_v3_NoCME_HRP']['HOLDOUT']['t']}`).",
        "",
        "Aporte al referente: entrega el veredicto limpio y definitivo en `HOLDOUT A5` sellado de los `4` frentes No-CME y sus carteras integradas, preservando intacta la barrera `TERMINAL >= 2026-10-01`.",
    ]
    (OUT / "RESULTADO.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    # Dedicated report for CARRIL2_A5 in canasta_amplia_20261127/RESULTADO_HOLDOUT_CARRIL2.md
    c2_ref = res["carril2_json_ref"]
    c2_h = p["Carril2_Sell16"]
    c2_md = [
        "# CANASTA-AMPLIA: Resultado del HOLDOUT A5 de la canasta Carril 2 sellada (`63` meses, 2026-11-27)",
        "",
        "Estado: RESULTADO — apertura única pre-registrada en [PREREGISTRO_HOLDOUT_CARRIL2.md](PREREGISTRO_HOLDOUT_CARRIL2.md) con autorización escrita K27 de Nico (`2026-11-27`), verificada contra [HOLDOUT_CARRIL2.json](HOLDOUT_CARRIL2.json). `TERMINAL >= 2026-10-01` sellado.",
        "",
        f"- **Motor diario (`HOLDOUT_CARRIL2.json`, operaciones=`{res['paridad'].get('carril2_ops', '') or 'ver json'}`):** Sharpe `{c2_ref.get('sharpe')}`, `t = {c2_ref.get('t')}`, meses `{c2_ref.get('meses')}`, meses+ `{c2_ref.get('pct_meses_pos')}`.",
        f"- **Serie mensual normalizada (`63` meses completos, `@10% vol`):** `DESC Sh = {c2_h['DESC']['sharpe']}`, `REP Sh = {c2_h['REP']['sharpe']}`, **`HOLDOUT Sh = {c2_h['HOLDOUT']['sharpe']} (t = {c2_h['HOLDOUT']['t']}, p = {c2_h['HOLDOUT']['p_una_cola']})`**, `MDD@10% = {c2_h['HOLDOUT'].get('mdd_at_10pct_vol', 0)}%`, `Stouffer(REP,H) = {c2_h['stouffer_REP_HOLDOUT']}`, veredicto **`{c2_h['veredicto']}`**.",
        "",
        "## Por época en `HOLDOUT A5` (`63` meses completos)",
        "| Época | `N_H` | `HOLDOUT Sh` | `t` | `% años+` | `MDD@10%` |",
        "| :--- | :---: | :---: | :---: | :---: | :---: |",
    ]
    for ep, ev in c2_h["epochs_HOLDOUT"].items():
        c2_md.append(f"| `{ep}` | `{ev['meses']}` | `{ev['sharpe']}` | `{ev['t']}` | `{ev.get('pct_anios_pos', 0):.1%}` | `{ev.get('mdd_at_10pct_vol', 0)}%` |")
    c2_md += [
        "",
        "Diagnóstico de grilla: sin grilla — 16 reglas-instrumento y pesos `1/sd_DESC` congelados en `PESOS_CARRIL2_SELLADA.json`.",
        f"Episodios: en `63` meses de `HOLDOUT A5` de `CARRIL2_A5`, la canasta logra `Sh={c2_h['HOLDOUT']['sharpe']}` (`t={c2_h['HOLDOUT']['t']}`, `{c2_h['HOLDOUT'].get('pct_anios_pos', 0):.1%}` años+).",
        "",
        "Aporte al referente: cierra el veredicto limpio de `63` meses sellados de la canasta `Carril 2 Sellada 16` e integra su resultado en [holdout_a5_nocme_20261127/RESULTADO.md](../holdout_a5_nocme_20261127/RESULTADO.md).",
    ]
    (ROOT / "docs/research/canasta_amplia_20261127/RESULTADO_HOLDOUT_CARRIL2.md").write_text("\n".join(c2_md) + "\n", encoding="utf-8")


if __name__ == "__main__":
    a = sys.argv[1:] + [""]
    if a[0] == "verificar_paridad":
        verificar_paridad()
    elif a[0] == "abrir":
        raise SystemExit(abrir())
    else:
        print(__doc__)
        raise SystemExit(2)
