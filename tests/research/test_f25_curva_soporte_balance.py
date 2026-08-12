# -*- coding: utf-8 -*-
"""Tests de F2.5 (curva de soporte comun y balance).

AUTOCONTENIDOS a proposito: arrays sinteticos inline, sin fixtures compartidos
con el test file del nulo por distancia y sin `data/`. Asi este archivo no
puede romper ni ser roto por los tests existentes.

Los dos tests que importan son los de EQUIVALENCIA (`test_equivalencia_*`):
son la red de seguridad de toda la duplicacion que introduce F2.5. Si esos dos
pasan, la celda central de la curva reproduce el matcher pre-registrado y el
resto de la rejilla es una variacion auditable de el.
"""
from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[2]


def _cargar(nombre_modulo, ruta_relativa):
    ruta = REPO / ruta_relativa
    spec = importlib.util.spec_from_file_location(nombre_modulo, ruta)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    import sys

    sys.modules[nombre_modulo] = mod
    spec.loader.exec_module(mod)
    return mod


f25 = _cargar("f25_curva_soporte_balance",
              "diag/tasa_senales/F2.5_curva_soporte_balance.py")
f11 = f25.f11


# ----------------------------------------------------------------------
# Fixtures sinteticos minimos
# ----------------------------------------------------------------------

def _por_minuto_sintetico():
    """3 sesiones x 4 minutos. bar_idx = 10*indice_sesion + minuto."""
    sesiones = ["2026-01-05", "2026-01-06", "2026-01-07"]
    por_minuto = {}
    for i, ses in enumerate(sesiones):
        for m in range(4):
            por_minuto.setdefault(m, []).append((ses, 10 * i + m))
    return por_minuto, sesiones


def _zona(minuto=1, sesion="2026-01-05"):
    return dict(minute_of_session=minuto, session_date=sesion)


# ----------------------------------------------------------------------
# EQUIVALENCIA -- los dos tests que sostienen todo lo demas
# ----------------------------------------------------------------------

def test_equivalencia_pool_ventana_0_contra_construir_pool_candidatos():
    por_minuto, _ses = _por_minuto_sintetico()
    creadoras = {11}
    zona = _zona(minuto=1, sesion="2026-01-05")
    n_bars = 40
    horizon_i = 5
    esperado = f11.construir_pool_candidatos(zona, por_minuto, creadoras, n_bars, horizon_i)
    obtenido = f25.pool_por_ventana(zona, por_minuto, creadoras, n_bars, horizon_i, 0)
    assert obtenido == esperado
    # y no es trivialmente vacio
    assert obtenido, "el fixture tiene que producir candidatos o el test no prueba nada"


def test_equivalencia_seleccion_sin_caliper_contra_emparejar_controles():
    por_minuto, _ses = _por_minuto_sintetico()
    creadoras = set()
    zona = _zona(minuto=2, sesion="2026-01-05")
    n_bars = 40
    horizon_i = 0
    candidatos = f25.pool_por_ventana(zona, por_minuto, creadoras, n_bars, horizon_i, 0)
    # covariables deterministas y distintas por barra
    cov_por_barra = {b: (0.10 * b, 1.0 + 0.05 * b) for _s, b in candidatos}
    zona_cov = (0.55, 1.55)

    match = f11.emparejar_controles(zona_cov, candidatos, cov_por_barra, k=2, min_controls=1)
    assert match["estado"] == "OK"
    esperado = [e["bar_index"] for e in match["elegidos"]]

    pool = [(cov_por_barra[b][0], cov_por_barra[b][1], s, b) for s, b in candidatos]
    scores, _m1, _m2 = f25.scores_del_pool(zona_cov, [(p[0], p[1]) for p in pool])
    triples = [(float(scores[i]), pool[i][2], pool[i][3]) for i in range(len(pool))]
    elegidos = f25.seleccionar(triples, k=2, caliper=None, min_controls=1)
    assert elegidos is not None
    assert [b for _sc, _s, b in elegidos] == esperado
    # y los scores coinciden numericamente con los de emparejar_controles
    assert [pytest.approx(sc) for sc, _s, _b in elegidos] == [
        pytest.approx(e["score"]) for e in match["elegidos"]]


# ----------------------------------------------------------------------
# Ventana de minuto
# ----------------------------------------------------------------------

def test_ventana_1_incluye_solo_minutos_vecinos():
    por_minuto, _ses = _por_minuto_sintetico()
    zona = _zona(minuto=1, sesion="2026-01-05")
    obtenido = f25.pool_por_ventana(zona, por_minuto, set(), 40, 0, 1)
    minutos_incluidos = sorted({b % 10 for _s, b in obtenido})
    assert minutos_incluidos == [0, 1, 2]


