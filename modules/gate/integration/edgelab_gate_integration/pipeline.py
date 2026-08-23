#!/usr/bin/env python3
"""
Pipeline de integración EdgeLab → GATE labels → target-free report.

Uso:
  python -m edgelab_gate_integration.pipeline \\
      --events path/to/export.csv \\
      --bars path/to/bars.csv \\
      --out-dir runs/gate_labels

Si --bars no trae columna regime, se calcula un régimen proxy target-free
(solo para cableado; en producción pasar barras ya detectadas causalmente).
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

# permitir import desde artifacts/
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from gate_adapter import (  # noqa: E402
    DEFAULT_MODEL_ID,
    label_events_at_t0,
    load_schema,
)
from gate_target_free import target_free_report  # noqa: E402

from .column_map import normalize_bar_time, normalize_events  # noqa: E402


def _load_table(path: Path) -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    if path.suffix.lower() in {".parquet", ".pq"}:
        return pd.read_parquet(path)
    if path.suffix.lower() in {".csv", ".txt"}:
        return pd.read_csv(path)
    if path.suffix.lower() in {".json", ".jsonl"}:
        if path.suffix.lower() == ".jsonl":
            return pd.read_json(path, lines=True)
        return pd.read_json(path)
    raise ValueError(f"unsupported format: {path.suffix}")


def _ensure_regime_on_bars(bars: pd.DataFrame) -> pd.DataFrame:
    """Si no hay regime, proxy por cuantiles de rvol/ret (solo cableado)."""
    if "regime" in bars.columns:
        return bars
    b = bars.copy()
    if "rvol" in b.columns:
        x = b["rvol"].astype(float)
    elif "ret" in b.columns:
        x = b["ret"].astype(float).rolling(15, min_periods=5).std()
    elif "mid" in b.columns:
        x = np.abs(np.diff(b["mid"].astype(float), prepend=b["mid"].iloc[0]))
        x = pd.Series(x).rolling(15, min_periods=5).std()
    else:
        # constante normal
        b["regime"] = 1
        b["post_calmo"] = 0.0
        b["post_normal"] = 1.0
        b["post_volatil"] = 0.0
        b["vpin"] = 0.5
        b["sticky_age_bars"] = 0
        return b

    x = pd.Series(x).ffill().fillna(0.0)
    q1, q2 = np.nanquantile(x, [0.33, 0.66])
    reg = np.zeros(len(b), dtype=int)
    reg[x.values > q1] = 1
    reg[x.values > q2] = 2
    b["regime"] = reg
    b["post_calmo"] = (reg == 0).astype(float)
    b["post_normal"] = (reg == 1).astype(float)
    b["post_volatil"] = (reg == 2).astype(float)
    if "vpin" not in b.columns:
        b["vpin"] = 0.5
    age = np.zeros(len(b), dtype=int)
    for i in range(1, len(b)):
        age[i] = age[i - 1] + 1 if reg[i] == reg[i - 1] else 0
    b["sticky_age_bars"] = age
    return b


def run_integration_pipeline(
    events_path: Path,
    bars_path: Path,
    out_dir: Path,
    *,
    seed: int = 20260823,
    model_id: str = DEFAULT_MODEL_ID,
    commit: str = "local",
    default_symbol: str = "ES",
) -> dict[str, Any]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    raw_events = _load_table(events_path)
    raw_bars = _load_table(bars_path)

    events = normalize_events(raw_events, default_symbol=default_symbol)
    bars = normalize_bar_time(raw_bars)
    bars = _ensure_regime_on_bars(bars)

    labels = label_events_at_t0(
        events,
        bars,
        seed=seed,
        model_id=model_id,
        commit=commit,
    )

    run_id = str(labels["run_id"].iloc[0]) if len(labels) else uuid.uuid4().hex[:16]

    # target-free on bar path if regime present
    tf = target_free_report(
        regime_path=bars["regime"].to_numpy() if "regime" in bars.columns else None,
        labels=labels,
    )

    labels_path = out_dir / f"gate_labels_{run_id}.csv"
    labels.to_csv(labels_path, index=False)

    artifact = {
        "schema_version": "edgelab_gate_integration_v1",
        "run_id": run_id,
        "seed": seed,
        "model_id": model_id,
        "commit": commit,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "events": str(Path(events_path).resolve()),
            "bars": str(Path(bars_path).resolve()),
            "n_events_in": int(len(events)),
            "n_bars": int(len(bars)),
        },
        "outputs": {
            "labels_csv": str(labels_path.resolve()),
            "n_labels": int(len(labels)),
            "n_as_of_ok": int(labels["as_of_ok"].sum()) if len(labels) else 0,
        },
        "target_free": tf,
        "gate_schema": load_schema().get("version"),
        "notes": [
            "Join as-of backward at event t0 only.",
            "If bars lacked regime, a quantile proxy was used (replace with real GATE detector for formal runs).",
            "No outcomes accessed.",
        ],
    }

    art_path = out_dir / f"gate_integration_{run_id}.json"
    art_path.write_text(json.dumps(artifact, indent=2, default=str), encoding="utf-8")
    artifact["outputs"]["artifact_json"] = str(art_path.resolve())
    # rewrite with full paths
    art_path.write_text(json.dumps(artifact, indent=2, default=str), encoding="utf-8")
    return artifact


def _write_fixture(out: Path) -> tuple[Path, Path]:
    """Fixtures mínimos si no hay EdgeLab montado."""
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(0)
    n = 120
    times = pd.date_range("2026-03-12 14:30", periods=n, freq="1min", tz="UTC")
    mid = 5200 + np.cumsum(rng.normal(0, 0.3, n))
    bars = pd.DataFrame(
        {
            "time": times,
            "mid": mid,
            "rvol": pd.Series(np.abs(rng.normal(0.2, 0.1, n))).rolling(10, min_periods=1).mean(),
            "vpin": np.clip(rng.normal(0.45, 0.1, n), 0, 1),
        }
    )
    # events every 8 bars
    ev = []
    for i in range(10, n, 8):
        ev.append(
            {
                "zone_id": f"Z{i}",
                "t_start": times[i].isoformat(),
                "trade_date": "2026-03-12",
                "Symbol": "ES",
                "width_ticks": float(3 + i % 4),
            }
        )
    events = pd.DataFrame(ev)
    bp = out / "fixture_bars.csv"
    ep = out / "fixture_events_edgelab_aliases.csv"
    bars.to_csv(bp, index=False)
    events.to_csv(ep, index=False)
    return ep, bp


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="EdgeLab → GATE integration pipeline")
    p.add_argument("--events", type=str, default=None, help="CSV/parquet export eventos")
    p.add_argument("--bars", type=str, default=None, help="CSV/parquet barras con features")
    p.add_argument("--out-dir", type=str, default=str(_ROOT / "runs_gate_labels"))
    p.add_argument("--seed", type=int, default=20260823)
    p.add_argument("--model-id", type=str, default=DEFAULT_MODEL_ID)
    p.add_argument("--commit", type=str, default="local")
    p.add_argument("--fixture", action="store_true", help="Generar y usar fixtures alias EdgeLab")
    args = p.parse_args(argv)

    if args.fixture or not args.events or not args.bars:
        fix_dir = Path(args.out_dir) / "_fixtures"
        ep, bp = _write_fixture(fix_dir)
        print(f"Using fixtures:\n  events={ep}\n  bars={bp}")
        events_path, bars_path = ep, bp
    else:
        events_path, bars_path = Path(args.events), Path(args.bars)

    art = run_integration_pipeline(
        events_path,
        bars_path,
        Path(args.out_dir),
        seed=args.seed,
        model_id=args.model_id,
        commit=args.commit,
    )
    print(json.dumps({k: art[k] for k in ("run_id", "model_id", "outputs", "target_free")}, indent=2, default=str))
    print(f"\nOK — artifact: {art['outputs'].get('artifact_json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
