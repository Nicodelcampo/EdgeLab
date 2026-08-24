#!/usr/bin/env python3
"""Entrada legacy GATE v1, retirada de corridas formales.

La ruta del schema quedó corregida para que la evidencia histórica sea legible,
pero este adaptador no puede etiquetar: usaba model_id sin checkpoint, no
segmentaba por instrumento/contrato/sesión y aceptaba magnitudes mal nombradas.
Use gate_adapter_v2.attach_context_at_t0.
"""
from __future__ import annotations

import json
from pathlib import Path

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schema" / "gate_context_schema_v1.json"
DEFAULT_MODEL_ID = None


def load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def label_events_at_t0(*args, **kwargs):
    raise RuntimeError(
        "gate_adapter v1 fue retirado: use gate_adapter_v2 con model_id hash-qualified, "
        "join por instrument/contract/cme_session y max_feature_age"
    )


def main() -> None:
    schema = load_schema()
    print(json.dumps({
        "status": "LEGACY_RETIRED",
        "schema_readable": True,
        "schema_version": schema.get("version"),
        "replacement": "modules.gate.core.gate_adapter_v2.attach_context_at_t0",
        "outcomes_accessed": False,
    }, indent=2))


if __name__ == "__main__":
    main()
