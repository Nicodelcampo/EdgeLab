"""SEGUNDO-INTENTO: muchas más aproximaciones que la versión con racimo, sólo entrada CONF hacia la zona, y U1 intacto después de llamar."""
from edgelab.research import grilla_generica as GG, intento_fallido_hacia_lux as V, segundo_intento as X, sintetico, u1_indaga as U


def test_mas_eventos_y_u1_intacto():
    ctx = GG.contexto_m1(sintetico.bloques(dias=60, planta=False, seed=3), tick=0.25)
    ns, ah = U.NS_U1, U.AH_CORTES
    D = X.disparos(ctx)
    assert (U.NS_U1, U.AH_CORTES) == (ns, ah)                       # el parche es sólo durante la llamada
    assert len(D) > 10 * max(len(V.disparos(ctx)), 1)
    assert set(D.ni.unique()) <= {0, 1, 2} and (D.lado.abs() == 1).all()
    assert all(e == "CONF" for e, _ in X.EJECUCIONES)
