"""Firewall del holdout (FASE 3b): guard único + log append-only.

edge_validation_contract.md §G4: prohibido usar el holdout (>= 2026-07-01)
para research económico; permitido SOLO para validaciones target-free, con
log de acceso.
"""
import os

import pytest

from edgelab.research.holdout_guard import (
    HOLDOUT_START_ISO,
    HoldoutViolation,
    check_holdout,
    touches_holdout,
)


def _read_lines(log_path):
    if not os.path.exists(log_path):
        return []
    with open(log_path, encoding="utf-8") as fh:
        return fh.readlines()


def test_development_pre_holdout_ok_no_log(tmp_path):
    lp = str(tmp_path / "log.md")
    # todo el rango es anterior a HOLDOUT_START (2026-07-01)
    check_holdout("2026-06-01T00:00:00", "2026-06-30T23:59:59",
                  purpose="development", caller="test", log_path=lp)
    # sin excepción, y sin log (development seguro no se audita)
    assert not os.path.exists(lp)


def test_development_touching_holdout_raises_and_logs(tmp_path):
    lp = str(tmp_path / "log.md")
    with pytest.raises(HoldoutViolation):
        check_holdout("2026-06-25T00:00:00", "2026-07-05T00:00:00",
                      purpose="development", caller="test-breach", log_path=lp)
    lines = _read_lines(lp)
    assert any("DENIED_holdout_breach" in ln and "test-breach" in ln for ln in lines)


def test_development_entirely_inside_holdout_raises(tmp_path):
    lp = str(tmp_path / "log.md")
    with pytest.raises(HoldoutViolation):
        check_holdout("2026-08-01T00:00:00", "2026-08-02T00:00:00",
                      purpose="development", caller="t", log_path=lp)


def test_target_free_always_allowed_and_logged(tmp_path):
    lp = str(tmp_path / "log.md")
    # incluso con una ventana DENTRO del holdout, target_free se permite
    check_holdout("2026-07-13T22:00:00", "2026-07-16T21:00:00",
                  purpose="target_free_validation", caller="gaps2-parity", log_path=lp)
    lines = _read_lines(lp)
    assert any("ALLOWED" in ln and "gaps2-parity" in ln for ln in lines)


def test_target_free_pre_holdout_also_logged(tmp_path):
    # target_free SIEMPRE se registra, incluso si la ventana ni toca el holdout
    lp = str(tmp_path / "log.md")
    check_holdout("2025-01-01T00:00:00", "2025-01-02T00:00:00",
                  purpose="target_free_validation", caller="t", log_path=lp)
    lines = _read_lines(lp)
    assert any("ALLOWED" in ln for ln in lines)


def test_log_is_append_only(tmp_path):
    lp = str(tmp_path / "log.md")
    check_holdout("2020-01-01T00:00:00", "2020-01-02T00:00:00",
                  purpose="target_free_validation", caller="first", log_path=lp)
    first_len = len(_read_lines(lp))
    check_holdout("2020-01-01T00:00:00", "2020-01-02T00:00:00",
                  purpose="target_free_validation", caller="second", log_path=lp)
    lines = _read_lines(lp)
    assert len(lines) == first_len + 1                  # solo CRECE
    assert any("first" in ln for ln in lines)            # la fila vieja SIGUE
    assert any("second" in ln for ln in lines)           # la fila nueva se agregó


def test_invalid_purpose_rejected(tmp_path):
    lp = str(tmp_path / "log.md")
    with pytest.raises(ValueError):
        check_holdout("2020-01-01T00:00:00", "2020-01-02T00:00:00",
                      purpose="whatever", caller="t", log_path=lp)


def test_boundary_end_exactly_at_holdout_start_touches():
    # "cualquier dato >= HOLDOUT_START" es inclusivo: end_utc == HOLDOUT_START
    # cuenta como que TOCA el holdout.
    assert touches_holdout("2026-06-01T00:00:00", HOLDOUT_START_ISO) is True
    # un instante antes: no toca
    assert touches_holdout("2026-06-01T00:00:00", "2026-06-30T23:59:59.999999") is False


