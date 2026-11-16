"""Base data loading, causal NinjaTrader 8 multi-series builder, and exact NT8 indicators.

Constructs causally all ten strategy data series (``bip1`` .. ``bip10``) defined in
``FUNDEDSYNCSTACK.OnStateChange(State.Configure)`` with exact ``America/Chicago`` and
``America/New_York`` DST conversions via ``zoneinfo.ZoneInfo``:

- ``bip1``: 1m ETH (``CME US Index Futures ETH``, 17:00 prev -> 16:00 CT, no 16:00-17:00 break/weekends)
- ``bip2``: 3m ETH
- ``bip3``: 5m ETH
- ``bip4``: 20m ETH
- ``bip5``: 1m US STOCK (``09:30-16:15 ET`` per bundled ``US STOCK.xml``, configurable to ``160000``)
- ``bip6``: 5m RTH (``CME US Index Futures RTH``, ``08:30-15:15 CT`` / ``09:30-16:15 ET``)
- ``bip7``: 1d RTH (daily RTH session bars)
- ``bip8``: 1d ETH (daily CME ETH session bars aligned by ``trade_date``)
- ``bip9``: 10m ETH
- ``bip10``: 15m ETH

All bar timestamps stored in ``BarSeries.ts_ns`` represent the NinjaTrader bar **close** timestamp
in UTC nanoseconds.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Mapping
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

try:
    from .contracts import (
        BarSeries,
        MultiSeriesContext,
        POINT_VALUE_NQ,
        TICK_SIZE_NQ,
    )
except ImportError:  # pragma: no cover - direct import fallback
    from contracts import (
        BarSeries,
        MultiSeriesContext,
        POINT_VALUE_NQ,
        TICK_SIZE_NQ,
    )

_NS_PER_SEC: int = 1_000_000_000
_NS_PER_MIN: int = 60 * _NS_PER_SEC
_TZ_UTC = ZoneInfo("UTC")
_TZ_CT = ZoneInfo("America/Chicago")
_TZ_ET = ZoneInfo("America/New_York")
_NT_APPROX_EPS: float = 1e-9  # Verified in NinjaTrader.Core.FloatingPoint.MathExtentions.ApproxCompare


def _assert_not_sellado(path: str | Path, allow_sellado: bool) -> Path:
    """Prevent accidental loading of sealed holdout files unless explicitly authorized."""
    raw = str(path)
    p = Path(path)
    if allow_sellado:
        return p
    resolved = str(p.resolve()) if os.path.exists(raw) else os.path.abspath(raw)
    checks = (raw, os.path.normpath(raw), resolved)
    for candidate in checks:
        lower = candidate.lower().replace("/", os.sep).replace("\\", os.sep)
        parts = Path(lower).parts
        if any(part == "sellado" or "sellado" in part for part in parts):
            raise ValueError(
                f"Anti-holdout guard blocked protected 'sellado' path: {path!r}. "
                "Pass allow_sellado=True only for an authorized final validation."
            )
    return p


def _normalize_tz(tz_name: str | ZoneInfo) -> ZoneInfo | str:
    """Return a ZoneInfo or valid timezone descriptor."""
    if isinstance(tz_name, ZoneInfo):
        return tz_name
    key = str(tz_name).strip()
    if key.upper() == "UTC":
        return _TZ_UTC
    return ZoneInfo(key)


def _parse_single_timestamp_ns(value: Any, tz_input: str | ZoneInfo) -> int:
    """Convert a scalar timestamp bound (str, datetime, int/float epoch) to UTC int64 ns."""
    if isinstance(value, (int, np.integer)):
        iv = int(value)
        av = abs(iv)
        if av < 10**11:
            return iv * _NS_PER_SEC
        if av < 10**14:
            return iv * 1_000_000
        if av < 10**17:
            return iv * 1_000
        return iv
    if isinstance(value, (float, np.floating)):
        return int(round(float(value) * _NS_PER_SEC))

    ts = pd.Timestamp(value)
    if ts.tzinfo is None:
        ts = ts.tz_localize(_normalize_tz(tz_input))
    ts = ts.tz_convert(_TZ_UTC).as_unit("ns")
    return int(ts.value)


def _parse_timestamps_to_utc_ns(series: pd.Series, tz_input: str | ZoneInfo) -> np.ndarray:
    """Vectorized parsing of numeric/string/datetime timestamps into UTC int64 nanoseconds."""
    if len(series) == 0:
        return np.empty(0, dtype=np.int64)

    if pd.api.types.is_datetime64_any_dtype(series.dtype):
        dt = pd.DatetimeIndex(series)
        if dt.tz is None:
            dt = dt.tz_localize(_normalize_tz(tz_input))
        return dt.tz_convert(_TZ_UTC).as_unit("ns").asi8.copy()

    if pd.api.types.is_integer_dtype(series.dtype):
        arr = series.to_numpy(dtype=np.int64, copy=False)
        med = int(np.median(np.abs(arr)))
        if med < 10**11:
            return arr * _NS_PER_SEC
        if med < 10**14:
            return arr * 1_000_000
        if med < 10**17:
            return arr * 1_000
        return arr.copy()

    if pd.api.types.is_float_dtype(series.dtype):
        arr = series.to_numpy(dtype=np.float64, copy=False)
        med = float(np.nanmedian(np.abs(arr)))
        if med < 1e11:
            return np.rint(arr * _NS_PER_SEC).astype(np.int64)
        if med < 1e14:
            return np.rint(arr * 1_000_000.0).astype(np.int64)
        if med < 1e17:
            return np.rint(arr * 1_000.0).astype(np.int64)
        return np.rint(arr).astype(np.int64)

    dt = pd.DatetimeIndex(pd.to_datetime(series, errors="raise"))
    if dt.tz is None:
        dt = dt.tz_localize(_normalize_tz(tz_input))
    return dt.tz_convert(_TZ_UTC).as_unit("ns").asi8.copy()


def _detect_csv_delimiter(path: Path) -> tuple[str, bool]:
    """Inspect the first non-empty line of a CSV/TXT file to detect separator and header."""
    with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
        first_line = ""
        for line in f:
            stripped = line.strip()
            if stripped:
                first_line = stripped
                break
    if not first_line:
        raise ValueError(f"Empty CSV/text file: {path}")

    for sep in (";", ",", "\t"):
        if sep in first_line:
            break
    else:
        sep = ","

    tokens = [tok.strip().lower() for tok in first_line.split(sep)]
    header_keywords = {"date", "time", "open", "high", "low", "close", "volume", "o", "h", "l", "c", "v", "t", "ts"}
    has_header = any(tok in header_keywords or any(ch.isalpha() for ch in tok) for tok in tokens)
    return sep, has_header


def _read_source_table(source: str | Path | pd.DataFrame | Mapping[str, Any]) -> pd.DataFrame:
    """Load DataFrame, EdgeLab ctx mapping, Parquet, or CSV file into a raw DataFrame."""
    if isinstance(source, pd.DataFrame):
        return source
    if isinstance(source, Mapping):
        return pd.DataFrame(dict(source))
    if isinstance(source, (str, Path)):
        path = Path(source)
        suffix = path.suffix.lower()
        if suffix in {".parquet", ".pq"}:
            return pd.read_parquet(path)
        sep, has_header = _detect_csv_delimiter(path)
        if has_header:
            return pd.read_csv(path, sep=sep)
        raw = pd.read_csv(path, sep=sep, header=None)
        if raw.shape[1] == 7:
            raw.columns = ["date", "time", "open", "high", "low", "close", "volume"]
        elif raw.shape[1] == 8:
            raw.columns = ["date", "time", "open", "high", "low", "close", "volume", "delta"]
        elif raw.shape[1] == 6:
            raw.columns = ["ts", "open", "high", "low", "close", "volume"]
        else:
            raise ValueError(f"Unsupported headerless CSV column count ({raw.shape[1]}) in {path}")
        return raw
    raise TypeError(f"Unsupported M1 data source type: {type(source).__name__}")


def _resolve_columns(df: pd.DataFrame, tz_input: str | ZoneInfo) -> tuple[np.ndarray, pd.DataFrame, bool]:
    """Normalize OHLCV (+ optional delta) and extract UTC int64 nanosecond timestamps."""
    col_map = {str(c).strip().lower(): c for c in df.columns}

    def pick(*aliases: str) -> str | None:
        for alias in aliases:
            if alias in col_map:
                return col_map[alias]
        return None

    c_ts = pick("ts_ns", "ts", "t", "ts_utc", "timestamp", "datetime", "time_utc", "date_time")
    if c_ts is not None:
        ts_ns = _parse_timestamps_to_utc_ns(df[c_ts], tz_input)
    else:
        c_date = pick("date", "fecha")
        c_time = pick("time", "hora")
        if c_date is not None and c_time is not None:
            d_str = df[c_date].astype(str).str.strip().str.replace(".", "-", regex=False)
            t_str = df[c_time].astype(str).str.strip()
            # Handle numeric HHMMSS without colons (e.g. 0, 100, 83000, 083000) cleanly
            if pd.api.types.is_integer_dtype(df[c_time]) or t_str.str.fullmatch(r"\d{5,6}").all():
                t_padded = t_str.str.zfill(6)
                t_str = t_padded.str[0:2] + ":" + t_padded.str[2:4] + ":" + t_padded.str[4:6]
            if d_str.str.fullmatch(r"\d{8}").all():
                d_str = d_str.str[0:4] + "-" + d_str.str[4:6] + "-" + d_str.str[6:8]
            combined = d_str + " " + t_str
            ts_ns = _parse_timestamps_to_utc_ns(combined, tz_input)
        else:
            raise ValueError(
                "Input data must provide either a timestamp column (t/ts/ts_ns/timestamp/datetime) "
                "or separate Date + Time columns."
            )

    def req_col(label: str, *aliases: str) -> np.ndarray:
        col = pick(*aliases)
        if col is None:
            raise ValueError(f"Missing required column for {label} (aliases={aliases}) in columns {list(df.columns)}")
        return df[col].to_numpy(dtype=np.float64, copy=False)

    out = pd.DataFrame(
        {
            "ts_ns": ts_ns,
            "open": req_col("open", "o", "open"),
            "high": req_col("high", "h", "high"),
            "low": req_col("low", "l", "low"),
            "close": req_col("close", "c", "close"),
            "volume": req_col("volume", "v", "vol", "volume"),
        }
    )
    c_delta = pick("delta", "bar_delta", "d")
    has_real_delta = c_delta is not None
    if has_real_delta:
        out["delta"] = df[c_delta].to_numpy(dtype=np.float64, copy=False)
    return ts_ns, out, has_real_delta


def load_m1_data(
    source: str | Path | pd.DataFrame | Mapping[str, Any],
    start: Any = None,
    end: Any = None,
    tz_input: str = "UTC",
    *,
    allow_sellado: bool = False,
    end_inclusive: bool = False,
    input_timestamp_is_close: bool = False,
) -> pd.DataFrame:
    """Load, validate, normalize to UTC ns, sort, and optionally time-slice 1-minute OHLCV data.

    Supports:
    - ``pd.DataFrame`` (``t``/``ts``/``Date+Time``, ``o``/``open``, ``h``/``high``, ``l``/``low``,
      ``c``/``close``, ``v``/``volume``, optional ``delta``)
    - EdgeLab-style ``ctx`` dictionary (``{t, o, h, l, c, v}``)
    - CSV / TXT / Parquet file path (e.g. ``NQ_M1_dukas-M1-.csv``)

    Holdout protection:
    - Raises ``ValueError`` whenever a file path points inside a ``sellado`` directory unless
      ``allow_sellado=True``.
    - Use ``end="2026-10-01"`` (with default ``end_inclusive=False``) to enforce strict pre-holdout
      filtering (``ts < 2026-10-01 00:00:00`` in ``tz_input``).
    """
    if isinstance(source, (str, Path)):
        _assert_not_sellado(source, allow_sellado=allow_sellado)

    raw_df = _read_source_table(source)
    _, norm_df, has_real_delta = _resolve_columns(raw_df, tz_input=tz_input)

    if isinstance(source, pd.DataFrame):
        if "has_real_delta" in source.attrs:
            has_real_delta = bool(source.attrs["has_real_delta"]) and ("delta" in norm_df.columns)
        if "timestamp_is_close" in source.attrs and not input_timestamp_is_close:
            input_timestamp_is_close = bool(source.attrs["timestamp_is_close"])

    if len(norm_df) > 0:
        norm_df = norm_df.sort_values("ts_ns", kind="mergesort")
        norm_df = norm_df.drop_duplicates(subset=["ts_ns"], keep="last")

        if start is not None or end is not None:
            ts_arr = norm_df["ts_ns"].to_numpy(dtype=np.int64, copy=False)
            mask = np.ones(len(norm_df), dtype=bool)
            if start is not None:
                start_ns = _parse_single_timestamp_ns(start, tz_input=tz_input)
                mask &= ts_arr >= start_ns
            if end is not None:
                end_ns = _parse_single_timestamp_ns(end, tz_input=tz_input)
                mask &= (ts_arr <= end_ns) if end_inclusive else (ts_arr < end_ns)
            norm_df = norm_df.loc[mask]

    norm_df = norm_df.reset_index(drop=True)
    norm_df.attrs["has_real_delta"] = has_real_delta
    norm_df.attrs["timestamp_is_close"] = bool(input_timestamp_is_close)
    return norm_df


def _wallclock_fields(ts_ns: np.ndarray, tz: ZoneInfo) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Convert UTC ns timestamps to ``(hhmmss, yyyymmdd, dow_0mon_6sun, minute_of_day)`` in ``tz``."""
    n = len(ts_ns)
    if n == 0:
        empty_i32 = np.empty(0, dtype=np.int32)
        return empty_i32, empty_i32, np.empty(0, dtype=np.int8), empty_i32

    idx = pd.DatetimeIndex(pd.to_datetime(ts_ns, unit="ns", utc=True)).tz_convert(tz)
    hhmmss = (idx.hour.to_numpy(np.int32) * 10000
              + idx.minute.to_numpy(np.int32) * 100
              + idx.second.to_numpy(np.int32)).astype(np.int32)
    cal_date = (idx.year.to_numpy(np.int32) * 10000
                + idx.month.to_numpy(np.int32) * 100
                + idx.day.to_numpy(np.int32)).astype(np.int32)
    dow = idx.dayofweek.to_numpy(np.int8)
    min_of_day = (idx.hour.to_numpy(np.int32) * 60 + idx.minute.to_numpy(np.int32)).astype(np.int32)
    return hhmmss, cal_date, dow, min_of_day


