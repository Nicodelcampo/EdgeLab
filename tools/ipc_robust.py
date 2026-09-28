#!/usr/bin/env python3
r"""IPC-ROB: prueba de robustez del positivo de la etapa A 25t. Manifiesto: docs/research/MANIFIESTO_IPC_ROBUSTEZ_20260928.md.

Sólo descubrimiento (≤ 2026-03-31). Pasos:
    .venv\Scripts\python tools\ipc_robust.py mid --inst ES     # velas de 25t con midquote, alineadas con la caché de trades
    .venv\Scripts\python tools\ipc_robust.py measure --inst ES
    .venv\Scripts\python tools\ipc_robust.py report
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "tools"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import evx as EV  # noqa: E402
import ipc as I  # noqa: E402
import peaks_rule as PR  # noqa: E402
import tbz_e2 as TB  # noqa: E402
import tbzx_iter2 as T2  # noqa: E402

OUT = REPO / "artifacts" / "ipc_rob"
DOC = "docs/research/MANIFIESTO_IPC_ROBUSTEZ_20260928.md"
SEED = 20260928
EXCL_SESSION = "20251215"                      # entrada 049: contrato dependiente de la regla de roll


# ------------------------------------------------------------------ velas con midquote
def mid_dir(inst):
    return OUT / "mid" / inst


def _mid_session(args):
    inst, s = args
    from edgelab.bridge.ticks import load_canonical_parquet
    f = mid_dir(inst) / f"{s['trade_date']}.npz"
    bf = T2.bars_dir(inst) / f"{s['trade_date']}.npz"
    if f.exists():
        return s["trade_date"], "EXISTE", None
    if not bf.exists():
        return s["trade_date"], "SIN_VELAS", None
    z = np.load(bf)
    tk = load_canonical_parquet(s["path"], contract=s["contract"], start_utc_ns=s["start"], end_utc_ns=s["end"])
    px = tk.price_ticks.astype(np.int64)
    bid = tk.bid_ticks.astype(np.float64); ask = tk.ask_ticks.astype(np.float64)
    bad = ~((bid > 0) & (ask > 0) & (ask >= bid))
    mid = np.where(bad, np.nan, (bid + ask) / 2.0)
    mid = pd.Series(mid).ffill().bfill().to_numpy()
    n = len(px); nb = (n + 24) // 25
    if nb != len(z["c"]):
        return s["trade_date"], f"DESALINEADO {nb} vs {len(z['c'])}", None
    idx = np.minimum(np.arange(nb) * 25 + 24, n - 1)
    if not np.array_equal(px[idx], z["c"].astype(np.int64)):
        return s["trade_date"], "CIERRES_DISTINTOS", None
    pad = nb * 25 - n
    m2 = np.r_[mid, np.full(pad, mid[-1])].reshape(nb, 25)
    mid_dir(inst).mkdir(parents=True, exist_ok=True)
    np.savez(f, h=m2.max(1).astype(np.float32), l=m2.min(1).astype(np.float32), c=m2[:, -1].astype(np.float32))
    return s["trade_date"], "OK", float(bad.mean())


def step_mid(inst, workers):
    ss = [s for s in T2.canonical_sessions(inst) if s["trade_date"] <= TB.EXP_END]
    rep = {}
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for fu in as_completed([ex.submit(_mid_session, (inst, s)) for s in ss]):
            d, st, badf = fu.result(); rep[d] = dict(estado=st, cotizaciones_invalidas=badf)
            print(d, st, flush=True)
    (OUT / f"mid_{inst}_reporte.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")


# ------------------------------------------------------------------ eventos (etapa A, con creación y volumen causal)
def events(a, Z, variant, w, cap):
    rows = []
    h, l, c, v = a["h"], a["l"], a["c"], a["v"]; n = len(c)
    for z in Z:
        pk = z["picos"]
        if len(pk) < variant["minp"]:
            continue
        pk0 = pk[:variant["minp"]]
        if pk0[-1][0] - pk0[0][0] < variant["minbars"]:
            continue
        if cap is not None and abs(pk0[-1][2] - pk0[0][2]) / max(pk0[-1][0] - pk0[0][0], 1) > cap:
            continue
        H = z["kind"] == "H"; s = 1 if H else -1
        idx = [p[0] for p in pk]; pr = [p[2] for p in pk]
        creation = idx[variant["minp"] - 1] + w
        if creation >= n - 2:
            continue
        if variant.get("rel_vol"):                     # D4: comercio entre picos (causal, como en la tanda de Nico)
            a0, b0 = idx[0], idx[variant["minp"] - 1]
            ref = np.median(v[:a0 + 1]) if a0 > 0 else np.nan
            if not (np.isfinite(ref) and ref > 0 and v[a0:b0 + 1].mean() >= variant["rel_vol"] * ref):
                continue
        for k in I.KS:
            m = variant["minp"]; touched = False; broken = False; ev = -1; m_R = -1; R = 1.0
            for j in range(creation, min(n - 1, creation + I.HMAX)):
                while m < len(idx) and idx[m] + w <= j:
                    m += 1
                last = pr[m - 1]
                if s * ((h[j] if H else l[j]) - last) > 0:
                    broken = True; break
                if m != m_R:
                    pulls = []
                    for u in range(1, m):
                        seg = (l if H else h)[idx[u - 1]:idx[u] + 1]
                        pulls.append(s * (pr[u - 1] - (seg.min() if H else seg.max())))
                    R = max(float(np.mean(pulls)) if pulls else 1.0, 1.0); m_R = m
                D = k * R
                if (h[j] if H else l[j]) == last and j > idx[m - 1]:
                    touched = True
                if s * (last - c[j]) >= D:
                    ev = j; break
            if broken or ev < 0:
                continue
            base = np.median(v[:creation]) if creation > 50 else np.nan          # auditoría 046 §3: volumen causal
            vol_rel = float(v[creation:ev + 1].mean() / base) if np.isfinite(base) and base > 0 else np.nan
            for lvl_name, lvl in (("ultimo", last), ("primero", pr[0])):
                far = last - s * 2 * D
                rows.append(dict(kind=z["kind"], k=k, nivel=lvl_name, virgen=int(not touched), vol_rel=vol_rel, ev=ev, D=D, R=R,
                                 creation=creation, edad=ev - idx[0], restantes=n - ev, lvl=float(lvl), far=float(far),
                                 lvl_dist=abs(lvl - c[ev]), far_dist=abs(c[ev] - far), s=s))
    return rows


def race(h, l, e, s, lvl, far, n):
    """Como ipc.race, pero marca velas ambiguas (tocan nivel y barrera a la vez) y devuelve también el desempate a 1."""
    end = min(n - 1, e + I.HMAX)
    for q in range(e + 1, end + 1):
        fail = (s > 0 and l[q] <= far) or (s < 0 and h[q] >= far)
        win = (s > 0 and h[q] >= lvl) or (s < 0 and l[q] <= lvl)
        if fail and win:
            return 0, 1, True
        if fail:
            return 0, 0, False
        if win:
            return 1, 1, False
    return 0, 0, False


def zone_index(Zs, variant, w):
    """Niveles as-of: para cada zona, (creación, [(índice de confirmación, precio)] de sus picos)."""
    out = []
    for z in Zs:
        pk = z["picos"]
        if len(pk) < variant["minp"]:
            continue
        out.append((pk[variant["minp"] - 1][0] + w, [(p[0] + w, p[2]) for p in pk]))
    return out


def near_zone_asof(zidx, q, price, R):
    for cr, pks in zidx:
        if cr > q:
            continue
        for ci, p in pks:
            if ci <= q and abs(price - p) < R:
                return True
    return False


def controls(S, A, M, keys, k, r, rng, zidx, piv):
    """C-SZ (as-of), C-SW actual (± R, as-of) y C-SW emparejado (distancia ± max(1 t, 10 %), edad 0,5–2×, exposición ≥ 0,8), en trade y mid."""
    a = A[k]; e = r["ev"]; s = r["s"]; s0 = a["st"][:, e]; rg0, sec0 = a["rg20"][e], a["sec20"][e]; clock = int(S[k]["clock"][e])
    others = [o for o in keys if o != k]
    res = {n_: [] for n_ in ("sz_t", "sz_m", "swa_t", "swa_m", "swm_t", "swm_m")}
    donors = {n_: [] for n_ in ("sz", "swa", "swm")}
    tol_d = max(1.0, 0.1 * r["lvl_dist"])
    for oi in rng.permutation(len(others)):
        if all(len(res[x]) >= I.N_PH for x in ("sz_t", "swa_t", "swm_t")):
            break
        o = others[int(oi)]; y = A[o]; my = M.get(o)
        lo_, hi_ = np.searchsorted(S[o]["clock"], clock - I.TOD), np.searchsorted(S[o]["clock"], clock + I.TOD)
        lo_ = max(lo_, 300)
        if hi_ <= lo_:
            continue
        tol = np.maximum(I.TOL * np.abs(s0)[:, None], I.ABS_TOL)
        ok = np.all(np.abs(y["st"][:, lo_:hi_] - s0[:, None]) <= tol, axis=0)
        rg, sec = y["rg20"][lo_:hi_], y["sec20"][lo_:hi_]
        ok &= (np.abs(rg - rg0) <= I.TOL * rg0) & (np.abs(np.log(np.maximum(sec, 1e-3) / max(sec0, 1e-3))) <= np.log(1 + I.TOL))
        ny = len(y["c"]); src = y["h"] if s > 0 else y["l"]
        for qi in rng.permutation(np.flatnonzero(ok))[:15]:
            q = lo_ + int(qi)
            target = y["c"][q] + s * r["lvl_dist"]; far = y["c"][q] - s * r["far_dist"]
            if len(res["sz_t"]) < I.N_PH and not near_zone_asof(zidx[o], q, target, r["R"]):
                res["sz_t"].append(race(y["h"], y["l"], q, s, target, far, ny)[0])
                if my is not None:
                    res["sz_m"].append(race(my["h"], my["l"], q, s, target, far, ny)[0])
                donors["sz"].append(o)
            pv = piv[o][s]; cand = pv[(pv >= q - 300) & (pv < q - 2)]
            cand = [u for u in cand if s * (src[u + 1:q + 1].max() if s > 0 else src[u + 1:q + 1].min()) <= s * src[u]
                    and not near_zone_asof(zidx[o], q, src[u], r["R"])]
            if len(res["swa_t"]) < I.N_PH:
                ca = [u for u in cand if abs(src[u] - target) <= r["R"]]
                if ca:
                    u = ca[-1]; res["swa_t"].append(race(y["h"], y["l"], q, s, src[u], far, ny)[0])
                    if my is not None:
                        res["swa_m"].append(race(my["h"], my["l"], q, s, src[u], far, ny)[0])
                    donors["swa"].append(o)
            if len(res["swm_t"]) < I.N_PH and (ny - q) >= 0.8 * r["restantes"]:
                cm = [u for u in cand if abs(src[u] - target) <= tol_d and 0.5 * r["edad"] <= (q - u) <= 2.0 * r["edad"]]
                if cm:
                    u = cm[-1]; res["swm_t"].append(race(y["h"], y["l"], q, s, src[u], far, ny)[0])
                    if my is not None:
                        res["swm_m"].append(race(my["h"], my["l"], q, s, src[u], far, ny)[0])
                    donors["swm"].append(o)
    out = {k_: (float(np.mean(v_)) if v_ else np.nan) for k_, v_ in res.items()}
    out.update({f"don_{k_}": ",".join(v_) for k_, v_ in donors.items()})
    return out


VARIANTS = {"ES": {"estandar": dict(minp=8, minbars=0), "estricto": dict(minp=12, minbars=0),
                   "D4_comercio": dict(minp=8, minbars=0, rel_vol=1.2)},
            "NQ": {"estandar": dict(minp=7, minbars=40), "estricto": dict(minp=10, minbars=40)}}


def step_measure(inst):
    S = T2.load(inst)
    keys = [k for k in sorted(S) if k <= TB.EXP_END]
    S = {k: S[k] for k in keys}
    A = {k: I.arrays(S[k]) for k in keys}
    for k in keys:
        A[k]["v"] = S[k]["v"].astype(float)
    M = {}
    for k in keys:
        f = mid_dir(inst) / f"{k}.npz"
        if f.exists():
            z = np.load(f); M[k] = dict(h=z["h"].astype(float), l=z["l"].astype(float))
    cfg = I.DET[inst]; cap = I.cap_of(inst); p = cfg["pars"]
    Zs = {k: PR.series(dict(t=S[k]["t"], h=A[k]["h"], l=A[k]["l"]), 1.0, p["w"], p["max_gap"], p["max_step"], p["min_pull"], p["nmin"],
                       extend_back=True, max_slope=None) for k in keys}
    piv = {k: {1: np.flatnonzero(PR.pivots(A[k]["h"], 2)), -1: np.flatnonzero(PR.pivots(-A[k]["l"], 2))} for k in keys}
    rng = np.random.default_rng(SEED)
    rows = []
    for vname, var in VARIANTS[inst].items():
        zidx = {k: zone_index(Zs[k], dict(minp=p["nmin"]), p["w"]) for k in keys}      # toda zona detectada, as-of
        for k in keys:
            for r in events(A[k], Zs[k], var, p["w"], cap):
                if r["nivel"] == "primero" and vname == "D4_comercio":
                    pass
                h, l, n = A[k]["h"], A[k]["l"], len(A[k]["c"])
                ht, _, amb_t = race(h, l, r["ev"], r["s"], r["lvl"], r["far"], n)
                hm = amb_m = None
                if k in M:
                    hm, _, amb_m = race(M[k]["h"], M[k]["l"], r["ev"], r["s"], r["lvl"], r["far"], n)
                _, ht1, _ = race(h, l, r["ev"], r["s"], r["lvl"], r["far"], n)
                cc = controls(S, A, M, keys, k, r, rng, zidx, piv)
                rows.append(dict(r, inst=inst, detector=vname, session=k, hit_t=ht, hit_t_amb1=ht1, amb_t=amb_t,
                                 hit_m=hm, amb_m=amb_m, **cc))
        print(inst, vname, "eventos", sum(1 for x in rows if x["detector"] == vname), flush=True)
    D = pd.DataFrame(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    D.to_parquet(OUT / f"R_{inst}.parquet", index=False)
    print(inst, "filas", len(D), "cobertura swm", round(float(D.swm_t.notna().mean()), 3), "mid", round(float(D.hit_m.notna().mean()), 3))


def _cell(D, c, t1, t2):
    g = D[(D.detector == c["detector"]) & (D.virgen == c["virgen"]) & (D.k == c["k"]) & (D.nivel == c["nivel"])]
    return g[g.vol_rel <= t1] if c["volumen"] == "bajo" else (g[g.vol_rel >= t2] if c["volumen"] == "alto" else g)


def step_report():
    rng = np.random.default_rng(SEED)
    src = json.loads((I.OUT / "reportA.json").read_text(encoding="utf-8"))
    cells = [dict(c, origen="etapaA") for c in src["pasan_B"]]
    for c in [c for c in src["pasan_B"] if c["inst"] == "ES" and c["detector"] == "estandar" and c["volumen"] == "todos"]:
        cells.append(dict(c, detector="D4_comercio", origen="D4"))
    data = {i: pd.read_parquet(OUT / f"R_{i}.parquet") for i in ("ES", "NQ") if (OUT / f"R_{i}.parquet").exists()}
    CONTR = {"A": ("hit_t", "sz_t"), "B": ("hit_t", "swa_t"), "C": ("hit_t", "swm_t"), "D": ("hit_m", "swm_m"), "E": ("hit_m", "sz_m")}
    out = []
    for c in cells:
        D = data[c["inst"]]; g0 = D[D.detector == c["detector"]]
        t1, t2 = g0.vol_rel.quantile([1 / 3, 2 / 3])
        g = _cell(D, c, t1, t2)
        row = dict({k: c[k] for k in ("inst", "detector", "virgen", "k", "volumen", "nivel", "origen")}, n_eventos=int(len(g)),
                   amb_t=float(g.amb_t.mean()) if len(g) else None)
        for code, (rc, cc) in CONTR.items():
            for tag, gg in (("", g), ("_sin1215", g[g.session != EXCL_SESSION])):
                h = gg.dropna(subset=[rc, cc])
                if len(h) < 30:
                    row[code + tag] = dict(n=int(len(h))); continue
                d, lo, hi, mde, p2 = EV.boot(h[rc].to_numpy(float), h[cc].to_numpy(float), h.session.to_numpy(), rng)
                cell = dict(n=int(len(h)), real=float(h[rc].mean()), control=float(h[cc].mean()), diff=d, ci=[lo, hi], mde=mde,
                            p1=(p2 / 2 if d > 0 else 1 - p2 / 2))
                if code == "D" and not tag:
                    months = pd.to_datetime(h.session, format="%Y%m%d").dt.strftime("%Y-%m")
                    lomo = [float((h[rc] - h[cc])[months != m].mean()) for m in months.unique()]
                    cell.update(lomo_min=min(lomo), lomo_max=max(lomo),
                                donantes_distintos=int(len(set(",".join(h.don_swm).split(",")) - {""})),
                                reuso_max=int(pd.Series(",".join(h.don_swm).split(",")).value_counts().max()))
                    hd = h.assign(hit_t=h.hit_t_amb1)
                row[code + tag] = cell
        out.append(row)
    ps = [r["D"].get("p1", 1.0) if isinstance(r.get("D"), dict) else 1.0 for r in out]
    for r, f in zip(out, T2.TX._bh(ps)):
        r["sostiene"] = bool(f and r["D"].get("ci", [0, 0])[0] > 0)
    n_orig = sum(r["sostiene"] for r in out if r["origen"] == "etapaA")
    ver = "ROBUSTO" if n_orig >= 12 else "NO_ROBUSTO"
    body = dict(schema="EDGELAB_IPC_ROB_V1", doc=DOC, code_commit=TB._git("rev-parse", "HEAD"),
                tree_dirty=bool(TB._git("status", "--porcelain", "--", "tools", "edgelab")), sostienen_originales=n_orig,
                veredicto=ver, celdas=out)
    raw = json.dumps(body, indent=1, default=float, ensure_ascii=False)
    (OUT / "reporte.json").write_text(raw, encoding="utf-8")
    sha = hashlib.sha256(raw.encode()).hexdigest()
    print(json.dumps(dict(sha=sha[:12], sostienen_originales=n_orig, de=23, veredicto=ver)))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["mid", "measure", "report"])
    ap.add_argument("--inst", default="ES"); ap.add_argument("--workers", type=int, default=2)
    a = ap.parse_args(argv)
    {"mid": lambda: step_mid(a.inst, a.workers), "measure": lambda: step_measure(a.inst), "report": step_report}[a.step]()


if __name__ == "__main__":
    main()
