#!/usr/bin/env python3
"""Contador GLOBAL de pruebas del proyecto (revisión 2026-10-04): consolida los registros por familia en un único
`docs/research/TRIAL_REGISTRY_GLOBAL.jsonl` encadenado (TrialRegistry). Idempotente: volver a correrlo no duplica.
Toda campaña nueva debe registrarse también acá (discovery_scan usa este archivo por defecto si no se pasa --registry).

    python tools/registro_global.py            # consolida
    python tools/registro_global.py --total    # imprime el total de pruebas del proyecto
    python tools/registro_global.py preregistrado <campaña> <FAMILIA> <n_pruebas> <PREREGISTRO.md>
        # la ÚNICA forma de contar una campaña fuera de la maquinaria estándar (K32): valida el pre-registro antes de registrar
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from edgelab.funnel.multiplicity import TrialRegistry  # noqa: E402

GLOBAL = REPO / "docs" / "research" / "TRIAL_REGISTRY_GLOBAL.jsonl"


PREFIJOS_MAQUINARIA = ("embudo/", "banco/", "analizador/", "analizador_embudo/", "atras/", "autopilot/", "cartera_forward/", "sqx/",
                       "discovery_", "variante_tau/")          # registran ellas mismas, con su propio preflight (embudo, banco, autopilot…)


def preregistrado(campania, familia, n, prereg):
    from edgelab.research.preflight import validar_preregistro
    if (mal := validar_preregistro(prereg)): raise SystemExit(f"no se cuenta {campania}: " + "; ".join(mal))
    nuevo = TrialRegistry(GLOBAL).ensure(campania, familia, int(n), str(prereg)); print("registrada" if nuevo else "ya estaba", campania, n)


def exigir_contada(prereg) -> None:
    """K51 (2026-11-19): una corrida ad hoc arrancó aunque `preregistrado` se había negado a contarla (la cadena de comandos siguió).
    Toda herramienta que mide desenlaces llama a esto antes de leer datos: se niega si el pre-registro no figura en el registro global."""
    p = str(Path(prereg).resolve().relative_to(REPO)) if Path(prereg).is_absolute() else str(prereg)
    for l in GLOBAL.read_text(encoding="utf-8").splitlines():
        if l.strip() and json.loads(l).get("note") == p: return
    raise SystemExit(f"K51: {p} no está contado en TRIAL_REGISTRY_GLOBAL.jsonl (python tools/registro_global.py preregistrado …); no se corre")


def main():
    if sys.argv[1:2] == ["preregistrado"]: return preregistrado(*sys.argv[2:6])
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
