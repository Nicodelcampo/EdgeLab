from __future__ import annotations

from diag.tasa_senales.recuento_kT_primer_toque import seleccionar_dos_ordenes
from diag.tasa_senales.recuento_kT_primer_toque_run import resumen_archivo


def _event(zone_id: str, touch_ms: int, created_ms: int, valid: bool) -> dict:
    return {
        "zone_id": zone_id,
        "first_touch_ms": touch_ms,
        "created_ms": created_ms,
        "valid": valid,
    }


def test_orden_b_no_deja_que_un_toque_no_operable_consuma_sep_min():
    """La capacidad sólo se asigna a entradas que realmente pueden operarse.

    `early_invalid` llega primero y queda dentro de los 120 minutos de
    `late_valid`. Aplicar sep_min antes de comprobar excursión+retorno (A)
    elimina el único evento operable; comprobar operabilidad primero (B) lo
    conserva.
    """
    events = [
        _event("early_invalid", 1_000_000, 100, False),
        _event("late_valid", 2_000_000, 200, True),
    ]

    result = seleccionar_dos_ordenes(
        events, session_date_of_ms=lambda _ms: "2026-06-01", sep_minutes=120
    )

    assert [e["zone_id"] for e in result["orden_a"]["events"]] == []
    assert [e["zone_id"] for e in result["orden_b"]["events"]] == ["late_valid"]


def test_ambos_ordenes_respetan_el_reinicio_de_sep_min_por_sesion():
    events = [
        _event("d1", 1_000_000, 100, True),
        _event("d2", 2_000_000, 200, True),
    ]

    result = seleccionar_dos_ordenes(
        events,
        session_date_of_ms=lambda ms: "d1" if ms == 1_000_000 else "d2",
        sep_minutes=120,
    )

    assert [e["zone_id"] for e in result["orden_a"]["events"]] == ["d1", "d2"]
    assert [e["zone_id"] for e in result["orden_b"]["events"]] == ["d1", "d2"]


def test_resumen_archivo_no_serializa_las_filas_individuales():
    measured = {
        "estado": "OK",
        "candidates": [_event("z", 1000, 1, True)],
        "counters": {"retorno_valido": 1},
        "violations": [],
        "zones": 1,
        "first_touches": 1,
    }

    result = resumen_archivo(measured)

    assert result["candidate_count"] == 1
    assert "candidates" not in result
