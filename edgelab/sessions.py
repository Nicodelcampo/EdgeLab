"""Matrices de ventanas intradía en hora de Nueva York.

Se conservan sin romper los contratos públicos existentes:

- ``build_session_matrices(df, start_h, start_m, duration_min)``;
- ``rth_matrices(df)`` para RTH ``[09:30,16:00)``.

La primitiva adicional ``minute_window_matrices`` permite ligar una ventana a
un calendario explícito, preservar días sin barras y hashear el denominador.
Los timestamps de entrada son UTC (naive o aware) y la conversión usa
``America/New_York``; nunca se fija manualmente EST/EDT.
"""
from __future__ import annotations

import hashlib
import json

import numpy as np
import pandas as pd

NEW_YORK_TZ = "America/New_York"
RTH_OPEN_MINUTE = 9 * 60 + 30
RTH_MIN = 390  # [09:30, 16:00)
YM_PRERANGE_START = "08:12"
YM_PRERANGE_END = "09:12"

_REQUIRED_COLUMNS = ("open", "high", "low", "close", "volume")


def _minute_of_day(value, field):
    if isinstance(value, int) and not isinstance(value, bool):
        minute = value
    elif isinstance(value, str):
        parts = value.split(":")
        if len(parts) != 2 or not all(part.isdigit() for part in parts):
            raise ValueError("%s debe tener formato HH:MM" % field)
        hour, minute_part = map(int, parts)
        if not 0 <= hour <= 23 or not 0 <= minute_part <= 59:
            raise ValueError("%s fuera de rango" % field)
        minute = hour * 60 + minute_part
    else:
        raise ValueError("%s debe ser minuto entero o HH:MM" % field)
    if not 0 <= minute < 24 * 60:
        raise ValueError("%s fuera de rango" % field)
    return minute


def _format_minute(minute):
    return "%02d:%02d" % divmod(minute, 60)


def _ny_index(index):
    if not isinstance(index, pd.DatetimeIndex):
        raise ValueError("el índice debe ser DatetimeIndex")
    if index.has_duplicates:
        raise ValueError("el índice contiene timestamps duplicados")
    if not index.is_monotonic_increasing:
        raise ValueError("el índice debe estar ordenado")
    utc = index.tz_localize("UTC") if index.tz is None else index.tz_convert("UTC")
    return utc.tz_convert(NEW_YORK_TZ)


def _calendar_days(session_days):
    if isinstance(session_days, (str, bytes)):
        raise ValueError("session_days debe ser una secuencia de fechas")
    try:
        raw = pd.DatetimeIndex(session_days)
    except (TypeError, ValueError) as exc:
        raise ValueError("session_days inválido") from exc
    if len(raw) == 0:
        raise ValueError("session_days no puede estar vacío")
    days = (
        raw.tz_localize(NEW_YORK_TZ)
        if raw.tz is None
        else raw.tz_convert(NEW_YORK_TZ)
    ).normalize()
    if days.has_duplicates:
        raise ValueError("session_days contiene duplicados")
    if not days.is_monotonic_increasing:
        raise ValueError("session_days debe estar ordenado")
    return days


