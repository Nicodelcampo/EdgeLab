"""MODELO-ASIA: descripción target-free del ancho del rango 18:00–20:00 ET (2026-11-01, Nico: «medilo con los datasets de Kaggle»).
Módulo aparte para no cambiar el código de `modelo_asia` mientras corren sus campañas (el embudo vigila el hash del experimento).
Lo corre la etapa DESCRIBIR (`etapas.ejecutar`); no simula operaciones ni mira nada posterior a las 20:00."""
from __future__ import annotations

import numpy as np
import pandas as pd

from edgelab.research.modelo_asia import (ANCHO_PTS, BASE, EJECUCIONES, EJES_ORDINALES, FIN_REL, INI_REL, VARIABLES,  # noqa: F401
                                          disparos, niveles, niveles_lote)
from edgelab.research.regimen_sesion import minuto_ny

NOMBRE = "MODELO-ASIA-DESCRIBIR"
INDICADORES = ["MODELO-ASIA"]


def describir(ctx: dict) -> dict:
    """Target-free (etapa DESCRIBIR): ancho del rango 18:00–20:00 ET por sesión (puntos del índice), para fijar la unidad de "puntos".
    No mira nada posterior a las 20:00."""
    h, l = np.asarray(ctx["h"], float), np.asarray(ctx["l"], float); ses = np.asarray(ctx["ses"], np.int64)
    rel = (minuto_ny(np.asarray(ctx["t"], np.int64)) - 1080) % 1440; ok = (rel > INI_REL) & (rel <= FIN_REL)
    df = pd.DataFrame(dict(ses=ses[ok], h=h[ok], l=l[ok])).groupby("ses").agg(h=("h", "max"), l=("l", "min"), n=("h", "size"))
    df = df[df.n >= 0.8 * (FIN_REL - INI_REL)]; a = (df.h - df.l).to_numpy()
    tramos = np.searchsorted(np.asarray(ANCHO_PTS), a, side="right")
    return dict(sesiones=int(len(a)), ancho=dict(zip(df.index.astype(int).tolist(), np.round(a, 2).tolist())),
                percentiles={str(q): float(np.percentile(a, q)) for q in (10, 25, 50, 75, 90)} if len(a) else {},
                por_tramo={str(t): int((tramos == t).sum()) for t in range(len(ANCHO_PTS) + 1)})
