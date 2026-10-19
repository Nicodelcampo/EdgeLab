# -*- coding: utf-8 -*-
"""Tests del generador browniano fixed-b y la cota de cobertura.

Los tests de propiedad usan un n_caminos reducido para mantener la suite
ligera. Los tests de regresión (sección B) usan las constantes congeladas
completas: GRILLA = 14775, N_CAMINOS = 50000, SEMILLA = 20260801.

GRILLA = 14775 = 197 * 75: con el n sellado en 197 días-bloque, el b de
producción b = 16/197 da b * GRILLA = 1200 entero exacto en IEEE double.
La sección B corre UNA sola simulación congelada por fixture de módulo
(antes re-simulaba la misma corrida ocho veces); las aserciones y los
valores pineados no cambiaron de naturaleza: se regeneraron por el cambio
de GRILLA (el stream aleatorio se re-alinea, ruido Monte Carlo esperado).
"""
from __future__ import annotations

import re

import numpy as np
import pytest

from edgelab.bridge.common import quantile_exact
from edgelab.stats.fixed_b import (
    FixedBError,
    FUNCIONAL_SIMETRICO,
    FUNCIONAL_UNA_COLA,
    GRILLA,
    N_CAMINOS,
    SEMILLA,
    _cdf_binomial,
    _clopper_pearson_lower,
    _clopper_pearson_upper,
    cota_de_cobertura,
    cuantil_G,
    cuantil_G_sim,
    simular_funcionales,
    veredicto_cota,
)

# Constantes reducidas para tests de propiedad (no afectan regresión).
N_CAMINOS_PROP = 2000
GRILLA_PROP = 1000

# b de producción: n sellado en 197 días-bloque, l = round(0.08*197) = 16.
B_PRODUCCION = 16 / 197

# --------------------------------------------------------------------- A) propiedades


def test_G_y_G_sim_estan_entre_cero_y_uno():
    res = simular_funcionales(
        [0.02, 0.08, 0.20],
        n_caminos=N_CAMINOS_PROP,
        grilla=GRILLA_PROP,
        semilla=SEMILLA,
    )
    for b, vals in res.items():
        assert vals["G"].min() >= 0.0
        assert vals["G"].max() <= 1.0
        assert vals["G_sim"].min() >= 0.0
        assert vals["G_sim"].max() <= 1.0


def test_determinismo_bit_a_bit():
    r1 = simular_funcionales(
        [0.08], n_caminos=N_CAMINOS_PROP, grilla=GRILLA_PROP, semilla=SEMILLA
    )
    r2 = simular_funcionales(
        [0.08], n_caminos=N_CAMINOS_PROP, grilla=GRILLA_PROP, semilla=SEMILLA
    )
    assert np.array_equal(r1[0.08]["G"], r2[0.08]["G"])
    assert np.array_equal(r1[0.08]["G_sim"], r2[0.08]["G_sim"])


def test_semillas_distintas_dan_resultados_distintos():
    r1 = simular_funcionales(
        [0.08], n_caminos=N_CAMINOS_PROP, grilla=GRILLA_PROP, semilla=SEMILLA
    )
    r2 = simular_funcionales(
        [0.08], n_caminos=N_CAMINOS_PROP, grilla=GRILLA_PROP, semilla=SEMILLA + 1
    )
    assert not np.array_equal(r1[0.08]["G"], r2[0.08]["G"])


def test_identidad_beta_exacta():
    """beta contado como ceros de G_sim coincide exactamente con beta por supremo.

    G_sim == 0 para un camino  <=>  |D(t)| < |W(1)| para todo t. En la
    discretización, ambos se calculan sobre los mismos puntos, así que la
    igualdad debe ser numéricamente exacta (no aproximada).
    """
    res = simular_funcionales(
        [0.08],
        n_caminos=N_CAMINOS_PROP,
        grilla=GRILLA_PROP,
        semilla=SEMILLA,
        _retornar_supremos=True,
    )
    G_sim = res[0.08]["G_sim"]
    sup_D = res[0.08]["sup_D"]
    W1_abs = res[0.08]["W1_abs"]
    ceros = G_sim == 0.0
    supremo_evento = sup_D < W1_abs
    assert np.array_equal(ceros, supremo_evento)
    assert ceros.mean() == supremo_evento.mean()


