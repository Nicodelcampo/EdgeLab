# -*- coding: utf-8 -*-
"""Auditoría 046 §10: semillas que cambian de verdad la inicialización y desestacionalización sólo con entrenamiento."""
import numpy as np
import pandas as pd

from edgelab.context.hmm3 import HMM3Config, _initial_parameters, _sequence_slices, fit_hmm3_seeds
from edgelab.context.l2_gate import apply_seasonal, fit_seasonal_profile, _ct_bucket


def _matrix(n=600, seed=1):
    rng = np.random.default_rng(seed)
    regimes = np.repeat([0, 1, 2, 1, 0, 2], n // 6)
    return np.vstack([rng.normal(r * 3.0, 1.0, size=6) for r in regimes])


def test_random_init_depends_on_seed_and_terciles_do_not():
    X = _matrix(); seq = _sequence_slices(["s"] * len(X))
    a = _initial_parameters(X, 0, seq, HMM3Config(init_mode="random", seed=1))[2]
    b = _initial_parameters(X, 0, seq, HMM3Config(init_mode="random", seed=2))[2]
    c = _initial_parameters(X, 0, seq, HMM3Config(seed=1))[2]
    d = _initial_parameters(X, 0, seq, HMM3Config(seed=2))[2]
    assert not np.allclose(a, b)
    assert np.allclose(c, d)                      # modo histórico: la semilla no participa (documentado)


def test_multi_seed_reports_agreement():
    X = _matrix()
    out = fit_hmm3_seeds(X, ["s"] * len(X), seeds=[1, 2, 3], code_identity="test-commit")
    assert len(out["per_seed"]) == 3 and 0.0 <= out["min_agreement"] <= 1.0
    assert out["best_seed"] in (1, 2, 3)


def test_seasonal_profile_removes_time_of_day_pattern_and_uses_only_train():
    # minute_id en reloj ART; 3 sesiones de train y 1 de evaluación con un patrón horario fuerte
    rows = []
    for day in range(4):
        base = 29_000_000 + day * 1440
        for m in range(600):
            mid = base + m
            pattern = 5.0 if (m // 60) % 2 == 0 else 1.0
            rows.append(dict(minute_id=mid, cme_session=f"d{day}", x=pattern * (1 + 0.01 * (m % 7))))
    f = pd.DataFrame(rows)
    train = f[f.cme_session != "d3"]
    prof = fit_seasonal_profile(train, ["x"], min_rows=10)   # 3 días × 5 min = 15 filas por franja
    adj = apply_seasonal(f, prof)
    ev = adj[adj.cme_session == "d3"]["x"].to_numpy()
    assert prof["features"]["x"]["mode"] == "log_ratio"
    assert abs(np.median(ev)) < 0.05 and ev.std() < 0.05            # el patrón horario desaparece
    assert len(set(_ct_bucket(f))) > 1
