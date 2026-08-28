"""Mapeo tick -> sesion CME (trade date) en America/Chicago.

Regla congelada (roll_rule_id independiente; ver docs/research):

    trade_date(t) = fecha local Chicago de t                 si hora_local <  17:00
                    fecha local Chicago de t + 1 dia         si hora_local >= 17:00

Esto implementa la convencion Globex: la sesion del trade date D abre a las
17:00 CT de D-1 y cierra a las 16:00 CT de D, con pausa de mantenimiento
16:00-17:00 CT.

Por que importa: el Contrato Kaggle v2 bloquea el holdout "por session_key y
session_date en America/Chicago, no solo por un timestamp UTC". Un corte UTC
en 2026-07-01T00:00:00Z conserva ticks de 2026-06-30 19:00 CT que pertenecen
al trade date 2026-07-01, es decir al holdout. Ese es un leak silencioso.

Las transiciones DST se derivan de la tzdata del sistema por biseccion exacta
al segundo. No hay reglas de DST hardcodeadas.

Solo numpy + stdlib.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

import numpy as np

CHICAGO = ZoneInfo("America/Chicago")
SESSION_OPEN_HOUR_CT = 17
MAINT_START_HOUR_CT = 16
NS_PER_SEC = 1_000_000_000
SEC_PER_DAY = 86_400
SEC_PER_MIN = 60
_EPOCH_ORDINAL = date(1970, 1, 1).toordinal()

# Rango de anios cubierto por la tabla de transiciones. Fuera de rango se
# levanta excepcion en vez de asumir un offset.
_TZ_YEAR_MIN = 2015
_TZ_YEAR_MAX = 2035


def _offset_seconds_at(ts_s: int) -> int:
    """Offset UTC de Chicago (segundos) en un instante UTC dado."""
    dt = datetime.fromtimestamp(int(ts_s), tz=timezone.utc).astimezone(CHICAGO)
    off = dt.utcoffset()
    assert off is not None
    return int(off.total_seconds())


def build_offset_table(
    year_min: int = _TZ_YEAR_MIN, year_max: int = _TZ_YEAR_MAX
) -> tuple[np.ndarray, np.ndarray]:
    """Tabla (instantes_utc_seg, offset_seg) de transiciones de Chicago.

    Muestreo diario para detectar el cambio y biseccion al segundo para el
    instante exacto. Determinista y auditable contra `zdump`.
    """
    t0 = int(datetime(year_min, 1, 1, tzinfo=timezone.utc).timestamp())
    t1 = int(datetime(year_max + 1, 1, 1, tzinfo=timezone.utc).timestamp())
    grid = list(range(t0, t1 + SEC_PER_DAY, SEC_PER_DAY))
    offs = [_offset_seconds_at(t) for t in grid]
    trans = [t0]
    vals = [offs[0]]
    for i in range(1, len(grid)):
        if offs[i] != offs[i - 1]:
            lo, hi = grid[i - 1], grid[i]
            prev = offs[i - 1]
            while hi - lo > 1:
                mid = (lo + hi) // 2
                if _offset_seconds_at(mid) == prev:
                    lo = mid
                else:
                    hi = mid
            trans.append(hi)
            vals.append(offs[i])
    return np.asarray(trans, dtype=np.int64), np.asarray(vals, dtype=np.int64)


_TRANS_S, _OFFS_S = build_offset_table()
_TZ_MIN_S = int(_TRANS_S[0])
_TZ_MAX_S = int(datetime(_TZ_YEAR_MAX + 1, 1, 1, tzinfo=timezone.utc).timestamp())


def chicago_offset_seconds(ts_utc_ns: np.ndarray) -> np.ndarray:
    """Offset UTC de Chicago para cada timestamp (vectorizado, exacto)."""
    ts_s = np.asarray(ts_utc_ns, dtype=np.int64) // NS_PER_SEC
    if ts_s.size:
        lo = int(ts_s.min())
        hi = int(ts_s.max())
        if lo < _TZ_MIN_S or hi >= _TZ_MAX_S:
            raise ValueError(
                f"timestamp fuera de la tabla tz [{_TZ_YEAR_MIN},{_TZ_YEAR_MAX}]: "
                f"min={lo} max={hi}"
            )
    idx = np.searchsorted(_TRANS_S, ts_s, side="right") - 1
    return _OFFS_S[idx]


def _ymd_from_epoch_days(days: np.ndarray) -> np.ndarray:
    """Dias-desde-epoch (calendario local) -> entero YYYYMMDD."""
    days = np.asarray(days, dtype=np.int64)
    if days.size == 0:
        return np.zeros(0, dtype=np.int32)
    uniq, inv = np.unique(days, return_inverse=True)
    out = np.empty(uniq.shape, dtype=np.int32)
    for i, d in enumerate(uniq):
        dd = date.fromordinal(_EPOCH_ORDINAL + int(d))
        out[i] = dd.year * 10000 + dd.month * 100 + dd.day
    return out[inv].astype(np.int32)


def local_parts(ts_utc_ns: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Devuelve (dias_locales_desde_epoch, segundos_del_dia_local)."""
    ts_s = np.asarray(ts_utc_ns, dtype=np.int64) // NS_PER_SEC
    local_s = ts_s + chicago_offset_seconds(ts_utc_ns)
    day = np.floor_divide(local_s, SEC_PER_DAY)
    sod = local_s - day * SEC_PER_DAY
    return day, sod


