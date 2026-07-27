# -*- coding: utf-8 -*-
"""Universo de datos admisibles — batería de integridad.

Incluye los checks de REGRESIÓN del defecto ya demostrado: la ventana de
mantenimiento rellenada con una copia de 13:00–14:00 en 9 días de 6E 09-26.
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from edgelab.bridge import universe as U

CT = ZoneInfo("America/Chicago")
NS = 1_000_000_000


def _ns(y, m, d, hh, mm=0, ss=0):
    return int(datetime(y, m, d, hh, mm, ss, tzinfo=CT).timestamp() * NS)


def _dia_normal(y=2026, m=7, d=14):
    """Sesión sintética con el hueco de mantenimiento REAL: ticks 00:00–16:00
    y 17:00–23:59, nada en el medio."""
    ts = []
    for hh in list(range(0, 16)) + list(range(17, 24)):
        for mm in (0, 20, 40):
            ts.append(_ns(y, m, d, hh, mm))
    return sorted(ts)


def test_un_dia_normal_es_APTO():
    ts = _dia_normal()
    r = U.evaluar_dia("6E 09-26", "2026-07-14", ts)
    assert r["estado"] == "APTO", r["motivos"]


# --------------------------------------------------- regresión del defecto real
def test_la_ventana_rellenada_se_detecta_por_REGLA_no_por_lista():
    """El defecto real: 16:00–17:00 con ticks ⇒ el hueco desaparece.

    Los 9 días de 6E 09-26 caen por acá, sin lista negra. Una lista se
    desactualiza el día que aparezca un décimo día; una regla no.
    """
    ts = sorted(_dia_normal() + [_ns(2026, 7, 14, 16, mm) for mm in (5, 25, 45)])
    r = U.evaluar_dia("6E 09-26", "2026-07-14", ts)
    assert r["estado"] == "DEFECTUOSO"
    codes = {m["code"] for m in r["motivos"]}
    assert "SIN_HUECO_DE_MANTENIMIENTO" in codes
    assert "TICKS_EN_VENTANA_CERRADA" in codes     # los dos, independientes


def test_fail_loud_cuenta_los_ticks_intrusos():
    ts = sorted(_dia_normal() + [_ns(2026, 7, 14, 16, mm) for mm in range(0, 60, 5)])
    r = U.evaluar_dia("6E 09-26", "2026-07-14", ts)
    m = [x for x in r["motivos"] if x["code"] == "TICKS_EN_VENTANA_CERRADA"][0]
    assert m["n"] == 12


def test_exigir_apto_levanta_con_el_motivo():
    ts = sorted(_dia_normal() + [_ns(2026, 7, 14, 16, 30)])
    r = U.evaluar_dia("6E 09-26", "2026-07-14", ts)
    with pytest.raises(U.IntegridadError) as e:
        U.exigir_apto(r)
    assert "NO pertenece al universo" in str(e.value)


# ------------------------------------------------------------------ front month
def test_antes_del_front_month_no_entra():
    r = U.evaluar_dia("6E 09-26", "2026-06-11", _dia_normal(2026, 6, 11))
    assert r["estado"] == "DEFECTUOSO"
    assert any(m["code"] == "PRE_FRONT_MONTH" for m in r["motivos"])


def test_el_dia_del_rolo_ya_entra():
    r = U.evaluar_dia("6E 09-26", "2026-06-12", _dia_normal(2026, 6, 12))
    assert not any(m["code"] == "PRE_FRONT_MONTH" for m in r["motivos"])


def test_contrato_sin_front_month_medido_no_se_admite():
    """Fail-closed: no se admite un contrato cuyo front month nadie midió."""
    r = U.evaluar_dia("XX 12-99", "2026-07-14", _dia_normal())
    assert any(m["code"] == "CONTRATO_SIN_FRONT_MONTH_DECLARADO" for m in r["motivos"])


# ----------------------------------------------------------- bordes de la semana
def test_viernes_con_cierre_tardio_cae():
    """El viernes 2026-06-26 real cerró 18:59 en vez de 15:59."""
    ts = [_ns(2026, 6, 26, hh, mm) for hh in list(range(0, 16)) + [17, 18]
          for mm in (0, 30)]
    r = U.evaluar_dia("6E 09-26", "2026-06-26", sorted(ts))
    assert any(m["code"] == "CIERRE_SEMANAL_TARDIO" for m in r["motivos"])


def test_viernes_con_cierre_temprano_DECLARADO_no_cae_por_eso():
    """2026-07-03 cierra 15:00 CT: es feriado observado, está declarado."""
    ts = sorted([_ns(2026, 7, 3, hh, mm) for hh in range(0, 15) for mm in (0, 30)])
    r = U.evaluar_dia("6E 09-26", "2026-07-03", ts)
    assert not any(m["code"] == "CIERRE_SEMANAL_TARDIO" for m in r["motivos"])


def test_apertura_dominical_temprana_cae():
    ts = sorted([_ns(2026, 7, 12, hh, 0) for hh in (16, 17, 18, 19)])
    r = U.evaluar_dia("6E 09-26", "2026-07-12", ts)
    assert any(m["code"] == "APERTURA_DOMINICAL_TEMPRANA" for m in r["motivos"])


# --------------------------------------------------------------- higiene basica
def test_timestamps_no_monotonos():
    ts = _dia_normal()
    ts[10], ts[11] = ts[11], ts[10]
    r = U.evaluar_dia("6E 09-26", "2026-07-14", ts)
    assert any(m["code"] == "TIMESTAMPS_NO_MONOTONOS" for m in r["motivos"])


def test_precio_fuera_de_grilla():
    ts = _dia_normal()
    r = U.evaluar_dia("6E 09-26", "2026-07-14", ts, price_ticks=[1.0] * (len(ts) - 1) + [1.5])
    assert any(m["code"] == "PRECIO_FUERA_DE_GRILLA" for m in r["motivos"])


def test_sin_ticks_es_INDETERMINADO_no_apto():
    """Un día que no se puede evaluar no es un día limpio."""
    r = U.evaluar_dia("6E 09-26", "2026-07-14", [])
    assert r["estado"] == "INDETERMINADO"


def test_la_bateria_esta_completa():
    """Si alguien agrega un chequeo y olvida enchufarlo, esto lo dice."""
    r = U.evaluar_dia("6E 09-26", "2026-07-14", _dia_normal())
    assert set(r["detalle"]) == set(U.BATERIA)
