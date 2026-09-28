"""Nulo simulado del espejo: se verifica contra probabilidades conocidas antes de tocar datos reales (auditoría 056 §6)."""
import numpy as np
import pytest

from edgelab.research.espejo_nulo import simulate_null


def _walk_triples(n=5000, p=0.3, trades=25, seed=1):
    rng = np.random.default_rng(seed)
    steps = rng.choice([-1, 0, 1], p=[p / 2, 1 - p, p / 2], size=(n, trades)).cumsum(1)
    return np.column_stack([steps[:, -1], np.maximum(steps.max(1), 0), np.minimum(steps.min(1), 0)]).astype(float)


def test_long_horizon_matches_gamblers_ruin():
    # barreras simétricas lejos del horizonte: P(completa) -> d_b / (d_a + d_b) (paseo justo)
    r = simulate_null(0, 10, -30, +1, _walk_triples(), horizon_100t=400, n=4000, seed=3)
    assert r["censurada"] < 0.01
    assert r["completa"] == pytest.approx(30 / 40, abs=0.03)


def test_direction_is_symmetric():
    t = _walk_triples()
    up = simulate_null(100, 110, 80, +1, t, 50, n=3000, seed=4)
    dn = simulate_null(100, 90, 120, -1, t, 50, n=3000, seed=4)
    assert up["completa"] == pytest.approx(dn["completa"], abs=0.03)


def test_short_horizon_censors_and_reports_it():
    r = simulate_null(0, 40, -40, +1, _walk_triples(), horizon_100t=1, n=2000, seed=5)
    assert r["censurada"] > 0.9
    assert abs(sum(r[k] for k in ("completa", "falla", "ambigua", "censurada")) - 1) < 1e-9


def test_drift_is_removed():
    t = _walk_triples(); t[:, 0] += 2; t[:, 1] += 2; t[:, 2] += 2          # deriva fuerte hacia A
    r = simulate_null(0, 20, -20, +1, t, 400, n=3000, seed=6)
    assert r["completa"] == pytest.approx(0.5, abs=0.05)


def test_needs_enough_history():
    with pytest.raises(ValueError):
        simulate_null(0, 10, -10, +1, _walk_triples(n=20), 10)
