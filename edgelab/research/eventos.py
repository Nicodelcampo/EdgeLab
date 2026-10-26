"""Eventos macro programados (CPI, NFP, FOMC por defecto) para el filtro y el diagnóstico de la grilla (2026-10-26). Los horarios
son los del calendario canónico de `edgelab/noticias.py` (`config/noticias/calendario_usd_tier1.csv`, fuente por fila); acá van
embebidos en `eventos_datos.py` (generado por `tools/eventos_desde_noticias.py`) porque los kernels de Kaggle no llevan archivos de
config. Para operaciones con entrada y salida y la regla de las firmas (±1 min) se usa `noticias.cruza_noticia`.

Dos usos, los dos declarados ANTES de mirar:
  - filtro de un experimento: `EXCLUIR_EVENTOS = dict(antes_min=15, despues_min=15, tipos=("CPI", "NFP_EMPLOYMENT_SITUATION", "FOMC_DECISION"))` en su módulo;
    `grilla_generica.correr` deja fuera (como un llenado imposible) las operaciones con entrada dentro de la ventana;
  - diagnóstico en las réplicas (`etapas`, REP): qué parte de las operaciones y del P&L cae cerca de un evento. Un edge que vive
    sólo ahí no es operable con reglas de firma (muchas prohíben operar en noticias) y es más frágil.
"""
from __future__ import annotations

import numpy as np

from edgelab.research.eventos_datos import EVENTOS

TIPOS = ("CPI", "NFP_EMPLOYMENT_SITUATION", "FOMC_DECISION")       # nombres de evento de edgelab/noticias.py


def tiempos(tipos=TIPOS) -> np.ndarray:
    return np.array(sorted(t for t, k, _ in EVENTOS if k in tipos), np.int64)


def cerca(t_s, antes_min: float = 15, despues_min: float = 15, tipos=TIPOS) -> np.ndarray:
    """True si t (s UTC) cae en [evento − antes, evento + después] de algún evento de `tipos`."""
    t = np.asarray(t_s, np.int64); ev = tiempos(tipos)
    if not len(ev) or not len(t): return np.zeros(len(t), bool)
    i = np.searchsorted(ev, t - int(despues_min * 60), side="left")          # primer evento >= t - después
    ok = i < len(ev)
    return ok & (ev[np.minimum(i, len(ev) - 1)] <= t + int(antes_min * 60))


def diagnostico(t_s, neto, antes_min: float = 15, despues_min: float = 60) -> dict:
    """Parte de las operaciones y del P&L neto con entrada cerca de un evento (ventana amplia por defecto: 15 min antes, 60 después)."""
    neto = np.asarray(neto, float); m = cerca(t_s, antes_min, despues_min); ok = np.isfinite(neto)
    tot = float(neto[ok].sum()); cer = float(neto[ok & m].sum())
    return dict(n=int(ok.sum()), n_cerca=int((ok & m).sum()), frac_ops=float((ok & m).mean()) if ok.any() else 0.0,
                pnl_total=tot, pnl_cerca=cer, media_cerca=float(neto[ok & m].mean()) if (ok & m).any() else None,
                media_lejos=float(neto[ok & ~m].mean()) if (ok & ~m).any() else None, ventana_min=[antes_min, despues_min])
