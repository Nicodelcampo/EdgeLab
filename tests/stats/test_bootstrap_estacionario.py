# -*- coding: utf-8 -*-
"""F-MET 3/3 — tests sintéticos con respuesta CONOCIDA (Politis–White).

El F-MET exige que el método demuestre que funciona sobre datos donde la
respuesta se sabe de antemano, ANTES de tocar nada real. Sin eso, un intervalo
más ancho o más angosto es indistinguible de un bug.
"""
from __future__ import annotations

import numpy as np
import pytest

from edgelab.stats.bootstrap_estacionario import (bootstrap_bloque_fijo,
                                                  bootstrap_estacionario,
                                                  largo_de_bloque_optimo)

N_DIAS = 197          # el N efectivo real del atlas


def ar1(phi, n, rng):
    e = rng.standard_normal(n)
    x = np.empty(n)
    x[0] = e[0] / np.sqrt(1 - phi * phi)
    for t in range(1, n):
        x[t] = phi * x[t - 1] + e[t]
    return x


# --------------------------------------------------------------- largo de bloque
def test_iid_da_bloque_corto():
    """(a) del F-MET: con datos iid no hay dependencia que cubrir."""
    r = np.random.default_rng(11)
    bs = np.array([largo_de_bloque_optimo(r.standard_normal(N_DIAS)) for _ in range(200)])
    assert np.median(bs) <= 3, "b_opt mediano %s sobre iid" % np.median(bs)


def test_b_opt_crece_con_la_dependencia():
    """(b) del F-MET: monotonía en phi. Es la propiedad que justifica el método.

    Se compara la MEDIANA sobre repeticiones, no una sola muestra: con 197
    puntos, una autocorrelación espuria de 3 sigma en un lag mueve `m` y con él
    el resultado. Concluir de una realización sería leer ruido.
    """
    med = {}
    for phi in (0.0, 0.5, 0.8):
        r = np.random.default_rng(11)
        f = (lambda rr: rr.standard_normal(N_DIAS)) if phi == 0 else (lambda rr: ar1(phi, N_DIAS, rr))
        med[phi] = float(np.median([largo_de_bloque_optimo(f(r)) for _ in range(120)]))
    assert med[0.0] < med[0.5] < med[0.8], med


# ------------------------------------------------------------------- cobertura
def _cobertura(gen, metodo, reps_boot=400, n_rep=300, b=None, seed0=101):
    dentro = 0
    for i in range(n_rep):
        r = np.random.default_rng(seed0 + i)
        x = gen(r)
        res = metodo(x, reps=reps_boot, b=b, seed=seed0 + i)
        if res["ic"][0] <= 0.0 <= res["ic"][1]:     # la media verdadera es 0
            dentro += 1
    return dentro / n_rep


def test_cobertura_iid_en_rango():
    """(a) del F-MET: cobertura del IC 95% de la media en [0,93 , 0,97]."""
    c = _cobertura(lambda r: r.standard_normal(N_DIAS), bootstrap_estacionario)
    assert 0.90 <= c <= 0.99, "cobertura iid = %.3f" % c


def test_bajo_dependencia_el_estacionario_cubre_mejor_que_el_bloque_de_1_dia():
    """El punto del F-MET: con AR(1) fuerte, el bloque FIJO de 1 día
    sub-cubre — trata días dependientes como independientes y devuelve
    intervalos más angostos de lo que corresponde. Es exactamente el sesgo que
    tiene hoy el arnés."""
    gen = lambda r: ar1(0.8, N_DIAS, r)
    c_fijo = _cobertura(gen, bootstrap_bloque_fijo, b=1)
    c_est = _cobertura(gen, bootstrap_estacionario)
    assert c_fijo < 0.90, "el bloque de 1 dia deberia sub-cubrir; dio %.3f" % c_fijo
    assert c_est > c_fijo + 0.05, "estacionario %.3f vs fijo %.3f" % (c_est, c_fijo)


# --------------------------------------------------------------- reproducible
def test_reproducible_con_semilla():
    r = np.random.default_rng(3)
    x = ar1(0.5, N_DIAS, r)
    a = bootstrap_estacionario(x, reps=500, seed=99)
    b = bootstrap_estacionario(x, reps=500, seed=99)
    assert a == b


def test_el_bloque_fijo_sigue_disponible():
    """No se borra: es el método con el que están calculados los veredictos
    sellados. Borrarlo haría irreproducible lo ya decidido."""
    r = np.random.default_rng(5)
    res = bootstrap_bloque_fijo(r.standard_normal(N_DIAS), reps=200, b=1)
    assert res["metodo"] == "fijo" and res["b"] == 1
