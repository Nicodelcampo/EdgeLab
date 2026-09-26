"""Composición outcome-free de operabilidad y decongestión de primeros toques.

No mide precios ni resultados: recibe filas ya clasificadas como `valid` cuando
cumplen `k_T > 0` y `j_retorno > k_T`, y publica ambos órdenes posibles:

* A: decongestionar todos los primeros toques y después exigir operabilidad;
* B: exigir operabilidad y después decongestionar las entradas realizables.
"""
from __future__ import annotations

from edgelab.research.first_touch_decongestion import decongest_first_touch_events


def _valid_rows(events: list[dict]) -> list[dict]:
    rows = []
    for index, event in enumerate(events):
        if not isinstance(event, dict):
            raise ValueError("events[%d] debe ser objeto" % index)
        if not isinstance(event.get("valid"), bool):
            raise ValueError("events[%d].valid debe ser bool" % index)
        rows.append(dict(event))
    return rows


def seleccionar_dos_ordenes(events, *, session_date_of_ms, sep_minutes):
    """Devuelve la selección con las dos composiciones auditables.

    El campo `valid` es una clasificación geométrica ya obtenida sin outcomes.
    No se usa para desempatar, ordenar ni calcular el ancla: el orden siempre
    permanece definido por `first_touch_ms`, `created_ms` y `zone_id`.
    """
    rows = _valid_rows(events)
    all_decongested = decongest_first_touch_events(
        rows, session_date_of_ms=session_date_of_ms, sep_minutes=sep_minutes
    )
    operable = [row for row in rows if row["valid"]]
    operable_decongested = decongest_first_touch_events(
        operable, session_date_of_ms=session_date_of_ms, sep_minutes=sep_minutes
    )
    return {
        "orden_a": {
            "definition": "sep_min sobre todos los primeros toques; luego operabilidad",
            "events": [row for row in all_decongested["events"] if row["valid"]],
            "decongestion": all_decongested,
        },
        "orden_b": {
            "definition": "operabilidad; luego sep_min sobre entradas realizables",
            "events": operable_decongested["events"],
            "decongestion": operable_decongested,
        },
    }