def _compute_eth_trade_date(open_ts_ns: np.ndarray) -> np.ndarray:
    """Compute CME ETH trade_date ``YYYYMMDD`` using exact wall-clock ``open >= 17:00 CT`` rollover."""
    if len(open_ts_ns) == 0:
        return np.empty(0, dtype=np.int32)
    idx_ct = pd.DatetimeIndex(pd.to_datetime(open_ts_ns, unit="ns", utc=True)).tz_convert(_TZ_CT)
    hhmm = idx_ct.hour.to_numpy(np.int32) * 100 + idx_ct.minute.to_numpy(np.int32)
    naive_days = idx_ct.tz_localize(None).normalize()
    shifted_days = naive_days + pd.to_timedelta((hhmm >= 1700).astype(np.int64), unit="D")
    return (shifted_days.year.to_numpy(np.int32) * 10000
            + shifted_days.month.to_numpy(np.int32) * 100
            + shifted_days.day.to_numpy(np.int32)).astype(np.int32)


def _make_bar_series(
    bip: int,
    name: str,
    timeframe_min: int,
    ts_ns: np.ndarray,
    open_: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    volume: np.ndarray,
    delta: np.ndarray,
    m1_end_idx: np.ndarray,
    *,
    session_mode: str,
    eth_trade_dates: np.ndarray | None = None,
) -> BarSeries:
    """Attach CT/ET calendar arrays and ``is_new_session`` flags cleanly to an OHLCV series."""
    hhmmss_ct, cal_date_ct, dow_ct, _ = _wallclock_fields(ts_ns, _TZ_CT)
    hhmmss_et, cal_date_et, dow_et, _ = _wallclock_fields(ts_ns, _TZ_ET)

    if session_mode == "eth":
        if eth_trade_dates is None:
            date_ct = _compute_eth_trade_date(ts_ns - _NS_PER_MIN)
        else:
            date_ct = eth_trade_dates.astype(np.int32, copy=False)
        session_key = date_ct
    elif session_mode == "rth":
        date_ct = cal_date_ct
        session_key = cal_date_ct
    elif session_mode == "us_stock":
        date_ct = cal_date_ct
        session_key = cal_date_et
    else:
        raise ValueError(f"Unknown session_mode={session_mode!r}")

    n = len(ts_ns)
    if n == 0:
        is_new_session = np.empty(0, dtype=bool)
    elif timeframe_min == 0:
        is_new_session = np.ones(n, dtype=bool)
    else:
        is_new_session = np.empty(n, dtype=bool)
        is_new_session[0] = True
        is_new_session[1:] = session_key[1:] != session_key[:-1]

    return BarSeries(
        bip=bip,
        name=name,
        timeframe_min=timeframe_min,
        ts_ns=ts_ns.astype(np.int64, copy=False),
        open=open_.astype(np.float64, copy=False),
        high=high.astype(np.float64, copy=False),
        low=low.astype(np.float64, copy=False),
        close=close.astype(np.float64, copy=False),
        volume=volume.astype(np.float64, copy=False),
        delta=delta.astype(np.float64, copy=False),
        hhmmss_ct=hhmmss_ct,
        date_ct=date_ct,
        cal_date_ct=cal_date_ct,
        dow_ct=dow_ct,
        hhmmss_et=hhmmss_et,
        cal_date_et=cal_date_et,
        dow_et=dow_et,
        is_new_session=is_new_session,
        m1_end_idx=m1_end_idx.astype(np.int64, copy=False),
    )


