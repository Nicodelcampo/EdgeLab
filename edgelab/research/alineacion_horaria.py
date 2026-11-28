"""K58 — verificar la hora de una fuente externa contra una referencia antes de usarla (2026-11-27).

Caso que lo motivó: la documentación de HistData dice «EST fijo», pero el sello es la hora de Nueva York CON horario de verano y marca la
apertura de la vela. La calibración de TRZ-EXTRANJEROS falló en los tres módulos hasta que una correlación minuto a minuto contra NQ
futuros mostró el desfase de 1 h en verano (`docs/research/trz_extranjeros_20261127/CALIBRACION_DIAGNOSTICO.json`).

Regla: toda fuente intradía nueva pasa por `exigir_alineada` contra una referencia del mismo subyacente (o muy correlacionada), por
separado en invierno y en verano, antes de medir nada con ella. Es target-free: sólo compara retornos de las dos fuentes entre sí.
"""
from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd


def correlacion_por_desfase(a: pd.Series, b: pd.Series, desfases_min: Iterable[int] = range(-180, 181, 30)) -> dict[int, float]:
    """Correlación de retornos de 1 minuto entre `a` y `b` corriendo `a` k minutos (k > 0: el sello de `a` está k minutos adelantado).

    `a` y `b` son precios indexados por tiempo (mismo huso o ambos con zona). Sólo usa minutos presentes en las dos series.
    """
    ra = np.log(a.astype(float)).diff()
    rb = np.log(b.astype(float)).diff()
    out: dict[int, float] = {}
    for k in desfases_min:
        ra_k = ra.copy()
        ra_k.index = ra_k.index - pd.Timedelta(minutes=int(k))
        x = pd.concat([ra_k, rb], axis=1, join="inner").dropna()
        out[int(k)] = float(x.iloc[:, 0].corr(x.iloc[:, 1])) if len(x) >= 30 else float("nan")
    return out


def mejor_desfase(a: pd.Series, b: pd.Series, desfases_min: Iterable[int] = range(-180, 181, 30)) -> tuple[int, float]:
    c = {k: v for k, v in correlacion_por_desfase(a, b, desfases_min).items() if np.isfinite(v)}
    if not c:
        raise ValueError("K58: sin minutos en común entre las dos fuentes; no se puede verificar la hora")
    k = max(c, key=c.get)
    return k, c[k]


def exigir_alineada(a: pd.Series, b: pd.Series, corr_min: float = 0.5,
                    desfases_min: Iterable[int] = range(-180, 181, 30), etiqueta: str = "") -> float:
    """Falla si la mejor correlación no está en desfase 0 o es menor que `corr_min` (incluye barrido fino ±5 min). Devuelve la correlación en desfase 0."""
    k, c = mejor_desfase(a, b, desfases_min)
    if k != 0:
        raise ValueError(f"K58 {etiqueta}: la fuente está corrida {k} min respecto de la referencia (corr {c:.3f}); "
                         "corregir la lectura de la hora antes de medir")
    k_fino, c_fino = mejor_desfase(a, b, range(-5, 6, 1))
    if abs(k_fino) > 0 and c_fino > c + 1e-4:
        raise ValueError(f"K58 {etiqueta}: desfase fino de {k_fino} min detectado (corr {c_fino:.3f} vs {c:.3f} en 0); "
                         "alinear apertura/cierre de vela")
    if c < corr_min:
        raise ValueError(f"K58 {etiqueta}: correlación {c:.3f} < {corr_min} en desfase 0; la referencia no sirve o los datos no son "
                         "del mismo subyacente")
    return c


def exigir_cierre_causal_diario(cierre_insumo_utc_h: float, cierre_activo_utc_h: float,
                                nombre_insumo: str = "", nombre_activo: str = "") -> None:
    """Guarda K58-D1 (cierre Sídney/Tokio vs CBOE NY): falla si un insumo diario cierra después que el activo en la misma fecha."""
    if float(cierre_insumo_utc_h) > float(cierre_activo_utc_h):
        raise ValueError(
            f"K58-D1 {nombre_insumo}->{nombre_activo}: el insumo cierra a las {cierre_insumo_utc_h:.2f} UTC, "
            f"después que el activo ({cierre_activo_utc_h:.2f} UTC) en la misma fecha (look-ahead diario)"
        )
