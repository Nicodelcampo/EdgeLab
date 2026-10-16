#!/usr/bin/env python3
"""Corrida de humo del autopilot (benchmark, sin hipótesis): carga una semana de M1 de GC por la ruta normal (verifica el manifiesto de lanzamiento) y escribe un JSON mínimo."""
import json, os, sys, time
from pathlib import Path
KAGGLE = Path("/kaggle/input").exists()
if KAGGLE:
    _roots = [Path("/kaggle/input"), *Path("/kaggle/input").glob("datasets/*")]
    os.environ["EDGELAB_DATA_ROOTS"] = os.pathsep.join(str(r) for r in _roots)
    sys.path.insert(0, str(next(p.parent for r in _roots for p in r.glob("edgelab-data-catalog/**/edgelab_data.py"))))
    OUT = Path("/kaggle/working")
else:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "docs/data_catalog")); OUT = Path("/tmp/smoke_out")
OUT.mkdir(parents=True, exist_ok=True)
import edgelab_data as ed
t0 = time.time(); m = ed.load_m1("GC", "2026-01-05", "2026-01-09")
res = dict(campaign="autopilot_smoke", rows=int(len(m)), sessions=int(m.session_date.nunique()), manifest_present=bool(os.environ.get("EDGELAB_LAUNCH_MANIFEST")), seconds=round(time.time() - t0, 1))
(OUT / "SMOKE.json").write_text(json.dumps(res)); print(res)
