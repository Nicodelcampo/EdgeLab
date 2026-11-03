"""INTENTO-FALLIDO (idea de Nico, 2026-11-03): geometría del intento, vías A y B, y causalidad (truncar el futuro no cambia el pasado)."""
import numpy as np
import pandas as pd

from edgelab.research import intento_fallido as IF


def _camino(precios):
    c = np.array(precios, float); h = c + 0.1; l = c - 0.1
    return h, l, c, np.zeros(len(c), np.int64)


def _corre(precios, T=100.0, A=10.0, d=1):
    h, l, c, ses = _camino(precios)
    return IF._intentos(np.array([0]), np.array([d]), np.array([T]), np.array([A]), h, l, c, ses,
                        np.array([0.10]), np.array([0.20]), np.array([0.5]), 50)


def test_toca_el_objetivo_no_hay_intento():
    # baja desde 110 hasta tocar 100 (el borde): U1 cumplió, no hay intento fallido
    assert _corre([110, 106, 103, 100.05, 99.5, 104]) == []


def test_via_a_y_via_b():
    # se acerca a 100.9 (best = 0.8 <= y=1.0), rebota +2 (z=2.0) al cierre -> A (hacia y a favor del rechazo); luego recupera la mitad -> B
    F = _corre([110, 106, 103, 101.0, 102.0, 103.0, 101.8, 104])
    reglas = [(f[3], f[4]) for f in F]
    assert (0, 5) in reglas and (1, 5) in reglas                  # A al cierre de la vela 5 (103 - 100 - 0.9 >= 2.0)
    assert (2, 6) in reglas and (4, 6) in reglas                  # B50: vuelve a <= 3.0 - 0.5*(3.0 - 0.9) = 1.95 -> 101.8
    a_rech = [f for f in F if f[3] == 1][0]; a_hacia = [f for f in F if f[3] == 0][0]
    assert abs(a_rech[5] - 100.9) < 1e-9                          # a favor del rechazo: stop detrás del intento
    assert abs(a_hacia[5] - 103.1) < 1e-9                         # hacia la zona: stop detrás del extremo del rechazo


def test_sin_acercarse_a_y_no_hay_evento():
    assert _corre([110, 106, 104, 106, 108, 110]) == []           # nunca llegó a 1.0 del objetivo


def test_lado_contrario_simetrico():
    F = _corre([90, 94, 97, 99.0, 98.0, 97.0], T=100.0, d=-1)    # precio abajo, objetivo = borde inferior 100
    assert any(f[3] == 0 and f[4] == 5 for f in F)


def test_causal_truncar_el_futuro_no_cambia_lo_ya_decidido():
    rng = np.random.default_rng(5); px = 110 + np.cumsum(rng.normal(0, 0.6, 400))
    h, l, c, ses = _camino(px)
    args = (np.array([0]), np.array([1]), np.array([px.min() - 1.0]), np.array([15.0]))
    full = IF._intentos(*args, h, l, c, ses, np.array(IF.YS), np.array(IF.ZS), np.array(IF.RS), 240)
    for corte in (60, 150, 300):
        part = IF._intentos(*args, h[:corte], l[:corte], c[:corte], ses[:corte], np.array(IF.YS), np.array(IF.ZS), np.array(IF.RS), 240)
        assert sorted(f for f in full if f[4] < corte) == sorted(part)


def test_niveles_stop_estructural_y_objetivos():
    ctx = dict(c=np.array([103.0]), tick=0.25)
    # a favor del rechazo (largo, precio arriba de la zona 95-100, origen E = 110)
    r = dict(lado=1, k=0, regla=1, stop_ref=100.9, zA=2.0, T=100.0, mid=97.5, lejos_zona=95.0, E=110.0)
    k, lim, s, e, st, tp, be, kl, dl = IF.niveles(r, ("2R", 0.0), ctx)
    assert (s, st, kl) == (1, 100.5, 0) and abs(tp - (103 + 2 * 2.5)) < 1e-9
    assert IF.niveles(r, ("2R", 0.5), ctx)[4] == 99.5                       # colchón 0,5·z = 1.0 más allá
    assert IF.niveles(r, ("Z3", 0.0), ctx)[5] == 110.0                     # todo el camino de vuelta al origen
    assert IF.niveles(dict(r, stop_ref=104.0), ("2R", 0.0), ctx) is None   # stop del lado equivocado: no se opera
    # hacia la zona (corto): Z1 borde cercano, Z2 medio, Z3 borde lejano
    h = dict(r, lado=-1, regla=0, stop_ref=103.1)
    assert [IF.niveles(h, (z, 0.0), ctx)[5] for z in ("Z1", "Z2", "Z3")] == [100.0, 97.5, 95.0]
    assert IF.niveles(h, ("Z1", 0.0), ctx)[4] == 103.5 and IF.niveles(h, ("Z1", 0.0), ctx)[7] == 1


def test_lineas_de_noticias_valen_con_ejecucion_cruzada():
    """La única línea es de tiempo (±inf): la simulación con señal en un instrumento y ejecución en otro no la rechaza."""
    from edgelab.research import grilla_generica as GG, intento_fallido_lux as X, sintetico
    assert X.LINEAS_SOLO_TIEMPO
    ctx = GG.contexto_m1(sintetico.bloques(dias=3, planta=False, seed=1), tick=0.25)
    lin = X.lineas_salida(ctx)
    assert not np.isfinite(lin).any()
