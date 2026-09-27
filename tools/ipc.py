#!/usr/bin/env python3
r"""IPC: ¿las acumulaciones de picos consecutivos son imanes? Etapa A (información), ES y NQ, exploración.

Manifiesto: docs/research/MANIFIESTO_IPC_IMAN_20260926.md (aprobado por Nico el 26/09).

    .venv\Scripts\python tools\ipc.py measure --inst ES
    .venv\Scripts\python tools\ipc.py measure --inst NQ
    .venv\Scripts\python tools\ipc.py report
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
import peaks_rule as PR  # noqa: E402
import tbz_e2 as TB  # noqa: E402
import tbzx_iter2 as T2  # noqa: E402

OUT = REPO / "artifacts" / "ipc"
DOC = "docs/research/MANIFIESTO_IPC_IMAN_20260926.md"
LEDGER = REPO / "artifacts" / "hippocampus" / "ipc_20260926.jsonl"
DET = {  # congelado en el manifiesto §1 y §4
    "ES": dict(pars=dict(w=2, max_gap=60, max_step=2, min_pull=2, nmin=6), src="ES_03-26_202601_25T_HFT",
               variants={"estandar": dict(minp=8, minbars=0), "estricto": dict(minp=12, minbars=0)}),
    "NQ": dict(pars=dict(w=1, max_gap=30, max_step=14, min_pull=7, nmin=5), src="NQ_03-26_202601_25T_HFT",
               variants={"estandar": dict(minp=7, minbars=40), "estricto": dict(minp=10, minbars=40)}),
}
KS = (2, 4, 8)
HMAX = 2000
N_PH, TOD, TOL, ABS_TOL = 3, 3600, 0.5, 0.15
SEED = 20260929


def cap_of(inst):
    d = json.loads((PR.VIEW / "bundles" / "peaks_det" / f"{DET[inst]['src']}.json").read_text(encoding="utf-8"))
    return d.get("tope_pendiente_p90") or d.get("tope_pendiente")


def arrays(x):
    a = EV.session_arrays(x)
    a["h"], a["l"] = x["h"].astype(float), x["l"].astype(float)
    e21 = EV.ema(a["c"], 21)
    a["st"] = np.vstack([(a["c"] - a["vw"]) / a["atr"], np.r_[np.full(5, np.nan), e21[5:] - e21[:-5]] / a["atr"]])
    a["vavg"] = float(np.mean(np.maximum(x["v"], 0))) or 1.0
    return a


def events(x, a, Z, variant, w, tick=1.0, cap=None):
    """Eventos causales por zona: se recorre vela a vela desde la creación; el último pico vigente es el último pico ya
    confirmado (índice + w). Evento = primer cierre a ≥ D del último pico, del lado contrario, con la zona sin romper."""
    h, l, c, v = a["h"], a["l"], a["c"], x["v"].astype(float)
    n = len(c)
    rows = []
    for z in Z:
        pk = z["picos"]
        if len(pk) < variant["minp"]:
            continue
        # CAUSAL (corrección 26/09): filtros de pendiente y duración con los picos conocidos en la creación, no con la serie
        # completa (incluía picos posteriores al evento: si el precio volvía, cambiaba qué zonas pasaban)
        pk0 = pk[:variant["minp"]]
        if pk0[-1][0] - pk0[0][0] < variant["minbars"]:
            continue
        if cap is not None and abs(pk0[-1][2] - pk0[0][2]) / tick / max(pk0[-1][0] - pk0[0][0], 1) > cap:
            continue
        H = z["kind"] == "H"; s = 1 if H else -1                     # s: dirección de los picos (arriba en un techo)
        idx = [p[0] for p in pk]; pr = [p[2] for p in pk]
        creation = idx[variant["minp"] - 1] + w
        if creation >= n - 2:
            continue
        for k in KS:
            m = variant["minp"]                                       # picos confirmados hasta ahora
            touched = False; broken = False; ev = -1; m_R = -1; R = 1.0
            for j in range(creation, min(n - 1, creation + HMAX)):
                while m < len(idx) and idx[m] + w <= j:
                    m += 1
                last = pr[m - 1]
                if s * ((h[j] if H else l[j]) - last) > 0:            # supera al último pico: se rompe la serie
                    broken = True; break
                if m != m_R:                                          # R sólo cambia cuando entra un pico nuevo
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
            vol_rel = float(v[creation:ev + 1].sum() / max((ev - creation + 1) * a["vavg"], 1e-9))
            for lvl_name, lvl in (("ultimo", last), ("primero", pr[0])):
                far = last - s * 2 * D
                hit, nb = race(h, l, ev, s, lvl, far, n)
                rows.append(dict(kind=z["kind"], k=k, nivel=lvl_name, virgen=int(not touched), vol_rel=vol_rel, ev=ev, D=D, R=R,
                                 hit=hit, bars=nb, lvl_dist=abs(lvl - c[ev]), far_dist=abs(c[ev] - far)))
    return rows


def race(h, l, e, s, lvl, far, n):
    end = min(n - 1, e + HMAX)
    for q in range(e + 1, end + 1):
        if (s > 0 and l[q] <= far) or (s < 0 and h[q] >= far):      # se aleja otro tanto primero (conservador)
            return 0, q - e
        if (s > 0 and h[q] >= lvl) or (s < 0 and l[q] <= lvl):
            return 1, q - e
    return 0, end - e


def control(S, A, keys, k, e, s, lvl_dist, far_dist, rng, zone_levels, R):
    """C-SZ: otra sesión, misma hora (± 1 h), mismo estado y actividad; nivel fantasma a la misma distancia, sin zona."""
    a = A[k]; s0 = a["st"][:, e]; rg0, sec0 = a["rg20"][e], a["sec20"][e]; clock = int(S[k]["clock"][e])
    others = [o for o in keys if o != k]; vals = []; pht = None; phs = None
    for oi in rng.permutation(len(others)):
        if len(vals) >= N_PH:
            break
        o = others[int(oi)]; y = A[o]
        lo_, hi_ = np.searchsorted(S[o]["clock"], clock - TOD), np.searchsorted(S[o]["clock"], clock + TOD)
        lo_ = max(lo_, 30)
        if hi_ <= lo_:
            continue
        st = y["st"][:, lo_:hi_]
        tol = np.maximum(TOL * np.abs(s0)[:, None], ABS_TOL)
        ok = np.all(np.abs(st - s0[:, None]) <= tol, axis=0)
        rg, sec = y["rg20"][lo_:hi_], y["sec20"][lo_:hi_]
        ok &= (np.abs(rg - rg0) <= TOL * rg0) & (np.abs(np.log(np.maximum(sec, 1e-3) / max(sec0, 1e-3))) <= np.log(1 + TOL))
        for qi in rng.permutation(np.flatnonzero(ok))[:10]:
            q = lo_ + int(qi)
            lvl = y["c"][q] + s * lvl_dist; far = y["c"][q] - s * far_dist
            if any(abs(lvl - zl) < R for zl in zone_levels.get(o, [])):
                continue                                             # hay una zona real cerca: no es «sin zona»
            hit, _ = race(y["h"], y["l"], q, s, lvl, far, len(y["c"]))
            vals.append(hit); pht = float(S[o]["t"][q]); phs = o
            break
    return (float(np.mean(vals)) if vals else np.nan, len(vals), pht, phs)


def control_sw(S, A, keys, k, e, s, lvl_dist, far_dist, rng, zone_levels, R, piv):
    """C-SW (agregado tras la corrida corregida, más estricto): el nivel es un máximo (o mínimo) RECIENTE real (pivote de
    2 velas en las últimas 300), todavía no superado, a la misma distancia (± R), que NO es parte de una acumulación.
    Contesta si atrae la acumulación o cualquier pico reciente."""
    a = A[k]; s0 = a["st"][:, e]; rg0, sec0 = a["rg20"][e], a["sec20"][e]; clock = int(S[k]["clock"][e])
    others = [o for o in keys if o != k]; vals = []
    for oi in rng.permutation(len(others)):
        if len(vals) >= N_PH:
            break
        o = others[int(oi)]; y = A[o]
        lo_, hi_ = np.searchsorted(S[o]["clock"], clock - TOD), np.searchsorted(S[o]["clock"], clock + TOD)
        lo_ = max(lo_, 300)
        if hi_ <= lo_:
            continue
        st = y["st"][:, lo_:hi_]
        tol = np.maximum(TOL * np.abs(s0)[:, None], ABS_TOL)
        ok = np.all(np.abs(st - s0[:, None]) <= tol, axis=0)
        rg, sec = y["rg20"][lo_:hi_], y["sec20"][lo_:hi_]
        ok &= (np.abs(rg - rg0) <= TOL * rg0) & (np.abs(np.log(np.maximum(sec, 1e-3) / max(sec0, 1e-3))) <= np.log(1 + TOL))
        src = y["h"] if s > 0 else y["l"]
        for qi in rng.permutation(np.flatnonzero(ok))[:15]:
            q = lo_ + int(qi)
            target = y["c"][q] + s * lvl_dist
            cand = [u for u in piv[o][s][(piv[o][s] >= q - 300) & (piv[o][s] < q - 2)] if abs(src[u] - target) <= R]
            cand = [u for u in cand if s * (src[u + 1:q + 1].max() if s > 0 else src[u + 1:q + 1].min()) <= s * src[u]]   # no superado
            cand = [u for u in cand if not any(abs(src[u] - zl) < R for zl in zone_levels.get(o, []))]
            if not cand:
                continue
            u = cand[-1]; lvl = src[u]; far = y["c"][q] - s * far_dist
            hit, _ = race(y["h"], y["l"], q, s, lvl, far, len(y["c"]))
            vals.append(hit); break
    return (float(np.mean(vals)) if vals else np.nan, len(vals))


def declare(inst, keys, part_tag="EXP"):
    from edgelab.edge_brain.episode_logger import measurement_episode
    from edgelab.edge_brain.hippocampus_store import DurableHippocampus
    part = f"P-IPC-{inst}-{part_tag}"
    if LEDGER.exists() and part in DurableHippocampus(LEDGER).partitions:
        return
    with measurement_episode(LEDGER, f"EP-IPC-PARTICION-{inst}" + ("" if part_tag == "EXP" else f"-{part_tag}"), goal=f"declarar partición IPC {inst} antes de medir",
                             recorded_by="tools/ipc.py measure", repo=REPO, prereg_ref=DOC) as ep:
        kind = "EXPLORATION" if part_tag == "EXP" else "REPLICATION"
        ep.store.record_partition(part, kind, f"{inst} 25T {part_tag} ({keys[0]}..{keys[-1]}), contrato canónico",
                                  [f"{inst}:{k}" for k in keys])


def step_measure(inst, part="disc"):
    S = T2.load(inst)
    if part == "rep":                                   # HOLDOUT-A3: replicación abr-sep, controles dentro de la misma partición
        keys = [k for k in sorted(S) if TB.REP_START <= k <= TB.REP_END]
        S = {k: S[k] for k in keys}
    else:
        keys = [k for k in sorted(S) if k <= TB.EXP_END]
    declare(inst, keys, "REP" if part == "rep" else "EXP")
    A = {k: arrays(S[k]) for k in keys}
    cfg = DET[inst]; cap = cap_of(inst); p = cfg["pars"]
    Zs = {}
    for k in keys:
        cd = dict(t=S[k]["t"], h=A[k]["h"], l=A[k]["l"])
        Zs[k] = PR.series(cd, 1.0, p["w"], p["max_gap"], p["max_step"], p["min_pull"], p["nmin"], extend_back=True, max_slope=None)
    zone_levels = {k: [z["picos"][-1][2] for z in Zs[k]] + [z["picos"][0][2] for z in Zs[k]] for k in keys}
    piv = {}
    for k in keys:
        piv[k] = {1: np.flatnonzero(PR.pivots(A[k]["h"], 2)), -1: np.flatnonzero(PR.pivots(-A[k]["l"], 2))}
    rng = np.random.default_rng(SEED)
    rows = []
    for vname, var in cfg["variants"].items():
        for k in keys:
            for r in events(S[k], A[k], Zs[k], var, p["w"], cap=cap):
                s = 1 if r["kind"] == "H" else -1
                cm, cn, pht, phs = control(S, A, keys, k, r["ev"], s, r["lvl_dist"], r["far_dist"], rng, zone_levels, r["R"])
                sw, swn = control_sw(S, A, keys, k, r["ev"], s, r["lvl_dist"], r["far_dist"], rng, zone_levels, r["R"], piv)
                rows.append(dict(r, inst=inst, detector=vname, session=k, ctrl=cm, n_ctrl=cn, ctrl_sw=sw, n_sw=swn, ph_t=pht, ph_session=phs, t_ev=float(S[k]["t"][r["ev"]])))
        print(inst, vname, "eventos", sum(1 for r in rows if r["detector"] == vname), flush=True)
    D = pd.DataFrame(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    D.to_parquet(OUT / (f"A_{inst}_rep.parquet" if part == "rep" else f"A_{inst}.parquet"), index=False)
    print(inst, "filas", len(D), "cobertura control", round(float((D.n_ctrl > 0).mean()), 3) if len(D) else None)


def step_report():
    rng = np.random.default_rng(SEED)
    cells = []
    for inst in ("ES", "NQ"):
        f = OUT / f"A_{inst}.parquet"
        if not f.exists():
            continue
        D = pd.read_parquet(f)
        for det in D.detector.unique():
            g0 = D[D.detector == det]
            t1, t2 = g0.vol_rel.quantile([1 / 3, 2 / 3])
            for virg in (1, 0):
                for k in KS:
                    for vol in ("todos", "bajo", "alto"):
                        for niv in ("ultimo", "primero"):
                            g = g0[(g0.virgen == virg) & (g0.k == k) & (g0.nivel == niv)]
                            if vol == "bajo":
                                g = g[g.vol_rel <= t1]
                            elif vol == "alto":
                                g = g[g.vol_rel >= t2]
                            g_sw = g.dropna(subset=["ctrl_sw"]) if "ctrl_sw" in g else g.iloc[0:0]
                            g = g.dropna(subset=["ctrl"])
                            base = dict(inst=inst, detector=det, virgen=virg, k=k, volumen=vol, nivel=niv, n=int(len(g)))
                            if len(g) < 50:
                                cells.append(dict(base, status="POCOS")); continue
                            d, lo, hi, mde, pv = EV.boot(g.hit.to_numpy(float), g.ctrl.to_numpy(), g.session.to_numpy(), rng)
                            h1 = (pd.to_datetime(g.session, format="%Y%m%d") < pd.Timestamp("2025-12-01")).to_numpy()
                            halves = [float((g.hit - g.ctrl)[m].mean()) if m.sum() >= 20 else None for m in (h1, ~h1)]
                            sw = None
                            if len(g_sw) >= 50:
                                d2, lo2, hi2, mde2, pv2 = EV.boot(g_sw.hit.to_numpy(float), g_sw.ctrl_sw.to_numpy(), g_sw.session.to_numpy(), rng)
                                sw = dict(n=int(len(g_sw)), real=float(g_sw.hit.mean()), control=float(g_sw.ctrl_sw.mean()), diff=d2, ci=[lo2, hi2], pval=pv2)
                            cells.append(dict(base, c_sw=sw, sessions=int(g.session.nunique()), real=float(g.hit.mean()), control=float(g.ctrl.mean()),
                                              diff=d, ci=[lo, hi], mde=mde, pval=pv, halves=halves, bars_med=float(g[g.hit == 1].bars.median()) if g.hit.sum() else None,
                                              status="OK"))
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
        c["pasa_B"] = bool(c["estado"] == "INFO+" and c.get("halves") and all(v is not None and v > 0 for v in c["halves"])
                           and c.get("c_sw") and c["c_sw"]["ci"][0] > 0)   # además tiene que ganarle al pico reciente (C-SW)
    from collections import Counter
    from edgelab.edge_brain.control_guard import audit_event_controls
    X = pd.concat([pd.read_parquet(OUT / f"A_{i}.parquet") for i in ("ES", "NQ") if (OUT / f"A_{i}.parquet").exists()]).dropna(subset=["ph_t"])
    audit = audit_event_controls((X.t_ev * 1e6).astype(np.int64).to_numpy(), (X.ph_t * 1e6).astype(np.int64).to_numpy(), HMAX * 60.0,
                                 same_session=(X.session == X.ph_session).to_numpy())
    body = dict(schema="EDGELAB_IPC_A_V1", doc=DOC, code_commit=TB._git("rev-parse", "HEAD"),
                tree_dirty=bool(TB._git("status", "--porcelain", "--", "tools", "edgelab")), estados=dict(Counter(c["estado"] for c in cells)),
                familia=len(ok), pasan_B=[c for c in cells if c["pasa_B"]], celdas=cells, control_audit=audit)
    raw = json.dumps(body, indent=1, default=float, ensure_ascii=False)
    (OUT / "reportA.json").write_text(raw, encoding="utf-8")
    sha = hashlib.sha256(raw.encode()).hexdigest()
    from edgelab.edge_brain.episode_logger import measurement_episode
    parts = [f"P-IPC-{i}-EXP" for i in ("ES", "NQ") if (OUT / f"A_{i}.parquet").exists()]
    with measurement_episode(LEDGER, f"EP-IPC-A-{sha[:8]}", goal="IPC etapa A: imán de acumulaciones de picos vs nivel sin zona",
                             recorded_by="tools/ipc.py report", repo=REPO, prereg_ref=DOC) as ep:
        ep.store.record_observation(f"OBS-IPC-A-{sha[:8]}", "IPC etapa A (alcance por celda)", "RESPONSE_PROFILE", parts,
                                    {f"{c['inst']}|{c['detector']}|v{c['virgen']}|k{c['k']}|{c['volumen']}|{c['nivel']}": (c.get("diff"), c["estado"]) for c in cells},
                                    {"hmax": HMAX}, sha, design="EVENT_VS_CONTROL", control_audit=audit)
    print(json.dumps(dict(sha=sha[:12], estados=body["estados"], familia=len(ok), pasan_B=len(body["pasan_B"]), audit=audit["status"])))


def step_replicate():
    """Replicación pre-registrada (manifiesto, HOLDOUT-A3): sólo las 23 celdas de `pasan_B`, unilateral, BH sobre las 23."""
    rng = np.random.default_rng(SEED)
    rep_src = json.loads((OUT / "reportA.json").read_text(encoding="utf-8"))
    assert rep_src["code_commit"] and len(rep_src["pasan_B"]) == 23
    cells = []
    for c0 in rep_src["pasan_B"]:
        D = pd.read_parquet(OUT / f"A_{c0['inst']}_rep.parquet")
        g0 = D[D.detector == c0["detector"]]
        t1, t2 = g0.vol_rel.quantile([1 / 3, 2 / 3])       # terciles del volumen: los de la replicación (el corte es relativo a la muestra)
        g = g0[(g0.virgen == c0["virgen"]) & (g0.k == c0["k"]) & (g0.nivel == c0["nivel"])]
        if c0["volumen"] == "bajo":
            g = g[g.vol_rel <= t1]
        elif c0["volumen"] == "alto":
            g = g[g.vol_rel >= t2]
        out = dict({k: c0[k] for k in ("inst", "detector", "virgen", "k", "volumen", "nivel")}, desc_diff=c0["diff"], desc_sw=c0["c_sw"]["diff"])
        for name, col in (("sz", "ctrl"), ("sw", "ctrl_sw")):
            h = g.dropna(subset=[col])
            if len(h) < 20:
                out[name] = dict(n=int(len(h))); continue
            d, lo, hi, mde, p2 = EV.boot(h.hit.to_numpy(float), h[col].to_numpy(), h.session.to_numpy(), rng)
            out[name] = dict(n=int(len(h)), sessions=int(h.session.nunique()), real=float(h.hit.mean()), control=float(h[col].mean()),
                             diff=d, ci=[lo, hi], mde=mde, p1=(p2 / 2 if d > 0 else 1 - p2 / 2))
        cells.append(out)
    ps = [c["sw"].get("p1", 1.0) for c in cells]
    for c, f in zip(cells, T2.TX._bh(ps)):
        c["replica"] = bool(f and c["sw"].get("diff", 0) > 0 and c["sz"].get("diff", 0) > 0)
        c["negativa_sig"] = bool(c["sw"].get("ci", [0, 0])[1] < 0)
    nrep = sum(c["replica"] for c in cells)
    veredicto = "REPLICA" if nrep >= 12 and not any(c["negativa_sig"] for c in cells) else "NO_REPLICA"
    body = dict(schema="EDGELAB_IPC_REP_V1", doc=DOC, fuente=rep_src.get("code_commit"), code_commit=TB._git("rev-parse", "HEAD"),
                tree_dirty=bool(TB._git("status", "--porcelain", "--", "tools", "edgelab")), replican=nrep, veredicto=veredicto, celdas=cells)
    raw = json.dumps(body, indent=1, default=float, ensure_ascii=False)
    (OUT / "reportREP.json").write_text(raw, encoding="utf-8")
    sha = hashlib.sha256(raw.encode()).hexdigest()
    from edgelab.edge_brain.episode_logger import measurement_episode
    parts = [f"P-IPC-{i}-REP" for i in ("ES", "NQ") if (OUT / f"A_{i}_rep.parquet").exists()]
    with measurement_episode(LEDGER, f"EP-IPC-REP-{sha[:8]}", goal="IPC replicación abr-sep de las 23 celdas", recorded_by="tools/ipc.py replicate",
                             repo=REPO, prereg_ref=DOC) as ep:
        ep.store.record_observation(f"OBS-IPC-REP-{sha[:8]}", "IPC replicación (alcance por celda)", "RESPONSE_PROFILE", parts,
                                    {f"{c['inst']}|{c['detector']}|v{c['virgen']}|k{c['k']}|{c['volumen']}|{c['nivel']}": (c["sw"].get("diff"), c["replica"]) for c in cells},
                                    {"hmax": HMAX}, sha)
    print(json.dumps(dict(sha=sha[:12], replican=nrep, veredicto=veredicto)))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["measure", "report", "replicate"])
    ap.add_argument("--inst", default="ES")
    ap.add_argument("--part", default="disc", choices=["disc", "rep"])
    a = ap.parse_args(argv)
    if a.step == "measure":
        step_measure(a.inst, a.part)
    elif a.step == "report":
        step_report()
    else:
        step_replicate()


if __name__ == "__main__":
    main()
