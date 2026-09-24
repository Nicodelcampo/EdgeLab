#!/usr/bin/env python3
r"""Réplica pre-registrada de V-RND (absorción en número redondo → ruptura) en otros instrumentos.
Protocolo congelado: docs/research/PROTOCOLO_REPLICA_VRND_ES_GC_6E_20260924.md (commit 96c664f, antes de mirar).

Reutilizable sin chat: la configuración por instrumento vive en INSTR. Para L2 nuevo (octubre, 12-26), se agrega
el contrato a `bases` y se corre con un rango y un id de partición nuevos. El protocolo no cambia.

    .venv\Scripts\python tools\vrnd_replicate.py declare
    .venv\Scripts\python tools\vrnd_replicate.py run --workers 4
    .venv\Scripts\python tools\vrnd_replicate.py report
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from math import erfc, sqrt
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "tools"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402

import nq_l2_explore as X  # noqa: E402
import nq_l2_synergy as S  # noqa: E402
from edgelab.research.l2_manipulation_heuristics import ASK  # noqa: E402

L2 = Path(r"E:\l2_parquet")
OUT = REPO / "artifacts" / "vrnd_replica"
LEDGER = REPO / "artifacts" / "hippocampus" / "vrnd_20260924.jsonl"
PROTO = "docs/research/PROTOCOLO_REPLICA_VRND_ES_GC_6E_20260924.md"
RANGE = ("20260701", "20260821")
US = X.US
HZ = (30, 60, 300)
H_FILTER = 900                      # mismo filtro de ventana que la corrida C de NQ
CTRL_LO_S, CTRL_HI_S = H_FILTER + 60, H_FILTER + 1800
N_CTRL, SEED, N_BOOT, MIN_EV = 5, 20260924, 2000, 30
INSTR = {
    "ES": dict(bases=["ES_09-26"], ns="ES-L2", round_t=100, sens_t=200, win_t=2, nq_scaled=-2.7, part="P-VRND-ES"),
    "GC": dict(bases=["GC_08-26", "GC_12-26"], ns="GC-L2", round_t=100, sens_t=250, win_t=2, nq_scaled=-3.6, part="P-VRND-GC"),
    "6E": dict(bases=["6E_09-26"], ns="VRND-6E", round_t=100, sens_t=200, win_t=2, nq_scaled=-2.0, part="P-VRND-6E"),
}


def continuity_fail_days(base):
    f = L2 / "continuity" / base / "continuity_summary.json"
    if not f.exists():
        return set()
    d = json.loads(f.read_text(encoding="utf-8"))
    bad = set()
    for b in d.get("boundaries", []):
        if str(b.get("continuity_status", "")).startswith("FAIL"):
            bad |= {b["left_session"], b["right_session"]}
    return bad


def n_trades(base, day):
    p = L2 / base / "l1_quotes" / f"{day}.parquet"
    if not p.exists():
        return 0
    s = pq.read_table(p, columns=["side"]).column("side").to_numpy()
    return int((s == 2).sum())


def plan(inst):
    """(día, base) elegibles por reglas target-free: contrato con más trades, >= 5.000 trades, sin FAIL de continuidad."""
    cfg = INSTR[inst]
    days = sorted({p.stem for b in cfg["bases"] for p in (L2 / b / "l2_depth").glob("*.parquet")
                   if RANGE[0] <= p.stem <= RANGE[1]})
    bad = {b: continuity_fail_days(b) for b in cfg["bases"]}
    out, skipped = [], []
    for d in days:
        cand = sorted(((n_trades(b, d), b) for b in cfg["bases"]), reverse=True)
        nt, b = cand[0]
        if nt < 5000:
            skipped.append((d, "POCA_ACTIVIDAD"))
        elif d in bad[b]:
            skipped.append((d, "CONTINUIDAD_FAIL"))
        else:
            out.append((d, b))
    return out, skipped


def session_rows(args):
    inst, day, base = args
    cfg = INSTR[inst]
    X.BASE = L2 / base                                     # load_l1 lee X.BASE (proceso aislado por worker)
    Q, T = X.load_l1(day)
    if len(T) < 5000 or len(Q) < 5000:
        return inst, day, "POCA_ACTIVIDAD", None
    if not X.clock_ok(T.ts.to_numpy(), day):
        return inst, day, "CLOCK_UNCERTIFIED_P84", None
    rng = np.random.default_rng([SEED, int(day), ord(inst[0])])
    qts = Q.ts.to_numpy()
    mid = (Q.bid.to_numpy() + Q.ask.to_numpy()) / 2.0
    spr = (Q.ask.to_numpy() - Q.bid.to_numpy()).astype(float)
    last = int(qts[-1])
    ev = X.absorption_events(T)
    evt = np.array([e["available_ts_us"] for e in ev]) if ev else np.array([])
    grid = np.arange(int(qts[0]) + 60 * US, last, 30 * US)
    vg = np.array([X.vol60(T, g) for g in grid]) if len(grid) else np.array([0.0])
    q1, q2 = np.percentile(vg, [33.3, 66.7])
    terc = lambda v: 0 if v <= q1 else (1 if v <= q2 else 2)
    ok_t = lambda t: t + H_FILTER * US <= last and not X.in_halt(t - 1800 * US, t + H_FILTER * US)

    def outc(t0, dirn):
        a = max(np.searchsorted(qts, t0, "right") - 1, 0)
        o = {}
        for h in HZ:
            b = max(np.searchsorted(qts, t0 + h * US, "right") - 1, 0)
            o[f"sig{h}"] = float(dirn * (mid[b] - mid[a]))
        o["spread0"] = float(spr[a])
        return o

    def rdist(L, step):
        r = L % step
        return int(min(r, step - r))

    rows = []
    for m, e in enumerate(ev):
        dirn = -1 if e["side"] == ASK else 1
        t0 = e["available_ts_us"] + X.LAT
        tch = X.touch_at(Q, t0, dirn)
        if tch is None or not ok_t(t0):
            continue
        dist = (e["tick"] - tch) if dirn == -1 else (tch - e["tick"])
        te = terc(X.vol60(T, t0))
        L = int(e["tick"])
        rows.append(dict(kind=1, match=m, dirn=dirn, t0=int(t0), level=L, rd=rdist(L, cfg["round_t"]),
                         rd_sens=rdist(L, cfg["sens_t"]), **outc(t0, dirn)))
        got = 0
        for _ in range(80 * N_CTRL):
            if got >= N_CTRL:
                break
            tc = int(t0 + rng.integers(CTRL_LO_S, CTRL_HI_S) * US)
            if (len(evt) and np.min(np.abs(evt - tc)) < X.EXCL_S * US) or not ok_t(tc) or terc(X.vol60(T, tc)) != te:
                continue
            tt = X.touch_at(Q, tc, dirn)
            if tt is None:
                continue
            lv = int(tt + dist if dirn == -1 else tt - dist)
            rows.append(dict(kind=0, match=m, dirn=dirn, t0=tc, level=lv, rd=rdist(lv, cfg["round_t"]),
                             rd_sens=rdist(lv, cfg["sens_t"]), **outc(tc, dirn)))
            got += 1
    df = pd.DataFrame(rows)
    df.insert(0, "session", day)
    df.insert(1, "base", base)
    return inst, day, None, df


def step_declare():
    from edgelab.edge_brain.episode_logger import measurement_episode
    OUT.mkdir(parents=True, exist_ok=True)
    plans = {}
    with measurement_episode(LEDGER, "EP-VRND-DECLARE-20260924", goal="V-RND: declarar particiones de réplica antes de medir",
                             recorded_by="tools/vrnd_replicate.py declare", repo=REPO, prereg_ref=PROTO) as ep:
        for inst, cfg in INSTR.items():
            p, sk = plan(inst)
            plans[inst] = dict(sessions=p, skipped=sk)
            desc = f"V-RND réplica {inst} L2 {RANGE[0]}..{RANGE[1]} (enmienda L2: desarrollo). Protocolo {PROTO}."
            if inst == "6E":
                desc += " Mismas fechas que P-6E-REG-L2HOLDOUT (ledger regimes_6e, FUTURE, sólo proxies target-free); OK Nico 24/09."
            ep.store.record_partition(cfg["part"], "EXPLORATION", desc, [f"{cfg['ns']}:{d}" for d, _ in p])
    (OUT / "plan.json").write_text(json.dumps(plans, indent=1), encoding="utf-8")
    print(json.dumps({k: (len(v["sessions"]), len(v["skipped"])) for k, v in plans.items()}))


def step_run(workers):
    plans = json.loads((OUT / "plan.json").read_text(encoding="utf-8"))
    jobs = [(inst, d, b) for inst, v in plans.items() for d, b in v["sessions"]
            if not (OUT / "rows" / inst / f"{d}.parquet").exists()]
    log = OUT / "run_log.jsonl"
    with ProcessPoolExecutor(workers) as ex:
        for inst, d, skip, df in ex.map(session_rows, jobs):
            if df is not None:
                (OUT / "rows" / inst).mkdir(parents=True, exist_ok=True)
                df.to_parquet(OUT / "rows" / inst / f"{d}.parquet", index=False)
            rec = dict(inst=inst, session=d, skip=skip, n_events=int((df.kind == 1).sum()) if df is not None and len(df) else 0)
            with open(log, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec) + "\n")
            print(json.dumps(rec), flush=True)


def verdict(I, lo, hi, mde, n_ev, scaled, spread):
    if lo is None or n_ev < MIN_EV:
        return "SIN_POTENCIA"
    if lo > 0:
        return "CONTRADICE"
    if hi < 0:
        return "REPLICA_ECONOMICA" if abs(I) >= spread else "REPLICA"
    return "NO_REPLICA" if mde <= abs(scaled) else "SIN_POTENCIA"


def step_report():
    from edgelab.edge_brain.episode_logger import measurement_episode
    res = {}
    for inst, cfg in INSTR.items():
        files = sorted((OUT / "rows" / inst).glob("*.parquet"))
        if not files:
            res[inst] = dict(verdict="SIN_DATOS")
            continue
        D = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
        used = sorted(D.session.unique())
        sidx = D.session.map({d: i for i, d in enumerate(used)}).to_numpy()
        W = S.boot_weights(len(used))
        kind = D.kind.to_numpy().astype(int)
        out = {}
        for tag, col in (("primario", "rd"), ("sensibilidad", "rd_sens")):
            inR = (D[col] <= cfg["win_t"]).to_numpy().astype(int)
            spread = float(D.spread0[(kind == 1) & (inR == 1)].median()) if ((kind == 1) & (inR == 1)).any() else float("nan")
            for h in HZ:
                st = S.cell_stats(sidx, D[f"sig{h}"].to_numpy(float), kind, inR, W, len(used))
                lo, hi, sd = S.ci(st["bI"])
                cell = dict(I=float(st["I"]), ci=[lo, hi], mde=(2.8 * sd if sd else None),
                            p=(erfc(abs(st["I"] / sd) / sqrt(2)) if sd else None),
                            R_solo=float(st["C_alone"]), R_solo_ci=S.ci(st["bC"])[:2],
                            abs_sola=float(st["A_alone"]), abs_sola_ci=S.ci(st["bA"])[:2],
                            n_ev_R=st["n_ev_in"], sess_ev_R=st["sess_ev_in"], spread_p50_R=spread)
                if tag == "primario" and h == 60:
                    cell["verdict"] = verdict(cell["I"], lo, hi, cell["mde"], st["n_ev_in"], cfg["nq_scaled"], spread)
                out[f"{tag}_{h}"] = cell
        res[inst] = dict(sessions=len(used), events=int((D.kind == 1).sum()), cells=out,
                         verdict=out["primario_60"]["verdict"])
    v = {k: r["verdict"] for k, r in res.items()}
    indep_ok = any(v.get(k, "").startswith("REPLICA") for k in ("GC", "6E"))
    contra = any(x == "CONTRADICE" for x in v.values())
    if indep_ok and not contra:
        fam = "PASA_A_CONFIRMACION_NQ"
    elif contra or all(x == "NO_REPLICA" for x in v.values()):
        fam = "MUERTA_EN_ALCANCE_DECLARADO"
    else:
        fam = "ESPERAR_MAS_L2" if sum(x == "SIN_POTENCIA" for x in v.values()) >= 2 else "NO_CONCLUYENTE"
    body = dict(schema="EDGELAB_VRND_REPLICA_V1", protocol=PROTO, code_commit=X._git("rev-parse", "HEAD"),
                tree_dirty=bool(X._git("status", "--porcelain", "--", "tools", "edgelab")),
                results=res, verdicts=v, family_decision=fam)
    raw = json.dumps(body, indent=1, default=float)
    (OUT / "report.json").write_text(raw, encoding="utf-8")
    sha = hashlib.sha256(raw.encode()).hexdigest()
    with measurement_episode(LEDGER, "EP-VRND-REPLICA-20260924", goal="V-RND réplica pre-registrada ES/GC/6E",
                             recorded_by="tools/vrnd_replicate.py report", repo=REPO, prereg_ref=PROTO) as ep:
        for inst, r in res.items():
            if "cells" in r:
                ep.store.record_observation(f"OBS-VRND-{inst}", f"V-RND réplica {inst}: absorción × redondo, sig60", "RESPONSE_PROFILE",
                                            [INSTR[inst]["part"]], dict(verdict=r["verdict"], primario_60=r["cells"]["primario_60"]),
                                            {"sessions": r["sessions"]}, sha, depends_on=["CODE:AbsorptionTracker@causal"])
    print(json.dumps(dict(verdicts=v, family=fam, sha=sha[:12])))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["declare", "run", "report"])
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args(argv)
    {"declare": step_declare, "run": lambda: step_run(a.workers), "report": step_report}[a.step]()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
