"""Adenda D — analisis local de la tabla de eventos de desarrollo (ES, 299 sesiones).

Pipeline completo (T1..T5) con validacion externa walk-forward por sesion (purga + embargo), seleccion interna por bloques de
sesiones y nulo del pipeline por desplazamiento circular de etiquetas. Todo con hiperparametros declarados de antemano.

Uso: python dev_filters_analysis.py <events.csv> <out.json> [--det NT8|PY] [--preset 1] [--res 100] [--fcode 1] [--nnull 100] [--friction 3.546]
Solo desarrollo: no acepta NQ/YM/holdout (la tabla ya excluye trade_date >= 20261001).
"""
from __future__ import annotations

import argparse
import json
import time
import warnings

import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import ElasticNetCV
from sklearn.tree import DecisionTreeRegressor

warnings.filterwarnings("ignore")
import lightgbm as lgb  # noqa: E402

FEATURES = [
    "h_ticks", "score", "slope_ticks", "elapsed", "zone_len", "trend_len", "post_ext_len", "d_orig_ticks", "d_outer_ticks", "close_frac",
    "atr_ticks", "h_over_atr", "ema_dist_atr", "bars_outside", "max_ext_ticks", "bar_range_ticks", "bar_body_ticks", "speed3", "speed10",
    "bar_dur_s", "pace5", "zone_vol", "zone_vol_pct50", "vol_ret5_ratio", "vol_bar_ratio", "poc_frac", "va_lo_frac", "va_hi_frac", "path_share",
    "outer_share", "node_ratio", "sector_share", "zone_ticks", "sess_range_ticks", "sess_pos_td", "dist_fwd_ticks", "dist_bwd_ticks",
    "mins_since_open", "rv50_atr", "hr_sin", "hr_cos",
]
BASELINE = ["hr_sin", "hr_cos", "atr_ticks", "rv50_atr", "bar_range_ticks", "speed3", "speed10", "sess_range_ticks", "mins_since_open", "vol_bar_ratio"]
Q_GRID = (0.3, 0.5, 0.7)


def prepare(df, friction):
    df = df.copy()
    td = df["trade_dir"].values
    df["sess_pos_td"] = np.where(td == 1, df["sess_pos"], 1.0 - df["sess_pos"])
    df["dist_fwd_ticks"] = np.where(td == 1, df["dist_hi_ticks"], df["dist_lo_ticks"])
    df["dist_bwd_ticks"] = np.where(td == 1, df["dist_lo_ticks"], df["dist_hi_ticks"])
    D = df["D_10H"].values
    o = df["out_10H"].values
    df["pnl"] = np.where(o == 1, D, np.where(o == -1, -D, df["ret_end_ticks"].values))
    df["pnl_net"] = df["pnl"] - friction
    df["win"] = (o == 1).astype(int)
    df["resolved"] = (o != 0).astype(int)
    return df.sort_values(["trade_date", "entry_bar"]).reset_index(drop=True)


def purge_no_overlap(df):
    keep = np.zeros(len(df), bool)
    last_sid, last_exit = None, -1
    for i, (sid, b, ex) in enumerate(zip(df["session_id"].values, df["entry_bar"].values, df["exit_10H"].values)):
        if sid != last_sid:
            last_sid, last_exit = sid, -1
        if b > last_exit:
            keep[i] = True
            last_exit = max(last_exit, ex)
    return df[keep].reset_index(drop=True)


def session_blocks(sessions, k):
    return [list(a) for a in np.array_split(sessions, k)]


def impute(Xtr, Xte):
    med = np.nanmedian(Xtr, axis=0)
    med = np.where(np.isnan(med), 0.0, med)
    f = lambda X: np.where(np.isnan(X), med, X)
    return f(Xtr), f(Xte)


def inner_splits(df_tr, k=4, embargo=1):
    sess = np.array(sorted(df_tr["session_id"].unique()))
    blocks = session_blocks(sess, k)
    out = []
    for bi, blk in enumerate(blocks):
        lo, hi = blk[0], blk[-1]
        val = df_tr["session_id"].between(lo, hi).values
        tr = ~df_tr["session_id"].between(lo - embargo, hi + embargo).values
        if val.sum() > 20 and tr.sum() > 50:
            out.append((np.where(tr)[0], np.where(val)[0]))
    return out


# --------- herramientas: cada una devuelve fit(Xtr,ytr_df)->scorer(X)->score (mayor = mejor) ---------
def tool_T1(X, df, cols):
    """Mejor variable simple (signo +/-) elegida por validacion interna: media de pnl_net en la mitad superior del puntaje."""
    y = df["pnl_net"].values
    splits = inner_splits(df)
    best, best_val = None, -1e9
    for j in range(X.shape[1]):
        for sg in (1.0, -1.0):
            vals = []
            for tr, va in splits:
                thr = np.median(sg * X[tr, j])
                m = sg * X[va, j] >= thr
                if m.sum() >= 5:
                    vals.append(y[va][m].mean())
            if vals and np.mean(vals) > best_val:
                best_val, best = np.mean(vals), (j, sg)
    j, sg = best
    return (lambda Z: sg * Z[:, j]), {"feature": cols[j], "sign": sg}


