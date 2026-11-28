#!/usr/bin/env python3
"""Genera los 3 graficos dark-mode post-auditoria (Iteraciones 1 y 2) del Marco Sin Forward."""
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
OUT = ROOT / "docs" / "research" / "auditoria_claude_20261127"
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


def _style_ax(ax):
    ax.set_facecolor(PANEL)
    ax.tick_params(colors=TEXT, labelsize=8.5)
    for spine in ax.spines.values():
        spine.set_color(GRID)
    ax.grid(True, color=GRID, linestyle="--", linewidth=0.5, alpha=0.6)


def _save_and_copy(fig, fname: str, out: Path = OUT) -> None:
    p = out / fname
    fig.savefig(p, dpi=160, facecolor=BG, bbox_inches="tight")
    plt.close(fig)
    if BRAIN_ART.exists():
        shutil.copy2(p, BRAIN_ART / fname)
    print("Saved chart:", p)


def chart1_auditoria_claude(aud: dict, msf: dict, cr_j: dict) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(15, 10), facecolor=BG)
    fig.suptitle(
        "Auditoria Forense (PR #203 + Auto-Auditoria It. 1-2): Trampa K27, Decaimiento Carril 2 y Fix Cripto",
        color=TEXT, fontsize=13.0, fontweight="bold", y=0.98,
    )

    # Panel 1: Required Dev Sharpe for K27 (80% power)
    ax = axes[0, 0]
    _style_ax(ax)
    k27 = aud["k27_impossibility"]["required_dev_sharpe_for_K27_80pct"]
    hs = ["holdout_18m", "holdout_22m", "holdout_45m", "holdout_63m", "holdout_100m"]
    xl = ["18m\n(Cripto)", "22m\n(CME A5)", "45m", "63m\n(Carril 2)", "100m"]
    for sh_k, lbl, col in [("shrink_0.5", "Shrinkage 0.5x", RED), ("shrink_0.7", "Shrinkage 0.7x", ORANGE), ("shrink_1.0", "Sin shrinkage 1.0x", CYAN)]:
        ax.plot(xl, [k27[h][sh_k] for h in hs], marker="o", linewidth=2.2, label=lbl, color=col)
    ax.axhspan(0.5, 1.1, color=GREEN, alpha=0.14, label="Sharpe realista regla/familia (0.5-1.1)")
    ax.set_ylabel("Sharpe minimo requerido en DESC", color=TEXT, fontsize=9.5)
    ax.set_title("1. Por que K27 (80% potencia) es imposible en 1 familia", color=TEXT, fontsize=10.5, fontweight="bold")
    ax.legend(facecolor=PANEL, edgecolor=GRID, labelcolor=TEXT, fontsize=8)

    # Panel 2: Orthogonal pooling power 63m (0.7x)
    ax = axes[0, 1]
    _style_ax(ax)
    pool = aud["k27_impossibility"]["orthogonal_pooling_SRind_070"]
    ms = ["M_1", "M_3", "M_5", "M_10", "M_15", "M_20", "M_30"]
    mx = [1, 3, 5, 10, 15, 20, 30]
    for rk, lbl, col in [("rho_0.05", "rho = 0.05", GREEN), ("rho_0.1", "rho = 0.10", CYAN), ("rho_0.15", "rho = 0.15", ORANGE), ("rho_0.25", "rho = 0.25", RED)]:
        ax.plot(mx, [pool[rk][m]["power_63m_sh07"] * 100 for m in ms], marker="s", linewidth=2.0, label=lbl, color=col)
    ax.axhline(80, color=TEXT, linestyle=":", linewidth=1.2, label="Meta 80% potencia (63m sellado, 0.7x)")
    ax.set_xlabel("Cantidad M de mecanismos decorrelacionados (SR_ind = 0.70)", color=TEXT, fontsize=9.5)
    ax.set_ylabel("Potencia Holdout (%)", color=TEXT, fontsize=9.5)
    ax.set_title("2. Solucion matematica de Nico: Sumar M estrategias ortogonales", color=TEXT, fontsize=10.5, fontweight="bold")
    ax.legend(facecolor=PANEL, edgecolor=GRID, labelcolor=TEXT, fontsize=8)

    # Panel 3: Carril 2 Sellada 16 Secular Decay by Epoch (DESC vs REP vs DR, zero holdout!)
    ax = axes[1, 0]
    _style_ax(ax)
    ep_map = msf["carril2_sellada16_by_epoch"]
    eps = ["2006_2012", "2013_2018", "2019_2026", "2021_2026"]
    elbls = ["2006-12\n(63m DR)", "2013-18\n(54m DR)", "2019-26\n(69m DR)", "2021-26\n(51m DR)"]
    x = np.arange(len(eps))
    w = 0.27
    ax.bar(x - w, [ep_map[e]["DESC"]["sharpe"] for e in eps], w, label="DESC", color=CYAN)
    ax.bar(x, [ep_map[e]["REP"]["sharpe"] for e in eps], w, label="REP", color=ORANGE)
    ax.bar(x + w, [ep_map[e]["DESC_REP"]["sharpe"] for e in eps], w, label="DESC+REP", color=GREEN)
    ax.axhline(0, color=MUTED, linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(elbls, fontsize=8.5, color=TEXT)
    ax.set_ylabel("Sharpe anualizado", color=TEXT, fontsize=9.5)
    ax.set_title("3. Hallazgo It.1: Decaimiento secular Carril 2 post-2018 (DESC 0.13)", color=TEXT, fontsize=10.0, fontweight="bold")
    ax.legend(facecolor=PANEL, edgecolor=GRID, labelcolor=TEXT, fontsize=8)

    # Panel 4: Cripto PIT bug vs clean staggered ex-TradFi (USD/m in REP and DESC)
    ax = axes[1, 1]
    _style_ax(ax)
    xs_r = cr_j["rules"]["CR2_XSMOM_Stag5d"]["bps_20"]
    co_r = cr_j["CR2_Core_XSMOM_ResidMom_bps20"]
    lbls = [
        "Claude Top25\nEMA_4H REP",
        "Claude Top25\nCR_1N REP",
        "Claude Bug L177\n(Audit DESC+REP)",
        "v2 Core XSMOM+Res\n(Ex-TradFi DR)",
        "v2 XSMOM Stag5d\n(Ex-TradFi DR)",
    ]
    vals = [
        aud["cripto_pit_audit"]["claude_CR1N_vs_EMA4H_REP_drag"]["top25_base20_EMA4H_REP_usd_m"],
        aud["cripto_pit_audit"]["claude_CR1N_vs_EMA4H_REP_drag"]["top25_base20_CR1N_REP_usd_m"],
        cr_j["rules"]["ABL_Claude_XSMOM_Bug"]["bps_20"]["DESC_REP"]["usd_mes"],
        co_r["DESC_REP"]["usd_mes"],
        xs_r["DESC_REP"]["usd_mes"],
    ]
    cols = [RED if v < 0 else (ORANGE if i == 2 else GREEN) for i, v in enumerate(vals)]
    bars = ax.barh(lbls, vals, color=cols, height=0.55)
    ax.axvline(0, color=TEXT, linewidth=0.8)
    for b, v in zip(bars, vals):
        ax.text(v + (6 if v >= 0 else -6), b.get_y() + b.get_height() / 2, f"${v:+.1f}/m", va="center", ha="left" if v >= 0 else "right", color=TEXT, fontsize=8.5)
    ax.set_xlabel("USD/mes neto (20 bps RT + funding, $10k/lado)", color=TEXT, fontsize=9)
    ax.set_title("4. Cripto PIT: bug L177 + ruido 4H vs XSMOM escalonado ex-TradFi", color=TEXT, fontsize=10.0, fontweight="bold")
    ax.set_xlim(-225, 290)

    plt.tight_layout(rect=[0, 0, 1, 0.95])
    _save_and_copy(fig, "auditoria_claude_k27_y_sesgos.png")


def chart2_frentes_v2(cr_j: dict, fut_j: dict, cr_s: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(15, 10), facecolor=BG)
    fig.suptitle(
        "Avances v2 Auditados (HOLDOUT SELLADO): CRIPTO-PIT Staggered Ex-TradFi y Falla Roll Yahoo =F",
        color=TEXT, fontsize=13.0, fontweight="bold", y=0.98,
    )

    # Panel 1: XSMOM Phase 0..4 vs Staggered 5d & Cost Stress (10-40 bps)
    ax = axes[0, 0]
    _style_ax(ax)
    ph = cr_j["xsmom_audit"]["phases_frozen_5d_Top20"]
    xs = cr_j["rules"]["CR2_XSMOM_Stag5d"]
    lbls = ["Ph 0", "Ph 1", "Ph 2", "Ph 3", "Ph 4", "Stag5d\n10bps", "Stag5d\n20bps", "Stag5d\n30bps", "Stag5d\n40bps"]
    vals = [ph[f"Phase_{i}"]["DESC_REP"]["sharpe"] for i in range(5)] + [
        xs[f"bps_{b}"]["DESC_REP"]["sharpe"] for b in (10, 20, 30, 40)
    ]
    cols = [CYAN if i != 0 else ORANGE for i in range(5)] + [GREEN, GREEN, TEAL, TEAL]
    bars = ax.bar(lbls, vals, color=cols, width=0.6)
    ax.axvline(4.5, color=MUTED, linestyle="--", linewidth=1)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.03, f"{v:.2f}", ha="center", color=TEXT, fontsize=8)
    ax.set_ylabel("Sharpe DESC+REP (51m, ex-TradFi)", color=TEXT, fontsize=9)
    ax.set_title("1. Hallazgo It.2: sesgo de fase (Ph 0=1.29) eliminado con Stag5d (1.08 -> 0.80 @40bps)", color=TEXT, fontsize=9.8, fontweight="bold")
    ax.tick_params(axis="x", labelsize=7.8)

    # Panel 2: Long-Short vs Long-Only vs Short-Only vs LongAlts-ShortBTC & Top10
    ax = axes[0, 1]
    _style_ax(ax)
    d20 = cr_j["xsmom_audit"]["decomp_Top20_hyst_4L4S"]
    d10 = cr_j["xsmom_audit"]["decomp_Top10_liq_3L3S"]
    dlbls = ["Top20\nL/S Alts", "Top20\nLong-Only", "Top20\nShort-Only", "Top20\nLong-ShBTC", "Top10\nL/S Alts"]
    sh_dr = [d20["Long-Short_Alts"]["sharpe"], d20["Long-Only_Alts"]["sharpe"], d20["Short-Only_Alts"]["sharpe"], d20["LongAlts-ShortBTC"]["sharpe"], d10["Long-Short_Alts"]["sharpe"]]
    sh_22 = [d20["Long-Short_Alts"]["22_26_sh"], d20["Long-Only_Alts"]["22_26_sh"], d20["Short-Only_Alts"]["22_26_sh"], d20["LongAlts-ShortBTC"]["22_26_sh"], d10["Long-Short_Alts"]["22_26_sh"]]
    betas = [d20["Long-Short_Alts"]["beta_BTC"], d20["Long-Only_Alts"]["beta_BTC"], d20["Short-Only_Alts"]["beta_BTC"], d20["LongAlts-ShortBTC"]["beta_BTC"], d10["Long-Short_Alts"]["beta_BTC"]]
    x = np.arange(len(dlbls))
    w = 0.35
    ax.bar(x - w / 2, sh_dr, w, label="DR 21-26 (51m)", color=GREEN)
    ax.bar(x + w / 2, sh_22, w, label="Ex-2021 (42m)", color=CYAN)
    for i, bt in enumerate(betas):
        ax.text(i, max(sh_dr[i], sh_22[i], 0.05) + 0.06, f"b={bt:+.2f}", ha="center", color=ORANGE, fontsize=7.8)
    ax.axhline(0, color=TEXT, linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(dlbls, fontsize=8, color=TEXT)
    ax.set_ylabel("Sharpe (20 bps + funding)", color=TEXT, fontsize=9)
    ax.set_title("2. Descomposicion de alfa XSMOM: L/S Alts sobrevive ex-2021 con beta BTC ~ 0", color=TEXT, fontsize=9.8, fontweight="bold")
    ax.legend(facecolor=PANEL, edgecolor=GRID, labelcolor=TEXT, fontsize=8)

    # Panel 3: Equity curves Cripto PIT v2 Staggered Ex-TradFi (DESC+REP only)
    ax = axes[1, 0]
    _style_ax(ax)
    for col, lbl, c in [
        ("CR2_XSMOM_Stag5d", "CR2_XSMOM_Stag5d (Sh 1.08, top5=28%, dh=0)", GREEN),
        ("CR2_Core_XSMOM_ResidMom", "CR2_Core XSMOM+Resid (Sh 0.75, 67% m+)", CYAN),
        ("CR2_Canasta_InvVol", "CR2_Canasta_InvVol (Sh 0.69)", PURPLE),
        ("ABL_Claude_XSMOM_Bug", "Claude Bug Line 177 (Sh 0.79, top5=48%)", RED),
    ]:
        if col in cr_s:
            s = cr_s[col].dropna()
            ax.plot(s.index, s.cumsum(), label=lbl, color=c, linewidth=1.7)
    ax.set_ylabel("PnL acumulado USD ($10k/lado, SOLO DESC+REP)", color=TEXT, fontsize=9)
    ax.set_title("3. CRIPTO-PIT v2 (226 crypto ex-TradFi): curva acumulada sin meses sellados", color=TEXT, fontsize=10.0, fontweight="bold")
    ax.legend(facecolor=PANEL, edgecolor=GRID, labelcolor=TEXT, fontsize=7.8)

    # Panel 4: Yahoo =F Roll Glitch Audit (why FUTUROS_NO_EQUITY_V2 is INVALIDATED)
    ax = axes[1, 1]
    _style_ax(ax)
    rg = fut_j["roll_glitch_audit"]
    top_rg = sorted(rg.items(), key=lambda kv: kv[1]["gt_8pct_days"], reverse=True)[:10]
    tks = [k for k, _ in top_rg]
    g8 = [v["gt_8pct_days"] for _, v in top_rg]
    g15 = [v["gt_15pct_days"] for _, v in top_rg]
    x = np.arange(len(tks))
    w = 0.38
    ax.bar(x - w / 2, g8, w, label="Dias |ret| > 8%", color=ORANGE)
    ax.bar(x + w / 2, g15, w, label="Dias |ret| > 15%", color=RED)
    for i, (_, v) in enumerate(top_rg):
        ax.text(i, v["gt_8pct_days"] + 4, f"{v['max_abs_ret']:.0%}", ha="center", color=TEXT, fontsize=7.5)
    ax.set_xticks(x)
    ax.set_xticklabels(tks, fontsize=8, color=TEXT)
    ax.set_ylabel("Cantidad de saltos diarios anomalos (2004-2026)", color=TEXT, fontsize=9)
    ax.set_title("4. INVALIDADO Yahoo =F: saltos sin back-adjustment (paridad M1 solo 0.76)", color=TEXT, fontsize=9.8, fontweight="bold")
    ax.legend(facecolor=PANEL, edgecolor=GRID, labelcolor=TEXT, fontsize=8)

    plt.tight_layout(rect=[0, 0, 1, 0.95])
    _save_and_copy(fig, "frentes_v2_cripto_pit_y_futuros_no_equity.png")


def chart3_marco_cscv(msf: dict, d_4f: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(15, 10), facecolor=BG)
    fig.suptitle(
        "Marco Sin Forward Corregido (HOLDOUT SELLADO): Igual 10% Vol, CSCV Limpio sin CME y Estres 0.5x",
        color=TEXT, fontsize=13.0, fontweight="bold", y=0.98,
    )
    kres = msf["kaggle_cscv_dsr_bootstrap"]

    # Panel 1: Cumulative equity scaled to EXACT 10% annualized own volatility (monthly 21-26 DESC+REP)
    ax = axes[0, 0]
    _style_ax(ax)
    cols_p1 = [
        ("CME50_C2_25_Cripto25", "CME50+C2(25)+CR(25) (Sh 2.52, MDD -5.2%)", GREEN, 2.2),
        ("CME_TRZV", "CME TRZV solo (Sh 2.49, MDD -3.8% [sesgo CME])", CYAN, 1.8),
        ("Super_3Core_HRP_Weekly", "3Core HRP Semanal (Sh 1.77, MDD -4.2%)", ORANGE, 1.7),
        ("CME_Div10", "CME Div10 solo (Sh 1.84, MDD -4.0%)", PURPLE, 1.4),
        ("Cripto_Core_Stag", "Cripto Core Stag (Sh 0.75, MDD -10.5% [LIMPIO])", TEAL, 1.5),
        ("Carril2_Sell16", "Carril 2 Sell16 (Sh 0.51, MDD -11.2% [LIMPIO])", MUTED, 1.2),
    ]
    d_m = d_4f.dropna(how="all").groupby(lambda d: d.to_period("M")).sum(min_count=1)
    # Build CME50 if not directly in d_4f? We added it in d21_save!
    x_idx = np.arange(len(d_m))
    for col, lbl, c, lw in cols_p1:
        if col in d_m:
            s = d_m[col].dropna()
            sd_ann = float(s.std(ddof=1)) * np.sqrt(12.0)
            s10 = s / max(sd_ann, 1e-9) * 10.0
            ax.plot(range(len(s10)), s10.cumsum(), label=lbl, color=c, linewidth=lw)
    ax.set_xlabel("Meses consecutivos DESC+REP (2021-01 .. 2026-09, 51m sin meses sellados)", color=TEXT, fontsize=8.5)
    ax.set_ylabel("Retorno acumulado (%) a exactamente 10% vol anual", color=TEXT, fontsize=9)
    ax.set_title("1. Curvas a VOLATILIDAD IDENTICA (10% anual): cero ilusion de escala", color=TEXT, fontsize=10.2, fontweight="bold")
    ax.legend(facecolor=PANEL, edgecolor=GRID, labelcolor=TEXT, fontsize=7.4, loc="upper left")

    # Panel 2: Weekly Correlation heatmap (zero Monday spike!)
    ax = axes[0, 1]
    _style_ax(ax)
    cm = pd.DataFrame(msf["corr_weekly_21_26_DR"])
    cols = ["CME_TRZV", "CME_Div10", "Carril2_Sell16", "Cripto_Core_Stag"]
    short = ["CME TRZV", "CME Div10", "Carril 2", "Cripto Core"]
    mat = cm.loc[cols, cols].to_numpy(float)
    ax.imshow(mat, cmap="coolwarm", vmin=-0.5, vmax=0.8)
    ax.set_xticks(range(4))
    ax.set_xticklabels(short, color=TEXT, fontsize=8.8)
    ax.set_yticks(range(4))
    ax.set_yticklabels(short, color=TEXT, fontsize=8.8)
    for i in range(4):
        for j in range(4):
            ax.text(j, i, f"{mat[i, j]:+.3f}", ha="center", va="center", color=TEXT, fontweight="bold", fontsize=9.2)
    ax.set_title("2. Correlacion semanal (W-FRI, 0 spike lunes): ortogonalidad <= 0.132", color=TEXT, fontsize=10.2, fontweight="bold")

    # Panel 3: Clean CSCV (zero CME!) vs Descriptive CME
    ax = axes[1, 0]
    _style_ax(ax)
    c_dict = kres["cscv"]
    ckeys = ["1_clean_carril2_16rules", "2_clean_non_cme_21rules", "3_descriptive_with_cme"]
    clbls = ["Carril2 16r\n(06-26 LIMPIO)", "No-CME 21r\n(21-26 LIMPIO)", "Con CME 31r\n(DESCRIPTIVO)"]
    best_oos = [c_dict[k]["best_single_OOS_SR_median"] for k in ckeys]
    ew_oos = [c_dict[k]["basket_1N_OOS_SR_median"] for k in ckeys]
    pbo = [c_dict[k]["PBO_prob_overfit"] * 100 for k in ckeys]
    x = np.arange(len(ckeys))
    w = 0.32
    ax.bar(x - w / 2, best_oos, w, label="Mejor regla unica OOS (Sharpe)", color=ORANGE)
    ax.bar(x + w / 2, ew_oos, w, label="Canasta 1/N OOS (Sharpe)", color=GREEN)
    for i, pv in enumerate(pbo):
        ax.text(i, max(best_oos[i], ew_oos[i]) + 0.08, f"PBO={pv:.1f}%\nP(+)=100%" if i != 1 else f"PBO={pv:.1f}%\nP(+)=86.5%", ha="center", color=TEXT, fontsize=7.8)
    ax.set_xticks(x)
    ax.set_xticklabels(clbls, fontsize=8.2, color=TEXT)
    ax.set_ylabel("Sharpe OOS mediano (12,870 splits CSCV)", color=TEXT, fontsize=9)
    ax.set_title("3. CSCV Limpio (sin sobrevivientes CME): 1/N supera siempre a elegir la mejor", color=TEXT, fontsize=9.8, fontweight="bold")
    ax.legend(facecolor=PANEL, edgecolor=GRID, labelcolor=TEXT, fontsize=7.8)
    ax.set_ylim(0, 2.25)

    # Panel 4: Shrinkage Stress (CME 0.5x) & Equal-10%-Vol MDD
    ax = axes[1, 1]
    _style_ax(ax)
    st_base = msf["shrinkage_stress_10pct_vol"]["CME_1.0x__C2_CR_1.0x"]
    st_real = msf["shrinkage_stress_10pct_vol"]["CME_0.5x__C2_CR_0.7x"]
    pkeys = ["CME_Div10_solo", "Super_3Core_EQ_Div10", "CME_TRZV_solo", "CME50_C2_25_Cripto25_TRZV"]
    plbls = ["CME Div10\nsolo", "3Core EQ\n(Div10)", "CME TRZV\nsolo", "CME50 +\nC2(25)+CR(25)"]
    x = np.arange(len(pkeys))
    w = 0.35
    sh_s = [st_real[p]["sharpe"] for p in pkeys]
    mdd_s = [abs(st_real[p]["mdd_at_10pct_vol"]) for p in pkeys]
    ax.bar(x - w / 2, sh_s, w, label="Sharpe bajo estres CME 0.5x / C2+CR 0.7x", color=CYAN)
    ax2 = ax.twinx()
    ax2.bar(x + w / 2, mdd_s, w, label="MDD @10% vol (%) bajo estres", color=RED, alpha=0.8)
    ax2.tick_params(colors=TEXT, labelsize=8.5)
    ax2.set_ylabel("MDD a 10% vol (%)", color=RED, fontsize=9)
    ax.set_xticks(x)
    ax.set_xticklabels(plbls, fontsize=8, color=TEXT)
    ax.set_ylabel("Sharpe bajo contraccion", color=CYAN, fontsize=9)
    ax.set_title("4. Estres realista (CME 0.5x a igual 10% vol): el valor real de diversificar", color=TEXT, fontsize=9.8, fontweight="bold")
    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labels1 + labels2, facecolor=PANEL, edgecolor=GRID, labelcolor=TEXT, fontsize=7.5, loc="upper left")

    plt.tight_layout(rect=[0, 0, 1, 0.95])
    _save_and_copy(fig, "marco_sin_forward_cscv_bayes_y_supercanasta.png")


def main() -> None:
    if plt is None:
        print("matplotlib not installed; skipping charts.")
        return
    aud = json.loads((OUT / "AUDITORIA_CLAUDE.json").read_text(encoding="utf-8"))
    cr_j = json.loads((OUT / "CRIPTO_PIT_V2.json").read_text(encoding="utf-8"))
    fut_j = json.loads((OUT / "FUTUROS_NO_EQUITY_V2.json").read_text(encoding="utf-8"))
    msf = json.loads((OUT / "MARCO_SIN_FORWARD.json").read_text(encoding="utf-8"))
    cr_s = pd.read_csv(OUT / "SERIES_CRIPTO_PIT_V2_DR.csv.gz", index_col=0, parse_dates=True)
    d_4f = pd.read_csv(OUT / "SERIES_4_FRENTES_DR.csv.gz", index_col=0, parse_dates=True)

    chart1_auditoria_claude(aud, msf, cr_j)
    chart2_frentes_v2(cr_j, fut_j, cr_s)
    if "kaggle_cscv_dsr_bootstrap" in msf:
        chart3_marco_cscv(msf, d_4f)


if __name__ == "__main__":
    main()
