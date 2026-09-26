import math

import pytest

from edgelab.research.g2_protocol import (
    G2ProtocolError,
    campaign_null_pvalue,
    pbo_cscv,
    walk_forward,
)
from edgelab.research.g2_ratio import CSCV_S, RatioCell


def test_nulo_exige_mil_replicas_y_cuenta_empates():
    with pytest.raises(G2ProtocolError, match="1000"):
        campaign_null_pvalue(1.0, [0.0] * 999)
    assert campaign_null_pvalue(0.0, [0.0] * 1000)[0] == 1.0


def test_nulo_detecta_estadistico_fuera_de_replicas():
    p_value, observed = campaign_null_pvalue(1.0, [0.0] * 1000)
    assert p_value == pytest.approx(1 / 1001)
    assert observed == 1.0


def test_pbo_canónico_no_ranquea_por_pnl_total():
    matrix = [(RatioCell(100, 100), RatioCell(2, 1)) for _ in range(16)]
    result = pbo_cscv(matrix)
    assert result.pbo == 0.0
    assert result.n_splits == math.comb(CSCV_S, CSCV_S // 2) == 70
    assert set(result.selected_configs) == {1}


def test_walk_forward_canónico_no_ranquea_por_frecuencia():
    folds = ("f1", "f2", "f3", "f4")
    per_fold = {
        "frecuente": {fold: RatioCell(100, 100) for fold in folds},
        "mejor": {fold: RatioCell(2, 1) for fold in folds},
    }
    result = walk_forward(per_fold, folds)
    assert result.observed == 2.0
    assert all(row.selected_config == "mejor" for row in result.selections)
