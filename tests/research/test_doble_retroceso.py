"""DOBLE-RETROCESO: barras de ticks, geometría de las 5 piernas, causalidad y niveles."""
import numpy as np

from edgelab.research import doble_retroceso as X, grilla_generica as GG, sintetico


def _ctx(dias=40, seed=11):
    return GG.contexto_m1(sintetico.bloques(dias=dias, planta=False, seed=seed), tick=0.25)


def test_barras_ticks_por_sesion_y_vela_m1():
    ctx = _ctx(10)
    o, h, l, c, s, m = X.barras_ticks(np.asarray(ctx["tpx"], float), np.asarray(ctx["tstart"], np.int64), np.asarray(ctx["ses"], np.int64), 100)
    assert len(c) > 0 and (h >= np.maximum(o, c)).all() and (l <= np.minimum(o, c)).all()
    assert (np.diff(m) >= 0).all() and (np.asarray(ctx["ses"])[m] == s).all()       # la vela M1 es de la misma sesión y no retrocede


def test_geometria_de_las_5_piernas():
    D = X.disparos(_ctx())
    assert len(D) > 0
    s = D.lado.to_numpy()
    assert ((D.p4 - D.p2) * s > 0).all()                     # P4 no toma P2
    assert (D.pasa_p1_atr > 0).all() and (D.cerca_p2_atr > 0).all()
    assert (D.imp1_atr >= X.IMP1_MIN - 1e-9).all()
    assert not D.duplicated(["k", "res", "modo", "lado"]).any()


def test_causal_truncar_no_cambia_lo_ya_decidido():
    ctx = _ctx(30, seed=5); D = X.disparos(ctx)
    corte = int(len(ctx["c"]) * 0.6)
    sub = {k: (v[:corte] if hasattr(v, "__len__") and len(v) == len(ctx["c"]) else v) for k, v in ctx.items()}
    sub["tstart"] = np.asarray(ctx["tstart"])[:corte + 1]; sub["tpx"] = np.asarray(ctx["tpx"])[:int(sub["tstart"][-1])]
    P = X.disparos(sub)
    cols = ["k", "lado", "modo", "res"]
    a = D[D.k < corte - 1][cols].astype(int).sort_values(cols).reset_index(drop=True)
    b = P[P.k < corte - 1][cols].astype(int).sort_values(cols).reset_index(drop=True)
    assert a.equals(b)


def test_niveles_stop_detras_de_p2():
    ctx = dict(c=np.array([100.0]), tick=0.25)
    r = dict(lado=-1, k=0, p2=103.0, p4=102.0, imp1=10.0, atr=2.0)
    k, lim, s, e, st, tp, be, kl, dl = X.niveles(r, ("P2", "2R"), ctx)
    assert (s, st, kl) == (-1, 103.25, 1) and abs(tp - (100 - 2 * 3.25)) < 1e-9
    assert X.niveles(r, ("P2_ATR", "MM"), ctx)[4] == 103.75 and X.niveles(r, ("P2", "MM"), ctx)[5] == 92.0
