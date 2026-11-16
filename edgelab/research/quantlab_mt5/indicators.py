"""Cargador causal pre-holdout, resampleo OHLC e indicadores exactos de MetaTrader 5.

Nota clave verificada contra Strategy Tester build 5956:
En MQL5, `iATR(symbol, tf, period)` calcula la media movil SIMPLE (`SMA`) del True Range
sobre `period` barras, a diferencia del suavizado RMA de Wilder usado en TradingView/MT4.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Iterable, Optional
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

_TZ_UTC = ZoneInfo("UTC")
from edgelab.holdout import HOLDOUT_APERTURA_UTC_ISO  # noqa: E402  (frontera única; 2026-11-16: antes "2026-10-01" UTC dejaba pasar 2 h del holdout)
DEFAULT_PRE_HOLDOUT_END = HOLDOUT_APERTURA_UTC_ISO


def check_anti_holdout(path: str | Path, allow_sellado: bool = False) -> Path:
    """Bloquea por defecto cualquier ruta que contenga 'sellado' (guardia anti-holdout)."""
    raw = str(path)
    p = Path(path)
    if allow_sellado:
        return p
    resolved = str(p.resolve()) if os.path.exists(raw) else os.path.abspath(raw)
    for candidate in (raw, os.path.normpath(raw), resolved):
        parts = Path(candidate.lower().replace("/", os.sep).replace("\\", os.sep)).parts
        if any("sellado" in part for part in parts):
            raise ValueError(
                f"Guardia anti-holdout bloqueo la ruta protegida 'sellado': {path!r}. "
                "Pase allow_sellado=True unicamente para validacion final autorizada."
            )
    return p


def _parse_bound_utc(val: Optional[str | pd.Timestamp], tz_input: str | ZoneInfo) -> Optional[pd.Timestamp]:
    if val is None:
        return None
    ts = pd.Timestamp(val)
    if ts.tzinfo is None:
        tz = _TZ_UTC if str(tz_input).upper() == "UTC" else ZoneInfo(str(tz_input))
        ts = ts.tz_localize(tz)
    return ts.tz_convert(_TZ_UTC)


def _normalize_frame_columns(df: pd.DataFrame, tz_input: str | ZoneInfo) -> pd.DataFrame:
    cols_lower = {c.lower().strip(): c for c in df.columns}
    if "ts_ns" in cols_lower:
        ts_idx = pd.to_datetime(df[cols_lower["ts_ns"]], unit="ns", utc=True)
    elif "date" in cols_lower and "time" in cols_lower:
        raw_dt = df[cols_lower["date"]].astype(str).str.strip() + " " + df[cols_lower["time"]].astype(str).str.strip()
        ts_idx = pd.to_datetime(raw_dt, format="mixed", errors="raise")
    elif "time" in cols_lower:
        ts_idx = pd.to_datetime(df[cols_lower["time"]], format="mixed", errors="raise")
    elif "timestamp" in cols_lower:
        ts_idx = pd.to_datetime(df[cols_lower["timestamp"]], format="mixed", errors="raise")
    elif "datetime" in cols_lower:
        ts_idx = pd.to_datetime(df[cols_lower["datetime"]], format="mixed", errors="raise")
    else:
        raise KeyError(f"No se encontro columna temporal en {list(df.columns)}")

    if getattr(ts_idx.dt, "tz", None) is None:
        tz = _TZ_UTC if str(tz_input).upper() == "UTC" else ZoneInfo(str(tz_input))
        ts_idx = ts_idx.dt.tz_localize(tz)
    ts_utc = ts_idx.dt.tz_convert(_TZ_UTC)

    out = pd.DataFrame({
        "time": ts_utc,
        "ts_ns": ts_utc.astype("datetime64[ns, UTC]").astype("int64"),
        "open": df[cols_lower["open"]].to_numpy(dtype=np.float64),
        "high": df[cols_lower["high"]].to_numpy(dtype=np.float64),
        "low": df[cols_lower["low"]].to_numpy(dtype=np.float64),
        "close": df[cols_lower["close"]].to_numpy(dtype=np.float64),
        "volume": df[cols_lower["volume"]].to_numpy(dtype=np.float64) if "volume" in cols_lower else np.ones(len(df), dtype=np.float64),
    })
    return out.sort_values("ts_ns").reset_index(drop=True)


def load_ohlc_data(
    path: str | Path,
    start: Optional[str] = None,
    end: Optional[str] = None,
    tz_input: str | ZoneInfo = "UTC",
    allow_sellado: bool = False,
    enforce_pre_holdout: bool = True,
) -> pd.DataFrame:
    """Carga datos OHLCV (CSV, Parquet o JSON) aplicando guardia anti-holdout y recorte temporal causal."""
    p = check_anti_holdout(path, allow_sellado=allow_sellado)
    if not p.exists():
        raise FileNotFoundError(f"No existe el archivo de datos: {p}")

    start_ts = _parse_bound_utc(start, tz_input)
    end_ts = _parse_bound_utc(end, tz_input)
    if enforce_pre_holdout and not allow_sellado:
        cap = pd.Timestamp(DEFAULT_PRE_HOLDOUT_END, tz="UTC")
        if end_ts is None or end_ts > cap:
            end_ts = cap

    suffix = p.suffix.lower()
    if suffix == ".parquet":
        raw_df = pd.read_parquet(p)
        df = _normalize_frame_columns(raw_df, tz_input)
    elif suffix == ".json":
        obj = json.loads(p.read_text(encoding="utf-8"))
        rows = obj.get("history", obj) if isinstance(obj, dict) else obj
        df = _normalize_frame_columns(pd.DataFrame(rows), tz_input)
    else:
        # Lectura por chunks para soportar CSVs grandes de Dukascopy (450+ MB) filtrando fechas temprano
        first = pd.read_csv(p, nrows=2)
        has_ymd_col = any(c.lower().strip() == "date" for c in first.columns)
        start_ymd = int(start_ts.strftime("%Y%m%d")) if (has_ymd_col and start_ts is not None and str(first.iloc[0, 0]).isdigit()) else None
        end_ymd = int(end_ts.strftime("%Y%m%d")) if (has_ymd_col and end_ts is not None and str(first.iloc[0, 0]).isdigit()) else None

        parts: list[pd.DataFrame] = []
        for chunk in pd.read_csv(p, chunksize=500_000):
            if start_ymd is not None:
                chunk = chunk[chunk.iloc[:, 0].astype(np.int64) >= start_ymd]
            if end_ymd is not None:
                chunk = chunk[chunk.iloc[:, 0].astype(np.int64) <= end_ymd]
            if not chunk.empty:
                parts.append(chunk)
        raw_df = pd.concat(parts, ignore_index=True) if parts else first.iloc[0:0]
        df = _normalize_frame_columns(raw_df, tz_input)

    if start_ts is not None:
        df = df[df["time"] >= start_ts]
    if end_ts is not None:
        df = df[df["time"] < end_ts]
    return df.reset_index(drop=True)


def resample_ohlc(df: pd.DataFrame, timeframe_min: int) -> pd.DataFrame:
    """Resamplea barras OHLCV a M5 (5), H1 (60), H4 (240) o D1 (1440) respetando apertura de barra."""
    if df.empty:
        return df.copy()
    work = df.copy()
    if "time" not in work.columns:
        work["time"] = pd.to_datetime(work["ts_ns"], unit="ns", utc=True)
    else:
        work["time"] = pd.to_datetime(work["time"], utc=True).astype("datetime64[ns, UTC]")
    work["ts_ns"] = work["time"].astype("int64")

    if len(work) >= 2:
        diffs = work["ts_ns"].diff().dropna()
        med_sec = float(diffs.median()) / 1e9 if len(diffs) else 0.0
        if timeframe_min * 60 == round(med_sec):
            return work.sort_values("ts_ns").reset_index(drop=True)

    bucket_ns = int(timeframe_min) * 60 * 1_000_000_000
    keys = (work["ts_ns"].to_numpy(dtype=np.int64) // bucket_ns) * bucket_ns
    work["_bucket"] = keys
    agg = work.groupby("_bucket", sort=True, as_index=False).agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        volume=("volume", "sum"),
    )
    agg = agg.rename(columns={"_bucket": "ts_ns"})
    agg["time"] = pd.to_datetime(agg["ts_ns"], unit="ns", utc=True)
    return agg[["time", "ts_ns", "open", "high", "low", "close", "volume"]].reset_index(drop=True)


def mql5_sma(values: Iterable[float], period: int) -> np.ndarray:
    """Media movil simple causal (`MODE_SMA`). Los primeros `period-1` valores son `NaN`."""
    arr = np.asarray(values, dtype=np.float64)
    out = np.full(len(arr), np.nan, dtype=np.float64)
    if period <= 0 or len(arr) < period:
        return out
    csum = np.cumsum(np.insert(arr, 0, 0.0))
    out[period - 1 :] = (csum[period:] - csum[:-period]) / float(period)
    return out


def mql5_ema(values: Iterable[float], period: int) -> np.ndarray:
    """Media movil exponencial causal (`MODE_EMA`, alpha = 2 / (period + 1))."""
    arr = np.asarray(values, dtype=np.float64)
    out = np.full(len(arr), np.nan, dtype=np.float64)
    if period <= 0 or len(arr) == 0:
        return out
    alpha = 2.0 / (period + 1.0)
    one_m = 1.0 - alpha
    cur = float(arr[0])
    out[0] = cur
    for i in range(1, len(arr)):
        cur = float(arr[i]) * alpha + cur * one_m
        out[i] = cur
    return out


def mql5_true_range(high: Iterable[float], low: Iterable[float], close: Iterable[float]) -> np.ndarray:
    """True Range barra a barra (`max(H-L, |H-prevC|, |L-prevC|)`)."""
    h = np.asarray(high, dtype=np.float64)
    l = np.asarray(low, dtype=np.float64)
    c = np.asarray(close, dtype=np.float64)
    if len(h) == 0:
        return np.empty(0, dtype=np.float64)
    tr = np.empty(len(h), dtype=np.float64)
    tr[0] = h[0] - l[0]
    if len(h) > 1:
        pc = c[:-1]
        tr[1:] = np.maximum(h[1:] - l[1:], np.maximum(np.abs(h[1:] - pc), np.abs(l[1:] - pc)))
    return tr


def mql5_atr(high: Iterable[float], low: Iterable[float], close: Iterable[float], period: int = 14) -> np.ndarray:
    """Replica exacta de `iATR` de MQL5 (SMA del True Range sobre `period` barras)."""
    tr = mql5_true_range(high, low, close)
    return mql5_sma(tr, period)


def compute_lot_size(
    balance: float,
    sl_dist: float,
    risk_mode: int,
    risk_percent: float,
    risk_money: float,
    fixed_lot: float,
    usd_per_price_unit: float,
    min_lot: float,
    lot_step: float,
    max_lot: float,
    allow_min_fallback: bool = True,
    risk_multiplier: float = 1.0,
) -> float:
    """Dimensionamiento unificado de lotes compartiendo modos 0 (%), 1 (USD) y 2 (fijo)."""
    if risk_mode == 2:
        steps = int(fixed_lot // lot_step)
        return min(max_lot, max(min_lot, round(steps * lot_step, 4)))
    if sl_dist <= 0 or usd_per_price_unit <= 0:
        return 0.0
    risk_cash = (balance * (risk_percent / 100.0) if risk_mode == 0 else risk_money) * risk_multiplier
    raw = risk_cash / (sl_dist * usd_per_price_unit)
    if raw < min_lot:
        return min_lot if allow_min_fallback else 0.0
    steps = int(raw // lot_step)
    lots = round(steps * lot_step, 4)
    return min(max_lot, max(min_lot, lots))
