"""python -m edgelab.autopilot --root /var/lib/edgelab-autopilot --config /etc/edgelab/autopilot.json --candidates candidates.json [--loop 600]"""
import argparse
import json
import time
from pathlib import Path

from .daemon import Autopilot
from .executor import KaggleExecutor
from .spec import RunSpec


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--root", required=True); ap.add_argument("--config", required=True); ap.add_argument("--candidates", required=True); ap.add_argument("--loop", type=int, default=0)
    a = ap.parse_args(); cfg = json.loads(Path(a.config).read_text())
    from edgelab.funnel.multiplicity import TrialRegistry
    reg = TrialRegistry(Path(cfg["registry"])) if cfg.get("registry") else None
    brain = None
    if cfg.get("brain_ledger"):
        from .brain import brain_sink
        brain = brain_sink(Path(cfg["brain_ledger"]))
    pilot = Autopilot(Path(a.root), KaggleExecutor(cfg.get("owner", "nicolasbuttaro")), cfg, registry=reg, brain=brain)
    while True:
        cands = [RunSpec.from_dict(d) for d in json.loads(Path(a.candidates).read_text())]
        print(json.dumps(pilot.tick(cands), default=str), flush=True)
        if not a.loop: break
        time.sleep(a.loop)


if __name__ == "__main__":
    main()
