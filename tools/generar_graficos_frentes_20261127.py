#!/usr/bin/env python3
"""Genera 2 graficos dark-mode para CRIPTO-PIT v3 + Frentes Ortogonales y Super-Canasta v2."""
from __future__ import annotations

import json
import shutil
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
OUT = ROOT / "docs/research/supercartera_v2_20261127"
BRAIN_ART = Path(r"C:\Users\nicoc\.gemini\antigravity\brain\417d395c-1bd7-4157-b782-277352881af1")

BG = "#0d1117"
PANEL = "#161b22"
GRID = "#30363d"
TEXT = "#e6edf3"
MUTED = "#8b949e"
CYAN = "#58a6ff"
GREEN = "#3fb950"
ORANGE = "#d29922"
RED = "#f85149"
PURPLE = "#bc8cff"
TEAL = "#39d353"


def _style(ax):
    ax.set_facecolor(PANEL)
    ax.tick_params(colors=TEXT, labelsize=8.5)
    for sp in ax.spines.values():
        sp.set_color(GRID)
    ax.grid(True, color=GRID, linestyle="--", linewidth=0.5, alpha=0.6)


def _save_copy(fig, fname: str) -> None:
    p = OUT / fname
    fig.savefig(p, dpi=160, facecolor=BG, bbox_inches="tight")
    plt.close(fig)
    if BRAIN_ART.exists():
        shutil.copy2(p, BRAIN_ART / fname)
    print("Saved chart:", p)


