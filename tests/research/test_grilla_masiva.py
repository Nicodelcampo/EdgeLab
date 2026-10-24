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


def test_resumen_nulo_publica_mde_y_dos_colas():
    rng = np.random.default_rng(3)
    P = [GM.Perilla("a", 4, "grupo"), GM.Perilla("b", 3, "grupo")]
    n = 20000; idx = [rng.integers(0, 4, n), rng.integers(0, 3, n)]; x = rng.normal(0, 2.0, n)
    S, Q, C = GM.tensor(P, idx, x); st = GM.estadisticas(S, Q, C)
    r = GM.resumen_nulo(st, P, q=0.10, referencia=0.5)
    assert r["evaluables"] == 12 and r["celdas"] == 12
    se = 2.0 / np.sqrt(n / 12)                                                   # ~ error estándar de cada celda
    assert abs(r["mde_confirmacion"]["mediana"] - (1.645 + 0.8416) * se) < 0.25 * (1.645 + 0.8416) * se
    assert r["mde_tamiz"]["mediana"] > r["mde_confirmacion"]["mediana"]          # el tamiz exige más que una sola prueba
    tv = st["t"][st["evaluable"]]                                                # las dos colas, contadas igual que a mano
    assert r["t"]["sobre_z_tamiz"] == int((tv > r["z_tamiz"] - 5e-4).sum()) == int((tv > r["z_tamiz"]).sum())
    assert r["t"]["bajo_menos_z_tamiz"] == int((tv < -r["z_tamiz"]).sum())
    assert [f["nivel"] for f in r["por_perilla"]["a"]] == [0, 1, 2, 3] and "detectarian_referencia" in r


def _grilla_sesiones(seed, efecto=0.0, n_ses=60, por_ses=120):
    rng = np.random.default_rng(seed); n = n_ses * por_ses
    ses = np.repeat(np.arange(n_ses), por_ses)
    P = [GM.Perilla("a", 4, "ge"), GM.Perilla("b", 5, "grupo"), GM.Perilla("c", 3, "le")]
    idx = [rng.integers(0, 4, n), rng.integers(0, 5, n), rng.integers(0, 3, n)]
    x = rng.normal(0, 1, n) + rng.normal(0, 0.5, n_ses)[ses]                   # dependencia dentro de la sesión
    x[(idx[0] == 3) & (idx[1] == 2)] += efecto
    S, Q, C = GM.tensor(P, idx, x); return P, idx, x, ses, GM.estadisticas(S, Q, C)


def test_romano_wolf_controla_fwer_con_ruido_y_encuentra_plantado():
    falsos = sum(bool(GM.romano_wolf(*_grilla_sesiones(s)[:4], _grilla_sesiones(s)[4], B=150, alfa=0.10, seed=s)["rechazadas"]) for s in range(30))
    assert falsos <= 7                                                           # ~10 % de 30, con margen binomial
    P, idx, x, ses, st = _grilla_sesiones(99, efecto=0.8)
    rw = GM.romano_wolf(P, idx, x, ses, st, B=150, alfa=0.10, seed=1)
    assert (3, 2, 0) in rw["rechazadas"] or any(c[0] == 3 and c[1] == 2 for c in rw["rechazadas"])
    assert all(c[1] == 2 for c in rw["rechazadas"])                              # sólo celdas que contienen lo plantado ("ge" acumula a)


def test_tensor_con_pesos_equivale_a_repetir_operaciones():
    P, idx, x, ses, _ = _grilla_sesiones(4)
    w = (np.arange(len(x)) % 3).astype(float)
    S1, Q1, C1 = GM.tensor(P, idx, x, pesos=w)
    rep = np.repeat(np.arange(len(x)), w.astype(int))
    S2, Q2, C2 = GM.tensor(P, [i[rep] for i in idx], x[rep])
    assert np.allclose(S1, S2) and np.allclose(Q1, Q2) and np.allclose(C1, C2)


def test_pistas_distintas_entre_si():
    P, idx, x, ses, st = _grilla_sesiones(7, efecto=0.3)
    rw = GM.romano_wolf(P, idx, x, ses, st, B=60, seed=2)
    ps = GM.pistas(st, rw["t"], k=10, min_dif=2)
    assert 0 < len(ps) <= 10
    for i, a in enumerate(ps):
        for b in ps[i + 1:]: assert sum(u != v for u, v in zip(a, b)) >= 2
