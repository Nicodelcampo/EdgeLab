#!/usr/bin/env python3
r"""VREV: reversión al VWAP desde un alejamiento X·ATR, con confirmaciones. E1 con economía incluida.

Manifiesto: docs/research/MANIFIESTO_VREV_E1_20260926.md (regla de alcance: toda conclusión es por celda).

    .venv\Scripts\python tools\vrev.py e1 --inst MYM
    .venv\Scripts\python tools\vrev.py report
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
from numba import njit  # noqa: E402

import evx as EV  # noqa: E402
import tbz_e2 as TB  # noqa: E402
import tbzx_iter2 as T2  # noqa: E402

OUT = REPO / "artifacts" / "vrev"
DOC = "docs/research/MANIFIESTO_VREV_E1_20260926.md"
LEDGER = REPO / "artifacts" / "hippocampus" / "vrev_20260926.jsonl"
XS = (2, 3, 4, 6)
CONF = ("C0", "C1", "C2", "C3")
KS = (1, 2)
W_CONF = 30
HMAX = 200
WARMUP = EV.WARMUP
N_PH = 3
TOD, TOL, ABS_TOL = 3600, 0.5, 0.15
COST = {"ES": 1.4, "NQ": 2.0, "YM": 2.0, "MYM": 3.0}
SEED = 20260926
ASSETS = ("MYM", "YM", "ES", "NQ")


@njit(cache=True)
def race(h, l, c, j, dr, target, stop, hmax):
    """Desde la vela j+1: stop primero si se tocan los dos en la misma vela. Devuelve (acierto, precio_salida, velas)."""
    n = len(c)
    end = min(n - 1, j + hmax)
    for q in range(j + 1, end + 1):
        if (dr > 0 and l[q] <= stop) or (dr < 0 and h[q] >= stop):
            return 0, stop, q - j
        if (dr > 0 and h[q] >= target) or (dr < 0 and l[q] <= target):
            return 1, target, q - j
    return 0, c[end], end - j


def trigger(A, e9, e21, i, dr, X):
    """Vela de confirmación para cada modo (o -1). Sólo mira hasta la vela que confirma."""
    c, vw, atr = A["c"], A["vw"], A["atr"]
    n = len(c)
    out = {"C0": i, "C1": -1, "C2": -1, "C3": -1}
    for j in range(i + 1, min(n - 1, i + W_CONF) + 1):
        if out["C1"] < 0 and dr * (e9[j] - e21[j]) > 0 and dr * (e9[j - 1] - e21[j - 1]) <= 0:
            out["C1"] = j
        if out["C2"] < 0 and dr * (c[j] - e21[j]) > 0 and dr * (c[j - 1] - e21[j - 1]) <= 0:
            out["C2"] = j
        if out["C3"] < 0 and abs(c[j] - vw[j]) <= (X - 0.5) * atr[j]:
            out["C3"] = j
    return out


def outcomes(A, j, dr, k, tick):
    c, h, l, vw, atr = A["c"], A["h"], A["l"], A["vw"], A["atr"]
    entry, target = c[j], vw[j]
    stop = entry - dr * k * atr[j]
    if dr * (target - entry) <= 0:
        return None
    hit, px, nb = race(h, l, c, j, dr, target, stop, HMAX)
    risk, rew = k * atr[j], abs(target - entry)
    return dict(hit=hit, R=dr * (px - entry) / risk, move_t=dr * (px - entry) / tick, rew_atr=rew / atr[j],
                p0=risk / (risk + rew + tick), bars=nb,
                **{f"d{hh}": (dr * (c[j + hh] - entry) / atr[j] if j + hh < len(c) else np.nan) for hh in (20, 60, 200)})


def step_e1(inst):
    S = T2.load(inst)
    keys = [k for k in sorted(S) if k <= TB.EXP_END]
    declare(inst, keys)
    tick = 1.0                                     # las velas están en ticks enteros
    A = {}
    for k in keys:
        a = EV.session_arrays(S[k]); a["h"] = S[k]["h"].astype(float); a["l"] = S[k]["l"].astype(float)
        a["e9"], a["e21"] = EV.ema(a["c"], 9), EV.ema(a["c"], 21)
        a["st"] = np.vstack([(a["c"] - a["vw"]) / a["atr"], np.r_[np.full(5, np.nan), a["e21"][5:] - a["e21"][:-5]] / a["atr"]])
        A[k] = a
    rng = np.random.default_rng(SEED)
    rows = []
    for k in keys:
        a = A[k]; n = a["n"]
        dist = (a["c"] - a["vw"]) / a["atr"]
        for X in XS:
            armed = True
            for i in range(WARMUP, n - 1):
                if not armed:
                    if abs(dist[i]) < X / 2:
                        armed = True
                    continue
                if abs(dist[i]) < X:
                    continue
                armed = False
                dr = -1 if dist[i] > 0 else 1
                trig = trigger(a, a["e9"], a["e21"], i, dr, X)
                for cf in CONF:
                    j = trig[cf]
                    if j < 0:
                        rows.append(dict(inst=inst, session=k, i=i, X=X, conf=cf, kind="real", entered=0)); continue
                    s0 = a["st"][:, j]; rg0, sec0 = a["rg20"][j], a["sec20"][j]; clock = int(S[k]["clock"][j])
                    for kk in KS:
                        o = outcomes(a, j, dr, kk, tick)
                        if o is None:
                            continue
                        base = dict(inst=inst, session=k, i=i, j=j, X=X, conf=cf, k=kk, dir=dr, clock=clock, t_ev=float(S[k]["t"][j]))
                        rows.append(dict(base, kind="real", entered=1, **o))
                    # controles: mismo estado en otra sesión, misma hora
                    got = 0
                    others = [x for x in keys if x != k]
                    for oi in rng.permutation(len(others)):
                        if got >= N_PH:
                            break
                        oname = others[int(oi)]; y = A[oname]
                        lo, hi = np.searchsorted(S[oname]["clock"], clock - TOD), np.searchsorted(S[oname]["clock"], clock + TOD)
                        lo = max(lo, WARMUP)
                        if hi <= lo:
                            continue
                        st = y["st"][:, lo:hi]
                        tol = np.maximum(TOL * np.abs(s0)[:, None], ABS_TOL)
                        ok = np.all(np.abs(st - s0[:, None]) <= tol, axis=0)
                        rg, sec = y["rg20"][lo:hi], y["sec20"][lo:hi]
                        ok &= (np.abs(rg - rg0) <= TOL * rg0) & (np.abs(np.log(np.maximum(sec, 1e-3) / max(sec0, 1e-3))) <= np.log(1 + TOL))
                        idx = np.flatnonzero(ok)
                        if not len(idx):
                            continue
                        q = lo + int(idx[int(rng.integers(len(idx)))])
                        for kk in KS:
                            o = outcomes(y, q, dr, kk, tick)
                            if o is None:
                                continue
                            rows.append(dict(inst=inst, session=k, i=i, j=j, X=X, conf=cf, k=kk, dir=dr, clock=clock, t_ev=float(S[k]["t"][j]),
                                             kind="control", ph_session=oname, ph_t=float(S[oname]["t"][q]), entered=1, **o))
                        got += 1
    D = pd.DataFrame(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    D.to_parquet(OUT / f"e1_{inst}.parquet", index=False)
    R = D[(D.kind == "real")]
    print(inst, "sesiones", len(keys), "alejamientos", R.drop_duplicates(["session", "i", "X"]).shape[0], "filas", len(D))


def declare(inst, keys):
    from edgelab.edge_brain.episode_logger import measurement_episode
    from edgelab.edge_brain.hippocampus_store import DurableHippocampus
    part = f"P-VREV-{inst}-EXP"
    if LEDGER.exists() and part in DurableHippocampus(LEDGER).partitions:
        return
    with measurement_episode(LEDGER, f"EP-VREV-PARTICION-{inst}", goal=f"declarar partición VREV {inst} antes de medir",
                             recorded_by="tools/vrev.py e1", repo=REPO, prereg_ref=DOC) as ep:
        ep.store.record_partition(part, "EXPLORATION", f"{inst} 25T exploración (<= 2026-03-31), contrato canónico",
                                  [f"{inst}:{k}" for k in keys])


def verdict(c):
    if c["status"] != "OK":
        return "SIN_POTENCIA"
    if c.get("fdr"):
        return "INFO+" if c["diff"] > 0 else "INFO-"
    return "SIN_INFO" if c["mde"] <= 0.10 else "SIN_POTENCIA"


def step_report():
    rng = np.random.default_rng(SEED)
    cells = []
    for inst in ASSETS:
        f = OUT / f"e1_{inst}.parquet"
        if not f.exists():
            continue
        D = pd.read_parquet(f)
        R = D[(D.kind == "real") & (D.entered == 1)]
        C = D[D.kind == "control"].groupby(["session", "i", "X", "conf", "k"])[["hit", "R", "move_t"]].mean()
        for (X, cf, kk), g in R.groupby(["X", "conf", "k"]):
            J = g.set_index(["session", "i", "X", "conf", "k"]).join(C, rsuffix="_c", how="inner").dropna(subset=["hit", "hit_c"])
            n_alej = D[(D.kind == "real") & (D.X == X) & (D.conf == cf)].drop_duplicates(["session", "i"]).shape[0]
            base = dict(inst=inst, X=X, conf=cf, k=kk, n_alejamientos=n_alej, n_entradas=int(len(g)), tasa_entrada=round(len(g) / max(n_alej * 1, 1), 3))
            if len(J) < 100:
                cells.append(dict(base, n=int(len(J)), status="POCOS")); continue
            ses = J.index.get_level_values("session").to_numpy()
            d, lo, hi, mde, pv = EV.boot(J.hit.to_numpy(), J.hit_c.to_numpy(), ses, rng)
            months = pd.to_datetime(pd.Series(ses), format="%Y%m%d")
            h1 = (months < pd.Timestamp("2025-12-01")).to_numpy()
            halves = {nm: float((J.hit - J.hit_c).to_numpy()[m].mean()) if m.sum() >= 30 else None for nm, m in (("h1", h1), ("h2", ~h1))}
            cells.append(dict(base, n=int(len(J)), sessions=int(len(set(ses))), hit=float(J.hit.mean()), hit_c=float(J.hit_c.mean()),
                              p0=float(J.p0.mean()), diff=d, ci=[lo, hi], mde=mde, pval=pv,
                              R=float(J.R.mean()), R_c=float(J.R_c.mean()), move_t=float(J.move_t.mean()), move_t_c=float(J.move_t_c.mean()),
                              neto_t=float(J.move_t.mean() - COST[inst]), costo_t=COST[inst], rew_atr=float(J.rew_atr.mean()),
                              halves=halves, status="OK"))
    ok = [c for c in cells if c["status"] == "OK"]
    for c, f in zip(ok, T2.TX._bh([c["pval"] for c in ok])):
        c["fdr"] = bool(f)
    for c in cells:
        c["estado"] = verdict(c)
        hv = [v for v in (c.get("halves") or {}).values() if v is not None]
        c["pasa_E2"] = bool(c["estado"] == "INFO+" and c["R"] > c["R_c"] and c["neto_t"] > 0 and len(hv) == 2 and all(v > 0 for v in hv))
    from edgelab.edge_brain.control_guard import audit_event_controls
    X_ = pd.concat([pd.read_parquet(OUT / f"e1_{i}.parquet") for i in ASSETS if (OUT / f"e1_{i}.parquet").exists()])
    X_ = X_[X_.kind == "control"]
    audit = audit_event_controls((X_.t_ev * 1e6).astype(np.int64).to_numpy(), (X_.ph_t * 1e6).astype(np.int64).to_numpy(), HMAX * 60.0,
                                 same_session=(X_.session == X_.ph_session).to_numpy())
    from collections import Counter
    body = dict(schema="EDGELAB_VREV_E1_V1", doc=DOC, code_commit=TB._git("rev-parse", "HEAD"),
                tree_dirty=bool(TB._git("status", "--porcelain", "--", "tools", "edgelab")),
                estados=dict(Counter(c["estado"] for c in cells)), celdas=cells, pasan_E2=[c for c in cells if c["pasa_E2"]],
                no_medido="ver manifiesto §5", control_audit=audit)
    raw = json.dumps(body, indent=1, default=float, ensure_ascii=False)
    (OUT / "report_e1.json").write_text(raw, encoding="utf-8")
    sha = hashlib.sha256(raw.encode()).hexdigest()
    from edgelab.edge_brain.episode_logger import measurement_episode
    parts = [f"P-VREV-{i}-EXP" for i in ASSETS if (OUT / f"e1_{i}.parquet").exists()]
    with measurement_episode(LEDGER, f"EP-VREV-E1-{sha[:8]}", goal="VREV E1: reversión al VWAP desde X·ATR con confirmaciones",
                             recorded_by="tools/vrev.py report", repo=REPO, prereg_ref=DOC) as ep:
        ep.store.record_observation(f"OBS-VREV-E1-{sha[:8]}", "VREV E1 por celda (alcance: sólo la variante medida)", "RESPONSE_PROFILE",
                                    parts, {f"{c['inst']}|X{c['X']}|{c['conf']}|k{c['k']}": (c.get("diff"), c["estado"]) for c in cells},
                                    {"hmax": HMAX}, sha, design="EVENT_VS_CONTROL", control_audit=audit)
    print(json.dumps(dict(sha=sha[:12], estados=body["estados"], pasan_E2=len(body["pasan_E2"]), audit=audit["status"])))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["e1", "report"])
    ap.add_argument("--inst", default="MYM")
    a = ap.parse_args(argv)
    step_e1(a.inst) if a.step == "e1" else step_report()


if __name__ == "__main__":
    main()
