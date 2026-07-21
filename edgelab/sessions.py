"""Sesiones RTH del ES/NQ: matrices dia × minuto en hora de Nueva York.

Convierte velas M1 (indice UTC naive) a matrices (n_dias, 390) de O/H/L/C/V
para la sesion RTH 09:30-16:00 ET, manejando DST via pytz (America/New_York).
Todo point-in-time por construccion (solo reorganiza datos).
"""
import numpy as np
import pandas as pd

RTH_MIN = 390  # 09:30 -> 16:00


def rth_matrices(df):
    """df: DataFrame OHLCV con DatetimeIndex UTC naive (velas M1).
    Devuelve dict con: days (fechas ET), O/H/L/C/V (n_dias,390) con NaN en
    minutos faltantes, prev_close (cierre RTH del dia valido previo)."""
    idx = df.index.tz_localize("UTC").tz_convert("America/New_York")
    et_date = idx.normalize()
    m_of_day = idx.hour * 60 + idx.minute
    m_rth = m_of_day - (9 * 60 + 30)
    in_rth = (m_rth >= 0) & (m_rth < RTH_MIN)

    sub = df.loc[in_rth]
    if not len(sub):
        raise ValueError("sin datos RTH")
    d = et_date[in_rth]
    m = m_rth[in_rth].to_numpy()
    days = pd.DatetimeIndex(sorted(pd.unique(d)))
    day_pos = pd.Series(np.arange(len(days)), index=days)
    rows = day_pos.loc[d].to_numpy()

    shape = (len(days), RTH_MIN)
    out = {}
    for col in ("open", "high", "low", "close", "volume"):
        M = np.full(shape, np.nan)
        M[rows, m] = sub[col].to_numpy(np.float64)
        out[col[0].upper()] = M
    out["days"] = days

    # cierre RTH del dia previo VALIDO (ultimo minuto con dato)
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


def valid_days_mask(O, min_minutes=300):
    """Dias con apertura 09:30 presente y cobertura suficiente."""
    has_open = ~np.isnan(O[:, 0])
    coverage = (~np.isnan(O)).sum(axis=1) >= min_minutes
    return has_open & coverage
