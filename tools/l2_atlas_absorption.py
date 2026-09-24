#!/usr/bin/env python3
r"""Atlas L2 — primer lote: absorción en GC 08-26 pre-holdout (docs/research/ATLAS_CAPA_DESCRIPTIVA_20260924.md).

NO es una prueba: no promueve ni descarta. Produce OBSERVACIONES descriptivas y SUGERENCIAS de análisis.
  - Target-free (30 sesiones): frecuencia, agrupamiento, repetición de nivel, estado del libro, co-ocurrencia con
    icebergs, contra la distribución incondicional o controles.
  - Perfil de respuesta (SOLO partición EXPLORATION, 15 primeras sesiones): movimiento en dirección fade a
    10/30/60/300 s, |movimiento|, MFE/MAE 300 s y ruptura del nivel, contra controles emparejados.
Registra en el Edge Brain (`artifacts/hippocampus/atlas_l2_20260924.jsonl`): particiones (antes de mirar retornos),
observaciones DESCRIPTIVE con dependencias, y sugerencias PROPOSED/LOW con la partición donde deben confirmarse.

    .venv\Scripts\python tools\l2_atlas_absorption.py
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import numpy as np  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402

from edgelab.research.holdout_guard import HOLDOUT_START_ISO  # noqa: E402
from edgelab.research.l2_manipulation_heuristics import ASK, AbsorptionTracker, IcebergTracker, large_size_thresholds  # noqa: E402
from edgelab.research.l2_phase0 import apply_event, defect_reasons, process_session  # noqa: E402
from tools.build_l2_viewer_bundle import DEFAULT_ICEBERG_KWARGS, ICEBERG_MIN_AVG_SIZE_PCTL  # noqa: E402

BASE = Path(r"E:\DatosNT8\gc_aug26_canonical_parquets")
OUT = REPO / "artifacts" / "l2_atlas"
LEDGER = REPO / "artifacts" / "hippocampus" / "atlas_l2_20260924.jsonl"
US = 1_000_000
LAT = 250_000
HORIZONS = (10, 30, 60, 300)
HALT_ART = (18 * 3600, 19 * 3600)
N_CTRL = 5
CTRL_SPAN_S = 1800
EXCL_S = 60
SEED = 20260924
N_BOOT = 5000
HOLDOUT_YMD = int(HOLDOUT_START_ISO[:10].replace("-", ""))


def _git(*a):
    return subprocess.run(["git", *a], cwd=REPO, capture_output=True, text=True).stdout.strip()


def _sod(ts_us):
    return (np.asarray(ts_us) // US) % 86400


def _in_halt(t0_us, t1_us):
    """True si [t0,t1] toca la pausa CME (reloj de pared ART), sin cruzar medianoche."""
    a, b = _sod(t0_us), _sod(t1_us)
    return (a < HALT_ART[1]) & (b >= HALT_ART[0]) & (a <= b) | (a > b) & ((a < HALT_ART[1]) | (b >= HALT_ART[0]))


def load_session(s):
    l1 = pq.read_table(BASE / "l1_quotes" / f"{s}.parquet", columns=["side", "price_tick", "size", "ts_us", "source_row"]).to_pandas()
    l2 = pq.read_table(BASE / "l2_depth" / f"{s}.parquet", columns=["side", "operation", "level", "price_tick", "size", "ts_us", "source_row"]).to_pandas()
    return l1.sort_values("source_row", kind="stable"), l2.sort_values("source_row", kind="stable")


def quotes_trades_absorption(l1):
    """Cotizaciones forward-filled, trades y absorciones CAUSALES con agresor por regla de cotización."""
    ab = AbsorptionTracker()
    bid = ask = None
    qt, qb, qa, tt, tp, ts_ = [], [], [], [], [], []
    for sd, p, z, t in zip(l1.side.to_numpy(), l1.price_tick.to_numpy(), l1["size"].to_numpy(), l1.ts_us.to_numpy()):
        if sd == 0:
            ask = int(p)
        elif sd == 1:
            bid = int(p)
        elif sd == 2:
            agg = 1 if (ask is not None and p >= ask) else (-1 if (bid is not None and p <= bid) else 0)
            ab.on_trade(int(p), int(t), float(z), agg)
            tt.append(int(t)); tp.append(int(p)); ts_.append(int(z))
            continue
        else:
            continue
        if bid is not None and ask is not None and ask > bid:
            qt.append(int(t)); qb.append(bid); qa.append(ask)
    Q = dict(ts=np.array(qt, np.int64), mid2=np.array(qb, np.int64) + np.array(qa, np.int64),
             bid=np.array(qb, np.int64), ask=np.array(qa, np.int64))
    T = dict(ts=np.array(tt, np.int64), px=np.array(tp, np.int64), sz=np.array(ts_, np.int64))
    return Q, T, sorted(ab.candidates(), key=lambda c: c["available_ts_us"])


def iceberg_candidates(l2, T, Q):
    side, op, size = l2.side.to_numpy(), l2.operation.to_numpy(), l2["size"].to_numpy().astype(float)
    ice = IcebergTracker(**dict(DEFAULT_ICEBERG_KWARGS, min_avg_size=large_size_thresholds(side, op, size, ICEBERG_MIN_AVG_SIZE_PCTL)))
    ts2, lv, tk = l2.ts_us.to_numpy(), l2.level.to_numpy(), l2.price_tick.to_numpy()
    allts = np.concatenate([T["ts"], ts2]); kind = np.concatenate([np.zeros(len(T["ts"]), np.int8), np.ones(len(ts2), np.int8)])
    idx = np.concatenate([np.arange(len(T["ts"])), np.arange(len(ts2))])
    asks, bids = [], []
    for o in np.lexsort((kind, allts)):
        i = int(idx[o])
        if kind[o] == 0:
            p = int(T["px"][i]); a0 = asks[0][0] if asks else None; b0 = bids[0][0] if bids else None
            d = 1 if (a0 is not None and p >= a0) else (-1 if (b0 is not None and p <= b0) else 0)
            ice.on_trade(p, int(T["ts"][i]), float(T["sz"][i]), d)
            continue
        s_, t_ = int(side[i]), int(tk[i]); book = asks if s_ == ASK else bids
        apply_event(book, int(op[i]), int(lv[i]), t_, int(size[i]), s_)
        best = book[0][0] if book else t_
        ice.on_l2_event(s_, int(op[i]), t_, float(size[i]), int(ts2[i]), abs(t_ - best))
    return ice.candidates()


def mid_at(Q, t):
    j = np.searchsorted(Q["ts"], t, side="right") - 1
    return np.where(j >= 0, Q["mid2"][np.clip(j, 0, None)] / 2.0, np.nan)


def response(Q, T, t0, d, level, last_ts):
    """Métricas de respuesta desde t0 en dirección d (+1 long / -1 short). NaN si el horizonte no entra."""
    out = {}
    m0 = float(mid_at(Q, t0))
    ok_all = (t0 + max(HORIZONS) * US <= last_ts) and not bool(_in_halt(t0 - 60 * US, t0 + max(HORIZONS) * US))
    if not ok_all or np.isnan(m0):
        return None
    for h in HORIZONS:
        mh = float(mid_at(Q, t0 + h * US))
        out[f"fade{h}"] = d * (mh - m0)
        out[f"abs{h}"] = abs(mh - m0)
        lo = np.searchsorted(T["ts"], t0, side="right"); hi = np.searchsorted(T["ts"], t0 + h * US, side="right")
        px = T["px"][lo:hi]
        out[f"break{h}"] = float(len(px) and ((px.max() > level) if d == -1 else (px.min() < level)))
    grid = t0 + np.arange(1, 301) * US
    path = d * (mid_at(Q, grid) - m0)
    out["mfe300"], out["mae300"] = float(np.nanmax(path)), float(np.nanmin(path))
    return out


def boot_ci(x, n=N_BOOT, seed=SEED):
    x = np.asarray([v for v in x if np.isfinite(v)])
    if len(x) < 3:
        return None
    rng = np.random.default_rng(seed)
    bs = x[rng.integers(0, len(x), (n, len(x)))].mean(1)
    return [float(x.mean()), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))]


def q(x):
    x = np.asarray([v for v in x if np.isfinite(v)])
    return None if not len(x) else {f"p{p}": float(np.percentile(x, p)) for p in (10, 25, 50, 75, 90)}


def target_free(per, usable, rng):
    """Observaciones TARGET-FREE (no miran retornos): frecuencia, racimos, repeticion de nivel, estado del libro
    contra su distribucion incondicional y co-ocurrencia con iceberg. Devuelve (tf, co_ev)."""
    tf = dict(events_per_session={s: len(per[s]["ev"]) for s in usable}, by_hour_art={}, side_ask_share=None,
              interarrival_cv=None, within60s_share=None, repeat_same_level_10min=None, context={}, iceberg_cooccurrence={})
    sides, cvs, w60, rep = [], [], [], []
    ctx = {k: ([], []) for k in ("spread", "depth_absorbing_side", "qi_toward_absorbing", "range60")}
    co_ev, co_ct = [], []
    for s in usable:
        d = per[s]; ev = d["ev"]; sn = d["snaps"]
        if len(ev) < 2:
            continue
        t = np.array([e["available_ts_us"] for e in ev]); gaps = np.diff(t) / US
        cvs.append(gaps.std() / gaps.mean()); w60.append(float((gaps < 60).mean()))
        for i, e in enumerate(ev):
            sides.append(e["side"] == ASK)
            h = str(int(_sod(e["available_ts_us"]) // 3600)); tf["by_hour_art"][h] = tf["by_hour_art"].get(h, 0) + 1
            prev = [x for x in ev[:i] if x["side"] == e["side"] and x["tick"] == e["tick"]
                    and e["available_ts_us"] - x["available_ts_us"] <= 600 * US]
            rep.append(bool(prev))
            j = np.searchsorted(sn["t"], e["available_ts_us"], side="right") - 1
            if j >= 0:
                bs, as_ = np.asarray(sn["bid_sz"][j]), np.asarray(sn["ask_sz"][j])
                absorbing = as_[0] if e["side"] == ASK else bs[0]
                qi = (bs[0] - as_[0]) / max(bs[0] + as_[0], 1) * (1 if e["side"] == ASK else -1)   # + = cola a favor del absorbente
                lo = np.searchsorted(d["T"]["ts"], e["available_ts_us"] - 60 * US); hi = np.searchsorted(d["T"]["ts"], e["available_ts_us"])
                r60 = float(np.ptp(d["T"]["px"][lo:hi])) if hi > lo else np.nan
                for k, v in (("spread", sn["ask"][j] - sn["bid"][j]), ("depth_absorbing_side", absorbing), ("qi_toward_absorbing", qi), ("range60", r60)):
                    ctx[k][0].append(float(v))
            ice_hit = any(c["side"] == e["side"] and c["tick"] == e["tick"]
                          and abs(c["first_observed_ts_us"] - e["available_ts_us"]) <= 60 * US for c in d["ice"])
            co_ev.append(ice_hit)
        # incondicional: todos los segundos validos de la sesion
        for j in range(0, len(sn["t"]), 5):
            bs, as_ = np.asarray(sn["bid_sz"][j]), np.asarray(sn["ask_sz"][j])
            ctx["spread"][1].append(float(sn["ask"][j] - sn["bid"][j])); ctx["depth_absorbing_side"][1].append(float((bs[0] + as_[0]) / 2))
            ctx["qi_toward_absorbing"][1].append(float((bs[0] - as_[0]) / max(bs[0] + as_[0], 1)) * float(rng.choice([-1, 1])))
            lo = np.searchsorted(d["T"]["ts"], int(sn["t"][j]) - 60 * US); hi = np.searchsorted(d["T"]["ts"], int(sn["t"][j]))
            if hi > lo:                                            # sin rng: no altera la secuencia aleatoria
                ctx["range60"][1].append(float(np.ptp(d["T"]["px"][lo:hi])))
        for _ in range(len(ev)):                                   # control de co-ocurrencia: tiempos y lados al azar
            tc = int(rng.integers(int(sn["t"][0]), int(sn["t"][-1]))); sd_ = int(rng.integers(0, 2))
            j = np.searchsorted(sn["t"], tc, side="right") - 1
            lvl = sn["ask"][j] if sd_ == ASK else sn["bid"][j]
            co_ct.append(any(c["side"] == sd_ and c["tick"] == lvl and abs(c["first_observed_ts_us"] - tc) <= 60 * US for c in d["ice"]))
    tf["side_ask_share"] = float(np.mean(sides)) if sides else None
    tf["interarrival_cv"] = float(np.median(cvs)) if cvs else None
    tf["within60s_share"] = float(np.mean(w60)) if w60 else None
    tf["repeat_same_level_10min"] = float(np.mean(rep)) if rep else None
    for k, (e_, u_) in ctx.items():
        tf["context"][k] = dict(event=q(e_), unconditional=q(u_))
    pe, pc = float(np.mean(co_ev)) if co_ev else 0.0, float(np.mean(co_ct)) if co_ct else 0.0
    tf["iceberg_cooccurrence"] = dict(event_share=pe, control_share=pc, lift=(pe / pc) if pc > 0 else None,
                                      note="umbral del iceberg = percentil de sesion (no causal): descriptivo, no para entradas")
    return tf, co_ev

def load_all(sessions):
    """Fase A: QA por sesion (reglas fijas de `defect_reasons`), absorciones causales e icebergs. Sin retornos."""
    per = {}
    for s in sessions:
        if int(s) >= HOLDOUT_YMD:                          # defensa en profundidad: el holdout no entra nunca
            raise ValueError(f"holdout session {s}")
        l1, l2 = load_session(s)
        res = process_session(l2, l1)
        if defect_reasons(res.qa):
            print(json.dumps(dict(session=s, skipped=defect_reasons(res.qa))), flush=True)
            continue
        Q, T, ev = quotes_trades_absorption(l1)
        ice = iceberg_candidates(l2, T, Q)
        per[s] = dict(Q=Q, T=T, ev=ev, ice=ice, snaps=res.snaps, last=int(Q["ts"][-1]))
        print(json.dumps(dict(session=s, absorptions=len(ev), icebergs=len(ice))), flush=True)
    return per


def _target_free_only(tag: str) -> int:
    """Solo observaciones target-free, para instrumentos con muy pocas sesiones pre-holdout (6E: 4). No hay perfil
    de respuesta: con tan pocas sesiones no hay particion de exploracion util, y mirar retornos gastaria las sesiones
    que un dia pueden servir para confirmar. Las sesiones se declaran FUTURE (sin uso con retornos asignado)."""
    from edgelab.edge_brain.episode_logger import measurement_episode
    OUT.mkdir(parents=True, exist_ok=True)
    sessions = sorted(p.stem for p in (BASE / "l2_depth").glob("*.parquet") if int(p.stem) < HOLDOUT_YMD)
    rng = np.random.default_rng(SEED)
    per = load_all(sessions)
    usable = sorted(per)
    if not usable:
        raise SystemExit("no usable sessions")
    tf, co_ev = target_free(per, usable, rng)
    heur = REPO / "edgelab" / "research" / "l2_manipulation_heuristics.py"
    det_ver = hashlib.sha256(heur.read_bytes()).hexdigest()[:16]
    body = dict(schema="EDGELAB_ATLAS_OBS_V1", phenomenon=f"L2 absorption (causal) {tag}", status="DESCRIPTIVE",
                kind="TARGET_FREE_ONLY", base=str(BASE), detector_version=det_ver, code_commit=_git("rev-parse", "HEAD"),
                tree_dirty=bool(_git("status", "--porcelain")), sessions=usable, skipped=sorted(set(sessions) - set(usable)),
                target_free=tf, iceberg_events=int(sum(co_ev)),
                resolution_note=f"{len(usable)} sesiones: descriptivo de baja resolucion; nada se transporta desde/hacia otros activos")
    raw = json.dumps(body, indent=1, default=float)
    (OUT / f"absorption_{tag}.json").write_text(raw, encoding="utf-8")
    sha = hashlib.sha256(raw.encode()).hexdigest()
    with measurement_episode(LEDGER, f"EP-ATLAS-L2-ABS-{tag}-TF-20260924", goal=f"Atlas L2: absorción {tag} (solo target-free)",
                             recorded_by="tools/l2_atlas_absorption.py --target-free-only", repo=REPO,
                             prereg_ref="docs/research/ATLAS_CAPA_DESCRIPTIVA_20260924.md") as ep:
        st = ep.store
        st.record_partition(f"P-{tag}-PRE", "FUTURE", f"{tag} L2 pre-holdout: sin uso con retornos asignado", usable)
        st.record_observation(f"OBS-ABS-{tag}-TARGETFREE", f"L2 absorption {tag}", "TARGET_FREE", [f"P-{tag}-PRE"],
                              {"events_total": int(sum(tf["events_per_session"].values())), "side_ask_share": tf["side_ask_share"],
                               "interarrival_cv": tf["interarrival_cv"], "repeat_same_level_10min": tf["repeat_same_level_10min"],
                               "iceberg_lift": tf["iceberg_cooccurrence"]["lift"]},
                              {"sessions": len(usable), "note": "baja resolucion"}, sha,
                              depends_on=[f"CODE:AbsorptionTracker@causal@{det_ver}", f"DATA:{BASE.name}"])
        ep.note("observations", "1")
    print(json.dumps(dict(tag=tag, sessions=usable, events=int(sum(tf["events_per_session"].values())), artifact_sha256=sha[:12])))
    return 0


def main(argv=None) -> int:
    import argparse
    global BASE
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", type=Path, default=BASE)
    ap.add_argument("--tag", default="GC0826", help="etiqueta de instrumento/contrato para ids del Brain")
    ap.add_argument("--target-free-only", action="store_true",
                    help="solo la parte target-free (sin perfil de respuesta): para instrumentos con pocas sesiones")
    a = ap.parse_args(argv)
    BASE = a.base
    if a.target_free_only:
        return _target_free_only(a.tag)
    OUT.mkdir(parents=True, exist_ok=True)
    sessions = sorted(p.stem for p in (BASE / "l2_depth").glob("*.parquet") if int(p.stem) < HOLDOUT_YMD)
    rng = np.random.default_rng(SEED)
    per = load_all(sessions)                               # fase A: QA + eventos (no mira retornos)
    usable = sorted(per)
    exp, conf = usable[:len(usable) // 2], usable[len(usable) // 2:]
    tf, co_ev = target_free(per, usable, rng)

    # ---------------- fase B: particiones al Brain ANTES de mirar retornos; perfil solo en EXPLORATION
    from edgelab.edge_brain.episode_logger import measurement_episode
    from edgelab.edge_brain.hippocampus import LessonCandidate
    heur = REPO / "edgelab" / "research" / "l2_manipulation_heuristics.py"
    det_ver = hashlib.sha256(heur.read_bytes()).hexdigest()[:16]
    with measurement_episode(LEDGER, "EP-ATLAS-L2-ABS-GC0826-20260924", goal="Atlas L2: absorción GC 08-26 (descriptivo)",
                             recorded_by="tools/l2_atlas_absorption.py", repo=REPO,
                             prereg_ref="docs/research/ATLAS_CAPA_DESCRIPTIVA_20260924.md") as ep:
        st = ep.store
        st.record_partition("P-GC0826-EXP", "EXPLORATION", "GC 08-26 L2 pre-holdout, primera mitad cronologica", exp)
        st.record_partition("P-GC0826-CONF", "CONFIRMATION_RESERVED", "GC 08-26 L2 pre-holdout, segunda mitad", conf)
        rows_e, rows_c, sess_diff = [], [], {k: [] for k in ("fade", "abs", "break")}
        for s in exp:
            d = per[s]; evt = np.array([e["available_ts_us"] for e in d["ev"]])
            se, sc = [], []
            for e in d["ev"]:
                dirn = -1 if e["side"] == ASK else 1
                t0 = e["available_ts_us"] + LAT
                r = response(d["Q"], d["T"], t0, dirn, e["tick"], d["last"])
                if r is None:
                    continue
                se.append(r)
                for _ in range(N_CTRL):                            # control emparejado: misma sesion, +-30 min, misma direccion
                    for _try in range(50):
                        tc = int(t0 + rng.integers(-CTRL_SPAN_S, CTRL_SPAN_S) * US)
                        if np.min(np.abs(evt - tc)) < EXCL_S * US:
                            continue
                        j = np.searchsorted(d["Q"]["ts"], tc, side="right") - 1
                        if j < 0:
                            continue
                        lvl = int(d["Q"]["ask"][j]) if dirn == -1 else int(d["Q"]["bid"][j])
                        rc = response(d["Q"], d["T"], tc, dirn, lvl, d["last"])
                        if rc is not None:
                            sc.append(rc); break
            rows_e += se; rows_c += sc
            for h in HORIZONS:
                for k in ("fade", "abs", "break"):
                    me = np.nanmean([x[f"{k}{h}"] for x in se]) if se else np.nan
                    mc = np.nanmean([x[f"{k}{h}"] for x in sc]) if sc else np.nan
                    sess_diff[k].append((h, s, me - mc))
        prof = dict(n_events=len(rows_e), n_controls=len(rows_c), by_horizon={})
        for h in HORIZONS:
            row = {}
            for k in ("fade", "abs", "break"):
                row[k] = dict(event=q([x[f"{k}{h}"] for x in rows_e]), control=q([x[f"{k}{h}"] for x in rows_c]),
                              event_mean=float(np.nanmean([x[f"{k}{h}"] for x in rows_e])),
                              control_mean=float(np.nanmean([x[f"{k}{h}"] for x in rows_c])),
                              session_diff_ci=boot_ci([v for (hh, _, v) in sess_diff[k] if hh == h]))
            prof["by_horizon"][str(h)] = row
        prof["mfe300"] = dict(event=q([x["mfe300"] for x in rows_e]), control=q([x["mfe300"] for x in rows_c]))
        prof["mae300"] = dict(event=q([x["mae300"] for x in rows_e]), control=q([x["mae300"] for x in rows_c]))

        # ---------------- sugerencias (reglas fijadas antes: ver doc) — nunca veredictos
        sug = []
        def ci(k, h):
            return prof["by_horizon"][str(h)][k]["session_diff_ci"]
        for h in (60, 300):
            c = ci("fade", h)
            if c and c[1] > 0:
                sug.append((f"SUG-ABS-FADE-{h}", f"Movimiento en dirección fade a {h}s mayor que en controles (IC diferencia {c[1]:.2f}..{c[2]:.2f} ticks). Pre-registrar spec de fade con tiempo máx {h}s."))
            if c and c[2] < 0:
                sug.append((f"SUG-ABS-FOLLOW-{h}", f"Movimiento a favor del flujo absorbido mayor que en controles a {h}s (IC {c[1]:.2f}..{c[2]:.2f}). Pre-registrar spec de continuación, no de fade."))
        for h in HORIZONS:
            c = ci("abs", h)
            if c and c[1] > 0:
                sug.append((f"SUG-ABS-VOL-{h}", f"|movimiento| a {h}s mayor tras absorción (IC {c[1]:.2f}..{c[2]:.2f} ticks): canal NO direccional (dimensionar stops / elegir horizonte)."))
                break
        for h in HORIZONS:
            c = ci("break", h)
            if c and c[2] < 0:
                sug.append((f"SUG-ABS-BARRIER-{h}", f"El nivel absorbido se rompe menos que un nivel de control a {h}s (IC {c[1]:.3f}..{c[2]:.3f}). Hipótesis: barrera de corto plazo (ojo: BigTrap2 como S/R murió; alcance distinto)."))
                break
        lift = tf["iceberg_cooccurrence"]["lift"]
        if lift and lift >= 2 and sum(co_ev) >= 30:
            sug.append(("SUG-ABS-ICE-CONFLUENCE", f"Absorción co-ocurre con iceberg {lift:.1f}× más que al azar: población 'absorción + iceberg' como hipótesis separada."))
        if tf["repeat_same_level_10min"] and tf["repeat_same_level_10min"] >= 0.2:
            sug.append(("SUG-ABS-NTH-TOUCH", f"{tf['repeat_same_level_10min']*100:.0f}% de las absorciones repiten nivel en 10 min: población 'toque n-ésimo' como hipótesis separada."))
        c300 = ci("fade", 300)
        if c300 and (c300[2] - c300[1]) / 2 > 1.0:
            sug.append(("SUG-ABS-MORE-DATA", f"Resolución insuficiente en fade 300 s (medio IC {(c300[2]-c300[1])/2:.2f} ticks): hacen falta más sesiones L2 para ese eje."))

        body = dict(schema="EDGELAB_ATLAS_OBS_V1", phenomenon="L2 absorption (causal) GC 08-26", status="DESCRIPTIVE",
                    detector_version=det_ver, code_commit=_git("rev-parse", "HEAD"), tree_dirty=bool(_git("status", "--porcelain")),
                    partitions=dict(exploration=exp, confirmation_reserved=conf), target_free=tf, response_profile=prof,
                    suggestions=[dict(id=i, text=t, confirm_on="P-GC0826-CONF") for i, t in sug])
        raw = json.dumps(body, indent=1, default=float)
        (OUT / "absorption_GC_08-26.json").write_text(raw, encoding="utf-8")
        sha = hashlib.sha256(raw.encode()).hexdigest()
        deps = [f"CODE:AbsorptionTracker@causal@{det_ver}", "DATA:gc_aug26_canonical_parquets"]
        st.record_observation("OBS-ABS-GC0826-TARGETFREE", "L2 absorption GC 08-26", "TARGET_FREE",
                              ["P-GC0826-EXP", "P-GC0826-CONF"],
                              {"events_total": int(sum(tf["events_per_session"].values())), "side_ask_share": tf["side_ask_share"],
                               "interarrival_cv": tf["interarrival_cv"], "repeat_same_level_10min": tf["repeat_same_level_10min"],
                               "iceberg_lift": lift}, {"sessions": len(usable)}, sha, depends_on=deps)
        st.record_observation("OBS-ABS-GC0826-RESPONSE", "L2 absorption GC 08-26", "RESPONSE_PROFILE", ["P-GC0826-EXP"],
                              {h: {k: prof["by_horizon"][h][k]["session_diff_ci"] for k in ("fade", "abs", "break")} for h in prof["by_horizon"]},
                              {"sessions": len(exp), "events": prof["n_events"], "controls": prof["n_controls"]}, sha, depends_on=deps)
        for sid, text in sug:
            st.record_lesson(LessonCandidate(lesson_id=sid, episode_id="EP-ATLAS-L2-ABS-GC0826-20260924",
                                             statement=f"{text} Confirmar SOLO en P-GC0826-CONF o datos futuros; motivated_by=OBS-ABS-GC0826-*.",
                                             confidence="LOW", status="PROPOSED", scope="SUGGESTED_ANALYSIS"))
        ep.note("observations", "2"); ep.note("suggestions", str(len(sug)))
    print(json.dumps(dict(sessions=len(usable), exploration=len(exp), events=int(sum(tf["events_per_session"].values())),
                          suggestions=[i for i, _ in sug], artifact_sha256=sha[:12])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
