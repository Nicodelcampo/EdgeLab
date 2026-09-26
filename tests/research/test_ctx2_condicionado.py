"""H-ES-CTX-2 - fija Holm, el MDE derivado del bootstrap y el p bilateral."""
from __future__ import annotations

import numpy as np
import pytest

from diag.tasa_senales.h_es_ctx2_condicionado import (FACTOR_MDE, HUECO_EPISODIO_MS,
                                                      TERCILES, holm,
                                                      mde_desde_bootstrap, p_bootstrap)

M = "ticks_por_ancho"


def ses(*bloques):
    return {i: {M: np.array(b, dtype=float)} for i, b in enumerate(bloques)}


# --------------------------------------------------------------------------
# Holm
# --------------------------------------------------------------------------

def test_holm_multiplica_por_m_el_mas_chico():
    r = holm([("a", 0.01), ("b", 0.04), ("c", 0.30)])
    assert r["a"] == pytest.approx(0.03)      # 3 * 0,01
    assert r["b"] == pytest.approx(0.08)      # 2 * 0,04
    assert r["c"] == pytest.approx(0.30)      # 1 * 0,30


def test_holm_es_monotono_no_decreciente():
    """Sin el acarreo, un p crudo mayor podria salir ajustado MENOR que uno anterior."""
    r = holm([("a", 0.02), ("b", 0.021), ("c", 0.9)])
    assert r["a"] <= r["b"] <= r["c"]


def test_holm_no_pasa_de_uno():
    r = holm([("a", 0.5), ("b", 0.6), ("c", 0.7)])
    assert all(v <= 1.0 for v in r.values())


def test_holm_con_una_sola_prueba_no_corrige():
    assert holm([("a", 0.03)])["a"] == pytest.approx(0.03)


def test_holm_es_menos_conservador_que_bonferroni():
    """Bonferroni multiplicaria TODOS por 3; Holm solo al mas chico."""
    r = holm([("a", 0.01), ("b", 0.04), ("c", 0.30)])
    assert r["c"] < 3 * 0.30


# --------------------------------------------------------------------------
# MDE derivado del bootstrap
# --------------------------------------------------------------------------

def test_mde_sale_del_ancho_del_intervalo():
    r = dict(ci95=[-1.959964, 1.959964])       # SE = 1 por construccion
    assert mde_desde_bootstrap(r) == pytest.approx(FACTOR_MDE, abs=1e-3)


def test_un_intervalo_mas_ancho_da_mas_MDE():
    a = mde_desde_bootstrap(dict(ci95=[-1.0, 1.0]))
    b = mde_desde_bootstrap(dict(ci95=[-10.0, 10.0]))
    assert b > a


def test_un_intervalo_colapsado_da_MDE_cero():
    assert mde_desde_bootstrap(dict(ci95=[3.0, 3.0])) == pytest.approx(0.0)


def test_sin_intervalo_devuelve_None():
    assert mde_desde_bootstrap({}) is None
    assert mde_desde_bootstrap(None) is None


def test_el_factor_es_el_de_80_por_ciento_de_potencia():
    assert FACTOR_MDE == pytest.approx(1.959964 + 0.841621)


# --------------------------------------------------------------------------
# p bilateral del bootstrap
# --------------------------------------------------------------------------

def test_p_nunca_es_cero():
    """Un efecto enorme sigue teniendo p >= 2/(B+1): con B replicas no se puede
    afirmar mas que eso."""
    d = ses(*[[100.0] * 5 for _ in range(15)])
    p = p_bootstrap(d, M, b=200, seed=1)
    assert p > 0.0 and p == pytest.approx(2 / 201, abs=1e-4)


def test_p_alto_cuando_el_efecto_cruza_cero():
    rng = np.random.default_rng(3)
    d = {i: {M: rng.normal(0, 5, 30)} for i in range(20)}
    assert p_bootstrap(d, M, b=300, seed=2) > 0.2


def test_p_es_determinista():
    d = ses([1.0, 2.0], [3.0, 4.0], [0.0, 1.0])
    assert p_bootstrap(d, M, b=200, seed=5) == p_bootstrap(d, M, b=200, seed=5)


def test_p_no_pasa_de_uno():
    d = ses(*[[0.0, 1.0, -1.0] for _ in range(10)])
    assert p_bootstrap(d, M, b=200, seed=7) <= 1.0


def test_sin_datos_devuelve_None():
    assert p_bootstrap({}, M) is None


# --------------------------------------------------------------------------
# Contextos congelados
# --------------------------------------------------------------------------

def test_los_terciles_cubren_el_percentil_sin_huecos_ni_solapes():
    for v in np.arange(0.0, 1.0, 0.01):
        assert sum(1 for lo, hi, _ in TERCILES if lo <= v < hi) == 1


def test_el_hueco_de_episodio_es_el_congelado():
    assert HUECO_EPISODIO_MS == 5_000
