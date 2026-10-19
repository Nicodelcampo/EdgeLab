"""Pipeline legacy retirado; conserva sólo el guard fail-closed.

La ruta formal es:
1) gate_features_l1_v0.build_l1_minute_features;
2) train_label_hmm3 train/label;
3) gate_adapter_v2.attach_context_at_t0.
"""
from __future__ import annotations

import pandas as pd


def _ensure_regime_on_bars(bars: pd.DataFrame) -> pd.DataFrame:
    required = {"context_state", "context_model_id", "context_run_id"}
    missing = sorted(required - set(bars.columns))
    if missing:
        raise ValueError(
            "fail-closed: no se inventan regímenes por cuantiles; "
            f"faltan labels de checkpoint real: {missing}"
        )
    return bars.copy()


def run_integration_pipeline(*args, **kwargs):
    raise RuntimeError(
        "pipeline v1 retirado; use modules.gate.integration.train_label_hmm3 y gate_adapter_v2"
    )
