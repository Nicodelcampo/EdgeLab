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