def trade_date_ymd(ts_utc_ns: np.ndarray) -> np.ndarray:
    """Trade date CME como entero YYYYMMDD (int32)."""
    day, sod = local_parts(ts_utc_ns)
    day = day + (sod >= SESSION_OPEN_HOUR_CT * 3600).astype(np.int64)
    return _ymd_from_epoch_days(day)


def minutes_since_session_open(ts_utc_ns: np.ndarray) -> np.ndarray:
    """Minutos transcurridos desde la apertura (17:00 CT) del trade date.

    Rango 0..1439. La pausa de mantenimiento cae en 1380..1439.
    """
    _, sod = local_parts(ts_utc_ns)
    shifted = (sod - SESSION_OPEN_HOUR_CT * 3600) % SEC_PER_DAY
    return (shifted // SEC_PER_MIN).astype(np.int32)


def is_maintenance_break(ts_utc_ns: np.ndarray) -> np.ndarray:
    """True si el tick cae en la pausa diaria 16:00-17:00 CT."""
    _, sod = local_parts(ts_utc_ns)
    return (sod >= MAINT_START_HOUR_CT * 3600) & (sod < SESSION_OPEN_HOUR_CT * 3600)


def ymd_to_date(ymd: int) -> date:
    ymd = int(ymd)
    return date(ymd // 10000, (ymd // 100) % 100, ymd % 100)


def ymd_weekday(ymd: int) -> int:
    """0=lunes ... 6=domingo."""
    return ymd_to_date(ymd).weekday()


def session_bounds_utc_ns(ymd: int) -> tuple[int, int]:
    """Instantes UTC (ns) de apertura y cierre de la sesion de trade date ymd.

    Apertura: 17:00 CT del dia anterior. Cierre: 16:00 CT del propio dia.
    """
    d = ymd_to_date(ymd)
    prev = date.fromordinal(d.toordinal() - 1)
    open_ct = datetime(
        prev.year, prev.month, prev.day, SESSION_OPEN_HOUR_CT, 0, 0, tzinfo=CHICAGO
    )
    close_ct = datetime(
        d.year, d.month, d.day, MAINT_START_HOUR_CT, 0, 0, tzinfo=CHICAGO
    )
    return (
        int(open_ct.timestamp()) * NS_PER_SEC,
        int(close_ct.timestamp()) * NS_PER_SEC,
    )
