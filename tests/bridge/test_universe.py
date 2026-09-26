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


def test_un_contrato_deja_de_ser_front_cuando_arranca_el_siguiente():
    """La ventana tiene DOS bordes. Sin el de arriba, el 2026-03-13 satisface el
    front month de `03-26` (desde 2025-12-12) Y el de `06-26` (desde 2026-03-13)
    a la vez, y la misma sesión queda reclamada por dos contratos."""
    r = U.evaluar_dia("6E 03-26", "2026-03-13", _dia_normal(2026, 3, 13))
    assert any(m["code"] == "POST_FRONT_MONTH" for m in r["motivos"])


def test_el_contrato_entrante_si_es_front_ese_mismo_dia():
    """El borde es [desde, hasta): el día del cruce pertenece al NUEVO."""
    r = U.evaluar_dia("6E 06-26", "2026-03-13", _dia_normal(2026, 3, 13))
    assert not any(m["code"] in ("PRE_FRONT_MONTH", "POST_FRONT_MONTH")
                   for m in r["motivos"])


def test_el_contrato_mas_nuevo_queda_abierto():
    """No hay un `desde` posterior contra el cual cerrarlo: no se inventa uno."""
    r = U.evaluar_dia("6E 09-26", "2026-07-20", _dia_normal(2026, 7, 20))
    assert not any(m["code"] == "POST_FRONT_MONTH" for m in r["motivos"])


def test_el_cierre_se_deriva_por_INSTRUMENTO_no_global():
    """ES y NQ rollan distinto que 6E. Un `desde` de otro instrumento no puede
    cerrar la ventana de éste."""
    hasta_6e = U.hasta_de_front_month("6E 03-26")
    assert hasta_6e == U.FRONT_MONTH["6E 06-26"]["desde"]


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


# ------------------------------------------- tipo de día (corrección 2026-07-27)
def _viernes(y=2026, m=7, d=10):
    """Viernes real: opera 00:00–15:59 CT y NO reabre."""
    return sorted(_ns(y, m, d, hh, mm) for hh in range(0, 16) for mm in (0, 20, 40))


def _domingo(y=2026, m=7, d=12):
    """Domingo real: abre 17:00 CT y sigue hasta la medianoche."""
    return sorted(_ns(y, m, d, hh, mm) for hh in range(17, 24) for mm in (0, 20, 40))


def test_viernes_completo_es_APTO():
    """REGRESIÓN: los 56 viernes del censo caían por SIN_HUECO_DE_MANTENIMIENTO.

    Un viernes cierra 16:00 y no reabre, así que no PUEDE tener un hueco que
    cubra las 16:00. El chequeo no le aplica.
    """
    r = U.evaluar_dia("6E 09-26", "2026-07-10", _viernes())
    assert r["tipo_de_dia"] == U.CIERRE_SEMANAL
    assert r["estado"] == "APTO", r["motivos"]
    assert r["detalle"]["hueco_mantenimiento"]["code"] == "NO_APLICA"


def test_domingo_completo_es_APTO():
    """REGRESIÓN: los 60 domingos caían igual. Un domingo abre 17:00."""
    r = U.evaluar_dia("6E 09-26", "2026-07-12", _domingo())
    assert r["tipo_de_dia"] == U.APERTURA_SEMANAL
    assert r["estado"] == "APTO", r["motivos"]


def test_lunes_a_jueves_SIGUE_exigiendo_el_hueco():
    """La corrección no puede aflojar el chequeo donde sí aplica."""
    ts = sorted(_dia_normal() + [_ns(2026, 7, 14, 16, mm) for mm in (5, 25, 45)])
    r = U.evaluar_dia("6E 09-26", "2026-07-14", ts)
    assert r["tipo_de_dia"] == U.COMPLETO
    assert any(m["code"] == "SIN_HUECO_DE_MANTENIMIENTO" for m in r["motivos"])


def test_sabado_con_ticks_es_fallo_duro():
    """El sábado 2025-09-13 con 10 ticks salía APTO. CME no opera los sábados."""
    ts = sorted(_ns(2026, 7, 11, hh, 0) for hh in (14, 15, 18, 20, 21))
    r = U.evaluar_dia("6E 09-26", "2026-07-11", ts)
    assert r["estado"] == "DEFECTUOSO"
    assert any(m["code"] == "SABADO_SIN_SESION" for m in r["motivos"])


def test_dia_vacio_no_pasa_por_pocos_ticks():
    """El otro modo de falla del sábado: con 10 ticks en 7 horas CUALQUIER hueco
    cubre las 16:00, así que `hueco_mantenimiento` pasaba. La cobertura horaria
    es la que lo atrapa."""
    ts = sorted([_ns(2026, 7, 14, 14, 0), _ns(2026, 7, 14, 15, 0),
                 _ns(2026, 7, 14, 21, 0), _ns(2026, 7, 14, 22, 0)])
    r = U.evaluar_dia("6E 09-26", "2026-07-14", ts)
    assert r["estado"] == "DEFECTUOSO"
    assert any(m["code"] == "COBERTURA_HORARIA_INSUFICIENTE" for m in r["motivos"])


def test_un_martes_sin_su_tarde_NO_se_hace_pasar_por_viernes():
    """Fail-closed: el tipo se deriva del dato, pero tiene que ser posible en
    ese día de la semana. Si no, faltarle 7 horas a un martes sería gratis."""
    r = U.evaluar_dia("6E 09-26", "2026-07-14", _viernes(2026, 7, 14))
    assert r["tipo_de_dia"] == U.CIERRE_SEMANAL
    assert any(m["code"] == "TIPO_DE_DIA_IMPOSIBLE" for m in r["motivos"])


def test_el_cierre_temprano_declarado_se_clasifica_solo():
    """Derivar del dato y no del calendario hace que los feriados salgan solos."""
    ts = sorted(_ns(2026, 7, 3, hh, mm) for hh in range(0, 15) for mm in (0, 20, 40))
    r = U.evaluar_dia("6E 09-26", "2026-07-03", ts)
    assert r["tipo_de_dia"] == U.CIERRE_SEMANAL
    assert r["estado"] == "APTO", r["motivos"]


def test_la_bateria_esta_completa():
    """Si alguien agrega un chequeo y olvida enchufarlo, esto lo dice."""
    r = U.evaluar_dia("6E 09-26", "2026-07-14", _dia_normal())
    assert set(r["detalle"]) == set(U.BATERIA)
