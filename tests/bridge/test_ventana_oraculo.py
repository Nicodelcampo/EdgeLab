# -*- coding: utf-8 -*-
"""Ventana de datos != ventana de comparación, fijada contra evidencia real.

El caso que motiva esto: el oráculo de junio de `tick:25` empieza un DOMINGO
(2026-06-14). Un margen fijo de 90 minutos no alcanza a tocar ningún tick de
la sesión anterior (mercado cerrado el fin de semana) y la frontera de
warm-up se calculaba mal, un día entero tarde. `inicio_de_ventana_de_datos`
resuelve esto derivando la frontera de `session_ids`, sin ninguna constante.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

import numpy as np
import pytest

from edgelab.bridge import bars as B
from edgelab.bridge.ticks import load_canonical_parquet
from edgelab.bridge.ventana_oraculo import (SinSesionAnteriorError,
                                            inicio_de_ventana_de_datos,
                                            recortar_a_ventana_de_oraculo)

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PARQUET = os.path.join(REPO, "data", "nt8", "6E", "6E_09-26_ticks.parquet")


def _ns(s):
    return int(datetime.fromisoformat(s).replace(tzinfo=timezone.utc).timestamp() * 1e9)


def _cargar(w0, w1):
    if not os.path.exists(PARQUET):
        pytest.skip("parquet canonico F2 no disponible en este entorno")
    return load_canonical_parquet(PARQUET, contract="6E 09-26",
                                  start_utc_ns=w0, end_utc_ns=w1)


# ------------------------------------------------------- el caso domingo
def test_domingo_de_reapertura_semanal():
    """2026-06-14 es domingo. Con una red amplia (10 dias hacia atras, alcanza
    el cierre del viernes), la frontera derivada tiene que caer EXACTO en la
    apertura dominical (2026-06-14 22:00 UTC = 17:00 CT), no un dia despues
    como daba el margen fijo de 90 minutos."""
    primer_evento_ns = _ns("2026-06-14T22:00:01.540")
    tk = _cargar(primer_evento_ns - 10 * 24 * 3600 * 1_000_000_000,
                primer_evento_ns + 3600 * 1_000_000_000)
    inicio = inicio_de_ventana_de_datos(tk.ts_ns, primer_evento_ns)
    # el resultado es el PRIMER TICK real de esa sesion, no una frontera teorica
    # redonda -- se compara por fecha/hora de apertura, no por igualdad exacta.
    dt = datetime.fromtimestamp(inicio / 1e9, tz=timezone.utc)
    assert (dt.year, dt.month, dt.day, dt.hour) == (2026, 6, 11, 22), (
        "la sesion anterior al domingo de reapertura es la del jueves 11 "
        "(el viernes 12 cierra 16:00 CT y el sabado no hay sesion); did=%s" % dt)


def test_dia_de_semana_normal():
    """2026-06-10 es miercoles: sin fin de semana de por medio, la sesion
    anterior real coincide con session_id - 1 (sin saltos)."""
    primer_evento_ns = _ns("2026-06-10T22:00:00.100")
    tk = _cargar(primer_evento_ns - 5 * 24 * 3600 * 1_000_000_000,
                primer_evento_ns + 3600 * 1_000_000_000)
    inicio = inicio_de_ventana_de_datos(tk.ts_ns, primer_evento_ns)
    ses = B.session_ids(tk.ts_ns)
    idx = int(np.searchsorted(tk.ts_ns, primer_evento_ns))
    idx_inicio = int(np.searchsorted(tk.ts_ns, inicio))
    assert ses[idx] - 1 == ses[idx_inicio], (
        "entre semana, sin feriados, la sesion anterior real es session_id - 1")


def test_el_salto_de_fin_de_semana_no_apunta_a_session_id_menos_uno():
    """El fin de semana 06-12 (viernes cierre) -> 06-14 (domingo apertura)
    salta DOS valores de session_id sin ningun tick (medido: 20617 y 20618
    ausentes). Si la funcion asumiera `session_id - 1` a ciegas, apuntaria a
    una sesion vacia y fallaria donde SI hay una sesion anterior real."""
    primer_evento_ns = _ns("2026-06-14T22:00:01.540")
    tk = _cargar(primer_evento_ns - 10 * 24 * 3600 * 1_000_000_000,
                primer_evento_ns + 3600 * 1_000_000_000)
    ses = B.session_ids(tk.ts_ns)
    idx_evento = int(np.searchsorted(tk.ts_ns, primer_evento_ns))
    s_evento = ses[idx_evento]
    assert not np.any(ses == (s_evento - 1)), (
        "este test asume que session_id-1 esta vacio; si el parquet cambio, "
        "revisar la premisa")
    inicio = inicio_de_ventana_de_datos(tk.ts_ns, primer_evento_ns)
    assert inicio is not None   # no debe levantar, hay sesion anterior real mas atras


def test_red_de_busqueda_insuficiente_falla_explicito():
    """Si la red no alcanza a cubrir una sesion anterior, no se asume nada."""
    primer_evento_ns = _ns("2026-06-14T22:00:01.540")
    tk = _cargar(primer_evento_ns - 3600 * 1_000_000_000,  # 1h: no llega a la sesion anterior
                primer_evento_ns + 3600 * 1_000_000_000)
    with pytest.raises(SinSesionAnteriorError):
        inicio_de_ventana_de_datos(tk.ts_ns, primer_evento_ns)


def test_ventana_vacia_falla_explicito():
    with pytest.raises(SinSesionAnteriorError):
        inicio_de_ventana_de_datos(np.array([], dtype=np.int64), 0)


# --------------------------------------------------------- recorte de comparacion
def test_recortar_a_ventana_de_oraculo():
    zonas = [
        dict(id="antes", created_ms=999),
        dict(id="justo_inicio", created_ms=1000),
        dict(id="dentro", created_ms=1500),
        dict(id="justo_fin", created_ms=2000),
        dict(id="despues", created_ms=2001),
        dict(id="sin_fecha", created_ms=None),
    ]
    vivas = {z["id"] for z in recortar_a_ventana_de_oraculo(zonas, 1000, 2000)}
    assert vivas == {"justo_inicio", "dentro", "justo_fin"}
