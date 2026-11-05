"""SEGUNDO-INTENTO (2026-11-03, Nico: «tomá lo que mejor funciona de la idea, que aparezcan muchas más operaciones por la potencia, y
aplicalo a otras familias para diversificar»).

Lo que mejor funcionó de INTENTO-FALLIDO-HACIA (marginales en las 3 fuentes y las 2 ventanas, `RESULTADO_IF_HACIA.md`):
  - entrar HACIA la zona tras el intento fallido, con CONFIRMACIÓN (una vela que cierre hacia la zona);
  - la primera pierna (alejamiento de la zona) larga en velas.
Lo que mataba la muestra se saca: el racimo de >= 3 zonas (U1) pasa a ser variable N ∈ {1, 2, 3} (zona individual o racimo) y el piso de
A/H baja de 4 a 2. La confirmación del filtro estrecho dejó 10 sesiones en 19 meses (no concluyente): acá la potencia es el objetivo.

Reutiliza todo: zonas y disparos causales de U1 (`u1_indaga`, `u1_oro` para la escala por instrumento, `u1_zonas` para almacenes),
piernas y niveles de `intento_fallido_b80` (tests propios). Pre-registro: docs/research/segundo_intento_20261103/PREREGISTRO_SEGUNDO_INTENTO.md.
"""
from __future__ import annotations

import pandas as pd

from edgelab.research import intento_fallido_b80 as IB
from edgelab.research import u1_indaga as U
from edgelab.research import u1_oro as UO
from edgelab.research.grilla_generica import Variable
from edgelab.research.intento_fallido_b80 import EXCLUIR_EVENTOS, LINEAS_SOLO_TIEMPO, lineas_salida, niveles  # noqa: F401

NOMBRE = "SEGUNDO-INTENTO"
INDICADORES = ["LUX-IMB"]
NS = (1, 2, 3)                      # zona individual, par o racimo
AH_MIN = 2.0
VARIABLES = [
    Variable("N", "ni", "grupo", categoria=len(NS)),
    Variable("r", "ri", "grupo", categoria=len(IB.RS)),
    Variable("A/H", "A_H", "extremos", cuantiles=3),
    Variable("dur_ida", "dur_ida", "extremos", cuantiles=3),
]
EJES_ORDINALES = ()
EJECUCIONES = [("CONF", tp) for tp in IB.TPS]          # sólo la entrada que mejor anduvo; TP Z1/Z2/Z3/2R
BASE = {"N": 0, "r": 1, "ejecución": 0}
VACIO = IB.VACIO + ["ni"]


def _aproximaciones(fuente, ctx, *a, **k) -> pd.DataFrame:
    """Disparos de U1 con N ∈ NS y A/H >= AH_MIN (sólo se cambian esos dos parámetros, durante la llamada)."""
    viejo_ns, viejo_ah = U.NS_U1, U.AH_CORTES
    U.NS_U1, U.AH_CORTES = NS, (AH_MIN,) + tuple(viejo_ah[1:])
    try: return fuente(ctx, *a, **k)
    finally: U.NS_U1, U.AH_CORTES = viejo_ns, viejo_ah


def construir(D: pd.DataFrame, ctx: dict) -> pd.DataFrame:
    if D is None or not len(D): return pd.DataFrame(columns=VACIO)
    partes = [IB.construir(D[D.ni == n].reset_index(drop=True), ctx).assign(ni=int(n)) for n in sorted(D.ni.unique())]
    partes = [p for p in partes if len(p)]
    return pd.concat(partes, ignore_index=True).sort_values(["k", "ni", "ri"], kind="stable", ignore_index=True) if partes else pd.DataFrame(columns=VACIO)


def disparos(ctx, r_ref: float | None = None) -> pd.DataFrame:
    """LUX-IMB calculado sobre las velas del propio sensor (cualquier instrumento), con la escala de U1 por instrumento."""
    D = _aproximaciones(UO.disparos, ctx, r_ref)
    if len(D) and "esc" in D: D = D[D.esc == UO.ESCALAS.index(1.0)].reset_index(drop=True)      # sólo la escala nominal
    return construir(D, ctx)
