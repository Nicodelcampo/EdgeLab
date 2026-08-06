import math
import pytest

from edgelab.research.g2_ratio import (
    CSCV_S, RatioCell, RatioGateError, pbo_ratio_cscv,
    walk_forward_ratio,
)


def test_ratio_cell_rechaza_bool_y_pnl_sin_trades():
    with pytest.raises(RatioGateError): RatioCell(True, 1)
    with pytest.raises(RatioGateError): RatioCell(1.0, True)
    with pytest.raises(RatioGateError, match="sin trades"): RatioCell(1.0, 0)


def test_pbo_usa_ratio_no_suma_para_elegir():
    matrix = [(RatioCell(100, 100), RatioCell(2, 1)) for _ in range(16)]
    result = pbo_ratio_cscv(matrix)
    assert result.n_splits == math.comb(CSCV_S, CSCV_S // 2) == 70
    assert set(result.selected_configs) == {1}
    assert result.pbo == 0.0


def test_pbo_empates_son_conservadores():
    result = pbo_ratio_cscv(
        [(RatioCell(1, 1), RatioCell(2, 2)) for _ in range(8)])
    assert result.pbo == 1.0
    assert all(x == pytest.approx(0.0) for x in result.lambdas)


def test_pbo_falla_si_un_split_deja_ratio_indefinido():
    matrix = [(RatioCell(1, 1),
               RatioCell(0, 0) if row < 4 else RatioCell(1, 1))
              for row in range(8)]
    with pytest.raises(RatioGateError, match="sin trades"):
        pbo_ratio_cscv(matrix)


def test_pbo_rechaza_matriz_no_rectangular_y_s_impar():
    with pytest.raises(RatioGateError, match="rectangular"):
        pbo_ratio_cscv([(RatioCell(1, 1), RatioCell(2, 1)),
                        (RatioCell(1, 1),)], s=2)
    matrix = [(RatioCell(1, 1), RatioCell(2, 1)) for _ in range(8)]
    with pytest.raises(RatioGateError, match="par"):
        pbo_ratio_cscv(matrix, s=3)


def test_walk_forward_selecciona_ratio_no_frecuencia():
    folds = ("f1", "f2", "f3", "f4")
    per = {
        "alta_frecuencia": {f: RatioCell(100, 100) for f in folds},
        "mejor_expectativa": {f: RatioCell(2, 1) for f in folds},
    }
    result = walk_forward_ratio(per, folds)
    assert [x.fold for x in result.selections] == ["f2", "f3", "f4"]
    assert all(x.selected_config == "mejor_expectativa"
               for x in result.selections)
    assert (result.total_pnl, result.total_n_trades, result.observed) == (6, 3, 2)


def test_walk_forward_agrega_oos_por_trades_no_media_de_folds():
    folds = ("f1", "f2", "f3")
    per = {
        "A": {"f1": RatioCell(2, 1), "f2": RatioCell(100, 100),
              "f3": RatioCell(-1, 1)},
        "B": {f: RatioCell(1 if f == "f1" else 0, 1) for f in folds},
    }
    result = walk_forward_ratio(per, folds)
    assert result.total_pnl == 99 and result.total_n_trades == 101
    assert result.observed == pytest.approx(99 / 101)
    assert result.observed != pytest.approx(
        sum(x.oos_ratio for x in result.selections) / 2)


def test_walk_forward_falla_ante_faltantes_o_fold_sin_trades():
    folds = ("f1", "f2")
    missing = {"A": {"f1": RatioCell(1, 1)},
               "B": {f: RatioCell(1, 1) for f in folds}}
    with pytest.raises(RatioGateError, match="faltan"):
        walk_forward_ratio(missing, folds)
    inactive = {
        "A": {"f1": RatioCell(1, 1), "f2": RatioCell(0, 0)},
        "B": {f: RatioCell(.5, 1) for f in folds},
    }
    with pytest.raises(RatioGateError, match="sin trades"):
        walk_forward_ratio(inactive, folds)
