#!/usr/bin/env python3
"""
GATE Paso 1 — Adaptador causal de contexto para eventos EdgeLab.

- Schema: gate_context_schema_v1.json
- Join: as_of backward only (feature_ts <= t0)
- Fail-closed si faltan features
- Sin outcomes
- Proveniencia: run_id, seed, model_id, commit

Uso típico:
  events = load_edgelab_export(...)  # columnas event_id, t0, session_id, ...
  bars   = load_bar_features(...)    # índice temporal monótono, features causales
  labels = label_events_at_t0(events, bars, model_id=..., seed=...)
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

SCHEMA_PATH = Path(__file__).resolve().parent / "gate_context_schema_v1.json"
SCHEMA_VERSION = "1.0.0"
REGIME_NAMES = {0: "calmo", 1: "normal", 2: "volatil", 3: "toxico"}

# model_id congelable (Paso 5 lo fijará; aquí default documentado)
DEFAULT_MODEL_ID = "gate_tf_causal_bal_v2_feat10_sticky90_vpin055"


@dataclass(frozen=True)
class RunProvenance:
    run_id: str
    seed: int
    model_id: str
    commit: str
    schema_version: str = SCHEMA_VERSION

    @staticmethod
    def create(seed: int, model_id: str, commit: str = "local") -> "RunProvenance":
        rid = uuid.uuid4().hex[:16]
        return RunProvenance(run_id=rid, seed=seed, model_id=model_id, commit=commit)


def load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def validate_events(events: pd.DataFrame) -> list[str]:
    """Devuelve lista de errores; vacía = OK."""
    schema = load_schema()
    required = ["event_id", "t0", "session_id"]
    errs = []
    for c in required:
        if c not in events.columns:
            errs.append(f"missing column: {c}")
    if errs:
        return errs
    if events["event_id"].duplicated().any():
        errs.append("event_id must be unique")
    if events["t0"].isna().any():
        errs.append("t0 has nulls")
    return errs


def _ensure_utc_ns(s: pd.Series) -> pd.Series:
    t = pd.to_datetime(s, utc=True)
    return t


def asof_regime_at_t0(
    events: pd.DataFrame,
    bar_index: pd.DatetimeIndex,
    regime_path: np.ndarray,
    posteriors: np.ndarray | None,
    vpin_path: np.ndarray | None,
    sticky_age: np.ndarray | None,
) -> pd.DataFrame:
    """
    Para cada evento, toma el último bar con ts <= t0.
    point-in-time / as-of; nunca mira el futuro.
    """
    if len(bar_index) != len(regime_path):
        raise ValueError("bar_index and regime_path length mismatch")

    bars = pd.DataFrame(
        {
            "ts": bar_index,
            "regime": regime_path.astype(np.int16),
        }
    ).sort_values("ts")
    if posteriors is not None:
        if posteriors.shape[0] != len(bar_index):
            raise ValueError("posteriors length mismatch")
        # esperar (T, 3) calmo/normal/vol
        bars["post_calmo"] = posteriors[:, 0]
        bars["post_normal"] = posteriors[:, 1]
        bars["post_volatil"] = posteriors[:, 2]
    else:
        bars["post_calmo"] = np.nan
        bars["post_normal"] = np.nan
        bars["post_volatil"] = np.nan
    if vpin_path is not None:
        bars["vpin"] = vpin_path
    else:
        bars["vpin"] = np.nan
    if sticky_age is not None:
        bars["sticky_age_bars"] = sticky_age
    else:
        bars["sticky_age_bars"] = -1

    ev = events.copy()
    ev["t0"] = _ensure_utc_ns(ev["t0"])
    bars["ts"] = pd.to_datetime(bars["ts"], utc=True)

    # merge_asof backward
    ev_sorted = ev.sort_values("t0")
    merged = pd.merge_asof(
        ev_sorted,
        bars,
        left_on="t0",
        right_on="ts",
        direction="backward",
    )
    # fail-closed: sin match → as_of_ok False
    merged["as_of_ok"] = merged["ts"].notna() & merged["regime"].notna()
    merged["fail_reason"] = np.where(merged["as_of_ok"], "", "no_bar_at_or_before_t0")
    merged["regime_name"] = merged["regime"].map(REGIME_NAMES)
    return merged


def label_events_at_t0(
    events: pd.DataFrame,
    bar_features: pd.DataFrame,
    *,
    regime_col: str = "regime",
    time_col: str = "time",
    post_cols: tuple[str, str, str] = ("post_calmo", "post_normal", "post_volatil"),
    vpin_col: str = "vpin",
    sticky_col: str = "sticky_age_bars",
    seed: int = 20260312,
    model_id: str = DEFAULT_MODEL_ID,
    commit: str = "local",
) -> pd.DataFrame:
    """
    API principal Paso 1.

    bar_features: DataFrame con columna temporal y régimen ya computado de forma causal
                  (el detector GATE corre sobre barras; este módulo solo etiqueta eventos).
    events: export EdgeLab con event_id, t0, session_id [, ancho_ticks].
    """
    errs = validate_events(events)
    if errs:
        raise ValueError("events invalid: " + "; ".join(errs))

    prov = RunProvenance.create(seed=seed, model_id=model_id, commit=commit)

    bf = bar_features.sort_values(time_col)
    idx = pd.DatetimeIndex(pd.to_datetime(bf[time_col], utc=True))
    regime = bf[regime_col].to_numpy()
    posts = None
    if all(c in bf.columns for c in post_cols):
        posts = bf[list(post_cols)].to_numpy(dtype=float)
    vpin = bf[vpin_col].to_numpy() if vpin_col in bf.columns else None
    sticky = bf[sticky_col].to_numpy() if sticky_col in bf.columns else None

    labeled = asof_regime_at_t0(events, idx, regime, posts, vpin, sticky)

    labeled["model_id"] = prov.model_id
    labeled["run_id"] = prov.run_id
    labeled["seed"] = prov.seed
    labeled["commit"] = prov.commit
    labeled["schema_version"] = prov.schema_version

    out_cols = [
        "event_id",
        "session_id",
        "t0",
        "regime",
        "regime_name",
        "post_calmo",
        "post_normal",
        "post_volatil",
        "vpin",
        "sticky_age_bars",
        "model_id",
        "run_id",
        "seed",
        "commit",
        "as_of_ok",
        "fail_reason",
    ]
    # preservar ancho si existe (Paso 2)
    if "ancho_ticks" in labeled.columns:
        out_cols.append("ancho_ticks")

    return labeled[[c for c in out_cols if c in labeled.columns]]


def demo_synthetic_roundtrip() -> dict[str, Any]:
    """Smoke test Paso 1 con datos sintéticos (sin EdgeLab real)."""
    from gate_generator_transformer import gen_latent_v2_target_budget
    from gate_recreate import generate_prices, BARS_PER_DAY
    from gate_five_proposals import enrich_features

    latent = gen_latent_v2_target_budget(BARS_PER_DAY)
    df = generate_prices(latent)
    df = enrich_features(df)
    # régimen proxy: latent como si viniera del detector (demo)
    df["regime"] = latent
    df["post_calmo"] = (latent == 0).astype(float)
    df["post_normal"] = (latent == 1).astype(float)
    df["post_volatil"] = (latent == 2).astype(float)
    age = np.zeros(len(df), dtype=int)
    for i in range(1, len(df)):
        age[i] = age[i - 1] + 1 if latent[i] == latent[i - 1] else 0
    df["sticky_age_bars"] = age

    # eventos sintéticos: cada 15 barras una "zona"
    rows = []
    for i in range(20, len(df), 15):
        rows.append(
            {
                "event_id": f"evt_{i}",
                "t0": df["time"].iloc[i],
                "session_id": "2026-03-12",
                "ancho_ticks": float(3 + (i % 5)),
            }
        )
    events = pd.DataFrame(rows)

    labels = label_events_at_t0(events, df, seed=20260312, commit="local-demo")
    n_ok = int(labels["as_of_ok"].sum())
    return {
        "n_events": len(labels),
        "n_as_of_ok": n_ok,
        "regime_counts": labels.loc[labels["as_of_ok"], "regime_name"]
        .value_counts()
        .to_dict(),
        "run_id": str(labels["run_id"].iloc[0]),
        "model_id": str(labels["model_id"].iloc[0]),
        "sample": labels.head(3).to_dict(orient="records"),
    }


def main():
    print("=== GATE Paso 1 — schema + adapter causal ===\n")
    schema = load_schema()
    print(f"Schema {schema['version']} — join: {schema['join_rules']['alignment']}")
    print(f"Forbidden: {schema['join_rules']['forbidden']}\n")

    result = demo_synthetic_roundtrip()
    print(f"Events: {result['n_events']} | as_of_ok: {result['n_as_of_ok']}")
    print(f"Regimes: {result['regime_counts']}")
    print(f"run_id={result['run_id']} model_id={result['model_id']}")

    out = Path(__file__).resolve().parent / "gate_paso1_demo_labels.json"
    out.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    print(f"\nDemo labels: {out}")
    print("Paso 1 smoke: OK")


if __name__ == "__main__":
    main()