def test_open_ended_range_is_failsafe_treated_as_touching():
    # end_utc=None (sin cota superior) -> fail-safe: se asume que SÍ toca
    assert touches_holdout("2020-01-01T00:00:00", None) is True


def test_default_log_path_points_to_docs():
    from edgelab.research.holdout_guard import DEFAULT_LOG_PATH
    assert DEFAULT_LOG_PATH.replace("\\", "/").endswith("docs/holdout_access_log.md")


# --------------------------------------------------------------------------
# REGLA 95 — la frontera es un sello, no un cursor. Regresión de INC-006.
#
# El 2026-08-01 03:16 un commit `chore` movió la frontera a 2026-08-01 y
# des-selló julio entero. Los tests que había NO lo atajaron: sólo comparaban
# contra `HOLDOUT_START_ISO`, o sea contra el valor ya corrompido. Un test que
# lee la misma constante que el código bajo prueba no prueba nada.
#
# Por eso estos cuatro anclan contra el SELLO (literal, histórico) y contra el
# RELOJ, que son las dos cosas que un editor del futuro no puede redefinir.
# --------------------------------------------------------------------------

def test_el_sello_original_es_el_literal_historico():
    """Ancla dura. Si alguien edita el sello, esto falla y es lo correcto:
    mover el sello es una decisión de Nico, no un refactor."""
    from edgelab.research.holdout_guard import _SELLO_ORIGINAL_ISO
    assert _SELLO_ORIGINAL_ISO == "2026-07-01T00:00:00"


def test_la_frontera_no_se_puede_atrasar_ni_editando_la_declarada():
    """El fix estructural: declarar una frontera POSTERIOR al sello no
    des-sella nada. Es la reproducción exacta del edit de INC-006."""
    from edgelab.research.holdout_guard import _resolver_frontera
    # el edit que causó INC-006, ahora inocuo
    assert _resolver_frontera("2026-08-01T00:00:00") == "2026-07-01T00:00:00"
    assert _resolver_frontera("2026-12-31T00:00:00") == "2026-07-01T00:00:00"
    # adelantarla SÍ se permite: sella MÁS material, nunca menos
    assert _resolver_frontera("2026-06-01T00:00:00") == "2026-06-01T00:00:00"


def test_el_sello_protege_algo_contra_la_fecha_del_sistema():
    """Corre contra el reloj real, no contra un literal.

    INC-006 no fue dañino el día que se escribió: venció solo cuando el reloj
    cruzó la frontera. Un test con fecha fija no puede detectar eso; éste sí,
    y va a fallar el día en que la frontera vuelva a quedar en el futuro."""
    from edgelab.research.holdout_guard import verificar_sello
    verificar_sello()          # levanta SelloInvalido si el holdout quedó vacío


def test_frontera_en_el_futuro_es_sello_invalido():
    """La condición que `verificar_sello` detecta, con la geometría de INC-006:
    frontera 2026-08-01 evaluada el 2026-07-31 => cero días sellados."""
    from datetime import datetime, timezone

    from edgelab.research.holdout_guard import SelloInvalido, verificar_sello
    with pytest.raises(SelloInvalido):
        verificar_sello(datetime(2026, 7, 31, 12, 0, tzinfo=timezone.utc),
                        frontera_iso="2026-08-01T00:00:00")


def test_real_log_file_has_retroactive_gaps2_entry():
    # el log real del repo (no tmp_path) debe tener la fila retroactiva de la
    # validación de paridad de Gaps2 (F4C), append-only desde su creación.
    from edgelab.research.holdout_guard import DEFAULT_LOG_PATH
    lines = _read_lines(DEFAULT_LOG_PATH)
    assert any("Gaps2" in ln and "retroactivo" in ln for ln in lines)
