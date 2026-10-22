#!/usr/bin/env python3
"""Activa la regla de decisión `escalera_v1` en el autopilot del Debian, en dos pasos (decisión de Nico, 2026-10-22: «hacé lo que
recomendás»: primero un ciclo en modo propose, después encender).

  1) Prueba, sin tocar nada real:
       sudo -u edgelab /opt/edgelab/venv/bin/python tools/autopilot_activar_escalera.py --config /etc/edgelab/autopilot.json \
           --root /var/lib/edgelab-autopilot/state/autopilot_runs --candidates /var/lib/edgelab-autopilot/state/autopilot_runs/candidates.json
     Copia el directorio de estado a uno temporal y corre UN ciclo con `decision: escalera_v1` y `mode: propose` sobre la copia
     (cierra corridas terminadas con la regla nueva y dice qué lanzaría, sin lanzar). Imprime el informe y `status()`.
  2) Aplicar (sólo si el paso 1 se ve bien):  ... --aplicar
     Agrega `"decision": "escalera_v1"` y `"escalera": {"alfa": 0.05, "q": 0.10}` a la configuración, con copia de respaldo
     `autopilot.json.antes_escalera`. No cambia `mode` ni ninguna otra clave. Para volver atrás: restaurar el respaldo.
Ningún archivo protegido cambia; `fdr.py` y `alpha.json` siguen intactos (las corridas abiertas con alfa se liquidan con su regla).
"""
import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
CLAVES = {"decision": "escalera_v1", "escalera": {"alfa": 0.05, "q": 0.10}}


def prueba(cfg_path: Path, root: Path, candidates: Path) -> dict:
    from edgelab.autopilot.daemon import Autopilot
    from edgelab.autopilot.executor import KaggleExecutor
    from edgelab.autopilot.spec import RunSpec
    cfg = json.loads(cfg_path.read_text(encoding="utf-8")); tmp = Path(tempfile.mkdtemp(prefix="escalera_prueba_"))
    copia = tmp / "estado"; shutil.copytree(root, copia, ignore=shutil.ignore_patterns(".lock"))
    cfg = dict(cfg, **CLAVES, mode="propose", evidence_runtime=str(copia / "evidence_runtime.jsonl"), registry=None, brain_ledger=None)
    pilot = Autopilot(copia, KaggleExecutor(cfg.get("owner", "nicolasbuttaro")), cfg, registry=None, brain=None)
    rep = pilot.tick([RunSpec.from_dict(d) for d in json.loads(candidates.read_text(encoding="utf-8"))])
    return dict(copia=str(copia), informe=rep, status=pilot.status(), nota="corrió sobre una COPIA del estado; nada real cambió")


def aplicar(cfg_path: Path) -> dict:
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    if cfg.get("decision") == "escalera_v1": return dict(ya_estaba=True)
    shutil.copy2(cfg_path, cfg_path.with_name(cfg_path.name + ".antes_escalera"))
    cfg.update(CLAVES); tmp = cfg_path.with_name(cfg_path.name + ".tmp")
    tmp.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"); tmp.replace(cfg_path)
    return dict(aplicado=True, respaldo=str(cfg_path.with_name(cfg_path.name + ".antes_escalera")), claves=CLAVES)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", required=True, type=Path); ap.add_argument("--root", type=Path); ap.add_argument("--candidates", type=Path)
    ap.add_argument("--aplicar", action="store_true"); a = ap.parse_args()
    if a.aplicar: print(json.dumps(aplicar(a.config), indent=1, ensure_ascii=False)); return
    if not (a.root and a.candidates): ap.error("la prueba necesita --root y --candidates")
    print(json.dumps(prueba(a.config, a.root, a.candidates), indent=1, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