def _aggregate_buckets(
    bip: int,
    name: str,
    timeframe_min: int,
    open_ts_ns: np.ndarray,
    close_ts_ns: np.ndarray,
    open_: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    volume: np.ndarray,
    delta: np.ndarray,
    m1_indices: np.ndarray,
    session_dates: np.ndarray,
    sess_min: np.ndarray,
    *,
    session_mode: str,
) -> BarSeries:
    """Causally aggregate sorted 1-minute bars into fixed intraday buckets or daily bars."""
    n = len(m1_indices)
    if n == 0:
        empty_f = np.empty(0, dtype=np.float64)
        empty_i = np.empty(0, dtype=np.int64)
        empty_d = np.empty(0, dtype=np.int32)
        return _make_bar_series(
            bip, name, timeframe_min, empty_i, empty_f, empty_f, empty_f, empty_f, empty_f, empty_f,
            empty_i, session_mode=session_mode, eth_trade_dates=empty_d,
        )

    if timeframe_min > 0:
        bucket_idx = (sess_min // timeframe_min).astype(np.int64)
        keys = session_dates.astype(np.int64) * 2048 + bucket_idx
    else:
        bucket_idx = np.zeros(n, dtype=np.int64)
        keys = session_dates.astype(np.int64)

    change = np.empty(n, dtype=bool)
    change[0] = True
    change[1:] = keys[1:] != keys[:-1]
    starts = np.flatnonzero(change)
    ends = np.empty_like(starts)
    ends[:-1] = starts[1:] - 1
    ends[-1] = n - 1

    agg_open = open_[starts]
    agg_high = np.maximum.reduceat(high, starts)
    agg_low = np.minimum.reduceat(low, starts)
    agg_close = close[ends]
    agg_vol = np.add.reduceat(volume, starts)
    agg_delta = np.add.reduceat(delta, starts)
    agg_m1_end = m1_indices[ends]

    if timeframe_min > 0:
        # Minute bars close at the exact bucket boundary (causal: last constituent minute is < boundary)
        rem_mins = (bucket_idx[ends] + 1) * timeframe_min - sess_min[ends].astype(np.int64)
        agg_ts_ns = open_ts_ns[ends] + rem_mins * _NS_PER_MIN
    else:
        agg_ts_ns = close_ts_ns[ends]

    return _make_bar_series(
        bip=bip,
        name=name,
        timeframe_min=timeframe_min,
        ts_ns=agg_ts_ns,
        open_=agg_open,
        high=agg_high,
        low=agg_low,
        close=agg_close,
        volume=agg_vol,
        delta=agg_delta,
        m1_end_idx=agg_m1_end,
        session_mode=session_mode,
        eth_trade_dates=session_dates[ends] if session_mode == "eth" else None,
    )


def build_multi_series(
    data: str | Path | pd.DataFrame | Mapping[str, Any],
    tick_size: float = TICK_SIZE_NQ,
    point_value: float = POINT_VALUE_NQ,
    tz_input: str = "UTC",
    *,
    allow_sellado: bool = False,
    input_timestamp_is_close: bool = False,
    us_stock_end_et: int = 161500,
) -> MultiSeriesContext:
    """Build causal ``MultiSeriesContext`` (``bip1`` .. ``bip10``) matching NT8 ``State.Configure``.

    Parameters
    ----------
    data:
        1-minute OHLCV (+ optional ``delta``) as DataFrame, EdgeLab ``ctx`` dict, CSV, or Parquet path.
    tick_size, point_value:
        Instrument contract geometry stored in ``MultiSeriesContext`` (default NQ ``0.25`` / ``20.0``).
    tz_input:
        Timezone applied when input timestamps are tz-naive (default ``"UTC"``).
    allow_sellado:
        Must stay ``False`` during development/research to prevent loading holdout data.
    input_timestamp_is_close:
        Set ``True`` if input 1m timestamps already stamp bar CLOSE rather than bar OPEN.
    us_stock_end_et:
        End time in ``HHMMSS`` ET for ``bip5`` (``US STOCK``). Defaults to ``161500`` matching
        the ``US STOCK.xml`` template shipped with ``FUNDEDSYNCSTACK-1.0.0.5`` (``09:30-16:15 ET``),
        which ``RunCapstone`` requires for ``exitTime_C = 16:15:00 ET``; pass ``160000`` for cash close.
    """
    df = load_m1_data(
        data,
        tz_input=tz_input,
        allow_sellado=allow_sellado,
        input_timestamp_is_close=input_timestamp_is_close,
    )
    has_real_delta = bool(df.attrs.get("has_real_delta", False)) and ("delta" in df.columns)
    is_close = bool(df.attrs.get("timestamp_is_close", input_timestamp_is_close))

    raw_ts_ns = df["ts_ns"].to_numpy(dtype=np.int64, copy=False)
    o_all = df["open"].to_numpy(dtype=np.float64, copy=False)
    h_all = df["high"].to_numpy(dtype=np.float64, copy=False)
    l_all = df["low"].to_numpy(dtype=np.float64, copy=False)
    c_all = df["close"].to_numpy(dtype=np.float64, copy=False)
    v_all = df["volume"].to_numpy(dtype=np.float64, copy=False)

    if has_real_delta:
        d_all = df["delta"].to_numpy(dtype=np.float64, copy=False)
    else:
        # Causal OHLCV proxy delta defined on already-closed M1 bars
        d_all = np.where(c_all > o_all, v_all, np.where(c_all < o_all, -v_all, 0.0)).astype(np.float64)

    if is_close:
        close_all_ns = raw_ts_ns
        open_all_ns = raw_ts_ns - _NS_PER_MIN
    else:
        open_all_ns = raw_ts_ns
        close_all_ns = raw_ts_ns + _NS_PER_MIN

    # Filter bip1 (CME US Index Futures ETH): Sun 17:00 -> Fri 16:00 CT, no [16:00, 17:00) break
    open_hhmmss_ct, _, open_dow_ct, _ = _wallclock_fields(open_all_ns, _TZ_CT)
    is_mon_thu = open_dow_ct <= 3
    is_fri = open_dow_ct == 4
    is_sun = open_dow_ct == 6
    eth_mask = (
        (is_mon_thu & ((open_hhmmss_ct < 160000) | (open_hhmmss_ct >= 170000)))
        | (is_fri & (open_hhmmss_ct < 160000))
        | (is_sun & (open_hhmmss_ct >= 170000))
    )

    eth_open_ns = open_all_ns[eth_mask]
    eth_close_ns = close_all_ns[eth_mask]
    eth_o = o_all[eth_mask]
    eth_h = h_all[eth_mask]
    eth_l = l_all[eth_mask]
    eth_c = c_all[eth_mask]
    eth_v = v_all[eth_mask]
    eth_d = d_all[eth_mask]

    n_eth = len(eth_open_ns)
    bip1_indices = np.arange(n_eth, dtype=np.int64)
    eth_trade_dates = _compute_eth_trade_date(eth_open_ns)
    _, _, _, eth_open_min_ct = _wallclock_fields(eth_open_ns, _TZ_CT)
    eth_sess_min = np.where(
        eth_open_min_ct >= 17 * 60,
        eth_open_min_ct - 17 * 60,
        eth_open_min_ct + 7 * 60,
    ).astype(np.int32)

    bip1 = _make_bar_series(
        bip=1,
        name="1m ETH",
        timeframe_min=1,
        ts_ns=eth_close_ns,
        open_=eth_o,
        high=eth_h,
        low=eth_l,
        close=eth_c,
        volume=eth_v,
        delta=eth_d,
        m1_end_idx=bip1_indices,
        session_mode="eth",
        eth_trade_dates=eth_trade_dates,
    )

    def make_eth(bip_id: int, label: str, tf_min: int) -> BarSeries:
        return _aggregate_buckets(
            bip_id, label, tf_min,
            eth_open_ns, eth_close_ns, eth_o, eth_h, eth_l, eth_c, eth_v, eth_d,
            bip1_indices, eth_trade_dates, eth_sess_min, session_mode="eth",
        )

    bip2 = make_eth(2, "3m ETH", 3)
    bip3 = make_eth(3, "5m ETH", 5)
    bip4 = make_eth(4, "20m ETH", 20)
    bip8 = make_eth(8, "1d ETH", 0)
    bip9 = make_eth(9, "10m ETH", 10)
    bip10 = make_eth(10, "15m ETH", 15)

    # US STOCK (bip5): derived directly from bip1 M1 bars to maintain valid m1_end_idx pointers
    eth_open_hhmmss_et, _, eth_open_dow_et, _ = _wallclock_fields(eth_open_ns, _TZ_ET)
    stock_mask = (
        (eth_open_dow_et <= 4)
        & (eth_open_hhmmss_et >= 93000)
        & (eth_open_hhmmss_et < int(us_stock_end_et))
    )
    bip5 = _make_bar_series(
        bip=5,
        name="1m US STOCK",
        timeframe_min=1,
        ts_ns=eth_close_ns[stock_mask],
        open_=eth_o[stock_mask],
        high=eth_h[stock_mask],
        low=eth_l[stock_mask],
        close=eth_c[stock_mask],
        volume=eth_v[stock_mask],
        delta=eth_d[stock_mask],
        m1_end_idx=bip1_indices[stock_mask],
        session_mode="us_stock",
    )

    # CME US Index Futures RTH (bip6 = 5m, bip7 = 1d): 08:30-15:15 CT Mon-Fri
    eth_open_hhmmss_ct, eth_open_cal_ct, eth_open_dow_ct, _ = _wallclock_fields(eth_open_ns, _TZ_CT)
    rth_mask = (
        (eth_open_dow_ct <= 4)
        & (eth_open_hhmmss_ct >= 83000)
        & (eth_open_hhmmss_ct < 151500)
    )
    rth_sess_min = (eth_open_min_ct[rth_mask] - (8 * 60 + 30)).astype(np.int32)
    rth_dates = eth_open_cal_ct[rth_mask]

    bip6 = _aggregate_buckets(
        6, "5m RTH", 5,
        eth_open_ns[rth_mask], eth_close_ns[rth_mask],
        eth_o[rth_mask], eth_h[rth_mask], eth_l[rth_mask], eth_c[rth_mask],
        eth_v[rth_mask], eth_d[rth_mask],
        bip1_indices[rth_mask], rth_dates, rth_sess_min, session_mode="rth",
    )
    bip7 = _aggregate_buckets(
        7, "1d RTH", 0,
        eth_open_ns[rth_mask], eth_close_ns[rth_mask],
        eth_o[rth_mask], eth_h[rth_mask], eth_l[rth_mask], eth_c[rth_mask],
        eth_v[rth_mask], eth_d[rth_mask],
        bip1_indices[rth_mask], rth_dates, rth_sess_min, session_mode="rth",
    )

    return MultiSeriesContext(
        bip1=bip1,
        bip2=bip2,
        bip3=bip3,
        bip4=bip4,
        bip5=bip5,
        bip6=bip6,
        bip7=bip7,
        bip8=bip8,
        bip9=bip9,
        bip10=bip10,
        tick_size=float(tick_size),
        point_value=float(point_value),
        has_real_delta=has_real_delta,
    )


def _as_float64_1d(arr: Any, name: str) -> np.ndarray:
    """Validate 1D numeric input and return contiguous float64 numpy array."""
    out = np.asarray(arr, dtype=np.float64)
    if out.ndim != 1:
        raise ValueError(f"{name} must be 1-dimensional, got shape {out.shape}")
    return out


def nt_sma(x: Any, n: int) -> np.ndarray:
    """Exact NinjaTrader 8 ``SMA(x, n)`` matching ``@SMA.cs``.

    Warmup behavior (bars ``0 .. n-1``): divides the running sum by ``i + 1`` rather than
    emitting ``NaN``. Chunked sliding sums or sequential prior-sum subtraction match NT8 exact
    ``PriorSum + Input[0]`` recurrence without global ``cumsum`` catastrophic cancellation.
    """
    period = int(n)
    if period < 1:
        raise ValueError(f"Period n must be >= 1, got {n}")
    vals = _as_float64_1d(x, "x")
    m = len(vals)
    if m == 0:
        return np.empty(0, dtype=np.float64)
    if period == 1:
        return vals.copy()

    src = vals.tolist()
    out = [0.0] * m
    prior_sum = 0.0
    limit = min(m, period)
    for i in range(limit):
        prior_sum += src[i]
        out[i] = prior_sum / (i + 1)
    for i in range(period, m):
        prior_sum = (prior_sum - src[i - period]) + src[i]
        out[i] = prior_sum / period
    return np.asarray(out, dtype=np.float64)


def nt_ema(x: Any, n: int) -> np.ndarray:
    """Exact NinjaTrader 8 ``EMA(x, n)`` matching ``@EMA.cs``.

    Seeded at bar ``0`` directly with ``x[0]`` (NOT with SMA of first ``n`` bars):
    ``k = 2.0 / (1 + n)``, ``v[i] = x[i] * k + (1 - k) * v[i - 1]``.
    """
    period = int(n)
    if period < 1:
        raise ValueError(f"Period n must be >= 1, got {n}")
    vals = _as_float64_1d(x, "x")
    m = len(vals)
    if m == 0:
        return np.empty(0, dtype=np.float64)
    if period == 1:
        return vals.copy()

    k1 = 2.0 / (1.0 + period)
    k2 = 1.0 - k1
    src = vals.tolist()
    out = [0.0] * m
    prev = src[0]
    out[0] = prev
    for i in range(1, m):
        prev = src[i] * k1 + k2 * prev
        out[i] = prev
    return np.asarray(out, dtype=np.float64)


def _true_range(high: np.ndarray, low: np.ndarray, close: np.ndarray) -> np.ndarray:
    """Compute NinjaTrader True Range: ``tr[0] = h[0] - l[0]``, ``tr[i] = max(h-l, |h-c1|, |l-c1|)``."""
    m = len(high)
    if m == 0:
        return np.empty(0, dtype=np.float64)
    tr = np.empty(m, dtype=np.float64)
    tr[0] = high[0] - low[0]
    if m > 1:
        hl = high[1:] - low[1:]
        hc = np.abs(high[1:] - close[:-1])
        lc = np.abs(low[1:] - close[:-1])
        tr[1:] = np.maximum(hl, np.maximum(hc, lc))
    return tr


def nt_atr(h: Any, l: Any, c: Any, n: int) -> np.ndarray:
    """Exact NinjaTrader 8 ``ATR(n)`` matching ``@ATR.cs`` (cumulative mean warmup then Wilder).

    Formula from ``@ATR.cs``:
    - ``v[0] = h[0] - l[0]``
    - ``i >= 1``: ``k = min(i + 1, n)``, ``v[i] = ((k - 1) * v[i - 1] + tr[i]) / k``
    """
    period = int(n)
    if period < 1:
        raise ValueError(f"Period n must be >= 1, got {n}")
    high = _as_float64_1d(h, "h")
    low = _as_float64_1d(l, "l")
    close = _as_float64_1d(c, "c")
    if not (len(high) == len(low) == len(close)):
        raise ValueError("h, l, c must have identical lengths")
    m = len(high)
    if m == 0:
        return np.empty(0, dtype=np.float64)

    tr = _true_range(high, low, close).tolist()
    out = [0.0] * m
    prev = tr[0]
    out[0] = prev
    warmup_end = min(m, period)
    for i in range(1, warmup_end):
        k = i + 1
        prev = ((k - 1) * prev + tr[i]) / k
        out[i] = prev
    if period < m:
        p_minus_1 = period - 1.0
        inv_p = 1.0 / period
        for i in range(period, m):
            prev = (p_minus_1 * prev + tr[i]) * inv_p
            out[i] = prev
    return np.asarray(out, dtype=np.float64)


def nt_adx(h: Any, l: Any, c: Any, n: int) -> np.ndarray:
    """Exact NinjaTrader 8 ``ADX(n)`` matching ``@ADX.cs``.

    Uses NT8's exact ``DoubleExtensions.ApproxCompare(x, 0.0) == 0`` threshold ``|x| <= 1e-9``
    when guarding division by ``sumTr`` and ``diPlus + diMinus``, initializes ``ADX[0] = 50.0``,
    accumulates raw sums for ``i < n``, and applies Wilder's running-sum decay ``s - s / n + x``
    for ``i >= n``.
    """
    period = int(n)
    if period < 1:
        raise ValueError(f"Period n must be >= 1, got {n}")
    high = _as_float64_1d(h, "h")
    low = _as_float64_1d(l, "l")
    close = _as_float64_1d(c, "c")
    if not (len(high) == len(low) == len(close)):
        raise ValueError("h, l, c must have identical lengths")
    m = len(high)
    if m == 0:
        return np.empty(0, dtype=np.float64)

    hl = high.tolist()
    ll = low.tolist()
    tr = _true_range(high, low, close).tolist()

    out = [0.0] * m
    sum_tr = tr[0]
    sum_dmp = 0.0
    sum_dmm = 0.0
    adx_prev = 50.0
    out[0] = 50.0

    inv_p = 1.0 / period
    p_minus_1 = period - 1.0

    for i in range(1, m):
        up = hl[i] - hl[i - 1]
        dn = ll[i - 1] - ll[i]
        dmp = up if (up > dn and up > 0.0) else 0.0
        dmm = dn if (dn > up and dn > 0.0) else 0.0

        if i < period:
            sum_tr += tr[i]
            sum_dmp += dmp
            sum_dmm += dmm
        else:
            sum_tr = sum_tr - sum_tr * inv_p + tr[i]
            sum_dmp = sum_dmp - sum_dmp * inv_p + dmp
            sum_dmm = sum_dmm - sum_dmm * inv_p + dmm

        if abs(sum_tr) <= _NT_APPROX_EPS:
            di_plus = 0.0
            di_minus = 0.0
        else:
            di_plus = 100.0 * (sum_dmp / sum_tr)
            di_minus = 100.0 * (sum_dmm / sum_tr)

        di_sum = di_plus + di_minus
        if abs(di_sum) <= _NT_APPROX_EPS:
            adx_prev = 50.0
        else:
            dx = 100.0 * (abs(di_plus - di_minus) / di_sum)
            adx_prev = (p_minus_1 * adx_prev + dx) * inv_p
        out[i] = adx_prev

    return np.asarray(out, dtype=np.float64)


__all__ = [
    "load_m1_data",
    "build_multi_series",
    "nt_sma",
    "nt_ema",
    "nt_atr",
    "nt_adx",
]
