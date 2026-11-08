"""ESPEJO-PICOS2: cuatro definiciones de pico (zigzag, iguales, mecha, horario), clasificación por banda de antigüedad y causalidad."""
import numpy as np

from edgelab.research import espejo_picos2 as X, grilla_generica as GG, indicadores as I, preflight as PF, sintetico


def test_zigzag_confirma_en_la_reversion():
    x = np.array([0, 1, 2, 5, 4, 3, 1, 2, 3, 6, 5, 2.]); ses = np.zeros(12, np.int64)
    q, cf, v = X._zigzag(x, x - 0.5, ses, 2.5)
    assert q.tolist() == [3, 9] and cf.tolist() == [5, 11] and v.tolist() == [5.0, 6.0]
    ses2 = np.r_[np.zeros(4, np.int64), np.ones(8, np.int64)]          # la sesión corta después del 5: no se confirma con la siguiente
    assert X._zigzag(x, x - 0.5, ses2, 2.5)[0].tolist() == [4, 9]       # la nueva sesión arranca su propio techo en 4


def test_iguales_mecha_horario():
    x = np.array([0, 3, 0, 0, 3.2, 0, 0, 9, 0, 0, 3.1, 0, 0.]); ses = np.zeros(13, np.int64)
    piv = np.zeros(13, bool); piv[[1, 4, 7, 10]] = True
    q, cf, v = X._iguales(x, ses, piv, 1, 0.25, 50)
    assert q.tolist() == [4] and v.tolist() == [3.2]                     # 10 no: entre 4 y 10 el 9 pasó a los dos
    cuerpo = np.array([0, 1, 0, 0, 3.0, 0, 0, 2, 0, 0, 3.0, 0, 0]); rango = np.full(13, 4.0)
    assert X._mecha(x, ses, piv, 1, cuerpo, rango, 0.40)[0].tolist() == [1, 7]
    T = np.arange(13) * 300.0                                            # velas de 5 min, ventanas de 15 min (3 velas)
    q, cf, v = X._horario(x, T, ses, 900.0)
    assert q.tolist() == [1, 4, 7, 10] and cf.tolist() == [3, 6, 9, 12]  # la última ventana (12) no cerró


def test_clasificar_bandas():
    # A = 100 en i0 = 20 (t = 1200 s), techo 110. Picos: 104 (min 2), 108 (min 15), 112 (min 10, queda), 106 roto en 12 (no cuenta)
    q = np.array([2, 5, 10, 15]); cf = q + 1; v = np.array([104., 106, 112, 108]); brk = np.array([99, 12, 99, 99])
    T = np.arange(40) * 60.0; ses = np.zeros(40, np.int64)
    R = X._clasificar(q, cf, v, brk, ses, T, 20, 29, 100.0, 110.0, 400.0, 800.0)
    assert R[0].tolist() == [1, 0.8, 0.2, 0]                             # <= 400 s: 108
    assert R[1].tolist() == [0, -1, -1, 1]                               # 400–800 s: 112 queda
    assert R[2][0] == 1 and abs(R[2][1] - 0.4) < 1e-9                    # > 800 s: 104
    assert R[3][0] == 2 and R[3][3] == 1 and abs(R[3][2] - 0.2) < 1e-9   # todos


def test_causal_estatico():
    assert PF.estatico(X) == []
    ctx = GG.contexto_m1(sintetico.bloques(dias=10, planta=False, seed=5), tick=0.25, ticks_por_barra=10)
    D = X.disparos(ctx)
    assert len(D) and set(D.ti) == {0, 1, 2, 3} and set(D.ai) == {0, 1, 2, 3}
    assert I.causal(X.disparos, ctx) == []
