# -*- coding: utf-8 -*-
"""Tests truth-known para F1.1_nulo_condicional_distancia.py, exigidos por
docs/research/BIGTRAP2_DISTANCE_MATCHED_NULL_PROTOCOL_2026-08-11.md Seccion 10
(13 obligatorios) + puntos adicionales pedidos por el auditor. Valores
conocidos, no solo "no crashea" -- ver docstring de cada test.

outcomes_accessed=False. No se abre el holdout. No se mide P&L/direccion.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[2]
MOD_PATH = REPO / "diag" / "tasa_senales" / "F1.1_nulo_condicional_distancia.py"
sys.path.insert(0, str(REPO))

_spec = importlib.util.spec_from_file_location("f11_ncd", MOD_PATH)
m = importlib.util.module_from_spec(_spec)
sys.modules["f11_ncd"] = m
_spec.loader.exec_module(m)

from edgelab.research.first_touch_census import session_date_ct  # noqa: E402


# ======================================================================
# Fixture sintetica reutilizable -- mercado FLAT por default (nada toca,
# nada invalida) salvo que un test inyecte una excursion especifica.
# ======================================================================

def _flat_bars(n_bars, base_close=10000, base_vol=100.0):
    """high=low=close=base_close en todas las barras (mercado sin movimiento).
    bar_volume constante. Con esto ninguna zona se toca ni se invalida salvo
    que un test edite explicitamente high_t/low_t/close_t en barras puntuales."""
    high_t = np.full(n_bars, base_close, dtype=np.int64)
    low_t = np.full(n_bars, base_close, dtype=np.int64)
    close_t = np.full(n_bars, base_close, dtype=np.int64)
    bar_volume = np.full(n_bars, base_vol, dtype=np.float64)
    return high_t, low_t, close_t, bar_volume


def _sesiones_sinteticas(n_sesiones, bars_por_sesion):
    """rango_sesion: sesion 'S0','S1',... -> (j0,j1) contiguos."""
    rango = {}
    ses_de_barra = []
    j = 0
    for i in range(n_sesiones):
        fecha = "2026-01-%02d" % (i + 1)
        rango[fecha] = (j, j + bars_por_sesion - 1)
        ses_de_barra.extend([fecha] * bars_por_sesion)
        j += bars_por_sesion
    return np.array(ses_de_barra, dtype=object), rango, list(rango.keys())


def _bar_end_ns_real_por_sesion(n_sesiones, bpp, dia_offset_inicial=0, hora_utc=14):
    """bar_end_ns con timestamps REALES (no fechas inventadas): cada sesion
    son `bpp` barras de 1 minuto consecutivas arrancando en un dia calendario
    distinto (un dia UTC de diferencia por sesion, hora fija a media tarde
    UTC para no rozar ningun limite de rollover), para que `session_date_ct`
    (la funcion REAL de produccion, no un mock) resuelva cada sesion a una
    fecha CT propia y estable. Necesario para tests que atraviesan
    `construir_universo_zonas`/`procesar_zonas_de_archivo`, que llaman a
    `session_date_ct(created_ms)` de verdad."""
    base = datetime(2026, 3, 2, hora_utc, 0, 0, tzinfo=timezone.utc)
    bar_end_ns = []
    for s in range(n_sesiones):
        inicio = base + timedelta(days=dia_offset_inicial + s)
        for k in range(bpp):
            t = inicio + timedelta(minutes=k + 1)
            bar_end_ns.append(int(t.timestamp() * 1e9))
    return np.array(bar_end_ns, dtype=np.int64)


def _fixture_reanclaje_end_to_end(n_sesiones=6, bpp=200, padding=2100):
    """Mismo escenario que test_integracion_control_usa_geometria_reanclada_no_la_absoluta
    (sesion 0 = fuente a precio 100, sesiones 1..n-1 = pool de controles a
    precio 1000, toque reanclado inyectado en 1002 el minuto siguiente a cada
    creacion), factorizado para que los tests F0/F3 end-to-end no repitan el
    fixture completo. `bar_end_ns` devuelto es SIEMPRE de largo
    n_activo+padding (a diferencia del test original, que solo lo necesitaba
    sin padding para `sesiones_de_barras`): los tests que corren `main()` de
    punta a punta necesitan que `bar_end_ns` tenga el mismo largo que
    high_t/low_t/close_t/bar_volume, porque ahi es main() quien llama a
    sesiones_de_barras con el `b.end_ns` que devuelve el bars_mod fakeado. El
    padding (misma duracion de barra, ningun `fecha` real lo reclama) da las
    >=max_age_bars=2000 barras futuras que el default de produccion exige,
    sin cruzar medianoche CT."""
    bar_end_ns = _bar_end_ns_real_por_sesion(n_sesiones, bpp)
    fechas_reales = [session_date_ct(int(bar_end_ns[s * bpp]) // 1_000_000) for s in range(n_sesiones)]
    assert len(set(fechas_reales)) == n_sesiones  # sin colisiones de fecha CT
    n_activo = n_sesiones * bpp
    n = n_activo + padding
    cola = bar_end_ns[-1] + (np.arange(1, padding + 1, dtype=np.int64) * 60_000_000_000)
    bar_end_ns_full = np.concatenate([bar_end_ns, cola])

    high_t = np.empty(n, dtype=np.int64)
    low_t = np.empty(n, dtype=np.int64)
    close_t = np.empty(n, dtype=np.int64)
    bar_volume = np.full(n, 100.0, dtype=np.float64)
    for s in range(n_sesiones):
        precio = 100 if s == 0 else 1000  # sesion 0 = fuente; 1..n-1 = pool de controles
        sl = slice(s * bpp, (s + 1) * bpp)
        high_t[sl] = precio
        low_t[sl] = precio
        close_t[sl] = precio
    high_t[n_activo:] = 1000  # padding: mismo precio que los controles, sin toques
    low_t[n_activo:] = 1000
    close_t[n_activo:] = 1000

    minuto_creacion = 70  # >=60: sigma60 causal disponible
    cb_fuente = minuto_creacion
    for s in range(1, n_sesiones):
        # toque SOLO en el precio absoluto 1002 (dentro de [1001,1003]
        # reanclado, fuera de [101,103] absoluto de la fuente).
        high_t[s * bpp + minuto_creacion + 1] = 1002

    ses_de_barra, rango_sesion = m.sesiones_de_barras(bar_end_ns_full, fechas_reales)
    created_ms_fuente = int(bar_end_ns[cb_fuente]) // 1_000_000
    tick_size = 1.0
    kernel_zones = [dict(
        id="zsrc", top=103 * tick_size + tick_size / 2.0, bottom=101 * tick_size - tick_size / 2.0,
        created_bar=cb_fuente, created_ms=created_ms_fuente, kind="trapped_buyers")]
    return dict(kernel_zones=kernel_zones, high_t=high_t, low_t=low_t, close_t=close_t,
               bar_volume=bar_volume, ses_de_barra=ses_de_barra, rango_sesion=rango_sesion,
               fechas_reales=fechas_reales, tick_size=tick_size, n=n, bar_end_ns=bar_end_ns_full)


# ======================================================================
# Reanclaje: el control se evalua con SU PROPIA geometria reanclada, nunca
# con los limites absolutos de la zona fuente (bug real del smoke 2026-08-11,
# corregido antes de aceptar ningun resultado sobre datos reales).
# ======================================================================

def test_reanclaje_geometria_tick_por_tick():
    """Punto 5 pedido: aserciones tick por tick sobre reanclar_geometria."""
    source_lo, source_hi = 101, 103
    source_anchor = 100
    control_anchor = 1000
    rel_lo, rel_hi, control_lo, control_hi = m.reanclar_geometria(
        source_lo, source_hi, source_anchor, control_anchor)
    assert rel_lo == source_lo - source_anchor == 1
    assert rel_hi == source_hi - source_anchor == 3
    assert control_lo - control_anchor == rel_lo
    assert control_hi - control_anchor == rel_hi
    assert control_hi - control_lo == source_hi - source_lo
    assert (control_lo, control_hi) == (1001, 1003)  # exactamente el ejemplo pedido


def test_integracion_control_usa_geometria_reanclada_no_la_absoluta():
    """Punto 4 pedido, end-to-end via procesar_zonas_de_archivo (el helper
    productivo real, no un bypass manual):

    - precio fuente = 100; zona fuente = [101,103];
    - precio del control = 1000; zona ESPERADA del control = [1001,1003];
    - se inyecta un toque UNICAMENTE en el precio absoluto 1002 (dentro de
      [1001,1003], fuera por completo de [101,103]);
    - el control debe registrar el toque (prueba que se reancla);
    - si el bug original siguiera presente (evaluar el control con los
      limites ABSOLUTOS [101,103] de la fuente), el control jamas tocaria,
      porque el precio en esa sesion nunca pasa por 101-103 -- se verifica
      exactamente eso llamando zone_lifecycle a mano con los limites viejos.
    """
    # Sesiones REALES cortas (200 min, muy dentro de un dia calendario CT --
    # nada de cruce de medianoche) para que session_date_ct() las resuelva
    # limpio a una fecha por sesion. procesar_zonas_de_archivo usa el
    # max_age_bars de PRODUCCION (2000, sin override), asi que cada candidato
    # necesita >=2000 barras futuras disponibles -- eso lo da un PADDING sin
    # etiqueta de sesion al final del array (indexar_por_minuto solo itera
    # las sesiones que estan en rango_sesion, asi que el padding nunca se
    # vuelve un candidato: solo aporta "barras futuras" para el horizonte).
    n_sesiones, bpp = 6, 200
    bar_end_ns = _bar_end_ns_real_por_sesion(n_sesiones, bpp)
    fechas_reales = [session_date_ct(int(bar_end_ns[s * bpp]) // 1_000_000) for s in range(n_sesiones)]
    assert len(set(fechas_reales)) == n_sesiones  # 6 fechas CT distintas, sin colisiones

    n_activo = n_sesiones * bpp
    padding = 2100  # > max_age_bars=2000, con margen
    n = n_activo + padding
    high_t = np.empty(n, dtype=np.int64)
    low_t = np.empty(n, dtype=np.int64)
    close_t = np.empty(n, dtype=np.int64)
    bar_volume = np.full(n, 100.0, dtype=np.float64)
    for s in range(n_sesiones):
        precio = 100 if s == 0 else 1000  # sesion 0 = fuente; 1-5 = pool de controles, MISMO precio
        sl = slice(s * bpp, (s + 1) * bpp)
        high_t[sl] = precio
        low_t[sl] = precio
        close_t[sl] = precio
    high_t[n_activo:] = 1000  # padding: mismo precio que los controles, sin toques
    low_t[n_activo:] = 1000
    close_t[n_activo:] = 1000

    minuto_creacion = 70  # >=60: sigma60 causal disponible
    cb_fuente = 0 * bpp + minuto_creacion
    # el "toque" de cada control va en la barra siguiente a su propio minuto de
    # creacion espejada -- precio ABSOLUTO 1002, que cae en [1001,1003]
    # (reanclado) pero NO en [101,103] (absoluto de la fuente).
    for s in range(1, n_sesiones):
        bar_control = s * bpp + minuto_creacion
        high_t[bar_control + 1] = 1002

    # rango_sesion cubre SOLO las 6 sesiones activas -- el padding no tiene
    # etiqueta de sesion y por eso jamas se ofrece como candidato.
    ses_de_barra, rango_sesion = m.sesiones_de_barras(bar_end_ns, fechas_reales)
    created_ms_fuente = int(bar_end_ns[cb_fuente]) // 1_000_000
    tick_size = 1.0  # ticks enteros=precios enteros en este fixture, mas simple de leer
    kernel_zones = [dict(
        id="zsrc", top=103 * tick_size + tick_size / 2.0, bottom=101 * tick_size - tick_size / 2.0,
        created_bar=cb_fuente, created_ms=created_ms_fuente, kind="trapped_buyers")]

    res = m.procesar_zonas_de_archivo(
        kernel_zones, high_t, low_t, close_t, bar_volume,
        ses_de_barra, rango_sesion, fechas_reales, tick_size, n)

    assert len(res["resultados"]) == 1
    fila = res["resultados"][0]
    assert fila["source_anchor_tick"] == 100
    assert fila["rel_lo_tick"] == 1 and fila["rel_hi_tick"] == 3
    assert fila["k_efectivo"] == 5  # sesiones 1-5, las 5 disponibles (el padding no cuenta)
    for ctrl in fila["controles_ledger"]:
        assert ctrl["control_anchor_tick"] == 1000
        assert (ctrl["control_lo_tick"], ctrl["control_hi_tick"]) == (1001, 1003)
        assert ctrl["y_ctrl"] == 1.0  # el toque inyectado en 1002 SI se detecta reanclado
    assert fila["p0_i"] == 1.0  # los 5 controles tocan: prueba que el reanclaje esta conectado

    # Prueba negativa explicita: evaluar esos MISMOS controles con los limites
    # ABSOLUTOS de la fuente (el bug original) da CERO toques -- confirma que
    # [101,103] en la sesion de control "no se usa" porque GEOMETRICAMENTE no
    # puede tocar ahi (precio siempre ~1000).
    for ctrl in fila["controles_ledger"]:
        j = ctrl["bar_index"]
        lc_con_bug = m.zone_lifecycle(101, 103, True, j, high_t, low_t, close_t, n)
        assert m.endpoint_binario(lc_con_bug) == 0.0


def test_zonas_cruzan_frontera_de_sesion_sin_truncar():
    """Punto 6 pedido: bigtrap2.py::update_zones no tiene NINGUNA nocion de
    sesion (verificado leyendo el kernel completo) -- una zona sigue viva y
    evaluable mas alla del final de su propia sesion, acotada solo por
    max_age_bars/horizonte, igual que el kernel. Si alguien truncara por
    error al final de la sesion, este test lo atraparia: el toque vive varias
    sesiones despues de la creacion y sigue contando."""
    n_sesiones, bpp = 4, 50
    high_t, low_t, close_t, _v = _flat_bars(n_sesiones * bpp, base_close=100)
    created_bar = 10  # sesion 0
    # zona [101,103]: NO contiene el close plano=100 (evita que la zona toque
    # desde la primera barra por overlap con el baseline, ver tests 02-05b).
    # el toque ocurre en la sesion 2 (bar 2*bpp+5=105), muy despues de que la
    # sesion 0 (barras 0-49) haya terminado.
    bar_toque = 2 * bpp + 5
    high_t[bar_toque] = 102
    lc = m.zone_lifecycle(101, 103, True, created_bar, high_t, low_t, close_t,
                          n_sesiones * bpp, max_age_bars=2000)
    assert lc["touched_before_removal"] is True
    assert lc["first_touch_age"] == bar_toque - created_bar
    assert lc["first_touch_age"] > bpp  # estrictamente mas alla de una sesion de distancia


# ======================================================================
# 1. Reanclaje conserva rel_lo, rel_hi, altura, distancia y lado tick x tick
# ======================================================================

def test_01_reanclaje_conserva_geometria_tick_por_tick():
    tick_size = 5e-05
    lo_tick, hi_tick = 20000, 20003  # altura 4 ticks
    bottom = lo_tick * tick_size - tick_size / 2.0
    top = hi_tick * tick_size + tick_size / 2.0
    lo2, hi2 = m.tick_bounds_from_price(top, bottom, tick_size)
    assert (lo2, hi2) == (lo_tick, hi_tick)
    altura = hi2 - lo2
    assert altura == 3  # hi_tick - lo_tick (4 ticks de ancho = 3 de diferencia entre bordes)
    # reanclado a otro close: la geometria relativa (rel_lo, rel_hi, altura, lado)
    # se preserva exactamente al sumar el mismo desplazamiento a ambos bordes
    close_fuente, close_control = 19998, 25000
    rel_lo, rel_hi = lo2 - close_fuente, hi2 - close_fuente
    ctrl_lo, ctrl_hi = close_control + rel_lo, close_control + rel_hi
    assert (ctrl_hi - ctrl_lo) == altura
    assert (ctrl_lo - close_control) == rel_lo
    assert (ctrl_hi - close_control) == rel_hi
    # lado: si la fuente esta por encima del close (trapped_buyers), el control
    # reanclado tambien queda por encima de SU close, por construccion (rel_lo>0)
    assert rel_lo > 0  # lo_tick(20000) > close_fuente(19998): confirma el fixture


def test_01b_tick_bounds_from_price_es_exactamente_la_inversa_del_kernel():
    """Genera zone_lo/zone_hi como lo hace bigtrap2.py::emit_side y verifica
    que tick_bounds_from_price recupera el lo_tick/hi_tick original, para un
    barrido de valores (no solo un caso feliz)."""
    tick_size = 5e-05
    for lo_tick in (1, 100, 12345, 99999):
        for ancho in (0, 1, 5, 20):
            hi_tick = lo_tick + ancho
            zone_lo = lo_tick * tick_size - tick_size / 2.0
            zone_hi = hi_tick * tick_size + tick_size / 2.0
            lo2, hi2 = m.tick_bounds_from_price(zone_hi, zone_lo, tick_size)
            assert (lo2, hi2) == (lo_tick, hi_tick), (lo_tick, hi_tick, lo2, hi2)


# ======================================================================
# 2. Zona disponible desde B+1; la barra creadora no toca
# ======================================================================

def test_02_zona_disponible_desde_b_mas_1_creadora_no_toca():
    n = 20
    high_t, low_t, close_t, _v = _flat_bars(n, base_close=100)
    created_bar = 5
    # zona [101,103]: NO contiene el close plano (100), asi que por default
    # ninguna barra la toca. Ahora hago que la barra CREADORA (5) sea la unica
    # que geometricamente tocaria (high=103) -- si el rango incluyera b0=created_bar
    # en vez de created_bar+1, este test fallaria.
    high_t[created_bar] = 103
    lc = m.zone_lifecycle(101, 103, True, created_bar, high_t, low_t, close_t, n)
    # el rango evaluado empieza en B+1=6, donde high vuelve a 100 (no toca) --
    # la excursion de la barra creadora nunca se evalua.
    assert lc["touched_before_removal"] is False
    assert lc["first_touch_age"] is None


# ======================================================================
# 3. Toque seguido de invalidacion en la misma barra cuenta como toque
# ======================================================================

def test_03_toque_e_invalidacion_misma_barra_cuenta_como_toque():
    n = 10
    high_t, low_t, close_t, _v = _flat_bars(n, base_close=100)
    created_bar = 0
    # zona trapped_buyers [101,103] (NO contiene el close plano=100: sin
    # excursion, nunca toca). En bar 3: high=103 (toca), close=104 (adverso, > hi=103)
    high_t[3] = 103
    close_t[3] = 104
    lc = m.zone_lifecycle(101, 103, True, created_bar, high_t, low_t, close_t, n)
    assert lc["removed_age"] == 3
    assert lc["removed_reason"] == "close_through"  # touched=True en esa barra
    assert lc["touched_before_removal"] is True
    assert lc["first_touch_age"] == 3


# ======================================================================
# 4. close_through_gap antes del cruce censura toques posteriores
# ======================================================================

def test_04_close_through_gap_censura_toques_posteriores():
    n = 10
    high_t, low_t, close_t, _v = _flat_bars(n, base_close=100)
    created_bar = 0
    # zona [101,103] (no contiene el close plano=100). bar 2: close=104 (adverso,
    # SIN tocar -- high sigue en 100, fuera de [101,103]) -> close_through_gap
    close_t[2] = 104
    # bar 5: high=102 (tocaria) -- pero la zona YA fue invalidada en bar 2
    high_t[5] = 102
    lc = m.zone_lifecycle(101, 103, True, created_bar, high_t, low_t, close_t, n)
    assert lc["removed_age"] == 2
    assert lc["removed_reason"] == "close_through_gap"
    assert lc["touched_before_removal"] is False  # el toque de bar 5 NUNCA se evalua
    assert lc["first_touch_age"] is None


# ======================================================================
# 5. Expiracion ocurre exactamente cuando age > max_age_bars
# ======================================================================

def test_05_expiracion_exactamente_en_age_mayor_a_max_age_bars():
    n = 20
    high_t, low_t, close_t, _v = _flat_bars(n, base_close=100)
    created_bar = 0
    max_age = 5
    lc = m.zone_lifecycle(99, 101, True, created_bar, high_t, low_t, close_t, n, max_age_bars=max_age)
    # age=5 (== max_age_bars) NO expira; age=6 (> max_age_bars) SI expira.
    assert lc["removed_reason"] == "max_age"
    assert lc["removed_age"] == max_age + 1


def test_05b_toque_en_la_barra_de_expiracion_no_cuenta_el_kernel_hace_continue():
    n = 20
    high_t, low_t, close_t, _v = _flat_bars(n, base_close=100)
    created_bar = 0
    max_age = 5
    # zona [101,103] (no contiene el close plano=100). En la barra donde expira
    # (age=6, bar=6), high=102 tocaria geometricamente -- pero el kernel hace
    # `continue` ANTES de chequear touched en esa barra.
    high_t[6] = 102
    lc = m.zone_lifecycle(101, 103, True, created_bar, high_t, low_t, close_t, n, max_age_bars=max_age)
    assert lc["removed_reason"] == "max_age"
    assert lc["removed_age"] == 6
    assert lc["touched_before_removal"] is False
    assert lc["first_touch_age"] is None


# ======================================================================
# Puntos adicionales del auditor: zona nunca tocada / censura por horizonte
# ======================================================================

def test_zona_nunca_tocada_en_todo_el_horizonte():
    n = 2100
    high_t, low_t, close_t, _v = _flat_bars(n, base_close=100)
    # nunca toca [99,101]: high/low/close siempre en 100, adentro del rango sin
    # cruzarlo hacia afuera -- redefino para que NUNCA sea >= lo y <= hi a la vez
    # con exceso (usamos una zona my lejos: [200,201])
    lc = m.zone_lifecycle(200, 201, True, 0, high_t, low_t, close_t, n, max_age_bars=2000)
    assert lc["touched_before_removal"] is False
    assert lc["first_touch_age"] is None
    assert lc["removed_reason"] == "max_age"  # expira sin haber tocado nunca


def test_zona_activa_al_final_del_horizonte_queda_censurada():
    n = 50
    high_t, low_t, close_t, _v = _flat_bars(n, base_close=100)
    created_bar = 0
    # horizon_cap=10 (mas chico que max_age_bars=2000 y que n): el rango
    # disponible se agota SIN expiracion (age nunca supera max_age_bars=2000)
    # ni invalidacion (mercado flat, sin adverse) -> censurado.
    lc = m.zone_lifecycle(200, 201, True, created_bar, high_t, low_t, close_t, n,
                          max_age_bars=2000, horizon_cap=10)
    assert lc["censored"] is True
    assert lc["removed_reason"] is None
    assert lc["removed_age"] is None


# ======================================================================
# 6/7/8/9. Control: otra sesion, mismo minuto, sin creacion, sin informacion
# futura, mismo horizonte que la fuente
# ======================================================================

def test_06_07_control_otra_sesion_mismo_minuto_sin_creacion_bigtrap():
    n_sesiones, bpp = 5, 30
    ses_de_barra, rango_sesion, fechas = _sesiones_sinteticas(n_sesiones, bpp)
    n = n_sesiones * bpp
    por_minuto = m.indexar_por_minuto(ses_de_barra, rango_sesion, n)

    zona = dict(session_date=fechas[0], minute_of_session=7, created_bar=7)
    creadoras = {7, 37}  # bar 37 = minuto 7 de la sesion 1 (S1): tambien creadora
    candidatos = m.construir_pool_candidatos(zona, por_minuto, creadoras, n, horizon_i=5)

    sesiones_candidatas = {ses for ses, _b in candidatos}
    assert fechas[0] not in sesiones_candidatas  # nunca la propia sesion (#6/#7 auditor)
    for ses, bar_idx in candidatos:
        j0, _j1 = rango_sesion[ses]
        assert (bar_idx - j0) == 7  # mismo minuto de sesion exacto
    assert 37 not in {b for _s, b in candidatos}  # barra creadora excluida (#7 protocolo)
    # S1 (indice de minuto 7 = bar 37) debe estar ausente por ser creadora; las
    # otras 3 sesiones (S2,S3,S4) deben estar presentes
    assert sesiones_candidatas == {fechas[2], fechas[3], fechas[4]}


def test_f1_creadoras_incluye_zonas_excluidas_del_universo_por_top_none():
    """F1 (fix 2026-08-11): una zona con top=None (o created_ms=None, o de
    una sesion fuera de este archivo) queda fuera de `universo`, pero su
    `created_bar` DEBE seguir marcado en `creadoras` -- si no, esa barra se
    cuela como candidato de control aunque BigTrap2 si haya creado una zona
    ahi. Antes del fix, `creadoras.add(cb)` vivia despues de los filtros y
    esto fallaba."""
    n_sesiones, bpp = 3, 100
    bar_end_ns = _bar_end_ns_real_por_sesion(n_sesiones, bpp)
    fechas = [session_date_ct(int(bar_end_ns[s * bpp]) // 1_000_000) for s in range(n_sesiones)]
    ses_de_barra, rango_sesion = m.sesiones_de_barras(bar_end_ns, fechas)
    n = n_sesiones * bpp

    cb_valida = 0 * bpp + 10
    cb_top_none = 1 * bpp + 10  # mismo minuto (10), otra sesion -- candidato natural
    kernel_zones = [
        dict(id="zvalida", top=101 * 1.0 + 0.5, bottom=101 * 1.0 - 0.5,
            created_bar=cb_valida, created_ms=int(bar_end_ns[cb_valida]) // 1_000_000,
            kind="trapped_buyers"),
        dict(id="ztop_none", top=None, bottom=None,
            created_bar=cb_top_none, created_ms=None, kind="trapped_buyers"),
    ]
    universo, creadoras = m.construir_universo_zonas(
        kernel_zones, ses_de_barra, rango_sesion, fechas, 1.0, n)

    assert len(universo) == 1 and universo[0]["zone_id"] == "zvalida"  # top=None excluida del universo
    assert cb_top_none in creadoras  # pero SI marca su barra como creadora
    assert cb_valida in creadoras

    # Verificacion cruzada: construir_pool_candidatos debe EXCLUIR cb_top_none
    # como candidato de la zona valida (mismo minuto=10, sesion 1).
    por_minuto = m.indexar_por_minuto(ses_de_barra, rango_sesion, n)
    candidatos = m.construir_pool_candidatos(universo[0], por_minuto, creadoras, n, horizon_i=5)
    assert cb_top_none not in {b for _s, b in candidatos}


def test_08_covariables_causales_nunca_leen_barras_futuras():
    n = 200
    close_t = np.arange(n, dtype=np.float64)  # tendencia conocida, sin ruido
    bar_volume = np.arange(n, dtype=np.float64) + 1.0
    cov = m.calcular_covariables_causales(close_t, bar_volume)
    # sigma60 en la barra 60 debe depender SOLO de close_t[0:61]; si cambio
    # close_t mas alla de 60, sigma60[60] no puede cambiar.
    cov_a = m.calcular_covariables_causales(close_t, bar_volume)["sigma60_ticks"][60]
    close_t2 = close_t.copy()
    close_t2[61:] = 999999.0  # alterar SOLO el futuro respecto de la barra 60
    cov_b = m.calcular_covariables_causales(close_t2, bar_volume)["sigma60_ticks"][60]
    assert cov_a == cov_b
    # y sigma60 en barras < 60 no esta disponible (NaN): no hay 60 diffs previos
    assert np.isnan(cov["sigma60_ticks"][:60]).all()
    assert np.isfinite(cov["sigma60_ticks"][60:]).all()


def test_09_horizonte_control_igual_al_horizonte_fuente():
    n = 2500
    high_t, low_t, close_t, _v = _flat_bars(n, base_close=100)
    created_bar_fuente = 2400  # cerca del final: H_i chico
    h_fuente = m.horizonte_zona(created_bar_fuente, n, max_age_bars=2000)
    assert h_fuente == (n - 1) - created_bar_fuente  # < 2000, acotado por fin de datos

    created_bar_control = 10  # lejos del final: tendria MUCHO mas horizonte propio
    lc_control_sin_cap = m.zone_lifecycle(200, 201, True, created_bar_control,
                                          high_t, low_t, close_t, n, max_age_bars=2000)
    lc_control_con_cap = m.zone_lifecycle(200, 201, True, created_bar_control,
                                          high_t, low_t, close_t, n, max_age_bars=2000,
                                          horizon_cap=h_fuente)
    # sin cap, el control expira a los 2000 (max_age_bars); CON el cap = h_fuente
    # (mucho menor), el control queda censurado ANTES de llegar a expirar --
    # confirma que el horizonte de la fuente efectivamente acota al control.
    assert lc_control_sin_cap["removed_reason"] == "max_age"
    assert lc_control_con_cap["censored"] is True
    assert lc_control_con_cap["removed_reason"] is None


# ======================================================================
# 10. Seleccion de vecinos es determinista ante empates
# ======================================================================

def test_10_desempate_determinista_por_score_sesion_bar_index():
    zona_cov = (0.0, 0.0)
    # 6 candidatos con distancia IDENTICA (empate total en score) -- el
    # desempate debe ser por (session_date, bar_index) ascendente.
    candidatos = [("S3", 50), ("S1", 20), ("S2", 10), ("S1", 5), ("S4", 1), ("S2", 99)]
    cov_por_barra = {b: (0.0, 0.0) for _s, b in candidatos}
    res1 = m.emparejar_controles(zona_cov, candidatos, cov_por_barra, k=8, min_controls=5)
    res2 = m.emparejar_controles(zona_cov, list(reversed(candidatos)), cov_por_barra, k=8, min_controls=5)
    assert res1["estado"] == "OK"
    orden_esperado = [("S1", 5), ("S1", 20), ("S2", 10), ("S2", 99), ("S3", 50), ("S4", 1)]
    obtenido1 = [(c["session_date"], c["bar_index"]) for c in res1["elegidos"]]
    obtenido2 = [(c["session_date"], c["bar_index"]) for c in res2["elegidos"]]
    assert obtenido1 == orden_esperado
    assert obtenido2 == orden_esperado  # el orden de ENTRADA no debe importar


# ======================================================================
# 11/12. Datasets sinteticos: sin efecto -> ~0; con toque acelerado -> positivo
# ======================================================================

def _correr_sintetico(n_sesiones, bpp, zonas, high_t, low_t, close_t, bar_volume):
    ses_de_barra, rango_sesion, fechas = _sesiones_sinteticas(n_sesiones, bpp)
    n = n_sesiones * bpp
    return m.procesar_zonas_de_archivo(
        zonas, high_t, low_t, close_t, bar_volume, ses_de_barra, rango_sesion,
        fechas, tick_size=5e-05, n_bars=n)


def test_11_dataset_sintetico_sin_efecto_da_residual_compatible_con_cero():
    """Todas las barras identicas entre sesiones (mismo close/volumen en cada
    minuto, replicado sesion a sesion) y NINGUNA zona toca nunca (rango lejos
    del precio) -- real y controles deben dar y_i=p0_i=0 en todos los casos,
    R_s=0 exacto, sin ningun IC que hacer: el residual es identicamente cero,
    no solo "cerca"."""
    n_sesiones, bpp = 6, 200
    high_t, low_t, close_t, bar_volume = _flat_bars(n_sesiones * bpp, base_close=100)
    tick_size = 5e-05
    zonas = []
    for s in range(n_sesiones):
        cb = s * bpp + 80  # >=60: sigma60 causal disponible (ventana de 60 diffs)
        bottom = 400 * tick_size - tick_size / 2.0  # MUY lejos de 100: nunca toca
        top = 401 * tick_size + tick_size / 2.0
        zonas.append(dict(id="z%d" % s, top=top, bottom=bottom, created_bar=cb,
                          created_ms=0, kind="trapped_buyers"))
        # created_ms/session mapping: reemplazamos abajo via monkeypatch de
        # session_date_ct no hace falta -- construimos directo el universo.
    res = _correr_sintetico(n_sesiones, bpp, [], high_t, low_t, close_t, bar_volume)
    # armamos el universo a mano (bypass de session_date_ct/created_ms) para
    # aislar el calculo puro de matching+lifecycle+agregacion:
    ses_de_barra, rango_sesion, fechas = _sesiones_sinteticas(n_sesiones, bpp)
    universo = []
    for s in range(n_sesiones):
        # minuto ESCALONADO por zona (80, 83, 86, ...): si las 6 zonas
        # compartieran el mismo minuto, cada una seria la "barra creadora" que
        # excluye a las demas de su propio pool de candidatos (regla #7) -- un
        # artefacto del fixture (todas las zonas en el mismo minuto), no algo
        # que pase en datos reales donde las creaciones caen en minutos dispares.
        minuto = 80 + s * 3
        cb = s * bpp + minuto
        universo.append(dict(zone_id="z%d" % s, created_bar=cb, session_date=fechas[s],
                             minute_of_session=minuto, is_bull=True, lo_tick=400, hi_tick=401))
    creadoras = {u["created_bar"] for u in universo}
    cov = m.calcular_covariables_causales(close_t, bar_volume)
    cov_por_barra = {i: (float(cov["log1p_sigma60_ticks"][i]), float(cov["log1p_bar_volume"][i]))
                     for i in range(len(close_t)) if np.isfinite(cov["log1p_sigma60_ticks"][i])}
    por_minuto = m.indexar_por_minuto(ses_de_barra, rango_sesion, len(close_t))
    # max_age chico A PROPOSITO en este test sintetico: con el default de
    # produccion (2000) la primera sesion tendria mas horizonte disponible que
    # bars_por_sesion*n_sesiones puede ofrecerle a un candidato de la ULTIMA
    # sesion -- artefacto de escala del fixture, no del algoritmo. No es un
    # barrido de max_age_bars de produccion: ese sigue frozen en DEFAULTS.
    max_age_test = 30
    residuales = []
    for u in universo:
        h_i = m.horizonte_zona(u["created_bar"], len(close_t), max_age_bars=max_age_test)
        candidatos = m.construir_pool_candidatos(u, por_minuto, creadoras, len(close_t), h_i)
        match = m.emparejar_controles(cov_por_barra[u["created_bar"]], candidatos, cov_por_barra)
        assert match["estado"] == "OK", match
        lc_real = m.zone_lifecycle(u["lo_tick"], u["hi_tick"], u["is_bull"], u["created_bar"],
                                   high_t, low_t, close_t, len(close_t),
                                   max_age_bars=max_age_test, horizon_cap=h_i)
        y_i = m.endpoint_binario(lc_real)
        p0s = [m.endpoint_binario(m.zone_lifecycle(u["lo_tick"], u["hi_tick"], u["is_bull"],
                                                    c["bar_index"], high_t, low_t, close_t,
                                                    len(close_t), max_age_bars=max_age_test,
                                                    horizon_cap=h_i))
              for c in match["elegidos"]]
        assert y_i == 0.0
        assert all(p == 0.0 for p in p0s)
        residuales.append((u["session_date"], y_i - float(np.mean(p0s))))
    por_sesion = m.agregar_por_sesion(residuales)
    assert all(v == 0.0 for v in por_sesion.values())
    ic = m.hac_bartlett_ic([por_sesion[s] for s in sorted(por_sesion)])
    assert ic["mean"] == 0.0
    assert m.decidir_etiqueta(ic) == "COMPATIBLE_WITH_ZERO"


def test_12_dataset_sintetico_con_toque_acelerado_da_residual_positivo():
    """Igual que el test 11, pero la zona REAL esta puesta exactamente en el
    precio (siempre toca, y_i=1 garantizado) mientras los controles (otras
    sesiones, mismo minuto) NUNCA tocan (y por lo tanto p0_i=0 siempre) --
    residual conocido = 1 - 0 = 1 en cada sesion, exacto."""
    n_sesiones, bpp = 6, 200
    high_t, low_t, close_t, bar_volume = _flat_bars(n_sesiones * bpp, base_close=100)
    ses_de_barra, rango_sesion, fechas = _sesiones_sinteticas(n_sesiones, bpp)
    n = len(close_t)
    universo = []
    for s in range(n_sesiones):
        # minuto escalonado por zona -- misma razon que test_11 (evitar que
        # las zonas se excluyan mutuamente como candidatas via la regla #7).
        minuto = 80 + s * 3
        cb = s * bpp + minuto  # >=60: sigma60 causal disponible
        universo.append(dict(zone_id="z%d" % s, created_bar=cb, session_date=fechas[s],
                             minute_of_session=minuto, is_bull=True, lo_tick=101, hi_tick=103))
        # zona [101,103]: NO contiene el close plano=100, asi que los controles
        # (que quedan en el baseline sin excursion) nunca tocan por default.
        # excursion SOLO en la barra siguiente a ESTA creacion especifica (toca YA):
        high_t[cb + 1] = 102
    creadoras = {u["created_bar"] for u in universo}
    cov = m.calcular_covariables_causales(close_t, bar_volume)
    cov_por_barra = {i: (float(cov["log1p_sigma60_ticks"][i]), float(cov["log1p_bar_volume"][i]))
                     for i in range(n) if np.isfinite(cov["log1p_sigma60_ticks"][i])}
    por_minuto = m.indexar_por_minuto(ses_de_barra, rango_sesion, n)
    # max_age_test=1 A PROPOSITO: cada zona toca (o no) SOLO en su barra cb+1.
    # Con una ventana mas ancha, el horizonte de un control puede alcanzar el
    # cb+1 de OTRA zona dentro de la misma sesion (los minutos estan a solo 3
    # barras de distancia entre si) -- artefacto del fixture compacto, no del
    # algoritmo: con 1 barra de horizonte esa colision es geometricamente
    # imposible (verificado: 3*s - 3*j nunca da 1 para enteros).
    max_age_test = 1
    residuales = []
    for u in universo:
        h_i = m.horizonte_zona(u["created_bar"], n, max_age_bars=max_age_test)
        candidatos = m.construir_pool_candidatos(u, por_minuto, creadoras, n, h_i)
        match = m.emparejar_controles(cov_por_barra[u["created_bar"]], candidatos, cov_por_barra)
        assert match["estado"] == "OK", match
        lc_real = m.zone_lifecycle(u["lo_tick"], u["hi_tick"], u["is_bull"], u["created_bar"],
                                   high_t, low_t, close_t, n, max_age_bars=max_age_test, horizon_cap=h_i)
        y_i = m.endpoint_binario(lc_real)
        assert y_i == 1.0  # toca en la barra siguiente por construccion
        p0s = [m.endpoint_binario(m.zone_lifecycle(u["lo_tick"], u["hi_tick"], u["is_bull"],
                                                    c["bar_index"], high_t, low_t, close_t, n,
                                                    max_age_bars=max_age_test, horizon_cap=h_i))
              for c in match["elegidos"]]
        assert all(p == 0.0 for p in p0s)  # los controles NO tienen la excursion inyectada
        residuales.append((u["session_date"], y_i - float(np.mean(p0s))))
    por_sesion = m.agregar_por_sesion(residuales)
    assert all(v == 1.0 for v in por_sesion.values())
    ic = m.hac_bartlett_ic([por_sesion[s] for s in sorted(por_sesion)])
    assert ic["mean"] == 1.0
    assert ic["ci95_lower"] > 0
    assert m.decidir_etiqueta(ic) == "RESIDUAL_POSITIVE"


# ======================================================================
# 13. Ningun gate puede pasar con cero zonas/controles/sesiones
# ======================================================================

def test_13_cero_zonas_no_puede_pasar_gates():
    cobertura = m.calcular_balance_cobertura([], {})
    assert cobertura["n_total_zonas"] == 0
    assert cobertura["cobertura"] == 0.0
    assert cobertura["cobertura"] < m.MIN_ZONE_COVERAGE
    ic_vacio = m.hac_bartlett_ic([])
    assert ic_vacio["n_sessions"] == 0
    assert m.decidir_etiqueta(ic_vacio) == "ABSTAIN_MATCHING"


def test_13b_pool_insuficiente_abstiene_no_inventa_controles():
    zona_cov = (0.0, 0.0)
    candidatos = [("S1", 1), ("S2", 2)]  # 2 candidatos, min_controls=5
    cov_por_barra = {1: (0.0, 0.0), 2: (0.0, 0.0)}
    res = m.emparejar_controles(zona_cov, candidatos, cov_por_barra, k=8, min_controls=5)
    assert res["estado"] == "ABSTAIN"
    assert res["elegidos"] == []


# ======================================================================
# Puntos adicionales del auditor: K=8/min=5, gates de cobertura/SMD, peso
# igual por sesion, HAC con serie sintetica conocida, determinismo, holdout,
# outcomes, controles duplicados
# ======================================================================

def test_k8_y_minimo_5():
    assert m.K_CONTROLS == 8
    assert m.MIN_CONTROLS == 5
    zona_cov = (0.0, 0.0)
    candidatos = [("S%d" % i, i) for i in range(12)]  # 12 candidatos disponibles
    cov_por_barra = {i: (float(i) * 0.001, 0.0) for i in range(12)}
    res = m.emparejar_controles(zona_cov, candidatos, cov_por_barra)
    assert res["estado"] == "OK"
    assert len(res["elegidos"]) == 8  # nunca mas de K=8 aunque el pool sea mas grande


def test_gate_falla_por_cobertura_menor_a_95_por_ciento():
    zonas_matched = (
        [dict(covariables_fuente=(0.0, 0.0), match=dict(estado="OK", elegidos=[]))] * 90
        + [dict(covariables_fuente=(0.0, 0.0), match=dict(estado="ABSTAIN", elegidos=[]))] * 10)
    cov_por_barra = {}
    res = m.calcular_balance_cobertura(zonas_matched, cov_por_barra)
    assert res["cobertura"] == pytest.approx(0.90)
    assert res["cobertura"] < m.MIN_ZONE_COVERAGE


def test_gate_falla_por_smd_fuera_de_tolerancia():
    reales = [10.0] * 20
    controles = [10.0 + 3.0] * 20  # diferencia grande, misma varianza (0) -> |SMD| debe marcar
    # con varianza cero de los dos lados y medias distintas, smd() no puede
    # dividir por 0: por diseno devuelve None (no confundir con "balance perfecto").
    valor = m.smd(reales, controles)
    assert valor is None
    # con algo de varianza, el SMD debe reflejar una diferencia grande y
    # superar el umbral 0.10
    rng = np.random.default_rng(0)
    reales2 = list(10.0 + rng.normal(0, 0.01, 200))
    controles2 = list(10.5 + rng.normal(0, 0.01, 200))
    valor2 = m.smd(reales2, controles2)
    assert valor2 is not None and abs(valor2) > m.MAX_ABS_SMD


# ======================================================================
# F2 (bloqueante para la corrida formal, auditoria 2026-08-11): el SMD
# agregado entre archivos NUNCA puede ser un promedio de SMDs por-archivo --
# +0.5 en un archivo y -0.5 en otro promedian 0.0 y pasarian el gate sin que
# ningun archivo individual este balanceado.
#
# F2.1 (segunda auditoria independiente, misma fecha, sobre el propio fix de
# F2): tres desviaciones mas.
# (a) pooling de controles SIN ponderar por 1/k_efectivo -- una zona con
#     K=8 pesaba mas del lado control que una con K=5 solo por tener mas
#     valores crudos en la lista;
# (b) "SMD pareado" (mean(diff)/sd(diff)) es en realidad un Cohen's d_z
#     (efecto pareado, escala de la SD de las diferencias), no un SMD
#     comparable al umbral 0.10 -- reemplazado por smd_matched_sets()
#     (smd() estandar entre fuente y promedio_de_sus_controles por zona);
# (c) max_abs_por_archivo filtraba los None antes de tomar el maximo, y un
#     archivo omitido del pooling (ausente del dict, o ABSTAIN) no dejaba
#     ningun rastro -- ahora agregar_smd_global() recibe el plan COMPLETO de
#     archivos y falla el gate (con motivo explicito) si cualquiera de ellos
#     esta ausente, en ABSTAIN, o con un SMD no finito.
# ======================================================================

def test_smd_ponderado_valores_conocidos():
    # sin pesos (None) -> peso 1 cada uno, coincide con smd() sin ponderar.
    r, c = [1.0, 3.0], [0.0, 2.0]
    assert m.smd_ponderado(r, c) == pytest.approx(m.smd(r, c))
    # con pesos dispares: 2 controles en 0.0 (peso 0.25 c/u) + 1 control en
    # 4.0 (peso 1.0) -- el de peso 1.0 domina la media ponderada del lado
    # control, no el conteo de valores.
    r2, c2, w2 = [2.0], [0.0, 0.0, 4.0], [0.25, 0.25, 1.0]
    media_c = (0.0 * 0.25 + 0.0 * 0.25 + 4.0 * 1.0) / sum(w2)
    assert media_c == pytest.approx(8.0 / 3.0)
    valor = m.smd_ponderado(r2, c2, w2)
    # verificacion independiente a mano (no solo re-llamar a la funcion): la
    # varianza ponderada del lado control, poblacional, con esos mismos pesos.
    var_c = sum(w * (x - media_c) ** 2 for x, w in zip(c2, w2)) / sum(w2)
    var_pool = (0.0 + var_c) / 2.0  # var_r=0.0: un solo valor
    assert valor == pytest.approx((2.0 - media_c) / math.sqrt(var_pool))
    # peso total 0 -> None (division por cero evitada, no un 0.0 enganoso)
    assert m.smd_ponderado([1.0], [1.0], [0.0]) is None
    assert m.smd_ponderado([], [1.0], [1.0]) is None


def test_smd_matched_sets_valores_conocidos():
    """smd_matched_sets NO es Cohen's d_z (mean(diff)/sd(diff)) -- es smd()
    estandar entre fuente y promedio_de_controles por zona. Ejemplo donde las
    dos formulas divergen: diffs constantes (sd(diff)=0) haria que el viejo
    smd_pareado devolviera None (indefinido), mientras que smd_matched_sets
    da un valor finito porque mira la varianza de cada lado por separado, no
    la de la diferencia."""
    fuente = [1.0, 3.0]
    control_mean = [0.0, 2.0]  # diffs=[1,1]: constante, sd(diff)=0
    assert m.smd_matched_sets(fuente, control_mean) == m.smd(fuente, control_mean)
    # a mano: media(fuente)=2.0, media(control_mean)=1.0, var poblacional de
    # cada lado (ambos [x-2,x] centrados) = 1.0, var_pool=1.0 -> smd=1.0.
    assert m.smd_matched_sets(fuente, control_mean) == pytest.approx(1.0)


def test_calcular_balance_cobertura_expone_crudo_pesos_y_matched_sets():
    """calcular_balance_cobertura tiene que devolver, ademas del SMD
    ponderado por-archivo, las listas crudas CON su peso (1/k_efectivo por
    control) y los pares (fuente, promedio_de_sus_controles) por zona para
    smd_matched_sets -- sin agregar entre zonas (F2.1). Valores conocidos a
    mano: 2 zonas OK (K=2 y K=1), 1 ABSTAIN (que no debe aportar nada)."""
    zonas_matched = [
        dict(covariables_fuente=(1.0, 5.0),
            match=dict(estado="OK", elegidos=[dict(bar_index=10), dict(bar_index=11)])),
        dict(covariables_fuente=(2.0, 6.0),
            match=dict(estado="OK", elegidos=[dict(bar_index=20)])),
        dict(covariables_fuente=(9.0, 9.0), match=dict(estado="ABSTAIN", elegidos=[])),
    ]
    cov_por_barra = {10: (0.5, 4.0), 11: (1.5, 6.0), 20: (1.0, 5.0)}
    res = m.calcular_balance_cobertura(zonas_matched, cov_por_barra)

    assert res["crudo_reales_s60"] == [1.0, 2.0]
    assert res["crudo_reales_lv"] == [5.0, 6.0]
    # los 3 controles de las 2 zonas OK, sin promediar por zona (bar 10 y 11
    # de la zona 1 con K=2, bar 20 de la zona 2 con K=1 -- ABSTAIN no aporta).
    assert res["crudo_controles_s60"] == [0.5, 1.5, 1.0]
    assert res["crudo_controles_lv"] == [4.0, 6.0, 5.0]
    # peso 1/K_i por control: zona 1 (K=2) -> 0.5 cada uno, zona 2 (K=1) -> 1.0.
    assert res["pesos_controles"] == [pytest.approx(0.5), pytest.approx(0.5), pytest.approx(1.0)]
    assert sum(res["pesos_controles"][:2]) == pytest.approx(1.0)  # peso total 1 por zona, sea K=2...
    assert sum(res["pesos_controles"][2:]) == pytest.approx(1.0)  # ...o K=1

    # matched-sets: un par (fuente, promedio_de_sus_controles) por zona OK.
    assert res["fuente_matched_sets_s60"] == [1.0, 2.0]
    assert res["control_mean_s60"] == [pytest.approx(1.0), pytest.approx(1.0)]  # (0.5+1.5)/2=1.0 | 1.0
    assert res["fuente_matched_sets_lv"] == [5.0, 6.0]
    assert res["control_mean_lv"] == [pytest.approx(5.0), pytest.approx(5.0)]  # (4.0+6.0)/2=5.0 | 5.0

    # el SMD por-archivo que devuelve tiene que ser EXACTAMENTE smd_ponderado
    # sobre sus propias listas crudas+pesos expuestas -- no otra cosa.
    assert res["smd_log1p_sigma60_ticks"] == pytest.approx(
        m.smd_ponderado(res["crudo_reales_s60"], res["crudo_controles_s60"], res["pesos_controles"]))


def test_f21_peso_por_control_neutraliza_diferencia_de_k():
    """K=5 vs K=8 tiene que aportar el MISMO peso total (1.0) del lado
    control -- una zona con 8 controles no puede pesar mas que una con 5
    solo por tener mas valores individuales en la lista cruda. zona A: 8
    controles en 1.0. zona B: 5 controles en 3.0. La media ponderada del lado
    control tiene que ser (1.0+3.0)/2=2.0 (una zona, un voto) -- NO 23/13
    (la media si se pondera por CANTIDAD de controles, que domina la zona de
    8)."""
    zonas_matched = [
        dict(covariables_fuente=(0.0, 0.0),
            match=dict(estado="OK", elegidos=[dict(bar_index=i) for i in range(8)])),
        dict(covariables_fuente=(0.0, 0.0),
            match=dict(estado="OK", elegidos=[dict(bar_index=100 + i) for i in range(5)])),
    ]
    cov_por_barra = {i: (1.0, 0.0) for i in range(8)}
    cov_por_barra.update({100 + i: (3.0, 0.0) for i in range(5)})
    res = m.calcular_balance_cobertura(zonas_matched, cov_por_barra)

    assert res["pesos_controles"][:8] == [pytest.approx(1.0 / 8)] * 8
    assert res["pesos_controles"][8:] == [pytest.approx(1.0 / 5)] * 5
    media_ponderada = np.average(res["crudo_controles_s60"], weights=res["pesos_controles"])
    assert media_ponderada == pytest.approx(2.0)  # (1.0+3.0)/2, NO 23/13≈1.77


def test_f2_agregar_smd_global_no_cancela_signo_entre_archivos():
    """El escenario exacto que motivo F2: un archivo con SMD=+0.5 y otro con
    SMD=-0.5 (mismo |SMD|, signo opuesto). Promediar los dos SMD por-archivo
    (el codigo pre-F2) da 0.0 y pasaria el gate |SMD|<=0.10 de golpe, sin que
    NINGUN archivo individual este balanceado. agregar_smd_global() no puede
    cancelarse asi: max_abs_por_archivo es un MAXIMO, no un promedio, y por
    construccion nunca puede dar menos que el peor |SMD| individual -- ni el
    pool global ni el matched-sets alcanzan a cazar esta cancelacion
    simetrica especifica por si solos (verificado abajo, K=1 por zona para
    que el pool ponderado y el matched-sets coincidan exactamente con el
    calculo a mano), asi que el gate depende de max_abs_por_archivo para
    este caso exacto."""
    # archivo A: 2 zonas, K=1 cada una. fuente=[-0.5,1.5] control=[-1.0,1.0]
    # -> media_fuente=0.5, media_control=0.0, var=1.0 ambos lados -> SMD=+0.5.
    reales_a, controles_a, pesos_a = [-0.5, 1.5], [-1.0, 1.0], [1.0, 1.0]
    assert m.smd_ponderado(reales_a, controles_a, pesos_a) == pytest.approx(0.5)
    # archivo B: fuente=[-1.5,0.5], mismos controles -> media_fuente=-0.5 -> SMD=-0.5.
    reales_b, controles_b, pesos_b = [-1.5, 0.5], [-1.0, 1.0], [1.0, 1.0]
    assert m.smd_ponderado(reales_b, controles_b, pesos_b) == pytest.approx(-0.5)
    # documentacion del bug pre-F2: el promedio naive cancela a ~0 y pasaria.
    assert (0.5 + (-0.5)) / 2 == pytest.approx(0.0)
    # el pool global ponderado (union) Y el matched-sets TAMBIEN cancelan en
    # este caso simetrico -- no son los que salvan el gate aca, max_abs_por_archivo si.
    assert m.smd_ponderado(reales_a + reales_b, controles_a + controles_b,
                           pesos_a + pesos_b) == pytest.approx(0.0)
    assert m.smd_matched_sets(reales_a + reales_b, controles_a + controles_b) == pytest.approx(0.0)

    cobertura_a = dict(
        crudo_reales_s60=reales_a, crudo_controles_s60=controles_a, pesos_controles=pesos_a,
        crudo_reales_lv=[0.0, 0.0], crudo_controles_lv=[0.0, 0.0],
        fuente_matched_sets_s60=reales_a, control_mean_s60=controles_a,
        fuente_matched_sets_lv=[0.0, 0.0], control_mean_lv=[0.0, 0.0],
        smd_log1p_sigma60_ticks=0.5, smd_log1p_bar_volume=0.0)
    cobertura_b = dict(
        crudo_reales_s60=reales_b, crudo_controles_s60=controles_b, pesos_controles=pesos_b,
        crudo_reales_lv=[0.0, 0.0], crudo_controles_lv=[0.0, 0.0],
        fuente_matched_sets_s60=reales_b, control_mean_s60=controles_b,
        fuente_matched_sets_lv=[0.0, 0.0], control_mean_lv=[0.0, 0.0],
        smd_log1p_sigma60_ticks=-0.5, smd_log1p_bar_volume=0.0)
    agg = m.agregar_smd_global({"archivoA": cobertura_a, "archivoB": cobertura_b},
                               ["archivoA", "archivoB"])

    assert agg["smd_log1p_sigma60_ticks_global_pooled"] == pytest.approx(0.0)
    assert agg["smd_log1p_sigma60_ticks_matched_sets"] == pytest.approx(0.0)
    # el centinela que NO puede cancelarse: el peor |SMD| individual sigue
    # siendo 0.5, sin importar cuantos archivos balanceados haya alrededor.
    assert agg["smd_log1p_sigma60_ticks_max_abs_por_archivo"] == pytest.approx(0.5)
    assert agg["smd_por_archivo"]["log1p_sigma60_ticks"] == {"archivoA": 0.5, "archivoB": -0.5}
    assert agg["smd_sigma60_ok"] is False  # el gate tiene que FALLAR, no cancelarse a "OK"
    assert agg["smd_log1p_sigma60_ticks_archivos_invalidos"] == []  # no es un fail-closed, es max_abs

    # log1p_bar_volume: los dos archivos SI estan balanceados (reales=controles
    # constante en 0.0) -> ese gate especifico tiene que pasar -- prueba que
    # el fallo de sigma60 no contamina el gate de la otra covariable.
    assert agg["smd_bar_volume_ok"] is True


def test_f21_fail_closed_archivo_invalido_hace_fallar_el_gate():
    """Un archivo con SMD invalido (None por ABSTAIN, ausente por completo
    del dict, o NaN explicito) tiene que hacer FALLAR el gate de esa
    covariable aunque el resto de los archivos esten perfectamente
    balanceados -- no se filtra antes de max_abs_por_archivo, se registra
    como invalido explicitamente (F2.1, auditoria 2026-08-11)."""
    cobertura_valida = dict(
        crudo_reales_s60=[0.0, 0.0], crudo_controles_s60=[0.0, 0.0], pesos_controles=[1.0, 1.0],
        crudo_reales_lv=[0.0, 0.0], crudo_controles_lv=[0.0, 0.0],
        fuente_matched_sets_s60=[0.0], control_mean_s60=[0.0],
        fuente_matched_sets_lv=[0.0], control_mean_lv=[0.0],
        smd_log1p_sigma60_ticks=0.0, smd_log1p_bar_volume=0.0)

    # Caso 1: archivo B explicitamente None (ABSTAIN, p.ej. `sequence` invalida).
    agg1 = m.agregar_smd_global({"archivoA": cobertura_valida, "archivoB": None},
                                ["archivoA", "archivoB"])
    assert agg1["smd_sigma60_ok"] is False
    assert agg1["smd_bar_volume_ok"] is False
    assert [a for a, _motivo in agg1["smd_log1p_sigma60_ticks_archivos_invalidos"]] == ["archivoB"]

    # Caso 2: archivo B directamente AUSENTE del dict (archivo planificado que
    # nunca se registro -- bug del caller, no un ABSTAIN declarado).
    agg2 = m.agregar_smd_global({"archivoA": cobertura_valida}, ["archivoA", "archivoB"])
    assert agg2["smd_sigma60_ok"] is False
    assert agg2["smd_bar_volume_ok"] is False

    # Caso 3: archivo B con SMD de sigma60 explicitamente NaN, pero
    # bar_volume valido -- el gate de sigma60 falla, el de bar_volume NO se
    # contamina (son covariables independientes).
    cobertura_nan = dict(cobertura_valida, smd_log1p_sigma60_ticks=float("nan"))
    agg3 = m.agregar_smd_global({"archivoA": cobertura_valida, "archivoB": cobertura_nan},
                                ["archivoA", "archivoB"])
    assert agg3["smd_sigma60_ok"] is False
    assert agg3["smd_bar_volume_ok"] is True


def test_ponderacion_igual_por_sesion_no_por_cantidad_de_zonas():
    # sesion A: 1 zona con r_i=1.0 => R_A=1.0
    # sesion B: 99 zonas con r_i=0.0 => R_B=0.0
    # con peso igual por sesion, el agregado es mean(1.0, 0.0)=0.5 -- NO
    # 1/100=0.01 (que seria el resultado si pesara por zona, no por sesion).
    residuales = [("A", 1.0)] + [("B", 0.0)] * 99
    por_sesion = m.agregar_por_sesion(residuales)
    assert por_sesion == {"A": 1.0, "B": 0.0}
    ic = m.hac_bartlett_ic([por_sesion["A"], por_sesion["B"]])
    assert ic["mean"] == pytest.approx(0.5)


def test_hac_bartlett_serie_sintetica_sin_autocorrelacion_recupera_media_y_se_razonable():
    """Serie iid conocida (media=2.0, sd=1.0, n=400): la media estimada debe
    caer cerca de 2.0 y el SE HAC debe ser del orden de sd/sqrt(n) (sin
    autocorrelacion, HAC no deberia inflar mucho el SE simple)."""
    rng = np.random.default_rng(42)
    n = 400
    x = list(2.0 + rng.normal(0, 1.0, n))
    ic = m.hac_bartlett_ic(x)
    assert ic["n_sessions"] == n
    assert ic["mean"] == pytest.approx(2.0, abs=0.15)
    se_simple = 1.0 / np.sqrt(n)
    assert ic["se_hac"] < se_simple * 2.0  # sin autocorrelacion, no deberia duplicarse
    assert ic["lag"] == int(np.ceil(np.sqrt(n)))
    assert ic["ci95_lower"] > 0  # media claramente > 0 con n=400


def test_hac_bartlett_lag_es_techo_de_raiz_de_n():
    for n in (1, 4, 5, 100, 201):
        ic = m.hac_bartlett_ic([1.0] * n if n > 0 else [])
        if n == 0:
            continue
        assert ic["lag"] == max(1, int(np.ceil(np.sqrt(n))))


def test_determinismo_mismo_input_mismo_hash():
    """Correr la MISMA capa de matching+lifecycle dos veces sobre el mismo
    input sintetico debe dar exactamente el mismo resultado -- serializado
    y hasheado, byte a byte."""
    n_sesiones, bpp = 4, 130
    high_t, low_t, close_t, bar_volume = _flat_bars(n_sesiones * bpp, base_close=100)
    ses_de_barra, rango_sesion, fechas = _sesiones_sinteticas(n_sesiones, bpp)
    n = len(close_t)
    cb = 70  # >=60: sigma60 causal disponible

    def _correr():
        # zona [101,103]: no contiene el close plano=100 (sin overlap con el
        # baseline de los controles, que deben quedar sin tocar por default).
        universo = [dict(zone_id="zA", created_bar=cb, session_date=fechas[0],
                         minute_of_session=cb, is_bull=True, lo_tick=101, hi_tick=103)]
        cov = m.calcular_covariables_causales(close_t, bar_volume)
        cov_por_barra = {i: (float(cov["log1p_sigma60_ticks"][i]), float(cov["log1p_bar_volume"][i]))
                        for i in range(n) if np.isfinite(cov["log1p_sigma60_ticks"][i])}
        por_minuto = m.indexar_por_minuto(ses_de_barra, rango_sesion, n)
        u = universo[0]
        h_i = m.horizonte_zona(u["created_bar"], n)
        candidatos = m.construir_pool_candidatos(u, por_minuto, {cb}, n, h_i)
        match = m.emparejar_controles(cov_por_barra[u["created_bar"]], candidatos, cov_por_barra)
        lc = m.zone_lifecycle(u["lo_tick"], u["hi_tick"], u["is_bull"], u["created_bar"],
                              high_t, low_t, close_t, n, horizon_cap=h_i)
        return dict(match=match, lifecycle=lc)

    r1, r2 = _correr(), _correr()
    import json
    h1 = hashlib.sha256(json.dumps(r1, sort_keys=True, default=str).encode()).hexdigest()
    h2 = hashlib.sha256(json.dumps(r2, sort_keys=True, default=str).encode()).hexdigest()
    assert h1 == h2


def test_proteccion_holdout_firewall_max_fecha():
    assert m.MAX_FECHA == "2026-06-30"
    # el modulo usa el mismo corte_del_sello()/MAX_FECHA que el resto del
    # proyecto (importado, no redefinido) -- verifica que no hay una segunda
    # constante de fecha divergente en este archivo.
    import inspect
    src = inspect.getsource(m)
    assert "2026-07-01" not in src and "2026-12-31" not in src  # el holdout no se referencia


def test_proteccion_no_hay_referencias_a_pnl_direccion_stops_targets():
    """El docstring del modulo SI menciona 'P&L'/'direccion' -- para declarar
    que estan EXCLUIDOS (exactamente lo que exige el protocolo). Lo que este
    test verifica es que el CODIGO (fuera del docstring principal, que es
    prosa) nunca los usa como variable, campo o computo."""
    import ast
    import inspect
    src_completo = inspect.getsource(m)
    tree = ast.parse(src_completo)
    docstring = ast.get_docstring(tree) or ""
    src_sin_docstring = src_completo.replace(docstring, "", 1).lower()
    for prohibido in ("pnl", "p&l", "stop_loss", "take_profit", "direction",
                      "qualityscore", "quality_score"):
        assert prohibido not in src_sin_docstring, (
            "referencia prohibida encontrada fuera del docstring: %s" % prohibido)
    assert "outcomes_accessed=false" in src_completo.lower()


def test_controles_no_duplicados_dentro_de_la_misma_zona():
    zona_cov = (0.0, 0.0)
    candidatos = [("S%d" % i, i) for i in range(10)]
    cov_por_barra = {i: (0.0, 0.0) for i in range(10)}
    res = m.emparejar_controles(zona_cov, candidatos, cov_por_barra)
    bar_indices = [c["bar_index"] for c in res["elegidos"]]
    assert len(bar_indices) == len(set(bar_indices))  # sin repetidos dentro de la misma zona


def test_data_root_resuelve_data_gitignoreado_desde_una_worktree():
    """Regresion del smoke 2026-08-11: `data/` esta gitignoreado (CLAUDE.md) y
    por eso NINGUNA worktree lo tiene, solo el checkout principal. `data_root()`
    debe encontrarlo igual, resolviendolo via `git worktree list` cuando la
    worktree local no lo tiene -- no debe asumir que vive junto al codigo."""
    root = m.data_root()
    assert root.exists() and root.is_dir()
    assert root.name == "data"
    # el checkout resuelto tiene que tener de verdad los parquets 6E que el
    # universo de research necesita -- si no, data_root() encontro un
    # directorio "data" equivocado (falso positivo silencioso).
    assert (root / "nt8" / "6E" / "6E_09-26_ticks.parquet").exists()


def test_un_control_puede_servir_a_varias_zonas_distintas():
    """Protocolo 7.3: 'Un control puede servir a varias zonas' -- NO es una
    prohibicion, es una propiedad explicitamente permitida. Este test la
    documenta como comportamiento esperado (dos zonas distintas SI pueden
    elegir el mismo bar_index como control)."""
    cov_por_barra = {i: (0.0, 0.0) for i in range(10)}
    candidatos = [("S%d" % i, i) for i in range(10)]
    res_a = m.emparejar_controles((0.0, 0.0), candidatos, cov_por_barra)
    res_b = m.emparejar_controles((0.0, 0.0), candidatos, cov_por_barra)
    bars_a = {c["bar_index"] for c in res_a["elegidos"]}
    bars_b = {c["bar_index"] for c in res_b["elegidos"]}
    assert bars_a == bars_b  # comparten controles: permitido, no un bug


# ======================================================================
# F0 (BLOQUEANTE, pedido por el auditor tras la auditoria independiente del
# fix de reanclaje 2026-08-11): modo --solo-estructural tiene que OMITIR el
# estimand por completo -- no calcularlo y esconderlo, directamente no
# llamarlo -- para que un smoke pre-interpretacion no pueda filtrar el efecto
# ni por accidente. F3: instrumentacion target-free de matching (n_pool,
# k_efectivo, abstenciones, offset de sesion, distancia de anclaje, y el
# centinela frac_control_bounds_iguales_a_fuente que detecta una regresion
# del bug de reanclaje).
# ======================================================================

def test_f0_solo_estructural_conserva_geometria_omite_endpoint():
    """calcular_endpoint=False tiene que dar EXACTAMENTE el mismo universo,
    matching y geometria reanclada que calcular_endpoint=True (el matching es
    target-free, no depende de si se mide el efecto) -- pero las claves del
    efecto (y_i, p0_i, r_i, lifecycle_real, secundarios_touch_by_horizon a
    nivel fila; y_ctrl a nivel control) tienen que estar AUSENTES del dict,
    no en None: ausentes."""
    fx = _fixture_reanclaje_end_to_end()
    kwargs = dict(kernel_zones=fx["kernel_zones"], high_t=fx["high_t"], low_t=fx["low_t"],
                 close_t=fx["close_t"], bar_volume=fx["bar_volume"], ses_de_barra=fx["ses_de_barra"],
                 rango_sesion=fx["rango_sesion"], fechas_universo=fx["fechas_reales"],
                 tick_size=fx["tick_size"], n_bars=fx["n"])
    res_full = m.procesar_zonas_de_archivo(**kwargs, calcular_endpoint=True)
    res_estructural = m.procesar_zonas_de_archivo(**kwargs, calcular_endpoint=False)

    assert len(res_full["resultados"]) == 1
    assert len(res_estructural["resultados"]) == 1
    fila_full = res_full["resultados"][0]
    fila_est = res_estructural["resultados"][0]

    claves_geometria = ["zone_id", "session_date", "created_bar", "k_efectivo",
                        "source_anchor_tick", "rel_lo_tick", "rel_hi_tick"]
    for k in claves_geometria:
        assert fila_full[k] == fila_est[k], k
    assert len(fila_full["controles_ledger"]) == len(fila_est["controles_ledger"]) == 5
    claves_ctrl_geometria = ["session_date", "bar_index", "score", "control_anchor_tick",
                             "control_lo_tick", "control_hi_tick", "session_offset",
                             "anchor_distance_ticks", "bounds_igual_a_fuente"]
    for c_full, c_est in zip(fila_full["controles_ledger"], fila_est["controles_ledger"]):
        for k in claves_ctrl_geometria:
            assert c_full[k] == c_est[k], k

    claves_efecto_fila = ["y_i", "p0_i", "r_i", "lifecycle_real", "secundarios_touch_by_horizon"]
    for k in claves_efecto_fila:
        assert k in fila_full, k
    for k in claves_efecto_fila:
        assert k not in fila_est, k
    assert "y_ctrl" in fila_full["controles_ledger"][0]
    assert all("y_ctrl" not in c for c in fila_est["controles_ledger"])

    # cobertura/universo/zonas_matched: F0 no toca esa parte, tienen que
    # quedar bit-identicas entre los dos modos.
    assert res_full["cobertura"] == res_estructural["cobertura"]
    assert len(res_full["universo"]) == len(res_estructural["universo"])
    assert len(res_full["zonas_matched"]) == len(res_estructural["zonas_matched"])


def test_f4_secundarios_touch_by_horizon_marcado_no_adjudicable():
    """F4 (multiplicidad, auditoria 2026-08-11): secundarios_touch_by_horizon
    no tiene contraparte de control en esos horizontes (1,2,5,10,20,60,120
    barras) -- p0_controles/y_ctrl solo se calculan al horizonte PRIMARIO. Sin
    control no hay residual que adjudicar, solo la tasa de toque cruda de la
    zona real. Tiene que venir envuelto con adjudicable=False y un motivo
    explicito, para que nadie lo cuente como un test adicional (inflaria el
    numero efectivo de hipotesis sin la comparacion pareada que lo haria
    valido)."""
    fx = _fixture_reanclaje_end_to_end()
    res = m.procesar_zonas_de_archivo(
        fx["kernel_zones"], fx["high_t"], fx["low_t"], fx["close_t"], fx["bar_volume"],
        fx["ses_de_barra"], fx["rango_sesion"], fx["fechas_reales"], fx["tick_size"], fx["n"],
        calcular_endpoint=True)
    assert len(res["resultados"]) == 1
    sec = res["resultados"][0]["secundarios_touch_by_horizon"]
    assert sec["adjudicable"] is False
    assert isinstance(sec["motivo"], str) and sec["motivo"]
    assert set(sec["valores"].keys()) == {1, 2, 5, 10, 20, 60, 120}
    assert all(v in (0.0, 1.0) for v in sec["valores"].values())


def test_f3_instrumentacion_histogramas_offsets_distancias_y_centinela():
    """instrumentacion_f3 sobre un escenario sintetico con valores conocidos
    a mano -- no solo 'no crashea'. 3 zonas_matched (2 OK con n_pool/k_efectivo
    distintos, 1 ABSTAIN con motivo declarado) y 2 resultados con 2 controles
    cada uno (offsets/distancias/bounds elegidos para calcular histogramas,
    resumenes numericos y el centinela a mano)."""
    zonas_matched = [
        dict(match=dict(estado="OK", n_pool=8, k_efectivo=5, elegidos=[])),
        dict(match=dict(estado="OK", n_pool=6, k_efectivo=5, elegidos=[])),
        dict(match=dict(estado="ABSTAIN", motivo="pool_insuficiente", n_pool=2, elegidos=[])),
    ]
    resultados = [
        dict(controles_ledger=[
            dict(session_offset=1, anchor_distance_ticks=10, bounds_igual_a_fuente=False),
            dict(session_offset=2, anchor_distance_ticks=20, bounds_igual_a_fuente=False),
        ]),
        dict(controles_ledger=[
            dict(session_offset=-1, anchor_distance_ticks=0, bounds_igual_a_fuente=True),
            dict(session_offset=None, anchor_distance_ticks=30, bounds_igual_a_fuente=False),
        ]),
    ]
    inst = m.instrumentacion_f3(zonas_matched, resultados)

    assert inst["histograma_n_pool"] == {8: 1, 6: 1, 2: 1}
    assert inst["histograma_k_efectivo"] == {5: 2}  # solo cuenta zonas OK
    assert inst["abstenciones_por_motivo"] == {"pool_insuficiente": 1}
    assert inst["n_controles_evaluados"] == 4
    # 1 de 4 controles tiene bounds identicos a la fuente -- y ese mismo
    # control tiene distancia 0 (coincidencia legitima, no la regresion que
    # el assert interno de instrumentacion_f3 vigila).
    assert inst["frac_control_bounds_iguales_a_fuente"] == pytest.approx(0.25)

    off = inst["offset_sesion_control_menos_fuente"]
    assert off["n"] == 3  # el offset None (session_date fuera de sesion_idx) se excluye
    assert off["min"] == -1.0 and off["max"] == 2.0
    assert off["media"] == pytest.approx((1 + 2 - 1) / 3)

    dist = inst["distancia_anclaje_ticks"]
    assert dist["n"] == 4  # la distancia SI la aportan los 4 controles, incluso con offset None
    assert dist["min"] == 0.0 and dist["max"] == 30.0
    assert dist["media"] == pytest.approx((10 + 20 + 0 + 30) / 4)


def test_f0_main_cli_solo_estructural_omite_claves_del_payload_y_del_stdout(tmp_path, monkeypatch, capsys):
    """Contrato pedido por el auditor: con --solo-estructural, ninguna clave
    del efecto aparece en el JSON de salida y el stdout no contiene 'mean' ni
    'ETIQUETA'. Corre main() end-to-end de verdad (dias_research/ticks_mod/
    bars_mod/REGISTRY fakeados con el mismo fixture de reanclaje, sin tocar
    datos reales ni el .venv/git/NORTH_STAR reales -- esos siguen siendo los
    de verdad) -- a diferencia de test_f0_solo_estructural_conserva_geometria_omite_endpoint
    (que prueba procesar_zonas_de_archivo directamente), esto cubre el
    ENSAMBLADO del payload dentro de main(), que es donde vivia el defecto
    real que el auditor senalo (una clave dejada afuera del `if` por error no
    la detectaria un test que no pasa por main())."""
    fx = _fixture_reanclaje_end_to_end()
    archivo = "FAKE_TEST_F0_SOLO_ESTRUCTURAL.parquet"

    class _FakeTk:
        sequence = np.arange(10, dtype=np.int64)
        tick_size = fx["tick_size"]

    class _FakeBars:
        end_ns = fx["bar_end_ns"]
        high_t = fx["high_t"]
        low_t = fx["low_t"]
        close_t = fx["close_t"]
        volume = fx["bar_volume"]

        def __len__(self):
            return len(self.end_ns)

    class _FakeTicksMod:
        @staticmethod
        def load_canonical_parquet(path, start_utc_ns=None, end_utc_ns=None):
            return _FakeTk()

    class _FakeBarsMod:
        @staticmethod
        def build_time_bars(tk, interval):
            return _FakeBars()

        @staticmethod
        def build_footprints(tk, b):
            return object()  # no None -- fuerza la rama con fp; el run fake la ignora igual

    class _FakeIndicatorMod:
        @staticmethod
        def run(*args, **kwargs):
            return {"zones": fx["kernel_zones"]}

    monkeypatch.setattr(m, "dias_research",
                        lambda: ([{"archivo": archivo, "fecha": f} for f in fx["fechas_reales"]],
                                {"nota": "fixture sintetico de test, no universo real"}))
    monkeypatch.setattr(m, "ticks_mod", _FakeTicksMod)
    monkeypatch.setattr(m, "bars_mod", _FakeBarsMod)
    monkeypatch.setattr(m, "REGISTRY", {m.INDICADOR: _FakeIndicatorMod})

    out_full = tmp_path / "full.json"
    out_est = tmp_path / "estructural.json"

    rc_full = m.main(["--smoke-archivo", archivo, "--out", str(out_full)])
    stdout_full = capsys.readouterr().out
    rc_est = m.main(["--smoke-archivo", archivo, "--solo-estructural", "--out", str(out_est)])
    stdout_est = capsys.readouterr().out

    assert rc_full == 0
    assert rc_est == 0

    payload_full = json.loads(out_full.read_text(encoding="utf-8"))
    payload_est = json.loads(out_est.read_text(encoding="utf-8"))

    # Modo completo: el estimand SI esta, tanto en el payload como en stdout.
    assert payload_full["estimand_suppressed"] is False
    assert "etiqueta" in payload_full
    assert "estimand_primario" in payload_full
    assert "por_sesion" in payload_full
    assert all("y_i" in fila for fila in payload_full["resultados_por_zona"])
    assert "mean" in stdout_full
    assert "ETIQUETA" in stdout_full

    # Modo estructural: NADA de eso -- ni en el payload ni en stdout.
    assert payload_est["estimand_suppressed"] is True
    assert "etiqueta" not in payload_est
    assert "estimand_primario" not in payload_est
    assert "por_sesion" not in payload_est
    assert payload_est["resultados_por_zona"], "el fixture tiene que producir al menos 1 zona OK"
    for fila in payload_est["resultados_por_zona"]:
        for k in ("y_i", "p0_i", "r_i", "lifecycle_real", "secundarios_touch_by_horizon"):
            assert k not in fila
        for ctrl in fila["controles_ledger"]:
            assert "y_ctrl" not in ctrl
    assert "ETIQUETA" not in stdout_est
    assert "mean" not in stdout_est
    assert "SUPRIMIDO" in stdout_est

    # F3: la instrumentacion target-free (matching, no efecto) esta presente
    # en los DOS modos -- no depende de calcular_endpoint.
    assert "instrumentacion" in payload_full
    assert "instrumentacion" in payload_est
    assert payload_full["instrumentacion"]["n_controles_evaluados"] == \
        payload_est["instrumentacion"]["n_controles_evaluados"]