def test_ventana_none_ignora_minuto_pero_respeta_sesion_y_creadoras():
    por_minuto, _ses = _por_minuto_sintetico()
    creadoras = {13}
    zona = _zona(minuto=1, sesion="2026-01-05")
    obtenido = f25.pool_por_ventana(zona, por_minuto, creadoras, 40, 0, None)
    barras = sorted(b for _s, b in obtenido)
    # todos los minutos, ninguna barra de la sesion fuente (0..3), sin la creadora
    assert barras == [10, 11, 12, 20, 21, 22, 23]


def test_ventana_respeta_el_horizonte():
    por_minuto, _ses = _por_minuto_sintetico()
    zona = _zona(minuto=1, sesion="2026-01-05")
    # n_bars=24 => la ultima barra es 23; horizon_i=3 exige bar_idx <= 20
    obtenido = f25.pool_por_ventana(zona, por_minuto, set(), 24, 3, None)
    assert max(b for _s, b in obtenido) <= 20


# ----------------------------------------------------------------------
# Caliper, k y min_controls
# ----------------------------------------------------------------------

def test_caliper_filtra_por_distancia():
    triples = [(0.05, "a", 1), (0.15, "a", 2), (0.40, "a", 3), (0.90, "a", 4)]
    assert f25.seleccionar(triples, k=None, caliper=0.2, min_controls=1) == [
        (0.05, "a", 1), (0.15, "a", 2)]
    assert f25.seleccionar(triples, k=None, caliper=0.01, min_controls=1) is None


def test_k_todos_toma_el_pool_entero():
    triples = [(0.30, "a", 3), (0.10, "a", 1), (0.20, "a", 2)]
    elegidos = f25.seleccionar(triples, k=None, caliper=None, min_controls=1)
    assert [b for _sc, _s, b in elegidos] == [1, 2, 3]


def test_min_controls_efectivo():
    assert f25.min_controls_efectivo(1, min_controls=5) == 1
    assert f25.min_controls_efectivo(3, min_controls=5) == 3
    assert f25.min_controls_efectivo(8, min_controls=5) == 5
    assert f25.min_controls_efectivo(None, min_controls=5) == 5


# ----------------------------------------------------------------------
# Soporte comun y sd_ref, con valores calculados a mano
# ----------------------------------------------------------------------

def test_posicion_en_pool_valores_a_mano():
    vals = [1.0, 2.0, 3.0, 4.0]
    assert f25.posicion_en_pool(5.0, vals) == (True, False, 1.0)
    assert f25.posicion_en_pool(0.5, vals) == (False, True, 0.0)
    assert f25.posicion_en_pool(2.5, vals) == (False, False, 0.5)
    # empate exacto: pct usa desigualdad ESTRICTA
    assert f25.posicion_en_pool(2.0, vals) == (False, False, 0.25)


def test_sd_pooled_within_valor_a_mano():
    # un solo estrato con [0, 2] => SS_within = 2.0, gl = 1 => sd = sqrt(2)
    estratos = {"arch": {0: dict(fuentes_s60=[0.0], pool_s60=[2.0],
                                 fuentes_lv=[], pool_lv=[])}}
    sd, diag = f25.sd_pooled_within(estratos, "s60")
    assert sd == pytest.approx(math.sqrt(2.0))
    assert diag["grados_libertad"] == 1
    assert diag["n_obs"] == 2
    assert diag["n_estratos_singleton"] == 0
    # estrato singleton no aporta grados de libertad
    sd_lv, diag_lv = f25.sd_pooled_within(estratos, "lv")
    assert sd_lv is None
    assert diag_lv["n_estratos_singleton"] == 1


# ----------------------------------------------------------------------
# Acumulacion cruda: la regla de F2/F2.1/F2.2/F2.3
# ----------------------------------------------------------------------

def test_fusionar_no_promedia_fracciones_ya_reducidas_por_archivo():
    """Dos archivos de tamano muy distinto: la fraccion pooleada tiene que ser
    total/total (3/12 = 0.25) y NO el promedio de las fracciones por archivo
    ((1/2 + 2/10)/2 = 0.35)."""
    def crudo(n, above):
        c = f25.crudo_vacio()
        s = f25._soporte_vacio()
        s["n_zonas"] = n
        s["suma_n_pool"] = 9 * n
        d = s["por_covariable"]["log1p_bar_volume"]
        d["above"] = above
        d["pcts"] = [1.0] * above + [0.5] * (n - above)
        c["soporte"][0] = s
        return c

    total = f25.crudo_vacio()
    f25.fusionar_crudos(total, crudo(2, 1))
    f25.fusionar_crudos(total, crudo(10, 2))
    resumen = f25.resumir_soporte(total["soporte"])
    frac = resumen[0]["por_covariable"]["log1p_bar_volume"]["frac_above_max"]
    assert frac == pytest.approx(3.0 / 12.0)
    assert frac != pytest.approx(0.35)


def test_resumir_celdas_calcula_smd_con_sd_ref_congelado():
    total = {"w=0|k=8|cal=ninguno": dict(
        n_zonas=10, n_zonas_ok=10, suma_n_pool_ok=100, suma_k_efectivo=80,
        suma_fuente_s60=10.0, suma_