"""Evidencia viva: las corridas del autopilot actualizan el estado de las pistas (append-only), para que las candidatas siguientes aprendan de ellas:
una réplica exitosa sube la pista, un fracaso la degrada, y toda muestra usada queda marcada como consumida (no se vuelve a proponer sobre ella)."""
from __future__ import annotations

import json
import time
from pathlib import Path

TRANSITIONS = {  # estado previo -> (si hit, si no hit)
    "WEAK_LEAD": ("REPLICATED_ONCE", "FAILED_REPLICATION"),
    "LEAD_INFO": ("REPLICATED_ONCE", "FAILED_REPLICATION"),
    "REPLICATED_ONCE": ("REPLICATED_TWICE", "FAILED_REPLICATION"),
    "ARTIFACT_SUSPECT": ("SURVIVES_CHECK", "ARTIFACT_CONFIRMED"),
}


def record_outcome(path: Path, spec, decision: dict, current: dict | None = None, result: dict | None = None) -> list:
    """spec.origin = {evidence_id: {"sample": muestra consumida, "tests": [prefijos de las pruebas de ESA pista]}} (o {evidence_id: muestra} sin filtro).
    El acierto de una pista se evalúa solo con sus pruebas (Holm al nivel apostado); una prueba rechazada que no pertenece a ninguna pista de origen abre una pista NUEVA."""
    from .analyze import rejected_tests
    cur = current or {}; out = []; Path(path).parent.mkdir(parents=True, exist_ok=True)
    rej = rejected_tests(result, decision["family_alpha"], decision["n_planned"]) if result is not None else set(); owned = set()
    def put(rec):
        with Path(path).open("a") as f: f.write(json.dumps(rec) + "\n")
        out.append(rec)
    for eid, o in (spec.origin or {}).items():
        sample, prefixes = (o, None) if isinstance(o, str) else (o.get("sample"), o.get("tests"))
        mine = {t for t in rej if prefixes is None or any(t.startswith(p) for p in prefixes)}; owned |= mine
        hit = bool(mine) if result is not None else bool(decision.get("hit"))
        prev = cur.get(eid, {}).get("status", "WEAK_LEAD"); nxt = TRANSITIONS.get(prev, (prev, prev))[0 if hit else 1]
        put(dict(ts=time.time(), evidence_id=eid, run_id=spec.run_id, prev_status=prev, status=nxt, consumed=[sample], hit=hit, rejected=sorted(mine), top=[(t["test"], t["p"]) for t in decision.get("top", [])[:3]]))
    for t in sorted(rej - owned):                                           # hallazgo fuera de las pistas de origen: pista nueva, sin muestra independiente aún
        put(dict(ts=time.time(), evidence_id=f"{spec.run_id}:{t}", run_id=spec.run_id, prev_status=None, status="WEAK_LEAD", consumed=[], hit=True, rejected=[t],
                 new_entry=dict(indicator=spec.family, asset=t, note=f"hallazgo exploratorio de {spec.run_id} (Holm al nivel apostado) fuera de la pista de origen; sin réplica independiente",
                                unused_samples=["new_data_after_holdout"], sources=[spec.prereg])))
    return out


def apply_runtime(ev: dict, path: Path) -> dict:
    """Devuelve una copia de la evidencia semilla con las actualizaciones vivas aplicadas (estado y muestras consumidas)."""
    if not Path(path).exists(): return ev
    ev = json.loads(json.dumps(ev)); E = {e["id"]: e for e in ev["entries"]}
    for line in Path(path).read_text().splitlines():
        r = json.loads(line); e = E.get(r["evidence_id"])
        if not e and r.get("new_entry"):
            e = dict(id=r["evidence_id"], **r["new_entry"]); ev["entries"].append(e); E[e["id"]] = e
        if not e: continue
        e["status"] = r["status"]; e["unused_samples"] = [s for s in e.get("unused_samples", []) if s not in r["consumed"]]
        e.setdefault("history", []).append(dict(run_id=r["run_id"], hit=r["hit"], status=r["status"]))
    return ev


def current_states(path: Path) -> dict:
    cur = {}
    if Path(path).exists():
        for line in Path(path).read_text().splitlines():
            r = json.loads(line); cur[r["evidence_id"]] = dict(status=r["status"])
    return cur
