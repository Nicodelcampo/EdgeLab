#!/usr/bin/env python3
"""Empaquetador GENÉRICO de kernels de Kaggle autocontenidos (reutilizable por cualquier corrida de grilla masiva).

Embebe los módulos del repo indicados (con su SHA-256), los escribe en /kaggle/working/pkg al arrancar y ejecuta el script
principal. El kernel no depende de que el repo esté en Kaggle y el resultado puede citar exactamente qué código corrió.
  python tools/kaggle_grilla/construir_kernel.py --main tools/kaggle_areas/areas_main.py --out kernel.py \
      --modulo edgelab/research/areas_expansion.py --modulo edgelab/research/areas_expansion_run.py
Siempre se agregan el núcleo genérico (grilla_masiva) y la escalera del embudo. Los __init__ de los paquetes se embeben
vacíos (los reales importan dependencias pesadas que el kernel no necesita).
"""
import argparse
import base64
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SIEMPRE = ["edgelab/research/grilla_masiva.py", "edgelab/funnel/escalera.py"]


def construir(main, out, modulos):
    mods = list(dict.fromkeys(modulos + SIEMPRE)); inits = set()
    for m in mods:
        parts = Path(m).parts
        for i in range(1, len(parts)): inits.add(str(Path(*parts[:i], "__init__.py")).replace("\\", "/"))
    emb, shas = [], {}
    for m in sorted(inits) + mods:
        b = b"" if m in inits else (ROOT / m).read_bytes()
        shas[m] = hashlib.sha256(b).hexdigest(); emb.append(f"    {m!r}: {base64.b64encode(b).decode()!r},")
    main_src = (ROOT / main).read_text(encoding="utf-8")
    codigo = hashlib.sha256(("".join(f"{k}={v}" for k, v in sorted(shas.items())) + main_src).encode()).hexdigest()
    cab = f'''# Kernel generado por tools/kaggle_grilla/construir_kernel.py (no editar a mano). Principal: {main}. Código: {codigo}
import base64, os, sys
_MODS = {{
{chr(10).join(emb)}
}}
_base = "/kaggle/working/pkg" if os.path.isdir("/kaggle/working") else os.path.abspath("_pkg_kernel")
for _m, _b in _MODS.items():
    _p = os.path.join(_base, _m); os.makedirs(os.path.dirname(_p), exist_ok=True)
    open(_p, "wb").write(base64.b64decode(_b))
sys.path.insert(0, _base)
CODIGO_SHA = {codigo!r}
MODULOS_SHA = {shas!r}
'''
    Path(out).write_text(cab + main_src, encoding="utf-8", newline="\n")
    return codigo, shas


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--main", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--modulo", action="append", default=[]); a = ap.parse_args()
    c, s = construir(a.main, a.out, a.modulo); print(a.out, c[:16], len(s), "módulos")
