"""Adapter canónico de BigTrap2Absorption al contrato común del bridge.

El kernel histórico devuelve eventos pipe en ``events`` y geometría ``lo/hi``.
El resto del bridge exige ``csv_lines`` y ``bottom/top``. Este adaptador sólo
normaliza el contrato; no cambia detección, orden de eventos ni lifecycle.
"""
from __future__ import annotations

from . import bigtrap2absorption as _impl

NAME = _impl.NAME
DEFAULTS = dict(_impl.DEFAULTS)

_LIFECYCLE = {"InvalidationMode", "MaxAgeBars", "MaxTouches"}
_VISUAL = {"DrawZoneBand"}


def _class_of(key: str) -> str:
    if key in _VISUAL:
        return "visual"
    if key in _LIFECYCLE:
        return "lifecycle"
    return "recompute"


PARAM_SPEC = {
    key: {**meta, "class": meta.get("class", _class_of(key))}
    for key, meta in _impl.PARAM_SPEC.items()
}


def run(ticks, bars=None, footprints=None, params=None, chart_tz="UTC"):
    raw = _impl.run(
        ticks, bars=bars, footprints=footprints, params=params, chart_tz=chart_tz
    )
    zones = []
    for original in raw.get("zones", []):
        z = dict(original)
        z.setdefault("indicator", NAME)
        z.setdefault("bottom", z.get("lo"))
        z.setdefault("top", z.get("hi"))
        z.setdefault("kind", z.get("side"))
        zones.append(z)
    event_lines = list(raw.get("events", []))
    return {
        **raw,
        "indicator": NAME,
        "params": dict(raw.get("params", DEFAULTS)),
        "header": None,
        "csv_lines": event_lines,
        "events": event_lines,
        "zones": zones,
        "params_line": None,
    }
