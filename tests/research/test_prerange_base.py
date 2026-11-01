"""PRERANGE-BASE: preflight, causalidad, paridad lote/escalar y la misma mecánica que prerange_hft."""
import numpy as np

from edgelab.research import grilla_generica as GG, indicadores as IND, preflight as PF, prerange_base as P, prerange_hft as X
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_paquete_20261031 import ctx_sintetico  # noqa: E402

_C = {}


def _ctx():
    if "c" not in _C: _C["c"] = ctx_sintetico(dias=30, seed=2)
    return _C["c"]


def test_preflight_y_tamano():
    assert PF.estatico(P) == [] and GG.n_celdas(P) == 144 and P.EJECUCIONES == X.EJECUCIONES


def test_causal():
    assert IND.causal(P.disparos, _ctx()) == []


def test_lote_igual_a_escalar_y_hay_disparos_de_los_tres_gatillos():
    ctx = _ctx(); D = P.disparos(ctx)
    assert set(D.gat.unique()) == {0, 1, 2}
    assert np.array_equal(GG.ops_por_fila(P, D, ctx), GG._ops_lote(P, D, ctx), equal_nan=True)
