"""ESPEJO-ZONAS: zonas vivas tomadas por la ida (cantidad, posición), antigüedad, nacidas en la ida, las de más allá y causalidad."""
import numpy as np

from edgelab.research import espejo_zonas as X, grilla_generica as GG, indicadores as I, preflight as PF, sintetico


def _ref_cruce(c, zi, u, arriba):
    out = []
    for z in range(len(zi)):
        r = len(c)
        for j in range(zi[z] + 1, len(c)):
            if (c[j] > u[z]) if arriba else (c[j] < u[z]): r = j; break
        out.append(r)
    return out


def test_primer_cruce_contra_fuerza_bruta():
    rng = np.random.default_rng(3)
    for _ in range(200):
        n = int(rng.integers(1, 50)); c = rng.normal(size=n).round(1); nz = int(rng.integers(0, 20))
        zi = rng.integers(0, n, nz); u = rng.normal(size=nz).round(1)
        for arriba in (True, False):
            assert list(X._primer_cruce(c, zi, u, arriba)) == _ref_cruce(c, zi, u, arriba)


def test_clasificar_bandas_vida_y_mas_alla():
    # A = 100 en la vela 20 (t = 1200 s), ida hasta la 29 con techo 110 (W = 10). Zonas (espacio techo):
    #  z0 [103,104] creada en 2 (18 min antes): vieja con corte de 10 min, viva -> tomada, pos 0,35
    #  z1 [108,109] creada en 15 (5 min antes): reciente, viva -> tomada, pos 0,85
    #  z2 [105,106] creada en 5 pero cruzada en 8 -> no cuenta
    #  z3 [111,112] creada en 10, viva, a 1 de techo (<= 0,25·W) -> más allá cercana
    #  z4 [107,107.5] nacida en la ida (vela 24) -> tomada sólo en las bandas «ida» y «todas»
    #  z5 [95,96] debajo de A -> nunca cuenta
    zi = np.array([2, 5, 10, 15, 24, 3]); near = np.array([103., 105, 111, 108, 107, 95]); far = np.array([104., 106, 112, 109, 107.5, 96])
    cruce = np.array([99, 8, 99, 99, 99, 99]); tz = zi * 60.0; sz = np.zeros(6, np.int64)
    o = np.argsort(zi, kind="stable"); zi, near, far, cruce, tz = zi[o], near[o], far[o], cruce[o], tz[o]
    def cl(banda): return X._clasificar(zi, near, far, cruce, tz, sz, 20, 29, 0, 100.0, 110.0, 0, 1200.0, banda, 600.0, 0.25)
    n, pos, m = cl(0); assert (n, m) == (1, 1) and abs(pos - 0.85) < 1e-9      # recientes: z1 (y z3, de 10 min, cuenta como reciente)
    n, pos, m = cl(1); assert (n, m) == (1, 0) and abs(pos - 0.35) < 1e-9      # viejas: z0
    n, pos, m = cl(2); assert (n, m) == (1, 0) and abs(pos - 0.725) < 1e-9     # nacidas en la ida: z4
    n, pos, m = cl(3); assert (n, m) == (3, 1)                                 # todas: z0, z1, z4 tomadas; z3 más allá


def test_causal_estatico_y_disparos():
    assert PF.estatico(X) == []
    ctx = GG.contexto_m1(sintetico.bloques(dias=10, planta=False, seed=5), tick=0.25, ticks_por_barra=10)
    D = X.disparos(ctx)
    assert len(D) and set(D.ai) == {0, 1, 2, 3} and set(D.zi_ind) == {0, 1}
    assert I.causal(X.disparos, ctx) == []
