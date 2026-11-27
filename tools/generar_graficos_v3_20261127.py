#!/usr/bin/env python3
"""Genera 2 graficos dark-mode para MACRO_RISK_PREMIA, CRIPTO_OFI_PIT y SUPERCARTERA v3."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ImportError:
    plt = None

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))

from generar_graficos_audit_20261127 import BG, CYAN, GREEN, GRID, MUTED, ORANGE, PANEL, PURPLE, RED, TEAL, TEXT, _save_and_copy, _style_ax  # noqa: E402

OUT = ROOT / "docs/research/supercartera_v3_20261127"


def chart_macro_y_ofi() -> None:
    mrp_j = json.loads((ROOT / "docs/research/macro_risk_premia_20261127/RESULTADO.json").read_text(encoding="utf-8"))
    ofi_j = json.loads((ROOT / "docs/research/cripto_ofi_20261127/RESULTADO.json").read_text(encoding="utf-8"))
    mrp_d = pd.read_csv(ROOT / "docs/research/macro_risk_premia_20261127/SERIES_MACRO_RP_DR.csv.gz", index_col=0, parse_dates=True).dropna(how="all")
    ofi_d = pd.read_csv(ROOT / "docs/research/cripto_ofi_20261127/SERIES_CRIPTO_OFI_DR.csv.gz", index_col=0, parse_dates=True).dropna(how="all")

    fig, axes = plt.subplots(2, 2, figsize=(15, 10), facecolor=BG)
    fig.suptitle(
        "Frentes Limpios Nuevos: MACRO_RISK_PREMIA (2006-2026, 0 iteracion REP) & CRIPTO_OFI_PIT (Flujo Taker No-OHLC)",
        color=TEXT, fontsize=12.5, fontweight="bold", y=0.98,
    )

    # Panel 1: Cumulative 10% vol curves of Macro Risk Premia (2006-2026 DESC+REP)
    ax = axes[0, 0]
    _style_ax(ax)
    m_mrp = mrp_d.groupby(mrp_d.index.to_period("M")).sum()
    xi = np.arange(len(m_mrp))
    xl = [str(p) for p in m_mrp.index]
    for col, lbl, c, lw in [
        ("RP4_Rates_Curve_Credit", "RP4 Tasas Curva+Credito (Sh=0.37, REP=0.64)", TEAL, 2.3),
        ("RP2_Sector_BAB_LowBeta", "RP2 Sectores BAB LowBeta (Sh=0.31, REP=0.67)", CYAN, 2.0),
        ("RP5_NonEq_MultiSpeed_Trend", "RP5 Tendencia MultiVel No-Eq (Sh=0.15, REP=0.30)", ORANGE, 1.5),
        ("RP1_Sector_XSMOM_Neut", "RP1 Sectores XSMOM (Sh=-0.07)", RED, 1.1),
        ("RP3_Country_XSMOM_Neut", "RP3 Paises XSMOM (Sh=-0.26)", MUTED, 1.1),
    ]:
        s = m_mrp[col]
        sd = float(s.std(ddof=1))
        s10 = s / (sd * np.sqrt(12.0)) * 10.0 if sd > 0 else s
        ax.plot(xi, s10.cumsum().to_numpy(float), label=lbl, color=c, linewidth=lw)
    ax.axhline(0, color=MUTED, linewidth=0.8)
    step = max(1, len(xi) // 7)
    ax.set_xticks(xi[::step])
    ax.set_xticklabels(xl[::step], color=TEXT, fontsize=8)
    ax.set_ylabel("Retorno acumulado % (@10% vol anual)", color=TEXT, fontsize=9)
    ax.set_title("1. MACRO_RISK_PREMIA: 186m DESC+REP (2006-2026, beta_SPY ~ 0)", color=TEXT, fontsize=10.5, fontweight="bold")
    ax.legend(facecolor=PANEL, edgecolor=GRID, labelcolor=TEXT, fontsize=7.6)

    # Panel 2: Macro Risk Premia DESC vs REP vs 2x Stress
    ax = axes[0, 1]
    _style_ax(ax)
    rk = list(mrp_j["rules"].keys())
    rl = ["Sec_XSMOM", "Sec_BAB", "Ctry_XSMOM", "Rates_Cred", "NonEq_Trend"]
    px = np.arange(len(rk))
    w = 0.26
    ax.bar(px - w, [mrp_j["rules"][k]["DESC"]["sharpe"] for k in rk], w, label="DESC (144m)", color=CYAN)
    ax.bar(px, [mrp_j["rules"][k]["REP"]["sharpe"] for k in rk], w, label="REP limpia (42m)", color=GREEN)
    ax.bar(px + w, [mrp_j["rules"][k]["DESC_REP_stress2x"]["sharpe"] for k in rk], w, label="DR 2x Costos+Borrow", color=RED)
    ax.axhline(0, color=MUTED, linewidth=0.8)
    ax.set_xticks(px)
    ax.set_xticklabels(rl, color=TEXT, fontsize=8.3)
    ax.set_ylabel("Sharpe anual", color=TEXT, fontsize=9)
    ax.set_title("2. Macro Primas: DESC vs REP limpia (RP2 & RP4 suben en REP)", color=TEXT, fontsize=10.5, fontweight="bold")
    ax.legend(facecolor=PANEL, edgecolor=GRID, labelcolor=TEXT, fontsize=7.8)

    # Panel 3: CRIPTO-OFI-PIT cumulative equity curves (20 bps + funding)
    ax = axes[1, 0]
    _style_ax(ax)
    m_ofi = ofi_d.groupby(ofi_d.index.to_period("M")).sum()
    xo = np.arange(len(m_ofi))
    xol = [str(p) for p in m_ofi.index]
    for col, lbl, c, lw in [
        ("OFI1_TakerFlow_21d_Stag5d", "OFI1 Taker Flow 21d (Sh=0.91, corr_XSMOM=+0.21)", TEAL, 2.3),
        ("OFI_Canasta_InvVol", "OFI Canasta InvVol (Sh=0.60, corr_XSMOM=+0.01)", CYAN, 2.0),
        ("OFI3_WhaleFlow_14d_Stag5d", "OFI3 Whale Ticket Flow 14d (Sh=0.10)", ORANGE, 1.4),
        ("OFI2_FlowReturn_Div_14d_Stag5d", "OFI2 Flow-Return Div 14d (Sh=-0.26)", RED, 1.2),
    ]:
        ax.plot(xo, m_ofi[col].cumsum().to_numpy(float), label=lbl, color=c, linewidth=lw)
    ax.axhline(0, color=MUTED, linewidth=0.8)
    so = max(1, len(xo) // 6)
    ax.set_xticks(xo[::so])
    ax.set_xticklabels(xol[::so], color=TEXT, fontsize=8)
    ax.set_ylabel("PnL acumulado USD (base $10k/tranche)", color=TEXT, fontsize=9)
    ax.set_title("3. CRIPTO_OFI_PIT (Flujo Taker No-OHLC, 20 bps + funding)", color=TEXT, fontsize=10.5, fontweight="bold")
    ax.legend(facecolor=PANEL, edgecolor=GRID, labelcolor=TEXT, fontsize=7.6)

    # Panel 4: OFI cost decay (10 -> 40 bps) & orthogonality callout
    ax = axes[1, 1]
    _style_ax(ax)
    bps_x = [10, 20, 30, 40]
    for k, lbl, c in [
        ("OFI1_TakerFlow_21d_Stag5d", "OFI1 Taker 21d (1.54x/m, corr=+0.205)", TEAL),
        ("OFI3_WhaleFlow_14d_Stag5d", "OFI3 Whale 14d (1.72x/m, corr=-0.188)", ORANGE),
        ("OFI2_FlowReturn_Div_14d_Stag5d", "OFI2 Divergencia 14d (2.25x/m)", RED),
    ]:
        ys = [ofi_j["rules"][k][f"bps_{b}"]["DESC_REP"]["sharpe"] for b in bps_x]
        ax.plot(bps_x, ys, marker="o", linewidth=2.1, label=lbl, color=c)
    ax.axhline(0, color=MUTED, linewidth=0.8)
    ax.axvline(20, color=GREEN, linestyle=":", linewidth=1.1, label="Costo base 20 bps RT + funding")
    ax.set_xlabel("Costo Round-Trip (bps)", color=TEXT, fontsize=9)
    ax.set_ylabel("Sharpe DESC+REP (51m)", color=TEXT, fontsize=9)
    ax.set_title("4. CRIPTO_OFI_PIT: Sensibilidad a Friccion y Baja Rotacion", color=TEXT, fontsize=10.5, fontweight="bold")
    ax.legend(facecolor=PANEL, edgecolor=GRID, labelcolor=TEXT, fontsize=7.6)

    plt.tight_layout(rect=[0, 0, 1, 0.95])
    _save_and_copy(fig, "macro_rp_y_cripto_ofi_20261127.png", out=OUT)


def chart_supercartera_v3() -> None:
    sv3 = json.loads((OUT / "SUPERCARTERA_V3.json").read_text(encoding="utf-8"))
    d_long = pd.read_csv(OUT / "SERIES_CLEAN63M_06_26_DR.csv.gz", index_col=0, parse_dates=True).dropna(how="all")
    d21 = pd.read_csv(OUT / "SERIES_SUPERCARTERA_V3_DR.csv.gz", index_col=0, parse_dates=True).dropna(how="all")

    m_long = d_long.groupby(d_long.index.to_period("M")).sum()
    m21 = d21.groupby(d21.index.to_period("M")).sum()

    fig, axes = plt.subplots(2, 2, figsize=(15, 10), facecolor=BG)
    fig.suptitle(
        "SUPERCARTERA v3: Pozo Limpio 63m Cero-Iteracion (2006-2026) + Multi-Frente 21-26 + HRP Corregido + CSCV",
        color=TEXT, fontsize=12.5, fontweight="bold", y=0.98,
    )

    # Panel 1: 2006-2026 Pure Clean 63m curves @ 10% vol
    ax = axes[0, 0]
    _style_ax(ax)
    xi = np.arange(len(m_long))
    xl = [str(p) for p in m_long.index]
    for col, lbl, c, lw in [
        ("Carril2_Sell16", "Carril 2 Sellada 16 (Sh=0.86, MDD=-13.2%)", CYAN, 1.8),
        ("Super_v3_Clean63m_EQ", "Pozo Limpio 63m EQ (Sh=0.85, REP=1.05)", TEAL, 2.3),
        ("Macro_RP_Canasta", "Macro RP Canasta RP4 (Sh=0.37, 21-26=0.77)", ORANGE, 1.7),
    ]:
        s = m_long[col]
        sd = float(s.std(ddof=1))
        s10 = s / (sd * np.sqrt(12.0)) * 10.0 if sd > 0 else s
        ax.plot(xi, s10.cumsum().to_numpy(float), label=lbl, color=c, linewidth=lw)
    ax.axhline(0, color=MUTED, linewidth=0.8)
    st = max(1, len(xi) // 7)
    ax.set_xticks(xi[::st])
    ax.set_xticklabels(xl[::st], color=TEXT, fontsize=8)
    ax.set_ylabel("Retorno acumulado % (@10% vol anual)", color=TEXT, fontsize=9)
    ax.set_title("1. Pozo Limpio 63m Cero-Iteracion (2006-2026, 186m DESC+REP)", color=TEXT, fontsize=10.5, fontweight="bold")
    ax.legend(facecolor=PANEL, edgecolor=GRID, labelcolor=TEXT, fontsize=7.6)

    # Panel 2: 2021-2026 Multi-front @ 10% vol
    ax = axes[0, 1]
    _style_ax(ax)
    x2 = np.arange(len(m21))
    xl2 = [str(p) for p in m21.index]
    for col, lbl, c, lw in [
        ("Super_v3_Core_TRZV_EQ", "Super v3 Core TRZV (Sh=2.49, Calmar=7.12, CME)", CYAN, 2.3),
        ("Super_v3_NoCME_HRP", "Super v3 No-CME HRP (Sh=1.55, Calmar=2.05)", TEAL, 2.5),
        ("Super_v3_Clean63m_EQ_21_26", "Pozo Limpio 63m EQ en 21-26 (Sh=0.88)", ORANGE, 1.7),
        ("Carril2_Sell16", "Carril 2 Sellada 16 en 21-26 (Sh=0.51)", PURPLE, 1.4),
    ]:
        s = m21[col]
        sd = float(s.std(ddof=1))
        s10 = s / (sd * np.sqrt(12.0)) * 10.0 if sd > 0 else s
        ax.plot(x2, s10.cumsum().to_numpy(float), label=lbl, color=c, linewidth=lw)
    ax.axhline(0, color=MUTED, linewidth=0.8)
    st2 = max(1, len(x2) // 6)
    ax.set_xticks(x2[::st2])
    ax.set_xticklabels(xl2[::st2], color=TEXT, fontsize=8)
    ax.set_ylabel("Retorno acumulado % (@10% vol anual)", color=TEXT, fontsize=9)
    ax.set_title("2. Tramo 2021-2026: HRP Reg vs EQ a 10% Vol (Super No-CME)", color=TEXT, fontsize=10.5, fontweight="bold")
    ax.legend(facecolor=PANEL, edgecolor=GRID, labelcolor=TEXT, fontsize=7.6)

    # Panel 3: Boot 20k Weekly Calmar vs MDD p95 & CSCV callouts
    ax = axes[1, 0]
    _style_ax(ax)
    kr = sv3.get("kaggle_summary") or {}
    bt = kr.get("boot_20k", {})
    bkeys = ["Carril2_Sell16_06_26", "Macro_RP_Canasta_06_26", "Super_v3_Clean63m_EQ", "Super_v3_NoCME_EQ", "Super_v3_NoCME_HRP", "Super_v3_Core_TRZV_EQ", "CME_TRZV"]
    blbls = ["C2_06_26", "MacroRP", "Clean63m", "NoCME_EQ", "NoCME_HRP", "CoreTRZV", "CME_TRZV"]
    bx = np.arange(len(bkeys))
    w = 0.36
    ax.bar(bx - w / 2, [bt.get(k, {}).get("calmar_p50", 0.0) for k in bkeys], w, label="Calmar p50 (Boot 20k)", color=TEAL)
    ax2 = ax.twinx()
    ax2.bar(bx + w / 2, [abs(bt.get(k, {}).get("mdd_p95", 0.0)) for k in bkeys], w, label="|MDD p95| % (@10%vol)", color=RED, alpha=0.8)
    ax2.tick_params(colors=RED, labelsize=8.5)
    ax.set_xticks(bx)
    ax.set_xticklabels(blbls, color=TEXT, fontsize=7.8, rotation=15, ha="right")
    ax.set_ylabel("Calmar p50", color=TEAL, fontsize=9)
    ax2.set_ylabel("|MDD p95| %", color=RED, fontsize=9)
    c1 = kr.get("cscv", {}).get("1_clean_long_06_26", {}).get("basket_1N_OOS_SR_med", "?")
    c2 = kr.get("cscv", {}).get("2_clean_nocme_21_26", {}).get("basket_1N_OOS_SR_med", "?")
    ax.set_title(f"3. Boot 20k | CSCV 1/N OOS Sh: Clean06-26={c1} | NoCME21-26={c2}", color=TEXT, fontsize=9.8, fontweight="bold")

    # Panel 4: HRP Weights (Fixed Reg vs Equal) + Sealed Holdout Power
    ax = axes[1, 1]
    _style_ax(ax)
    hrp_nc = sv3["hrp_nocme_weights"]
    h_keys = list(hrp_nc.keys())
    hx = np.arange(len(h_keys))
    eq_w = 1.0 / max(1, len(h_keys))
    ax.bar(hx - 0.18, [hrp_nc[k] for k in h_keys], 0.35, label="HRP Regularizado (0.85*S+0.15*D)", color=CYAN)
    ax.bar(hx + 0.18, [eq_w] * len(h_keys), 0.35, label="1/N Igualitario", color=MUTED, alpha=0.7)
    ax.set_xticks(hx)
    ax.set_xticklabels([k.replace("_Canasta", "") for k in h_keys], color=TEXT, fontsize=8.0, rotation=15, ha="right")
    ax.set_ylabel("Peso asignado (fraccion)", color=TEXT, fontsize=9)
    pw = sv3["pooled_pwr"]
    ax.set_title(
        f"4. Pesos HRP No-CME Reales | Pot 63m (0.7x): Clean={pw['3_Pool_Clean_63m_ZeroIter']['pot_07x']} / Dyn={pw['5_Pool_NoCME_Dyn_63m']['pot_07x']}",
        color=TEXT, fontsize=9.8, fontweight="bold",
    )
    ax.legend(facecolor=PANEL, edgecolor=GRID, labelcolor=TEXT, fontsize=7.6)

    plt.tight_layout(rect=[0, 0, 1, 0.95])
    _save_and_copy(fig, "supercartera_v3_clean_63m_y_cscv.png", out=OUT)


def main() -> None:
    if plt is None:
        print("matplotlib no disponible; saltando graficos v3.")
        return
    chart_macro_y_ofi()
    chart_supercartera_v3()


if __name__ == "__main__":
    main()
