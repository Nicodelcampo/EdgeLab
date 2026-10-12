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


def record_outcome(path: Path, spec, decision: dict, current: dict | None = None) -> list:
    """spec.origin = {evidence_id: muestra_consumida}. Agrega una línea por pista de origen; `current` = estados vigentes (para encadenar transiciones)."""
    cur = current or {}; out = []
    for eid, sample in (spec.origin or {}).items():
        prev = cur.get(eid, {}).get("status", "WEAK_LEAD"); nxt = TRANSITIONS.get(prev, (prev, prev))[0 if decision.get("hit") else 1]
        rec = dict(ts=time.time(), evidence_id=eid, run_id=spec.run_id, prev_status=prev, status=nxt, consumed=[sample], hit=bool(decision.get("hit")), rejections=decision.get("rejections"),
                   top=[(t["test"], t["p"]) for t in decision.get("top", [])[:3]])
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with Path(path).open("a") as f: f.write(json.dumps(rec) + "\n")
        out.append(rec)
    return out


def apply_runtime(ev: dict, path: Path) -> dict:
    """Devuelve una copia de la evidencia semilla con las actualizaciones vivas aplicadas (estado y muestras consumidas)."""
    if not Path(path).exists(): return ev
    ev = json.loads(json.dumps(ev)); E = {e["id"]: e for e in ev["entries"]}
    for line in Path(path).read_text().splitlines():
        r = json.loads(line); e = E.get(r["evidence_id"])
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
