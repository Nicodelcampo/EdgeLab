"""Afinidad de una estrategia con un régimen: cuánto rinde en ese régimen comparado con su media, con contracción hacia la media
global (pocos días en un régimen no alcanzan para creerle). Sólo usa operaciones de sesiones ya cerradas, etiquetadas con el régimen
que se conocía ANTES de cada sesión (`regimen.etiquetar`).

multiplicador = media contraída del régimen / media global, recortado a [0, MULT_MAX]. Si la media contraída es <= 0, el
multiplicador es 0: la estrategia se SUSPENDE ese día (sigue en papel para no perder información; no se retira por régimen).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

K_CONTRACCION, MULT_MAX = 20.0, 2.0


def tabla(ops: pd.DataFrame, regimen_por_ses: pd.Series) -> pd.DataFrame:
    """`ops`: columnas ses, neto. Devuelve n, media y multiplicador por régimen."""
    o = ops.assign(reg=ops.ses.map(regimen_por_ses)).dropna(subset=["reg"])
    if not len(o): return pd.DataFrame(columns=["reg", "n", "media", "media_contraida", "mult"])
    mu = float(o.neto.mean()); g = o.groupby("reg").neto.agg(["count", "mean"]).reset_index()
    g.columns = ["reg", "n", "media"]
    g["media_contraida"] = (g.n * g.media + K_CONTRACCION * mu) / (g.n + K_CONTRACCION)
    g["mult"] = np.clip(g.media_contraida / mu, 0.0, MULT_MAX) if mu > 0 else 0.0
    g.loc[g.media_contraida <= 0, "mult"] = 0.0
    return g


def multiplicador(ops: pd.DataFrame, regimen_por_ses: pd.Series, regimen_hoy: str | None) -> float:
    """1 sin información del régimen de hoy (no se castiga ni premia lo que no se midió)."""
    if regimen_hoy is None: return 1.0
    t = tabla(ops, regimen_por_ses)
    if not len(t): return 1.0
    fila = t[t.reg == regimen_hoy]
    if len(fila): return float(fila.mult.iloc[0])
    mu = float(ops.neto.mean()) if len(ops) else 0.0
    return 1.0 if mu > 0 else 0.0
