#!/usr/bin/env python3
r"""EXEC-QI: costo de entrar pasivo vs agresivo, condicionado al desequilibrio del libro (QI).
Manifiesto con OK de Nico: docs/research/MANIFIESTO_EJECUCION_QI_L2_20260924.md ("OK manifiesto EXEC-QI").

Métrica (aclarada antes de correr, §4 del manifiesto):
- Las dos políticas terminan con la misma posición: P cruza al vencer T si no se llenó.
- Evaluadas a un horizonte común, la diferencia de P&L entre ellas es exactamente la diferencia de precio pagado.
- Por eso el ahorro por decisión es `d·(p_A − p_P)` en ticks, y la selección adversa ya está adentro: una orden
  pasiva que se llena antes de un movimiento en contra paga ese movimiento igual que la agresiva.
- El markout de 60 s de los fills pasivos se publica sólo como diagnóstico.

Reutilizable: INSTR/planes por instrumento. Cuando llegue L2 nuevo, se corre con otra partición y sin cambiar reglas.

    .venv\Scripts\python tools\exec_qi.py declare
    .venv\Scripts\python tools\exec_qi.py run --workers 4
    .venv\Scripts\python tools\exec_qi.py report
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

import nq_l2_explore as X  # noqa: E402

L2 = Path(r"E:\l2_parquet")
OUT = REPO / "artifacts" / "exec_qi"
LEDGER = REPO / "artifacts" / "hippocampus" / "exec_qi_20260924.jsonl"
MANIF = "docs/research/MANIFIESTO_EJECUCION_QI_L2_20260924.md"
US, LAT = X.US, X.LAT
TS = (5, 30, 120)
H_MARK = 60
QUEUES = {"pesimista": 1.0, "optimista": 0.5}
QI_CUT = 1 / 3                                   # cortes fijos sobre d·QI (lección de la exploración B)
SEED, N_BOOT = 20260924, 2000
MIN_SAVE = 0.5                                   # regla de sugerencia (ticks)


def qi_bin(x):
    return np.where(x <= -QI_CUT, 0, np.where(x >= QI_CUT, 2, 1))   # 0 contra, 1 neutral, 2 a favor


def block(sod):
    h = sod / 3600.0
    return np.select([(h >= 10.5) & (h < 11.5), (h >= 11.5) & (h < 16), (h >= 16) & (h < 18), (h >= 4) & (h < 10.5)],
                     [1, 2, 3, 4], 0)                                 # 0 Asia, 1 apertura, 2 RTH, 3 cierre, 4 Europa (ART)


def plans():
    vr = json.loads((REPO / "artifacts" / "vrnd_replica" / "plan.json").read_text(encoding="utf-8"))
    out = {k: [(d, b) for d, b in v["sessions"]] for k, v in vr.items()}
    nq_log = [json.loads(x) for x in (REPO / "artifacts" / "nq_l2_synergy_C" / "run_log.jsonl").read_text(encoding="utf-8").splitlines()]
    out["NQ"] = [(r["session"], "NQ_09-26") for r in nq_log if not r.get("skip")]
    return out


def simulate_passive(qts, bid, ask, bsz, asz, tts, tpx, tsz, tag, t0, d, T_s, frac):
    """Una orden límite en el mejor precio propio puesta en t0 (ya con latencia), con la misma regla que `session`:
    cola = tamaño visible × frac + 1, sin avance por cancelaciones; llena si el volumen agresivo contrario en ese
    precio supera la cola o si hay un trade que atraviesa el precio. Si no se llena en T_s, cruza al precio contrario.
    Devuelve (precio, lleno, t_fill_us)."""
    j = max(np.searchsorted(qts, t0, "right") - 1, 0)
    L, q0 = (bid[j], bsz[j]) if d == 1 else (ask[j], asz[j])
    a, b = np.searchsorted(tts, t0, "right"), np.searchsorted(tts, t0 + T_s * US, "right")
    px, sz, ag, ts = tpx[a:b], tsz[a:b], tag[a:b], tts[a:b]
    through = (px < L) if d == 1 else (px > L)
    hit = (px == L) & (ag == (-1 if d == 1 else 1))
    ok = through | (np.cumsum(np.where(hit, sz, 0.0)) >= q0 * frac + 1)
    if ok.any():
        return float(L), 1, int(ts[int(np.argmax(ok))])
    jT = max(np.searchsorted(qts, t0 + T_s * US, "right") - 1, 0)
    return float(ask[jT] if d == 1 else bid[jT]), 0, None


def session(args):
    inst, day, base = args
    X.BASE = L2 / base
    Q, T = X.load_l1(day)
    if len(T) < 5000 or len(Q) < 5000 or not X.clock_ok(T.ts.to_numpy(), day):
        return inst, day, "SKIP", None
    qts, bid, ask = Q.ts.to_numpy(), Q.bid.to_numpy(), Q.ask.to_numpy()
    bsz, asz = Q.bsz.to_numpy().astype(float), Q.asz.to_numpy().astype(float)
    mid = (bid + ask) / 2.0
    tts, tpx, tsz, tag = T.ts.to_numpy(), T.px.to_numpy(), T.sz.to_numpy().astype(float), T.aggr.to_numpy()
    last = int(qts[-1])
    H = max(TS) + H_MARK
    grid = np.arange(int(qts[0]) + 60 * US, last - H * US, US)
    grid = grid[[not X.in_halt(g - 60 * US, g + H * US) for g in grid]]
    t0 = grid + LAT
    j0 = np.maximum(np.searchsorted(qts, t0, "right") - 1, 0)
    qi = (bsz[j0] - asz[j0]) / np.maximum(bsz[j0] + asz[j0], 1)
    blk = block((grid // US) % 86400)
    lo = np.searchsorted(tts, t0, "right")
    hi = np.searchsorted(tts, t0 + max(TS) * US, "right")
    # acumuladores: [dir(2), qi(3), T(3), cola(2), bloque(5)] -> suma de ahorro, n, n_fill, suma markout
    shp = (2, 3, len(TS), len(QUEUES), 5)
    acc = {k: np.zeros(shp) for k in ("save", "n", "fill", "mark")}
    qkeys = list(QUEUES.values())
    for di, d in enumerate((1, -1)):
        m0 = mid[j0]
        pA = np.where(d == 1, ask[j0], bid[j0])
        lvl = np.where(d == 1, bid[j0], ask[j0])
        q0 = np.where(d == 1, bsz[j0], asz[j0])
        qb = qi_bin(d * qi)
        for i in range(len(grid)):
            a, b = lo[i], hi[i]
            px, sz, ag, ts = tpx[a:b], tsz[a:b], tag[a:b], tts[a:b]
            L = lvl[i]
            if d == 1:
                through = px < L
                hit = (px == L) & (ag == -1)
            else:
                through = px > L
                hit = (px == L) & (ag == 1)
            cum = np.cumsum(np.where(hit, sz, 0.0))
            for qk, frac in enumerate(qkeys):
                need = q0[i] * frac + 1
                ok = through | (cum >= need)
                k = int(np.argmax(ok)) if ok.any() else -1
                tf = ts[k] if k >= 0 else None
                for ti, Tm in enumerate(TS):
                    if tf is not None and tf <= t0[i] + Tm * US:
                        pP, filled = L, 1
                        jm = max(np.searchsorted(qts, tf + H_MARK * US, "right") - 1, 0)
                        mark = d * (mid[jm] - pP)
                    else:
                        jT = max(np.searchsorted(qts, t0[i] + Tm * US, "right") - 1, 0)
                        pP, filled, mark = (ask[jT] if d == 1 else bid[jT]), 0, 0.0
                    idx = (di, qb[i], ti, qk, blk[i])
                    acc["save"][idx] += d * (pA[i] - pP)
                    acc["n"][idx] += 1
                    acc["fill"][idx] += filled
                    acc["mark"][idx] += mark
        _ = m0
    spread = float(np.median(ask[j0] - bid[j0]))
    return inst, day, None, dict(spread_p50=spread, n_grid=int(len(grid)), **{k: v.tolist() for k, v in acc.items()})


def step_declare():
    from edgelab.edge_brain.episode_logger import measurement_episode
    OUT.mkdir(parents=True, exist_ok=True)
    p = plans()
    with measurement_episode(LEDGER, "EP-EXECQI-DECLARE-20260924", goal="EXEC-QI: declarar particiones antes de medir",
                             recorded_by="tools/exec_qi.py declare", repo=REPO, prereg_ref=MANIF) as ep:
        for inst, ss in p.items():
            ep.store.record_partition(f"P-EXECQI-{inst}", "EXPLORATION",
                                      f"EXEC-QI {inst}: mismas sesiones que P-NQL2-EXP / P-VRND-{inst} (exploración ya mirada; nada se confirma acá)",
                                      [f"EXQ-{inst}:{d}" for d, _ in ss])
    (OUT / "plan.json").write_text(json.dumps(p, indent=1), encoding="utf-8")
    print(json.dumps({k: len(v) for k, v in p.items()}))


def step_run(workers):
    p = json.loads((OUT / "plan.json").read_text(encoding="utf-8"))
    (OUT / "sessions").mkdir(parents=True, exist_ok=True)
    jobs = [(i, d, b) for i, ss in p.items() for d, b in ss if not (OUT / "sessions" / f"{i}_{d}.json").exists()]
    with ProcessPoolExecutor(workers) as ex:
        for inst, day, skip, res in ex.map(session, jobs):
            (OUT / "sessions" / f"{inst}_{day}.json").write_text(json.dumps(dict(skip=skip, **(res or {}))), encoding="utf-8")
            print(inst, day, skip or res["n_grid"], flush=True)


def boot(S, N):
    """Media agrupada por sesión (S, N: vectores por sesión) con IC bootstrap por sesión."""
    ok = N > 0
    S, N = S[ok], N[ok]
    if len(S) < 5:
        return None
    r = np.random.default_rng(SEED)
    idx = r.integers(0, len(S), (N_BOOT, len(S)))
    b = S[idx].sum(1) / N[idx].sum(1)
    return [float(S.sum() / N.sum()), float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5)), int(len(S))]


def step_report(tag="", record=None):
    from edgelab.edge_brain.episode_logger import measurement_episode
    p = json.loads((OUT / "plan.json").read_text(encoding="utf-8"))
    qnames, qib = list(QUEUES), ["contra", "neutral", "a_favor"]
    res, sug = {}, []
    for inst, ss in p.items():
        R = [json.loads((OUT / "sessions" / f"{inst}_{d}.json").read_text(encoding="utf-8")) for d, _ in ss
             if (OUT / "sessions" / f"{inst}_{d}.json").exists()]
        R = [r for r in R if not r.get("skip")]
        if not R:
            continue
        A = {k: np.array([r[k] for r in R]) for k in ("save", "n", "fill", "mark")}   # [ses, dir, qi, T, cola, bloque]
        spread = float(np.median([r["spread_p50"] for r in R]))
        cells = {}
        for qk, qn in enumerate(qnames):
            for ti, Tm in enumerate(TS):
                row = {}
                for b, bn in enumerate(qib + ["todos"]):
                    sl = (slice(None), slice(None), (slice(None) if bn == "todos" else b), ti, qk, slice(None))
                    s_ = A["save"][sl].reshape(len(R), -1).sum(1)
                    n_ = A["n"][sl].reshape(len(R), -1).sum(1)
                    f_ = A["fill"][sl].reshape(len(R), -1).sum(1)
                    m_ = A["mark"][sl].reshape(len(R), -1).sum(1)
                    row[bn] = dict(ahorro=boot(s_, n_), fill_rate=float(f_.sum() / max(n_.sum(), 1)),
                                   markout60_fills=(float(m_.sum() / f_.sum()) if f_.sum() else None))
                    c = row[bn]["ahorro"]
                    if qn == "pesimista" and bn != "todos" and c and c[1] > 0 and c[0] >= MIN_SAVE:
                        # la regla exige que el supuesto optimista también lo sostenga
                        so = A["save"][(slice(None), slice(None), b, ti, 1, slice(None))].reshape(len(R), -1).sum(1)
                        no = A["n"][(slice(None), slice(None), b, ti, 1, slice(None))].reshape(len(R), -1).sum(1)
                        co = boot(so, no)
                        if co and co[1] > 0 and co[0] >= MIN_SAVE:
                            sug.append(dict(inst=inst, qi=bn, T=Tm, ahorro_pes=c, ahorro_opt=co))
                cells[f"{qn}_T{Tm}"] = row
        # por bloque horario, sólo descriptivo (pesimista, T=30, todos los QI)
        by_block = {}
        for bi, bnm in enumerate(["Asia", "apertura", "RTH", "cierre", "Europa"]):
            sl = (slice(None), slice(None), slice(None), 1, 0, bi)
            by_block[bnm] = boot(A["save"][sl].reshape(len(R), -1).sum(1), A["n"][sl].reshape(len(R), -1).sum(1))
        res[inst] = dict(sessions=len(R), spread_p50=spread, cells=cells, by_block_pes_T30=by_block)
    body = dict(schema="EDGELAB_EXEC_QI_V1", manifest=MANIF, code_commit=X._git("rev-parse", "HEAD"),
                tree_dirty=bool(X._git("status", "--porcelain", "--", "tools", "edgelab")), results=res, suggestions=sug)
    raw = json.dumps(body, indent=1, default=float)
    (OUT / "report.json").write_text(raw, encoding="utf-8")
    sha = hashlib.sha256(raw.encode()).hexdigest()
    from edgelab.edge_brain.hippocampus import LessonCandidate
    with measurement_episode(LEDGER, f"EP-EXECQI-20260924{tag}", goal="EXEC-QI: costo pasivo vs agresivo según QI",
                             recorded_by="tools/exec_qi.py report", repo=REPO, prereg_ref=MANIF) as ep:
        for inst, r in res.items():
            if record and inst not in record:
                continue
            ep.store.record_observation(f"OBS-EXECQI-{inst}{tag}", f"ahorro pasivo vs agresivo por QI, {inst}", "RESPONSE_PROFILE",
                                        [f"P-EXECQI-{inst}"], {k: {q: v["ahorro"] for q, v in row.items()} for k, row in r["cells"].items()},
                                        {"sessions": r["sessions"], "spread_p50": r["spread_p50"]}, sha, design="OTHER")
        for i, s in enumerate(sug):
            if record and s["inst"] not in record:
                continue
            ep.store.record_lesson(LessonCandidate(
                lesson_id=f"SUG-EXECQI-{s['inst']}-{s['qi']}-T{s['T']}{tag}", episode_id=f"EP-EXECQI-20260924{tag}",
                statement=(f"{s['inst']}: entrar pasivo con QI {s['qi']} y T={s['T']}s ahorra {s['ahorro_pes'][0]:.2f} ticks "
                           f"(pesimista, IC {s['ahorro_pes'][1]:.2f}..{s['ahorro_pes'][2]:.2f}). Confirmar en P-NQL2-CONF / holdout L2 y en sim NT8."),
                confidence="LOW", status="PROPOSED", scope="SUGGESTED_ANALYSIS"))
    print(json.dumps(dict(instruments=list(res), suggestions=len(sug), sha=sha[:12])))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["declare", "run", "report", "one"])
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--inst"); ap.add_argument("--day"); ap.add_argument("--base")
    ap.add_argument("--tag", default=""); ap.add_argument("--record", nargs="*")
    a = ap.parse_args(argv)
    if a.step == "one":
        import time
        t = time.time()
        r = session((a.inst, a.day, a.base))
        print(r[2], r[3]["n_grid"] if r[3] else None, round(time.time() - t, 1), "s")
        return 0
    {"declare": step_declare, "run": lambda: step_run(a.workers), "report": lambda: step_report(a.tag, a.record)}[a.step]()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
