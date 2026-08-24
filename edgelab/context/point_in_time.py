"""Join point-in-time estricto de estados de contexto a eventos.

No detecta regímenes ni mira outcomes. Una feature con el mismo timestamp que
el evento se considera ambigua salvo que exista una secuencia de publicación;
este schema no la tiene, por lo que exige ``feature_available_at < event_time``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

_VALID_STATES = ("calm", "normal", "volatile")
_REQUIRED_EVENT = ("event_id", "instrument", "contract", "cme_session", "event_time")
_REQUIRED_CONTEXT = (
    "instrument", "contract", "cme_session", "data_window_end",
    "feature_available_at", "context_state", "context_model_id", "context_run_id",
)
_PROBABILITY_COLUMNS = ("p_calm", "p_normal", "p_volatile")


@dataclass(frozen=True)
class ContextJoinSpec:
    model_id: str = "gate_gc_l1_hmm3_forward_v0"
    schema_version: str = "edgelab.context_labels/0.1.0"
    max_feature_age_ns: int = 60_000_000_000
    key_columns: tuple[str, ...] = ("instrument", "contract", "cme_session")
    valid_states: tuple[str, ...] = _VALID_STATES

    def __post_init__(self) -> None:
        if not self.model_id.strip():
            raise ValueError("model_id vacío")
        if self.max_feature_age_ns <= 0:
            raise ValueError("max_feature_age_ns debe ser > 0")
        if tuple(self.valid_states) != _VALID_STATES:
            raise ValueError("v0 congela exactamente calm/normal/volatile; toxic no es válido")


@dataclass
class ContextJoinResult:
    frame: pd.DataFrame
    report: dict[str, Any]

    def require_complete(self) -> pd.DataFrame:
        if not bool(self.frame["context_as_of_ok"].all()):
            counts = self.frame.loc[
                ~self.frame["context_as_of_ok"], "context_fail_reason"
            ].value_counts().to_dict()
            raise ValueError(f"contexto incompleto: {counts}")
        return self.frame


def _require_columns(df: pd.DataFrame, required: tuple[str, ...], name: str) -> None:
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError(f"{name}: faltan columnas {missing}")


def _to_utc_ns(values: pd.Series, name: str) -> tuple[pd.Series, np.ndarray]:
    """Normaliza siempre a nanosegundos, incluso con pandas 3 (default us)."""
    if pd.api.types.is_numeric_dtype(values):
        numeric = pd.to_numeric(values, errors="raise")
        if pd.api.types.is_float_dtype(numeric) and not np.equal(
            numeric, np.floor(numeric)
        ).all():
            raise ValueError(f"{name}: epoch ns no puede tener fracción")
        source = numeric.to_numpy(dtype=np.int64)
        parsed = pd.to_datetime(source, unit="ns", utc=True, errors="coerce")
    else:
        parsed = pd.to_datetime(values, utc=True, errors="coerce")
    dt = pd.Series(parsed, index=values.index).astype("datetime64[ns, UTC]")
    if dt.isna().any():
        raise ValueError(f"{name}: timestamps inválidos")
    ns = dt.astype("int64").to_numpy(dtype=np.int64)
    return dt, ns


def _validate_probabilities(contexts: pd.DataFrame) -> tuple[str, ...]:
    present = tuple(column for column in _PROBABILITY_COLUMNS if column in contexts.columns)
    if present and present != _PROBABILITY_COLUMNS:
        raise ValueError("contexts: si hay probabilidades deben estar p_calm/p_normal/p_volatile")
    if not present:
        return ()
    values = contexts.loc[:, list(present)].apply(
        pd.to_numeric, errors="raise"
    ).to_numpy(dtype=float)
    if not np.isfinite(values).all() or np.any((values < 0) | (values > 1)):
        raise ValueError("contexts: probabilidades fuera de [0,1]")
    if not np.allclose(values.sum(axis=1), 1.0, rtol=0.0, atol=1e-6):
        raise ValueError("contexts: probabilidades no suman 1")
    return _PROBABILITY_COLUMNS


def attach_context_at_event_time(
    events: pd.DataFrame,
    contexts: pd.DataFrame,
    *,
    spec: ContextJoinSpec | None = None,
    require_complete: bool = False,
) -> ContextJoinResult:
    """Adjunta el último contexto estrictamente anterior dentro de la misma identidad."""
    spec = spec or ContextJoinSpec()
    _require_columns(events, _REQUIRED_EVENT, "events")
    _require_columns(contexts, _REQUIRED_CONTEXT, "contexts")
    if events["event_id"].astype(str).duplicated().any():
        raise ValueError("events: event_id duplicado")
    if len(contexts) == 0:
        raise ValueError("contexts vacío")

    ev = events.copy().reset_index(drop=True)
    cx = contexts.copy().reset_index(drop=True)
    for column in spec.key_columns:
        ev[column] = ev[column].astype(str)
        cx[column] = cx[column].astype(str)
    ev["event_id"] = ev["event_id"].astype(str)
    ev["event_time"], ev_ns = _to_utc_ns(ev["event_time"], "events.event_time")
    cx["data_window_end"], data_end_ns = _to_utc_ns(
        cx["data_window_end"], "contexts.data_window_end"
    )
    cx["feature_available_at"], available_ns = _to_utc_ns(
        cx["feature_available_at"], "contexts.feature_available_at"
    )
    cx["_available_ns"] = available_ns
    cx["_data_end_ns"] = data_end_ns

    if np.any(data_end_ns > available_ns):
        raise ValueError("contexts: data_window_end posterior a feature_available_at")
    states = cx["context_state"].astype(str)
    invalid_states = sorted(set(states) - set(spec.valid_states))
    if invalid_states:
        raise ValueError(f"contexts: estados inválidos {invalid_states}")
    model_ids = set(cx["context_model_id"].astype(str))
    if model_ids != {spec.model_id}:
        raise ValueError(f"contexts: model_id {sorted(model_ids)} != {spec.model_id}")
    if cx["context_run_id"].astype(str).str.strip().eq("").any():
        raise ValueError("contexts: context_run_id vacío")
    probability_columns = _validate_probabilities(cx)

    duplicate_key = list(spec.key_columns) + ["_available_ns"]
    if cx.duplicated(duplicate_key).any():
        raise ValueError("contexts: clave+feature_available_at duplicada")
    cx = cx.sort_values(duplicate_key, kind="mergesort").reset_index(drop=True)

    n = len(ev)
    state_out = np.full(n, None, dtype=object)
    model_out = np.full(n, None, dtype=object)
    run_out = np.full(n, None, dtype=object)
    available_out = np.full(n, np.datetime64("NaT"), dtype="datetime64[ns]")
    data_end_out = np.full(n, np.datetime64("NaT"), dtype="datetime64[ns]")
    age_out = np.full(n, -1, dtype=np.int64)
    ok_out = np.zeros(n, dtype=bool)
    reason_out = np.full(n, "NO_CONTEXT_KEY", dtype=object)
    prob_out = {column: np.full(n, np.nan, dtype=float) for column in probability_columns}

    grouped_contexts = {
        tuple(key if isinstance(key, tuple) else (key,)): group.reset_index(drop=True)
        for key, group in cx.groupby(list(spec.key_columns), sort=False, dropna=False)
    }
    for raw_key, event_group in ev.groupby(
        list(spec.key_columns), sort=False, dropna=False
    ):
        key = tuple(raw_key if isinstance(raw_key, tuple) else (raw_key,))
        group = grouped_contexts.get(key)
        positions = event_group.index.to_numpy(dtype=np.int64)
        if group is None:
            continue
        feature_ns = group["_available_ns"].to_numpy(dtype=np.int64)
        # side='left' excluye igualdad: sin sequence, el mismo timestamp es ambiguo.
        idx = np.searchsorted(feature_ns, ev_ns[positions], side="left") - 1
        has_prior = idx >= 0
        reason_out[positions[has_prior]] = "STALE_CONTEXT"
        reason_out[positions[~has_prior]] = "NO_STRICT_PRIOR_CONTEXT"
        if not bool(has_prior.any()):
            continue

        event_positions = positions[has_prior]
        selected = group.iloc[idx[has_prior]].reset_index(drop=True)
        selected_available = selected["_available_ns"].to_numpy(dtype=np.int64)
        selected_data_end = selected["_data_end_ns"].to_numpy(dtype=np.int64)
        age = ev_ns[event_positions] - selected_available
        causal = selected_available < ev_ns[event_positions]
        data_causal = selected_data_end < ev_ns[event_positions]
        fresh = age <= spec.max_feature_age_ns
        valid = causal & data_causal & fresh
        if np.any(~causal | ~data_causal):
            raise AssertionError("join point-in-time seleccionó una fila futura o ambigua")

        good_positions = event_positions[valid]
        selected_good = selected.loc[valid].reset_index(drop=True)
        ok_out[good_positions] = True
        reason_out[good_positions] = ""
        state_out[good_positions] = selected_good["context_state"].astype(str).to_numpy()
        model_out[good_positions] = selected_good["context_model_id"].astype(str).to_numpy()
        run_out[good_positions] = selected_good["context_run_id"].astype(str).to_numpy()
        age_out[event_positions] = age
        available_out[good_positions] = selected_good["feature_available_at"].to_numpy(
            dtype="datetime64[ns]"
        )
        data_end_out[good_positions] = selected_good["data_window_end"].to_numpy(
            dtype="datetime64[ns]"
        )
        for column in probability_columns:
            prob_out[column][good_positions] = selected_good[column].to_numpy(dtype=float)

    out = ev.copy()
    out["context_state"] = pd.Series(state_out, dtype="string")
    out["context_feature_available_at"] = pd.to_datetime(available_out, utc=True)
    out["context_data_window_end"] = pd.to_datetime(data_end_out, utc=True)
    out["context_age_ns"] = pd.array(
        np.where(age_out >= 0, age_out, None), dtype="Int64"
    )
    out["context_model_id"] = pd.Series(model_out, dtype="string")
    out["context_run_id"] = pd.Series(run_out, dtype="string")
    out["context_schema_version"] = spec.schema_version
    out["context_as_of_ok"] = ok_out
    out["context_fail_reason"] = reason_out
    for column, values in prob_out.items():
        out[column] = values

    reason_counts = out.loc[
        ~out["context_as_of_ok"], "context_fail_reason"
    ].value_counts().to_dict()
    report = {
        "schema": spec.schema_version,
        "model_id": spec.model_id,
        "join": "strict_backward_by_instrument_contract_cme_session",
        "max_feature_age_ns": spec.max_feature_age_ns,
        "n_events": int(len(out)),
        "n_as_of_ok": int(out["context_as_of_ok"].sum()),
        "coverage": float(out["context_as_of_ok"].mean()) if len(out) else 0.0,
        "fail_reasons": {str(key): int(value) for key, value in reason_counts.items()},
        "states": list(spec.valid_states),
        "outcomes_accessed": False,
    }
    result = ContextJoinResult(frame=out, report=report)
    if require_complete:
        result.require_complete()
    return result
