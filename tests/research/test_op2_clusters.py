"""OP-2: filas reales y de control con R por geometría; causal (cambiar lo posterior al horizonte no cambia operaciones anteriores)."""
import numpy as np
import pandas as pd

from edgelab.research import op2_clusters as O

S = 1_000_000_000


def test_op2_filas_y_causalidad():
    rng = np.random.default_rng(4); n = 40000; ts = 1_700_000_000 * S + np.arange(n) * S; px = 20000 + np.cumsum(rng.normal(0, 1.5, n)); v = np.ones(n)
    C = pd.DataFrame(dict(t_ns=[int(ts[k]) for k in (8000, 20000)], lo=[px[8000] - 4, px[20000] - 4], hi=[px[8000] + 4, px[20000] + 4]))
    F = pd.DataFrame(O.op2_del_dia("NQ", 20250805, ts, px, v, C, 0.25, 1.5455))
    assert len(F) and {"op_g05", "op_g1", "op_g2", "op_costo_r"} <= set(F.columns) and set(F.placebo) <= {0, 1}
    assert F[["op_g05", "op_g1", "op_g2"]].abs().max().max() <= 2.0 + 1e-9
    px2 = px.copy(); px2[34000:] += 800
    F2 = pd.DataFrame(O.op2_del_dia("NQ", 20250805, ts, px2, v, C, 0.25, 1.5455))
    pd.testing.assert_frame_equal(F[F.placebo == 0].head(1).reset_index(drop=True), F2[F2.placebo == 0].head(1).reset_index(drop=True))