def _calendar_digest(days, start, end):
    payload = {
        "timezone": NEW_YORK_TZ,
        "window": [_format_minute(start), _format_minute(end)],
        "endpoint_policy": "half_open",
        "session_days": [day.strftime("%Y-%m-%d") for day in days],
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def minute_window_matrices(df, *, start, end, session_days=None):
    """Convierte OHLCV M1 a matrices día × minuto para ``[start,end)``.

    ``session_days`` es el calendario local elegible, ordenado y sin
    duplicados. Si se omite, los días se infieren de los datos y
    ``calendar_complete`` queda en False: sirve para compatibilidad/diagnóstico,
    no como denominador formal.

    Los días explícitos sin barras se preservan como filas NaN. Barras de una
    fecha no incluida en el calendario explícito son error, no se descartan.
    Se admiten ventanas que cruzan medianoche; la fecha asignada es la del
    inicio de la ventana.
    """
    if not isinstance(df, pd.DataFrame):
        raise ValueError("df debe ser DataFrame")
    missing = [column for column in _REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError("faltan columnas OHLCV: %s" % missing)

    start_minute = _minute_of_day(start, "start")
    end_minute = _minute_of_day(end, "end")
    span = (end_minute - start_minute) % (24 * 60)
    if span == 0:
        raise ValueError("la ventana debe durar entre 1 y 1439 minutos")

    local = _ny_index(df.index)
    minute = np.asarray(local.hour * 60 + local.minute, dtype=np.int64)
    slots = (minute - start_minute) % (24 * 60)
    in_window = slots < span

    local_days = local.normalize()
    if end_minute <= start_minute:
        local_days = pd.DatetimeIndex(
            [
                day - pd.Timedelta(days=1) if raw_minute < end_minute else day
                for day, raw_minute in zip(local_days, minute)
            ]
        )
    bar_days = local_days[in_window]

    explicit_calendar = session_days is not None
    if explicit_calendar:
        days = _calendar_days(session_days)
        unknown = pd.DatetimeIndex(pd.unique(bar_days)).difference(days)
        if len(unknown):
            raise ValueError(
                "hay barras de ventana fuera de session_days: %s"
                % [day.strftime("%Y-%m-%d") for day in unknown]
            )
    else:
        days = pd.DatetimeIndex(sorted(pd.unique(bar_days)))
        if len(days) == 0:
            raise ValueError("sin datos en la ventana solicitada")

    shape = (len(days), span)
    out = {}
    if in_window.any():
        day_position = {day: index for index, day in enumerate(days)}
        rows = np.asarray([day_position[day] for day in bar_days], dtype=np.int64)
        columns = slots[in_window].astype(np.int64)
        cell_ids = rows * span + columns
        if len(np.unique(cell_ids)) != len(cell_ids):
            raise ValueError("más de una barra para el mismo día/minuto")
        sub = df.iloc[np.flatnonzero(in_window)]
    else:
        rows = columns = np.asarray([], dtype=np.int64)
        sub = df.iloc[0:0]

    for column in _REQUIRED_COLUMNS:
        matrix = np.full(shape, np.nan)
        if len(sub):
            matrix[rows, columns] = sub[column].to_numpy(np.float64)
        out[column[0].upper()] = matrix

    local_minutes = (start_minute + np.arange(span)) % (24 * 60)
    out.update(
        days=days,
        timezone=NEW_YORK_TZ,
        window_start=_format_minute(start_minute),
        window_end=_format_minute(end_minute),
        endpoint_policy="half_open",
        window_minutes=local_minutes,
        m_rth=local_minutes - RTH_OPEN_MINUTE,
        calendar_complete=explicit_calendar,
        calendar_sha256=_calendar_digest(days, start_minute, end_minute),
    )
    return out


def _legacy_result(window):
    """Restaura exactamente las claves históricas y encadena cierres."""
    out = {key: window[key] for key in ("O", "H", "L", "C", "V", "days")}
    last_close = np.full(len(out["days"]), np.nan)
    for index, row in enumerate(out["C"]):
        finite = np.flatnonzero(~np.isnan(row))
        if len(finite):
            last_close[index] = row[finite[-1]]
    previous_close = np.full(len(out["days"]), np.nan)
    previous = np.nan
    for index, close in enumerate(last_close):
        previous_close[index] = previous
        if not np.isnan(close):
            previous = close
    out["prev_close"] = previous_close
    out["rth_close"] = last_close
    return out


def build_session_matrices(df, start_h=9, start_m=30, duration_min=RTH_MIN):
    """API existente: ventana ET configurable con resultado histórico.

    Se conservan firma y claves. Internamente usa la primitiva general y, como
    antes, infiere días desde los datos; quien necesite inferencia formal debe
    usar ``minute_window_matrices(..., session_days=...)`` o el wrapper YM.
    """
    for value, field in (
        (start_h, "start_h"),
        (start_m, "start_m"),
        (duration_min, "duration_min"),
    ):
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError("%s debe ser entero" % field)
    if not 0 <= start_h <= 23 or not 0 <= start_m <= 59:
        raise ValueError("hora de inicio fuera de rango")
    if not 1 <= duration_min < 24 * 60:
        raise ValueError("duration_min fuera de rango")
    start = start_h * 60 + start_m
    end = (start + duration_min) % (24 * 60)
    window = minute_window_matrices(df, start=start, end=end)
    return _legacy_result(window)


def rth_matrices(df):
    """RTH ``[09:30,16:00)`` — alias compatible de 390 minutos."""
    return build_session_matrices(df, start_h=9, start_m=30, duration_min=RTH_MIN)


def valid_days_mask(O, min_minutes=300):
    """Días con primer minuto presente y cobertura mínima; API histórica."""
    if not isinstance(min_minutes, int) or isinstance(min_minutes, bool):
        raise ValueError("min_minutes debe ser entero")
    if O.ndim != 2 or not 1 <= min_minutes <= O.shape[1]:
        raise ValueError("min_minutes fuera de rango")
    has_open = ~np.isnan(O[:, 0])
    coverage = (~np.isnan(O)).sum(axis=1) >= min_minutes
    return has_open & coverage


def valid_window_mask(O, *, min_minutes=None):
    """Validez de una ventana genérica; por defecto exige cobertura completa."""
    if O.ndim != 2 or O.shape[1] == 0:
        raise ValueError("O debe ser matriz día × minuto no vacía")
    required = O.shape[1] if min_minutes is None else min_minutes
    return valid_days_mask(O, min_minutes=required)


def ym_prerange_matrices(df, *, session_days):
    """Ventana candidata YM-PRERANGE ``[08:12,09:12)`` en Nueva York.

    ``session_days`` es obligatorio: la función formal no puede construir el
    denominador únicamente con días que casualmente tienen datos.
    """
    out = minute_window_matrices(
        df,
        start=YM_PRERANGE_START,
        end=YM_PRERANGE_END,
        session_days=session_days,
    )
    valid = valid_window_mask(out["O"])
    highs = np.full(len(out["days"]), np.nan)
    lows = np.full(len(out["days"]), np.nan)
    for index in np.flatnonzero(valid):
        highs[index] = float(np.nanmax(out["H"][index]))
        lows[index] = float(np.nanmin(out["L"][index]))
    out["valid"] = valid
    out["range_high"] = highs
    out["range_low"] = lows
    out["range_width"] = highs - lows
    out["window_id"] = "YM-PRERANGE@America/New_York/[08:12,09:12)"
    return out