def tool_T2(X, df, cols):
    y = df["pnl_net"].values
    mu, sd = X.mean(0), X.std(0) + 1e-9
    Xs = (X - mu) / sd
    m = ElasticNetCV(l1_ratio=[0.2, 0.5, 0.9], cv=inner_splits(df) or 3, max_iter=4000, n_alphas=20).fit(Xs, y)
    return (lambda Z: m.predict((Z - mu) / sd)), {"nonzero": int((np.abs(m.coef_) > 1e-9).sum())}


def tool_T3(X, df, cols):
    y = df["pnl_net"].values
    t = DecisionTreeRegressor(max_depth=3, min_samples_leaf=max(30, int(0.1 * len(y))), random_state=0).fit(X, y)
    return (lambda Z: t.predict(Z)), {}


def _lgb_params(n, seed=0):
    return dict(n_estimators=120, learning_rate=0.05, num_leaves=6, min_child_samples=max(20, n // 50), subsample=0.8, subsample_freq=1,
                colsample_bytree=0.8, reg_lambda=5.0, verbose=-1, n_jobs=4, random_state=seed)


def tool_T4(X, df, cols):
    y = df["pnl_net"].values
    m = lgb.LGBMRegressor(**_lgb_params(len(y))).fit(X, y)
    return (lambda Z: m.predict(Z)), {}


TOOLS = {"T1_univariate": tool_T1, "T2_elasticnet": tool_T2, "T3_tree3": tool_T3, "T4_lgbm": tool_T4}


def oof_scores(tool, X, df, cols):
    sc = np.full(len(df), np.nan)
    for tr, va in inner_splits(df):
        s, _ = tool(X[tr], df.iloc[tr].reset_index(drop=True), cols)
        sc[va] = s(X[va])
    return sc


def choose_q(sc, y):
    best_q, best_v = 0.5, -1e9
    ok = ~np.isnan(sc)
    for q in Q_GRID:
        thr = np.quantile(sc[ok], 1 - q)
        m = ok & (sc >= thr)
        if m.sum() >= 10 and y[m].mean() > best_v:
            best_q, best_v = q, y[m].mean()
    return best_q, np.quantile(sc[ok], 1 - best_q)


def tool_T5_select(df_tr, Xtr, df_te, Xte, F):
    """LightGBM clasificador de victoria entre resueltos + isotonica con OOF; actua si P*D-(1-P)*D-F > 0 (ignora el timeout en el criterio de entrada)."""
    r = df_tr["resolved"].values == 1
    if r.sum() < 80:
        return np.zeros(len(df_te), bool)
    ywin = df_tr["win"].values
    oof = np.full(len(df_tr), np.nan)
    for tr, va in inner_splits(df_tr):
        trr = tr[r[tr]]
        m = lgb.LGBMClassifier(**_lgb_params(len(trr))).fit(Xtr[trr], ywin[trr])
        oof[va] = m.predict_proba(Xtr[va])[:, 1]
    ok = ~np.isnan(oof) & r
    if ok.sum() < 50:
        return np.zeros(len(df_te), bool)
    iso = IsotonicRegression(out_of_bounds="clip").fit(oof[ok], ywin[ok])
    m = lgb.LGBMClassifier(**_lgb_params(int(r.sum()))).fit(Xtr[r], ywin[r])
    p = iso.predict(m.predict_proba(Xte)[:, 1])
    D = df_te["D_10H"].values
    return (p * D - (1 - p) * D - F) > 0


def run_pipeline(df, friction, cols, seed_label_shift=None, rng=None):
    """Walk-forward externo. Devuelve metricas agregadas por herramienta y por pliegue."""
    sessions = np.array(sorted(df["session_id"].unique()))
    chunks = session_blocks(sessions, 6)
    res = {k: {"sel": [], "all": [], "sid": [], "folds": []} for k in list(TOOLS) + ["T5_abstain"]}
    y_all = df["pnl_net"].values
    for fi in range(1, 6):
        te_s = chunks[fi]
        tr_s = [s for c in chunks[:fi] for s in c]
        if len(tr_s) < 30:
            continue
        gap = tr_s[-1]
        te = df["session_id"].between(te_s[0], te_s[-1]).values
        tr = df["session_id"].isin(tr_s).values & ~df["session_id"].between(te_s[0] - 1, te_s[0]).values
        dtr, dte = df[tr].reset_index(drop=True), df[te].reset_index(drop=True)
        Xtr, Xte = impute(dtr[cols].values.astype(float), dte[cols].values.astype(float))
        ytr = dtr["pnl_net"].values
        for name, tool in TOOLS.items():
            sc_oof = oof_scores(tool, Xtr, dtr, cols)
            q, thr = choose_q(sc_oof, ytr)
            scorer, info = tool(Xtr, dtr, cols)
            sel = scorer(Xte) >= thr
            res[name]["sel"].append(dte["pnl_net"].values[sel]); res[name]["all"].append(dte["pnl_net"].values)
            res[name]["sid"].append(dte["session_id"].values[sel])
            res[name]["folds"].append({"fold": fi, "q": q, "n_sel": int(sel.sum()), "n_test": len(dte), "E_sel": float(dte["pnl_net"].values[sel].mean()) if sel.any() else None,
                                       "E_all": float(dte["pnl_net"].mean()), "info": info})
        sel = tool_T5_select(dtr, Xtr, dte, Xte, friction)
        res["T5_abstain"]["sel"].append(dte["pnl_net"].values[sel]); res["T5_abstain"]["all"].append(dte["pnl_net"].values)
        res["T5_abstain"]["sid"].append(dte["session_id"].values[sel])
        res["T5_abstain"]["folds"].append({"fold": fi, "n_sel": int(sel.sum()), "n_test": len(dte),
                                           "E_sel": float(dte["pnl_net"].values[sel].mean()) if sel.any() else None, "E_all": float(dte["pnl_net"].mean())})
    out = {}
    for name, r in res.items():
        if not r["all"]:
            continue
        s = np.concatenate(r["sel"]) if r["sel"] else np.array([])
        a = np.concatenate(r["all"])
        out[name] = {"E_sel": float(s.mean()) if len(s) else None, "E_all": float(a.mean()), "dE": float(s.mean() - a.mean()) if len(s) else None,
                     "n_sel": int(len(s)), "n_all": int(len(a)), "retention": float(len(s) / len(a)), "folds": r["folds"],
                     "folds_pos": int(sum(1 for f in r["folds"] if f["E_sel"] is not None and f["E_sel"] > f["E_all"]))}
    return out


def baseline_dE(df, friction):
    """Baseline continuo fuerte: LightGBM sobre BASELINE; mismo protocolo (T4 con columnas del baseline)."""
    return run_pipeline(df, friction, BASELINE)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("events"); ap.add_argument("out")
    ap.add_argument("--det", default="NT8"); ap.add_argument("--preset", type=int, default=1); ap.add_argument("--res", type=int, default=100)
    ap.add_argument("--fcode", type=int, default=1); ap.add_argument("--nnull", type=int, default=100); ap.add_argument("--friction", type=float, default=3.546)
    ap.add_argument("--rth", type=int, default=1); ap.add_argument("--seed", type=int, default=20261015)
    a = ap.parse_args()
    t0 = time.time()
    raw = pd.read_csv(a.events)
    df = raw[(raw.det == a.det) & (raw.preset == a.preset) & (raw.res == a.res) & (raw.fcode == a.fcode)]
    if a.rth:
        df = df[df.rth_ct == 1]
    df = purge_no_overlap(prepare(df, a.friction))
    cols = [c for c in FEATURES if c in df.columns]
    print(f"N eventos (RTH CT, purgado)={len(df)}, sesiones={df.session_id.nunique()}, E_all={df.pnl_net.mean():.3f} ticks, wr_res={df[df.resolved==1].win.mean():.4f}", flush=True)
    obs = run_pipeline(df, a.friction, cols)
    base = baseline_dE(df, a.friction) if True else {}
    best = max(((k, v["dE"]) for k, v in obs.items() if v.get("dE") is not None), key=lambda x: x[1])
    print("observado:", {k: (round(v["dE"], 3), round(v["retention"], 2)) for k, v in obs.items() if v.get("dE") is not None}, "mejor:", best, flush=True)
    rng = np.random.default_rng(a.seed)
    null_max, N = [], len(df)
    lab = ["pnl", "pnl_net", "win", "resolved"]
    for r in range(a.nnull):
        k = int(rng.integers(int(0.2 * N), int(0.8 * N)))
        d2 = df.copy()
        for c in lab:
            d2[c] = np.roll(df[c].values, k)
        o2 = run_pipeline(d2, a.friction, cols)
        null_max.append(max(v["dE"] for v in o2.values() if v.get("dE") is not None))
        if (r + 1) % 10 == 0:
            print(f"nulo {r + 1}/{a.nnull} ({time.time() - t0:.0f}s)", flush=True)
    null_max = np.array(null_max)
    p = float((1 + np.sum(null_max >= best[1])) / (len(null_max) + 1)) if len(null_max) else None
    out = {"spec": "EXP-CORRIDOR-DEV-D analysis v1", "det": a.det, "preset": a.preset, "res": a.res, "fcode": a.fcode, "rth": a.rth, "friction": a.friction,
           "N": int(N), "n_sessions": int(df.session_id.nunique()), "E_all": float(df.pnl_net.mean()), "observed": obs, "baseline_continuo": base,
           "best_tool": best[0], "best_dE": best[1], "null_max_dE": null_max.tolist(), "p_pipeline": p, "elapsed_s": round(time.time() - t0, 1)}
    json.dump(out, open(a.out, "w"), indent=1)
    print("p_pipeline =", p, "| elapsed", out["elapsed_s"], flush=True)


if __name__ == "__main__":
    main()
