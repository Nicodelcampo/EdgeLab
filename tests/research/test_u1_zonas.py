"""U1-ZONAS: con las zonas de LUX-IMB puestas en el almacén, la gramática da exactamente U1-ORO-GRILLA; causalidad; el módulo de
U1-INDAGA queda intacto."""
import numpy as np
import pandas as pd
import pytest

from edgelab.research import areas_expansion as AX, grilla_generica as GG, indicadores as I, sintetico, u1_indaga as U, u1_oro as UO, u1_zonas as X


@pytest.fixture(scope="module")
def ctx():
    return GG.contexto_m1(sintetico.bloques(dias=70, planta=True, seed=4), tick=0.25)


def _ref(ctx):
    return float(np.median(ctx["h"] - ctx["l"]))


def _almacen_lux(ctx):
    """Las zonas de LUX-IMB por mes (como las arma U1-ORO-GRILLA), en formato almacén: creación = cierre de la vela creadora."""
    mes, _ = UO.escala_por_mes(ctx, _ref(ctx)); filas = []
    for m in pd.unique(mes):
        ix = np.flatnonzero(mes == m); a, b = ix[0], ix[-1] + 1
        Z = AX.zonas(ctx["t"][a:b], ctx["o"][a:b], ctx["h"][a:b], ctx["l"][a:b], ctx["c"][a:b])
        filas.append(pd.DataFrame(dict(t_ns=ctx["t"][a:b][Z["zi"]] * 10**9, lo=Z["zlo"], hi=Z["zhi"])))
    return pd.concat(filas, ignore_index=True)


def test_con_zonas_de_lux_es_u1_oro(ctx):
    a = X.disparos(dict(ctx, zonas={"AVZP2": _almacen_lux(ctx)}), r_ref=_ref(ctx)).drop(columns="ind")
    b = UO.disparos(ctx, r_ref=_ref(ctx))
    assert len(b) > 0
    pd.testing.assert_frame_equal(a.reset_index(drop=True), b.reset_index(drop=True), check_dtype=False)
    assert U.AX is AX                                                     # se devuelve el módulo original


def test_zona_disponible_al_cierre_de_su_vela():
    t = np.array([60, 120, 180, 240], np.int64)
    Z = X.zonas_almacen(pd.DataFrame(dict(t_ns=[90 * 10**9, 120 * 10**9, 300 * 10**9], lo=[1.0, 2.0, 3.0], hi=[1.5, 2.5, 3.5])), t)
    assert list(Z["zi"]) == [1, 1]                                        # 90 s -> vela que cierra a 120; la de 300 s no existe todavía


def test_causal(ctx, monkeypatch):
    monkeypatch.setattr(UO, "R_USATECH", _ref(ctx))
    Zs = _almacen_lux(ctx)
    f = lambda c: X.disparos(dict(c, zonas={"AVZP2": Zs}))
    assert I.causal(f, ctx, columnas=["k", "lado", "ni", "xi", "A_H", "esc"]) == []
