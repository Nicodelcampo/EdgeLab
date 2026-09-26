# -*- coding: utf-8 -*-
"""Barras de tick con reinicio por sesión — TICKBAR-001, defecto 2 de PRED-003.

El defecto: `build_tick_bars` particionaba GLOBAL (`arange(n)//N`) mientras NT8
**reinicia el conteo en cada frontera de sesión**. Demostrado sobre la captura
`tickbar_frontera2_25t`: la última barra de la sesión cierra corta (19 eventos,
volumen 2700 idéntico al de NT8) y la siguiente arranca en el primer evento
posterior al hueco.

Estos tests fijan las tres cosas que la corrección tiene que cumplir: el
reinicio, la convención de frontera compartida con `sessions.py`, y que la
versión vieja quede documentada como defecto en vez de desaparecer sin rastro.
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import numpy as np
import pytest

from edgelab.bridge import bars as B
from edgelab.bridge import sessions as S
from edgelab.bridge.ticks import TickSeries

CT = ZoneInfo("America/Chicago")
NS = 1_000_000_000


def _ns(y, m, d, hh, mm=0, ss=0):
    """ns UTC. `ss` puede pasar de 59: se propaga a minutos, que es lo comodo
    para generar series sinteticas de N ticks consecutivos."""
    base = datetime(y, m, d, hh, tzinfo=CT) + timedelta(minutes=mm, seconds=ss)
    return int(base.timestamp() * NS)


def _serie(ts):
    ts = np.asarray(sorted(ts), dtype=np.int64)
    n = len(ts)
    return TickSeries(
        ts_ns=ts, price_ticks=np.arange(n, dtype=np.int64) % 7 + 22800,
        volume=np.ones(n, dtype=np.float64), bid_ticks=None, ask_ticks=None,
        sequence=np.arange(n, dtype=np.int64), tick_size=5e-05,
        instrument="6E", contract="6E 09-26", source="test")


def _dos_sesiones(n1=27, n2=30):
    """Sesión A (n1 ticks) + frontera + sesión B (n2 ticks)."""
    a = [_ns(2026, 7, 14, 9, 0, i) for i in range(n1)]          # antes del cierre
    b = [_ns(2026, 7, 14, 18, 0, i) for i in range(n2)]         # tras la reapertura
    return a, b


# ------------------------------------------------------- el reinicio
def test_el_conteo_reinicia_en_la_frontera():
    a, b = _dos_sesiones(27, 30)
    bars = B.build_tick_bars(_serie(a + b), 25)
    tam = np.bincount(bars.tick_bar_idx.astype(np.int64))
    # sesión A: 27 ticks -> 25 + 2 (residual). Sesión B: 30 -> 25 + 5.
    assert list(tam) == [25, 2, 25, 5], list(tam)


def test_sin_reinicio_las_barras_CRUZAN_la_frontera():
    """La semántica vieja, documentada como defecto y no borrada."""
    a, b = _dos_sesiones(27, 30)
    bars = B.build_tick_bars(_serie(a + b), 25, reiniciar_por_sesion=False)
    tam = np.bincount(bars.tick_bar_idx.astype(np.int64))
    assert list(tam) == [25, 25, 7], list(tam)   # la 2a barra cruza la sesión


def test_la_ultima_barra_de_la_sesion_puede_ser_CORTA():
    """Es lo que hace NT8: bar 3770 tuvo 19 de 25 eventos."""
    a, b = _dos_sesiones(19, 25)
    bars = B.build_tick_bars(_serie(a + b), 25)
    tam = np.bincount(bars.tick_bar_idx.astype(np.int64))
    assert list(tam) == [19, 25], list(tam)


def test_ningun_bloque_mezcla_sesiones():
    """P7 de PRED-003."""
    a, b = _dos_sesiones(37, 41)
    ts = np.asarray(sorted(a + b), dtype=np.int64)
    bars = B.build_tick_bars(_serie(a + b), 25)
    ses = B.session_ids(ts)
    for k in np.unique(bars.tick_bar_idx):
        assert len(set(ses[bars.tick_bar_idx == k])) == 1, k


# ------------------------------------------- convención de frontera compartida
def test_convencion_inicio_fin_semiabierta():
    """Un tick EXACTAMENTE en la apertura pertenece a la sesión que abre."""
    ap = _ns(2026, 7, 14, 17, 0, 0)
    ids = B.session_ids(np.array([ap - 1, ap, ap + 1], dtype=np.int64))
    assert ids[0] != ids[1], "el tick de la apertura debe abrir sesión nueva"
    assert ids[1] == ids[2]


def test_la_convencion_coincide_con_sessions_py_en_datos_LIMPIOS():
    """Condición 2: la misma convención que el calendario ya validado 7/7.

    Se evalúa sobre un día limpio — con la ventana 16:00–17:00 VACÍA, que es lo
    que el universo garantiza. En los 9 días defectuosos las dos difieren, y esa
    diferencia es un síntoma del defecto de datos, no de la convención: ahí
    `sessions.py` asigna los ticks del hueco a la sesión siguiente con un
    `begin` posterior a ellos mismos.
    """
    ts = ([_ns(2026, 7, 14, h, m) for h in range(0, 16) for m in (0, 30)]
          + [_ns(2026, 7, 14, h, m) for h in (17, 18, 19) for m in (0, 30)])
    ts = np.asarray(sorted(ts), dtype=np.int64)
    ids = B.session_ids(ts)
    fronteras = np.flatnonzero(np.diff(ids)) + 1
    for i in fronteras:
        assert S.session_key(int(ts[i - 1])) != S.session_key(int(ts[i])), (
            "frontera espuria en %d" % i)


def test_los_dias_defectuosos_son_los_que_discrepan():
    """Deja registrado POR QUÉ discrepan, para que nadie lo lea como un bug de
    la convención: es el bloque duplicado dentro de la ventana cerrada."""
    ts = sorted([_ns(2026, 6, 24, h, m) for h in range(0, 24) for m in (0, 30)])
    ts = np.asarray(ts, dtype=np.int64)          # incluye 16:00 y 16:30
    ids = B.session_ids(ts)
    fronteras = np.flatnonzero(np.diff(ids)) + 1
    espurias = [i for i in fronteras
                if S.session_key(int(ts[i - 1])) == S.session_key(int(ts[i]))]
    assert espurias, "con ticks en la ventana cerrada TIENE que haber discrepancia"


# ------------------------------------------------------------------- higiene
def test_una_sola_sesion_se_comporta_como_antes():
    ts = [_ns(2026, 7, 14, 9, 0, i) for i in range(100)]
    a = B.build_tick_bars(_serie(ts), 25)
    b = B.build_tick_bars(_serie(ts), 25, reiniciar_por_sesion=False)
    assert np.array_equal(a.tick_bar_idx, b.tick_bar_idx)


def test_serie_vacia_falla_ruidosamente():
    with pytest.raises(ValueError):
        B.build_tick_bars(_serie([]), 25)
