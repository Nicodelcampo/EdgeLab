#!/usr/bin/env python3
"""Arma el script del kernel AREAS-EXP-1: embebe los módulos del repo (motor, conductor, escalera) con su SHA-256, los escribe
en /kaggle/working/pkg al arrancar y ejecuta `areas_main.py`. Un solo archivo, sin depender del repo en Kaggle.
  python tools/kaggle_areas/construir_kernel.py <salida.py>
"""
import base64
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULOS = ["edgelab/__init__.py", "edgelab/research/__init__.py", "edgelab/research/areas_expansion.py", "edgelab/research/areas_expansion_run.py", "edgelab/research/grilla_masiva.py",
           "edgelab/funnel/__init__.py", "edgelab/funnel/escalera.py"]


def main():
    out = Path(sys.argv[1]); emb, shas = [], {}
    for m in MODULOS:
        b = (ROOT / m).read_bytes() if (ROOT / m).exists() else b""
        if m == "edgelab/funnel/__init__.py": b = b""                     # el __init__ del funnel importa numba/pyarrow pesados: no hace falta
        if m == "edgelab/__init__.py": b = b""
        shas[m] = hashlib.sha256(b).hexdigest(); emb.append(f"    {m!r}: {base64.b64encode(b).decode()!r},")
    main_src = (ROOT / "tools/kaggle_areas/areas_main.py").read_text(encoding="utf-8")
    codigo = hashlib.sha256(("".join(sorted(shas.values())) + main_src).encode()).hexdigest()
    txt = f'''# Kernel AREAS-EXP-1 (generado por tools/kaggle_areas/construir_kernel.py; no editar a mano). Código: {codigo}
import base64, os, sys
_MODS = {{
{chr(10).join(emb)}
}}
_base = "/kaggle/working/pkg" if os.path.isdir("/kaggle/working") else os.path.abspath("_pkg_areas")
for _m, _b in _MODS.items():
    _p = os.path.join(_base, _m); os.makedirs(os.path.dirname(_p), exist_ok=True)
    open(_p, "wb").write(base64.b64decode(_b))
sys.path.insert(0, _base)
CODIGO_SHA = {codigo!r}
MODULOS_SHA = {shas!r}
'''
    out.write_text(txt + main_src, encoding="utf-8", newline="\n")
    print(out, codigo[:16], {k: v[:12] for k, v in shas.items()})


if __name__ == "__main__":
    main()
