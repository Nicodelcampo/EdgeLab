"""Estadística DESCRIPTIVA de las zonas de tendencia estable (sin hipótesis sobre el precio): anatomía, contextos, tipología y secuencias.
Las funciones trabajan sobre filas por zona; solo los resúmenes se publican (la tabla por zona queda privada)."""
from __future__ import annotations

import numpy as np

FEATS = ["len", "move_atr", "slope_atr_bar", "touches", "gap_mean_atr", "near_far_ratio", "atr_pts", "activity"]


def zone_rows(zones, c, h, l, e, atr, end_ns, volume, sd, hour_ct, minute_ct, tick, contract, inset):
    """Atributos por zona confirmada. Todas las medidas son geométricas/temporales de la propia zona."""
    n = len(c); rows = []
    smax = np.maximum.accumulate; import pandas as pd
    ser_h = pd.Series(h); ser_l = pd.Series(l); g = pd.Series(sd)
    run_max = ser_h.groupby(g).cummax().to_numpy(); run_min = ser_l.groupby(g).cummin().to_numpy()
    for z in zones:
        if not z.get("confirmed") or not inset[z["detect"]]: continue
        a, b = z["start"], z["end"]; L = b - a + 1; line = z["line"]; env = z.get("env", {}); at = float(atr[b]) if atr[b] > 0 else np.nan
        mins = float(end_ns[b] - end_ns[a]) / 6e10; tod = hour_ct[a:b + 1] * 60 + minute_ct[a:b + 1]; rth = float(np.mean((tod >= 510) & (tod < 900)))
        rng = run_max[a] - run_min[a]
        rows.append(dict(contract=contract, session=str(sd[a]), dir=int(z["dir"]), start_hour=int(hour_ct[a]), weekday=int(__import__("datetime").date.fromisoformat(str(sd[a])).weekday()), len=int(L), minutes=round(mins, 1),
                         move_atr=float(abs(c[b] - c[a]) / at), move_pts=float(abs(c[b] - c[a]) * tick), slope_atr_bar=float(abs(line["slope"]) / at), touches=int(line["touches"]),
                         touch_per_100=float(100 * line["touches"] / L), gap_mean_atr=float(np.mean(np.abs(e[a:b + 1] - c[a:b + 1])) / at), near_far_ratio=float(env["near_mean"] / env["far_mean"]) if env.get("far_mean") else np.nan,
                         far_cv=float(env.get("far_cv", np.nan)), near_cv=float(env.get("near_cv", np.nan)), atr_pts=float(at * tick), activity=float(L / max(mins, 1e-9)), rth_frac=round(rth, 2),
                         bars_last_touch_to_end=int(b - z["last_touch"]), end_reason=z["end_reason"], range_pos_start=float((c[a] - run_min[a]) / rng) if rng > 0 else np.nan,
                         start_bar=int(a), end_bar=int(b)))
    return rows


def _q(a):
    a = np.asarray([x for x in a if np.isfinite(x)], float)
    return None if len(a) == 0 else dict(p10=float(np.percentile(a, 10)), median=float(np.median(a)), p90=float(np.percentile(a, 90)), n=int(len(a)))


def _rank(x):
    o = np.argsort(np.argsort(x)); return o.astype(float)


def kmeans(X, k, seed=0, iters=60):
    rng = np.random.default_rng(seed); n = len(X); C = [X[rng.integers(n)]]
    for _ in range(k - 1):
        d2 = np.min([((X - c) ** 2).sum(1) for c in C], axis=0); C.append(X[rng.choice(n, p=d2 / d2.sum())] if d2.sum() > 0 else X[rng.integers(n)])
    C = np.array(C)
    for _ in range(iters):
        lab = np.argmin(((X[:, None, :] - C[None]) ** 2).sum(2), axis=1); newC = np.array([X[lab == j].mean(0) if (lab == j).any() else C[j] for j in range(k)])
        if np.allclose(newC, C): break
        C = newC
    return lab, C