def chart_cripto_y_ortogonales() -> None:
    cr_j = json.loads((ROOT / "docs/research/cripto_pit_v3_20261127/RESULTADO.json").read_text(encoding="utf-8"))
    fo_j = json.loads((ROOT / "docs/research/frentes_ortogonales_20261127/RESULTADO.json").read_text(encoding="utf-8"))
    cr_df = pd.read_csv(ROOT / "docs/research/cripto_pit_v3_20261127/SERIES_CRIPTO_PIT_V3_DR.csv.gz", index_col=0, parse_dates=True)
    cr_valid = cr_df.dropna(how="all")

    fig, axes = plt.subplots(2, 2, figsize=(15, 10), facecolor=BG)
    fig.suptitle(
        "CRIPTO-PIT v3 (226 monedas + premiumIndex/BAB) & Frentes Ortogonales Global VolComp M1DK (Solo DESC+REP)",
        color=TEXT, fontsize=12.5, fontweight="bold", y=0.98,
    )

    # Panel 1: Cumulative equity of CR3 mechanisms + basket (20 bps + funding)
    ax = axes[0, 0]
    _style(ax)
    m_cr = cr_valid.groupby(cr_valid.index.to_period("M")).sum()
    x_lbl = [str(p) for p in m_cr.index]
    xi = np.arange(len(x_lbl))
    curves = [
        ("CR3_Canasta_InvVol", "CR3 Canasta InvVol (Sh=1.29, t=2.66)", TEAL, 2.6),
        ("CR3_XSMOM_21d_Stag5d", "XSMOM 21d Stag5d (Sh=1.08)", CYAN, 1.9),
        ("CR3_XSMOM_BetaNeut_Stag5d", "XSMOM BetaNeut (Sh=0.79)", PURPLE, 1.6),
        ("CR3_BAB_LowVol_Stag5d", "BAB LowVol (Sh=0.77, rho=-0.22)", ORANGE, 2.0),
        ("CR3_Basis_Carry_Stag5d", "Basis+Funding Carry (Sh=0.34)", RED, 1.3),
    ]
    for col, lbl, c, lw in curves:
        ax.plot(xi, m_cr[col].cumsum().to_numpy(float), label=lbl, color=c, linewidth=lw)
    ax.axhline(0, color=MUTED, linewidth=0.8)
    step = max(1, len(xi) // 6)
    ax.set_xticks(xi[::step])
    ax.set_xticklabels(x_lbl[::step], color=TEXT, fontsize=8)
    ax.set_ylabel("PnL acumulado USD (base $10k/tranche, DESC+REP)", color=TEXT, fontsize=9)
    ax.set_title("1. CRIPTO-PIT v3: 51m continuos DESC+REP (sin saltos HOLDOUT)", color=TEXT, fontsize=10.5, fontweight="bold")
    ax.legend(facecolor=PANEL, edgecolor=GRID, labelcolor=TEXT, fontsize=7.8)

    # Panel 2: Correlation heatmap among CR3 mechanisms
    ax = axes[0, 1]
    _style(ax)
    ax.grid(False)
    cols = ["CR3_XSMOM_21d_Stag5d", "CR3_XSMOM_BetaNeut_Stag5d", "CR3_Basis_Carry_Stag5d", "CR3_BAB_LowVol_Stag5d", "CR3_ResidMom_21d_2F_Stag5d"]
    short = ["XSMOM", "BetaNeut", "BasisCarry", "BAB_LowVol", "ResidMom2F"]
    mat = np.array([[cr_j["monthly_corr_DESC_REP"][r][c] for c in cols] for r in cols])
    ax.imshow(mat, cmap="coolwarm", vmin=-0.5, vmax=1.0, aspect="auto")
    ax.set_xticks(range(len(short)))
    ax.set_yticks(range(len(short)))
    ax.set_xticklabels(short, color=TEXT, fontsize=8.5, rotation=20, ha="right")
    ax.set_yticklabels(short, color=TEXT, fontsize=8.5)
    for i in range(len(short)):
        for j in range(len(short)):
            val = mat[i, j]
            tc = "#0d1117" if val > 0.45 else TEXT
            ax.text(j, i, f"{val:+.2f}", ha="center", va="center", color=tc, fontsize=8.5, fontweight="bold")
    ax.set_title("2. Correlacion mensual CR3: BAB ortogonal (-0.22 vs XSMOM)", color=TEXT, fontsize=10.5, fontweight="bold")

    # Panel 3: Cost sensitivity 10 -> 40 bps
    ax = axes[1, 0]
    _style(ax)
    bps_x = [10, 20, 30, 40]
    for col, lbl, c in [
        ("CR3_XSMOM_21d_Stag5d", "XSMOM 21d (2.7x/m)", CYAN),
        ("CR3_XSMOM_BetaNeut_Stag5d", "XSMOM BetaNeut (2.7x/m)", PURPLE),
        ("CR3_BAB_LowVol_Stag5d", "BAB LowVol (1.25x/m)", ORANGE),
        ("CR3_Basis_Carry_Stag5d", "Basis Carry (3.2x/m)", RED),
        ("CR3_ResidMom_21d_2F_Stag5d", "ResidMom 2F (2.6x/m)", MUTED),
    ]:
        ys = [cr_j["rules"][col][f"bps_{b}"]["DESC_REP"]["sharpe"] for b in bps_x]
        ax.plot(bps_x, ys, marker="o", linewidth=2.0, label=lbl, color=c)
    ax.axhline(0, color=MUTED, linewidth=0.8)
    ax.axvline(20, color=GREEN, linestyle=":", linewidth=1.1, label="Costo base realista (20 bps RT)")
    ax.set_xlabel("Costo Round-Trip (bps)", color=TEXT, fontsize=9)
    ax.set_ylabel("Sharpe DESC+REP (51m)", color=TEXT, fontsize=9)
    ax.set_title("3. Sensibilidad de Sharpe neto a friccion (10 -> 40 bps)", color=TEXT, fontsize=10.5, fontweight="bold")
    ax.legend(facecolor=PANEL, edgecolor=GRID, labelcolor=TEXT, fontsize=7.8)

    # Panel 4: Global VolComp M1DK pairs (8 bps vs 16 bps + 21-26)
    ax = axes[1, 1]
    _style(ax)
    pairs = fo_j["Global_VolComp_M1DK"]["pairs"]
    pkeys = list(pairs.keys())
    px = np.arange(len(pkeys))
    w = 0.27
    s8 = [pairs[k]["DESC_REP_8bps"]["sharpe"] for k in pkeys]
    s16 = [pairs[k]["DESC_REP_16bps"]["sharpe"] for k in pkeys]
    s19 = [pairs[k]["DESC_REP_19_26_8bps"]["sharpe"] for k in pkeys]
    ax.bar(px - w, s8, w, label="DR Completo (8 bps)", color=CYAN)
    ax.bar(px, s16, w, label="DR Doble Friccion (16 bps)", color=RED)
    ax.bar(px + w, s19, w, label="2019-2026 DR (8 bps)", color=GREEN)
    ax.axhline(0, color=MUTED, linewidth=0.8)
    ax.set_xticks(px)
    ax.set_xticklabels([k.replace("C2_", "") for k in pkeys], rotation=30, ha="right", color=TEXT, fontsize=7.5)
    ax.set_ylabel("Sharpe mensual", color=TEXT, fontsize=9)
    ax.set_title("4. Transferencia Global VolComp M1DK (Canasta 7 reglas 21-26 Sh=1.16)", color=TEXT, fontsize=10.5, fontweight="bold")
    ax.legend(facecolor=PANEL, edgecolor=GRID, labelcolor=TEXT, fontsize=7.8)

    plt.tight_layout(rect=[0, 0, 1, 0.95])
    _save_copy(fig, "cripto_pit_v3_basis_y_ortogonales.png")


def chart_supercartera_v2() -> None:
    sv2 = json.loads((OUT / "SUPERCARTERA_V2.json").read_text(encoding="utf-8"))
    df_d = pd.read_csv(OUT / "SERIES_SUPERCARTERA_V2_DR.csv.gz", index_col=0, parse_dates=True)
    df_d = df_d.dropna(how="all")

    # Monthly series exact 10% own annual vol (DESC+REP)
    m_df = df_d.groupby(df_d.index.to_period("M")).sum()
    fig, axes = plt.subplots(2, 2, figsize=(15, 10), facecolor=BG)
    fig.suptitle(
        "SUPERCARTERA v2: 3 Frentes Limpios (Carril 2 + CRIPTO v3 + Global VolComp) + CME a Volatilidad Identica (10%)",
        color=TEXT, fontsize=12.5, fontweight="bold", y=0.98,
    )

    # Panel 1: 10% vol monthly cumulative curves
    ax = axes[0, 0]
    _style(ax)
    xi = np.arange(len(m_df))
    xlbl = [str(p) for p in m_df.index]
    curves = [
        ("Super_v2_Core_TRZV_EQ", "Super v2 Core TRZV (Sh=2.86, sesgo CME)", CYAN, 2.2),
        ("Super_v2_NoCME_EQ", "Super v2 No-CME LIMPIA (Sh=1.56, Calmar=2.62)", TEAL, 2.6),
        ("CME_TRZV", "CME TRZV Solo (Sh=2.49, sesgo CME)", MUTED, 1.5),
        ("Cripto_v3_Canasta", "Cripto v3 Canasta (Sh=1.27)", PURPLE, 1.6),
        ("Global_VolComp_M1DK", "Global VolComp M1DK (Sh=1.16)", ORANGE, 1.6),
        ("Carril2_Sell16", "Carril 2 Sellada 16 (Sh=0.51)", "#79c0ff", 1.3),
    ]
    for col, lbl, c, lw in curves:
        s = m_df[col]
        sd = float(s.std(ddof=1))
        s10 = s / (sd * np.sqrt(12.0)) * 10.0 if sd > 0 else s
        ax.plot(xi, s10.cumsum().to_numpy(float), label=lbl, color=c, linewidth=lw)
    ax.axhline(0, color=MUTED, linewidth=0.8)
    step = max(1, len(xi) // 6)
    ax.set_xticks(xi[::step])
    ax.set_xticklabels(xlbl[::step], color=TEXT, fontsize=8)
    ax.set_ylabel("Retorno acumulado % (@ 10% vol anual propia)", color=TEXT, fontsize=9)
    ax.set_title("1. Curvas a Volatilidad Identica 10% (2021-2026 DESC+REP 51m)", color=TEXT, fontsize=10.5, fontweight="bold")
    ax.legend(facecolor=PANEL, edgecolor=GRID, labelcolor=TEXT, fontsize=7.6)

    # Panel 2: Front monthly correlation heatmap
    ax = axes[0, 1]
    _style(ax)
    ax.grid(False)
    ccols = ["CME_TRZV", "CME_Div10", "Carril2_Sell16", "Global_VolComp_M1DK", "Cripto_v3_Canasta", "FundedSync_O_1MNQ"]
    cshort = ["CME_TRZV", "CME_Div10", "Carril2", "GlobalVol", "Cripto_v3", "O_1MNQ"]
    cmat = np.array([[sv2["corr_monthly_21_26_DR"][r][c] for c in ccols] for r in ccols])
    ax.imshow(cmat, cmap="coolwarm", vmin=-0.5, vmax=1.0, aspect="auto")
    ax.set_xticks(range(len(cshort)))
    ax.set_yticks(range(len(cshort)))
    ax.set_xticklabels(cshort, color=TEXT, fontsize=8.3, rotation=20, ha="right")
    ax.set_yticklabels(cshort, color=TEXT, fontsize=8.3)
    for i in range(len(cshort)):
        for j in range(len(cshort)):
            v = cmat[i, j]
            ax.text(j, i, f"{v:+.2f}", ha="center", va="center", color="#0d1117" if v > 0.45 else TEXT, fontsize=8.3, fontweight="bold")
    ax.set_title("2. Correlaciones mensuales entre frentes (GlobalVol vs Carril2 = +0.13)", color=TEXT, fontsize=10.5, fontweight="bold")

    # Panel 3: Bootstrap 20k Weekly Calmar & MDD p95 + CSCV callouts
    ax = axes[1, 0]
    _style(ax)
    kres = sv2.get("kaggle_summary") or {}
    bt = kres.get("bootstrap_20k_weekly_10pct_vol", {})
    bkeys = ["Carril2_Sell16", "Global_VolComp_M1DK", "Cripto_v3_Canasta", "Super_v2_NoCME_EQ", "Super_v2_EQ", "Super_v2_Core_TRZV_EQ", "CME_TRZV"]
    blbls = ["Carril2", "GlobalVol", "Cripto_v3", "NoCME_EQ\n(LIMPIO)", "Super_EQ\n(CME)", "CoreTRZV\n(CME)", "CME_TRZV\n(CME)"]
    bx = np.arange(len(bkeys))
    cals = [bt.get(k, {}).get("calmar_median", 0.0) for k in bkeys]
    mdds = [abs(bt.get(k, {}).get("mdd_p95_pct", 0.0)) for k in bkeys]
    w = 0.36
    b1 = ax.bar(bx - w / 2, cals, w, label="Calmar p50 (Boot 20k @10%vol)", color=TEAL)
    ax2 = ax.twinx()
    b2 = ax2.bar(bx + w / 2, mdds, w, label="MDD p95 % (@10%vol, menor mejor)", color=RED, alpha=0.8)
    ax2.tick_params(colors=RED, labelsize=8.5)
    ax.set_xticks(bx)
    ax.set_xticklabels(blbls, color=TEXT, fontsize=7.8)
    ax.set_ylabel("Calmar p50 (10% vol)", color=TEAL, fontsize=9)
    ax2.set_ylabel("|MDD p95| % (10% vol)", color=RED, fontsize=9)
    cscv_nc = kres.get("cscv", {}).get("2_clean_non_cme_28rules", {})
    cscv_c2 = kres.get("cscv", {}).get("1_clean_carril2_16rules", {})
    ax.set_title(
        f"3. Boot 20k Semanal | CSCV No-CME 28r OOS Sh={cscv_nc.get('basket_1N_OOS_SR_median', '?')} (C2={cscv_c2.get('basket_1N_OOS_SR_median', '?')})",
        color=TEXT, fontsize=9.8, fontweight="bold",
    )
    lines1, lbls1 = ax.get_legend_handles_labels()
    lines2, lbls2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, lbls1 + lbls2, facecolor=PANEL, edgecolor=GRID, labelcolor=TEXT, fontsize=7.5, loc="upper left")

    # Panel 4: CME 0.5x shrinkage stress + Pooled Holdout Power
    ax = axes[1, 1]
    _style(ax)
    st = sv2["shrinkage_stress_10pct_vol"]
    pkeys = ["CME_TRZV", "Super_v2_NoCME_EQ", "Super_v2_EQ", "Super_v2_Core_TRZV_EQ"]
    plbls = ["CME_TRZV", "Super No-CME\n(Limpia)", "Super 4F\n(Div10)", "Super Core\n(TRZV)"]
    px = np.arange(len(pkeys))
    w = 0.26
    for idx_s, (sc_k, sc_l, col) in enumerate([
        ("CME_1.0x__Oth_1.0x", "Observado 1.0x/1.0x", CYAN),
        ("CME_0.5x__Oth_0.7x", "Estres CME 0.5x / Oth 0.7x", ORANGE),
        ("CME_0.5x__Oth_0.5x", "Estres Severo 0.5x/0.5x", RED),
    ]):
        ys = [st[sc_k][pk]["sharpe"] for pk in pkeys]
        ax.bar(px + (idx_s - 1) * w, ys, w, label=sc_l, color=col)
    ax.set_xticks(px)
    ax.set_xticklabels(plbls, color=TEXT, fontsize=8.3)
    ax.set_ylabel("Sharpe bajo contraccion", color=TEXT, fontsize=9)
    pw = sv2["pooled_sealed_holdout_power"]
    pw_nocme = pw.get("5_Pooled_NoCME_3F_21_26", {})
    pw_dyn = pw.get("6_Pooled_NoCME_3F_Dyn_06_26", {})
    ax.set_title(
        f"4. Estres CME 0.5x | Pot. Holdout No-CME: 18m(0.7x)={pw_nocme.get('potencia_sh07', '?')} / 63m={pw_dyn.get('potencia_sh07', '?')}",
        color=TEXT, fontsize=9.8, fontweight="bold",
    )
    ax.legend(facecolor=PANEL, edgecolor=GRID, labelcolor=TEXT, fontsize=7.6)

    plt.tight_layout(rect=[0, 0, 1, 0.95])
    _save_copy(fig, "supercartera_v2_frentes_y_cscv.png")


def main() -> None:
    if plt is None:
        print("matplotlib no disponible; saltando generacion de graficos.")
        return
    chart_cripto_y_ortogonales()
    chart_supercartera_v2()


if __name__ == "__main__":
    main()
