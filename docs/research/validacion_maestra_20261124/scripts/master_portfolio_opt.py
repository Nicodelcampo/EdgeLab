#!/usr/bin/env python3
"""Front 4: Master Portfolio Placement & Prop-Firm Monte Carlo Optimization across ALL 5 account classes."""
import json
import math
import sys
from pathlib import Path
import numpy as np
import pandas as pd

SCRATCH = Path(r"C:\Users\Usuario\.gemini\antigravity\brain\6d51dfbd-ecbb-4249-894c-b2e8b3258c4b\scratch")
VAL_DIR = SCRATCH / "validation_full"
sys.path.insert(0, str(SCRATCH))

from audit3_orthogonality_eprocess_and_mc import (  # noqa: E402
    _sim_cfd_2phase_daily,
    _sim_lucid150_daily,
    eprocess_wait_months,
    load_daily_matrix,
)

# 1. Load Baseline Matrix (2020-2025 DESC+REP) & Core5 exact funded daily std ($851.76)
df, _, core5_exact = load_daily_matrix()
# Add validated REP series (on REP dates!) + full D+R series for C2_VZ & ES5N_ES
# Wait: for unbiased Monte Carlo, evaluate BOTH on REP-only (out-of-sample 2020-25, ~340 days) AND Full D+R!
rep_df = df[df["a5"] == "REP"].copy()

# Load clean REP daily R of C2_VZ, C2_EVRP, ES5N_ES
REPO = Path(r"E:\EdgeLab-fundedsync")
c2_l2 = pd.read_csv(REPO / "docs/research/carril2_20261119/OPS_LOTE2.csv.gz")
sc_cfd = {"ES": 0.35 / 0.8877, "NQ": 0.981 / 1.5455}
c2_l2["r_cfd"] = c2_l2["Rb"].astype(float) - c2_l2["fricR"].astype(float) * c2_l2["inst"].map(sc_cfd).fillna(1.0)

vz_rep = c2_l2[(c2_l2["bloque"] == "REP") & (c2_l2["definicion"] == "C2_VZ") & (c2_l2["inst"].isin(["ES", "NQ"])) & (c2_l2["fecha"] >= 20200101)].groupby("fecha")["r_cfd"].sum()
ev_rep = c2_l2[(c2_l2["bloque"] == "REP") & (c2_l2["definicion"] == "C2_EVRP") & (c2_l2["inst"].isin(["ES", "NQ"])) & (c2_l2["fecha"] >= 20200101)].groupby("fecha")["r_cfd"].sum()
fv = pd.read_csv(VAL_DIR / "FULL_VAL_REP_DAILY_R.csv.gz").set_index("ses")

rep_df["C2_VZ_CFD"] = vz_rep.reindex(rep_df.index, fill_value=0.0)
rep_df["C2_EVRP_CFD"] = ev_rep.reindex(rep_df.index, fill_value=0.0)
rep_df["ES5N_ES_CFD"] = fv["ES5N_ES_2020_25_CFD"].reindex(rep_df.index, fill_value=0.0) if "ES5N_ES_2020_25_CFD" in fv else 0.0

# Also build full 2020-2025 DESC+REP for C2_VZ & ES5N_ES for 5.5-yr correlation & Worst20% month check
full_df = df.copy()
vz_all = c2_l2[(c2_l2["bloque"].isin(["DESC", "REP"])) & (c2_l2["definicion"] == "C2_VZ") & (c2_l2["inst"].isin(["ES", "NQ"])) & (c2_l2["fecha"] >= 20200101)].groupby("fecha")["r_cfd"].sum()
full_df["C2_VZ_CFD"] = vz_all.reindex(full_df.index, fill_value=0.0)

# Target std: exact Core5 funded std = 851.76 USD/day (verified in audit3)
FUNDED_STD_BASE = 851.76

