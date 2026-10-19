#!/usr/bin/env python3
r"""IPC macro: la misma lógica sobre ES en velas de 500 ticks. Etapa A.

Manifiesto: docs/research/MANIFIESTO_IPC_MACRO_ES_500T_20260926.md (OK de Nico 26/09).
Velas: 20 velas de 25t de la caché canónica (tools/tbzx_iter2.py, bars/*.npz) agrupadas por sesión = 500t exactas.

    .venv\Scripts\python tools\ipc_macro.py measure
    .venv\Scripts\python tools\ipc_macro.py report
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
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

OUT = REPO / "artifacts" / "ipc_macro"
DOC = "docs/research/MANIFIESTO_IPC_MACRO_ES_500T_20260926.md"
LEDGER = I.LEDGER
MULT = 20
PARS = dict(w=2, max_gap=30, max_step=6, min_pull=6, nmin=5)       # congelado (validación con juicios de Nico)
CAP = 0.45                                                          # t/vela, elegido en las dos mitades de enero
VARIANTS = {"estandar": dict(minp=5), "estricto": dict(minp=6)}
KS = (2, 4)
PIV_LOOK = 100                                                      # C-SW: pivotes de las últimas 100 velas de 500t
SEED = 20260930


def load500():
    S = T2.load("ES")
    out = {}
    for k, x in S.items():
        N = len(x["t"]); n = N // MULT * MULT; rem = N - n

        def agg(a, f):
            parts = [f(a[:n].reshape(-1, MULT), axis=1)] if n else []
            if rem:
                parts.append(np.array([f(a[n:])]))
            return np.concatenate(parts)

        def last(a):
            parts = [a[MULT - 1:n:MULT]] if n else []
            if rem:
                parts.append(a[-1:])
            return np.concatenate(parts)
        out[k] = dict(t=last(x["t"]), h=agg(x["h"], np.max).astype(np.int64), l=agg(x["l"], np.min).astype(np.int64),
                      c=last(x["c"]).astype(np.int64), v=agg(x["v"], np.sum).astype(np.float64), clock=last(x["clock"]).astype(np.int64))
    return out


def events(a, Z, variant):
    """E1 alejamiento (con edad desde la creación) y E2 regreso a zona virgen. Causal, como tools/ipc.py."""
    h, l, c = a["h"], a["l"], a["c"]; n = len(c); w = PARS["w"]
    rows = []
    for z in Z:
        pk = z["picos"]
        if len(pk) < variant["minp"]:
            continue
        pk0 = pk[:variant["minp"]]                                    # sólo picos conocidos en la creación
        if abs(pk0[-1][2] - pk0[0][2]) / max(pk0[-1][0] - pk0[0][0], 1) > CAP:
            continue
        H = z["kind"] == "H"; s = 1 if H else -1
        idx = [p[0] for p in pk]; pr = [p[2] for p in pk]
        creation = idx[variant["minp"] - 1] + w
        if creation >= n - 2:
            continue
        for k in KS:
            m = variant["minp"]; touched = False; ev = -1; m_R = -1; R = 1.0; rg = -1
            ev_last = ev_D = ev_R = None
            for j in range(creation, n):
                if ev < 0:
                    while m < len(idx) and idx[m] + w <= j:
                        m += 1
                    lastp = pr[m - 1]
                    if s * ((h[j] if H else l[j]) - lastp) > 0:
                        break                                         # se rompe la serie
                    if m != m_R:
                        pulls = []
                        for u in range(1, m):
                            seg = (l if H else h)[idx[u - 1]:idx[u] + 1]
                            pulls.append(s * (pr[u - 1] - (seg.min() if H else seg.max())))
                        R = max(float(np.mean(pulls)) if pulls else 1.0, 1.0); m_R = m
                    D = k * R
                    if (h[j] if H else l[j]) == lastp and j > idx[m - 1]:
                        touched = True
                    if s * (lastp - c[j]) >= D:
                        ev = j; ev_last, ev_D, ev_R = lastp, D, R
                        if touched:
                            break                                     # no virgen: no hay E2
                else:                                                 # E2: nivel y D fijos del alejamiento
                    if (s > 0 and h[j] >= ev_last) or (s < 0 and l[j] <= ev_last):
                        break                                         # tocó antes de volver a D/2
                    if s * (ev_last - c[j]) <= ev_D / 2:
                        rg = j; break
            if ev < 0:
                continue
            far = ev_last - s * 2 * ev_D
            hit, nb = I.race(h, l, ev, s, ev_last, far, n)
            rows.append(dict(evento="alejamiento", kind=z["kind"], k=k, virgen=int(not touched), edad=ev - creation, ev=ev, D=ev_D, R=ev_R,
                             hit=hit, bars=nb, lvl_dist=abs(ev_last - c[ev]), far_dist=abs(c[ev] - far)))
            if rg > 0:
                far2 = ev_last - s * ev_D
                hit2, nb2 = I.race(h, l, rg, s, ev_last, far2, n)
                rows.append(dict(evento="regreso", kind=z["kind"], k=k, virgen=1, edad=rg - creation, ev=rg, D=ev_D, R=ev_R,
                                 hit=hit2, bars=nb2, lvl_dist=abs(ev_last - c[rg]), far_dist=abs(c[rg] - far2)))
    return rows


def control_sw(S, A, keys, k, e, s, lvl_dist, far_dist, rng, zone_levels, R, piv):
    """C-SW de tools/ipc.py con la ventana de pivotes de 500t (PIV_LOOK velas)."""
    a = A[k]; s0 = a["st"][:, e]; rg0, sec0 = a["rg20"][e], a["sec20"][e]; clock = int(S[k]["clock"][e])
    others = [o for o in keys if o != k]; vals = []
    for oi in rng.permutation(len(others)):
        if len(vals) >= I.N_PH:
            break
        o = others[int(oi)]; y = A[o]
        lo_, hi_ = np.searchsorted(S[o]["clock"], clock - I.TOD), np.searchsorted(S[o]["clock"], clock + I.TOD)
        lo_ = max(lo_, PIV_LOOK)
        if hi_ <= lo_:
            continue
        tol = np.maximum(I.TOL * np.abs(s0)[:, None], I.ABS_TOL)
        ok = np.all(np.abs(y["st"][:, lo_:hi_] - s0[:, None]) <= tol, axis=0)
        rg, sec = y["rg20"][lo_:hi_], y["sec20"][lo_:hi_]
        ok &= (np.abs(rg - rg0) <= I.TOL * rg0) & (np.abs(np.log(np.maximum(sec, 1e-3) / max(sec0, 1e-3))) <= np.log(1 + I.TOL))
        src = y["h"] if s > 0 else y["l"]
        for qi in rng.permutation(np.flatnonzero(ok))[:15]:
            q = lo_ + int(qi)
            target = y["c"][q] + s * lvl_dist
            pv = piv[o][s]
            cand = [u for u in pv[(pv >= q - PIV_LOOK) & (pv < q - 2)] if abs(src[u] - target) <= R]
            cand = [u for u in cand if s * (src[u + 1:q + 1].max() if s > 0 else src[u + 1:q + 1].min()) <= s * src[u]]
            cand = [u for u in cand if not any(abs(src[u] - zl) < R for zl in zone_levels.get(o, []))]
            if not cand:
                continue
            u = cand[-1]; far = y["c"][q] - s * far_dist
            hit, _ = I.race(y["h"], y["l"], q, s, src[u], far, len(y["c"]))
            vals.append(hit); break
    return (float(np.mean(vals)) if vals else np.nan, len(vals))


def step_measure():
    S = load500()
    keys = [k for k in sorted(S) if k <= TB.EXP_END]
    part = "P-IPC-ES500-EXP"
    from edgelab.edge_brain.episode_logger import measurement_episode
    from edgelab.edge_brain.hippocampus_store import DurableHippocampus
    if not (LEDGER.exists() and part in DurableHippocampus(LEDGER).partitions):
        with measurement_episode(LEDGER, "EP-IPC-PARTICION-ES500", goal="declarar partición IPC macro ES 500t", recorded_by="tools/ipc_macro.py measure",
                                 repo=REPO, prereg_ref=DOC) as ep:
            ep.store.record_partition(part, "EXPLORATION", "ES 500T (20x25T) exploración (<= 2026-03-31), contrato canónico", [f"ES500:{k}" for k in keys])
    A = {k: I.arrays(S[k]) for k in keys}
    Zs = {k: PR.series(dict(t=S[k]["t"], h=A[k]["h"], l=A[k]["l"]), 1.0, *PARS.values(), extend_back=True, max_slope=None) for k in keys}
    zone_levels = {k: [z["picos"][-1][2] for z in Zs[k]] for k in keys}
    piv = {k: {1: np.flatnonzero(PR.pivots(A[k]["h"], 2)), -1: np.flatnonzero(PR.pivots(-A[k]["l"], 2))} for k in keys}
    rng = np.random.default_rng(SEED)
    rows = []
    for vname, var in VARIANTS.items():
        for k in keys:
            for r in events(A[k], Zs[k], var):
                s = 1 if r["kind"] == "H" else -1
                cm, cn, pht, phs = I.control(S, A, keys, k, r["ev"], s, r["lvl_dist"], r["far_dist"], rng, zone_levels, r["R"])
                sw, swn = control_sw(S, A, keys, k, r["ev"], s, r["lvl_dist"], r["far_dist"], rng, zone_levels, r["R"], piv)
                rows.append(dict(r, detector=vname, session=k, ctrl=cm, n_ctrl=cn, ctrl_sw=sw, n_sw=swn, ph_t=pht, ph_session=phs,
                                 t_ev=float(S[k]["t"][r["ev"]])))
        print(vname, "eventos", sum(1 for r in rows if r["detector"] == vname), flush=True)
    D = pd.DataFrame(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    D.to_parquet(OUT / "A_ES500.parquet", index=False)
    print("filas", len(D), "sesiones", len(keys), "zonas", sum(len(z) for z in Zs.values()),
          "cobertura C-SZ", round(float((D.n_ctrl > 0).mean()), 3), "C-SW", round(float((D.n_sw > 0).mean()), 3))


def step_report():
    rng = np.random.default_rng(SEED)
    D = pd.read_parquet(OUT / "A_ES500.parquet")
    med_age, cells = {}, []
    for det in VARIANTS:
        for k in KS:
            ga = D[(D.detector == det) & (D.k == k) & (D.evento == "alejamiento")]
            med_age[f"{det}|k{k}"] = float(ga.edad.median()) if len(ga) else None   # sólo edades: sin mirar resultados
            specs = [("alejamiento", v, mo) for v in (1, 0) for mo in ("todos", "temprano", "tardio")] + [("regreso", 1, "todos")]
            for evn, virg, mo in specs:
                g = D[(D.detector == det) & (D.k == k) & (D.evento == evn) & (D.virgen == virg)]
                if mo == "temprano":
                    g = g[g.edad <= med_age[f"{det}|k{k}"]]
                elif mo == "tardio":
                    g = g[g.edad > med_age[f"{det}|k{k}"]]
                g_sw = g.dropna(subset=["ctrl_sw"]); g = g.dropna(subset=["ctrl"])
                base = dict(evento=evn, detector=det, k=k, virgen=virg, momento=mo, n=int(len(g)),
                            D_med_ticks=float(g.D.median()) if len(g) else None)
                if len(g) < 50:
                    cells.append(dict(base, status="POCOS")); continue
                d, lo, hi, mde, pv = EV.boot(g.hit.to_numpy(float), g.ctrl.to_numpy(), g.session.to_numpy(), rng)
                h1 = (pd.to_datetime(g.session, format="%Y%m%d") < pd.Timestamp("2025-12-01")).to_numpy()
                halves = [float((g.hit - g.ctrl)[m].mean()) if m.sum() >= 20 else None for m in (h1, ~h1)]
                sw = None
                if len(g_sw) >= 50:
                    d2, lo2, hi2, _, pv2 = EV.boot(g_sw.hit.to_numpy(float), g_sw.ctrl_sw.to_numpy(), g_sw.session.to_numpy(), rng)
                    sw = dict(n=int(len(g_sw)), real=float(g_sw.hit.mean()), control=float(g_sw.ctrl_sw.mean()), diff=d2, ci=[lo2, hi2], pval=pv2)
                cells.append(dict(base, status="OK", sessions=int(g.session.nunique()), real=float(g.hit.mean()), control=float(g.ctrl.mean()),
                                  diff=d, ci=[lo, hi], mde=mde, pval=pv, halves=halves, c_sw=sw))
    ok = [c for c in cells if c["status"] == "OK"]
    for c, f in zip(ok, T2.TX._bh([c["pval"] for c in ok])):
        c["fdr"] = bool(f)
    for c in cells:
        if c["status"] != "OK":
            c["estado"] = "SIN_POTENCIA"
        elif c["fdr"]:
            c["estado"] = "INFO+" if c["diff"] > 0 else "INFO-"
        else:
            c["estado"] = "SIN_INFO" if c["mde"] <= 0.10 else "SIN_POTENCIA"
        c["pasa_B"] = bool(c["estado"] == "INFO+" and all(v is not None and v > 0 for v in c["halves"])
                           and c.get("c_sw") and c["c_sw"]["ci"][0] > 0)
    from collections import Counter
    from edgelab.edge_brain.control_guard import audit_event_controls
    X = D.dropna(subset=["ph_t"])
    audit = audit_event_controls((X.t_ev * 1e6).astype(np.int64).to_numpy(), (X.ph_t * 1e6).astype(np.int64).to_numpy(), 2000 * 60.0,
                                 same_session=(X.session == X.ph_session).to_numpy())
    body = dict(schema="EDGELAB_IPC_MACRO_A_V1", doc=DOC, code_commit=TB._git("rev-parse", "HEAD"),
                tree_dirty=bool(TB._git("status", "--porcelain", "--", "tools", "edgelab")), mediana_edad=med_age,
                estados=dict(Counter(c["estado"] for c in cells)), familia=len(ok), pasan_B=[c for c in cells if c["pasa_B"]],
                celdas=cells, control_audit=audit)
    raw = json.dumps(body, indent=1, default=float, ensure_ascii=False)
    (OUT / "reportA.json").write_text(raw, encoding="utf-8")
    sha = hashlib.sha256(raw.encode()).hexdigest()
    from edgelab.edge_brain.episode_logger import measurement_episode
    with measurement_episode(LEDGER, f"EP-IPC-MACRO-A-{sha[:8]}", goal="IPC macro ES 500t etapa A", recorded_by="tools/ipc_macro.py report",
                             repo=REPO, prereg_ref=DOC) as ep:
        ep.store.record_observation(f"OBS-IPC-MACRO-A-{sha[:8]}", "IPC macro ES 500t etapa A (alcance por celda)", "RESPONSE_PROFILE",
                                    ["P-IPC-ES500-EXP"],
                                    {f"{c['evento']}|{c['detector']}|k{c['k']}|v{c['virgen']}|{c['momento']}": (c.get("diff"), c["estado"]) for c in cells},
                                    {"mult": MULT}, sha, design="EVENT_VS_CONTROL", control_audit=audit)
    print(json.dumps(dict(sha=sha[:12], estados=body["estados"], familia=len(ok), pasan_B=len(body["pasan_B"]), audit=audit["status"])))


def main(argv=None):
    ap = argparse.ArgumentParser(); ap.add_argument("step", choices=["measure", "report"])
    a = ap.parse_args(argv)
    step_measure() if a.step == "measure" else step_report()


if __name__ == "__main__":
    main()
