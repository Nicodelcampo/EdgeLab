"""Calendario de sesiones CME (ETH: 17:00 CT -> 16:00 CT, DST-aware).

Replica la semantica del SessionIterator de NT8 con el template CME US
Index/FX Futures ETH. Los cierres de sesion son lunes-viernes 16:00 CT;
cada sesion abre 17:00 CT del dia calendario anterior (domingo 17:00 para
la sesion del lunes). Feriados NO modelados: declarado; si el oraculo NT8
difiere en un feriado, aparece como diff de paridad y se documenta.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

CT = ZoneInfo("America/Chicago")
NS = 1_000_000_000


def _local(ts_ns: int) -> datetime:
    return datetime.fromtimestamp(ts_ns / 1e9, tz=timezone.utc).astimezone(CT)


def session_end_ns(ts_ns: int) -> int:
    """Proximo cierre de sesion (16:00 CT, lun-vie) estrictamente > ts."""
    d = _local(ts_ns)
    cand = d.replace(hour=16, minute=0, second=0, microsecond=0)
    while cand <= d or cand.weekday() >= 5:
        cand = (cand + timedelta(days=1)).replace(hour=16, minute=0, second=0, microsecond=0)
    return int(cand.timestamp() * NS)


def session_begin_ns(ts_ns: int) -> int:
    """Inicio real (17:00 CT) de la sesion que contiene ts.
    Para la sesion que cierra el lunes, abre el domingo 17:00 CT."""
    end_local = _local(session_end_ns(ts_ns))
    beg = (end_local - timedelta(days=1)).replace(hour=17, minute=0, second=0, microsecond=0)
    # si el dia previo al cierre es sabado (no ocurre con cierres lun-vie,
    # salvo lunes -> domingo, que es valido), no hay ajuste extra
    return int(beg.timestamp() * NS)


def session_key(ts_ns: int) -> str:
    """Trade date (fecha local CT del cierre de la sesion que contiene ts)."""
    return _local(session_end_ns(ts_ns)).strftime("%Y-%m-%d")
