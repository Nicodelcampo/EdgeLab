#!/usr/bin/env python3
"""Paso 2 de docs/research/urgencia_vs_evidencia_20261117/PROPUESTA.md: contracción empírica por selección (edgelab/research/contraccion.py)
sobre las pistas con réplica de todas las campañas del embudo. Pre-registro: PREREGISTRO_PASO2.md.
  python tools/contraccion_empirica.py      # -> docs/research/urgencia_vs_evidencia_20261117/RESULTADO_PASO2.json
"""
import json, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
OUT = ROOT / "docs/research/urgencia_vs_evidencia_20261117/RESULTADO_PASO2.json"


def main():
    from edgelab.research import contraccion as C
    P = C.pares(ROOT); res = dict(preregistro="docs/research/urgencia_vs_evidencia_20261117/PREREGISTRO_PASO2.md", global_=C.estimar(P))
    np_ = np.array([p[2] for p in P]); res["por_multiplicidad"] = {}
    for nom, lo, hi in (("<1.000 pruebas", 0, 1e3), ("1.000–20.000", 1e3, 2e4), (">20.000", 2e4, np.inf)):
        sub = [p for p, x in zip(P, np_) if lo <= x < hi]
        if len({p[0] for p in sub}) >= 10: res["por_multiplicidad"][nom] = C.estimar(sub, B=1000)
    hl = [(p[3], p[4], p[5]) for p in P if p[5] is not None]
    if hl:
        d, r, c = map(np.array, zip(*hl))
        res["harvey_liu"] = dict(pares=len(hl), conservado_medio=float(c.mean()), esperado_medio=float((c * d).mean()), observado_medio=float(r.mean()))
    OUT.write_text(json.dumps(res, indent=1, default=float)); print(json.dumps(res, indent=1, default=float))


if __name__ == "__main__":
    main()
