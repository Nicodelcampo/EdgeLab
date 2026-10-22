"""AREAS-EXP-1: el motor contra casos de resultado conocido (sin datos de mercado)."""
import itertools

import numpy as np
import pytest

from edgelab.research import areas_expansion as AX


def _Z(zs, n, t_close):
    zi = np.array([z[0] for z in zs]); lo = np.array([z[1] for z in zs], float); hi = np.array([z[2] for z in zs], float)
    return dict(zi=zi, zlo=lo, zhi=hi, zfin=np.searchsorted(t_close, t_close[zi] + AX.VIDA_MIN * 60, side="right"), og=np.zeros(len(zi), bool))


def test_area_se_marca_una_vez_y_dos_pegadas_cuentan_una():
    n = 200; t = np.arange(n) * 60 + 60
    zs = [(10, 100, 101), (11, 101, 102), (12, 102, 103),          # grupo 1: 3 zonas pegadas -> área a la barra 12
          (13, 103.5, 104),                                          # crece pegada (G=1): no se vuelve a marcar
          (20, 200, 201), (21, 200.5, 201.5), (22, 201, 202)]        # otra área lejos -> sí
    ev = AX.eventos(_Z(zs, n, t), t, G=1.0, ns=(3,), ws=(10.0,))
    assert [(e[0], e[1], e[2]) for e in ev[(3, 10.0)]] == [(12, 100.0, 103.0), (22, 200.0, 202.0)]
    ev2 = AX.eventos(_Z(zs, n, t), t, G=1.0, ns=(3,), ws=(1.5,))                   # banda de 1,5: ninguna banda junta 3 zonas
    assert ev2[(3, 1.5)] == []


def test_disparo_por_acercamiento_y_descarte_si_vuelve_antes_de_alejarse():
    n = 60; t = np.arange(n) * 60 + 60
    c = np.r_[np.full(11, 101.0), 104, 106, 108, 110, 109, 107, 105, 103.5, np.full(n - 19, 103.5)]
    h, l = c + 0.25, c - 0.25
    ev = (10, 100.0, 102.0, np.array([0]))                       # H = 2
    d = {x["xi"]: x for x in AX.disparos(ev, h, l, c, t)}
    # extremo 110.25 -> A = 8.25; x=0,75: D <= 6,19 -> cierre 107 (D=5) en la barra 16; x=0,5: D<=4,13 -> 105 (D=3) barra 17
    assert d[0]["k"] == 16 and d[1]["k"] == 17 and d[0]["lado"] == 1 and d[0]["E"] == pytest.approx(110.25)
    c2 = np.r_[np.full(11, 101.0), 102.5, 101.0, np.full(n - 13, 101.0)]           # sale, vuelve antes de 1·H y no se aleja más
    assert AX.disparos(ev, c2 + .25, c2 - .25, c2, t) == []
    # varios ciclos sobre la MISMA área: arriba y vuelve, abajo y vuelve (atravesarla no la invalida)
    c3 = np.r_[np.full(11, 101.0), 105, 108, 104, 101.0, 97, 94, 98, 101.0, np.full(n - 19, 101.0)]
    d3 = AX.disparos(ev, c3 + .25, c3 - .25, c3, t)
    assert sorted({(x["ciclo"], x["lado"]) for x in d3}) == [(0, 1), (1, -1)]


def _sim(start, s, lim, nivel, st, tp, be, o, h, l, c, ses, tpx=None, tstart=None):
    a = lambda v, dt=float: np.array([v], dt)
    if tpx is None: tpx, tstart = np.zeros(0), np.zeros(len(c) + 1, np.int64)        # sin ticks
    pnl, amb = AX.simular(a(start, np.int64), a(s, np.int64), a(lim, np.int64), a(nivel), a(st), a(tp), a(be, np.int64), o, h, l, c, ses, 1.0, tpx, tstart)
    return pnl[0]


def test_simulador_tp_stop_con_hueco_be_limite_y_sesion():
    n = 30; ses = np.zeros(n, np.int64)
    c = np.full(n, 100.0); o = c.copy(); h = c + 1; l = c - 1
    h[5] = 106                                                                     # compra a 100 (cierre barra 2), TP 105 -> +5
    assert _sim(2, 1, 0, 0, 95, 105, 0, o, h, l, c, ses) == 5
    o2, l2 = o.copy(), l.copy(); o2[4] = 90; l2[4] = 89                            # stop 95 con hueco: se llena al open 90
    assert _sim(2, 1, 0, 0, 95, 105, 0, o2, h, l2, c, ses) == -10
    h3, l3 = h.copy(), l.copy(); h3[4] = 106 - 1; l3[6] = 98                       # +5 = 1R (stop 95) arma BE; luego cae a 98 <= 100
    assert _sim(2, 1, 0, 0, 95, 110, 1, o, h3, l3, c, ses) == 0
    assert np.isnan(_sim(2, -1, 1, 103, 108, 95, 0, o, c + 1, l, c, ses))          # venta límite 103: el máximo (101) nunca la atraviesa
    ses2 = ses.copy(); ses2[10:] = 1; c4 = c.copy(); c4[9] = 102                   # sin SL/TP: sale al cierre de la última barra de la sesión
    assert _sim(2, 1, 0, 0, 90, 120, 0, o, h, l, c4, ses2) == 2


