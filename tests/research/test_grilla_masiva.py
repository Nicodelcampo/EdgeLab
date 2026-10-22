"""Núcleo genérico de grilla masiva: el tensor acumulado coincide con filtrar operación por operación, en los cinco modos."""
import itertools

import numpy as np

from edgelab.research import grilla_masiva as GM


def test_tensor_igual_a_fuerza_bruta_en_todos_los_modos():
    rng = np.random.default_rng(5); T = 3000
    P = [GM.Perilla("g", 2, "grupo"), GM.Perilla("ge", 4, "ge"), GM.Perilla("le", 3, "le"), GM.Perilla("eq", 3, "eq_any"), GM.Perilla("ex", 3, "extremos")]
    idx = [rng.integers(0, p.niveles, T) for p in P]; v = rng.normal(0, 1, T)
    S, Q, C = GM.tensor(P, idx, v)
    assert S.shape == tuple(p.tamano_celdas() for p in P)
    for cel in itertools.product(*[range(p.tamano_celdas()) for p in P]):
        m = GM.mascara(P, idx, cel)
        assert C[cel] == m.sum() and np.isclose(S[cel], v[m].sum()) and np.isclose(Q[cel], (v[m] ** 2).sum())


def test_criba_ruido_no_nomina_y_efecto_si():
    rng = np.random.default_rng(1); T = 20000
    P = [GM.Perilla("a", 10, "grupo"), GM.Perilla("b", 4, "ge")]
    a, b = rng.integers(0, 10, T), rng.integers(0, 4, T)
    ruido = rng.normal(0, 1, T)
    st = GM.estadisticas(*GM.tensor(P, [a, b], ruido)); assert len(GM.criba(st)["nominadas"]) <= 2
    efecto = ruido + np.where(a == 3, 0.5, 0)                    # sólo el grupo 3 tiene edge
    nom = GM.criba(GM.estadisticas(*GM.tensor(P, [a, b], efecto)))["nominadas"]
    assert nom and all(c[0] == 3 for c in nom)
