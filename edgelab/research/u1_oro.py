"""U1-ORO-GRILLA (2026-10-25): la grilla completa de U1-INDAGA trasladada al oro (señal en XAU de Dukascopy, operación en GC), con la
ESCALA del área como perilla. Pedido de Nico: «priorizá las corridas del oro inspiradas en las de USATECH; las más rentables, más
variantes». U1 es la más rentable de las medidas en USATECH/NQ (+17 a +28 pts/op de desarrollo).

Sólo dos parámetros de U1 tienen unidades de precio: el alto máximo del área W (40 pts) y la separación G (1 pt). Acá se escalan por
mes: segmento = mes UTC y factor del mes m = ESCALA × (rango M1 mediano del mes m−1 en el propio XAU) / R_USATECH, donde R_USATECH es
el rango M1 mediano de USATECH en el descubrimiento de U1 (2025-08-05 → 2026-03-31, medido por el kernel U1-ORO). El primer mes no
dispara (no tiene mes anterior). La perilla `escala` ∈ {0,5; 1; 2}: la equivalente a U1 y una a cada lado. Todo lo demás (N, x, A/H,
anatomía, ejecuciones sin BE) es U1-INDAGA tal cual: se importa, no se copia.
Costo de partir por mes: un área no cruza el borde de un mes (zonas de 500 min: se pierden las que nacen en las últimas horas).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from edgelab.research import u1_indaga as U
from edgelab.research.grilla_generica import Variable
from edgelab.research.u1_indaga import niveles  # noqa: F401

NOMBRE = "U1-ORO-GRILLA"
INDICADORES = ["LUX-IMB"]
ESCALAS = (0.5, 1.0, 2.0)
R_USATECH = 6.25                   # rango M1 mediano de USATECH en 2025-08-05..2026-03-31, medido por el kernel U1-ORO (U1_ORO.json, rango_m1_usatech)
RANGO_M1_202609 = {"ES": 1.25, "MES": 1.25, "DK:USA500IDXUSD": 1.25, "NQ": 7.75, "MNQ": 7.75, "DK:USATECHIDXUSD": 7.65,
                   "YM": 9.0, "MYM": 9.0, "DK:USA30IDXUSD": 9.01, "GC": 1.8, "MGC": 1.8, "DK:XAUUSD": 1.75}
VARIABLES = list(U.VARIABLES) + [Variable("escala", "esc", "grupo", categoria=len(ESCALAS))]
EJES_ORDINALES = tuple(U.EJES_ORDINALES) + (len(U.VARIABLES),)
EJECUCIONES = [e for e in U.EJECUCIONES if e[3] == 0]                    # sin el BE muerto (como tests/research/exp_u1_sin_be.py)
VACIO = ["m", "k", "xi", "ciclo", "lado", "lo", "hi", "H", "E", "A", "D", "ni", "A_H", "esc"]
BASE = {"N": 0, "x": 1, "A/H": 1, "escala": 1, "ejecución": EJECUCIONES.index(("E1A", "T1", "S3", 0))}


def escala_por_mes(ctx, r_ref: float) -> tuple:
    """(segmento por vela = mes UTC, {mes: rango M1 mediano del mes anterior / r_ref}); el primer mes queda NaN salvo cuando
    arranca en el holdout (202610, escalado causalmente con el rango M1 mediano de 202609 en desarrollo) o viene `r_mes_previo`."""
    import os
    mes = pd.to_datetime(ctx["t"] - 60, unit="s").strftime("%Y%m").astype(int).to_numpy()
    r = pd.Series(ctx["h"] - ctx["l"]).groupby(mes).median()
    prev = r.shift(1) / r_ref
    r0 = ctx.get("r_mes_previo") or (RANGO_M1_202609.get(ctx.get("sensor") or os.environ.get("SENSOR", ""))
                                     if len(prev) and int(prev.index[0]) == 202610 else None)
    if r0 is not None and len(prev) and np.isnan(prev.iloc[0]): prev.iloc[0] = float(r0) / r_ref
    return mes, {int(m): float(prev.loc[m]) for m in r.index}


def disparos(ctx, r_ref: float | None = None) -> pd.DataFrame:
    r_ref = r_ref or R_USATECH
    if not r_ref: raise ValueError("R_USATECH sin fijar: medirlo antes de usar el experimento")
    mes, f = escala_por_mes(ctx, r_ref); out = []
    for i, e in enumerate(ESCALAS):
        cx = dict(ctx, seg=mes, escala_seg={m: v * e for m, v in f.items()})
        D = U.disparos(cx)
        if len(D): out.append(D.assign(esc=i))
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame(columns=VACIO)
