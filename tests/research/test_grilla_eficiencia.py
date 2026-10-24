"""Oráculos de las optimizaciones del núcleo de grilla (2026-10-24): cada camino rápido da EXACTAMENTE lo mismo que el lento.

- Romano-Wolf por pares (sesión, celda) + producto matricial  ==  un tensor denso por réplica (implementación anterior);
- p de `estadisticas` con erf vectorizado                       ==  1 - NormalDist().cdf;
- `aplicar_tope_lote` / `_trasladar` vectorizados               ==  sus versiones escalares / en bucle;
- `niveles_lote` de un experimento                              ==  `niveles` fila por fila (lo exige el preflight).
"""
from statistics import NormalDist

import numpy as np
import pandas as pd
import pytest

from edgelab.research import grilla_generica as GG
from edgelab.research import grilla_masiva as GM

MODOS = ("grupo", "ge", "le", "eq_any", "extremos")


def _grilla(seed, n=6000, n_ses=50, efecto=0.0):
    rng = np.random.default_rng(seed)
    P = [GM.Perilla("a", 4, "ge"), GM.Perilla("b", 3, "grupo"), GM.Perilla("c", 3, "le"), GM.Perilla("d", 3, "eq_any"),
         GM.Perilla("e", 3, "extremos"), GM.Perilla("f", 1, "extremos")]
    idx = [rng.integers(-1, 4, n), rng.integers(0, 3, n), rng.integers(0, 3, n), rng.integers(0, 3, n), rng.integers(0, 3, n),
           np.zeros(n, int)]
    ses = rng.integers(0, n_ses, n)
    x = rng.normal(0, 1, n) + rng.normal(0, 0.5, n_ses)[ses]
    x[(idx[0] == 3) & (idx[1] == 1)] += efecto
    x[::101] = np.nan                                                            # sin llenado: fuera de toda celda
    return P, idx, x, ses, GM.estadisticas(*GM.tensor(P, idx, x), min_n=10)


@pytest.mark.parametrize("bloque", [None, 3000])
def test_medias_bootstrap_iguales_al_denso(bloque):
    P, idx, x, ses, st = _grilla(1)
    ev = st["evaluable"].ravel(); us, inv = np.unique(ses, return_inverse=True)
    W = np.random.default_rng(3).multinomial(len(us), np.full(len(us), 1 / len(us)), size=40).astype(float)
    M1 = GM._medias_bootstrap_denso(P, idx, x, inv, ev, W)
    bs = GM._Bootstrap(P, idx, x, inv, len(us), ev, W, bloque_bytes=bloque)
    M2 = np.concatenate([M for _, _, M in bs.bloques()], 1)
    assert bloque is None or bs.ancho < bs.n_ev                                 # el caso por bloques de verdad parte en bloques
    assert np.array_equal(np.isnan(M1), np.isnan(M2)) and np.nanmax(np.abs(M1 - M2)) <= 1e-6


def _romano_wolf_denso(perillas, indices, valores, sesiones, st, B, alfa, seed, pasos=5):
    """La implementación anterior completa (oráculo)."""
    ev = st["evaluable"].ravel(); m0 = st["media"].ravel()[ev].astype(np.float32)
    us, inv = np.unique(np.asarray(sesiones), return_inverse=True); rng = np.random.default_rng(seed)
    W = np.stack([rng.multinomial(len(us), np.full(len(us), 1 / len(us))) for _ in range(B)]).astype(float)
    M = GM._medias_bootstrap_denso(perillas, indices, valores, inv, ev, W)
    sd = np.nanstd(M, 0); sd[~(sd > 0)] = np.nan; t = m0 / sd; M -= m0; M /= sd
    activos = np.isfinite(t); rech = np.zeros(len(t), bool); umbrales = []
    for _ in range(pasos):
        mx = np.nanmax(np.where(activos, M, -np.inf), axis=1); c = float(np.quantile(mx, 1 - alfa)); umbrales.append(c)
        nuevo = activos & (t > c)
        if not nuevo.any(): break
        rech |= nuevo; activos &= ~nuevo
    mx0 = np.nanmax(np.where(np.isfinite(t), M, -np.inf), axis=1)
    return t, umbrales, rech, mx0


