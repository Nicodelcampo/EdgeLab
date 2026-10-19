"""Primitivas G2 que preservan el estimando expectativa neta por trade.

PBO y walk-forward agregan celdas (sum_pnl, n_trades) y recién entonces
calculan el ratio. Nunca rankean configuraciones por PnL total ni promedian
ratios de folds con distinto número de trades.
"""
from __future__ import annotations

import itertools
import math
from dataclasses import dataclass
from math import isfinite
from typing import Hashable, Mapping, Sequence

CSCV_S = 8
PBO_MAX = 0.50


class RatioGateError(ValueError):
    """El gate no puede evaluarse sin inventar o cambiar el estimando."""


@dataclass(frozen=True)
class RatioCell:
    pnl_net: float
    n_trades: int

    def __post_init__(self):
        if (not isinstance(self.pnl_net, (int, float))
                or isinstance(self.pnl_net, bool) or not isfinite(self.pnl_net)):
            raise RatioGateError("pnl_net debe ser numerico finito")
        if not isinstance(self.n_trades, int) or isinstance(self.n_trades, bool):
            raise RatioGateError("n_trades debe ser entero")
        if self.n_trades < 0:
            raise RatioGateError("n_trades no puede ser negativo")
        if self.n_trades == 0 and self.pnl_net != 0:
            raise RatioGateError("celda sin trades debe tener pnl_net=0")

    @property
    def ratio(self):
        if self.n_trades == 0:
            raise RatioGateError("ratio indefinido: celda sin trades")
        return self.pnl_net / self.n_trades


@dataclass(frozen=True)
class PBORatioResult:
    pbo: float
    lambdas: tuple[float, ...]
    selected_configs: tuple[int, ...]
    n_splits: int
    s: int
    n_rows: int
    n_configs: int
    metric: str = "sum_pnl_over_n_trades"

    @property
    def passed(self):
        return self.pbo <= PBO_MAX


@dataclass(frozen=True)
class FoldSelection:
    fold: Hashable
    selected_config: Hashable
    trained_with: tuple[Hashable, ...]
    in_sample_pnl: float
    in_sample_n_trades: int
    in_sample_ratio: float
    oos_pnl: float
    oos_n_trades: int
    oos_ratio: float


@dataclass(frozen=True)
class WalkForwardRatioResult:
    observed: float
    total_pnl: float
    total_n_trades: int
    selections: tuple[FoldSelection, ...]
    folds: tuple[Hashable, ...]
    metric: str = "sum_pnl_over_n_trades"

    @property
    def passed(self):
        return self.observed > 0.0


def _aggregate(cells):
    return RatioCell(float(sum(x.pnl_net for x in cells)),
                     sum(x.n_trades for x in cells))


def _ratio_for_rows(matrix, rows, config):
    return _aggregate([matrix[row][config] for row in rows]).ratio


def _validate_matrix(matrix):
    rows = tuple(tuple(row) for row in matrix)
    if not rows:
        raise RatioGateError("PBO requiere filas temporales")
    n_configs = len(rows[0])
    if n_configs < 2:
        raise RatioGateError("PBO requiere al menos dos configuraciones")
    for row in rows:
        if len(row) != n_configs:
            raise RatioGateError("matriz PBO no rectangular")
        if any(not isinstance(cell, RatioCell) for cell in row):
            raise RatioGateError("cada celda PBO debe ser RatioCell")
    return rows, n_configs


def pbo_ratio_cscv(matrix, *, s=CSCV_S):
    """CSCV con ranking IS/OOS por ratio de totales trade-weighted."""
    rows, n_configs = _validate_matrix(matrix)
    if not isinstance(s, int) or isinstance(s, bool) or s < 2 or s % 2:
        raise RatioGateError("S debe ser entero par >= 2")
    if len(rows) < s:
        raise RatioGateError("hacen falta al menos S filas temporales")
    cuts = [round(i * len(rows) / s) for i in range(s + 1)]
    blocks = [tuple(range(cuts[i], cuts[i + 1])) for i in range(s)]
    if any(not block for block in blocks):
        raise RatioGateError("CSCV produjo un bloque vacio")
    lambdas, selected = [], []
    for combination in itertools.combinations(range(s), s // 2):
        train_blocks = set(combination)
        train = tuple(row for block in combination for row in blocks[block])
        test = tuple(row for block in range(s) if block not in train_blocks
                     for row in blocks[block])
        train_perf = [_ratio_for_rows(rows, train, c) for c in range(n_configs)]
        test_perf = [_ratio_for_rows(rows, test, c) for c in range(n_configs)]
        winner = max(range(n_configs), key=lambda c: (train_perf[c], -c))
        selected.append(winner)
        selected_oos = test_perf[winner]
        less = sum(value < selected_oos for value in test_perf)
        equal = sum(value == selected_oos for value in test_perf)
        rank = less + (equal + 1.0) / 2.0
        omega = rank / (n_configs + 1.0)
        omega = min(max(omega, 1e-12), 1.0 - 1e-12)
        lambdas.append(math.log(omega / (1.0 - omega)))
    expected = math.comb(s, s // 2)
    if len(lambdas) != expected:
        raise RatioGateError("particiones CSCV incompletas")
    pbo = sum(value <= 0.0 for value in lambdas) / len(lambdas)
    return PBORatioResult(pbo, tuple(lambdas), tuple(selected), len(lambdas),
                          s, len(rows), n_configs)


def walk_forward_ratio(per_fold: Mapping[Hashable, Mapping[Hashable, RatioCell]],
                       folds_ordered: Sequence[Hashable]):
    """Re-selecciona por ratio histórico y agrega OOS como ratio de totales."""
    folds = tuple(folds_ordered)
    if len(folds) < 2 or len(set(folds)) != len(folds):
        raise RatioGateError("walk-forward requiere folds unicos y al menos dos")
    configs = tuple(sorted(per_fold, key=lambda value: str(value)))
    if len(configs) < 2:
        raise RatioGateError("walk-forward requiere al menos dos configuraciones")
    for config in configs:
        missing = [fold for fold in folds if fold not in per_fold[config]]
        if missing:
            raise RatioGateError("faltan celdas para %r: %r" % (config, missing))
        if any(not isinstance(per_fold[config][fold], RatioCell) for fold in folds):
            raise RatioGateError("cada fold debe contener RatioCell")
    selections, oos_cells = [], []
    for position in range(1, len(folds)):
        previous, test_fold = folds[:position], folds[position]
        training = {config: _aggregate([per_fold[config][fold]
                                        for fold in previous])
                    for config in configs}
        ratios = {config: training[config].ratio for config in configs}
        winner = max(configs, key=lambda c: (ratios[c], -configs.index(c)))
        oos = per_fold[winner][test_fold]
        oos_ratio = oos.ratio
        oos_cells.append(oos)
        selections.append(FoldSelection(
            test_fold, winner, previous, training[winner].pnl_net,
            training[winner].n_trades, ratios[winner], oos.pnl_net,
            oos.n_trades, oos_ratio))
    aggregate = _aggregate(oos_cells)
    return WalkForwardRatioResult(aggregate.ratio, aggregate.pnl_net,
                                  aggregate.n_trades, tuple(selections), folds)
