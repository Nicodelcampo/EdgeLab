"""Ejecutores. KaggleExecutor llama a las mismas herramientas auditadas que usa el humano (tools/kaggle_launch.py: preflight en vivo + manifiesto de versiones)."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


class LaunchRejected(RuntimeError):
    """El proveedor (o la validación local previa al envío) rechazó EXPLÍCITAMENTE el lanzamiento: se sabe que no hay corrida. Cualquier otra excepción es un envío incierto."""


class KaggleExecutor:
    def __init__(self, owner: str = "nicolasbuttaro"):
        self.owner = owner

    def launch(self, spec) -> str:
        slug = f"{self.owner}/edgelab-{spec.run_id}".lower()
        cmd = [sys.executable, str(REPO / "tools/kaggle_launch.py"), "--slug", slug, "--script", spec.script, "--allow-missing"]
        for n in spec.needs: cmd += ["--need", n]
        for d in spec.extra_datasets: cmd += ["--extra-dataset", d]
        for k, v in spec.env.items(): cmd += ["--env", f"{k}={v}"]
        cmd += (["--internet"] if spec.internet else []) + (["--gpu"] if spec.gpu else [])
        r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, timeout=900)
        if '"hasError":false' not in r.stdout and '"error":""' not in r.stdout:
            if r.returncode != 0 and '"ref"' not in r.stdout: raise LaunchRejected("lanzamiento rechazado antes del envío: " + (r.stdout + r.stderr)[-400:])
            raise LaunchRejected("lanzamiento rechazado: " + (r.stdout + r.stderr)[-400:])
        return slug

    def status(self, handle: str) -> str:
        r = subprocess.run([sys.executable, str(REPO / "tools/kaggle_kernel.py"), "status", "--slug", handle], cwd=REPO, capture_output=True, text=True, timeout=300)
        try: return json.loads(r.stdout.strip().splitlines()[-1])["status"]
        except Exception: return "unknown"

    def fetch(self, handle: str, filename: str) -> dict:
        out = Path(tempfile.mkdtemp()) / "r.json"
        subprocess.run([sys.executable, str(REPO / "tools/kaggle_kernel.py"), "output", "--slug", handle, "--file", filename, "--out", str(out)], cwd=REPO, capture_output=True, text=True, timeout=600)
        return json.loads(out.read_text())


class FakeExecutor:
    """Para pruebas: lanza «al instante» y devuelve los resultados que se le den."""
    def __init__(self, results: dict, fail=()):
        self.results, self.fail, self.launched = results, set(fail), []
    def launch(self, spec): self.launched.append(spec.run_id); return "fake/" + spec.run_id
    def status(self, handle): return "error" if handle.split("/")[1] in self.fail else "complete"
    def fetch(self, handle, filename): return self.results[handle.split("/")[1]]