@pytest.mark.parametrize("seed,efecto,memoria", [(2, 0.0, None), (5, 0.9, None), (5, 0.9, 1)])
def test_romano_wolf_igual_al_denso(seed, efecto, memoria, monkeypatch):
    P, idx, x, ses, st = _grilla(seed, efecto=efecto)
    if memoria: monkeypatch.setattr(GM, "RW_MEMORIA_BYTES", memoria)              # sin caché: recalcula cada paso por bloques
    r = GM.romano_wolf(P, idx, x, ses, st, B=80, alfa=0.10, seed=seed)
    t, umbrales, rech, mx0 = _romano_wolf_denso(P, idx, x, ses, st, B=80, alfa=0.10, seed=seed)
    ev = np.flatnonzero(st["evaluable"].ravel())
    assert np.allclose(r["t"].ravel()[ev], t, equal_nan=True, rtol=1e-6)
    assert np.allclose(r["umbrales"], umbrales, rtol=1e-6)
    assert r["rechazadas"] == [tuple(int(v) for v in np.unravel_index(f, st["n"].shape)) for f in ev[rech]]
    assert np.isclose(r["nula_max_q"]["q90"], float(np.quantile(mx0, .9)), rtol=1e-6)
    if efecto: assert r["rechazadas"]                                             # lo plantado se encuentra igual que antes


def test_cola_superior_igual_a_normaldist():
    t = np.r_[np.random.default_rng(0).normal(0, 3, 5000), 0.0, 8.0, -8.0, 40.0, -40.0]
    ref = np.array([1 - NormalDist().cdf(v) for v in t])
    assert np.max(np.abs(GM._cola_superior(t) - ref)) <= 2.3e-16


def test_aplicar_tope_lote_igual_al_escalar():
    rng = np.random.default_rng(4); n = 3000; tick = 0.25
    s = rng.choice([-1, 1], n); e = np.round(rng.normal(20000, 50, n) / tick) * tick
    st = e - s * np.round(rng.uniform(0.25, 40, n) / tick) * tick; tp = e + s * np.round(rng.uniform(0.25, 40, n) / tick) * tick
    for tope in (None, ("pts", 10.0), ("mult", 1.0), ("mult", 3.0)):
        ref = np.array([GG.aplicar_tope(e[i], int(s[i]), st[i], tp[i], tope, tick) for i in range(n)])
        assert np.array_equal(GG.aplicar_tope_lote(e, s, st, tp, tope, tick), ref)


def _ctx(seed, n=3000, tick=0.25, desfase=0.0, huecos=()):
    rng = np.random.default_rng(seed); c = 20000 + desfase + np.cumsum(rng.choice([-tick, 0, tick], n))
    h, l = c + tick * rng.integers(0, 4, n), c - tick * rng.integers(0, 4, n)
    t = np.arange(n) * 60.0; keep = np.ones(n, bool); keep[list(huecos)] = False
    return dict(t=t[keep], c=c[keep], h=h[keep], l=l[keep], o=c[keep], ses=(np.arange(n) // 400)[keep], tick=tick)


@pytest.mark.parametrize("retraso", [0, 1, 3])
def test_trasladar_igual_al_bucle(retraso):
    ctx = _ctx(1); cx = _ctx(2, desfase=37.3, huecos=range(500, 540))
    rng = np.random.default_rng(9); n = 1500; k = rng.integers(0, len(ctx["t"]), n); s = rng.choice([-1, 1], n)
    e = ctx["c"][k]; O = np.column_stack([np.arange(n), np.zeros(n), k, rng.choice([0, 1, 2], n), s, e,
                                          e - s * rng.uniform(0.5, 6, n), e + s * rng.uniform(0.5, 6, n), np.zeros(n)]).astype(float)
    O1, ok1 = GG._trasladar_bucle(O, ctx, cx, retraso); O2, ok2 = GG._trasladar(O, ctx, cx, retraso)
    assert ok1.any() and (~ok1).any() and np.array_equal(ok1, ok2) and np.array_equal(O1, O2)


class _ExpLote:
    """Experimento mínimo con niveles y niveles_lote (el patrón que sigue cualquier módulo del agente)."""
    NOMBRE = "LOTE"; EJECUCIONES = [(d, m) for d in (1, -1) for m in (1.0, 2.0)]

    @staticmethod
    def niveles(r, ej, ctx):
        d, m = ej; k = int(r["k"]); e = float(ctx["c"][k]); a = float(r["a"])
        if a < 1: return None
        return k, 0, d, e, e - d * a, e + d * m * a, 0

    @staticmethod
    def niveles_lote(D, ej, ctx):
        d, m = ej; k = D.k.to_numpy(); e = ctx["c"][k]; a = D.a.to_numpy(float)
        X = np.column_stack([k, np.zeros(len(D)), np.full(len(D), d), e, e - d * a, e + d * m * a, np.zeros(len(D))]).astype(float)
        X[~(a >= 1), 0] = np.nan
        return X


def test_niveles_lote_mismo_orden_y_valores():
    ctx = _ctx(3); rng = np.random.default_rng(0)
    D = pd.DataFrame(dict(k=rng.integers(0, len(ctx["c"]), 400), a=rng.uniform(0, 5, 400)))
    O1 = GG.ops_por_fila(_ExpLote, D, ctx); O2 = GG._ops_lote(_ExpLote, D, ctx)
    assert len(O1) and np.array_equal(O1, O2)
