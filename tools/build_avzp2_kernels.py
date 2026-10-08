#!/usr/bin/env python3
r"""Arma (y opcionalmente sube) los kernels de Kaggle de la familia AVZP2 a partir de un script de etapa 1 del repo.

Por qué existe: el dataset de código `edgelab-code-avcl-fast` NO contiene `edgelab/bridge/indicators/avolzonepoi2.py`.
Cada kernel lleva ese módulo INCRUSTADO en el script (reemplazando su import), más las variables de entorno del
instrumento y los contratos. Antes esto se hacía a mano en E:\kaggle_kernels; acá queda versionado.

Uso:
  python tools/build_avzp2_kernels.py tools/avzp2_racimo_grid_stage1.py avzgrid --out E:\kaggle_kernels [--push]
Genera <out>/<prefijo>_k1..k3 con z.py + kernel-metadata.json (ids nicolasbuttaro/edgelab-<prefijo>-kN).
Los resultados se bajan con: kaggle kernels output nicolasbuttaro/edgelab-<prefijo>-kN -p <dir>
Kaggle falla a veces al arrancar (log vacío o "[]"): relanzar el mismo kernel sin cambios. Máximo 5 sesiones a la vez.
"""
import argparse
import json
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SPLIT = {"k1": "MNQ_09-25,MNQ_12-25", "k2": "MNQ_03-26,MNQ_06-26", "k3": "MNQ_09-26,MNQ_12-26"}   # k3 = confirmación
DATASETS = ["nicolasbuttaro/edgelab-data-catalog", "nicolasbuttaro/edgelab-ticks-nt8-canonical",
            "nicolasbuttaro/edgelab-ticks-nt8-reexport-20261005", "nicolasbuttaro/edgelab-code-avcl-fast",
            "nicolasbuttaro/edgelab-nt8-historical-missing-20261001", "nicolasbuttaro/edgelab-mgc-nt8-raw-parquet-20261002",
            "nicolasbuttaro/edgelab-ticks-es-nq-2026q3-ext"]


def build(stage1, prefix, out, inst="MNQ", push=False):
    s0 = Path(stage1).read_text(encoding="utf-8")
    mod = (REPO / "edgelab/bridge/indicators/avolzonepoi2.py").read_text(encoding="utf-8").split("from __future__ import annotations", 1)[1]
    imports = [l for l in s0.splitlines() if l.startswith("from edgelab.bridge.indicators.avolzonepoi2 import")]
    assert len(imports) == 1, "el script tiene que importar avolzonepoi2 en una sola línea"
    for k, contracts in SPLIT.items():
        s = s0
        i = s.index("from __future__ import annotations") + len("from __future__ import annotations")
        s = s[:i] + '\nimport os\nos.environ["AVCL_INST"]="%s"\nos.environ["AVCL_CONTRACTS"]="%s"\n' % (inst, contracts) + s[i:]
        s = s.replace(imports[0], "from collections import defaultdict\n" + mod + "\nzp2_run = run\n")
        d = Path(out) / ("%s_%s" % (prefix, k))
        d.mkdir(parents=True, exist_ok=True)
        (d / "z.py").write_text(s, encoding="utf-8")
        kid = "edgelab-%s-%s" % (prefix, k)
        (d / "kernel-metadata.json").write_text(json.dumps(dict(
            id="nicolasbuttaro/" + kid, title=kid, code_file="z.py", language="python", kernel_type="script", is_private=True,
            enable_gpu=False, enable_internet=False, dataset_sources=DATASETS, competition_sources=[], kernel_sources=[])), encoding="utf-8")
        print("armado", d)
        if push:
            subprocess.run(["kaggle", "kernels", "push", "-p", str(d)], check=False)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("stage1"); ap.add_argument("prefix"); ap.add_argument("--out", default=r"E:\kaggle_kernels")
    ap.add_argument("--inst", default="MNQ"); ap.add_argument("--push", action="store_true")
    a = ap.parse_args()
    build(a.stage1, a.prefix, a.out, a.inst, a.push)
