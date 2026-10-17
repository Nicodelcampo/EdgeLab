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


if __name__ == "__main__":
    main()
