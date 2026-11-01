"""PRERANGE-ZONAS: causalidad as-of, oráculo, escala, pares, poda, controles de ruido y plantado, preflight y campañas."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from edgelab.research import grilla_generica as GG, indicadores as I, preflight as PF, prerange_zonas as Z, sintetico
from test_prerange_hft import _bloques_plantados

ROOT = Path(__file__).resolve().parents[2]


def _ctx(dias=45, seed=17):
    return GG.contexto_m1(sintetico.bloques(dias=dias, planta=False, seed=seed), tick=0.25)


def test_causal_con_zonas_de_todo_el_periodo():
    ctx = _ctx(); assert I.causal(Z.disparos, ctx) == []
    t = ctx["t"]; k = np.arange(5, len(t), 11); F = pd.DataFrame(dict(t_ns=t[k] * 10**9, lo=ctx["c"][k], hi=ctx["c"][k] + .25))
    assert I.causal(Z.disparos, dict(ctx, zonas={"A": F, "B": F})) == []


def test_zona_de_la_vela_del_disparo_y_futuras_no_cuentan():
    ctx = _ctx(); B = Z.base_disparos(ctx); b = B.iloc[len(B) // 2]; k = int(b.k); t = int(ctx["t"][k])
    F = pd.DataFrame(dict(t_ns=[t * 10**9, (t + 60) * 10**9], lo=[b.hi_rng + 1] * 2, hi=[b.hi_rng + 2] * 2))
    D, P, Y = Z.relativas(B.iloc[[len(B) // 2]], dict(ctx, zonas={"A": F}), "A"); assert len(D) == 0
    F2 = F.assign(t_ns=[(t - 60) * 10**9, t * 10**9])
    D, P, Y = Z.relativas(B.iloc[[len(B) // 2]], dict(ctx, zonas={"A": F2}), "A"); assert len(D) == 1 and P[0] == 0


def test_zona_terminada_no_cuenta():
    ctx = _ctx(); B = Z.base_disparos(ctx).iloc[[5]]; k = int(B.k.iloc[0]); t = ctx["t"]
    F = pd.DataFrame(dict(t_ns=[t[k - 9] * 10**9] * 2, lo=[1.0, 1.0], hi=[2.0, 2.0], t_fin_ns=[t[k - 1] * 10**9, t[k + 1] * 10**9]))
    assert len(Z.relativas(B, dict(ctx, zonas={"A": F}), "A")[0]) == 1


def test_oraculo():
    r = np.random.default_rng(3); n = 80
    kk = np.sort(r.integers(10, 900, n)); lo = r.uniform(90, 100, n); hi = lo + r.uniform(1, 9, n); la = r.choice([-1, 1], n); atr = r.uniform(.5, 3, n)
    zi = np.sort(r.integers(0, 900, 300)); zl = r.uniform(80, 120, 300); zh = zl + r.uniform(0, 3, 300); fin = zi + r.integers(1, 400, 300)
    a = sorted(zip(*(x.tolist() for x in Z._relativas_nb(kk, lo, hi, la, atr, zi, zl, zh, fin, 300))))
    assert np.allclose(np.array(a), np.array(Z.relativas_py(kk, lo, hi, la, atr, zi, zl, zh, fin, 300)))


def test_escala_por_atr():
    ctx = _ctx(); B = Z.base_disparos(ctx); F = pd.DataFrame(dict(t_ns=[ctx["t"][0] * 10**9], lo=[1.0], hi=[2.0]))
    B2 = B.assign(atr=B.atr * 2, lo_rng=B.lo_rng, hi_rng=B.hi_rng); k0 = B.assign(k=Z.VIDA // 2); k0 = k0[:5]
    a = Z.relativas(k0, dict(ctx, zonas={"A": F}), "A")[2]; b = Z.relativas(k0.assign(atr=k0.atr * 2), dict(ctx, zonas={"A": F}), "A")[2]
    assert len(B2) and np.allclose(a, 2 * b)


def test_par_es_el_minimo():
    a = np.array([[[3, 3]] * 3]); b = np.array([[[1, 5]] * 3])
    assert (Z._conj({"A": a, "B": b}, "A+B") == np.array([[[1, 3]] * 3])).all()


def test_avzp2_usa_la_decision(tmp_path, monkeypatch):
    pd.DataFrame(dict(t_ns=[10, 20], lo=[1., 1.], hi=[2., 2.], t_decidida_ns=[50, -1])).to_parquet(tmp_path / "ZONAS_AVZP2_NQ.parquet")
    monkeypatch.setenv("ENTRADA", str(tmp_path))
    assert Z.cargar_zonas(dict(sensor="NQ"), "AVZP2").t_ns.tolist() == [50]


def test_con_sensor_sin_cortes_falla():
    ctx = _ctx(); ctx["sensor"] = "GC"
    with pytest.raises(ValueError): Z.disparos(ctx)


def test_censo_marca_degeneradas_duplicadas_y_poda():
    ctx = _ctx(dias=120); ctx["zonas"] = {"A": Z._control(ctx, 15), "B": Z._control(ctx, 22), "V": pd.DataFrame(dict(t_ns=[0], lo=[1.], hi=[2.]))}
    c = Z.censo(ctx, ("A", "B", "V")); f = c["conjuntos"]
    assert set(f) == {"A", "B", "V", "A+B", "A+V", "B+V"} and f["V"]["evaluables"] == 0
    assert all(x["evaluables"] == x["unicas"] + x["duplicadas"] for x in f.values())
    assert Z.podar(c, min_unicas=1)[0] in f and "V" not in Z.podar(c, min_unicas=1)


def test_control_ruido():
    v = GG.B_RW; GG.B_RW = 40
    try: res, _ = GG.correr(Z, _ctx(dias=120, seed=31), modo="DESC", friccion=1.0, extra_adverso=.5, log=lambda s: None)
    finally: GG.B_RW = v
    assert res["canales"]["total"]["evaluables"] > 0 and res["canales"]["total"]["n_rechazadas_rw"] == 0


def test_control_plantado():
    ctx = GG.contexto_m1(_bloques_plantados(), tick=.25); v = GG.B_RW; GG.B_RW = 100
    try: res, _ = GG.correr(Z, ctx, modo="DESC", friccion=1.0, extra_adverso=.5, log=lambda s: None)
    finally: GG.B_RW = v
    t = res["canales"]["total"]; assert t["n_rechazadas_rw"] > 0 and Z.EJECUCIONES[t["pistas"][0]["celda"][-1]][0] == "RETORNO"


def test_preflight():
    assert PF.estatico(Z) == [] and GG.n_celdas(Z) <= 30000
    err, _ = PF.dinamico(Z); assert err == []


@pytest.mark.parametrize("a", ["NQ", "ES", "YM"])
def test_campana(a):
    from edgelab.research import linaje as LN
    p = ROOT / f"config/autopilot/grillas/campanas/PRERANGE-ZONAS-{a}.json"
    if not p.exists(): pytest.skip("sin campaña")
    d = json.loads(p.read_text(encoding="utf-8"))
    assert d["embudo"] and d["n_celdas_por_canal"] == GG.n_celdas(Z) and d["oos"][1] <= 20260930
    assert not d["activa"] or any("se lanza" in x for x in d.get("decisiones", [])), "activa sin la decisión de lanzarla registrada"
    assert LN.problemas(d["familia"]) == [] and a in Z.CORTES
    assert len(Z.CORTES[a]["conjuntos"]) <= Z.N_CONJ