# Correlation & Worst 20% Core months on 2020-2025 REP (strictly OOS!)
cols_check = ["Core4_NQ", "RQ5_ES_Fut", "RQ5_ES_CFD", "RQ5_NQ_CFD", "SOM_ES_CFD", "Turtles_GC_CFD", "C2_VZ_CFD", "C2_EVRP_CFD", "ES5N_ES_CFD"]
cm = rep_df["Core4_NQ"].groupby(rep_df.index // 100).sum()
q20 = cm.quantile(0.20)
wm = cm[cm <= q20].index
print(f"=== OOS REP (2020-25, n_days={len(rep_df)}, n_months={len(cm)}, Core Worst20% sum={cm.loc[wm].sum():+.2f}R) ===")
ortho_summary = {}
for c in cols_check:
    s = rep_df[c]
    sm = s.groupby(s.index // 100).sum()
    cd = float(rep_df["Core4_NQ"].corr(s)) if s.std() > 0 else 0.0
    cm_c = float(cm.corr(sm)) if sm.std() > 0 else 0.0
    sh = float((s.mean() / s.std(ddof=1)) * math.sqrt(252)) if s.std() > 0 else 0.0
    cum = s.cumsum().to_numpy(); pk = np.maximum.accumulate(np.r_[0.0, cum])[1:]
    mdd = float((cum - pk).min())
    w20 = float(sm.loc[wm].sum())
    ortho_summary[c] = dict(sum_r=round(float(s.sum()), 2), sharpe=round(sh, 2), maxdd_r=round(mdd, 1), corr_d=round(cd, 3), corr_m=round(cm_c, 3), worst20m_r=round(w20, 2))
    print(f"  {c:16s} | sum={s.sum():+6.2f}R Sh={sh:+5.2f} DD={mdd:6.1f}R | corrD={cd:+.3f} corrM={cm_c:+.3f} | Worst20%M={w20:+6.2f}R")

# Define candidate portfolios per Prop Firm / Account Class
# Components inside portfolios are normalized by each component's REP std so weights w represent exact risk-budget share!
stds_rep = {c: float(rep_df[c].std(ddof=1)) for c in cols_check}
std_core_rep = stds_rep["Core4_NQ"]

def make_usd_series(weights: dict[str, float], target_std_usd: float | None = None) -> np.ndarray:
    """Combine normalized sleeves (scaled by Core4 std), then scale to target daily USD std (or additive if target_std_usd is None)."""
    comb = np.zeros(len(rep_df), dtype=float)
    for k, w in weights.items():
        if stds_rep.get(k, 0.0) <= 0:
            continue
        # Normalize each component to Core4 daily vol so w=0.20 means 20% of Core4 daily vol
        comb += w * (rep_df[k].to_numpy(float) * (std_core_rep / stds_rep[k]))
    if target_std_usd is not None:
        comb_usd = comb * (target_std_usd / float(np.std(comb, ddof=1)))
    else:
        # Fixed Core4 dollar multiplier (additive risk)
        comb_usd = comb * (FUNDED_STD_BASE / std_core_rep)
    return comb_usd

# Bootstrap sequences: N=3000 x 252 trading days (12 months) on OOS REP!
N_PATHS = 3000
H_DAYS = 252
rng = np.random.default_rng(20261124)
j_seq = rng.integers(0, len(rep_df), size=(N_PATHS, H_DAYS))

PORTFOLIOS = {
    # 1. Futures Intraday-Flat (LucidFlex 150K / Tradeify / Topstep)
    "Core_Solo": ({"Core4_NQ": 1.0}, FUNDED_STD_BASE, ["Lucid150K", "Tradeify_Topstep", "The5ers100K", "FTMO_Swing100K", "Personal"]),
    "FUT_Intraday_Core+RQ5_ES_eqvol": ({"Core4_NQ": 0.80, "RQ5_ES_Fut": 0.25}, FUNDED_STD_BASE, ["Lucid150K", "Tradeify_Topstep"]),
    "FUT_Intraday_Core+RQ5_ES_add15": ({"Core4_NQ": 1.0, "RQ5_ES_Fut": 0.18}, None, ["Lucid150K", "Tradeify_Topstep"]),
    # 2. CFD Intraday-Flat (The5ers HS 100K)
    "CFD_Flat_Core+OrthoIntraday_eqvol": ({"Core4_NQ": 0.72, "RQ5_ES_CFD": 0.25, "SOM_ES_CFD": 0.15, "ES5N_ES_CFD": 0.15}, FUNDED_STD_BASE, ["The5ers100K"]),
    "CFD_Flat_Core+OrthoIntraday_add15": ({"Core4_NQ": 1.0, "RQ5_ES_CFD": 0.22, "SOM_ES_CFD": 0.12, "ES5N_ES_CFD": 0.12}, None, ["The5ers100K"]),
    # 3. CFD Swing Allowed (FTMO Swing 100K & Boveda Personal): unlocks Turtles_GC + C2_VZ!
    "SWING_Core+Turtles_C2VZ_eqvol": ({"Core4_NQ": 0.65, "RQ5_ES_CFD": 0.20, "Turtles_GC_CFD": 0.30, "C2_VZ_CFD": 0.28}, FUNDED_STD_BASE, ["FTMO_Swing100K", "Personal"]),
    "SWING_FullOrtho_eqvol": ({"Core4_NQ": 0.60, "RQ5_ES_CFD": 0.20, "SOM_ES_CFD": 0.12, "ES5N_ES_CFD": 0.12, "Turtles_GC_CFD": 0.30, "C2_VZ_CFD": 0.28}, FUNDED_STD_BASE, ["FTMO_Swing100K", "Personal"]),
    "SWING_FullOrtho_add15": ({"Core4_NQ": 0.90, "RQ5_ES_CFD": 0.22, "SOM_ES_CFD": 0.12, "Turtles_GC_CFD": 0.32, "C2_VZ_CFD": 0.30}, None, ["FTMO_Swing100K", "Personal"]),
}

mc_rows = []
print("\n=== MASTER PROP MONTE CARLO (N=3,000, OOS REP 2020-25, 100% & 60% Stress) ===")
for pname, (wts, tgt_std, firms) in PORTFOLIOS.items():
    P_base = make_usd_series(wts, tgt_std)
    # Daily Sharpe / R metrics of blend
    sh_blend = float((P_base.mean() / P_base.std(ddof=1)) * math.sqrt(252))
    # Empirical worst 20% months on blend
    s_b = pd.Series(P_base, index=rep_df.index)
    sm_b = s_b.groupby(s_b.index // 100).sum()
    w20_usd = float(sm_b.loc[wm].sum())

    for mult_label, mult in (("REP_100%", 1.0), ("REP_60%_Stress", 0.60)):
        P = P_base - (1.0 - mult) * float(P_base.mean())
        for firm in firms:
            if firm == "Lucid150K":
                # Eval uses 1.25x funded sizing just like audit3 (speed eval -> Core5 funded)
                c12, cmin, r12, hp = _sim_lucid150_daily(1.25 * P, P, j_seq)
            elif firm == "Tradeify_Topstep":
                # Tradeify Growth 150K / Topstep 150K proxy (intraday-flat, fee $200, T=$9k, MLL=$4.5k, DLL=$3k, pay=5d >=$250)
                c12, cmin, r12, hp = _sim_lucid150_daily(1.25 * P, P, j_seq, fee=200.0, dll=3000.0, eval_cons=0.50)
            elif firm == "The5ers100K":
                # Scale CFD 100K risk ~0.85x base ($724/d)
                P5 = 0.85 * P
                c12, cmin, r12, hp = _sim_cfd_2phase_daily(P5, j_seq, fee=495.0, t1=8000.0, t2=5000.0, max_dd=10000.0, dll=5000.0, min_days=3, pay_cycle=14, min_pay=150.0, split=0.80, refund=True)
            elif firm == "FTMO_Swing100K":
                P5 = 0.85 * P
                c12, cmin, r12, hp = _sim_cfd_2phase_daily(P5, j_seq, fee=540.0, t1=10000.0, t2=5000.0, max_dd=10000.0, dll=5000.0, min_days=4, pay_cycle=14, min_pay=1.0, split=0.80, refund=True)
            else:  # Personal Uncapped ($100k ref, 1.0x base)
                # Direct cumulative equity & MaxDD across 252d paths
                paths = P[j_seq]
                eq = np.cumsum(paths, axis=1)
                c12 = eq[:, -1]
                pk = np.maximum.accumulate(np.hstack([np.zeros((N_PATHS, 1)), eq]), axis=1)[:, 1:]
                cmin = np.min(eq - pk, axis=1)
                r12 = np.zeros(N_PATHS)
                hp = (c12 > 0).astype(float)

            row = {
                "portfolio": pname, "firm": firm, "regime": mult_label,
                "blend_sharpe": round(sh_blend, 2), "blend_std_usd": round(float(P_base.std(ddof=1)), 0),
                "w20m_usd": round(w20_usd, 0),
                "net_12m_mean": round(float(c12.mean()), 0),
                "net_12m_med": round(float(np.median(c12)), 0),
                "p_payout": round(float(hp.mean()), 4),
                "payouts_yr": round(float(r12.mean()), 2),
                "cmin_p10": round(float(np.percentile(cmin, 10)), 0),
            }
            mc_rows.append(row)
            print(f"  {firm:16s} | {pname:34s} | {mult_label:14s} | Sh={sh_blend:.2f} Neto=${row['net_12m_mean']:+7.0f} P(pay)={row['p_payout']*100:5.1f}% #Pay={row['payouts_yr']:4.2f} p10=${row['cmin_p10']:+6.0f}")

# E-process wait time for the new SWING_FullOrtho_eqvol blend (daily R units normalized to Core std)
P_swing = make_usd_series(PORTFOLIOS["SWING_FullOrtho_eqvol"][0], FUNDED_STD_BASE) / FUNDED_STD_BASE
ep_100 = eprocess_wait_months(P_swing, piso=-6.0, techo=10.0, mult=1.0)
ep_60 = eprocess_wait_months(P_swing, piso=-6.0, techo=10.0, mult=0.60)
print(f"\nE-Process Wait (SWING_FullOrtho): 100%={ep_100} | 60%={ep_60}")

out_json = {
    "ortho_oos_rep": ortho_summary,
    "mc_results": mc_rows,
    "eprocess_swing_ortho": {"rep_100": ep_100, "rep_60": ep_60},
}
(VAL_DIR / "MASTER_PORTFOLIO_OPT.json").write_text(json.dumps(out_json, indent=2), encoding="utf-8")
pd.DataFrame(mc_rows).to_csv(VAL_DIR / "MASTER_MC_PROP.csv", index=False)
print("Saved MASTER_PORTFOLIO_OPT.json & MASTER_MC_PROP.csv")
