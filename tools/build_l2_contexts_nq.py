#!/usr/bin/env python3
r"""Contextos L2 (4 climas) en NQ según docs/research/PROTOCOLO_CONTEXTOS_L2_NQ_20260928.md (auditoría 051 §1).

Target-free. Pasos:
    .venv\Scripts\python tools\build_l2_contexts_nq.py preflight     # verifica todo y NO escribe artefactos
    .venv\Scripts\python tools\build_l2_contexts_nq.py extract       # features por sesión (caché en E:\l2_contexts\NQ)
    .venv\Scripts\python tools\build_l2_contexts_nq.py fit           # entrena (20), etiqueta (40), reporte PASS/STOP

El preflight aborta (exit 1) si algo difiere del protocolo: exactamente 20 + 40 sesiones del catálogo, contrato por
sesión, archivos presentes con el tamaño del manifiesto, `conversion.subsecond_unit == 100ns_ticks`, parámetros
congelados (desestacionalización activa, semillas 1..10).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402

from edgelab.context.l2_gate import (context_gate_report, extract_minute_features, fit_regime4_model,  # noqa: E402
                                     label_regime4, seed_labels)

CATALOG = REPO / "docs" / "research" / "contract_regimes" / "L2_sessions_catalog_20260927.json"
PROTOCOL = REPO / "docs" / "research" / "PROTOCOLO_CONTEXTOS_L2_NQ_20260928.md"
L2 = Path(r"E:\l2_parquet")
CACHE = Path(r"E:\l2_contexts\NQ")
OUT = REPO / "artifacts" / "l2_contexts" / "NQ"
N_TRAIN, N_EVAL = 20, 40
SEEDS = list(range(1, 11))
ART_TO_UTC_US = 3 * 3600 * 1_000_000
ROLL_DATE = "20260915"


def _sha(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def plan():
    cat = json.loads(CATALOG.read_text(encoding="utf-8"))
    ses = sorted(cat["instrumentos"]["NQ"]["sesiones"], key=lambda s: s["trade_date"])
    return ses[:N_TRAIN], ses[N_TRAIN:N_TRAIN + N_EVAL], ses


def preflight():
    train, ev, allses = plan()
    errs = []
    if len(allses) != N_TRAIN + N_EVAL:
        errs.append(f"el catálogo tiene {len(allses)} sesiones NQ, el protocolo exige {N_TRAIN + N_EVAL}")
    for s in allses:
        cdir = L2 / s["contract"]
        for f in s["files"]:
            man = cdir / "manifests" / f"{f}.manifest.json"
            if not man.exists():
                errs.append(f"{s['trade_date']}: falta manifiesto {man}"); continue
            m = json.loads(man.read_text(encoding="utf-8"))
            if m.get("conversion", {}).get("subsecond_unit") != "100ns_ticks":
                errs.append(f"{s['trade_date']}/{f}: subsecond_unit={m.get('conversion', {}).get('subsecond_unit')}")
            for k in ("l2_depth", "l1_quotes"):
                o = m["outputs"][k]; p = Path(o["path"])
                if not p.exists() or p.stat().st_size != o["bytes"]:
                    errs.append(f"{s['trade_date']}/{f}: {k} ausente o de otro tamaño")
    frozen = dict(n_train=N_TRAIN, n_eval=N_EVAL, seeds=SEEDS, deseasonalize=True, roll_date=ROLL_DATE,
                  train_ids=[s["trade_date"] for s in train], eval_ids=[s["trade_date"] for s in ev],
                  contracts={s["trade_date"]: s["contract"] for s in allses},
                  catalog_sha256=hashlib.sha256(CATALOG.read_bytes()).hexdigest(),
                  protocol_sha256=hashlib.sha256(PROTOCOL.read_bytes()).hexdigest())
    frozen["plan_sha256"] = _sha(frozen)
    print(json.dumps(dict(errores=errs, entrenamiento=f"{frozen['train_ids'][0]}..{frozen['train_ids'][-1]}",
                          evaluacion=f"{frozen['eval_ids'][0]}..{frozen['eval_ids'][-1]}", plan_sha256=frozen["plan_sha256"]),
                     ensure_ascii=False, indent=1))
    if errs:
        sys.exit(1)
    return frozen


def _load(s, kind):
    """Archivos diarios COMPLETOS que cubren la sesión (28/09: recortar a la ventana perdía la foto inicial del libro
    que trae cada archivo, y el libro nunca quedaba listo). Entre archivos consecutivos hay unos segundos de
    solapamiento: del archivo siguiente se descartan las filas con reloj anterior al último del archivo previo."""
    parts, last = [], None
    for k, f in enumerate(sorted(s["files"])):
        t = pq.read_table(L2 / s["contract"] / kind / f"{f}.parquet").to_pandas()
        t = t.sort_values("source_row", kind="mergesort")
        if last is not None:
            t = t[t["ts_us"] >= last]
        if len(t):
            last = int(t["ts_us"].iloc[-1])
        t["source_row"] = t["source_row"].astype(np.int64) + k * 10**12        # los source_row reinician por archivo
        if kind == "l2_depth":
            t["resync"] = False
            if len(t):
                t.iloc[0, t.columns.get_loc("resync")] = True                    # sólo si la foto inicial sobrevivió
        parts.append(t)
    return pd.concat(parts, ignore_index=True).reset_index(drop=True)


def _in_session(feats, s):
    """Minutos (reloj ART de minute_id) dentro de la ventana CME de la sesión."""
    lo = (s["start_ns"] // 10**9 - 10800) // 60; hi = (s["end_ns"] // 10**9 - 10800) // 60
    m = feats["minute_id"]
    return feats[(m >= lo) & (m <= hi)].reset_index(drop=True)


def extract():
    preflight()
    _, _, allses = plan()
    CACHE.mkdir(parents=True, exist_ok=True)
    for s in allses:
        f = CACHE / f"{s['trade_date']}.parquet"
        if f.exists():
            continue
        l2 = _load(s, "l2_depth"); l1 = _load(s, "l1_quotes")
        feats, diag = extract_minute_features(l2, l1, session=s["trade_date"], instrument="NQ", contract=s["contract"])
        feats = _in_session(feats, s)
        diag["minute_rows_session"] = int(len(feats)); diag["eligible_minutes_session"] = int(feats["feature_eligible"].sum())
        feats.to_parquet(f, index=False)
        (CACHE / f"{s['trade_date']}.diag.json").write_text(json.dumps(diag, indent=1), encoding="utf-8")
        print(s["trade_date"], "minutos", len(feats), "elegibles", diag["eligible_minutes_session"], "libro inválido", diag["book_invalid_events"], "inversiones",
              diag["clock_inversions_interleaved"], "trades BBO vieja", diag["stale_bbo_trades"], flush=True)
        del l2, l1, feats


def fit():
    frozen = preflight()
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True).stdout.strip()
    dirty = bool(subprocess.run(["git", "status", "--porcelain", "--", "edgelab", "tools"], cwd=REPO, capture_output=True, text=True).stdout.strip())
    train, ev, allses = plan()
    feats = pd.concat([pd.read_parquet(CACHE / f"{s['trade_date']}.parquet") for s in allses], ignore_index=True)
    tr_ids = [s["trade_date"] for s in train]; ev_ids = [s["trade_date"] for s in ev]
    model = fit_regime4_model(feats, train_sessions=tr_ids, code_identity=head, deseasonalize=True, seeds=SEEDS)
    labels = label_regime4(feats, model, evaluation_sessions=ev_ids)
    _, sets = seed_labels(feats, model, ev_ids)
    rep = context_gate_report(labels, model, train_sessions=tr_ids, evaluation_sessions=ev_ids, roll_date=ROLL_DATE,
                              seed_label_sets=sets)
    rep.update(plan=frozen, code_commit=head, tree_dirty=dirty,
               diagnostics={s["trade_date"]: json.loads((CACHE / f"{s['trade_date']}.diag.json").read_text(encoding="utf-8"))
                            for s in allses})
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "model.json").write_text(json.dumps(model, default=float), encoding="utf-8")
    labels.to_parquet(OUT / "labels.parquet", index=False)
    (OUT / "gate_report.json").write_text(json.dumps(rep, indent=1, default=float, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(dict(model_id=model["model_id"], verdict=rep["verdict"], stops=rep["stops"],
                          coverage=rep["coverage"]["value"], seeds=rep.get("seed_stability_eval")), indent=1, default=float))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("step", choices=["preflight", "extract", "fit"])
    {"preflight": preflight, "extract": extract, "fit": fit}[ap.parse_args().step]()
