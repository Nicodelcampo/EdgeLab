#!/usr/bin/env python3
r"""MM-QI: provisión pasiva de liquidez filtrada por QI (manifiesto docs/research/MANIFIESTO_MM_QI_L2_20260924.md,
OK de Nico: "OK manifiesto MM-QI, adelante con todo").

Aclaración escrita antes de correr: en la variante "neutral" los dos lados califican con el mismo |QI|. El empate
se resuelve con un sorteo de semilla fija, para no sesgar hacia un lado.

Fill: `exec_qi.simulate_passive` (cola pesimista, validada como conservadora frente a NT8 en
PROTOCOLO_VALIDACION_EXEC_QI_NT8_20260924.md).

    .venv\Scripts\python tools\mm_qi.py declare
    .venv\Scripts\python tools\mm_qi.py run --workers 4
    .venv\Scripts\python tools\mm_qi.py report
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "tools"))

import numpy as np  # noqa: E402

import exec_qi as E  # noqa: E402
import nq_l2_explore as X  # noqa: E402

OUT = REPO / "artifacts" / "mm_qi"
LEDGER = REPO / "artifacts" / "hippocampus" / "mm_qi_20260924.jsonl"
MANIF = "docs/research/MANIFIESTO_MM_QI_L2_20260924.md"
US = X.US
T_IN = 30
T_OUTS = (30, 120)
BINS = ("contra", "neutral", "a_favor")
SCEN = {"base": dict(lat=250_000, frac=1.0), "lat1s": dict(lat=1_000_000, frac=1.0), "cola2x": dict(lat=250_000, frac=2.0)}
COMM_T = {"NQ": 0.5, "GC": 0.25, "ES": 0.2, "6E": 0.4}          # USD 2,50 por lado, en ticks
USD_T = {"NQ": 5.0, "GC": 10.0, "ES": 12.5, "6E": 6.25}
SEED, N_BOOT = 20260924, 2000


def run_config(arr, qi_at, t_start, t_end, halt, bin_name, t_out, lat, frac, rng):
    qts = arr[0]
    t = t_start
    attempts, trades = 0, []
    exits_passive = 0
    while t < t_end:
        if halt(t):
            t += US
            continue
        t0 = t + lat
        qi = qi_at(t0)
        cands = []
        for d in (1, -1):
            b = E.qi_bin(np.array([d * qi]))[0]
            if BINS[b] == bin_name:
                cands.append(d)
        if not cands:
            t += US
            continue
        d = cands[0] if len(cands) == 1 else int(rng.choice(cands))
        attempts += 1
        p_in, filled, t_fill = E.simulate_passive(*arr, t0, d, T_IN, frac)
        if not filled:
            t = t0 + T_IN * US + US
            continue
        t1 = t_fill + lat
        p_out, f_out, t_out_fill = E.simulate_passive(*arr, t1, -d, t_out, frac)
        exits_passive += f_out
        trades.append(d * (p_out - p_in))
        t_next = (t_out_fill if f_out else t1 + t_out * US) + US
        if t_next <= t:                                     # guardia: el reloj del simulador nunca retrocede
            raise RuntimeError(f"el simulador no avanza: t={t} t_next={t_next}")
        t = t_next
    return attempts, trades, exits_passive


def session(args):
    inst, day, base = args
    X.BASE = E.L2 / base
    Q, T = X.load_l1(day)
    if len(T) < 5000 or len(Q) < 5000 or not X.clock_ok(T.ts.to_numpy(), day):
        return inst, day, None
    arr = (Q.ts.to_numpy(), Q.bid.to_numpy(), Q.ask.to_numpy(), Q.bsz.to_numpy().astype(float), Q.asz.to_numpy().astype(float),
           T.ts.to_numpy(), T.px.to_numpy(), T.sz.to_numpy().astype(float), T.aggr.to_numpy())
    qts, bsz, asz = arr[0], arr[3], arr[4]

    def qi_at(t):
        j = max(np.searchsorted(qts, t, "right") - 1, 0)
        return float((bsz[j] - asz[j]) / max(bsz[j] + asz[j], 1))

    span = (T_IN + max(T_OUTS) + 10) * US
    halt = lambda t: X.in_halt(t - 60 * US, t + span)
    t_start, t_end = int(qts[0]) + 60 * US, int(qts[-1]) - span
    res = {}
    for sc, p in SCEN.items():
        for bn in BINS:
            for to in T_OUTS:
                rng = np.random.default_rng([SEED, int(day), ord(inst[0])])
                a, tr, ep = run_config(arr, qi_at, t_start, t_end, halt, bn, to, p["lat"], p["frac"], rng)
                tr = np.asarray(tr, float) - 2 * COMM_T[inst]
                res[f"{sc}|{bn}|{to}"] = dict(attempts=a, trades=len(tr), exits_passive=int(ep), pnl_sum=float(tr.sum()),
                                              pnl=[round(x, 2) for x in tr.tolist()])
    return inst, day, res


def step_declare():
    from edgelab.edge_brain.episode_logger import measurement_episode
    OUT.mkdir(parents=True, exist_ok=True)
    p = json.loads((REPO / "artifacts" / "exec_qi" / "plan.json").read_text(encoding="utf-8"))
    with measurement_episode(LEDGER, "EP-MMQI-DECLARE-20260924", goal="MM-QI: declarar particiones antes de medir",
                             recorded_by="tools/mm_qi.py declare", repo=REPO, prereg_ref=MANIF) as ep:
        for inst, ss in p.items():
            ep.store.record_partition(f"P-MMQI-{inst}", "EXPLORATION",
                                      f"MM-QI {inst}: mismas sesiones que P-EXECQI-{inst} (exploración; nada se confirma acá)",
                                      [f"MMQ-{inst}:{d}" for d, _ in ss])
    (OUT / "plan.json").write_text(json.dumps(p, indent=1), encoding="utf-8")
    print(json.dumps({k: len(v) for k, v in p.items()}))


def step_run(workers):
    p = json.loads((OUT / "plan.json").read_text(encoding="utf-8"))
    (OUT / "sessions").mkdir(parents=True, exist_ok=True)
    jobs = [(i, d, b) for i, ss in p.items() for d, b in ss if not (OUT / "sessions" / f"{i}_{d}.json").exists()]
    from concurrent.futures import as_completed
    with ProcessPoolExecutor(workers) as ex:                 # as_completed: una sesión lenta no bloquea a las demás
        futs = [ex.submit(session, j) for j in jobs]
        for fu in as_completed(futs):
            inst, day, res = fu.result()
            (OUT / "sessions" / f"{inst}_{day}.json").write_text(json.dumps(res), encoding="utf-8")
            print(inst, day, None if res is None else res["base|contra|30"]["trades"], flush=True)


def boot_per_attempt(S, A):
    ok = A > 0
    S, A = S[ok], A[ok]
    if len(S) < 5:
        return None
    r = np.random.default_rng(SEED)
    idx = r.integers(0, len(S), (N_BOOT, len(S)))
    b = S[idx].sum(1) / A[idx].sum(1)
    return [float(S.sum() / A.sum()), float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5)), int(len(S))]


def step_report():
    from edgelab.edge_brain.episode_logger import measurement_episode
    from edgelab.edge_brain.hippocampus import LessonCandidate
    p = json.loads((OUT / "plan.json").read_text(encoding="utf-8"))
    res, sug = {}, []
    for inst, ss in p.items():
        R = [json.loads((OUT / "sessions" / f"{inst}_{d}.json").read_text(encoding="utf-8")) for d, _ in ss]
        R = [r for r in R if r]
        cells = {}
        for bn in BINS:
            for to in T_OUTS:
                row = {}
                for sc in SCEN:
                    k = f"{sc}|{bn}|{to}"
                    S = np.array([r[k]["pnl_sum"] for r in R]); A = np.array([r[k]["attempts"] for r in R])
                    N = np.array([r[k]["trades"] for r in R])
                    allp = np.concatenate([np.asarray(r[k]["pnl"], float) for r in R]) if N.sum() else np.array([])
                    row[sc] = dict(por_intento=boot_per_attempt(S, A),
                                   por_trade=(float(allp.mean()) if len(allp) else None),
                                   trades_por_sesion=float(N.mean()), fill_entrada=float(N.sum() / max(A.sum(), 1)),
                                   salida_pasiva=float(sum(r[k]["exits_passive"] for r in R) / max(N.sum(), 1)),
                                   p5_p50_p95=(np.percentile(allp, [5, 50, 95]).round(2).tolist() if len(allp) else None),
                                   sesiones_positivas=float((S > 0).mean()),
                                   usd_por_sesion=float(S.mean() * USD_T[inst]), peor_sesion_usd=float(S.min() * USD_T[inst]))
                cells[f"{bn}_T{to}"] = row
                b, l1, c2 = row["base"]["por_intento"], row["lat1s"]["por_intento"], row["cola2x"]["por_intento"]
                if b and l1 and c2 and b[1] > 0 and l1[1] > 0 and c2[1] > 0 and row["base"]["sesiones_positivas"] >= 0.6:
                    sug.append(dict(inst=inst, variante=f"{bn}_T{to}", base=b, lat1s=l1, cola2x=c2))
        res[inst] = dict(sessions=len(R), cells=cells)
    body = dict(schema="EDGELAB_MM_QI_V1", manifest=MANIF, code_commit=X._git("rev-parse", "HEAD"),
                tree_dirty=bool(X._git("status", "--porcelain", "--", "tools", "edgelab")), results=res, suggestions=sug)
    raw = json.dumps(body, indent=1, default=float)
    (OUT / "report.json").write_text(raw, encoding="utf-8")
    sha = hashlib.sha256(raw.encode()).hexdigest()
    with measurement_episode(LEDGER, "EP-MMQI-20260924", goal="MM-QI: P&L neto de provisión pasiva filtrada por QI",
                             recorded_by="tools/mm_qi.py report", repo=REPO, prereg_ref=MANIF) as ep:
        for inst, r in res.items():
            ep.store.record_observation(f"OBS-MMQI-{inst}", f"MM-QI {inst}: P&L neto por intento, 6 variantes x 3 escenarios",
                                        "RESPONSE_PROFILE", [f"P-MMQI-{inst}"],
                                        {v: {s: c[s]["por_intento"] for s in c} for v, c in r["cells"].items()},
                                        {"sessions": r["sessions"]}, sha, design="OTHER")
        for s in sug:
            ep.store.record_lesson(LessonCandidate(
                lesson_id=f"SUG-MMQI-{s['inst']}-{s['variante']}", episode_id="EP-MMQI-20260924",
                statement=(f"MM-QI {s['inst']} {s['variante']}: {s['base'][0]:.2f} t/intento (IC {s['base'][1]:.2f}..{s['base'][2]:.2f}); "
                           f"se sostiene con latencia 1 s y cola x2. CONDICIONADO al modelo de fill: exige fills reales y P-NQL2-CONF."),
                confidence="LOW", status="PROPOSED", scope="SUGGESTED_ANALYSIS"))
    print(json.dumps(dict(suggestions=[(s["inst"], s["variante"]) for s in sug], sha=sha[:12])))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["declare", "run", "report", "one"])
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--inst"); ap.add_argument("--day"); ap.add_argument("--base")
    a = ap.parse_args(argv)
    if a.step == "one":
        import time
        t = time.time()
        _, _, r = session((a.inst, a.day, a.base))
        print(round(time.time() - t, 1), "s", {k: (v["attempts"], v["trades"], round(v["pnl_sum"], 1)) for k, v in r.items()})
        return 0
    {"declare": step_declare, "run": lambda: step_run(a.workers), "report": step_report}[a.step]()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
