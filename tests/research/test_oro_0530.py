import numpy as np
import pandas as pd

from edgelab.research import oro_0530 as X
from edgelab.funnel import escalera as ES


def _ctx(dias=260, seed=0, deriva=0.0, burst=1.0):
    """M1 sintético 24 h por día hábil: paseo aleatorio; `deriva` puntos por minuto entre 05:30 y 06:30 UTC; `burst` multiplica
    los ticks de 05:30 a 05:35."""
    rng = np.random.default_rng(seed); t, o, h, l, c, n = [], [], [], [], [], []; p = 2000.0
    d0 = pd.Timestamp("2024-01-01").value // 10**9
    for k in range(dias):
        dia = d0 + 86400 * k
        if pd.Timestamp(dia, unit="s").dayofweek >= 5: continue
        for m in range(1440):
            r = rng.normal(0, 0.3) + (deriva if X.ANCLA <= m < X.ANCLA + 60 else 0.0)
            oo = p; p = p + r; hh, ll = max(oo, p) + abs(rng.normal(0, .1)), min(oo, p) - abs(rng.normal(0, .1))
            t.append(dia + 60 * m + 60); o.append(oo); h.append(hh); l.append(ll); c.append(p)
            n.append(int(rng.poisson(20 * (burst if X.ANCLA <= m < X.ANCLA + 5 else 1.0))))
    ts = np.r_[0, np.cumsum(n)].astype(np.int64)
    return dict(t=np.array(t, np.int64), o=np.array(o), h=np.array(h), l=np.array(l), c=np.array(c), v=np.array(n, float), tstart=ts,
                ses=(np.array(t) // 86400).astype(np.int64))


def _p(D):
    return [r["p"] for r in X.evaluar(D, 0.605, 0.805, n_boot=2000)]


def test_control_ruido():
    nom = [len(ES.tamiz_fdr(_p(X.tabla(X.minutos_utc(_ctx(seed=s)))), q=0.10)["nominadas"]) for s in range(3)]
    assert sum(nom) <= 1                                        # sin efecto: el tamiz casi nunca nomina


def test_control_plantado():
    res = X.evaluar(X.tabla(X.minutos_utc(_ctx(seed=7, deriva=0.08))), 0.605, 0.805, n_boot=2000)
    nom = ES.tamiz_fdr([r["p"] for r in res], q=0.10)["nominadas"]
    assert {res[i]["celda"] for i in nom} >= {"deriva_30", "deriva_60"}
    d60 = next(r for r in res if r["celda"] == "deriva_60"); assert abs(d60["media"] - 0.08 * 60) < 1.5 and d60["neto_base"] > 0


def test_perfil_ve_el_burst_sin_mirar_precios():
    P = X.perfil(X.minutos_utc(_ctx(dias=40, burst=4.0)))
    assert P.ticks_rel.loc[X.ANCLA:X.ANCLA + 4].min() > 3 and P.ticks_rel.drop(range(X.ANCLA, X.ANCLA + 5)).max() < 1.5
    D = X.tabla(X.minutos_utc(_ctx(dias=40, burst=4.0)))
    assert D.burst_ticks.median() > 3


def test_causal_las_direcciones_no_usan_el_futuro_de_la_entrada():
    ctx = _ctx(dias=30, seed=3); D0 = X.tabla(X.minutos_utc(ctx))
    M = X.minutos_utc(ctx); tarde = (M.mdd >= X.ANCLA + 5).to_numpy()            # todo lo posterior a la entrada de «arranque»
    ctx2 = dict(ctx); ctx2["o"] = np.where(tarde, ctx["o"] + 50, ctx["o"]); ctx2["c"] = np.where(tarde, ctx["c"] - 50, ctx["c"])
    D1 = X.tabla(X.minutos_utc(ctx2))
    assert (D0.dir_arranque == D1.dir_arranque).all() and (D0.dir_previo == D1.dir_previo).all()


def test_falta_una_vela_no_se_rellena():
    ctx = _ctx(dias=10, seed=4); M = X.minutos_utc(ctx)
    quita = ((M.mdd == X.ANCLA + 15) & (M.dia == M.dia.iloc[0])).to_numpy()
    ctx2 = {k: (v[~quita] if k != "tstart" else np.r_[v[:-1][~quita], v[-1]]) for k, v in ctx.items() if k != "tick"}
    D = X.tabla(X.minutos_utc(ctx2))
    assert np.isnan(D.deriva_15.iloc[0]) and np.isfinite(D.deriva_15.iloc[1])


def _ctx_ruptura(salto):
    """Ticks sintéticos: rango [2000,1, 2000,9] hasta 05:30; desde 05:31 sube `salto` puntos por minuto (tendencia, no un hueco: un
    hueco llena al precio real después del salto y no gana nada, como debe)."""
    from edgelab.research import grilla_generica as GG
    d0 = pd.Timestamp("2025-03-04").value // 10**9; filas = []
    for m in range(4 * 60, 7 * 60):
        base = 2000.5 if m < X.ANCLA + 1 else 2000.5 + salto * (m - X.ANCLA)
        for s in (5, 25, 45):
            w = 0.4 if m <= X.ANCLA else 0.1                                    # oscilación chica después de cruzar
            px = base + (w if s == 25 else -w if s == 45 else 0.0)
            filas.append((int((d0 + 60 * m + s) * 1e9), px))
    b = pd.DataFrame(filas, columns=["ts_ns", "px"]).assign(vol=1.0, sesion=20250304, segmento=0)
    return GG.contexto_m1([b], tick=0.1)


def test_ruptura_niveles_del_rango_previo_y_cobra_la_expansion():
    R = X.ruptura(_ctx_ruptura(+0.5))
    assert len(R) == len(X.RUPTURA_HOLDS) * len(X.RUPTURA_STOPS) and R.entro.all() and (R.lado == 1).all()
    assert (R.bruto > 5).all() and np.allclose(R.rango, 0.8)                 # entra arriba del máximo previo y cobra la tendencia
    R0 = X.ruptura(_ctx_ruptura(0.0))
    assert not R0.entro.any()                                                 # sin salir del rango no hay operación
    Rb = X.ruptura(_ctx_ruptura(-0.5)); assert (Rb.lado == -1).all() and (Rb.bruto > 5).all()   # simétrico: el lado lo elige el mercado
