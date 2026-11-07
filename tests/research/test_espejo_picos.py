"""ESPEJO-PICOS: picos vivos tomados por la ida (cantidad, posición, sobrepaso), los que quedan, causalidad y objetivos más allá de A."""
import numpy as np

from edgelab.research import espejo_picos as X, grilla_generica as GG, indicadores as I, preflight as PF, sintetico


def test_clasificar_picos_tomados_y_que_quedan():
    # techo: escalera de picos vivos 110, 108, 106 antes de A (índice 20); la ida sube de 100 a 109 -> toma 106 y 108, queda 110
    x = np.full(40, 100.0)
    for q, v in ((4, 110.0), (9, 108.0), (14, 106.0)): x[q] = v
    x[20:30] = np.linspace(100, 109, 10)
    piv = np.zeros(40, bool); piv[[4, 9, 14]] = True
    n_t, pos, sob, n_q, techo = X._clasificar(x, piv, 2, 20, 29, 100.0, 2000, 60, False)
    assert (n_t, n_q, techo) == (2, 1, 109.0)
    assert abs(pos - ((6 / 9 + 8 / 9) / 2)) < 1e-9 and abs(sob - 1 / 9) < 1e-9
    assert X._clasificar(x, piv, 2, 20, 29, 100.0, 2000, 3, True)[0] == 0          # separación > 3: no forman serie


def test_causal_estatico_y_niveles():
    assert PF.estatico(X) == []
    ctx = GG.contexto_m1(sintetico.bloques(dias=10, planta=False, seed=5), tick=0.25, ticks_por_barra=10)
    assert I.causal(X.disparos, ctx) == []
    c = dict(c=np.array([20060.0, 20059.0]), ses=np.zeros(2, np.int64), tick=0.25)
    r = dict(k=0, lado=-1, A=20000.0, B=20120.0, W=120.0)
    assert X.niveles(r, ("B1", "A150"), c)[5] == 19940.0                              # 1,5·W desde B: 30 pts más allá de A
