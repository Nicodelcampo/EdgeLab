"""python -m edgelab.autopilot --root /var/lib/edgelab-autopilot --config /etc/edgelab/autopilot.json --candidates candidates.json [--loop 600]"""
import argparse
import json
import time
from pathlib import Path

from .daemon import Autopilot
from .executor import KaggleExecutor
from .spec import RunSpec


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--root", required=True); ap.add_argument("--config", required=True); ap.add_argument("--candidates", required=True); ap.add_argument("--loop", type=int, default=0); ap.add_argument("--status", action="store_true")
    a = ap.parse_args(); cfg = json.loads(Path(a.config).read_text())
    from edgelab.funnel.multiplicity import TrialRegistry
    reg = TrialRegistry(Path(cfg["registry"])) if cfg.get("registry") else None
    brain = None
    if cfg.get("brain_ledger"):
        from .brain import brain_sink
        brain = brain_sink(Path(cfg["brain_ledger"]))
    pilot = Autopilot(Path(a.root), KaggleExecutor(cfg.get("owner", "nicolasbuttaro")), cfg, registry=reg, brain=brain)
    if a.status:
        print(json.dumps(pilot.status(), indent=1, default=str)); return
    runner = None
    if cfg.get("roles_ledger"):                                   # roles LLM (cronista) sólo si la configuración lo pide
        from .roles import RoleRunner
        runner = RoleRunner(Path(cfg["roles_ledger"]))
    while True:
        if cfg.get("sala"):                                       # puente con Chaski: comandos antes del ciclo
            from .sala import aplicar_comandos
            aplicar_comandos(Path(a.root), pilot.pause_files()[1], cfg["sala"].get("autorizados", []), pilot.status)   # sólo el interruptor de la sala
        cands = [RunSpec.from_dict(d) for d in json.loads(Path(a.candidates).read_text())]
        rep = pilot.tick(cands)
        print(json.dumps(rep, default=str), flush=True)
        if cfg.get("sala"):                                       # y el resumen después
            from .sala import reportar
            from .mejora import diagnosticar
            rep["diagnostico"] = diagnosticar([rep], pilot.status())
            reportar(Path(a.root), rep, pilot.status(), runner=runner if cfg["sala"].get("cronista") else None)
        if not a.loop: break
        time.sleep(a.loop)


if __name__ == "__main__":
    main()
