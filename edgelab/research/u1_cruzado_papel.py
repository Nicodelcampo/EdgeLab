"""U1-CRUZADO en papel (2026-11-02, Nico: «sí, dalo de alta»): la regla congelada del acta del holdout exploratorio, tal cual.

Regla (`docs/research/areas_expansion_20261022/u1/ACTA_HOLDOUT_EXPLORATORIO_U1_CRUZADO.md`, de `PREREGISTRO_TOPES_Y_DENSIDAD_U1.md`):
- señal U1 sobre USATECH (Dukascopy): N ≥ 3 zonas LUX-IMB en 40 pts, A/H ≥ 8, regreso al 75 %;
- ejecución en NQ con la base trasladada, en el tick siguiente (E1A);
- objetivo en el borde lejano del área (T3), stop más allá del extremo (S3) con tope de 3× la distancia al objetivo;
- fricción canónica de NQ.
No es una celda de la grilla: corre `u1_cruzado.operar`, el mismo código del descubrimiento. La etapa OPERAR (`etapas.ejecutar`) lo
llama con el contexto del sensor (USATECH) y el de ejecución (NQ). Paridad contra la medición de desarrollo en
`tests/research/test_u1_cruzado_papel.py` y en el kernel de verificación del pre-registro.
"""
from __future__ import annotations

import numpy as np

from edgelab.research import u1_cruzado as U1C

NOMBRE = "U1-CRUZADO-PAPEL"
INDICADORES = ["LUX-IMB"]
EJECUCION = "E1A/T3/S3"
TOPE = ("mult", 3.0)


def operar_papel(ctx_us: dict, ctx_nq: dict, friccion: float, desde: int | None = None) -> dict:
    """Operaciones de la regla congelada: {celda, ses, neto, t} en puntos de NQ netos de fricción. Sólo sesiones >= `desde`."""
    F = U1C.operar(ctx_us, ctx_nq, tope=TOPE)
    if not len(F): return dict(operaciones={})
    g = F[(F.ejecucion == EJECUCION) & F.bruto.notna()]
    if desde is not None: g = g[g.ses >= int(desde)]
    g = g.sort_values(["ses", "t"], kind="stable")
    return dict(operaciones=dict(celda=[0] * len(g), ses=g.ses.astype(int).tolist(), neto=(g.bruto.to_numpy(float) - friccion).tolist(),
                                 t=g.t.astype(float).tolist()),
                resumen=dict(n=int(len(g)), media=float(np.mean(g.bruto - friccion)) if len(g) else None))


def disparos(ctx: dict):
    """Las señales sobre el sensor (para el certificado de causalidad del lanzamiento)."""
    return U1C.senales(ctx)