def summarize(rows, k=4, seed=0):
    if not rows: return {}
    out = dict(n_zones=len(rows), n_sessions=len({(r["contract"], r["session"]) for r in rows})); A = {f: np.array([r[f] for r in rows], float) for f in FEATS + ["move_pts", "minutes", "rth_frac", "bars_last_touch_to_end", "range_pos_start", "far_cv", "near_cv", "touch_per_100"]}
    out["distributions"] = {f: _q(v) for f, v in A.items()}
    dirs = np.array([r["dir"] for r in rows]); out["direction"] = dict(up=int((dirs > 0).sum()), down=int((dirs < 0).sum()))
    out["end_reason"] = {k_: int(sum(1 for r in rows if r["end_reason"] == k_)) for k_ in sorted({r["end_reason"] for r in rows})}
    def by(key, vals):
        res = {}
        for v in vals:
            idx = [i for i, r in enumerate(rows) if r[key] == v]
            if idx: res[str(v)] = dict(n=len(idx), len_median=float(np.median(A["len"][idx])), move_atr_median=float(np.median(A["move_atr"][idx])), slope_median=float(np.median(A["slope_atr_bar"][idx])), up_share=round(float((dirs[idx] > 0).mean()), 2))
        return res
    out["by_start_hour_ct"] = by("start_hour", range(24)); out["by_weekday"] = by("weekday", range(5))
    t1, t2 = np.percentile(A["atr_pts"], [33.3, 66.7]); terc = np.where(A["atr_pts"] <= t1, "baja", np.where(A["atr_pts"] <= t2, "media", "alta")); out["by_volatility_tercile"] = dict(cuts_atr_pts=[float(t1), float(t2)], **{t: dict(n=int((terc == t).sum()), len_median=float(np.median(A["len"][terc == t])), move_atr_median=float(np.median(A["move_atr"][terc == t])), slope_median=float(np.median(A["slope_atr_bar"][terc == t]))) for t in ("baja", "media", "alta") if (terc == t).any()})
    F = ["len", "move_atr", "slope_atr_bar", "touches", "gap_mean_atr", "atr_pts", "activity"]; M = np.array([_rank(A[f]) for f in F]); C = np.corrcoef(M)
    out["spearman"] = {F[i]: {F[j]: round(float(C[i, j]), 2) for j in range(len(F))} for i in range(len(F))}
    # secuencias por sesión
    by_s = {}
    for r in rows: by_s.setdefault((r["contract"], r["session"]), []).append(r)
    cnt = np.array([len(v) for v in by_s.values()]); gaps, same, tot, overlap, pairs = [], 0, 0, 0, 0
    for v in by_s.values():
        v.sort(key=lambda r: r["start_bar"])
        for p, q in zip(v[:-1], v[1:]):
            tot += 1; same += int(p["dir"] == q["dir"]); gaps.append(q["start_bar"] - p["end_bar"])
            if q["start_bar"] <= p["end_bar"]: overlap += 1
    out["per_session"] = dict(zones_per_session=_q(cnt), sessions_with_zero_not_observable="solo se cuentan sesiones con al menos una zona", histogram={str(i): int((cnt == i).sum()) for i in range(1, 6)} | {"6+": int((cnt >= 6).sum())})
    out["sequence"] = dict(pairs=tot, same_direction_share=round(same / tot, 3) if tot else None, overlap_share=round(overlap / tot, 3) if tot else None, gap_bars_between_zones=_q(gaps))
    # tipología
    Xf = np.column_stack([np.log(A["len"]), A["slope_atr_bar"], A["touches"], A["gap_mean_atr"], np.nan_to_num(A["near_far_ratio"], nan=np.nanmedian(A["near_far_ratio"]))]); X = (Xf - Xf.mean(0)) / (Xf.std(0) + 1e-12)
    lab, Cn = kmeans(X, k, seed); order = np.argsort(Cn[:, 0]); remap = {int(o): i for i, o in enumerate(order)}; lab = np.array([remap[int(x)] for x in lab]); sess = np.array([r["session"] for r in rows]); half = np.median(np.unique(sess).astype(str).view(np.uint8).size and np.arange(len(np.unique(sess)))) if False else None
    uniq = sorted(set(sess)); first = np.isin(sess, uniq[:len(uniq) // 2]); types = {}
    for j in range(k):
        m = lab == j
        if not m.any(): continue
        types[f"tipo_{j}"] = dict(n=int(m.sum()), share=round(float(m.mean()), 3), share_first_half=round(float((m & first).sum() / max(first.sum(), 1)), 3), share_second_half=round(float((m & ~first).sum() / max((~first).sum(), 1)), 3),
                                  len_median=float(np.median(A["len"][m])), slope_median=float(np.median(A["slope_atr_bar"][m])), touches_median=float(np.median(A["touches"][m])), gap_mean_atr_median=float(np.median(A["gap_mean_atr"][m])), near_far_median=float(np.nanmedian(A["near_far_ratio"][m])),
                                  move_atr_median=float(np.median(A["move_atr"][m])), up_share=round(float((dirs[m] > 0).mean()), 2), top_start_hours=[int(h) for h in np.argsort(-np.bincount([rows[i]["start_hour"] for i in np.flatnonzero(m)], minlength=24))[:3]])
    out["typology_kmeans"] = dict(k=k, features=["log(largo)", "pendiente ATR/barra", "toques", "distancia media a EMA (ATR)", "razón acercamiento/alejamiento"], types=types, note="agrupación exploratoria; k elegido a mano; sin hipótesis sobre el precio")
    h1, h2 = ~np.zeros(len(rows), bool) & first, ~first
    out["halves"] = {n: dict(n=int(m.sum()), len_median=float(np.median(A["len"][m])) if m.any() else None, move_atr_median=float(np.median(A["move_atr"][m])) if m.any() else None, slope_median=float(np.median(A["slope_atr_bar"][m])) if m.any() else None) for n, m in (("primera_mitad", h1), ("segunda_mitad", h2))}
    return out