def test_identidad_beta_exacta_una_cola():
    """beta de producción: ceros de G == supremo con signo por debajo de W(1).

    G == 0 para un camino  <=>  W(1) > D(t) para todo t  <=>  sup_t D(t) < W(1)
    (con SIGNO, sin valor absoluto). Es la identidad análoga a la del
    simétrico, sobre el funcional que usa la inferencia.
    """
    res = simular_funcionales(
        [0.08],
        n_caminos=N_CAMINOS_PROP,
        grilla=GRILLA_PROP,
        semilla=SEMILLA,
        _retornar_supremos=True,
    )
    G = res[0.08]["G"]
    sup_D_una_cola = res[0.08]["sup_D_una_cola"]
    W1 = res[0.08]["W1"]
    ceros = G == 0.0
    supremo_evento = sup_D_una_cola < W1
    assert np.array_equal(ceros, supremo_evento)
    assert ceros.mean() == supremo_evento.mean()


def test_convergencia_small_b():
    """Con b pequeño, el cuantil calibrado debe acercarse a alpha.

    Los autores fuerzan cv(0) = alpha, así que la cuadrática calibrada debe pasar
    cerca de alpha para b chico. Usamos tolerancia laxa porque es una simulación
    Monte Carlo con n_caminos reducido.
    """
    q = cuantil_G_sim(0.01, 0.05, n_caminos=5000, grilla=GRILLA_PROP, semilla=SEMILLA)
    assert q == pytest.approx(0.05, abs=0.01)


def test_monotonia_en_b():
    """G_sim_alpha no crece con b; beta no decrece con b.

    Los caminos se comparten dentro de cada llamada, pero comparar b a b requiere
    llamadas separadas. Aun así, la propiedad debe mantenerse aproximadamente.
    Permitimos empates.
    """
    bs = [0.02, 0.05, 0.08, 0.12, 0.16, 0.20]
    qs = [
        cuantil_G_sim(b, 0.05, n_caminos=N_CAMINOS_PROP, grilla=GRILLA_PROP, semilla=SEMILLA)
        for b in bs
    ]
    betas = [
        cota_de_cobertura(
            b, FUNCIONAL_SIMETRICO,
            n_caminos=N_CAMINOS_PROP, grilla=GRILLA_PROP, semilla=SEMILLA,
        )["beta"]
        for b in bs
    ]
    for i in range(len(bs) - 1):
        assert qs[i] >= qs[i + 1] - 1e-12
        assert betas[i] <= betas[i + 1] + 1e-12


@pytest.mark.parametrize(
    "func,args,msg_fragment",
    [
        (cuantil_G, (1.5, 0.05), "b debe estar en (0,1)"),
        (cuantil_G, (-0.1, 0.05), "b debe estar en (0,1)"),
        (cuantil_G, (0.0801, 0.05), "b * grilla debe ser entero exacto"),
        (cuantil_G_sim, (0.08, 1.5), "alpha debe estar en (0,1)"),
        (cuantil_G_sim, (0.08, -0.1), "alpha debe estar en (0,1)"),
        (lambda *a: simular_funcionales([0.08], n_caminos=0), (), "n_caminos debe ser positivo"),
        (lambda *a: simular_funcionales([0.08], grilla=0), (), "grilla debe ser positivo"),
        (simular_funcionales, ([],), "bs está vacío"),
    ],
)
def test_errores_de_dominio_lanzan_fixed_b_error(func, args, msg_fragment):
    with pytest.raises(FixedBError, match=re.escape(msg_fragment)):
        func(*args)


# --------------------------------------------------------------------- B) regresión golden


@pytest.fixture(scope="module")
def sim_frozen():
    """UNA sola corrida con las constantes congeladas para toda la sección.

    Los dos b van en la misma llamada: los caminos se comparten (comparaciones
    pareadas) y el RNG se paga una sola vez. Antes de esta fixture, la sección
    re-simulaba la misma corrida congelada ocho veces (una por test).
    """
    return simular_funcionales(
        [0.08, B_PRODUCCION],
        n_caminos=N_CAMINOS,
        grilla=GRILLA,
        semilla=SEMILLA,
        _retornar_supremos=True,
    )


@pytest.fixture(scope="module")
def veredicto_frozen():
    """Una sola evaluación del camino público `veredicto_cota` a constantes
    congeladas, compartida por los tests de veredicto de la sección."""
    return veredicto_cota(0.08, 0.05, FUNCIONAL_UNA_COLA)


def _q(arr, alpha):
    """Cuantil con la convención exacta del repo (la misma que usa el módulo)."""
    return float(quantile_exact(np.sort(arr), alpha))


def test_golden_b_008_05(sim_frozen):
    """Valores congelados con GRILLA=14775, N_CAMINOS=50000, SEMILLA=20260801.

    Migrados desde GRILLA=5000: el cambio de grilla re-alinea el stream
    aleatorio (ruido Monte Carlo esperado, no bug). El simétrico es
    NO CITABLE - diagnóstico de contraste.
    """
    assert _q(sim_frozen[0.08]["G"], 0.05) == pytest.approx(0.031558040311902312, abs=1e-9)
    assert _q(sim_frozen[0.08]["G_sim"], 0.05) == pytest.approx(0.02309842577607768, abs=1e-9)