def test_tensor_acumulado_igual_a_fuerza_bruta():
    rng = np.random.default_rng(3); T = 4000
    ni, xi = rng.integers(0, 3, T), rng.integers(0, 3, T); ei = rng.integers(0, len(AX.EJEC), T)
    ab, cb, pb, vb = rng.integers(0, len(AX.A_CORTES), T), rng.integers(0, 4, T), rng.integers(0, 3, T), rng.integers(0, 3, T)
    net = rng.normal(0, 1, T)
    S, Q, C = AX.tensor_celdas(ni, xi, ei, ab, cb, pb, vb, net)
    assert S.shape == (3, 3, len(AX.EJEC), len(AX.A_CORTES), 4, 4, 3)
    for (n_, x_, e_, a_, c_, p_, v_) in [(0, 1, 5, 0, 3, 3, 2), (2, 0, 100, 2, 0, 1, 0), (1, 2, 7, 1, 1, 3, 1)]:
        m = (ni == n_) & (xi == x_) & (ei == e_) & (ab >= a_) & (cb <= c_) & ((pb == p_) if p_ < 3 else True) & \
            ((vb == {0: 0, 1: 2}[v_]) if v_ < 2 else True)
        assert C[n_, x_, e_, a_, c_, p_, v_] == m.sum() and S[n_, x_, e_, a_, c_, p_, v_] == pytest.approx(net[m].sum())


def test_niveles_hacia_y_rebote():
    d = dict(m=0, k=5, lado=1, lo=100.0, hi=102.0, H=2.0, E=110.0, A=8.0, D=3.0)
    c = np.full(10, 105.0)
    lim, s, e, st, tp, be = AX.niveles(d, ("HACIA", "T2", "E1C", "S2", 0), np.nan, 0.25, c)
    assert (lim, s, e, tp, st) == (0, -1, 105.0, 101.0, 109.0)                    # venta hacia el área, TP al 50 %, stop a 1x
    assert AX.niveles(d, ("HACIA", "T1", "E3", "S1", 0), np.nan, 0.25, c) is None  # E3 no aplica a HACIA
    lim, s, e, st, tp, be = AX.niveles(d, ("REBOTE", "2R", "E3", "S1", 1), np.nan, 0.25, c)
    assert (lim, s, e, st, tp, be) == (1, 1, 102.0, 101.0, 104.0, 1)              # compra límite en el borde, stop 0,5·H, 2R


def test_ambiguedad_m1_se_resuelve_con_el_orden_de_los_ticks():
    """Vela 4 toca stop (95) y objetivo (105). Los ticks dicen cuál fue primero; sin ticks se toma el stop."""
    n = 10; ses = np.zeros(n, np.int64); c = np.full(n, 100.0); o = c.copy(); h = c + 1; l = c - 1
    h[4], l[4] = 107, 94
    ticks = {4: [100, 103, 106.5, 94]}                                                # primero atraviesa el TP
    def csr(tk):
        px, st = [], [0]
        for j in range(n): px += tk.get(j, [c[j]]); st.append(len(px))
        return np.array(px, float), np.array(st, np.int64)
    assert _sim(2, 1, 0, 0, 95, 105, 0, o, h, l, c, ses, *csr(ticks)) == 5
    assert _sim(2, 1, 0, 0, 95, 105, 0, o, h, l, c, ses, *csr({4: [100, 96, 94.5, 107]})) == -5.5   # primero el stop; salta 95 y se llena en el tick real 94,5
    assert _sim(2, 1, 0, 0, 95, 105, 0, o, h, l, c, ses) == -5                                   # sin ticks: stop


