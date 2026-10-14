"""Estadística DESCRIPTIVA de las zonas de tendencia estable (sin hipótesis sobre el precio): anatomía, contextos, tipología y secuencias.
Las funciones trabajan sobre filas por zona; solo los resúmenes se publican (la tabla por zona queda privada)."""
from __future__ import annotations

import numpy as np

FRACS = (0.25, 0.5, 0.75, 1.0); NS = (50, 100, 200, 400)
FEATS = ["len", "move_atr", "slope_atr_bar", "touches", "gap_mean_atr", "near_far_ratio", "atr_pts", "activity"]


def zone_rows(zones, c, h, l, e, atr, end_ns, volume, sd, hour_ct, minute_ct, tick, contract, inset, post=None):
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
        if post is not None: rows[-1].update(post_one(z, a, b, c, h, l, sd, post, [(zz["start"], zz["end"]) for zz in zones if zz.get("confirmed")]))
    return rows


def _window_stats(R, hb, d, b, N, bar_start, price, vol, h, l, sd, n):
    """Volumen (a nivel de tick) en las N barras siguientes a b, en la franja «más allá» (desde R en el sentido d) y en la franja «adentro» (hacia atrás), ambas de altura hb en ticks; y si el precio llegó a los bordes."""
    if b + N >= n or sd[b + N] != sd[b]: return None
    i0, i1 = bar_start[b + 1], bar_start[b + N + 1]; p = price[i0:i1]; v = vol[i0:i1]
    if d > 0: beyond = (p > R) & (p <= R + hb); inside = (p <= R) & (p > R - hb); rb = float(h[b + 1:b + N + 1].max() >= R + hb); ri = float(l[b + 1:b + N + 1].min() <= R - hb)
    else: beyond = (p < R) & (p >= R - hb); inside = (p >= R) & (p < R + hb); rb = float(l[b + 1:b + N + 1].min() <= R - hb); ri = float(h[b + 1:b + N + 1].max() >= R + hb)
    return [float(v[beyond].sum()), float(v[inside].sum()), rb, ri, float(v.sum())]


def post_one(z, a, b, c, h, l, sd, post, intervals):
    """Para una zona: estadísticas de volumen post-fin por (fracción, N) y el mismo cálculo en una barra al azar fuera de las zonas (control con la misma altura y dirección)."""
    n = len(c); H = float(h[a:b + 1].max() - l[a:b + 1].min()); d = int(z["dir"]); rng = post["rng"]; out = dict(H_ticks=H, post={}, ctrl={})
    r = None
    for _ in range(50):
        cand = int(rng.integers(300, n - max(NS) - 2))
        if all(not (s0 - 5 <= cand <= e0 + max(NS)) for s0, e0 in intervals): r = cand; break
    for f in FRACS:
        hb = f * H
        for N in NS:
            key = f"f{f}_N{N}"; w = _window_stats(float(c[b]), hb, d, b, N, post["bar_start"], post["price"], post["vol"], h, l, sd, n); out["post"][key] = w
            out["ctrl"][key] = None if r is None else _window_stats(float(c[r]), hb, d, r, N, post["bar_start"], post["price"], post["vol"], h, l, sd, n)
    return out


