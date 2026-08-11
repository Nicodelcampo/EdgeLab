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
import sys
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
