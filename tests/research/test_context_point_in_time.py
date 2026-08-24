from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from edgelab.context import (
    ContextJoinSpec,
    attach_context_at_event_time,
    build_l1_minute_features,
)


def _events(times=("2026-03-24T14:00:30Z",)):
    return pd.DataFrame(
        {
            "event_id": [f"e{i}" for i in range(len(times))],
            "instrument": ["GC"] * len(times),
            "contract": ["GC 06-26"] * len(times),
            "cme_session": ["20260324"] * len(times),
            "event_time": list(times),
        }
    )


def _contexts(times=("2026-03-24T14:00:00Z",), states=("normal",)):
    return pd.DataFrame(
        {
            "instrument": ["GC"] * len(times),
            "contract": ["GC 06-26"] * len(times),
            "cme_session": ["20260324"] * len(times),
            "data_window_end": list(times),
            "feature_available_at": list(times),
            "context_state": list(states),
            "context_model_id": ["gate_gc_l1_hmm3_forward_v0"] * len(times),
            "context_run_id": ["run-1"] * len(times),
            "p_calm": [0.1] * len(times),
            "p_normal": [0.8] * len(times),
            "p_volatile": [0.1] * len(times),
        }
    )


def test_join_es_backward_y_no_usa_feature_futura():
    cx = _contexts(
        ("2026-03-24T14:00:00Z", "2026-03-24T14:00:31Z"),
        ("normal", "volatile"),
    )
    out = attach_context_at_event_time(_events(), cx).frame.iloc[0]
    assert out["context_as_of_ok"]
    assert out["context_state"] == "normal"
    assert out["context_feature_available_at"] <= out["event_time"]


def test_join_no_cruza_contrato_ni_sesion():
    cx = _contexts()
    cx["contract"] = "GC 04-26"
    out = attach_context_at_event_time(_events(), cx)
    assert not out.frame.loc[0, "context_as_of_ok"]
    assert out.frame.loc[0, "context_fail_reason"] == "NO_CONTEXT_KEY"


def test_contexto_mas_viejo_que_un_minuto_falla_cerrado():
    out = attach_context_at_event_time(
        _events(("2026-03-24T14:02:00Z",)),
        _contexts(("2026-03-24T14:00:00Z",)),
    )
    assert not out.frame.loc[0, "context_as_of_ok"]
    assert out.frame.loc[0, "context_fail_reason"] == "STALE_CONTEXT"
    with pytest.raises(ValueError, match="contexto incompleto"):
        out.require_complete()


def test_toxic_no_es_un_estado_valido():
    with pytest.raises(ValueError, match="estados inválidos"):
        attach_context_at_event_time(_events(), _contexts(states=("toxic",)))


def test_model_id_distinto_falla_cerrado():
    cx = _contexts()
    cx["context_model_id"] = "demo_sin_identidad"
    with pytest.raises(ValueError, match="model_id"):
        attach_context_at_event_time(_events(), cx)


def test_data_window_end_no_puede_ser_posterior_a_disponibilidad():
    cx = _contexts()
    cx["data_window_end"] = "2026-03-24T14:00:01Z"
    with pytest.raises(ValueError, match="data_window_end"):
        attach_context_at_event_time(_events(), cx)


def test_features_l1_se_publican_al_cierre_del_minuto_sin_ofi_ni_vpin():
    base = pd.Timestamp("2026-03-24T14:00:00Z").value
    ticks = pd.DataFrame(
        {
            "ts_utc_ns": [base + 10_000_000_000, base + 50_000_000_000, base + 60_000_000_000],
            "price_ticks": [100, 101, 101],
            "bid_ticks": [100, 100, 100],
            "ask_ticks": [101, 101, 101],
            "volume": [1.0, 2.0, 1.0],
            "instrument": ["GC"] * 3,
            "contract": ["GC 06-26"] * 3,
            "cme_session": ["20260324"] * 3,
        }
    )
    features = build_l1_minute_features(ticks)
    first = features.iloc[0]
    assert first["feature_available_at"] == pd.Timestamp("2026-03-24T14:01:00Z")
    assert first["data_window_end"] < first["feature_available_at"]
    assert "tape_imbalance" in features
    assert "ofi" not in features
    assert "vpin" not in features
    assert np.isfinite(first["tick_rate_per_second"])


def test_spec_no_permite_cambiar_los_tres_estados_en_silencio():
    with pytest.raises(ValueError, match="congela"):
        ContextJoinSpec(valid_states=("calm", "normal", "volatile", "toxic"))
