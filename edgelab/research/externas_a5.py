"""EXTERNAS-28 (2026-11-18): las 28 estrategias traducidas del catálogo externo (`estrategias/catalogo_externo.py`, 114 variantes)
llevadas al contrato de `edgelab/research/tablas.py` para correr con la partición HOLDOUT-A5 sobre M1 real de futuros (motor único
`ejecucion.py`, ya calibrado, en lugar del simulador del analizador, que corre sobre 14 meses de ticks).

Se reutiliza tal cual la función `senales(barras, **params)` de cada estrategia (sin tocar su lógica) y se traduce cada señal a una fila:
  k     = la vela M1 cuyo cierre es `available_at` (la que decide); el motor entra en el primer tick de la vela siguiente
  lado  = `dir`; obj/stop = cierre de k ± target_pts / stop_pts (niveles en precio); fin = k + time_stop_min velas (el motor corta
          además en el fin del tramo continuo: cambio de sesión o hueco > 30 min)
Cada variante es una definición `Xnnn` (nombres sin «-» porque `a5` usa «-» para contrastes); el mapa a estrategia y parámetros está
en `VARIANTES` y se publica en la carpeta de la campaña. Pre-registro: docs/research/externas_a5_20261118/PREREGISTRO.md.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from edgelab.research import analizador as A
from edgelab.research.estrategias.catalogo_externo import ESTRATEGIAS_EXTERNAS

NOMBRE = "EXTERNAS-28"
EJECUCIONES = [("PRECIOS", "obj", "stop", "fin")]
VARIANTES = [(m, p) for m in ESTRATEGIAS_EXTERNAS for p in A.variantes(m)]
DEFINICIONES = [f"X{i:03d}" for i in range(len(VARIANTES))]
_F0 = Path(__file__).resolve().parents[2] / "docs/research/externas_a5_20261118/FASE0.json"
# Las tablas con desenlaces se arman sólo con las variantes que pasaron la fase 0 (fricción ≤ 0,08 R, sin retornos); sin FASE0.json, todas
ACTIVAS = json.loads(_F0.read_text(encoding="utf-8"))["pasan"] if _F0.exists() else list(DEFINICIONES)


def mapa() -> list[dict]:
    return [dict(definicion=d, estrategia=m.NOMBRE, familia=m.FAMILIA, instrumento_declarado=m.INSTRUMENTO, parametros=p)
            for d, (m, p) in zip(DEFINICIONES, VARIANTES)]


def eventos(ctx: dict) -> pd.DataFrame:
    t = np.asarray(ctx["t"], float); c = np.asarray(ctx["c"], float)
    ts = (t * 1000).astype(np.int64)                                       # ms del cierre de cada vela (convención del analizador)
    B = pd.DataFrame(dict(ts=ts, o=np.asarray(ctx["o"], float), h=np.asarray(ctx["h"], float), l=np.asarray(ctx["l"], float), c=c,
                          v=np.asarray(ctx["v"], float), ses=np.asarray(ctx["ses"])))
    filas = []
    for d, (m, p) in zip(DEFINICIONES, VARIANTES):
        if d not in ACTIVAS: continue
        for s in m.senales(B, **p):
            k = int(np.searchsorted(ts, int(s["available_at"]), side="right")) - 1
            lado = int(s["dir"]); tp = float(s["target_pts"]); sl = float(s["stop_pts"])
            if k < 0 or lado not in (1, -1) or not (tp > 0 and sl > 0): continue
            stop = c[k] - lado * sl; obj = c[k] + lado * tp
            filas.append(dict(k=k, lado=lado, ref=obj, ext=stop, rg=sl, obj=obj, stop=stop,
                              fin=k + int(s.get("time_stop_min") or 10_000), **{d: True}))
    act = [d for d in DEFINICIONES if d in ACTIVAS]
    cols = ["k", "lado", "ref", "ext", "rg", "obj", "stop", "fin"] + act
    if not filas: return pd.DataFrame(columns=cols)
    E = pd.DataFrame(filas)
    for x in act:
        E[x] = E[x].fillna(False).astype(bool) if x in E else False
    return E[cols].astype({"k": np.int64, "lado": np.int64, "fin": np.int64}).sort_values(["k", "lado"] + act, kind="mergesort").reset_index(drop=True)
