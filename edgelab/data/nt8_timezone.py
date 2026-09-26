"""Verificación empírica de la timezone del export NT8 por SCHEDULE-FIT contra el
calendario CME 6E (gate P0, F2 — reemplaza el método de bordes, frágil en mercado
fino).

Idea: para un offset candidato O (horas), ts_utc = ts_local − O; se convierte a CT
(DST-aware, zoneinfo America/Chicago) y se mide la fracción de ticks FUERA de la
sesión CME (halt diario 16:00–17:00 CT; fin de semana vie 16:00 → dom 17:00 CT).
El offset correcto minimiza las violaciones (~0). Como la conversión a CT es
DST-aware, un export de OFFSET FIJO (UTC/ART) puntúa consistentemente aunque el
rango cruce cambios de DST; uno que *siga* DST no.

`verify_offset` chequea un offset objetivo (default 0 = UTC): verificado si su score
es bajo, está en (o muy cerca de) el mínimo global, y ART (−3 h) es claramente peor.
El residual (~feriados CME no modelados) se reporta aparte con `forbidden_days`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

CT = ZoneInfo("America/Chicago")
NS = 1_000_000_000
ART_OFFSET_S = -3 * 3600


def cme_forbidden(weekday, hour):
    """bool[]: True si (weekday, hour) CT cae FUERA de sesión CME 6E."""
    weekday = np.asarray(weekday); hour = np.asarray(hour)
    daily_halt = np.isin(weekday, [0, 1, 2, 3, 4]) & (hour == 16)   # 16:00–17:00 CT L-V
    sat = weekday == 5
    fri_after = (weekday == 4) & (hour >= 16)                        # vie cierre
    sun_before = (weekday == 6) & (hour < 17)                        # dom pre-apertura
    return daily_halt | sat | fri_after | sun_before


def _ct_index(ts_utc_ns):
    return pd.DatetimeIndex(np.asarray(ts_utc_ns, "int64").astype("datetime64[ns]")) \
        .tz_localize("UTC").tz_convert(CT)


def schedule_violation(ts_utc_ns) -> float:
    idx = _ct_index(ts_utc_ns)
    return float(cme_forbidden(idx.weekday.to_numpy(), idx.hour.to_numpy()).mean())


def score_offsets(ts_local_ns, candidates_h=range(-12, 13), sample=200_000) -> dict:
    ts = np.asarray(ts_local_ns, "int64")
    if len(ts) > sample:
        ts = ts[np.linspace(0, len(ts) - 1, sample).astype(int)]
    return {oh * 3600: schedule_violation(ts - oh * 3600 * NS) for oh in candidates_h}


def forbidden_days(ts_utc_ns, top=15):
    """Días (CT) con ticks fuera de sesión — candidatos a feriados CME no modelados."""
    idx = _ct_index(ts_utc_ns)
    mask = cme_forbidden(idx.weekday.to_numpy(), idx.hour.to_numpy())
    if not mask.any():
        return []
    days = pd.Series(idx[mask].date).value_counts().head(top)
    return [(str(d), int(c)) for d, c in days.items()]


@dataclass
class VerifyResult:
    offset_s: int              # offset objetivo evaluado (0 = UTC)
    verified: bool
    score: float               # violación al offset objetivo
    min_offset_s: int          # offset con violación mínima
    min_score: float
    art_score: float
    note: str = ""
    scores_s: dict = field(default_factory=dict)


def verify_offset(ts_local_ns, offset_s=0, max_score=0.03, near_min=0.006,
                  art_margin=0.02) -> VerifyResult:
    scores = score_offsets(ts_local_ns)
    min_off = min(scores, key=scores.get)
    min_sc = scores[min_off]
    sc = scores.get(offset_s, 1.0)
    art = scores.get(ART_OFFSET_S, 1.0)
    verified = (sc < max_score and (sc - min_sc) < near_min and art > sc + art_margin)
    note = (f"offset={offset_s}s score={sc:.5f}; min@{min_off}s={min_sc:.5f}; "
            f"ART={art:.5f}; {'VERIFICADO' if verified else 'NO verificado'}")
    return VerifyResult(offset_s, verified, sc, min_off, min_sc, art, note, scores)
