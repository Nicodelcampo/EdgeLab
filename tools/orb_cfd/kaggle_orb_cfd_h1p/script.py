"""ORB-CFD Fase 0B (manifiesto ORB_CFD_FASE0B_MANIFIESTO_20261017.md, aprobada opcion A).
Conjunto M UNICAMENTE (fecha de trading <= 2025-07-17). Celda primaria: rango 15 min, primer toque del mid, E al cierre (15:45 ET).
E = signo x (P_t - nivel_roto)/ancho; P_t = ultimo mid ESTRICTAMENTE anterior a t. Nulo: permutacion de signos entre dias (2000).
Descriptivo sin inferencia: 11:30, ventanas 5/30/60, media por ano, cuantiles, media recortada 1 %, bootstrap por bloques mensuales.
"""
import glob, json, math, os, time
from pathlib import Path
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

NS = 1_000_000_000
NS_MIN = 60 * NS
M_END_DAY = 20250717
OR_MINS = (5, 15, 30, 60)
PRIMARY_W = 15
HORIZONS = {"1130": 120, "1545": 375}
NULL_REPS = 2000
BOOT_REPS = 2000
MAX_GAP_S = 120.0
MAX_FIRST_S = 300.0
MIN_OR15 = 20
MIN_LATE = 100
INSTR = {"USA500": "ES", "USATECH": "NQ"}


def rth_rows(path):
    pf = pq.ParquetFile(path)
    T, D, M = [], [], []
    for b in pf.iter_batches(batch_size=4_000_000, columns=["time_utc_ns", "bid", "ask"]):
        t = b.column(0).to_numpy()
        bid = b.column(1).to_numpy()
        ask = b.column(2).to_numpy()
        et = pd.DatetimeIndex(t, tz="UTC").tz_convert("America/New_York")
        mins = et.hour.values * 60 + et.minute.values
        dint = (et.year.values * 10000 + et.month.values * 100 + et.day.values).astype(np.int64)
        m = (et.dayofweek.values < 5) & (mins >= 565) & (mins < 960) & (dint <= M_END_DAY)
        if m.any():
            T.append(t[m])
            D.append(dint[m])
            M.append((bid[m] + ask[m]) / 2.0)
    return np.concatenate(T), np.concatenate(D), np.concatenate(M)


