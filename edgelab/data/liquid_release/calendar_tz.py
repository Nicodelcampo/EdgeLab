"""Calendario CME mínimo y verificación de huso a partir del escaneo por hora (D01, D06).

No hay calendario histórico oficial en el repo (D06): este módulo deriva lo que se puede comprobar con los propios datos
y lo declara como tal. Las horas límite (16:00 y 17:00 CT) caen en horas enteras, por eso un offset entero de horas se
evalúa exactamente sobre bins horarios.
"""
from __future__ import annotations

from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from edgelab.data.nt8_timezone import cme_forbidden

CT = ZoneInfo("America/Chicago")
NS_H = 3_600_000_000_000


def raw_hour_index(raw_date: np.ndarray, raw_hour: np.ndarray) -> pd.DatetimeIndex:
    """(yyyymmdd, hora cruda) -> instante 'naive' (se interpreta luego como UTC + offset)."""
    d = pd.to_datetime(raw_date.astype(str), format="%Y%m%d")
    return d + pd.to_timedelta(raw_hour.astype(int), unit="h")


def ct_parts(naive_utc: pd.DatetimeIndex, offset_h: int):
    """Convierte (sello crudo - offset) tratado como UTC a hora de Chicago (DST-aware). -> (weekday, hour, ct_index)."""
    idx = (naive_utc - pd.to_timedelta(offset_h, unit="h")).tz_localize("UTC").tz_convert(CT)
    return idx.weekday.to_numpy(), idx.hour.to_numpy(), idx


def violation_by_offset(bins: pd.DataFrame, offsets=range(-12, 13)) -> dict:
    """Fracción de ticks que cae FUERA de la sesión CME (halt 16-17 CT, fin de semana) para cada offset entero de horas.
    `bins` necesita raw_date, raw_hour, n."""
    naive = raw_hour_index(bins["raw_date"].to_numpy(), bins["raw_hour"].to_numpy())
    n = bins["n"].to_numpy(dtype=np.float64)
    tot = n.sum()
    out = {}
    for o in offsets:
        wd, hr, _ = ct_parts(naive, o)
        out[o] = float(n[cme_forbidden(wd, hr)].sum() / tot) if tot else float("nan")
    return out


def trade_date(naive_utc: pd.DatetimeIndex, offset_h: int = 0) -> np.ndarray:
    """Fecha de trading CME (int yyyymmdd): sesión 17:00-16:00 CT; el tick pertenece al día en que cierra la sesión
    (se corren 7 h hacia adelante en hora de Chicago)."""
    _, _, ct = ct_parts(naive_utc, offset_h)
    td = (ct + pd.Timedelta(hours=7)).normalize().tz_localize(None)
    return (td.year * 10000 + td.month * 100 + td.day).to_numpy()


def in_break(naive_utc: pd.DatetimeIndex, offset_h: int = 0) -> np.ndarray:
    """True si la hora CT cae en la pausa diaria (16:00-17:00 CT) o en el fin de semana cerrado."""
    wd, hr, _ = ct_parts(naive_utc, offset_h)
    return cme_forbidden(wd, hr)


def is_dst_summer(naive_utc: pd.DatetimeIndex) -> np.ndarray:
    """True si la fecha cae en horario de verano de EE.UU. (CDT)."""
    ct = naive_utc.tz_localize("UTC").tz_convert(CT)
    return np.array([bool(t.dst()) for t in ct])
