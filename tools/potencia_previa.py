#!/usr/bin/env python3
"""Potencia y frecuencia ANTES de invertir en una estrategia (mejora, holdout o forward): K27–K29 de
docs/research/ERRORES_Y_GUARDAS_AGENTE_DEBIAN_20261026.md. Usa holdout_ventanas.plan_potencia (la misma compuerta que registra aperturas).

  python tools/potencia_previa.py <ops.csv[.gz]> [...]        # columnas R y dia/fecha: frecuencia, meses para decidir el forward, veredicto
  python tools/potencia_previa.py <ops> --fijo N              # además: potencia de una lectura de N operaciones (holdout)
  python tools/potencia_previa.py --conteo <json {prueba: n}> # qué pruebas entran a la familia BH (n >= 30) y cuáles quedan SIN_POTENCIA_PREVIA
La línea «Potencia previa: …» que imprime se copia al pre-registro (lo exigen preflight.validar_preregistro y tests/test_guardas_principiante_20261117.py, K32).
"""
import json, sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))


def main(a):
    from edgelab.research import holdout_ventanas as HV
    from edgelab.funnel.escalera import separar_por_n
    if "--conteo" in a:
        d = json.loads(Path(a[a.index("--conteo") + 1]).read_text()); dentro, fuera = separar_por_n(d)
        print(json.dumps(dict(familia_bh=dentro, sin_potencia_previa=fuera, n_familia=len(dentro)), indent=1, ensure_ascii=False)); return 0
    fijo = int(a[a.index("--fijo") + 1]) if "--fijo" in a else None; mal = 0
    for f in [x for x in a if not x.startswith("--") and not (fijo and x == str(fijo))]:
        g = pd.read_csv(f); dia = g["dia"] if "dia" in g else g["fecha"]
        p = HV.plan_desde_ops(g.R, dia)
        lin = (f"Potencia previa: {Path(f).name}: {p.get('ops_por_mes', 0):.1f} ops/mes, R/op {p['efecto']:+.3f}, sd {p['sd_op']:.2f}, "
               f"n para decidir {p.get('n_necesarias')}, {p.get('meses_para_decidir')} meses → {'OK' if not p['problemas'] else 'NO: ' + '; '.join(p['problemas'])}")
        if fijo:
            q = HV.plan_potencia("fijo", p["efecto"] / 2, p["sd_op"], n=fijo, fuente_efecto="mitad del desarrollo")
            lin += f" | lectura de N {fijo} con la mitad del efecto: potencia {q.get('potencia')}" + ("" if not q["problemas"] else " (NO se abre)")
            mal += bool(q["problemas"])
        print(lin); mal += bool(p["problemas"])
    return 1 if mal else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
