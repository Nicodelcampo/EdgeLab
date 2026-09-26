#!/usr/bin/env python3
r"""Exploración L2 de NQ (manifiesto docs/research/MANIFIESTO_NQ_L2_EXPLORACION_20260924.md, OK de Nico 2026-09-24).

Pasos:
  declare   particiones P-NQL2-EXP / P-NQL2-CONF en el ledger propio, ANTES de calcular nada
  run       familias A (absorción) y B (desequilibrio de filas), SOLO sesiones de P-NQL2-EXP
  report    agrega, aplica las reglas de sugerencia (fijas en este archivo) y registra observaciones

Target: descriptivo. Ninguna prueba de P&L. La reserva no se lee.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402

from edgelab.research.l2_manipulation_heuristics import ASK, AbsorptionTracker  # noqa: E402

BASE = Path(r"E:\l2_parquet\NQ_09-26")
QA = REPO / "artifacts" / "l2_phase0" / "NQ_NQ_09-26" / "qa.jsonl"
OUT = REPO / "artifacts" / "nq_l2"
LEDGER = REPO / "artifacts" / "hippocampus" / "nq_l2_20260924.jsonl"
MANIF = "docs/research/MANIFIESTO_NQ_L2_EXPLORACION_20260924.md"
EXP_RANGE, CONF_RANGE = ("20260701", "20260821"), ("20260824", "20261031")
US = 1_000_000
ART = 3 * 3600 * US
LAT = 250_000
HORIZONS = (10, 30, 60, 300)
QI_H = (1, 10, 60)
N_CTRL, CTRL_SPAN_S, EXCL_S = 5, 1800, 60
SEED, N_BOOT = 20260924, 5000
TICK = 0.25


def _git(*a):
    return subprocess.run(["git", *a], cwd=REPO, capture_output=True, text=True).stdout.strip()


def sessions_in(rng):
    return sorted(p.stem for p in (BASE / "l2_depth").glob("*.parquet") if rng[0] <= p.stem <= rng[1])


def clock_ok(tr_ts_us, day):
    """P-84: la pausa diaria (18:00-19:00 del reloj crudo ART) vacía de trades de lunes a jueves; domingo abre a las 19:00.
    Además (24/09, P-92): los timestamps de los trades en orden de archivo tienen que ser monótonos. ES 09-26 del 21/08
    (NRD parcial, cortado a las 11:57) traía 31.553 retrocesos de hasta 9 s. Con timestamps desordenados, `searchsorted`
    devuelve basura y un simulador por eventos puede no avanzar nunca (así se colgó MM-QI)."""
    if len(tr_ts_us) > 1 and bool((np.diff(np.asarray(tr_ts_us)) < 0).any()):
        return False
    wd = pd.Timestamp(day).dayofweek
    sod_min = (tr_ts_us // 60_000_000) % 1440
    if wd <= 3:
        return int(((sod_min >= 18 * 60 + 2) & (sod_min < 19 * 60 - 2)).sum()) <= 5
    return True


def usable(day):
    if not QA.exists():
        return None
    for line in QA.read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        if str(r.get("session")) == day:
            return bool(r.get("usable"))
    return None


def load_l1(day):
    t = pq.read_table(BASE / "l1_quotes" / f"{day}.parquet", columns=["side", "price_tick", "size", "ts_us", "source_row"]) \
        .to_pandas().sort_values("source_row", kind="stable")
    t = t[t.side <= 2]
    ask = t.price_tick.where(t.side == 0).ffill()
    bid = t.price_tick.where(t.side == 1).ffill()
    asz = t["size"].where(t.side == 0).ffill()
    bsz = t["size"].where(t.side == 1).ffill()
    q = t.side < 2
    Q = pd.DataFrame(dict(ts=t.ts_us[q], bid=bid[q], ask=ask[q], bsz=bsz[q], asz=asz[q])).dropna()
    Q = Q[Q.ask > Q.bid]
    tr = t.side == 2
    pa, pb = ask.shift(1)[tr], bid.shift(1)[tr]              # cotización vigente ANTES del trade
    px = t.price_tick[tr]
    agg = np.where(px >= pa, 1, np.where(px <= pb, -1, 0))
    T = pd.DataFrame(dict(ts=t.ts_us[tr], px=px, sz=t["size"][tr], aggr=agg))
    return Q.reset_index(drop=True), T.reset_index(drop=True)


def absorption_events(T):
    ab = AbsorptionTracker()
    for p, ts, sz, a in zip(T.px.to_numpy(), T.ts.to_numpy(), T.sz.to_numpy(), T.aggr.to_numpy()):
        ab.on_trade(int(p), int(ts), float(sz), int(a))
    return sorted(ab.candidates(), key=lambda c: c["available_ts_us"])


def in_halt(t0, t1):
    a, b = (t0 // US) % 86400, (t1 // US) % 86400
    return (a < 19 * 3600 and b >= 18 * 3600) if a <= b else True


def mid_at(Q, t):
    j = np.searchsorted(Q.ts.to_numpy(), t, side="right") - 1
    j = np.clip(j, 0, None)
    return (Q.bid.to_numpy()[j] + Q.ask.to_numpy()[j]) / 2.0


def touch_at(Q, t, dirn):
    j = np.searchsorted(Q.ts.to_numpy(), t, side="right") - 1
    if j < 0:
        return None
    return Q.ask.to_numpy()[j] if dirn == -1 else Q.bid.to_numpy()[j]


def response(Q, T, t0, dirn, level, last):
    if t0 + max(HORIZONS) * US > last or in_halt(t0 - 60 * US, t0 + max(HORIZONS) * US):
        return None
    m0 = float(mid_at(Q, t0))
    tts, tpx = T.ts.to_numpy(), T.px.to_numpy()
    out = {}
    for h in HORIZONS:
        mh = float(mid_at(Q, t0 + h * US))
        out[f"fade{h}"] = dirn * (mh - m0)
        out[f"abs{h}"] = abs(mh - m0)
        lo, hi = np.searchsorted(tts, t0, "right"), np.searchsorted(tts, t0 + h * US, "right")
        px = tpx[lo:hi]
        out[f"break{h}"] = float(len(px) > 0 and ((px.max() > level) if dirn == -1 else (px.min() < level)))
    return out


def vol60(T, t):
    tts = T.ts.to_numpy()
    lo, hi = np.searchsorted(tts, t - 60 * US), np.searchsorted(tts, t)
    return float(T.sz.to_numpy()[lo:hi].sum())


def family_a(day, Q, T, rng):
    ev = absorption_events(T)
    last = int(Q.ts.iloc[-1])
    evt = np.array([e["available_ts_us"] for e in ev]) if ev else np.array([])
    # terciles de actividad de la sesión (volumen 60 s), en una grilla de 30 s: target-free
    grid = np.arange(int(Q.ts.iloc[0]) + 60 * US, last, 30 * US)
    vg = np.array([vol60(T, g) for g in grid]) if len(grid) else np.array([0.0])
    q1, q2 = np.percentile(vg, [33.3, 66.7])
    terc = lambda v: 0 if v <= q1 else (1 if v <= q2 else 2)
    rows_e, rows_c = [], []
    for e in ev:
        dirn = -1 if e["side"] == ASK else 1
        t0 = e["available_ts_us"] + LAT
        tch = touch_at(Q, t0, dirn)
        if tch is None:
            continue
        dist = (e["tick"] - tch) if dirn == -1 else (tch - e["tick"])
        r = response(Q, T, t0, dirn, e["tick"], last)
        if r is None:
            continue
        te = terc(vol60(T, t0))
        rows_e.append(r)
        got = 0
        for _ in range(80 * N_CTRL):
            if got >= N_CTRL:
                break
            tc = int(t0 + rng.integers(-CTRL_SPAN_S, CTRL_SPAN_S) * US)
            if len(evt) and np.min(np.abs(evt - tc)) < EXCL_S * US:
                continue
            if terc(vol60(T, tc)) != te:
                continue
            tt = touch_at(Q, tc, dirn)
            if tt is None:
                continue
            rc = response(Q, T, tc, dirn, tt + dist if dirn == -1 else tt - dist, last)
            if rc is None:
                continue
            rows_c.append(rc); got += 1
    diff = {}
    for h in HORIZONS:
        for k in ("fade", "abs", "break"):
            me = np.nanmean([x[f"{k}{h}"] for x in rows_e]) if rows_e else np.nan
            mc = np.nanmean([x[f"{k}{h}"] for x in rows_c]) if rows_c else np.nan
            diff[f"{k}{h}"] = float(me - mc) if np.isfinite(me) and np.isfinite(mc) else None
    return dict(n_events=len(rows_e), n_controls=len(rows_c), diff=diff,
                event_mean={f"{k}{h}": (float(np.nanmean([x[f"{k}{h}"] for x in rows_e])) if rows_e else None)
                            for h in HORIZONS for k in ("fade", "abs", "break")})


def family_b(day, Q):
    """QI en una grilla de 1 s fuera de la pausa. Respuesta: próximo cambio del medio (dirección) y movimiento a 1/10/60 s."""
    ts = Q.ts.to_numpy()
    grid = np.arange(ts[0] + 60 * US, ts[-1] - 60 * US, US)
    grid = grid[[not in_halt(g, g + 60 * US) for g in grid]]
    j = np.searchsorted(ts, grid, side="right") - 1
    bsz, asz = Q.bsz.to_numpy()[j], Q.asz.to_numpy()[j]
    qi = (bsz - asz) / np.maximum(bsz + asz, 1)
    mid = (Q.bid.to_numpy() + Q.ask.to_numpy()) / 2.0
    m0 = mid[j]
    # próximo cambio del medio
    chg = np.flatnonzero(np.diff(mid) != 0) + 1
    k = np.searchsorted(chg, j + 1)
    nxt = np.where(k < len(chg), mid[chg[np.minimum(k, len(chg) - 1)]] - m0, 0.0)
    nxt_t = np.where(k < len(chg), ts[chg[np.minimum(k, len(chg) - 1)]] - grid, np.inf)
    up = np.where(nxt_t <= 60 * US, np.sign(nxt), 0.0)
    res = dict(n=int(len(grid)), qi=qi.astype(np.float32).tolist(), up=up.astype(np.int8).tolist())
    for h in QI_H:
        jh = np.searchsorted(ts, grid + h * US, side="right") - 1
        res[f"mv{h}"] = (mid[jh] - m0).astype(np.float32).tolist()
    return res


def boot_ci(x):
    x = np.asarray([v for v in x if v is not None and np.isfinite(v)], float)
    if len(x) < 3:
        return None
    r = np.random.default_rng(SEED)
    bs = x[r.integers(0, len(x), (N_BOOT, len(x)))].mean(1)
    return [float(x.mean()), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5)), int(len(x))]


def step_declare():
    from edgelab.edge_brain.episode_logger import measurement_episode
    exp = [f"NQ:{d}" for d in sessions_in(EXP_RANGE)]
    conf = [f"NQ:{d}" for d in sessions_in(CONF_RANGE)] + [f"NQ:future:{m}" for m in ("202610",)]
    with measurement_episode(LEDGER, "EP-NQL2-DECLARE-20260924", goal="NQ L2: declarar particiones antes de medir",
                             recorded_by="tools/nq_l2_explore.py declare", repo=REPO, prereg_ref=MANIF) as ep:
        ep.store.record_partition("P-NQL2-EXP", "EXPLORATION", "NQ L2 dev 2026-07-01..2026-08-21", exp)
        ep.store.record_partition("P-NQL2-CONF", "CONFIRMATION_RESERVED", "NQ L2 dev 2026-08-24..2026-10-31 (oct se agrega al bajarse)", conf)
    print(json.dumps(dict(exp=len(exp), conf=len(conf))))


def step_run():
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / "sessions.jsonl"
    done = {json.loads(x)["session"] for x in out.read_text(encoding="utf-8").splitlines()} if out.exists() else set()
    rng = np.random.default_rng(SEED)
    for day in sessions_in(EXP_RANGE):
        if day in done:
            continue
        rec = dict(session=day)
        u = usable(day)
        Q, T = load_l1(day)
        if len(T) < 5000 or len(Q) < 5000:
            rec["skip"] = "POCA_ACTIVIDAD"
        elif u is False:
            rec["skip"] = "DEFECT_PHASE0"
        elif not clock_ok(T.ts.to_numpy(), day):
            rec["skip"] = "CLOCK_UNCERTIFIED_P84"
        else:
            rec["usable_phase0"] = u
            rec["A"] = family_a(day, Q, T, rng)
            rec["B"] = family_b(day, Q)
        with open(out, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
        print(json.dumps({k: v for k, v in rec.items() if k != "B"} | ({"B_n": rec["B"]["n"]} if "B" in rec else {}))[:300], flush=True)


def step_report():
    from edgelab.edge_brain.episode_logger import measurement_episode
    from edgelab.edge_brain.hippocampus import LessonCandidate
    rows = [json.loads(x) for x in (OUT / "sessions.jsonl").read_text(encoding="utf-8").splitlines()]
    ok = [r for r in rows if "A" in r and usable(r["session"]) is not False]   # QA de Fase 0 aplicada al reportar
    A = {}
    for h in HORIZONS:
        for k in ("fade", "abs", "break"):
            A[f"{k}{h}"] = boot_ci([r["A"]["diff"][f"{k}{h}"] for r in ok])
    # B: deciles con cortes del conjunto de exploración; efecto por sesión = decil alto - decil bajo
    allqi = np.concatenate([np.asarray(r["B"]["qi"]) for r in ok])
    cuts = np.percentile(allqi, np.arange(10, 100, 10))
    B = {"cuts": cuts.tolist()}
    per_dec = {m: np.zeros((len(ok), 10)) for m in ["up"] + [f"mv{h}" for h in QI_H]}
    for i, r in enumerate(ok):
        qi = np.asarray(r["B"]["qi"]); d = np.searchsorted(cuts, qi, side="right")
        for m in per_dec:
            v = np.asarray(r["B"][m], float)
            for dd in range(10):
                sel = d == dd
                per_dec[m][i, dd] = v[sel].mean() if sel.any() else np.nan
    for m, arr in per_dec.items():
        B[m] = dict(by_decile=np.nanmean(arr, 0).tolist(), top_minus_bottom=boot_ci((arr[:, 9] - arr[:, 0]).tolist()))
    sug = []
    for h in HORIZONS:
        c = A[f"fade{h}"]
        if c and (c[1] > 0 or c[2] < 0):
            sug.append((f"SUG-NQ-ABS-FADE-{h}", f"Absorción NQ: fade {h}s con IC {c[1]:.2f}..{c[2]:.2f} (en ticks x4 = puntos/0.25). Comparar contra ~4,6 ticks de spread RTH."))
        c = A[f"break{h}"]
        if c and c[2] < 0:
            sug.append((f"SUG-NQ-ABS-BARRIER-{h}", f"Absorción NQ: menos ruptura que un control a igual distancia y actividad a {h}s (IC {c[1]:.3f}..{c[2]:.3f})."))
    for m in ("up", "mv10", "mv60"):
        c = B[m]["top_minus_bottom"]
        if c and (c[1] > 0 or c[2] < 0):
            sug.append((f"SUG-NQ-QI-{m.upper()}", f"QI NQ: decil alto - bajo en {m} con IC {c[1]:.3f}..{c[2]:.3f}."))
    body = dict(schema="EDGELAB_NQ_L2_EXPLORE_V1", manifest=MANIF, code_commit=_git("rev-parse", "HEAD"),
                tree_dirty=bool(_git("status", "--porcelain", "--", "tools", "edgelab")),
                sessions_used=[r["session"] for r in ok], skipped=[(r["session"], r.get("skip")) for r in rows if "A" not in r],
                A_session_diff_ci=A, B=B, suggestions=[dict(id=i, text=t, confirm_on="P-NQL2-CONF") for i, t in sug])
    raw = json.dumps(body, indent=1, default=float)
    (OUT / "report.json").write_text(raw, encoding="utf-8")
    sha = hashlib.sha256(raw.encode()).hexdigest()
    dep = ["CODE:AbsorptionTracker@causal", "DATA:l2_parquet/NQ_09-26"]
    with measurement_episode(LEDGER, "EP-NQL2-EXPLORE-20260924", goal="NQ L2 exploración A+B", recorded_by="tools/nq_l2_explore.py report",
                             repo=REPO, prereg_ref=MANIF) as ep:
        ep.store.record_observation("OBS-NQL2-A", "absorción NQ vs control igual distancia+actividad", "RESPONSE_PROFILE", ["P-NQL2-EXP"],
                                    {k: v for k, v in A.items()}, {"sessions": len(ok)}, sha, depends_on=dep,
                                    design="EVENT_VS_CONTROL")   # controles en +-30 min: el Brain lo rechaza (LES-CTRL-TIMING)
        ep.store.record_observation("OBS-NQL2-B", "desequilibrio de filas NQ", "RESPONSE_PROFILE", ["P-NQL2-EXP"],
                                    {m: B[m]["top_minus_bottom"] for m in ("up", "mv1", "mv10", "mv60")}, {"sessions": len(ok)}, sha, depends_on=dep,
                                    design="NO_CONTROL")
        for i, t in sug:
            ep.store.record_lesson(LessonCandidate(lesson_id=i, episode_id="EP-NQL2-EXPLORE-20260924", statement=t + " Confirmar SOLO en P-NQL2-CONF.",
                                                   confidence="LOW", status="PROPOSED", scope="SUGGESTED_ANALYSIS"))
    print(json.dumps(dict(sessions=len(ok), suggestions=[i for i, _ in sug], sha=sha[:12])))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["declare", "run", "report"])
    a = ap.parse_args(argv)
    dict(declare=step_declare, run=step_run, report=step_report)[a.step]()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
