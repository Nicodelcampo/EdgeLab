"""Adaptador formal GATE v2: point-in-time, por identidad y fail-closed."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schema" / "gate_context_schema_v2.json"
MODEL_ID_RE = re.compile(r"^gate_gc_l1_hmm3_forward_v0:[0-9a-f]{16}$")
STATES = ("calm", "normal", "volatile")
KEYS = ("instrument", "contract", "cme_session")
EVENT_REQUIRED = ("event_id", *KEYS, "event_time")
CONTEXT_REQUIRED = (
    *KEYS, "data_window_end", "feature_available_at", "context_state",
    "context_model_id", "context_run_id",
)


def load_schema() -> dict[str, Any]:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    if schema.get("version") != "2.0.0":
        raise ValueError("schema GATE v2 inesperado")
    return schema


def _require(df: pd.DataFrame, columns: tuple[str, ...], name: str) -> None:
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise ValueError(f"{name}: faltan columnas {missing}")


def _utc(values: pd.Series, name: str) -> pd.Series:
    out = pd.to_datetime(values, utc=True, errors="coerce")
    if out.isna().any():
        raise ValueError(f"{name}: timestamps inválidos")
    return out


def attach_context_at_t0(events: pd.DataFrame, contexts: pd.DataFrame, *,
                         model_id: str, max_feature_age: str = "1min",
                         require_complete: bool = False) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Adjunta el último estado ya disponible en t0 dentro de la misma identidad."""
    load_schema()
    if not MODEL_ID_RE.fullmatch(model_id):
        raise ValueError("model_id debe identificar un checkpoint real hash-qualified")
    _require(events, EVENT_REQUIRED, "events")
    _require(contexts, CONTEXT_REQUIRED, "contexts")
    if events["event_id"].astype(str).duplicated().any():
        raise ValueError("events: event_id duplicado")
    if len(contexts) == 0:
        raise ValueError("contexts vacío")

    ev = events.copy().reset_index(drop=True)
    cx = contexts.copy().reset_index(drop=True)
    for key in KEYS:
        ev[key] = ev[key].astype(str)
        cx[key] = cx[key].astype(str)
    ev["event_time"] = _utc(ev["event_time"], "event_time")
    cx["data_window_end"] = _utc(cx["data_window_end"], "data_window_end")
    cx["feature_available_at"] = _utc(cx["feature_available_at"], "feature_available_at")
    if (cx["data_window_end"] > cx["feature_available_at"]).any():
        raise ValueError("data_window_end > feature_available_at")
    invalid_states = sorted(set(cx["context_state"].astype(str)) - set(STATES))
    if invalid_states:
        raise ValueError(f"estados inválidos: {invalid_states}")
    if set(cx["context_model_id"].astype(str)) != {model_id}:
        raise ValueError("context_model_id no coincide con el checkpoint requerido")
    if cx["context_run_id"].astype(str).str.strip().eq("").any():
        raise ValueError("context_run_id vacío")
    if cx.duplicated(list(KEYS) + ["feature_available_at"]).any():
        raise ValueError("contexto duplicado para identidad+feature_available_at")

    probability_columns = ("p_calm", "p_normal", "p_volatile")
    present = tuple(c for c in probability_columns if c in cx.columns)
    if present and present != probability_columns:
        raise ValueError("posteriores incompletos")
    if present:
        p = cx[list(probability_columns)].to_numpy(dtype=float)
        if not np.isfinite(p).all() or np.any((p < 0) | (p > 1)):
            raise ValueError("posteriores fuera de [0,1]")
        if not np.allclose(p.sum(axis=1), 1.0, rtol=0, atol=1e-6):
            raise ValueError("posteriores no suman uno")

    tolerance = pd.Timedelta(max_feature_age)
    grouped = {
        tuple(key if isinstance(key, tuple) else (key,)): group.sort_values("feature_available_at")
        for key, group in cx.groupby(list(KEYS), sort=False, dropna=False)
    }
    states, runs, available, data_end, ages, ok, reasons = [], [], [], [], [], [], []
    post = {c: [] for c in present}
    for row in ev.itertuples(index=False):
        key = tuple(str(getattr(row, c)) for c in KEYS)
        group = grouped.get(key)
        if group is None:
            chosen = None
            reason = "NO_CONTEXT_KEY"
        else:
            times = group["feature_available_at"].astype("int64").to_numpy()
            event_ns = int(row.event_time.value)
            position = int(np.searchsorted(times, event_ns, side="right") - 1)
            if position < 0:
                chosen = None
                reason = "NO_PRIOR_CONTEXT"
            else:
                candidate = group.iloc[position]
                age = row.event_time - candidate["feature_available_at"]
                if age > tolerance:
                    chosen = candidate
                    reason = "STALE_CONTEXT"
                else:
                    chosen = candidate
                    reason = ""
        is_ok = chosen is not None and reason == ""
        ok.append(is_ok)
        reasons.append(reason)
        states.append(str(chosen["context_state"]) if is_ok else None)
        runs.append(str(chosen["context_run_id"]) if is_ok else None)
        available.append(chosen["feature_available_at"] if is_ok else pd.NaT)
        data_end.append(chosen["data_window_end"] if is_ok else pd.NaT)
        ages.append(int((row.event_time - chosen["feature_available_at"]).value) if chosen is not None else None)
        for col in present:
            post[col].append(float(chosen[col]) if is_ok else np.nan)

    out = ev.copy()
    out["context_state"] = pd.Series(states, dtype="string")
    out["context_feature_available_at"] = pd.to_datetime(available, utc=True)
    out["context_data_window_end"] = pd.to_datetime(data_end, utc=True)
    out["context_age_ns"] = pd.array(ages, dtype="Int64")
    out["context_model_id"] = pd.Series([model_id if value else None for value in ok], dtype="string")
    out["context_run_id"] = pd.Series(runs, dtype="string")
    out["context_as_of_ok"] = ok
    out["context_fail_reason"] = reasons
    for col, values in post.items():
        out[col] = values
    report = {
        "schema_version": "2.0.0",
        "model_id": model_id,
        "join": "backward_by_instrument_contract_cme_session",
        "max_feature_age": str(tolerance),
        "n_events": int(len(out)),
        "n_as_of_ok": int(out["context_as_of_ok"].sum()),
        "coverage": float(out["context_as_of_ok"].mean()) if len(out) else 0.0,
        "fail_reasons": {
            str(k): int(v) for k, v in out.loc[
                ~out["context_as_of_ok"], "context_fail_reason"
            ].value_counts().items()
        },
        "outcomes_accessed": False,
    }
    if require_complete and not bool(out["context_as_of_ok"].all()):
        raise ValueError(f"cobertura de contexto incompleta: {report['fail_reasons']}")
    return out, report