def test_golden_b_008_10(sim_frozen):
    """Simétrico: NO CITABLE - diagnóstico de contraste."""
    assert _q(sim_frozen[0.08]["G"], 0.10) == pytest.approx(0.084449021627188467, abs=1e-9)
    assert _q(sim_frozen[0.08]["G_sim"], 0.10) == pytest.approx(0.07113432396645579, abs=1e-9)


def test_golden_b_16_197_05(sim_frozen):
    """b de producción (16/197, n = 197 días-bloque sellado).

    cuantil_G ES la constante de producción. cuantil_G_sim:
    NO CITABLE - diagnóstico de contraste.
    """
    assert _q(sim_frozen[B_PRODUCCION]["G"], 0.05) == pytest.approx(0.031305244549204476, abs=1e-9)
    assert _q(sim_frozen[B_PRODUCCION]["G_sim"], 0.05) == pytest.approx(0.022834413671184443, abs=1e-9)


def test_golden_b_16_197_10(sim_frozen):
    """Simétrico: NO CITABLE - diagnóstico de contraste."""
    assert _q(sim_frozen[B_PRODUCCION]["G"], 0.10) == pytest.approx(0.083971714790807311, abs=1e-9)
    assert _q(sim_frozen[B_PRODUCCION]["G_sim"], 0.10) == pytest.approx(0.070271066588096648, abs=1e-9)


def test_golden_beta_008(sim_frozen):
    """beta a 0.08 sobre ambos funcionales. Simétrico: NO CITABLE - contraste."""
    G = sim_frozen[0.08]["G"]
    G_sim = sim_frozen[0.08]["G_sim"]
    assert (G == 0.0).mean() == pytest.approx(0.01336, abs=1e-9)
    assert (sim_frozen[0.08]["sup_D_una_cola"] < sim_frozen[0.08]["W1"]).mean() == pytest.approx(0.01336, abs=1e-9)
    assert (G_sim == 0.0).mean() == pytest.approx(0.01474, abs=1e-9)
    assert (sim_frozen[0.08]["sup_D"] < sim_frozen[0.08]["W1_abs"]).mean() == pytest.approx(0.01474, abs=1e-9)


def test_golden_beta_16_197(sim_frozen):
    """beta al b de producción. Simétrico: NO CITABLE - diagnóstico de contraste."""
    G = sim_frozen[B_PRODUCCION]["G"]
    G_sim = sim_frozen[B_PRODUCCION]["G_sim"]
    k = int((G == 0.0).sum())
    assert k == 675
    assert (G == 0.0).mean() == pytest.approx(0.0135, abs=1e-9)
    assert (sim_frozen[B_PRODUCCION]["sup_D_una_cola"] < sim_frozen[B_PRODUCCION]["W1"]).mean() == pytest.approx(0.0135, abs=1e-9)
    assert _clopper_pearson_lower(k, N_CAMINOS) == pytest.approx(0.012327850803103502, abs=1e-9)
    assert _clopper_pearson_upper(k, N_CAMINOS) == pytest.approx(0.01474971230572919, abs=1e-9)
    k_sim = int((G_sim == 0.0).sum())
    assert k_sim == 748
    assert (G_sim == 0.0).mean() == pytest.approx(0.01496, abs=1e-9)


def test_golden_veredicto_008_005(veredicto_frozen):
    assert veredicto_frozen["veredicto"] == "APTO"
    assert veredicto_frozen["ic_sup"] == pytest.approx(0.014603570989038417, abs=1e-9)


def test_golden_veredicto_16_197_005(sim_frozen):
    """APTO al b de producción, evaluado con la regla del módulo sobre la
    corrida congelada compartida (el camino público `veredicto_cota` a
    constantes congeladas queda cubierto por `veredicto_frozen` a 0.08)."""
    k = int((sim_frozen[B_PRODUCCION]["G"] == 0.0).sum())
    assert k / N_CAMINOS <= 0.05
    assert _cdf_binomial(k, N_CAMINOS, 0.05) <= 0.01


# --------------------------------------------------------------------- C) compuerta


def test_veredicto_cota_devuelve_estructura_y_veredicto_valido(veredicto_frozen):
    v = veredicto_frozen
    assert set(v.keys()) == {"b", "alpha", "beta", "beta_por_supremo", "ic_sup", "ic_inf", "veredicto", "funcional"}
    assert v["veredicto"] in {"APTO", "NO APTO", "INCONCLUSO"}
    assert v["b"] == pytest.approx(0.08)
    assert v["alpha"] == pytest.approx(0.05)
    assert v["funcional"] == FUNCIONAL_UNA_COLA


