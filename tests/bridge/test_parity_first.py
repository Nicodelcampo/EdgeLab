"""Verifica que los kernels «paridad primero» cumplan el contrato.

El test central es el criterio de aceptación declarado en
`docs/research/PARITY_FIRST_INDICATOR_CONTRACT_2026-09-02.md`: bajo ruido de ±1
en el volumen por celda, el turnover debe ser < 5 %. aVolClusterPOI daba 66 %.
"""
import random

from edgelab.bridge.indicators.parity_first import (
    evaluate_avol_block, evaluate_impulse_window)


def _block(seed=0, n_cells=60, center=100_000):
    rng = random.Random(seed)
    cells = {}
    for i in range(n_cells):
        t = center - n_cells // 2 + i
        # cola baja + un pico concentrado en el medio, como un bloque real
        cells[t] = rng.randint(1, 9) if abs(i - n_cells // 2) > 4 else rng.randint(40, 120)
    return cells


def test_decision_is_deterministic():
    cells = _block(1)
    a = evaluate_avol_block(cells, close_tick=100_050)
    b = evaluate_avol_block(dict(reversed(list(cells.items()))), close_tick=100_050)
    assert a == b, "el orden de inserción del dict no debe cambiar la decisión"


def test_share_is_integer_basis_points():
    # 10 y 11 son contiguas y forman cluster; 50 queda aislada y no lo integra
    cells = {10: 30, 11: 30, 50: 40}
    out = evaluate_avol_block(cells, close_tick=20, params={"min_block_cells": 3,
                                                            "min_share_bps": 0})
    assert isinstance(out["share_bps"], int)
    assert (out["sel_lower_tick"], out["sel_upper_tick"]) == (10, 11)
    # 60 de 100 -> 6000 bps exactos, división entera
    assert out["share_bps"] == 6000


def test_abstains_are_explicit():
    assert evaluate_avol_block({1: 5}, 1)["decision"] == "ABSTAIN_FEW_CELLS"
    far = {10: 5, 30: 5, 50: 5}          # sin celdas contiguas
    assert evaluate_avol_block(far, 1)["decision"] == "ABSTAIN_NO_CLUSTER"
    flat = {i: 10 for i in range(20)}    # ningún cluster domina
    assert evaluate_avol_block(flat, 1, {"min_share_bps": 9000})["decision"] == "ABSTAIN_BELOW_SHARE"


def test_avol_turnover_under_noise_is_below_5pct():
    """Criterio de aceptación del contrato. aVolClusterPOI daba 0,66 acá."""
    base, changed, total = {}, 0, 0
    for s in range(60):
        cells = _block(s)
        b = evaluate_avol_block(cells, close_tick=100_050)
        base[s] = (b["decision"], b["sel_lower_tick"], b["sel_upper_tick"])
    rng = random.Random(99)
    for s in range(60):
        cells = _block(s)
        noisy = {t: max(1, v + rng.randint(-1, 1)) for t, v in cells.items()}
        n = evaluate_avol_block(noisy, close_tick=100_050)
        total += 1
        if (n["decision"], n["sel_lower_tick"], n["sel_upper_tick"]) != base[s]:
            changed += 1
    turnover = changed / total
    assert turnover < 0.05, f"turnover {turnover:.3f} supera el 5% del contrato"


def test_impulse_uses_no_clock_and_is_integer():
    closes = list(range(100, 100 + 12 * 3, 3))       # sube 3 ticks por barra
    highs = [c + 1 for c in closes]
    lows = [c - 1 for c in closes]
    vols = [10] * 12
    out = evaluate_impulse_window(closes, highs, lows, vols)
    assert out["decision"] == "CREATE"
    assert out["direction"] == 1
    assert out["displacement_ticks"] == 33
    assert out["path_ticks"] == 33
    assert out["efficiency_bps"] == 10000          # recta perfecta
    assert isinstance(out["efficiency_bps"], int)
    assert out["zone_lower_tick"] == min(lows)


def test_impulse_rejects_choppy_path():
    closes = [100, 110, 100, 110, 100, 110, 100, 110, 100, 110, 100, 116]
    out = evaluate_impulse_window(closes, [c + 1 for c in closes],
                                  [c - 1 for c in closes], [10] * 12)
    assert out["decision"] == "ABSTAIN_LOW_EFFICIENCY"
    assert out["path_ticks"] > out["displacement_ticks"]


def test_impulse_turnover_under_volume_noise_is_zero():
    """El impulso no mira volumen por celda: el ruido de volumen no debe moverlo."""
    closes = list(range(100, 100 + 12 * 3, 3))
    highs = [c + 1 for c in closes]
    lows = [c - 1 for c in closes]
    rng = random.Random(7)
    a = evaluate_impulse_window(closes, highs, lows, [10] * 12)
    b = evaluate_impulse_window(closes, highs, lows,
                                [max(1, 10 + rng.randint(-1, 1)) for _ in range(12)])
    assert a["decision"] == b["decision"]
    assert (a["zone_lower_tick"], a["zone_upper_tick"]) == (b["zone_lower_tick"], b["zone_upper_tick"])
