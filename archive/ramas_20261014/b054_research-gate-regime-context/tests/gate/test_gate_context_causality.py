from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from modules.gate.core.gate_adapter_v2 import attach_context_at_t0, load_schema
from modules.gate.core.gate_features_l1_v0 import build_l1_minute_features

MODEL_ID = "gate_gc_l1_hmm3_forward_v0:0123456789abcdef"


def _events(time="2026-03-24T14:00:30Z", contract="GC 06-26"):
    return pd.DataFrame({
        "event_id": ["e1"], "instrument": ["GC"], "contract": [contract],
        "cme_session": ["20260324"], "event_time": [time],
    })


def _contexts(times=("2026-03-24T14:00:00Z",), states=("normal",)):
    return pd.DataFrame({
        "instrument": ["GC"] * len(times), "contract": ["GC 06-26"] * len(times),
        "cme_session": ["20260324"] * len(times), "data_window_end": list(times),
        "feature_available_at": list(times), "context_state": list(states),
        "context_model_id": [MODEL_ID] * len(times), "context_run_id": ["run-1"] * len(times),
        "p_calm": [0.1] * len(times), "p_normal": [0.8] * len(times),
        "p_volatile": [0.1] * len(times),
    })


def test_schema_carga_desde_schema_y_no_desde_core():
    assert load_schema()["version"] == "2.0.0"


def test_join_no_usa_feature_futura_y_es_por_identidad():
    contexts = _contexts(
        ("2026-03-24T14:00:00Z", "2026-03-24T14:00:31Z"),
        ("normal", "volatile"),
    )
    out, report = attach_context_at_t0(_events(), contexts, model_id=MODEL_ID)
    assert report["n_as_of_ok"] == 1
    assert out.loc[0, "context_state"] == "normal"
    assert out.loc[0, "context_feature_available_at"] <= out.loc[0, "event_time"]
    other, _ = attach_context_at_t0(
        _events(contract="GC 04-26"), contexts, model_id=MODEL_ID
    )
    assert not other.loc[0, "context_as_of_ok"]
    assert other.loc[0, "context_fail_reason"] == "NO_CONTEXT_KEY"


def test_contexto_stale_falla_cerrado():
    out, _ = attach_context_at_t0(
        _events("2026-03-24T14:02:00Z"), _contexts(), model_id=MODEL_ID
    )
    assert not out.loc[0, "context_as_of_ok"]
    assert out.loc[0, "context_fail_reason"] == "STALE_CONTEXT"


def test_model_id_sin_hash_y_estado_toxic_son_invalidos():
    with pytest.raises(ValueError, match="checkpoint"):
        attach_context_at_t0(_events(), _contexts(), model_id="gate_gc_l1_hmm3_forward_v0")
    with pytest.raises(ValueError, match="estados inválidos"):
        attach_context_at_t0(_events(), _contexts(states=("toxic",)), model_id=MODEL_ID)


def test_minuto_se_publica_al_final_y_no_reintroduce_ofi_vpin():
    base = pd.Timestamp("2026-03-24T14:00:00Z").value
    ticks = pd.DataFrame({
        "ts_utc_ns": [base + 10_000_000_000, base + 50_000_000_000, base + 60_000_000_000],
        "price_ticks": [100, 101, 101], "bid_ticks": [100, 100, 100],
        "ask_ticks": [101, 101, 101], "volume": [1.0, 2.0, 1.0],
        "instrument": ["GC"] * 3, "contract": ["GC 06-26"] * 3,
        "cme_session": ["20260324"] * 3,
    })
    features = build_l1_minute_features(ticks)
    first = features.iloc[0]
    assert first["feature_available_at"] == pd.Timestamp("2026-03-24T14:01:00Z")
    assert first["data_window_end"] < first["feature_available_at"]
    assert "tape_imbalance" in features
    assert not ({"ofi", "ofi_z", "ofi_ema_z", "vpin"} & set(features.columns))
    assert np.isfinite(first["tick_rate_per_second"])
