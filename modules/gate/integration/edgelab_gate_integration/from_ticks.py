#!/usr/bin/env python3
"""
Ingesta del parquet tick EdgeLab (schema ts_utc_ns / price_ticks / aggressor)
→ barras 1m → features causales → regime proxy → eventos sintéticos de prueba
→ pipeline GATE labels + target-free.

El parquet de muestra es 6E 09-26 (no ES zonas); sirve para validar el cableado
sobre el schema real de intake del lab.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from edgelab_gate_integration.pipeline import run_integration_pipeline


def load_ticks(path: Path, max_rows: int | None = 500_000) -> pd.DataFrame:
    pf = pq.ParquetFile(path)
    if max_rows is None:
        t = pf.read()
    else:
        # leer row groups hasta max_rows
        tables = []
        n = 0
        for i in range(pf.metadata.num_row_groups):
            rg = pf.read_row_group(i)
            tables.append(rg)
            n += rg.num_rows
            if n >= max_rows:
                break
        import pyarrow as pa

        t = pa.concat_tables(tables)
        if t.num_rows > max_rows:
            t = t.slice(0, max_rows)
    df = t.to_pandas()
    df["ts"] = pd.to_datetime(df["ts_utc_ns"], unit="ns", utc=True)
    return df.sort_values("ts").reset_index(drop=True)


def ticks_to_bars_1m(ticks: pd.DataFrame) -> pd.DataFrame:
    """OHLC mid + volume + signed volume + spread en barras 1m."""
    t = ticks.copy()
    mid_ticks = (t["bid_ticks"].astype(float) + t["ask_ticks"].astype(float)) / 2.0
    t["mid"] = mid_ticks  # en ticks de precio del contrato
    t["spread_ticks"] = (t["ask_ticks"] - t["bid_ticks"]).astype(float)
    sign = np.where(t["aggressor"].astype(str).str.lower().values == "buy", 1.0, -1.0)
    # unknown aggressor → 0
    agg = t["aggressor"].astype(str).str.lower()
    sign = np.where(agg == "buy", 1.0, np.where(agg == "sell", -1.0, 0.0))
    t["signed_vol"] = sign * t["volume"].astype(float)
    t = t.set_index("ts")

    ohlc = t["mid"].resample("1min").ohlc()
    ohlc.columns = ["open", "high", "low", "close"]
    vol = t["volume"].resample("1min").sum().rename("volume")
    signed = t["signed_vol"].resample("1min").sum().rename("signed")
    spread = t["spread_ticks"].resample("1min").mean().rename("spread")
    n_ticks = t["mid"].resample("1min").count().rename("n_ticks")

    bars = pd.concat([ohlc, vol, signed, spread, n_ticks], axis=1).dropna(subset=["close"])
    bars["mid"] = bars["close"]
    bars["ret"] = bars["mid"].diff()
    bars["rvol"] = bars["ret"].rolling(15, min_periods=5).std()
    # OFI proxy: signed volume z
    s = bars["signed"].fillna(0.0)
    mu = s.rolling(20, min_periods=5).mean()
    sd = s.rolling(20, min_periods=5).std().replace(0, np.nan)
    bars["ofi_z"] = ((s - mu) / sd).shift(1)  # causal: usa stats hasta t-1 conceptual simple
    bars["tape_imb"] = (s / bars["volume"].replace(0, np.nan)).clip(-1, 1)
    bars["vpin"] = bars["tape_imb"].abs().rolling(30, min_periods=5).mean()
    bars["er"] = _efficiency_ratio(bars["mid"].values, 10)
    bars = bars.reset_index().rename(columns={"ts": "time"})
    return bars


def _efficiency_ratio(mid: np.ndarray, win: int = 10) -> np.ndarray:
    out = np.full(len(mid), np.nan)
    for i in range(win, len(mid)):
        net = abs(mid[i] - mid[i - win])
        path = np.sum(np.abs(np.diff(mid[i - win : i + 1])))
        out[i] = net / path if path > 1e-12 else 0.0
    return out


def events_from_bars(bars: pd.DataFrame, every: int = 12) -> pd.DataFrame:
    """Eventos sintéticos estilo export (para ejercitar alias map)."""
    rows = []
    for i in range(20, len(bars), every):
        rows.append(
            {
                "zone_id": f"6E_Z{i}",
                "t_start": bars["time"].iloc[i],
                "trade_date": str(bars["time"].iloc[i])[:10],
                "Symbol": "6E",
                "width_ticks": float(2 + (i % 5)),
            }
        )
    return pd.DataFrame(rows)


def main():
    sample = _ROOT / "edgelab_sample" / "sample.parquet"
    if not sample.exists():
        raise SystemExit(f"missing {sample}")

    print(f"Loading ticks from {sample} (cap 400k for speed)...")
    ticks = load_ticks(sample, max_rows=400_000)
    print(f"  ticks={len(ticks)} instrument={ticks['instrument'].iloc[0]} contract={ticks['contract'].iloc[0]}")
    print(f"  range {ticks['ts'].iloc[0]} → {ticks['ts'].iloc[-1]}")

    bars = ticks_to_bars_1m(ticks)
    print(f"  bars_1m={len(bars)}")

    events = events_from_bars(bars)
    out = _ROOT / "runs_gate_labels" / "from_real_ticks"
    out.mkdir(parents=True, exist_ok=True)
    ep = out / "events_from_6e.csv"
    bp = out / "bars_1m_6e.csv"
    events.to_csv(ep, index=False)
    bars.to_csv(bp, index=False)

    art = run_integration_pipeline(
        ep,
        bp,
        out,
        seed=20260823,
        commit="drive-sample-6e",
        default_symbol="6E",
    )
    summary = {
        "instrument": "6E",
        "contract": str(ticks["contract"].iloc[0]),
        "n_ticks_used": int(len(ticks)),
        "n_bars": int(len(bars)),
        "n_events": int(len(events)),
        "run_id": art["run_id"],
        "n_as_of_ok": art["outputs"]["n_as_of_ok"],
        "target_free_minutes": art["target_free"].get("bar_path", {}).get("minutes_by_regime"),
        "corr_ancho_verdict": art["target_free"]
        .get("event_labels", {})
        .get("corr_with_ancho", {})
        .get("verdict"),
        "labels_csv": art["outputs"]["labels_csv"],
        "artifact_json": art["outputs"]["artifact_json"],
    }
    print(json.dumps(summary, indent=2))
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\nOK — {out}")


if __name__ == "__main__":
    main()
