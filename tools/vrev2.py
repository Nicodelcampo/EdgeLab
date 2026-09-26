#!/usr/bin/env python3
r"""VREV-A (reversión al VWAP tras agotamiento) y VCONT (continuación tras el primer alejamiento). E1.

Manifiesto: docs/research/MANIFIESTO_VREVA_VCONT_E1_20260926.md.

    .venv\Scripts\python tools\vrev2.py e1 --inst MYM
    .venv\Scripts\python tools\vrev2.py report
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
import tbz_e2 as TB  # noqa: E402
import tbzx_iter2 as T2  # noqa: E402
import vrev as V  # noqa: E402

OUT = REPO / "artifacts" / "vrev2"
DOC = "docs/research/MANIFIESTO_VREVA_VCONT_E1_20260926.md"
LEDGER = REPO / "artifacts" / "hippocampus" / "vreva_vcont_20260926.jsonl"   # ledger propio: particiones independientes de VREV
XS = (3, 4, 6)
W_EXH, W_CONT = 60, 30
SEED = 20260927
ASSETS = V.ASSETS


def arrays(x):
    a = EV.session_arrays(x)
    a["h"], a["l"] = x["h"].astype(float), x["l"].astype(float)
    a["e21"] = EV.ema(a["c"], 21)
    sl = np.r_[np.full(5, np.nan), a["e21"][5:] - a["e21"][:-5]] / a["atr"]
    a["sl"] = sl
    a["st"] = np.vstack([(a["c"] - a["vw"]) / a["atr"], sl])
    return a


def base_events(a):
    """(i, X, dir_hacia_vwap) del primer alejamiento, con rearme a X/2."""
    dist = (a["c"] - a["vw"]) / a["atr"]
    out = []
    for X in XS:
        armed = True
        for i in range(V.WARMUP, a["n"] - 1):
            if not armed:
                if abs(dist[i]) < X / 2:
                    armed = True
                continue
            if abs(dist[i]) >= X:
                armed = False
                out.append((i, X, -1 if dist[i] > 0 else 1))
    return out


def trades(a, i, X, dv):
    """Lista de (familia, variante, j, dir, target, stop). dv = dirección hacia el VWAP."""
    c, h, l, vw, atr, n = a["c"], a["h"], a["l"], a["vw"], a["atr"], a["n"]
    res = []
    # ---- VREV-A: agotamiento
    ext, ext_i = (l[i], i) if dv > 0 else (h[i], i)            # extremo de la excursión (lejos del VWAP)
    fired = {}
    for j in range(i + 1, min(n - 1, i + W_EXH) + 1):
        if (dv > 0 and l[j] < ext) or (dv < 0 and h[j] > ext):
            ext, ext_i = (l[j] if dv > 0 else h[j]), j
        if abs(c[j] - vw[j]) < (X / 2) * atr[j]:
            break
        if "A1-10" not in fired and j - ext_i >= 10:
            fired["A1-10"] = (j, ext)
        if "A1-20" not in fired and j - ext_i >= 20:
            fired["A1-20"] = (j, ext)
        if "A2" not in fired and dv * (c[j] - ext) >= atr[j]:
            fired["A2"] = (j, ext)
        if "A3" not in fired and np.isfinite(a["sl"][j]) and np.isfinite(a["sl"][j - 1]) and dv * a["sl"][j] > 0 >= dv * a["sl"][j - 1]:
            fired["A3"] = (j, ext)
    for var, (j, ex) in fired.items():
        for k in (0.5, 1.0):
            tgt, stp = vw[j], ex - dv * k * atr[j]
            if dv * (tgt - c[j]) > 0 and dv * (c[j] - stp) > 0:
                res.append(("VREVA", f"{var}|k{k}", j, dv, tgt, stp))
    # ---- VCONT: continuación (alejándose del VWAP)
    dc = -dv
    js = {"K0": i}
    ext2 = h[i] if dc > 0 else l[i]
    for j in range(i + 1, min(n - 1, i + W_CONT) + 1):
        if (dc > 0 and c[j] > ext2) or (dc < 0 and c[j] < ext2):
            js["K1"] = j
            break
    for var, j in js.items():
        for m in (2, 4):
            for k in (1, 2):
                res.append(("VCONT", f"{var}|m{m}|k{k}", j, dc, c[j] + dc * m * atr[j], c[j] - dc * k * atr[j]))
    return res


def outcome(a, j, dr, tgt, stp):
    c = a["c"]
    hit, px, nb = V.race(a["h"], a["l"], c, j, dr, tgt, stp, V.HMAX)
    risk = abs(c[j] - stp)
    return dict(hit=hit, R=dr * (px - c[j]) / risk, move_t=dr * (px - c[j]), p0=risk / (risk + abs(tgt - c[j]) + 1), bars=nb,
                **{f"d{hh}": (dr * (c[j + hh] - c[j]) / a["atr"][j] if j + hh < len(c) else np.nan) for hh in (20, 60, 200)})


def step_e1(inst):
    S = T2.load(inst)
    keys = [k for k in sorted(S) if k <= TB.EXP_END]
    declare(inst, keys)
    A = {k: arrays(S[k]) for k in keys}
    rng = np.random.default_rng(SEED)
    rows = []
    for k in keys:
        a = A[k]
        for (i, X, dv) in base_events(a):
            for fam, var, j, dr, tgt, stp in trades(a, i, X, dv):
                clock = int(S[k]["clock"][j])
                base = dict(inst=inst, fam=fam, var=var, X=X, session=k, i=i, j=j, dir=dr, clock=clock, t_ev=float(S[k]["t"][j]))
                rows.append(dict(base, kind="real", **outcome(a, j, dr, tgt, stp)))
                # geometría en ATR para transferir al control
                gt, gs = (tgt - a["c"][j]) / a["atr"][j], (stp - a["c"][j]) / a["atr"][j]
                s0 = a["st"][:, j]; rg0, sec0 = a["rg20"][j], a["sec20"][j]
                got = 0
                others = [x for x in keys if x != k]
                for oi in rng.permutation(len(others)):
                    if got >= V.N_PH:
                        break
                    on = others[int(oi)]; y = A[on]
                    lo, hi = np.searchsorted(S[on]["clock"], clock - V.TOD), np.searchsorted(S[on]["clock"], clock + V.TOD)
                    lo = max(lo, V.WARMUP)
                    if hi <= lo:
                        continue
                    st = y["st"][:, lo:hi]
                    tol = np.maximum(V.TOL * np.abs(s0)[:, None], V.ABS_TOL)
                    ok = np.all(np.abs(st - s0[:, None]) <= tol, axis=0)
                    rg, sec = y["rg20"][lo:hi], y["sec20"][lo:hi]
                    ok &= (np.abs(rg - rg0) <= V.TOL * rg0) & (np.abs(np.log(np.maximum(sec, 1e-3) / max(sec0, 1e-3))) <= np.log(1 + V.TOL))
                    idx = np.flatnonzero(ok)
                    if not len(idx):
                        continue
                    q = lo + int(idx[int(rng.integers(len(idx)))])
                    cq, aq = y["c"][q], y["atr"][q]
                    rows.append(dict(base, kind="control", ph_session=on, ph_t=float(S[on]["t"][q]),
                                     **outcome(y, q, dr, cq + gt * aq, cq + gs * aq)))
                    got += 1
    D = pd.DataFrame(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    D.to_parquet(OUT / f"e1_{inst}.parquet", index=False)
    print(inst, "sesiones", len(keys), "operaciones reales", int((D.kind == "real").sum()), "filas", len(D))


def declare(inst, keys):
    from edgelab.edge_brain.episode_logger import measurement_episode
    from edgelab.edge_brain.hippocampus_store import DurableHippocampus
    for fam in ("VREV2",):                                   # una partición por activo, compartida por VREV-A y VCONT (misma corrida)
        part = f"P-{fam}-{inst}-EXP"
        if LEDGER.exists() and part in DurableHippocampus(LEDGER).partitions:
            continue
        with measurement_episode(LEDGER, f"EP-{fam}-PARTICION-{inst}", goal=f"declarar partición {fam} {inst} antes de medir",
                                 recorded_by="tools/vrev2.py e1", repo=REPO, prereg_ref=DOC) as ep:
            ep.store.record_partition(part, "EXPLORATION", f"{inst} 25T exploración (<= 2026-03-31), contrato canónico",
                                      [f"{inst}:{k}" for k in keys])


def step_report():
    rng = np.random.default_rng(SEED)
    cells = []
    for inst in ASSETS:
        f = OUT / f"e1_{inst}.parquet"
        if not f.exists():
            continue
        D = pd.read_parquet(f)
        R = D[D.kind == "real"]
        C = D[D.kind == "control"].groupby(["fam", "var", "X", "session", "i", "j"])[["hit", "R", "move_t"]].mean()
        for (fam, var, X), g in R.groupby(["fam", "var", "X"]):
            J = g.set_index(["fam", "var", "X", "session", "i", "j"]).join(C, rsuffix="_c", how="inner").dropna(subset=["hit", "hit_c"])
            base = dict(inst=inst, fam=fam, var=var, X=int(X), n_real=int(len(g)))
            if len(J) < 100:
                cells.append(dict(base, n=int(len(J)), status="POCOS")); continue
            ses = J.index.get_level_values("session").to_numpy()
            d, lo, hi, mde, pv = EV.boot(J.hit.to_numpy(), J.hit_c.to_numpy(), ses, rng)
            h1 = (pd.to_datetime(pd.Series(ses), format="%Y%m%d") < pd.Timestamp("2025-12-01")).to_numpy()
            halves = {nm: float((J.hit - J.hit_c).to_numpy()[m].mean()) if m.sum() >= 30 else None for nm, m in (("h1", h1), ("h2", ~h1))}
            cells.append(dict(base, n=int(len(J)), sessions=int(len(set(ses))), cobertura=round(len(J) / len(g), 3), hit=float(J.hit.mean()),
                              hit_c=float(J.hit_c.mean()), p0=float(J.p0.mean()), diff=d, ci=[lo, hi], mde=mde, pval=pv,
                              R=float(J.R.mean()), R_c=float(J.R_c.mean()), move_t=float(J.move_t.mean()), neto_t=float(J.move_t.mean() - V.COST[inst]),
                              halves=halves, status="OK"))
    for fam in ("VREVA", "VCONT"):
        ok = [c for c in cells if c["status"] == "OK" and c["fam"] == fam]
        for c, f in zip(ok, T2.TX._bh([c["pval"] for c in ok])):
            c["fdr"] = bool(f)
    for c in cells:
        c["estado"] = V.verdict(c)
        hv = [v for v in (c.get("halves") or {}).values() if v is not None]
        c["pasa_E2"] = bool(c["estado"] == "INFO+" and c["R"] > c["R_c"] and c["neto_t"] > 0 and len(hv) == 2 and all(v > 0 for v in hv))
    from collections import Counter
    from edgelab.edge_brain.control_guard import audit_event_controls
    X_ = pd.concat([pd.read_parquet(OUT / f"e1_{i}.parquet") for i in ASSETS if (OUT / f"e1_{i}.parquet").exists()])
    X_ = X_[X_.kind == "control"]
    audit = audit_event_controls((X_.t_ev * 1e6).astype(np.int64).to_numpy(), (X_.ph_t * 1e6).astype(np.int64).to_numpy(), V.HMAX * 60.0,
                                 same_session=(X_.session == X_.ph_session).to_numpy())
    est = {fam: dict(Counter(c["estado"] for c in cells if c["fam"] == fam)) for fam in ("VREVA", "VCONT")}
    body = dict(schema="EDGELAB_VREVA_VCONT_E1_V1", doc=DOC, code_commit=TB._git("rev-parse", "HEAD"),
                tree_dirty=bool(TB._git("status", "--porcelain", "--", "tools", "edgelab")), estados=est, celdas=cells,
                pasan_E2=[c for c in cells if c["pasa_E2"]], control_audit=audit)
    raw = json.dumps(body, indent=1, default=float, ensure_ascii=False)
    (OUT / "report_e1.json").write_text(raw, encoding="utf-8")
    sha = hashlib.sha256(raw.encode()).hexdigest()
    from edgelab.edge_brain.episode_logger import measurement_episode
    parts = [f"P-VREV2-{i}-EXP" for i in ASSETS if (OUT / f"e1_{i}.parquet").exists()]
    with measurement_episode(LEDGER, f"EP-VREVA-VCONT-E1-{sha[:8]}", goal="VREV-A y VCONT E1 por celda",
                             recorded_by="tools/vrev2.py report", repo=REPO, prereg_ref=DOC) as ep:
        ep.store.record_observation(f"OBS-VREVA-VCONT-E1-{sha[:8]}", "VREV-A y VCONT E1 (alcance por celda)", "RESPONSE_PROFILE", parts,
                                    {f"{c['fam']}|{c['inst']}|X{c['X']}|{c['var']}": (c.get("diff"), c["estado"]) for c in cells},
                                    {"hmax": V.HMAX}, sha, design="EVENT_VS_CONTROL", control_audit=audit)
    print(json.dumps(dict(sha=sha[:12], estados=est, pasan_E2=len(body["pasan_E2"]), audit=audit["status"])))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["e1", "report"])
    ap.add_argument("--inst", default="MYM")
    a = ap.parse_args(argv)
    step_e1(a.inst) if a.step == "e1" else step_report()


if __name__ == "__main__":
    main()
