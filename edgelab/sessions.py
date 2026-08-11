"""Sesiones del ES/NQ: matrices dia × minuto en hora de Nueva York.

Convierte velas M1 (indice UTC naive) a matrices (n_dias, duration_min) de
O/H/L/C/V para una ventana horaria ET, manejando DST via pytz
(America/New_York). Todo point-in-time por construccion (solo reorganiza
datos).

## Alcance declarado — leer antes de usar con una ventana nueva

`build_session_matrices` sólo resuelve ventanas que caen DENTRO del mismo día
calendario ET que `start_h:start_m` (no cruza medianoche). Para 08:12–09:12 ET
(YM-PRERANGE) eso es exacto: la ventana entera cae en el mismo día. Para una
ventana que empiece de noche y termine al día siguiente, esta función
etiqueta cada minuto con el día ET en el que cayó — NO con "la sesión de
trading a la que pertenece" (eso es `edgelab/bridge/sessions.py`,
`session_begin_ns`/`session_end_ns`, que sí modela el cierre 16:00 CT / apertura
17:00 CT del ETH completo). Son dos primitivas distintas para preguntas
distintas: ésta arma una matriz día×minuto de una ventana de reloj fija;
`bridge/sessions.py` etiqueta a qué sesión de trading pertenece un timestamp
cualquiera. No usar ésta para una ventana que cruce medianoche sin extenderla
primero — devolvería el minuto en el día ET equivocado, en silencio.

## Nota de procedencia (2026-08-10)

Generalizada desde la versión original, restringida a RTH 09:30-16:00 ET
(`rth_matrices`, conservada como alias exacto — mismo resultado, ninguna
llamada existente cambia de comportamiento). La generalización se investigó
primero en una sesión paralela (Google Antigravity, otro clon del repo); se
revisó la fuente real antes de portarla —no el resumen de esa sesión— y se
agregaron los tests que no existían.
"""
import numpy as np
import pandas as pd

RTH_MIN = 390  # 09:30 -> 16:00


def build_session_matrices(df, start_h=9, start_m=30, duration_min=RTH_MIN):
    """df: DataFrame OHLCV con DatetimeIndex UTC naive (velas M1).
    `start_h`/`start_m`: inicio de la ventana, hora ET. `duration_min`:
    largo de la ventana en minutos — debe caer dentro del mismo día ET que
    el inicio (ver limitación de medianoche en el docstring del módulo).

    Devuelve dict con: days (fechas ET), O/H/L/C/V (n_dias, duration_min) con
    NaN en minutos faltantes, prev_close (cierre de la ventana del dia
    valido previo)."""
    idx = df.index.tz_localize("UTC").tz_convert("America/New_York")
    et_date = idx.normalize()
    m_of_day = idx.hour * 60 + idx.minute
    m_win = m_of_day - (start_h * 60 + start_m)
    in_window = (m_win >= 0) & (m_win < duration_min)

    sub = df.loc[in_window]
    if not len(sub):
        raise ValueError("sin datos en la ventana solicitada (%02d:%02d, %d min)"
                         % (start_h, start_m, duration_min))
    d = et_date[in_window]
    m = m_win[in_window].to_numpy()
    days = pd.DatetimeIndex(sorted(pd.unique(d)))
    day_pos = pd.Series(np.arange(len(days)), index=days)
    rows = day_pos.loc[d].to_numpy()

    shape = (len(days), duration_min)
    out = {}
    for col in ("open", "high", "low", "close", "volume"):
        M = np.full(shape, np.nan)
        M[rows, m] = sub[col].to_numpy(np.float64)
        out[col[0].upper()] = M
    out["days"] = days

    # cierre de la ventana del dia previo VALIDO (ultimo minuto con dato)
    C = out["C"]
    last_close = np.full(len(days), np.nan)
    for i in range(len(days)):
        row = C[i]
        ok = ~np.isnan(row)
        if ok.any():
            last_close[i] = row[np.flatnonzero(ok)[-1]]
    prev_close = np.full(len(days), np.nan)
    prev = np.nan
    for i in range(len(days)):
        prev_close[i] = prev
        if not np.isnan(last_close[i]):
            prev = last_close[i]
    out["prev_close"] = prev_close
    out["rth_close"] = last_close
    return out


def rth_matrices(df):
    """RTH 09:30–16:00 ET — alias exacto, mismo resultado que siempre."""
    return build_session_matrices(df, start_h=9, start_m=30, duration_min=RTH_MIN)


def valid_days_mask(O, min_minutes=300):
    """Dias con apertura de la ventana presente y cobertura suficiente."""
    has_open = ~np.isnan(O[:, 0])
    coverage = (~np.isnan(O)).sum(axis=1) >= min_minutes
    return has_open & coverage
