#!/usr/bin/env python3
"""Front 3: Local Clean REP Validation of FM2|FM2N, C2_VZ, RQ2, RQ6 (strictly DESC + REP only, HOLDOUT never touched)."""
import json
import math
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(r"E:\EdgeLab-fundedsync")
SCRATCH = Path(r"C:\Users\Usuario\.gemini\antigravity\brain\6d51dfbd-ecbb-4249-894c-b2e8b3258c4b\scratch")
OUT_DIR = SCRATCH / "validation_full"
OUT_DIR.mkdir(parents=True, exist_ok=True)

FRIC_FUT = {"NQ": 1.5455, "ES": 0.8877, "YM": 5.052, "GC": 0.605}
FRIC_CFD = {"NQ": 0.9810, "ES": 0.3500, "YM": 3.000, "GC": 0.300}


def eval_series(df_sub: pd.DataFrame, col_ses: str, col_r: str, min_yr: int | None = None) -> dict:
    x = df_sub.copy()
    if min_yr is not None:
        x = x[x[col_ses] // 10000 >= min_yr]
    if len(x) == 0:
        return {"n": 0}
    ses = x[col_ses].to_numpy(np.int64)
    r = x[col_r].to_numpy(float)
    ok = np.isfinite(r)
    ses, r = ses[ok], r[ok]
    if len(r) == 0:
        return {"n": 0}
    g = pd.DataFrame({"s": ses, "r": r}).groupby("s")["r"].agg(["sum", "count"])
    n = int(g["count"].sum())
    mean_op = float(g["sum"].sum() / n)
    se = float(np.sqrt(((g["sum"] - mean_op * g["count"]) ** 2).sum()) / n)
    t_stat = float(mean_op / se) if se > 0 else 0.0
    p_val = float(0.5 * math.erfc(t_stat / math.sqrt(2))) if se > 0 else 1.0
    daily = g["sum"].sort_index()
    n_yrs = max(1.0, len(np.unique(ses // 10000)))
    sharpe = float((daily.mean() / daily.std(ddof=1)) * math.sqrt(len(daily) / n_yrs)) if len(daily) > 1 and daily.std(ddof=1) > 0 else 0.0
    cum = daily.cumsum().to_numpy()
    pk = np.maximum.accumulate(np.r_[0.0, cum])[1:]
    maxdd = float((cum - pk).min())
    yr = pd.Series(r).groupby(ses // 10000).sum()
    pf = float(r[r > 0].sum() / abs(r[r < 0].sum())) if (r < 0).any() else 99.0
    return {
        "n": n,
        "sesiones": int(len(daily)),
        "r_mean": round(mean_op, 5),
        "r_total": round(float(r.sum()), 3),
        "wr": round(float((r > 0).mean()), 4),
        "pf": round(pf, 3),
        "t": round(t_stat, 3),
        "p": round(p_val, 5),
        "sharpe_yr": round(sharpe, 3),
        "maxdd_r": round(maxdd, 2),
        "pct_yrs_pos": round(float((yr > 0).mean()), 3),
        "daily": daily,
    }


def eval_tablas_ops(df: pd.DataFrame, definicion: str, ctrl: str | None, insts: list[str], e_col="P_obj_stop_fin", min_yr: int | None = None) -> dict:
    """Evaluate a reglas from tablas.py OPS_DESC_REP across DESC and REP with Fut & CFD friction."""
    out = {}
    for blk in ("DESC", "REP"):
        sub = df[(df["bloque"] == blk) & (df[definicion].astype(bool)) & (df["inst"].isin(insts)) & df[f"r_{e_col}"].notna() & (df[f"k_{e_col}"] > 0)].copy()
        if min_yr is not None:
            sub = sub[sub["ses"] // 10000 >= min_yr]
        if len(sub) == 0:
            out[blk] = {"n": 0}
            continue
        rb = sub[f"r_{e_col}"].to_numpy(float)
        k = sub[f"k_{e_col}"].to_numpy(float)
        sub["r_bruto"] = rb
        sub["r_fut"] = rb - sub["inst"].map(FRIC_FUT).to_numpy(float) / k
        sub["r_cfd"] = rb - sub["inst"].map(FRIC_CFD).to_numpy(float) / k
        sb = eval_series(sub, "ses", "r_bruto")
        sf = eval_series(sub, "ses", "r_fut")
        sc = eval_series(sub, "ses", "r_cfd")
        sf.pop("daily", None)
        d_cfd = sc.pop("daily", pd.Series(dtype=float))
        sb.pop("daily", None)
        blk_res = {"n": sc["n"], "r_bruto": sb["r_mean"], "fut": sf, "cfd": sc}
        if ctrl and ctrl in df.columns:
            csub = df[(df["bloque"] == blk) & (df[ctrl].astype(bool)) & (df["inst"].isin(insts)) & df[f"r_{e_col}"].notna() & (df[f"k_{e_col}"] > 0)].copy()
            if min_yr is not None:
                csub = csub[csub["ses"] // 10000 >= min_yr]
            if len(csub):
                crb = csub[f"r_{e_col}"].to_numpy(float)
                ck = csub[f"k_{e_col}"].to_numpy(float)
                csub["r_cfd"] = crb - csub["inst"].map(FRIC_CFD).to_numpy(float) / ck
                csc = eval_series(csub, "ses", "r_cfd")
                csc.pop("daily", None)
                blk_res["ctrl_cfd"] = csc
                blk_res["diff_cfd"] = round(sc["r_mean"] - csc["r_mean"], 5)
        out[blk] = blk_res
        out[f"_{blk}_daily_cfd"] = d_cfd
    return out


# Load Core4 reference
can = pd.read_csv(SCRATCH / "canasta_series_diarias_r.csv.gz").rename(columns={"Unnamed: 0": "ses"})
can["ses"] = pd.to_datetime(can["ses"]).dt.strftime("%Y%m%d").astype(int)
can = can.set_index("ses").sort_index()
core4 = can[["A20", "T", "R", "ZB"]].sum(axis=1)

results = {}
rep_daily = {}

# 1. FM2 & FM2N (Flujos Macro)
fm_df = pd.read_csv(ROOT / "docs/research/flujos_macro_20261119/OPS_DESC_REP.csv.gz")
assert set(fm_df["bloque"].unique()) <= {"DESC", "REP"}
for label, insts, myr in [
    ("FM2_NQ_2020_25", ["NQ"], 2020),
    ("FM2_NQ_full", ["NQ"], None),
    ("FM2_ES_NQ_2020_25", ["ES", "NQ"], 2020),
    ("FM2_ALL4_full", ["ES", "NQ", "YM", "GC"], None),
]:
    r = eval_tablas_ops(fm_df, "FM2", "FM2N", insts, min_yr=myr)
    d_rep = r.pop("_REP_daily_cfd", pd.Series(dtype=float))
    r.pop("_DESC_daily_cfd", None)
    results[label] = r
    if label == "FM2_NQ_2020_25":
        rep_daily["FM2_NQ_CFD"] = d_rep
    elif label == "FM2_ES_NQ_2020_25":
        rep_daily["FM2_ESNQ_CFD"] = d_rep

# 2. C2_VZ & LOTE2 (CARRIL2)
c2_l2 = pd.read_csv(ROOT / "docs/research/carril2_20261119/OPS_LOTE2.csv.gz")
assert set(c2_l2["bloque"].unique()) <= {"DESC", "REP"}
# Strictly verify salida in DESC/REP too
for label, dname, insts, myr in [
    ("C2_VZ_ES_NQ_2018_25", "C2_VZ", ["ES", "NQ"], 2018),
    ("C2_VZ_ES_NQ_2020_25", "C2_VZ", ["ES", "NQ"], 2020),
    ("C2_VZ_ES_NQ_full", "C2_VZ", ["ES", "NQ"], None),
    ("C2_VZ_NQ_2018_25", "C2_VZ", ["NQ"], 2018),
    ("C2_VZ_ES_2018_25", "C2_VZ", ["ES"], 2018),
    ("C2_VBB_ES_NQ_full", "C2_VBB", ["ES", "NQ"], None),
    ("C2_EVRP_ES_NQ_full", "C2_EVRP", ["ES", "NQ"], None),
    ("C2_P80_ES_NQ_full", "C2_P80", ["ES", "NQ"], None),
    ("C2_DBO_ES_NQ_full", "C2_DBO", ["ES", "NQ"], None),
]:
    blk_res = {}
    for blk in ("DESC", "REP"):
        sub = c2_l2[(c2_l2["bloque"] == blk) & (c2_l2["definicion"] == dname) & (c2_l2["inst"].isin(insts))].copy()
        if myr is not None:
            sub = sub[sub["fecha"] // 10000 >= myr]
        if len(sub) == 0:
            blk_res[blk] = {"n": 0}
            continue
        # R already uses canonical futures friction; recover CFD improvement if fricR exists
        sub["r_fut"] = sub["R"].astype(float)
        # Approximate CFD via fricR ratio
        scale_cfd = sub["inst"].map(lambda i: FRIC_CFD[i] / FRIC_FUT[i]).to_numpy(float)
        sub["r_cfd"] = sub["Rb"].astype(float) - sub["fricR"].astype(float) * scale_cfd
        sf = eval_series(sub, "fecha", "r_fut")
        sc = eval_series(sub, "fecha", "r_cfd")
        sf.pop("daily", None)
        d_c = sc.pop("daily", pd.Series(dtype=float))
        blk_res[blk] = {"n": sc["n"], "fut": sf, "cfd": sc}
        if blk == "REP" and label == "C2_VZ_ES_NQ_2018_25":
            rep_daily["C2_VZ_ESNQ_CFD"] = d_c
        if blk == "REP" and label == "C2_VZ_ES_NQ_full":
            rep_daily["C2_VZ_ESNQ_FULL_CFD"] = d_c
    results[label] = blk_res

# Also check LOTE1 (D7/IBS/TT/TOM) in REP just for confirmation
c2_l1 = pd.read_csv(ROOT / "docs/research/carril2_20261119/OPS.csv.gz")
assert set(c2_l1["bloque"].unique()) <= {"DESC", "REP"}
for dname in ("C2_D7", "C2_IBS", "C2_TT", "C2_TOM"):
    blk_res = {}
    for blk in ("DESC", "REP"):
        sub = c2_l1[(c2_l1["bloque"] == blk) & (c2_l1["definicion"] == dname) & (c2_l1["fecha"] // 10000 >= 2020)].copy()
        if len(sub):
            sf = eval_series(sub, "fecha", "R")
            sf.pop("daily", None)
            blk_res[blk] = sf
        else:
            blk_res[blk] = {"n": 0}
    results[f"{dname}_2020_25"] = blk_res

# 3. RQ2 & RQ6 (Roboquant)
rq_df = pd.read_csv(ROOT / "docs/research/roboquant_20261118/OPS_DESC_REP.csv.gz")
assert set(rq_df["bloque"].unique()) <= {"DESC", "REP"}
for label, dname, ctrl, insts, myr in [
    ("RQ2_ES_NQ_2020_25", "RQ2", "RQ2N", ["ES", "NQ"], 2020),
    ("RQ2_ES_NQ_full", "RQ2", "RQ2N", ["ES", "NQ"], None),
    ("RQ2_ALL3_full", "RQ2", "RQ2N", ["ES", "NQ", "YM"], None),
    ("RQ6_ES_NQ_2020_25", "RQ6", None, ["ES", "NQ"], 2020),
    ("RQ6_ES_NQ_full", "RQ6", None, ["ES", "NQ"], None),
]:
    r = eval_tablas_ops(rq_df, dname, ctrl, insts, min_yr=myr)
    d_rep = r.pop("_REP_daily_cfd", pd.Series(dtype=float))
    r.pop("_DESC_daily_cfd", None)
    results[label] = r
    if label in ("RQ2_ES_NQ_2020_25", "RQ6_ES_NQ_2020_25"):
        rep_daily[f"{label}_CFD"] = d_rep

# Save REP daily R & compute orthogonality vs Core4 on REP 2020-2025
# Determine exact REP dates from union of REP daily series (or core4 >= 20200101 on REP dates)
df_rep = pd.DataFrame(rep_daily).fillna(0.0).sort_index()
df_rep.index.name = "ses"
df_rep.to_csv(OUT_DIR / "LOCAL_TIER2_REP_DAILY_R.csv.gz", compression="gzip")

# Orthogonality on REP sessions
ortho = {}
rep_idx = core4.index.intersection(df_rep.index)
rep_idx20 = rep_idx[rep_idx >= 20200101]
c_rep20 = core4.loc[rep_idx20]
cm = c_rep20.groupby(c_rep20.index // 100).sum()
q20 = cm.quantile(0.20)
worst_m = cm[cm <= q20].index
for col in df_rep.columns:
    y = df_rep[col].reindex(rep_idx20, fill_value=0.0)
    ym = y.groupby(y.index // 100).sum()
    ortho[col] = {
        "rep20_sum_r": round(float(y.sum()), 2),
        "corr_d_vs_core4_rep20": round(float(c_rep20.corr(y)), 4) if y.std() > 0 else None,
        "corr_m_vs_core4_rep20": round(float(cm.corr(ym)), 4) if ym.std() > 0 else None,
        "core_worst20m_r": round(float(cm.loc[worst_m].sum()), 2),
        "cand_worst20m_r": round(float(ym.loc[worst_m].sum()), 2),
    }

out_all = {"strategies": results, "ortho_rep20": ortho}
(OUT_DIR / "LOCAL_TIER2_REP.json").write_text(json.dumps(out_all, indent=2), encoding="utf-8")

print("=== LOCAL TIER 2 CLEAN REP SUMMARY ===")
for k, v in results.items():
    rep = v.get("REP", {})
    dsc = v.get("DESC", {})
    if "cfd" in rep:
        rc, rf = rep["cfd"], rep["fut"]
        dc = dsc.get("cfd", {})
        print(f"{k:24s} | DESC CFD={dc.get('r_mean',0):+.4f}(n={dsc.get('n',0)}) | REP CFD={rc['r_mean']:+.4f} (n={rc['n']}, PF={rc['pf']:.2f}, t={rc['t']:+.2f}, p={rc['p']:.4f}) | FUT={rf['r_mean']:+.4f} (t={rf['t']:+.2f})")
    elif rep.get("n", 0) > 0:
        print(f"{k:24s} | DESC R={dsc.get('r_mean',0):+.4f}(n={dsc.get('n',0)}) | REP R={rep['r_mean']:+.4f} (n={rep['n']}, PF={rep['pf']:.2f}, t={rep['t']:+.2f})")
print("=== ORTHO VS CORE4 (REP 2020-25) ===")
for k, v in ortho.items():
    print(f"{k:24s} {v}")
