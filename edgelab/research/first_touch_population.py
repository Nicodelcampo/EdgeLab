"""Población outcome-free de primeros toques para EXPLORE-001."""
from __future__ import annotations


class FirstTouchPopulationError(ValueError):
    pass


def _required_int(row, key, context):
    value = row.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise FirstTouchPopulationError("%s.%s debe ser entero" % (context, key))
    return value


def extract_first_touch_events(indicator_result):
    """Reconstruye un evento por zona: su primer toque posterior a creación.

    No lee precios posteriores, PnL ni outcomes. Falla cerrado si el lifecycle
    no permite probar la regla anti look-ahead de EXPLORE-001.
    """
    if not isinstance(indicator_result, dict):
        raise FirstTouchPopulationError("indicator_result debe ser objeto")
    rows = indicator_result.get("events")
    if not isinstance(rows, list):
        raise FirstTouchPopulationError("events debe ser lista")

    created = {}
    first_touches = {}
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise FirstTouchPopulationError("events[%d] debe ser objeto" % index)
        event_type = row.get("type")
        if event_type not in ("ZONE_CREATED", "ZONE_TOUCHED"):
            continue
        zone_id = row.get("zone_id")
        if not isinstance(zone_id, str) or not zone_id:
            raise FirstTouchPopulationError("events[%d] no identifica zone_id" % index)
        if event_type == "ZONE_CREATED":
            if zone_id in created:
                raise FirstTouchPopulationError("ZONE_CREATED duplicado: %s" % zone_id)
            created[zone_id] = row
            continue
        touch_count = _required_int(row, "touch_count", "events[%d]" % index)
        if touch_count != 1:
            continue
        if zone_id in first_touches:
            raise FirstTouchPopulationError("primer toque duplicado: %s" % zone_id)
        first_touches[zone_id] = row

    zone_kind = {}
    zones = indicator_result.get("zones") or []
    if not isinstance(zones, list):
        raise FirstTouchPopulationError("zones debe ser lista")
    for zone in zones:
        if not isinstance(zone, dict):
            raise FirstTouchPopulationError("zone debe ser objeto")
        zone_id = zone.get("id")
        if isinstance(zone_id, str) and zone_id:
            zone_kind[zone_id] = zone.get("kind")

    output = []
    for zone_id, touch in first_touches.items():
        creation = created.get(zone_id)
        if creation is None:
            raise FirstTouchPopulationError("primer toque sin creación: %s" % zone_id)
        created_bar = _required_int(creation, "bar_index", "creation[%s]" % zone_id)
        touch_bar = _required_int(touch, "bar_index", "touch[%s]" % zone_id)
        created_ms = _required_int(creation, "unix_ms", "creation[%s]" % zone_id)
        first_touch_ms = _required_int(touch, "unix_ms", "touch[%s]" % zone_id)
        if touch_bar <= created_bar:
            raise FirstTouchPopulationError(
                "toque no posterior a barra creadora: %s" % zone_id)
        if first_touch_ms <= created_ms:
            raise FirstTouchPopulationError(
                "timestamp de toque no posterior a creación: %s" % zone_id)
        output.append({
            "zone_id": zone_id,
            "created_bar": created_bar,
            "first_touch_bar": touch_bar,
            "created_ms": created_ms,
            "first_touch_ms": first_touch_ms,
            "kind": zone_kind.get(zone_id),
            "outcomes_accessed": False,
        })
    return sorted(output, key=lambda row: (row["first_touch_ms"], row["zone_id"]))
