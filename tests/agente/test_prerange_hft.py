"""PRERANGE-HFT: ventana, causalidad con zonas, oráculo de S, escala, controles y preflight."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from edgelab.research import grilla_generica as GG, indicadores as I, preflight as PF, prerange_hft as X, sintetico

ROOT = Path(__file__).resolve().parents[2]
DIA = 1760054400            # 2025-10-10 00:00 UTC; EDT: 08:12 ET = 12:12 UTC


def _ctx(dias=45, planta=False, seed=17):
    return GG.contexto_m1(sintetico.bloques(dias=dias, planta=planta, seed=seed), tick=0.25)


def _ctx_mano(barrido_min):
    """M1 de 08:00 a 11:00 ET con rango [100,110] y un barrido al alza que abre en `barrido_min` (minutos ET) y reingresa en la siguiente."""
    mins = np.arange(480, 660); n = len(mins); t = DIA + (mins + 240) * 60 + 60
    c = np.full(n, 105.0); h = c + 1; l = c - 1; o = c.copy()
    ini = np.flatnonzero(mins == 492)[0]; h[ini] = 110; l[ini + 1] = 100
    i = np.flatnonzero(mins == barrido_min)[0]
    h[i], c[i] = 113.0, 111.0; c[i + 1] = 108.0
    return dict(t=t.astype(np.int64), o=o, h=h, l=l, c=c, v=np.full(n, 10.0), ses=np.zeros(n, np.int64), tick=0.25,
                zonas={f: pd.DataFrame(columns=["t_ns", "lo", "hi"]) for f in X.FUENTES_ZONAS})


def test_barrido_en_0912_0929_dispara_y_antes_no():
    D = X.disparos(_ctx_mano(555))                                         # 09:15, fuera de OTR-930
    assert set(D.gat) >= {0, 2} and (D.lado == 1).all() and D.E_exc.iloc[0] == 113
    assert D.lo_rng.iloc[0] == 100 and D.hi_rng.iloc[0] == 110             # el barrido no extendió el rango
    assert len(X.disparos(_ctx_mano(545))) == 0                            # 09:05 cae dentro de la ventana: ensancha el rango


def _oraculo(kk, ref, ext, esc, zi, zlo, zhi, ht, lt, v, umbral):
    S, D = np.zeros(len(kk)), np.full(len(kk), X.DIST_SIN_ZONA)
    for d, k in enumerate(kk):
        for z in range(len(zi)):
            if not k - X.VIDA <= zi[z] <= k: continue
            vivos = []
            for p in range(zlo[z], zhi[z] + 1):
                acc = 0.0; muerto = False
                for j in range(zi[z] + 1, min(k, zi[z] + X.VIDA) + 1):
                    if lt[j] <= p <= ht[j]: acc += max(1.0, v[j] / (ht[j] - lt[j] + 1.0))
                    if acc >= umbral: muerto = True; break
                if not muerto: vivos.append(p)
            if not vivos: continue
            lo, hi = min(vivos), max(vivos); dist = lambda r: (lo - r if r < lo else (r - hi if r > hi else 0.0)) * esc[d]
            if dist(ref[d]) <= X.MAXD: S[d] += 1 / (1 + dist(ref[d]) / 2)
            D[d] = min(D[d], dist(ext[d]))
    return S, D


def test_oraculo():
    rng = np.random.default_rng(3); n = 900
    c = np.cumsum(rng.integers(-3, 4, n)) + 1000.0; ht = c + rng.integers(0, 6, n); lt = c - rng.integers(0, 6, n); v = rng.integers(1, 200, n).astype(float)
    zi = np.sort(rng.integers(0, n - 1, 60)); zlo = (c[zi] + rng.integers(-8, 8, 60)).astype(np.int64); zhi = zlo + rng.integers(0, 4, 60)
    kk = np.sort(rng.integers(0, n, 80)); ref = np.round(c[kk] + rng.integers(-10, 10, 80)); ext = ref + 3; esc = rng.choice([0.5, 1.0, 2.0], 80)
    off, muerte = X._desgaste_nb(zi, zlo, zhi, ht, lt, v, np.asarray(X.UMBRALES), X.VIDA)
    for u, um in enumerate(X.UMBRALES):
        S, D = X._confluencia_nb(kk, ref, ext, esc, zi, zlo, off, muerte, u, X.VIDA, X.MAXD, X.DIST_SIN_ZONA)
        So, Do = _oraculo(kk, ref, ext, esc, zi, zlo, zhi, ht, lt, v, um)
        np.testing.assert_allclose(S, So); np.testing.assert_allclose(D, Do)


def test_causal():
    ctx = _ctx()
    assert I.causal(X.disparos, ctx) == []
    t = ctx["t"]; n = len(t)                                               # con zonas fijas de TODO el período (también las futuras)
    k = np.arange(5, n, 11); Z = pd.DataFrame(dict(t_ns=t[k] * 10**9, lo=ctx["c"][k], hi=ctx["c"][k] + .25))
    assert I.causal(X.disparos, dict(ctx, zonas={f: Z for f in X.FUENTES_ZONAS})) == []


def test_zona_futura_no_cambia_S():
    ctx = _ctx(); D = X.disparos(ctx); k = int(D.k.iloc[len(D) // 2])
    Z = pd.DataFrame(dict(t_ns=[(int(ctx["t"][k]) + 1) * 10**9], lo=[D.hi_rng.iloc[len(D) // 2]], hi=[D.hi_rng.iloc[len(D) // 2]]))
    D2 = X.disparos(dict(ctx, zonas={f: Z for f in X.FUENTES_ZONAS}))
    assert (D2[D2.k <= k].S == 0).all()


def test_escala_comparable_entre_activos():
    """Mismo gráfico con tick 4 veces menor (NQ frente a ES): misma S y distancia escaladas."""
    kk = np.array([5]); zi = np.array([1]); args = dict(u=0, vida=500, maxd=20.0, sin_zona=1e6)
    H, Lo = np.full(10, 2000.0), np.full(10, 1990.0); v = np.ones(10)
    o1, m1 = X._desgaste_nb(zi, np.array([1000]), np.array([1000]), H, Lo, v, np.array([1e9]), 500)
    o4, m4 = X._desgaste_nb(zi, np.array([4000]), np.array([4000]), H * 4, Lo * 4, v, np.array([1e9]), 500)
    a = X._confluencia_nb(kk, np.array([1006.0]), np.array([1007.0]), np.array([1.0]), zi, np.array([1000]), o1, m1, **dict(args))
    b = X._confluencia_nb(kk, np.array([4024.0]), np.array([4028.0]), np.array([.25]), zi, np.array([4000]), o4, m4, **dict(args))
    np.testing.assert_allclose(a, b)


def test_con_sensor_sin_almacen_falla(tmp_path, monkeypatch):
    monkeypatch.setenv("ENTRADA", str(tmp_path)); monkeypatch.delenv("SELLADO", raising=False)
    with pytest.raises(FileNotFoundError): X.disparos(dict(_ctx(dias=12), sensor="YM"))


def test_niveles_lote_identico_y_sin_fade_en_extremo():
    ctx = _ctx(planta=True, seed=23); D = X.disparos(ctx); O1, O2 = GG.ops_por_fila(X, D, ctx), GG._ops_lote(X, D, ctx)
    assert np.array_equal(O1, O2, equal_nan=True)
    ret = [i for i, e in enumerate(X.EJECUCIONES) if e[0] == "RETORNO"]
    assert not np.isin(O1[D.gat.to_numpy()[O1[:, 0].astype(int)] == 2, 1], ret).any()


def test_control_ruido():
    viejo = GG.B_RW; GG.B_RW = 40
    try: res, _ = GG.correr(X, _ctx(dias=120, seed=31), modo="DESC", friccion=1.0, extra_adverso=.5, log=lambda s: None)
    finally: GG.B_RW = viejo
    assert res["canales"]["total"]["evaluables"] > 0 and res["canales"]["total"]["n_rechazadas_rw"] == 0


def _bloques_plantados(dias=120, tick=.25):
    """Rango en la ventana; 10:00 ET barre un lado, reingresa y baja hasta cerca del opuesto sin barrerlo: efecto plantado de RETORNO."""
    rng = np.random.default_rng(5); nivel = 20000.0
    for d in range(dias):
        base = (DIA + d * 86400) * 10**9; seg = np.arange(0, 10 * 3600, 5); lado = rng.choice([-1, 1])
        ts = base + (11 * 3600 + seg) * 10**9 + rng.integers(0, 4 * 10**9, len(seg)); x = seg / 60 + 7 * 60                   # x = minuto ET
        p = nivel + np.cumsum(rng.choice([-tick, 0, tick], len(seg))) * .3 + 30 * np.sin((x - 492) / 60 * 2 * np.pi) * ((x >= 492) & (x < 552))
        m = x >= 600; desp = np.where(x < 603, 45 * (x - 600) / 3, np.where(x < 608, 45 - 55 * (x - 603) / 5, -10 - 18 * np.minimum((x - 608) / 60, 1)))
        p = p + np.where(m, lado * desp, 0.0); p = np.round(p / tick) * tick
        nivel = float(p[0])
        yield pd.DataFrame(dict(ts_ns=ts, px=p, vol=rng.integers(1, 6, len(p)).astype(float), sesion=np.full(len(p), d), segmento=np.zeros(len(p), int)))


def test_control_plantado():
    ctx = GG.contexto_m1(_bloques_plantados(), tick=.25); viejo = GG.B_RW; GG.B_RW = 100
    try: res, _ = GG.correr(X, ctx, modo="DESC", friccion=1.0, extra_adverso=.5, log=lambda s: None)
    finally: GG.B_RW = viejo
    tot = res["canales"]["total"]; assert tot["n_rechazadas_rw"] > 0 and tot["pistas"]
    mejor = tot["pistas"][0]; ej = X.EJECUCIONES[mejor["celda"][-1]]
    assert ej[0] == "RETORNO" and mejor["media_neta"] > 0


def test_diagnostico_marca_degeneracion():
    D = X.disparos(_ctx()); dg = X.diagnostico_e0(D.assign(S=0.0, hay=0))
    assert all(f["veredicto"] == "DEGENERADA_CASI_TODO_S_0" for f in dg["por_fuente"].values())


def test_fuentes_de_zonas_reales_crean_zonas_con_rafagas():
    rng = np.random.default_rng(1); bl = []; px = 20000.0
    for d in range(3):
        ts, p, v = [], [], []; t = (1760000400 + d * 86400) * 10**9; q = px
        for i in range(9000):
            if i % 600 == 300:
                for _ in range(12):
                    t += 2_000_000; q += .25; ts.append(t); p.append(q); v.append(20.0)
            t += int(rng.integers(50, 400)) * 1_000_000; q += rng.choice([-.25, 0, .25]); ts.append(t); p.append(q); v.append(float(rng.integers(1, 4)))
        bl.append(pd.DataFrame(dict(ts_ns=ts, px=p, vol=v)))
    for fn in (X.zonas_hft2, X.zonas_hftnq):
        Z = fn(iter(bl), .25); assert len(Z) > 0 and (Z.hi >= Z.lo).all() and (Z.t_ns.diff().dropna() >= 0).all()


def test_preflight_y_n_celdas():
    assert PF.estatico(X) == [] and GG.n_celdas(X) == 7776 <= 30000
    assert "hftzones_universal" not in Path(X.__file__).read_text(encoding="utf-8")


@pytest.mark.parametrize("a", ["NQ", "ES", "YM"])
def test_campana(a):
    from edgelab.research import linaje as LN
    d = json.loads((ROOT / f"config/autopilot/grillas/campanas/PRERANGE-HFT-{a}.json").read_text(encoding="utf-8"))
    assert d["embudo"] and d["n_celdas_por_canal"] == GG.n_celdas(X) and d["conductor"] == "debian" and d["oos"][1] <= 20260930
    assert d["sensor"] == d["ejecucion"] == a and (ROOT / d["spec"]).exists() and LN.problemas(d["familia"]) == []
