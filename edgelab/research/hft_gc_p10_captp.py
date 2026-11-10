"""HFT-GC-P10-CAPTP (2026-11-05, Programa R): Entradas HFT de `GC` con veto corto + recorte causal de `TP` delante de Barrera HFT (`CAP_TP_DELANTE`).

Pre-registro: `docs/research/hft_gc_p10_20261105/PREREGISTRO_BARRERAS_HFT_R.md`.

Variante paralela pre-registrada a `HFT-GC-P10-VETO`:
  - Veta la entrada cuando la primera barrera HFT frontal está demasiado cerca (`d_lib_r < piso_veto`, con `piso_veto` en `{1.0R, 1.5R}`,
    o cuando tras descontar `2 ticks` de margen delante del borde cercano queda `< max(19 ticks, 0.85R)`).
  - Si `piso_veto <= d_lib_r` y la barrera HFT aparece antes del `TP` original (`2.0R`, `3.0R` o `4.0R`), conserva la entrada y
    adelanta el `TP` exactamente `2 ticks` delante del borde cercano de esa primera barrera HFT vigente.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from edgelab.research import barreras_hft as BH, hft_gc_cluster_p10 as BASE_EXP, hft_gc_p10_veto as VETO_EXP
from edgelab.research.eventos import TIPOS_TIER1
from edgelab.research.grilla_generica import Variable
from edgelab.research.intento_fallido import lineas_salida  # noqa: F401

NOMBRE = "HFT-GC-P10-CAPTP"
INDICADORES = ["HFT-GC-CLUSTER-P10"]
NORMALIZAR = "riesgo"
PREFLIGHT_T0_S = 1_760_047_200
LINEAS_SOLO_TIEMPO = True
EXCLUIR_EVENTOS = dict(antes_min=5, despues_min=5, tipos=TIPOS_TIER1)

CORTES_PISO_VETO_R = (1.0, 1.5)
VARIABLES = [
    Variable("mecanismo", "mec", "grupo", categoria=len(BASE_EXP.MECANISMOS)),
    Variable("franja_ny", "franja", "eq_any", categoria=4),
    Variable("tipo_barrera", "t_bar", "grupo", categoria=len(BH.TIPOS_BARRERA)),
    Variable("antiguedad", "edad", "grupo", categoria=len(BH.ANTIGUEDADES)),
    Variable("mitigacion", "mit", "grupo", categoria=len(BH.MITIGACIONES)),
    Variable("piso_veto", "d_lib_r", "ge", cortes=CORTES_PISO_VETO_R, piso=True),
]
EJES_ORDINALES = (5,)
EJECUCIONES = [("S3_ATR", 2.0), ("S3_ATR", 3.0), ("S3_ATR", 4.0)]
BASE = {
    "mecanismo": 1,
    "franja_ny": 2,
    "tipo_barrera": 0,
    "antiguedad": 2,
    "mitigacion": 1,
    "piso_veto": 1,
    "ejecución": 1,
}
VACIO = VETO_EXP.VACIO


def disparos(ctx: dict) -> pd.DataFrame:
    return VETO_EXP.disparos(ctx)


def niveles(fila: dict, ej: tuple, ctx: dict):
    _, mult_tp = ej
    k = int(fila["k"])
    s = int(fila["lado"])
    mec = int(fila["mec"])
    ent = float(fila["ent"])
    sl = float(fila["sl"])
    riesgo = float(fila["riesgo"])
    d_px = float(fila["d_lib_px"])
    tick = float(ctx["tick"])

    limite = 1 if mec in (0, 3) else 2
    dist_tp = min(float(mult_tp) * riesgo, d_px - 2.0 * tick)
    objetivo = float(np.round((ent + s * dist_tp) / tick) * tick)
    piso_tp = max(19.0 * tick, 0.85 * riesgo)
    if (objetivo - ent) * s < piso_tp - 1e-9:
        return None
    return (k, limite, s, ent, sl, objetivo, 0, (0 if s == 1 else 1), 0.0)


def niveles_lote(D: pd.DataFrame, ej: tuple, ctx: dict) -> np.ndarray:
    m = len(D)
    out = np.full((m, 9), np.nan, dtype=np.float64)
    if m == 0:
        return out
    _, mult_tp = ej
    tick = float(ctx["tick"])
    k = D["k"].to_numpy(np.int64)
    s = D["lado"].to_numpy(np.int64)
    mec = D["mec"].to_numpy(np.int64)
    ent = D["ent"].to_numpy(np.float64)
    sl = D["sl"].to_numpy(np.float64)
    riesgo = D["riesgo"].to_numpy(np.float64)
    d_px = D["d_lib_px"].to_numpy(np.float64)

    limite = np.where((mec == 0) | (mec == 3), 1.0, 2.0)
    dist_tp = np.minimum(float(mult_tp) * riesgo, d_px - 2.0 * tick)
    objetivo = np.round((ent + s * dist_tp) / tick) * tick
    piso_tp = np.maximum(19.0 * tick, 0.85 * riesgo)
    valido = ((objetivo - ent) * s) >= (piso_tp - 1e-9)

    out[valido, 0] = k[valido]
    out[valido, 1] = limite[valido]
    out[valido, 2] = s[valido]
    out[valido, 3] = ent[valido]
    out[valido, 4] = sl[valido]
    out[valido, 5] = objetivo[valido]
    out[valido, 6] = 0.0
    out[valido, 7] = np.where(s[valido] == 1, 0.0, 1.0)
    out[valido, 8] = 0.0
    return out

