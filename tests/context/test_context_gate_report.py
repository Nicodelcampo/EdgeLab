# -*- coding: utf-8 -*-
"""Auditoría 051 §4-§5: reporte de compuertas con PASS/STOP automático, sólo sobre evaluación, con estabilidad por
semilla y estado, concentración horaria y clasificador de sólo-hora. Datos sintéticos, sin retornos."""
import numpy as np
import pandas as pd

from edgelab.context.hmm3 import HMM3Config
from edgelab.context.l2_gate import (TOXIC_FEATURES, context_gate_report, fit_regime4_model, label_regime4,
                                     seed_labels)

NAMES = list(dict.fromkeys(list(HMM3Config().feature_names) + list(TOXIC_FEATURES)))


def _frame(n_sessions=8, minutes=300, hour_driven=False, seed=3):
    rng = np.random.default_rng(seed)
    rows = []
    for d in range(n_sessions):
        base = 29_000_000 + d * 1440
        regime = np.repeat(rng.integers(0, 3, size=minutes // 30), 30)
        for m in range(minutes):
            r = (m // 100) % 3 if hour_driven else regime[m]
            row = dict(cme_session=f"2026070{d}", minute_id=base + m, feature_eligible=True)
            for k, name in enumerate(NAMES):
                row[name] = abs(rng.normal(1.0 + 2.0 * r + 0.1 * k, 0.3)) + 0.01
            rows.append(row)
    return pd.DataFrame(rows)


def _run(f, **kw):
    sessions = sorted(f.cme_session.unique())
    train, ev = sessions[:4], sessions[4:]
    model = fit_regime4_model(f, train_sessions=train, code_identity="test-commit", deseasonalize=True, seeds=[1, 2, 3], **kw)
    lab = label_regime4(f, model)
    _, sets = seed_labels(f, model, ev)
    return context_gate_report(lab, model, train_sessions=train, evaluation_sessions=ev, roll_date=ev[2],
                               seed_label_sets=sets)


def test_report_has_gates_and_verdict_on_evaluation_only():
    rep = _run(_frame())
    assert rep["outcomes_accessed"] is False
    assert set(rep["coverage"]) >= {"labeled", "eligible", "value", "pass"}
    assert "seed_stability_eval" in rep and "hour_concentration" in rep and "roll_drift" in rep
    assert rep["verdict"] in ("PASS", "STOP") and isinstance(rep["stops"], list)


def test_hour_driven_climate_is_stopped():
    rep = _run(_frame(hour_driven=True))
    assert rep["verdict"] == "STOP"
    assert any(s.startswith("HOUR") for s in rep["stops"]) or "SEED_INSTABILITY" in rep["stops"]