def open_ns(td):
    return pd.Timestamp(td // 10000, (td // 100) % 100, td % 100, 9, 30, tz="America/New_York").tz_convert("UTC").value


def last_before(ts, px, t):
    i = int(np.searchsorted(ts, t, side="left")) - 1
    return float(px[i]) if i >= 0 else None


def session(td, ts, px):
    o = open_ns(int(td))
    sel = (ts >= o) & (ts <= o + 390 * NS_MIN)
    t, p = ts[sel], px[sel]
    w1 = t < o + 60 * NS_MIN
    if w1.sum() < 2:
        return None, "sin_rth"
    if (t[0] - o) / NS > MAX_FIRST_S:
        return None, "primera_cotizacion_tarde"
    if (np.diff(t[w1]) / NS).max() > MAX_GAP_S:
        return None, "hueco_mayor_120s"
    if (t < o + 15 * NS_MIN).sum() < MIN_OR15:
        return None, "pocas_cotizaciones_or15"
    if ((t >= o + 330 * NS_MIN) & (t < o + 375 * NS_MIN)).sum() < MIN_LATE:
        return None, "cierre_temprano"
    mnt = ((t - o) // NS_MIN).astype(np.int64)
    lastmin = pd.DataFrame({"m": mnt, "p": p}).groupby("m")["p"].last()
    out = {"td": int(td)}
    for W in OR_MINS:
        tw = o + W * NS_MIN
        inw = t < tw
        hi, lo = float(p[inw].max()), float(p[inw].min())
        width = hi - lo
        if width <= 0:
            continue
        post = t >= tw
        pt, pp = t[post], p[post]
        up, dn = np.flatnonzero(pp > hi), np.flatnonzero(pp < lo)
        c = []
        if len(up):
            c.append((int(pt[up[0]]), "up", hi))
        if len(dn):
            c.append((int(pt[dn[0]]), "down", lo))
        d = {"width": width}
        if c:
            tb, side, lvl = min(c)
            sg = 1.0 if side == "up" else -1.0
            for tag, h in HORIZONS.items():
                if tb < o + h * NS_MIN:
                    P = last_before(t, p, o + h * NS_MIN)
                    sub = lastmin[lastmin.index <= h - 1]
                    P2 = float(sub.iloc[-1]) if len(sub) else None
                    d["s_" + tag] = sg
                    d["D_" + tag] = (P - lvl) / width
                    d["E_" + tag] = sg * (P - lvl) / width
                    d["Eabs_" + tag] = abs(P - lvl) / width
                    d["dis_" + tag] = int(P != P2)
        out[W] = d
    return out, None


def stats(R, W, tag, rng):
    rows = [(r["td"], r[W]) for r in R if W in r and ("E_" + tag) in r[W]]
    if len(rows) < 5:
        return {"n_days": len(rows)}
    tds = np.array([a for a, _ in rows])
    E = np.array([d["E_" + tag] for _, d in rows])
    sg = np.array([d["s_" + tag] for _, d in rows])
    D = np.array([d["D_" + tag] for _, d in rows])
    n = len(E)
    mu, sd = float(E.mean()), float(E.std(ddof=1))
    se = sd / math.sqrt(n)
    nm = np.array([float((sg[rng.permutation(n)] * D).mean()) for _ in range(NULL_REPS)])
    p1 = float((1 + np.sum(nm >= mu)) / (NULL_REPS + 1.0))
    p2 = float((1 + np.sum(np.abs(nm - nm.mean()) >= abs(mu - nm.mean()))) / (NULL_REPS + 1.0))
    h = n // 2
    s = np.sort(E)
    k = int(0.01 * n)
    months = tds // 100
    um = np.unique(months)
    groups = [E[months == m] for m in um]
    bm = np.array([np.concatenate([groups[i] for i in rng.integers(0, len(um), len(um))]).mean() for _ in range(BOOT_REPS)])
    years = {}
    for y in np.unique(tds // 10000):
        e = E[(tds // 10000) == y]
        years[int(y)] = {"n": int(len(e)), "mean": float(e.mean())}
    return {"n_days": n, "mean_E": mu, "sd": sd, "se": se, "ci95": [mu - 1.96 * se, mu + 1.96 * se],
            "MDE_80pct_2p5onesided_R": 2.8 * sd / math.sqrt(n),
            "null_sign_permutation": {"mean": float(nm.mean()), "p975": float(np.percentile(nm, 97.5)),
                                      "p_value_one_sided": p1, "p_value_two_sided": p2},
            "half1_mean": float(E[:h].mean()), "half2_mean": float(E[h:].mean()), "half1_n": int(h), "half2_n": int(n - h),
            "quantiles_5_25_50_75_95": [float(np.percentile(E, q)) for q in (5, 25, 50, 75, 95)],
            "median": float(np.median(E)), "trimmed_mean_1pct": float(s[k:n - k].mean()) if n > 2 * k else None,
            "frac_positive": float((E > 0).mean()), "mean_abs_extension": float(np.mean([d["Eabs_" + tag] for _, d in rows])),
            "block_bootstrap_month_ci95": [float(np.percentile(bm, 2.5)), float(np.percentile(bm, 97.5))],
            "mean_by_year": years, "second_path_disagreements": int(sum(d["dis_" + tag] for _, d in rows))}


def verdict(p):
    if not p or p.get("n_days", 0) < 5:
        return "SIN_DATOS", {}
    lo, hi = p["ci95"]
    pn = p["null_sign_permutation"]["p_value_one_sided"]
    gi = {"MDE_ok_le_0.25R": p["MDE_80pct_2p5onesided_R"] <= 0.25, "ci_lower_gt_0": lo > 0, "p_lt_0.025": pn < 0.025,
          "both_halves_positive": p["half1_mean"] > 0 and p["half2_mean"] > 0,
          "ci_within_pm0.10": (lo >= -0.10 and hi <= 0.10), "p_gt_0.10": pn > 0.10}
    if gi["ci_lower_gt_0"] and gi["p_lt_0.025"] and gi["both_halves_positive"]:
        return "SENAL_EN_M", gi
    if gi["ci_within_pm0.10"] and gi["p_gt_0.10"]:
        return "NO_GO", gi
    return "ABSTENCION", gi


def run(inst, path):
    t0 = time.time()
    ts, day, mid = rth_rows(path)
    ud, st = np.unique(day, return_index=True)
    en = np.append(st[1:], len(day))
    recs, disc = [], {}
    for td, a, b in zip(ud, st, en):
        r, why = session(td, ts[a:b], mid[a:b])
        if r is None:
            disc[why] = disc.get(why, 0) + 1
        else:
            recs.append(r)
    rng = np.random.default_rng(20261017)
    out = {"n_days_total": int(len(ud)), "n_days_valid": len(recs), "discards": disc,
           "first_day": int(ud[0]), "last_day": int(ud[-1])}
    for W in OR_MINS:
        for tag in HORIZONS:
            out["W%d_%s" % (W, tag)] = stats(recs, W, tag, rng)
    v, gi = verdict(out["W%d_1545" % PRIMARY_W])
    out["VERDICT_M"] = v
    out["gate_inputs"] = gi
    out["elapsed_s"] = round(time.time() - t0, 1)
    return out


def main():
    out_dir = Path(os.environ.get("STUDY_OUT", "/kaggle/working"))
    out_dir.mkdir(parents=True, exist_ok=True)
    allp = sorted(glob.glob("/kaggle/input/**/*_ticks.parquet", recursive=True))
    res = {"spec_id": "EXP-ORB-CFD-0B-M-V1", "manifest": "ORB_CFD_FASE0B_MANIFIESTO_20261017.md",
           "set": "M (<= 2025-07-17)", "holdout_touched": False, "price": "mid"}
    for inst in INSTR:
        p = [x for x in allp if inst in os.path.basename(x)]
        try:
            res[inst] = run(inst, p[0])
            print("OK", inst, res[inst]["VERDICT_M"], flush=True)
        except Exception as e:
            res[inst] = {"ERROR": repr(e)[:500]}
            print("ERR", inst, repr(e)[:500], flush=True)
    txt = json.dumps(res, indent=1, default=float)
    (out_dir / "EXP_ORB_CFD_0B_M_RESULTS.json").write_text(txt, encoding="utf-8")
    print("=== CFD0B_START ===\n" + txt[:150000] + "\n=== CFD0B_END ===", flush=True)




# ======================================================================================
# ORB-CFD H1 - Nivel P (manifiesto ORB_CFD_H1_HERRAMIENTAS_MANIFIESTO_20261017.md, secc. 2-3 y enmienda A1).
# Se concatena DESPUES de orb_cfd_0b.py (sin su main). Conjunto M (<= 2025-07-17). Celda: rango 15 min, primer toque, E al cierre.
# 6 hipotesis (precio): H1 gap, H2 ancho relativo, H3 espacio libre, H4 velocidad, H5 tendencia previa, H6 ElasticNet walk-forward.
# ======================================================================================
from sklearn.linear_model import ElasticNetCV
from sklearn.model_selection import TimeSeriesSplit

MIN_HIST_BREAKS = 60
EN_MIN_TRAIN = 500
EN_REFIT = 250
EN_PURGE = 5
PERM_REPS = 2000
HYP = ["H1_gap", "H2_ancho_rel", "H3_espacio", "H4_velocidad", "H5_tendencia_previa", "H6_elasticnet"]


def daily_summary(ts, day, mid):
    ud, st = np.unique(day, return_index=True)
    en = np.append(st[1:], len(day))
    out = []
    for td, a, b in zip(ud, st, en):
        o = open_ns(int(td))
        t, p = ts[a:b], mid[a:b]
        sel = (t >= o) & (t < o + 390 * NS_MIN)
        if sel.sum() < 50:
            out.append({"td": int(td), "ok": False})
            continue
        tt, pp = t[sel], p[sel]
        w = tt < o + 15 * NS_MIN
        wid = float(pp[w].max() - pp[w].min()) if w.sum() >= 5 else None
        out.append({"td": int(td), "ok": True, "open": float(pp[0]), "close": float(pp[-1]), "hi": float(pp.max()),
                    "lo": float(pp.min()), "w15": wid})
    return out


def break_info(ts, day, mid, td_a, td_b):
    o = open_ns(int(td_a))
    t, p = ts[td_b[0]:td_b[1]], mid[td_b[0]:td_b[1]]
    sel = (t >= o) & (t <= o + 390 * NS_MIN)
    t, p = t[sel], p[sel]
    tw = o + 15 * NS_MIN
    inw = t < tw
    hi, lo = float(p[inw].max()), float(p[inw].min())
    post = t >= tw
    pt, pp = t[post], p[post]
    up, dn = np.flatnonzero(pp > hi), np.flatnonzero(pp < lo)
    c = []
    if len(up):
        c.append((int(pt[up[0]]), "up", hi))
    if len(dn):
        c.append((int(pt[dn[0]]), "down", lo))
    if not c:
        return None
    tb, side, lvl = min(c)
    return {"side": 1.0 if side == "up" else -1.0, "level": lvl, "width": hi - lo, "speed_min": (tb - tw) / NS_MIN}


def build_rows(ts, day, mid):
    ds = daily_summary(ts, day, mid)
    ud, st = np.unique(day, return_index=True)
    en = np.append(st[1:], len(day))
    span = {int(td): (int(a), int(b)) for td, a, b in zip(ud, st, en)}
    widths_hist = []
    rows = []
    prev = None
    for d in ds:
        td = d["td"]
        if not d["ok"]:
            continue
        r_sess, why = session(td, ts[span[td][0]:span[td][1]], mid[span[td][0]:span[td][1]])
        if prev is not None and r_sess is not None and PRIMARY_W in r_sess and "E_1545" in r_sess[PRIMARY_W] and len(widths_hist) >= 20:
            bi = break_info(ts, day, mid, td, span[td])
            if bi is not None and bi["width"] > 0:
                w = bi["width"]
                sgn = bi["side"]
                pdh, pdl = prev["hi"], prev["lo"]
                room = (pdh - bi["level"]) / w if sgn > 0 else (bi["level"] - pdl) / w
                rows.append({
                    "td": td, "E": r_sess[PRIMARY_W]["E_1545"], "sgn": sgn, "width": w,
                    "gap": d["open"] - prev["close"], "wrel": w / float(np.median(widths_hist[-20:])),
                    "room": min(max(room, 0.0), 99.0), "speed": bi["speed_min"],
                    "trend": prev["close"] - prev["open"]})
        if d["w15"] is not None and d["w15"] > 0:
            widths_hist.append(d["w15"])
        prev = d
    return rows


def welch(a, b):
    na, nb = len(a), len(b)
    d = float(a.mean() - b.mean())
    se = math.sqrt(a.var(ddof=1) / na + b.var(ddof=1) / nb)
    return d, se


def cut_expanding_median(vals):
    cut = np.full(len(vals), np.nan)
    for i in range(len(vals)):
        if i >= MIN_HIST_BREAKS:
            cut[i] = np.median(vals[:i])
    return cut


def hyp_labels(rows):
    sg = np.array([r["sgn"] for r in rows])
    gap = np.array([r["gap"] for r in rows])
    tr = np.array([r["trend"] for r in rows])
    wrel = np.array([r["wrel"] for r in rows])
    room = np.array([r["room"] for r in rows])
    spd = np.array([r["speed"] for r in rows])
    n = len(rows)
    lab = {}
    ok = np.arange(n) >= MIN_HIST_BREAKS
    g = np.sign(sg * gap)
    lab["H1_gap"] = (g > 0, ok & (g != 0))
    lab["H2_ancho_rel"] = (wrel > 1.0, ok)
    cr = cut_expanding_median(room)
    lab["H3_espacio"] = (room > cr, ok & ~np.isnan(cr))
    cs = cut_expanding_median(spd)
    lab["H4_velocidad"] = (spd < cs, ok & ~np.isnan(cs))
    t5 = np.sign(sg * tr)
    lab["H5_tendencia_previa"] = (t5 > 0, ok & (t5 != 0))
    return lab


def elasticnet_labels(rows, rng_seed=20261017):
    n = len(rows)
    sg = np.array([r["sgn"] for r in rows]); w = np.array([r["width"] for r in rows])
    X = np.column_stack([
        np.clip(sg * np.array([r["gap"] for r in rows]) / w, -5, 5),
        np.log(np.array([r["wrel"] for r in rows])),
        np.minimum(np.array([r["room"] for r in rows]), 10.0),
        np.log1p(np.array([r["speed"] for r in rows])),
        np.clip(sg * np.array([r["trend"] for r in rows]) / w, -10, 10)])
    y = np.clip(np.array([r["E"] for r in rows]), -5, 5)
    fav = np.zeros(n, dtype=bool)
    elig = np.zeros(n, dtype=bool)
    model, mu, sd, cut = None, None, None, None
    last_fit = None
    coefs = []
    for i in range(EN_MIN_TRAIN + EN_PURGE, n):
        if model is None or (i - last_fit) >= EN_REFIT:
            tr_end = i - EN_PURGE
            Xt, yt = X[:tr_end], y[:tr_end]
            mu, sd = Xt.mean(axis=0), Xt.std(axis=0) + 1e-9
            try:
                model = ElasticNetCV(l1_ratio=[0.1, 0.5, 0.9], n_alphas=30, cv=TimeSeriesSplit(5), max_iter=20000, random_state=rng_seed)
            except TypeError:
                model = ElasticNetCV(l1_ratio=[0.1, 0.5, 0.9], alphas=30, cv=TimeSeriesSplit(5), max_iter=20000, random_state=rng_seed)
            model.fit((Xt - mu) / sd, yt)
            cut = float(np.median(model.predict((Xt - mu) / sd)))
            last_fit = i
            coefs.append({"fit_at_index": int(i), "alpha": float(model.alpha_), "l1_ratio": float(model.l1_ratio_),
                          "coef": [float(c) for c in model.coef_], "intercept": float(model.intercept_)})
        pr = float(model.predict(((X[i] - mu) / sd).reshape(1, -1))[0])
        fav[i] = pr > cut
        elig[i] = True
    return (fav, elig), coefs


def test_hyp(rows, fav, elig, rng):
    idx = np.flatnonzero(elig)
    E = np.array([rows[i]["E"] for i in idx])
    f = fav[idx]
    if f.sum() < 10 or (~f).sum() < 10:
        return {"n_eligible": int(len(idx)), "n_fav": int(f.sum()), "n_unfav": int((~f).sum()), "undefined": True, "p_one_sided": 1.0}
    d, se = welch(E[f], E[~f])
    nm = np.empty(PERM_REPS)
    for k in range(PERM_REPS):
        pm = rng.permutation(f)
        nm[k] = E[pm].mean() - E[~pm].mean()
    p1 = float((1 + np.sum(nm >= d)) / (PERM_REPS + 1.0))
    h = len(E) // 2
    fa, fb = f[:h], f[h:]
    dh = []
    for sl_E, sl_f in ((E[:h], fa), (E[h:], fb)):
        dh.append(float(sl_E[sl_f].mean() - sl_E[~sl_f].mean()) if sl_f.sum() > 2 and (~sl_f).sum() > 2 else float("nan"))
    mf, sf = float(E[f].mean()), float(E[f].std(ddof=1) / math.sqrt(f.sum()))
    q = lambda x: [float(np.percentile(x, k)) for k in (5, 25, 50, 75, 95)]
    return {"n_eligible": int(len(idx)), "n_fav": int(f.sum()), "n_unfav": int((~f).sum()),
            "mean_fav": mf, "mean_fav_ci95": [mf - 1.96 * sf, mf + 1.96 * sf], "mean_unfav": float(E[~f].mean()),
            "sd_fav": float(E[f].std(ddof=1)), "sd_unfav": float(E[~f].std(ddof=1)),
            "D": d, "D_se": se, "D_ci95": [d - 1.96 * se, d + 1.96 * se], "MDE_D_80pct": 2.8 * se,
            "p_one_sided": p1, "D_by_half": dh, "q_fav": q(E[f]), "q_unfav": q(E[~f])}


def holm(ps):
    order = np.argsort(ps)
    m = len(ps)
    adj = np.empty(m)
    run = 0.0
    for rank, i in enumerate(order):
        run = max(run, (m - rank) * ps[i])
        adj[i] = min(1.0, run)
    return adj


def run_h1(path, inst):
    t0 = time.time()
    ts, day, mid = rth_rows(path)
    rows = build_rows(ts, day, mid)
    rng = np.random.default_rng(20261017)
    out = {"n_break_days_with_history": len(rows)}
    res = {}
    lab = hyp_labels(rows)
    for h in HYP[:5]:
        res[h] = test_hyp(rows, lab[h][0], lab[h][1], rng)
    try:
        (fav, elig), coefs = elasticnet_labels(rows)
        res["H6_elasticnet"] = test_hyp(rows, fav, elig, rng)
        out["elasticnet_fits"] = coefs
    except Exception as e:
        res["H6_elasticnet"] = {"ERROR": repr(e)[:300], "p_one_sided": 1.0}
    ps = np.array([res[h].get("p_one_sided", 1.0) for h in HYP])
    adj = holm(ps)
    for h, a in zip(HYP, adj):
        res[h]["p_holm"] = float(a)
    out["hypotheses"] = res
    out["corr_features"] = np.corrcoef(np.array([[r["sgn"] * r["gap"] / r["width"], np.log(r["wrel"]), min(r["room"], 10), np.log1p(r["speed"]), r["sgn"] * r["trend"] / r["width"]] for r in rows]).T).round(3).tolist()
    out["base_mean_E_all_rows"] = float(np.mean([r["E"] for r in rows]))
    out["elapsed_s"] = round(time.time() - t0, 1)
    return out


def classify(usa500, usatech):
    verdict = {}
    for h in HYP:
        a = usa500["hypotheses"].get(h, {})
        b = usatech["hypotheses"].get(h, {})
        if a.get("undefined") or "D" not in a:
            verdict[h] = "SIN_DATOS"
            continue
        dh = a["D_by_half"]
        mejora = (a["p_holm"] < 0.05 and a["mean_fav_ci95"][0] > 0 and all((x == x and x > 0) for x in dh)
                  and ("D" in b and b["D"] > 0))
        nomejora = a["D_ci95"][0] >= -0.25 and a["D_ci95"][1] <= 0.25
        verdict[h] = "MEJORA_EN_M" if mejora else ("NO_MEJORA" if nomejora else "ABSTENCION")
    return verdict


def main_h1():
    out_dir = Path(os.environ.get("STUDY_OUT", "/kaggle/working"))
    out_dir.mkdir(parents=True, exist_ok=True)
    allp = sorted(glob.glob("/kaggle/input/**/*_ticks.parquet", recursive=True))
    res = {"spec_id": "EXP-ORB-CFD-H1-P-V1", "manifest": "ORB_CFD_H1_HERRAMIENTAS_MANIFIESTO_20261017.md (+A1)", "set": "M (<= 2025-07-17)",
           "holdout_touched": False}
    for inst in INSTR:
        p = [x for x in allp if inst in os.path.basename(x)]
        try:
            res[inst] = run_h1(p[0], inst)
            print("OK", inst, flush=True)
        except Exception as e:
            import traceback
            res[inst] = {"ERROR": repr(e)[:500], "tb": traceback.format_exc()[-1500:]}
            print("ERR", inst, repr(e)[:500], flush=True)
    if "hypotheses" in res.get("USA500", {}) and "hypotheses" in res.get("USATECH", {}):
        res["VERDICTS"] = classify(res["USA500"], res["USATECH"])
    txt = json.dumps(res, indent=1, default=float)
    (out_dir / "EXP_ORB_CFD_H1_P_RESULTS.json").write_text(txt, encoding="utf-8")
    print("=== H1P_START ===\n" + txt[:150000] + "\n=== H1P_END ===", flush=True)


if __name__ == "__main__":
    main_h1()
