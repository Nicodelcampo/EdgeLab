"""ESPEJO-MACRO-10T-ANCHO: con el ancho mínimo en 5 viajes aparecen al menos los mismos disparos que con 10, y sigue causal."""
from edgelab.research import espejo_macro_ancho as X, espejo_macro_tiempo as TI, grilla_generica as GG, indicadores as I, preflight as PF, sintetico


def test_mas_disparos_que_la_variante_en_tiempo_y_causal():
    assert PF.estatico(X) == []
    ctx = GG.contexto_m1(sintetico.bloques(dias=10, planta=False, seed=5), tick=0.25, ticks_por_barra=10)
    assert len(X.disparos(ctx)) >= len(TI.disparos(ctx)) and TI.VIAJES_MIN == 10.0      # no deja el padre modificado
    assert I.causal(X.disparos, ctx) == []
