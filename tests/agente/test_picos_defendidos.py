"""PICOS-DEFENDIDOS: velas de N minutos, causalidad, verificador independiente de cada disparo, controles de ruido y plantado,
preflight y campañas."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from edgelab.research import grilla_generica as GG, indicadores as I, preflight as PF, sintetico
from edgelab.research.agente import picos_defendidos as X
from edgelab.research.zonas_gaps import _atr_causal

ROOT = Path(__file__).resolve().parents[2]


def _ctx(dias=40, seed=11):
    return GG.contexto_m1(sintetico.bloques(dias=dias, planta=False, seed=seed), tick=0.25)


def _bloques_tendencia(dias=150, seed=7, tick=0.25, deriva=0.04):
    """Efecto plantado: cada día tiene una deriva fuerte con signo al azar. Un nivel defendido EN CONTRA de la deriva se toma después:
    las operaciones con tendencia a favor deberían ganar y las en contra, perder."""
    rng = np.random.default_rng(seed); nivel = 20000.0; t0 = 1_760_000_000 * 10**9
    for d in range(dias):
        n = 23 * 60 * 6; ts = t0 + d * 86400 * 10**9 + np.sort(rng.integers(0, 23 * 3600 * 10**9, n))
        paso = rng.choice([-tick, 0.0, tick], n, p=[.33, .34, .33]) + rng.choice([-1, 1]) * deriva
        p = nivel + np.cumsum(paso); nivel = float(p[-1])
        yield pd.DataFrame(dict(ts_ns=ts, px=np.round(p / tick) * tick, vol=rng.integers(1, 6, n).astype(float), sesion=np.full(n, d),
                                segmento=np.zeros(n, int)))


def test_velas_tf_ohlc_y_decision():
    base = 1_760_000_100 - (1_760_000_100 % 300); t = base + 60 * np.arange(1, 13)       # 12 M1: dos bloques de 5 cerrados y 2 abiertas
    o = np.arange(12.0); h = o + 1 + (np.arange(12) == 2); l = o - 1; c = o + .5; ses = np.zeros(12, np.int64)
    O, H, L, C, S, K, M = X.velas_tf(t, o, h, l, c, ses, 5)
    assert K.tolist() == [4, 9] and M.tolist() == [0, 5] and H.tolist() == [h[0:5].max(), h[5:10].max()] and C.tolist() == [c[4], c[9]]
    keep = np.arange(12) != 4                                                                # falta la M1 del borde: se decide en la siguiente
    O, H, L, C, S, K, M = X.velas_tf(t[keep], o[keep], h[keep], l[keep], c[keep], ses[keep], 5)
    assert K.tolist() == [4, 8] and C.tolist() == [c[3], c[9]]


def test_causal():
    ctx = _ctx(dias=30)
    assert I.causal(X.disparos, ctx) == []
    assert I.causal_por_disparo(X.disparos, ctx, n=25) == []


def test_verificador_independiente():
    """Para cada disparo (muestra), las condiciones se reconstruyen con fuerza bruta sobre las velas de su temporalidad: nivel no
    tomado hasta k, acercamiento a <= D·A sin tomarlo y alejamientos mínimos. Es el oráculo del detector compilado."""
    ctx = _ctx(dias=30); D = X.disparos(ctx); assert len(D) > 100
    t, o, h, l, c, ses = (np.asarray(ctx[x]) for x in ("t", "o", "h", "l", "c", "ses"))
    rng = np.random.default_rng(0)
    for i in rng.choice(len(D), 150, replace=False):
        r = D.iloc[int(i)]; tf = X.TFS[int(r.tf)]
        O, H, L, C, S, K, M = X.velas_tf(t.astype(np.int64), o, h, l, c, ses.astype(np.int64), tf)
        j = int(np.flatnonzero(K == r.k)[0]); s = int(r.lado); A = float(r.A)
        xh, xl, xc = (H, L, C) if s == 1 else (-L, -H, -C); P = s * float(r.P)
        jp = int(np.flatnonzero(K == r.kp)[0]); assert jp < j and S[jp] == S[j] and np.isclose(xh[jp], P)
        tramo_h, tramo_l = xh[jp + 1:j + 1], xl[jp + 1:j + 1]
        assert tramo_h.max() < P + ctx["tick"]                                         # no tomado desde el pico hasta k
        assert r.alej1 >= X.X1_MIN - 1e-9 and r.alej2 >= X.X2_MIN - 1e-9 and 0 <= r.cerca <= X.D_MAX + 1e-9
        assert (P - tramo_l.min()) / A >= r.alej1 - 1e-9                               # el alejamiento 1 existió
        assert tramo_h.max() >= P - X.D_MAX * A - 1e-9                                  # hubo acercamiento a <= D·A
        assert np.isclose(s * float(r.ext2), tramo_l.min()) or s * float(r.ext2) >= tramo_l.min() - 1e-9
        d = X.DISPARADORES[int(r.disp)]
        if d.startswith("REACERCA"):
            f = 1 / 3 if d.endswith("33") else 1 / 2; e2 = s * float(r.ext2)
            assert xc[j] >= e2 + f * (P - e2) - 1e-9
        if d == "ESPEJO_100": assert xc[j] >= P - r.cerca * A - 1e-6                  # volvió al máximo del acercamiento


def test_niveles_lote_igual_a_niveles():
    ctx = _ctx(dias=20); D = X.disparos(ctx).iloc[:400]
    O1, O2 = GG.ops_por_fila(X, D, ctx), GG._ops_lote(X, D, ctx)
    assert O1.shape == O2.shape and np.array_equal(O1, O2, equal_nan=True)


def test_riesgo_minimo_y_objetivo_mas_alla_del_nivel():
    ctx = _ctx(dias=20); D = X.disparos(ctx).iloc[:300]
    for ej in X.EJECUCIONES:
        Z = X.niveles_lote(D, ej, ctx); ok = np.isfinite(Z[:, 0]); s = Z[ok, 2]
        assert np.all((Z[ok, 3] - Z[ok, 4]) * s >= X.RIESGO_MIN * D.A.to_numpy()[ok] - ctx["tick"] - 1e-9)
        assert np.all((Z[ok, 5] - D.P.to_numpy()[ok]) * s >= ctx["tick"] - 1e-9)


def test_control_ruido():
    v = GG.B_RW; GG.B_RW = 40
    try: res, _ = GG.correr(X, _ctx(dias=120, seed=31), modo="DESC", friccion=1.0, extra_adverso=.5, log=lambda s: None)
    finally: GG.B_RW = v
    tot = res["canales"]["total"]
    assert tot["evaluables"] > 0 and tot["nominadas_fdr"] == 0


def test_control_plantado():
    ctx = GG.contexto_m1(_bloques_tendencia(), tick=.25); v = GG.B_RW; GG.B_RW = 100
    try: res, _ = GG.correr(X, ctx, modo="DESC", friccion=1.0, extra_adverso=.5, log=lambda s: None)
    finally: GG.B_RW = v
    tot = res["canales"]["total"]; assert tot["n_rechazadas_rw"] > 0 and tot["pistas"]
    mejor = tot["pistas"][0]; nom = [p.nombre for p in GG.perillas(X, res.get("cortes", {}))]
    assert mejor["media_neta"] > 0 and mejor["celda"][nom.index("tendencia")] != 1          # nunca «en contra» de la deriva plantada


def test_preflight():
    assert PF.estatico(X) == []
    err, _ = PF.dinamico(X); assert err == []


@pytest.mark.parametrize("a", ["NQ", "ES"])
def test_campana(a):
    from edgelab.research import linaje as LN
    p = ROOT / f"config/autopilot/grillas/campanas/PICOS-DEFENDIDOS-{a}.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    assert d["embudo"] and d["experimento"] == X.__name__ and d["n_celdas_por_canal"] == GG.n_celdas(X)
    assert d["desc"][1] <= 20260331 and d["oos"] == [20260401, 20260930] and d["holdout"]["desde"] >= 20261001
    assert d["estadistico"] == "R" and d["conductor"] in ("debian", "local")
    assert not d["activa"] or any("se lanza" in x for x in d.get("decisiones", [])), "activa sin la decisión de lanzarla registrada"
    assert LN.problemas(d["familia"]) == []