def _eventos_oraculo(Z, t_close, G, ns, ws):
    """Implementación de referencia en Python puro (la regla tal como está escrita en la spec)."""
    out = {(n_, w_): [] for n_ in ns for w_ in ws}; marcas = {k: [] for k in out}
    for m in np.unique(Z["zi"]):
        viva = np.flatnonzero((Z["zi"] <= m) & (Z["zfin"] > m))
        if len(viva) < min(ns): continue
        o = viva[np.argsort(Z["zlo"][viva], kind="stable")]; lo_v, hi_v, nueva = Z["zlo"][o], Z["zhi"][o], Z["zi"][o] == m
        for w_ in ws:
            M = (lo_v[None, :] >= lo_v[:, None]) & (hi_v[None, :] <= lo_v[:, None] + w_)
            cnt = M.sum(1); cands = np.flatnonzero((cnt >= min(ns)) & (M & nueva[None, :]).any(1))
            if not len(cands): continue
            alto = np.array([hi_v[M[i]].max() for i in cands])
            cands = cands[np.lexsort((alto - lo_v[cands], -cnt[cands]))]; usadas = []
            for i in cands:
                lo_, hi_ = float(lo_v[i]), float(hi_v[M[i]].max())
                if any(lo_ <= h2 and hi_ >= l2 for l2, h2 in usadas): continue
                usadas.append((lo_, hi_))
                for n_ in ns:
                    if cnt[i] < n_: continue
                    if any(t_close[m] - tm <= AX.VIDA_MIN * 60 and lo_ <= h_ + G and hi_ >= l_ - G for tm, l_, h_ in marcas[(n_, w_)]): continue
                    marcas[(n_, w_)].append((t_close[m], lo_, hi_)); out[(n_, w_)].append((int(m), lo_, hi_, sorted(o[M[i]].tolist())))
    return out


@pytest.mark.parametrize("seed", [0, 1, 2, 3])
def test_eventos_compilado_igual_al_oraculo(seed):
    rng = np.random.default_rng(seed); n = 3000; t = np.arange(n) * 60 + 60; K = 600
    zi = np.sort(rng.integers(3, n, K)); lo = np.round(rng.normal(100, 8, K) * 4) / 4; hi = lo + rng.choice([0.25, 0.5, 1, 2, 4], K)
    Z = _Z(list(zip(zi, lo, hi)), n, t)
    a = AX.eventos(Z, t, 1.0, ns=(3, 5), ws=(2.0, 6.0)); b = _eventos_oraculo(Z, t, 1.0, (3, 5), (2.0, 6.0))
    for k in b:
        assert [(e[0], e[1], e[2], sorted(e[3].tolist())) for e in a[k]] == b[k], k


def test_empates_de_ancho_casi_exactos_se_ordenan_igual_que_el_oraculo():
    """Bug real (2026-10-22): dos bandas con la misma cantidad de zonas y anchos que difieren en milésimas; una clave
    combinada -cnt*1e12 + ancho perdía la precisión del ancho y elegía otra banda."""
    n = 100; t = np.arange(n) * 60 + 60
    zs = [(50, 24870.37, 24871.0), (50, 24871.76, 24873.0), (50, 24873.5, 24875.23), (50, 24875.6, 24876.62)]
    Z = _Z(zs, n, t)
    a = AX.eventos(Z, t, 0.0, ns=(3,), ws=(4.87,)); b = _eventos_oraculo(Z, t, 0.0, (3,), (4.87,))
    assert [(e[0], e[1], e[2], sorted(e[3].tolist())) for e in a[(3, 4.87)]] == b[(3, 4.87)]


def test_momento_de_entrada_es_un_parametro_declarado():
    """E1C llena al cierre de la vela de decisión; E1A en el primer tick de la siguiente (con hueco, al precio del hueco).
    Ninguno es el «correcto» por defecto: cada análisis lo declara (Nico, 2026-10-22)."""
    n = 12; ses = np.zeros(n, np.int64); c = np.full(n, 100.0); o = c.copy(); h = c + 1; l = c - 1
    o[3] = 102; h[3] = 103; l[3] = 101.5; c[3] = 102; h[6] = 110                     # la vela siguiente abre con hueco a 102
    assert _sim(2, 1, 0, 0, 90, 108, 0, o, h, l, c, ses) == 8                        # E1C: compra a 100, TP 108
    assert _sim(2, 1, 2, 0, 90, 108, 0, o, h, l, c, ses) == 6                        # E1A: compra a 102 (open siguiente)
    ses2 = ses.copy(); ses2[3:] = 1
    assert np.isnan(_sim(2, 1, 2, 0, 90, 108, 0, o, h, l, c, ses2))                  # E1A no cruza de sesión


def test_v_rel_sin_dato_no_cae_en_ningun_tercio():
    ab, cb, pb, vb = AX.bins_variables(np.array([2.0, 2.0]), np.array([1.0, 1.0]), np.array([0.5, 0.5]), np.array([np.nan, 0.01]), [0.04, 0.13], (1, 2, 3))
    assert vb.tolist() == [-1, 0]