def summarize_post(rows):
    """Resumen: por (fracción, N) compara el volumen «más allá» vs «adentro» tras el fin de la zona, contra el control al azar. share = más_allá / (más_allá + adentro)."""
    res = {}
    def agg(items):
        it = [w for w in items if w is not None and (w[0] + w[1]) > 0]
        if not it: return None
        sh = np.array([w[0] / (w[0] + w[1]) for w in it]); return dict(n=len(it), share_beyond_mean=round(float(sh.mean()), 4), share_beyond_median=round(float(np.median(sh)), 4), frac_beyond_gt_inside=round(float((sh > 0.5).mean()), 4),
                                                                 p_reach_beyond=round(float(np.mean([w[2] for w in it])), 4), p_reach_inside=round(float(np.mean([w[3] for w in it])), 4), band_volume_share_of_window=round(float(np.mean([(w[0] + w[1]) / w[4] if w[4] > 0 else np.nan for w in it])), 4))
    for f in FRACS:
        for N in NS:
            k = f"f{f}_N{N}"; z = agg([r["post"][k] for r in rows if "post" in r]); c = agg([r["ctrl"][k] for r in rows if "ctrl" in r and r["ctrl"].get(k) is not None])
            pairs = [(r["session"], r["post"][k], r["ctrl"][k]) for r in rows if "post" in r and r["post"].get(k) is not None and r["ctrl"].get(k) is not None and (r["post"][k][0] + r["post"][k][1]) > 0 and (r["ctrl"][k][0] + r["ctrl"][k][1]) > 0]
            pd_ = None
            if len(pairs) >= 20:                                                       # diferencia apareada zona − control, error estándar agrupado por sesión (las zonas de una sesión no son independientes)
                bys = {}
                for ss, w, cw in pairs: bys.setdefault(ss, []).append(w[0] / (w[0] + w[1]) - cw[0] / (cw[0] + cw[1]))
                m_ = np.array([np.mean(v) for v in bys.values()]); allv = np.array([x for v in bys.values() for x in v]); pd_ = dict(n_pairs=len(pairs), n_sessions=len(bys), mean_diff=round(float(allv.mean()), 4), se_cluster_session=round(float(m_.std(ddof=1) / np.sqrt(len(m_))), 4) if len(m_) > 1 else None)
            res[k] = dict(zonas=z, control_azar=c, diferencia_share=None if not z or not c else round(z["share_beyond_mean"] - c["share_beyond_mean"], 4), diferencia_apareada=pd_)
    ctx = {}
    keyf = "f0.5_N200"
    def sub(name, mask):
        idx = [r for r, m in zip(rows, mask) if m]
        if len(idx) >= 20: ctx[name] = dict(zonas=agg([r["post"][keyf] for r in idx]), control_azar=agg([r["ctrl"][keyf] for r in idx if r["ctrl"].get(keyf) is not None]))
    slope = np.array([r["slope_atr_bar"] for r in rows]); lens = np.array([r["len"] for r in rows]); hrs = np.array([r["start_hour"] for r in rows]); dirs = np.array([r["dir"] for r in rows]); ses = sorted({r["session"] for r in rows}); first = np.array([r["session"] in set(ses[:len(ses) // 2]) for r in rows])
    t1, t2 = np.percentile(slope, [33.3, 66.7]); l1, l2 = np.percentile(lens, [33.3, 66.7])
    for name, mask in (("alcista", dirs > 0), ("bajista", dirs < 0), ("pendiente_baja", slope <= t1), ("pendiente_media", (slope > t1) & (slope <= t2)), ("pendiente_alta", slope > t2), ("largo_corto", lens <= l1), ("largo_medio", (lens > l1) & (lens <= l2)), ("largo_largo", lens > l2),
                       ("inicio_8_10_CT", (hrs >= 8) & (hrs <= 10)), ("inicio_otras_horas", (hrs < 8) | (hrs > 10)), ("primera_mitad", first), ("segunda_mitad", ~first)): sub(name, mask)
    return dict(definicion="franja = fraccion × altura de la zona (rango de precio); «más allá» desde el cierre del fin de zona en el sentido de la tendencia, «adentro» igual altura hacia atrás; volumen por tick en las N barras siguientes (misma sesión)", por_fraccion_y_N=res, por_contexto_f0_5_N200=ctx)


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
    out = dict(n_zones=len(rows), n_sessions=len({(r["contract"], r["session"]) for r in rows}));
    if rows and "post" in rows[0]: out["volumen_post_fin"] = summarize_post(rows)
    A = {f: np.array([r[f] for r in rows], float) for f in FEATS + ["move_pts", "minutes", "rth_frac", "bars_last_touch_to_end", "range_pos_start", "far_cv", "near_cv", "touch_per_100"]}
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


def post_break_rows(zones, c, h, l, atr, sd, bar_start, price, vol, seed=0, k_near=5, tol_atr=0.75, lookback=20, min_bar=300):
    """Corrección del sesgo de fin de zona: la referencia es la barra de RUPTURA (kb = fin + 1, lo único conocido en tiempo real) y el control se empareja por el contramovimiento previo
    (cierre anterior→ruptura y desplazamiento de `lookback` barras, en ATR) en el mismo sentido, en barras fuera de las zonas. `zones`: lista de dicts con dir, start_bar, end_bar, end_reason, H_ticks, session."""
    n = len(c); rng = np.random.default_rng(seed); Nmax = max(NS); atr = np.where(atr > 0, atr, np.nan)
    t = np.arange(n); cm1 = np.r_[c[0], c[:-1]]; cml = np.r_[np.full(lookback, c[0]), c[:-lookback]]
    X = {s: (s * (cm1 - c) / atr, s * (cml - c) / atr) for s in (1, -1)}
    blocked = np.zeros(n, bool)
    for z in zones: blocked[max(z["start_bar"] - 5, 0):min(z["end_bar"] + Nmax + 2, n)] = True
    ok = (~blocked) & (t >= min_bar) & (t < n - Nmax - 2) & np.isfinite(atr)
    rows = []
    for z in zones:
        if z["end_reason"] not in ("ruptura", "alejamiento"): continue
        b = int(z["end_bar"]) + 1; d = int(z["dir"])
        if b + Nmax + 2 >= n or b < lookback: continue
        x1, x20 = X[d][0][b], X[d][1][b]; H = float(z["H_ticks"]); out = dict(session=z["session"], end_reason=z["end_reason"], dir=d, start_bar=int(z["start_bar"]), end_bar=int(z["end_bar"]), len=int(z["len"]) if "len" in z else None,
                                                                                     slope_atr_bar=float(z.get("slope_atr_bar", np.nan)), start_hour=int(z.get("start_hour", -1)), x_counter_1bar_atr=float(x1), x_counter_20bar_atr=float(x20), post={}, ctrl={})
        dist = (X[d][0] - x1) ** 2 + (X[d][1] - x20) ** 2; dist = np.where(ok, dist, np.inf); idx = np.argpartition(dist, k_near)[:k_near]; idx = idx[np.isfinite(dist[idx])]
        r = int(rng.choice(idx)) if len(idx) and np.sqrt(dist[idx].min()) <= tol_atr else None; out["match_dist_atr"] = None if r is None else float(np.sqrt(dist[r]))
        for f in FRACS:
            hb = f * H
            for N in NS:
                key = f"f{f}_N{N}"; out["post"][key] = _window_stats(float(c[b]), hb, d, b, N, bar_start, price, vol, h, l, sd, n)
                out["ctrl"][key] = None if r is None else _window_stats(float(c[r]), hb, d, r, N, bar_start, price, vol, h, l, sd, n)
        rows.append(out)
    return rows
