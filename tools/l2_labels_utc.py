#!/usr/bin/env python3
r"""Etiquetas de clima L2 NQ → versión UTC para research (Entrada 067, punto 2).

Una sola conversión, sobre la hora de DISPONIBILIDAD (cierre del minuto), en enteros:
    available_utc_us    = feature_available_at_us + ART_TO_UTC_US
    minute_start_utc_us = minute_start_us         + ART_TO_UTC_US
ART = UTC-3 fijo (Argentina no tiene horario de verano; resolución en docs/research/RESOLUCION_RELOJ_GC_L2_20260922.md
y tools/build_l2_catalog.py::ART_TO_UTC_NS). Falla si la entrada ya trae columnas UTC (evita doble conversión) o si
la semántica de reloj no es la esperada.

    python tools/l2_labels_utc.py artifacts/l2_contexts/NQ/labels.parquet OUT.parquet
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

ART_TO_UTC_US = 3 * 3600 * 1_000_000
CLOCK_PREFIX = "NT8_WALL_CLOCK"
KEEP = ["instrument", "contract", "cme_session", "clock_semantics", "minute_id", "minute_start_us", "data_window_end_us",
        "feature_available_at_us", "feature_eligible", "evaluation_eligible", "context_state", "context_group",
        "context_as_of_ok", "context_fail_reason", "context_model_id", "p_calm", "p_normal", "p_volatile", "flow_toxicity_score"]


def to_utc(lab: pd.DataFrame) -> pd.DataFrame:
    if {"available_utc_us", "minute_start_utc_us"} & set(lab.columns):
        raise ValueError("la entrada ya tiene columnas UTC: doble conversión")
    sem = set(lab["clock_semantics"].astype(str))
    if not all(s.startswith(CLOCK_PREFIX) for s in sem):
        raise ValueError(f"semántica de reloj inesperada: {sem}")
    for c in ("minute_start_us", "feature_available_at_us"):
        if lab[c].dtype != np.int64:
            raise ValueError(f"{c} no es int64")
    out = lab[KEEP].copy()
    out["minute_start_utc_us"] = out["minute_start_us"] + ART_TO_UTC_US
    out["available_utc_us"] = out["feature_available_at_us"] + ART_TO_UTC_US
    # disponibilidad = cierre del minuto [t, t+1): nunca antes del fin de su ventana
    if (out["available_utc_us"] - out["minute_start_utc_us"] < 60_000_000).any():
        raise ValueError("etiqueta disponible antes del cierre de su minuto")
    return out


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    o = to_utc(pd.read_parquet(src))
    o.to_parquet(dst, index=False)
    print("filas", len(o), "sesiones", o["cme_session"].nunique())