# --------------------------------------------------------------------- D) CDF binomial exacta


def test_cdf_binomial_k_igual_n_es_uno():
    for p in (0.1, 0.5, 0.9):
        assert _cdf_binomial(10, 10, p) == pytest.approx(1.0)


def test_cdf_binomial_k_cero():
    n = 10
    for p in (0.1, 0.3, 0.7):
        assert _cdf_binomial(0, n, p) == pytest.approx((1 - p) ** n)


def test_cdf_binomial_n_1():
    for p in (0.1, 0.5, 0.9):
        assert _cdf_binomial(0, 1, p) == pytest.approx(1 - p)


def test_cdf_binomial_simetria():
    casos = [
        (5, 2, 0.3),
        (7, 3, 0.4),
        (10, 4, 0.6),
        (20, 8, 0.25),
    ]
    for n, k, p in casos:
        izq = _cdf_binomial(k, n, p)
        der = 1.0 - _cdf_binomial(n - k - 1, n, 1 - p)
        assert izq == pytest.approx(der, rel=1e-12)


def test_cdf_binomial_decrece_en_p():
    n, k = 20, 5
    ps = np.linspace(0.05, 0.95, 19)
    vals = [_cdf_binomial(k, n, p) for p in ps]
    for i in range(len(vals) - 1):
        assert vals[i] >= vals[i + 1]


def test_cdf_binomial_crece_en_k():
    n, p = 20, 0.4
    vals = [_cdf_binomial(k, n, p) for k in range(n + 1)]
    for i in range(len(vals) - 1):
        assert vals[i] <= vals[i + 1]


def test_cdf_binomial_caso_conocido():
    """n=4, k=2, p=0.5 -> P(X<=2) = 11/16."""
    assert _cdf_binomial(2, 4, 0.5) == pytest.approx(11.0 / 16.0)


def test_cdf_binomial_estabilidad_n_grande():
    v = _cdf_binomial(2500, 50000, 0.05)
    assert 0.0 <= v <= 1.0
    assert np.isfinite(v)


def test_coherencia_biseccion_con_decision():
    """U <= alpha debe coincidir exactamente con F(alpha) <= delta."""
    delta = 0.01
    casos = [
        (0, 100, 0.05),
        (5, 100, 0.05),
        (10, 500, 0.05),
        (50, 1000, 0.10),
        (100, 5000, 0.05),
        (2500, 50000, 0.05),
    ]
    for k, n, alpha in casos:
        U = _clopper_pearson_upper(k, n)
        F_alpha = _cdf_binomial(k, n, alpha)
        assert (U <= alpha) == (F_alpha <= delta)


def test_clopper_pearson_lower_k_cero_es_cero():
    assert _clopper_pearson_lower(0, 100) == pytest.approx(0.0)


def test_clopper_pearson_lower_k_igual_n():
    """k == n: L = delta**(1/n) EXACTO.

    P(X <= n-1; n, p) = 1 - p**n = 1 - delta  =>  p = delta**(1/n).
    """
    delta = 0.01
    n = 100
    v = _clopper_pearson_lower(n, n, delta=delta)
    assert v == pytest.approx(delta ** (1 / n))


@pytest.mark.parametrize("funcional", [FUNCIONAL_UNA_COLA, FUNCIONAL_SIMETRICO])
def test_clopper_pearson_monotonia_ic_inf_beta_ic_sup(sim_frozen, funcional):
    vals = (sim_frozen[0.08]["G"] if funcional == FUNCIONAL_UNA_COLA
            else sim_frozen[0.08]["G_sim"])
    k = int((vals == 0.0).sum())
    n = vals.size
    beta = k / n
    assert _clopper_pearson_lower(k, n) <= beta <= _clopper_pearson_upper(k, n)


def test_clopper_pearson_lower_golden():
    ic_inf = _clopper_pearson_lower(832, 50000)
    assert ic_inf == pytest.approx(0.015337389893375075, abs=1e-9)


def test_clopper_pearson_lower_consistencia_upper():
    """ic_inf + ic_sup encierran beta; ic_inf no excede ic_sup."""
    casos = [
        (0, 100),
        (50, 500),
        (832, 50000),
    ]
    for k, n in casos:
        lo = _clopper_pearson_lower(k, n)
        hi = _clopper_pearson_upper(k, n)
        assert lo <= hi
        beta = k / n
        assert lo <= beta <= hi
