"""LUXIMB-AMARILLA: la secuencia ruptura → excursión → regreso marca los tres puntos en orden y se invalida bien."""
import numpy as np

from edgelab.research import luximb_amarilla as A


def _arr(*x):
    return np.array(x, float)


def test_secuencia_tres_puntos():
    # impulso alcista: caja [100, 110] (borde externo 110, interno 100), H_am = 10, e = 1 → excursión >= 10
    c = _arr(105, 112, 125, 120, 115, 108, 99); h = c + 0.5; l = c - 0.5
    ks, xs = A._secuencia_nb(h, l, c, 0, len(c), 1, 100.0, 110.0, 10.0, 1.0)
    # rompe en 1, extremo 125,5 en 2 (A 15,5 >= 10); ANTES cuando cierra <= 125,5 − 6,2 = 119,3 → vela 4 (115); EN_CAJA en 5 (108); DESPUES en 6 (99)
    assert ks.tolist() == [4, 5, 6] and xs[0] == 125.5


def test_invalidada_si_vuelve_por_dentro_antes_de_armarse():
    c = _arr(105, 112, 113, 99, 130); h = c + 0.5; l = c - 0.5
    ks, _ = A._secuencia_nb(h, l, c, 0, len(c), 1, 100.0, 110.0, 10.0, 1.0)
    assert (ks < 0).all()


def test_contrato_en_sintetico():
    from edgelab.research import grilla_generica as GG, sintetico
    E = A.eventos(GG.contexto_m1(list(sintetico.bloques(dias=60, planta=False, seed=11)), tick=0.25))
    assert len(E) and all(d in E for d in A.DEFINICIONES)
    v = E[E.lado == -1]                                                    # venta: objetivos abajo, stops arriba del extremo
    assert (v.obj_0 <= v.obj_50).all() and (v.stop_ext25 >= v.stop_ext).all()
