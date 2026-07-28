# -*- coding: utf-8 -*-
"""Tests del generador browniano fixed-b y la cota de cobertura.

Los tests de propiedad usan un n_caminos reducido para mantener la suite
ligera. Los tests de regresión (sección B) usan las constantes congeladas
completas: GRILLA = 5000, N_CAMINOS = 50000, SEMILLA = 20260801.
"""
from __future__ import annotations

import re

import numpy as np
import pytest

from edgelab.stats.fixed_b import (
    FixedBError,
    GRILLA,
    N_CAMINOS,
    SEMILLA,
    _cdf_binomial,
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
        cota_de_cobertura(b, n_caminos=N_CAMINOS_PROP, grilla=GRILLA_PROP, semilla=SEMILLA)["beta"]
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


def test_golden_b_008_05():
    """Valores congelados con GRILLA=5000, N_CAMINOS=50000, SEMILLA=20260801."""
    assert cuantil_G(0.08, 0.05) == pytest.approx(0.03108019995653119, abs=1e-9)
    assert cuantil_G_sim(0.08, 0.05) == pytest.approx(0.02216909367528798, abs=1e-9)


def test_golden_b_008_10():
    assert cuantil_G(0.08, 0.10) == pytest.approx(0.0838948054770702, abs=1e-9)
    assert cuantil_G_sim(0.08, 0.10) == pytest.approx(0.06868072158226472, abs=1e-9)


def test_golden_beta_008():
    cota = cota_de_cobertura(0.08)
    assert cota["beta"] == pytest.approx(0.01664, abs=1e-9)
    assert cota["beta_por_supremo"] == pytest.approx(0.01664, abs=1e-9)


# --------------------------------------------------------------------- C) compuerta


def test_veredicto_cota_devuelve_estructura_y_veredicto_valido():
    v = veredicto_cota(0.08, 0.05)
    assert set(v.keys()) == {"b", "alpha", "beta", "ic_sup", "veredicto"}
    assert v["veredicto"] in {"APTO", "NO APTO", "INCONCLUSO"}
    assert v["b"] == pytest.approx(0.08)
    assert v["alpha"] == pytest.approx(0.05)


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
