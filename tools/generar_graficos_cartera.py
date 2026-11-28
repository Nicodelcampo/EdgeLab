#!/usr/bin/env python3
"""Paso 7: Genera las 4 figuras comparativas dark-mode de la auditoria, expansion, cripto y optimizacion OOS + Multi-Prop."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ImportError:
    matplotlib = plt = None
import numpy as np
import pandas as pd

OUT = ROOT / "docs/research/auditoria_cartera_20261126"
BRAIN = Path(r"C:\Users\nicoc\.gemini\antigravity\brain\417d395c-1bd7-4157-b782-277352881af1")

if plt is not None:
    plt.rcParams.update({
        "figure.facecolor": "#0d1117",
        "axes.facecolor": "#161b22",
        "axes.edgecolor": "#30363d",
        "axes.labelcolor": "#e6edf3",
        "text.color": "#e6edf3",
        "xtick.color": "#8b949e",
        "ytick.color": "#8b949e",
        "grid.color": "#21262d",
        "legend.facecolor": "#161b22",
        "legend.edgecolor": "#30363d",
        "font.size": 9.5,
    })


def _save(fig: plt.Figure, name: str) -> None:
    p1 = OUT / name
    fig.savefig(p1, dpi=150, bbox_inches="tight", facecolor="#0d1117")
    if BRAIN.exists():
        shutil.copy2(p1, BRAIN / name)
    plt.close(fig)
    print("Saved:", p1)


def fig1_auditoria_claude(aud: dict, intra_d: pd.DataFrame, mixto_d: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(15, 9.5), gridspec_kw={"height_ratios": [1.3, 1.0]})

    # A: Cumulative OOS Intraday Equity (Vol-Matched to Actual_Base)
    ax = axes[0, 0]
    base_sd = intra_d["Actual_Base"].groupby(intra_d.index.to_period("M")).sum().std(ddof=1)
    styles = [
        ("Actual_Base", "#8b949e", "--", 1.8, "Actual Base 8M"),
        ("Claude_Regla", "#f0883e", "-", 2.0, "Claude Regla (con F/C sin NT8)"),
        ("Regla_V2_Clean", "#58a6ff", "-", 2.4, "Regla V2 Limpia (sin F/C)"),
        ("Discrete_Micro_Opt", "#3fb950", "-", 2.2, "Discrete Micro Opt (0..3 micros)"),
    ]
    for col, c, ls, lw, lbl in styles:
        sd_m = intra_d[col].groupby(intra_d.index.to_period("M")).sum().std(ddof=1)
        sc = base_sd / sd_m if sd_m > 0 else 1.0
        eq = (intra_d[col] * sc).cumsum()
        sh = (intra_d[col].groupby(intra_d.index.to_period("M")).sum().mean() / sd_m * np.sqrt(12))
        ax.plot(eq.index, eq.values, color=c, ls=ls, lw=lw, label=f"{lbl} (Sh={sh:.2f})")
    ax.axvspan(pd.Timestamp("2026-05-01"), pd.Timestamp("2026-09-30"), color="#f85149", alpha=0.10, label="Tramo estres May-Sep 2026")
    ax.set_title("INTRADIA PROP (WF 2021-07 -> 2026-09, igual volatilidad)", fontweight="bold")
    ax.set_ylabel("USD acumulados (vol-matched)")
    ax.grid(True, alpha=0.4)
    ax.legend(loc="upper left", fontsize=8)

    # B: Cumulative OOS Mixto Equity (Vol-Matched)
    ax = axes[0, 1]
    base_sd_m = mixto_d["Actual_Base"].groupby(mixto_d.index.to_period("M")).sum().std(ddof=1)
    for col, c, ls, lw, lbl in [
        ("Actual_Base", "#8b949e", "--", 1.8, "Actual Mixto 11M"),
        ("Claude_Regla", "#f0883e", "-", 2.0, "Claude Regla Mixto"),
        ("Regla_V2_Clean", "#58a6ff", "-", 2.4, "Regla V2 Limpia Mixto"),
        ("MaxDiv", "#d2a8ff", "-", 2.2, "MaxDiv Mixto"),
    ]:
        sd_m = mixto_d[col].groupby(mixto_d.index.to_period("M")).sum().std(ddof=1)
        sc = base_sd_m / sd_m if sd_m > 0 else 1.0
        eq = (mixto_d[col] * sc).cumsum()
        sh = (mixto_d[col].groupby(mixto_d.index.to_period("M")).sum().mean() / sd_m * np.sqrt(12))
        ax.plot(eq.index, eq.values, color=c, ls=ls, lw=lw, label=f"{lbl} (Sh={sh:.2f})")
    ax.axvspan(pd.Timestamp("2026-05-01"), pd.Timestamp("2026-09-30"), color="#f85149", alpha=0.10)
    ax.set_title("MIXTO CME (WF 2021-07 -> 2026-09, igual volatilidad)", fontweight="bold")
    ax.grid(True, alpha=0.4)
    ax.legend(loc="upper left", fontsize=8)

    # C: Multi-Split Robustness (6 cut dates from AUDITORIA_RESUMEN.json)
    ax = axes[1, 0]
    ms = aud["multi_splits"]
    cuts = list(ms.keys())
    x = np.arange(len(cuts))
    w = 0.26
    ax.bar(x - w, [ms[c]["INTRADIA"]["actual_sh"] for c in cuts], width=w, color="#8b949e", label="Actual")
    ax.bar(x, [ms[c]["INTRADIA"]["claude_sh"] for c in cuts], width=w, color="#f0883e", label="Claude Regla")
    ax.bar(x + w, [ms[c]["INTRADIA"]["fix3_sh"] for c in cuts], width=w, color="#58a6ff", label="Fix3 Sin F/C")
    ax.set_xticks(x)
    ax.set_xticklabels(cuts, rotation=15)
    ax.set_ylabel("Sharpe OOS Intradia")
    ax.set_title("Sensibilidad de Sharpe OOS al punto de corte (Intradia)", fontweight="bold")
    ax.grid(True, axis="y", alpha=0.4)
    ax.legend(fontsize=8)

    # D: FS_O_NQ zombie vs O_qty1_NQ post 2025-10-14 & Fixed Params 2012-2026 Sharpe
    ax = axes[1, 1]
    mods = ["F\n(Fabio)", "C\n(Capstone)", "N\n(NDay)", "O\n(Overnight)", "V\n(Vault)", "Z\n(Zeta)", "T\n(Orb)", "R\n(AtrPhase)"]
    full_m = aud["fc_2012_2026_audit"]
    shs = [full_m[k]["sharpe_2012_2026"] for k in ("F", "C", "N", "O", "V", "Z", "T", "R")]
    cols_b = ["#f85149" if s < 0.4 else ("#f0883e" if s < 0.6 else "#3fb950") for s in shs]
    bars = ax.bar(np.arange(len(mods)), shs, color=cols_b)
    ax.axhline(0.5, color="#8b949e", ls=":", lw=1.2, label="Umbral minimo edge estable")
    for b, s in zip(bars, shs):
        ax.text(b.get_x() + b.get_width() / 2, s + 0.03, f"{s:.2f}", ha="center", va="bottom", fontsize=8)
    ax.set_xticks(np.arange(len(mods)))
    ax.set_xticklabels(mods, fontsize=8)
    ax.set_ylabel("Sharpe 2012-2026 (1 micro)")
    ax.set_title("Auditoria 15 años: F y C tienen Sh<0.25 (entraron por recorte 2019-23)", fontweight="bold")
    ax.grid(True, axis="y", alpha=0.4)
    ax.legend(fontsize=8)

    fig.suptitle("AUDITORIA FORENSE: REGLA-CARTERA DE CLAUDE VS VERSION LIMPIA SIN F/C", fontsize=13, fontweight="bold", y=0.99)
    fig.tight_layout()
    _save(fig, "auditoria_claude_regla_vs_fixes.png")


def fig2_expansion_multiactivo(exp_d: pd.DataFrame, kg_meta: dict, adapt: dict) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(15.5, 6.5), gridspec_kw={"width_ratios": [1.15, 1.0]})

    # Left: Correlation Heatmap across 15 diverse surviving/clean streams (DESC+REP < 2026-10-01)
    ax = axes[0]
    pool_cols = [c for c in [
        "T_NQ", "R_ATR50_NQ", "Z_ATR50_NQ", "V_nm30_tp1400_NQ", "RQ5_NQ", "SOM_eod_NQ",
        "RQ5_ES", "ES5N_ES", "T_ES_adapt", "C2VZ_NQ", "SOMSF_NQ", "O_qty1_ATR50",
        "DK_ORB_DAX", "DK_DON_WTI", "CR_HRP_PORT"
    ] if c in exp_d.columns]
    # Note DK_ORB_DAX / DK_DON_WTI / CR_HRP_PORT only valid on DESC+REP dates
    M = exp_d[pool_cols].dropna(how="any").groupby(lambda i: i.to_period("M")).sum()
    corr = M.corr().to_numpy()
    im = ax.imshow(corr, cmap="RdBu_r", vmin=-0.5, vmax=0.8)
    ax.set_xticks(np.arange(len(pool_cols)))
    ax.set_yticks(np.arange(len(pool_cols)))
    ax.set_xticklabels(pool_cols, rotation=45, ha="right", fontsize=7.5)
    ax.set_yticklabels(pool_cols, fontsize=7.5)
    for i in range(len(pool_cols)):
        for j in range(len(pool_cols)):
            ax.text(j, i, f"{corr[i, j]:.2f}", ha="center", va="center", fontsize=6.3, color="#0d1117" if abs(corr[i, j]) > 0.35 else "#e6edf3")
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label="Correlacion Mensual (A5 DESC+REP)")
    ax.set_title("Matriz de Decorrelacion Multi-Activo y Multi-Frente", fontweight="bold")

    # Right: Top CME Causal Improvements & Kaggle Orthogonal Streams Sharpe (DESC vs REP)
    ax = axes[1]
    items = [
        ("R_ATR50_NQ (CME)", 1.64, "#3fb950"),
        ("SOM_eod_NQ (CME EOD)", 1.33, "#3fb950"),
        ("Z_ATR50_NQ (CME)", 1.08, "#3fb950"),
        ("V_nm30_tp1400_NQ", 1.00, "#58a6ff"),
        ("N_ATR25_NQ (CME)", 0.83, "#58a6ff"),
        ("W_eod_ATR25_NQ", 0.56, "#58a6ff"),
        ("T_ES_adapt (CME)", 0.39, "#a371f7"),
        ("CME_RTY_OVN (Kaggle)", kg_meta["candidates"]["CME_RTY_OVN_RAW"]["DESC_REP"]["sharpe"], "#d29922"),
        ("DK_WTI_DON (Kaggle)", kg_meta["candidates"]["DK_WTI_DON"]["DESC_REP"]["sharpe"], "#f0883e"),
        ("DK_DAX_ORB (Kaggle)", kg_meta["candidates"]["DK_DAX_ORB"]["DESC_REP"]["sharpe"], "#f0883e"),
        ("CR_Trend_4H_EMA", 1.04, "#39d353"),
        ("CR_Donchian_1D", 0.90, "#39d353"),
    ]
    labels = [x[0] for x in items][::-1]
    vals = [x[1] for x in items][::-1]
    cols = [x[2] for x in items][::-1]
    bars = ax.barh(np.arange(len(labels)), vals, color=cols)
    for b, v in zip(bars, vals):
        ax.text(v + 0.03, b.get_y() + b.get_height() / 2, f"{v:.2f}", va="center", fontsize=8)
    ax.set_yticks(np.arange(len(labels)))
    ax.set_yticklabels(labels, fontsize=8.5)
    ax.set_xlabel("Sharpe anualizado (muestra limpia A5 / 2019-2026)")
    ax.set_title("Nuevos Motores & Mejoras Causales (CME + M1DK + Cripto)", fontweight="bold")
    ax.grid(True, axis="x", alpha=0.4)

    fig.suptitle("EXPANSION MULTI-ACTIVO: MEJORAS CAUSALES CME + ORTOGONALES GLOBALES", fontsize=13, fontweight="bold", y=0.99)
    fig.tight_layout()
    _save(fig, "expansion_multiactivo_y_decorrelacion.png")


def fig3_cripto_y_supercartera(cr_res: dict, cr_d: pd.DataFrame, multi_d: pd.DataFrame, opt: dict) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(15.5, 6.2))

    # Left: Crypto strategies DESC vs REP (A5 sealed holdout)
    ax = axes[0]
    cr_dr = cr_d.dropna(subset=["CR_HRP_PORT"])
    for c, col, lbl in [
        ("CR_Donchian_1D", "#58a6ff", "Donchian 20/10 1D"),
        ("CR_Trend_4H_EMA", "#3fb950", "EMA 24/96 4H + Trail"),
        ("CR_XSMOM_Neutral", "#d2a8ff", "XSMOM Neutral 14d"),
        ("CR_HRP_PORT", "#f0883e", "Cartera Cripto HRP (fit DESC)"),
    ]:
        eq = cr_dr[c].cumsum()
        sh_rep = cr_res["strategies_A5"][c]["REP"]["sharpe"] if c in cr_res["strategies_A5"] else cr_res["crypto_portfolio"]["HRP_DESC"]["REP"]["sharpe"]
        ax.plot(eq.index, eq.values, color=col, lw=2.0 if "HRP" in c else 1.4, label=f"{lbl} (REP Sh={sh_rep:.2f})")
    ax.set_title("FRENTE CRIPTO BINANCE (8 perpetuos, net 10bps+funding, solo DESC+REP)", fontweight="bold")
    ax.set_ylabel("USD acumulados (base $10,000, 100% causal)")
    ax.grid(True, alpha=0.4)
    ax.legend(loc="upper left", fontsize=8)

    # Right: Multi-Front Walk-Forward OOS (CME Base vs CME+M1+Cripto HRP & MaxDiv, Vol-Matched)
    ax = axes[1]
    base_sd = multi_d["Actual_Base"].groupby(multi_d.index.to_period("M")).sum().std(ddof=1)
    u_c = opt["universo_C_multifrente_DESC_REP"]["raw_oos"]
    for col, c, ls, lbl in [
        ("Actual_Base", "#8b949e", "--", f"CME Actual Mixto (Sh={u_c['Actual_Base']['sharpe']:.2f})"),
        ("Regla_V2_Clean", "#58a6ff", "-", f"Regla V2 Multi-Frente (Sh={u_c['Regla_V2_Clean']['sharpe']:.2f})"),
        ("HRP", "#3fb950", "-", f"HRP Multi-Frente (Sh={u_c['HRP']['sharpe']:.2f}, CalInt={u_c['HRP']['calmar_intra']:.2f})"),
        ("MaxDiv", "#f0883e", "-", f"MaxDiv Multi-Frente (Sh={u_c['MaxDiv']['sharpe']:.2f}, DR={u_c['MaxDiv']['div_ratio']:.2f})"),
    ]:
        sd_m = multi_d[col].groupby(multi_d.index.to_period("M")).sum().std(ddof=1)
        sc = base_sd / sd_m if sd_m > 0 else 1.0
        eq = (multi_d[col] * sc).cumsum()
        ax.plot(eq.index, eq.values, color=c, ls=ls, lw=2.1, label=lbl)
    ax.set_title("SUPER-CARTERA MULTI-FRENTE: CME + WTI + CRIPTO (WF OOS DESC+REP)", fontweight="bold")
    ax.set_ylabel("USD acumulados (vol-matched a CME Actual)")
    ax.grid(True, alpha=0.4)
    ax.legend(loc="upper left", fontsize=8)

    fig.tight_layout()
    _save(fig, "cartera_cripto_y_supercartera_multifrente.png")


def fig4_optimizacion_y_props(opt: dict, mc: dict) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(15.5, 6.2))
    methods = ["Actual_Base", "Claude_Regla", "Regla_V2_Clean", "HRP", "ERC", "MaxDiv", "Discrete_Micro_Opt"]
    labels = ["Actual\nBase", "Claude\nRegla", "Regla V2\nLimpia", "HRP", "ERC", "MaxDiv", "Discreta\nMicros"]
    x = np.arange(len(methods))
    w = 0.25

    # Left: Prop Pass Rates (50% conservative mean shrinkage) across Lucid 150K, Lucid 50K, Tradeify 150K
    ax = axes[0]
    p_l150 = [mc["lucid_150k"][f"INTRA_{m}_Fixed_m50"]["pasa"] * 100 for m in methods]
    p_l50 = [mc["lucid_50k"][f"INTRA_{m}_Fixed_m50"]["pasa"] * 100 for m in methods]
    p_tr = [mc["tradeify_150k"][f"INTRA_{m}_Fixed_m50"]["pasa"] * 100 for m in methods]
    ax.bar(x - w, p_l150, width=w, color="#58a6ff", label="LucidFlex 150K")
    ax.bar(x, p_l50, width=w, color="#f0883e", label="LucidFlex 50K")
    ax.bar(x + w, p_tr, width=w, color="#3fb950", label="Tradeify SelectFlex 150K")
    for i in range(len(methods)):
        ax.text(x[i] - w, p_l150[i] + 1, f"{p_l150[i]:.0f}%", ha="center", fontsize=7.5)
        ax.text(x[i] + w, p_tr[i] + 1, f"{p_tr[i]:.0f}%", ha="center", fontsize=7.5)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8.5)
    ax.set_ylabel("Probabilidad de pasar evaluacion (%) — media 50%")
    ax.set_title("Monte Carlo 20,000 Rutas: Tasa de Pase Prop (media al 50%)", fontweight="bold")
    ax.grid(True, axis="y", alpha=0.4)
    ax.legend(fontsize=8)

    # Right: EV in USD across Lucid 150K (Fixed vs Grossman-Zhou), Tradeify 150K, FTMO 100K CFD (Mixed continuous)
    ax = axes[1]
    ev_l150_fx = [mc["lucid_150k"][f"INTRA_{m}_Fixed_m50"]["ev"] for m in methods]
    ev_l150_gz = [mc["lucid_150k"][f"INTRA_{m}_GrossmanZhou_m50"]["ev"] for m in methods]
    ev_ftmo = [mc["ftmo_100k"][f"MIXTO_{m}_m50"]["ev"] for m in methods]
    ax.bar(x - w, ev_l150_fx, width=w, color="#58a6ff", label="Lucid 150K Fijo (m50)")
    ax.bar(x, ev_l150_gz, width=w, color="#a371f7", label="Lucid 150K Grossman-Zhou (m50)")
    ax.bar(x + w, ev_ftmo, width=w, color="#3fb950", label="FTMO 100K CFD Mixto (m50)")
    ax.axhline(0, color="#f85149", ls="--", lw=1.0)
    for i in range(len(methods)):
        ax.text(x[i] + w, max(0, ev_ftmo[i]) + 25, f"${ev_ftmo[i]:.0f}", ha="center", fontsize=7)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8.5)
    ax.set_ylabel("Valor Esperado Neto por Evaluacion (USD)")
    ax.set_title("EV Neto Multi-Prop (Futuros Intradia vs CFD Mixto Continuo)", fontweight="bold")
    ax.grid(True, axis="y", alpha=0.4)
    ax.legend(fontsize=8)

    fig.suptitle("OPTIMIZACION DE CARTERAS EN PROPS Y BROKER (20,000 TRAYECTORIAS)", fontsize=13, fontweight="bold", y=0.99)
    fig.tight_layout()
    _save(fig, "optimizacion_carteras_oos_y_props.png")


def main() -> None:
    aud = json.loads((OUT / "AUDITORIA_RESUMEN.json").read_text(encoding="utf-8"))
    adapt = json.loads((OUT / "ADAPTAR_PRESENTE_V2.json").read_text(encoding="utf-8"))
    kg_meta = json.loads((OUT / "kaggle_m1_out/KAGGLE_M1_EXPANSION.json").read_text(encoding="utf-8"))
    cr_res = json.loads((OUT / "CARTERA_CRIPTO_RESUMEN.json").read_text(encoding="utf-8"))
    opt = json.loads((OUT / "OPTIMIZACION_CARTERAS.json").read_text(encoding="utf-8"))
    mc = json.loads((OUT / "kaggle_mc20k_out/KAGGLE_MC20K_RESUMEN.json").read_text(encoding="utf-8"))

    exp_d = pd.read_csv(OUT / "SERIES_EXPANDIDAS_DIARIAS.csv.gz", index_col=0, parse_dates=True)
    kg_d = pd.read_csv(OUT / "kaggle_m1_out/KAGGLE_M1_DAILY_DR.csv.gz", index_col=0, parse_dates=True).reindex(exp_d.index)
    cr_d = pd.read_csv(OUT / "SERIES_CRIPTO_DESC_REP.csv.gz", index_col=0, parse_dates=True)
    for c in kg_meta.get("alive_candidates", []):
        exp_d[c] = kg_d[c]
    # Add crypto HRP aligned cleanly to business dates for heatmap
    ses_int = pd.Series([int(d.strftime("%Y%m%d")) for d in exp_d.index], index=exp_d.index)
    from edgelab.holdout import a5_bloque
    mask_dr = ses_int.map(a5_bloque).isin(["DESC", "REP"])
    cr_sub = cr_d.dropna(subset=["CR_HRP_PORT"])
    pos_b = np.searchsorted(exp_d.index.to_numpy(), cr_sub.index.to_numpy(), side="left")
    vp = pos_b < len(exp_d.index)
    tb = pd.Series(exp_d.index[pos_b[vp]], index=cr_sub.index[vp])
    exp_d["CR_HRP_PORT"] = np.where(mask_dr, cr_sub.iloc[vp]["CR_HRP_PORT"].groupby(tb).sum().reindex(exp_d.index).fillna(0.0), np.nan)

    intra_d = pd.read_csv(OUT / "OOS_INTRADIA_7M.csv.gz", index_col=0, parse_dates=True)
    mixto_d = pd.read_csv(OUT / "OOS_MIXTO_7M.csv.gz", index_col=0, parse_dates=True)
    multi_d = pd.read_csv(OUT / "OOS_MULTIFRENTE_7M.csv.gz", index_col=0, parse_dates=True)

    fig1_auditoria_claude(aud, intra_d, mixto_d)
    fig2_expansion_multiactivo(exp_d, kg_meta, adapt)
    fig3_cripto_y_supercartera(cr_res, cr_d, multi_d, opt)
    fig4_optimizacion_y_props(opt, mc)


if __name__ == "__main__":
    main()
