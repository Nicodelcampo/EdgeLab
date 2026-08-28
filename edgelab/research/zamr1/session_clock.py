# -*- coding: utf-8 -*-
"""Reloj de sesión CME ETH para ZAMR-1.

`session_date_ct` en first_touch_census.py devuelve la fecha civil Chicago.
Eso NO es la sesión CME: un tick a las 17:00 CT pertenece al trade date
siguiente. Esta convención replica `edgelab.bridge.bars.session_ids`.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

CHICAGO = ZoneInfo("America/Chicago")
CUTOVER_HOUR = 17


def session_date_cme(ts_ns: int) -> str:
    if not isinstance(ts_ns, int) or isinstance(ts_ns, bool):
        raise TypeError("ts_ns debe ser int")
    local = datetime.fromtimestamp(ts_ns / 1e9, tz=timezone.utc).astimezone(CHICAGO)
    if local.hour >= CUTOVER_HOUR:
        local = local + timedelta(days=1)
    return local.date().isoformat()


def session_date_from_unix_ms(unix_ms: int) -> str:
    return session_date_cme(int(unix_ms) * 1_000_000)
