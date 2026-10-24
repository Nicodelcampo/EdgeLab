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
        if (ce := cfg.get("embudo") or {}).get("activo"):            # embudo de grilla: un paso por campaña activa (edgelab/research/embudo.py)
            from edgelab.funnel.libro_lord import LibroLord
            from edgelab.research import embudo as EMB, embudo_runners as ER, holdout_ventanas as HV
            raiz = Path(a.root) / "embudo"; lec, tk = ER.lectores_sellados(ce.get("sellado"), raiz)
            ventanas = Path(a.root) / "HOLDOUT_VENTANAS.jsonl"; HV.sincronizar(HV.LIBRO, ventanas)   # libro en el estado, no en el clon de código
            emb = EMB.Embudo(raiz, dict(kaggle=ER.KaggleRunner(cfg.get("owner", "nicolasbuttaro")), local=ER.LocalRunner(lec, tk, carpeta=raiz / "_local")),
                             registro=reg, libro=LibroLord(Path(a.root) / "libro_lord.json"), ventanas=ventanas)
            rep["embudo"] = EMB.avanzar_todas(Path(ce.get("campanas", "config/autopilot/grillas/campanas")), emb, conductor=ce.get("conductor", "debian"))
        from .pedidos import desde_ciclo
        if (pd := desde_ciclo(Path(a.root), rep)): rep["pedidos"] = [p["id"] for p in pd]   # lo que sólo una persona puede resolver
        print(json.dumps(rep, default=str), flush=True)
        if cfg.get("sala"):                                       # y el resumen después
            from .sala import reportar
            from .mejora import diagnosticar
            rep["diagnostico"] = diagnosticar([rep], pilot.status())
            hubo = bool(rep.get("launched") or rep.get("closed") or rep.get("pedidos") or rep.get("blocked") or rep.get("event") not in (None, "tick", "tick_no_capacity", "tick_account_cap", "paused", "locked_by_other_controller"))
            if hubo:                                              # ciclos sin novedades no gastan llamadas ni llenan la sala
                reportar(Path(a.root), rep, pilot.status(), runner=runner if cfg["sala"].get("cronista") else None)
        if not a.loop: break
        time.sleep(a.loop)


if __name__ == "__main__":
    main()
