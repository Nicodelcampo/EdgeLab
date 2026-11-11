"""LUXIMB-HVN: simulador tick a tick (E0 con parcial/BE, EXT), perfil de volumen más allá de B y causalidad por prefijo."""
import numpy as np
import pandas as pd

from edgelab.research import grilla_generica as GG, luximb_hvn as H, sintetico


def _p(*xs):
    return np.array(xs, float)


def test_e0_objetivo_stop_parcial_y_be():
    # impulso alcista (d=1) con A = 90; entrada (venta) en 100: D = 10; stop 0,2·D = 2, objetivo 1,0·D = 10
    tpx = _p(100, 99, 95, 90.5, 90)
    assert H._e0_nb(tpx, 0, len(tpx), 1, 90.0, 0.2, 1.0, 0.0, 0.0) == 5.0                 # objetivo: 10 / 2
    tpx = _p(100, 101, 103)
    assert H._e0_nb(tpx, 0, len(tpx), 1, 90.0, 0.2, 1.0, 0.0, 0.0) == -1.5                # stop a mercado: sale en 103 (−3 / 2)
    tpx = _p(100, 97.5, 101, 103)                                                          # parcial 50 % a 0,25·D = 2,5 y después stop
    assert np.isclose(H._e0_nb(tpx, 0, len(tpx), 1, 90.0, 0.2, 1.0, 0.25, 0.0), (0.5 * 2.5 + 0.5 * -3) / 2)
    tpx = _p(100, 97.5, 100, 103)                                                          # BE a 0,25·D: vuelve a la entrada → 0
    assert H._e0_nb(tpx, 0, len(tpx), 1, 90.0, 0.2, 1.0, 0.0, 0.25) == 0.0
    tpx = _p(100, 97.5, 100.25)                                                            # parcial + BE: medio cobrado, medio a ~0
    assert np.isclose(H._e0_nb(tpx, 0, len(tpx), 1, 90.0, 0.2, 1.0, 0.25, 0.25), (0.5 * 2.5 + 0.5 * -0.25) / 2)
    assert np.isnan(H._e0_nb(_p(89, 88), 0, 2, 1, 90.0, 0.2, 1.0, 0.0, 0.0))             # entrada ya pasada de A: D <= 0


def test_ext_espera_extension_y_vuelta():
    # impulso alcista A = 0, B = 100 (rango 100); e = 0,1 → extensión a 110; r = 0,05 → entra al volver a 105; stop 0,05 más allá
    ts = np.array([0, 10], np.int64); fin = np.array([1], np.int64)
    tpx = _p(101, 106, 110, 108, 105, 80, 50)
    R, k = H._ext_nb(tpx, ts, fin, 0, len(tpx), 1, 0.0, 100.0, 100.0, 0.1, 0.05, 0.05, 1, 0.5)
    assert k == 10.0 and R == 5.5                                          # venta en 105, stop 115, objetivo la mitad (50): 55 / 10
    R, _ = H._ext_nb(_p(101, 106, 111, 160), ts, fin, 0, 4, 1, 0.0, 100.0, 100.0, 0.1, 0.05, 0.05, 1, 0.5)
    assert np.isnan(R)                                                     # se pasó de c = 0,5 (150) antes de volver: cancelada
    R, _ = H._ext_nb(_p(101, 104, 102, 99), ts, fin, 0, 4, 1, 0.0, 100.0, 100.0, 0.1, 0.05, 0.05, 1, 0.5)
    assert np.isnan(R)                                                     # nunca llegó a extenderse 0,1: sin entrada


def test_hvn_franjas():
    # una vela de perfil antes del impulso; impulso bajista (d = −1) con B = 100 y rango 20: franja más allá = [90, 100]
    vps = np.array([0, 4, 4], np.int64); vpx = _p(95, 92, 105, 85); vvo = _p(10, 10, 4, 5)
    r, cen = H._hvn_nb(np.array([1]), np.array([1]), np.array([0]), np.array([-1]), _p(100), _p(20), vps, vpx, vvo, 10)
    assert r[0] == 20 / 5 and np.isclose(cen[0], (10 * 0.5 + 10 * 0.8) / 20)


def test_causal_por_prefijo():
    """Los rasgos de un evento no cambian si se corta la serie después de su vela de marca."""
    bl = list(sintetico.bloques(dias=24, planta=False, seed=11))
    full = GG.contexto_m1(bl, tick=0.25); corto = GG.contexto_m1(bl[:16], tick=0.25)
    Ef, Ec = H.eventos(full), H.eventos(corto)
    corte = len(corto["c"]) - 1
    rasgos = ["k", "d", "i0", "pa", "ext", "rg", "nz", "nini25", "hvn_240", "hvn_1440"] + [c for c in Ef.columns if c.startswith("D")]
    a = Ef[Ef.k < corte][rasgos].reset_index(drop=True); b = Ec[Ec.k < corte][rasgos].reset_index(drop=True)
    assert len(a) > 20
    pd.testing.assert_frame_equal(a, b)


def test_tabla_completa_y_nombres():
    ctx = GG.contexto_m1(sintetico.bloques(dias=12, planta=False, seed=3), tick=0.25)
    T = H.tabla(ctx)
    assert len(T) and H.VISOR in T.columns
    for x in H.E0: assert f"r_{H.nombre_e0(x)}" in T and f"k_{H.nombre_e0(x)}" in T
    for x in H.EXT: assert f"r_{H.nombre_ext(x)}" in T
    assert len({H.nombre_e0(x) for x in H.E0}) == len(H.E0) and len({H.nombre_ext(x) for x in H.EXT}) == len(H.EXT)
