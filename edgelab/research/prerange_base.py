"""PRERANGE-BASE (2026-11-01): el barrido del rango 08:12-09:12 NY sin filtro de zonas, en una grilla chica y sobre historia que esta
familia nunca miró. Pre-registro: docs/research/prerange_base_20261101/SPEC_PRERANGE_BASE.md.

Por qué: PRERANGE-ZONAS (28.512 celdas por canal, ~240 disparos por gatillo) no nominó nada en DESC y su canasta de NQ quedó con potencia
0,17. El cuello es la potencia, no la idea: acá se mide la regla base (los mismos disparos y las mismas 16 ejecuciones de
`prerange_hft`/`otr_930_sweep`) con dos perillas (gatillo y alto del rango en ATR) = 144 celdas por canal, sobre los CFD de Dukascopy
2023-01 → 2025-07 (antes de cualquier dato que usaron las familias del rango de las 8:12). Reutiliza `prerange_zonas.base_disparos` y
`prerange_hft.niveles`/`niveles_lote`: nada de la mecánica se reescribe.
"""
from __future__ import annotations

import pandas as pd

from edgelab.research import prerange_hft as X
from edgelab.research.grilla_generica import Variable
from edgelab.research.prerange_hft import niveles, niveles_lote  # noqa: F401
from edgelab.research.prerange_zonas import base_disparos

NOMBRE = "PRERANGE-BASE"
INDICADORES = ["OTR-930-SWEEP"]
VARIABLES = [Variable("gatillo", "gat", "grupo", categoria=len(X.GATILLOS)),
             Variable("alto_rango", "ancho", "extremos", cuantiles=3)]          # H del rango / ATR14 as-of k, terciles del E0
EJECUCIONES = X.EJECUCIONES
EJES_ORDINALES = (1,)
BASE = {"gatillo": 0, "alto_rango": 2, "ejecución": 0}


def disparos(ctx: dict) -> pd.DataFrame:
    D = base_disparos(ctx)
    return D.assign(ancho=D.H_rng / D.atr.where(D.atr > 0))
