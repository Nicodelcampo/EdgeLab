#!/usr/bin/env python3
"""Contador GLOBAL de pruebas del proyecto (revisión 2026-10-04): consolida los registros por familia en un único
`docs/research/TRIAL_REGISTRY_GLOBAL.jsonl` encadenado (TrialRegistry). Idempotente: volver a correrlo no duplica.
Toda campaña nueva debe registrarse también acá (discovery_scan usa este archivo por defecto si no se pasa --registry).

    python tools/registro_global.py            # consolida
    python tools/registro_global.py --total    # imprime el total de pruebas del proyecto
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from edgelab.funnel.multiplicity import TrialRegistry  # noqa: E402

GLOBAL = REPO / "docs" / "research" / "TRIAL_REGISTRY_GLOBAL.jsonl"


def main():
    g = TrialRegistry(GLOBAL)
    if "--total" not in sys.argv:
        for f in sorted((REPO / "docs" / "research").glob("*/trial_registry.jsonl")):
            for line in f.read_text().splitlines():
                if line.strip():
                    r = json.loads(line)
                    g.ensure(f"{f.parent.name}/{r['campaign_id']}", r["family_id"], int(r["n_trials"]), r.get("note", ""))
    print(json.dumps(dict(campanias=g.n_campaigns(), pruebas_totales=g.total(), archivo=str(GLOBAL.relative_to(REPO)))))


if __name__ == "__main__":
    main()
