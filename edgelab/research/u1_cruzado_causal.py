"""U1-CRUZADO con disparos CAUSALES (2026-11-02): la misma regla congelada que `u1_cruzado_papel`, pero con
`areas_expansion.disparos_causales` (lo que se puede operar en vivo). Sirve para medir cuánto del resultado de U1 venía de la
mirada al futuro de `disparos` y es la versión que se porta a JForex. Etapa OPERAR."""
from __future__ import annotations

import numpy as np

from edgelab.research import u1_cruzado as U1C
from edgelab.research.u1_cruzado_papel import EJECUCION, TOPE

NOMBRE = "U1-CRUZADO-CAUSAL"
INDICADORES = ["LUX-IMB"]


def operar_papel(ctx_us: dict, ctx_nq: dict, friccion: float, desde: int | None = None) -> dict:
    F = U1C.operar(ctx_us, ctx_nq, tope=TOPE, causal=True)
    if not len(F): return dict(operaciones={})
    g = F[(F.ejecucion == EJECUCION) & F.bruto.notna()]
    if desde is not None: g = g[g.ses >= int(desde)]
    g = g.sort_values(["ses", "t"], kind="stable")
    return dict(operaciones=dict(celda=[0] * len(g), ses=g.ses.astype(int).tolist(), neto=(g.bruto.to_numpy(float) - friccion).tolist(),
                                 t=g.t.astype(float).tolist(), lado=g.lado.astype(int).tolist(), k_us=g.k_us.astype(int).tolist()),
                resumen=dict(n=int(len(g)), media=float(np.mean(g.bruto - friccion)) if len(g) else None))


def disparos(ctx: dict):
    """Las señales sobre el sensor (para el certificado de causalidad del lanzamiento)."""
    return U1C.senales(ctx)
