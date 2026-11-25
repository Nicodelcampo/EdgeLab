"""Bar-open phase shift sensitivity analysis on real CME NQ and CFD USATECHIDXUSD ticks.

Experiments implemented:
  A. Sub-minute candle-open phase shifts delta in {0, 5, ..., 55} seconds (12 phases)
     across 322 clean real CME NQ tick sessions (K30 2025-08-05..2026-09-25 +
     Sellado 2026-10-01..2026-11-13, excluding holiday/maintenance sessions).
  B. Multi-minute clock shifts dM in {-2, -1, 0, +1, +2, +3, +4} minutes across full
     2020-2026 M1 history + pure M5 HTF boundary phase shift on SOMEOD (p in 0..4m).
  C. Real CFD USATECHIDXUSD tick spread audit (2026-10-01..2026-11-15) and shifted-bar
     evaluation vs CME NQ Sellado net of real window-specific spread friction.
"""

from __future__ import annotations

import concurrent.futures
import glob
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.csv as pacsv
import pyarrow.parquet as pq

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from edgelab.holdout import a5_bloque, sesion_excluida

M1_PARQUET = Path(
    r"C:\Users\nicoc\OneDrive\Documentos\NinjaTrader 8\exports\edgelab_nt8_m1_parquet\NQ_M1_nonadj_utc.parquet"
)
K30_TICKS = REPO / "data" / "ticks_nq_calibracion" / "NQ_ticks.parquet"
SELLADO_DIR = Path(r"C:\EdgeLab\sellado")
USATECH_TICKS = SELLADO_DIR / "USATECHIDXUSD_ticks.parquet"
VERIFY_EXE = Path(
    r"C:\Users\nicoc\.gemini\antigravity\brain\417d395c-1bd7-4157-b782-277352881af1\scratch\VerifyCfdCoreParity.exe"
)
OUT_DIR = REPO / "docs" / "research" / "fundedsync_bar_phase_shift_20261123"
SCRATCH_WORK = Path(
    r"C:\Users\nicoc\.gemini\antigravity\brain\417d395c-1bd7-4157-b782-277352881af1\scratch\phase_shift_work"
)
ARTIFACT_DIR = Path(
    r"C:\Users\nicoc\.gemini\antigravity\brain\417d395c-1bd7-4157-b782-277352881af1"
)

MIN_NS = 60_000_000_000
SEC_NS = 1_000_000_000
TICK_SIZE_NQ = 0.25

# Dark visual palette matching repository charts
BG_FIG = "#0d1316"
BG_AX = "#11191c"
GRID_COL = "#243137"
FG_TEXT = "#e6eef2"
MUTED_TEXT = "#9ab0ba"
ACCENT_TEAL = "#2ec4b6"
ACCENT_GOLD = "#f4b942"
ACCENT_CORAL = "#e76f51"
ACCENT_BLUE = "#5fa8d3"
ACCENT_GREEN = "#80ed99"



class StreamingShiftResampler:
    """Streams chronological tick chunks into shifted 1-minute OHLCV candles cleanly across chunk boundaries.

    Every shifted bucket `[k*60 + delta, (k+1)*60 + delta)` is assigned nominal bar-close UTC
    `(k + 1) * 60` seconds so downstream causal evaluators (`ExactMinute == true`) assess rule sensitivity
    purely to the underlying candle-open boundary displacement `delta`.
    """

    def __init__(self, deltas_s: Sequence[int]) -> None:
        self.deltas_s = [int(d) for d in deltas_s]
        self._active: dict[int, list[float] | None] = {d: None for d in self.deltas_s}
        self._chunks: dict[int, list[tuple[np.ndarray, ...]]] = {d: [] for d in self.deltas_s}
        self._last_ts: int | None = None

    def feed_chunk(
        self,
        ts_utc_ns: np.ndarray,
        prices: np.ndarray,
        volumes: np.ndarray,
    ) -> None:
        """Ingest one chronological chunk of ticks and merge boundary-crossing candles safely."""
        if len(ts_utc_ns) == 0:
            return
        ts = np.asarray(ts_utc_ns, dtype=np.int64)
        px = np.asarray(prices, dtype=np.float64)
        vol = np.asarray(volumes, dtype=np.float64)

        if len(ts) > 1 and np.any(ts[1:] < ts[:-1]):
            order = np.argsort(ts, kind="mergesort")
            ts, px, vol = ts[order], px[order], vol[order]

        if self._last_ts is not None and int(ts[0]) < self._last_ts:
            mask = ts >= self._last_ts
            if not np.any(mask):
                return
            ts, px, vol = ts[mask], px[mask], vol[mask]
        self._last_ts = int(ts[-1])

        for d in self.deltas_s:
            d_ns = np.int64(d) * np.int64(SEC_NS)
            b = (ts - d_ns) // np.int64(MIN_NS)
            chg = np.flatnonzero(b[1:] != b[:-1]) + 1
            starts = np.concatenate((np.array([0], dtype=np.int64), chg))
            ends = np.concatenate((chg, np.array([len(b)], dtype=np.int64)))

            bk = b[starts]
            bo = px[starts]
            bh = np.maximum.reduceat(px, starts)
            bl = np.minimum.reduceat(px, starts)
            bc = px[ends - 1]
            bv = np.add.reduceat(vol, starts)

            act = self._active[d]
            if act is not None:
                if int(bk[0]) == int(act[0]):
                    if float(bh[0]) > act[2]:
                        act[2] = float(bh[0])
                    if float(bl[0]) < act[3]:
                        act[3] = float(bl[0])
                    act[4] = float(bc[0])
                    act[5] += float(bv[0])
                    bk, bo, bh, bl, bc, bv = bk[1:], bo[1:], bh[1:], bl[1:], bc[1:], bv[1:]

                if len(bk) > 0:
                    self._chunks[d].append((
                        np.array([int(act[0])], dtype=np.int64),
                        np.array([act[1]], dtype=np.float64),
                        np.array([act[2]], dtype=np.float64),
                        np.array([act[3]], dtype=np.float64),
                        np.array([act[4]], dtype=np.float64),
                        np.array([act[5]], dtype=np.float64),
                    ))
                    act = None
                else:
                    self._active[d] = act
                    continue

            if len(bk) > 1:
                self._chunks[d].append((bk[:-1], bo[:-1], bh[:-1], bl[:-1], bc[:-1], bv[:-1]))
            if len(bk) > 0:
                self._active[d] = [
                    int(bk[-1]),
                    float(bo[-1]),
                    float(bh[-1]),
                    float(bl[-1]),
                    float(bc[-1]),
                    float(bv[-1]),
                ]

    def finish(self) -> dict[int, pd.DataFrame]:
        """Flush final active buckets and return DataFrames keyed by delta_s."""
        out: dict[int, pd.DataFrame] = {}
        for d in self.deltas_s:
            act = self._active[d]
            parts = list(self._chunks[d])
            if act is not None:
                parts.append((
                    np.array([int(act[0])], dtype=np.int64),
                    np.array([act[1]], dtype=np.float64),
                    np.array([act[2]], dtype=np.float64),
                    np.array([act[3]], dtype=np.float64),
                    np.array([act[4]], dtype=np.float64),
                    np.array([act[5]], dtype=np.float64),
                ))
                self._active[d] = None
            if not parts:
                out[d] = pd.DataFrame(columns=["close_utc_ns", "o", "h", "l", "c", "v"])
                continue
            bk = np.concatenate([p[0] for p in parts])
            close_ns = (bk + np.int64(1)) * np.int64(MIN_NS)
            out[d] = pd.DataFrame({
                "close_utc_ns": close_ns,
                "o": np.concatenate([p[1] for p in parts]),
                "h": np.concatenate([p[2] for p in parts]),
                "l": np.concatenate([p[3] for p in parts]),
                "c": np.concatenate([p[4] for p in parts]),
                "v": np.concatenate([p[5] for p in parts]),
            })
        return out


def _plt():                                   # matplotlib sólo al graficar: el cálculo y los tests no lo necesitan
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams["text.parse_math"] = False
    return plt


def resample_ticks_to_shifted_m1(
    ts_utc_ns: np.ndarray,
    prices: np.ndarray,
    volumes: np.ndarray,
    deltas_s: Sequence[int] = (0,),
    chunk_size: int | None = None,
) -> dict[int, pd.DataFrame]:
    """Vectorized helper to resample ticks into shifted 1m OHLCV DataFrames (supports chunking for tests)."""
    res = StreamingShiftResampler(deltas_s)
    n = len(ts_utc_ns)
    if n == 0:
        return res.finish()
    step = int(chunk_size) if chunk_size and chunk_size > 0 else n
    for start in range(0, n, step):
        end = min(n, start + step)
        res.feed_chunk(ts_utc_ns[start:end], prices[start:end], volumes[start:end])
    return res.finish()


def _format_close_utc_col(close_ns: np.ndarray) -> np.ndarray:
    """Format int64 UTC nanoseconds to ISO8601 seconds strings via vectorized datetime64 casting."""
    arr = np.asarray(close_ns, dtype=np.int64).view("datetime64[ns]").astype("datetime64[s]")
    return arr.astype(str)


def _write_m1_csv(df: pd.DataFrame, out_path: Path, close_utc_col: np.ndarray | None = None) -> None:
    """Write M1 OHLCV table to unquoted CSV fast via pyarrow.csv."""
    c_col = _format_close_utc_col(df["close_utc_ns"].to_numpy(np.int64)) if close_utc_col is None else close_utc_col
    tb = pa.table({
        "close_utc": pa.array(c_col),
        "o": pa.array(df["o"].to_numpy(np.float64)),
        "h": pa.array(df["h"].to_numpy(np.float64)),
        "l": pa.array(df["l"].to_numpy(np.float64)),
        "c": pa.array(df["c"].to_numpy(np.float64)),
        "v": pa.array(df["v"].to_numpy(np.float64)),
    })
    pacsv.write_csv(tb, str(out_path), write_options=pacsv.WriteOptions(include_header=True, quoting_style="none"))


def _load_canonical_m1_close(desde_utc: str = "2023-01-01") -> pd.DataFrame:
    """Load canonical NQ_M1_nonadj_utc.parquet and shift index by +60s to exact bar-close UTC."""
    m1 = pd.read_parquet(M1_PARQUET)
    if m1.index.tz is not None:
        m1.index = m1.index.tz_convert("UTC").tz_localize(None)
    m1 = m1[m1.index >= pd.Timestamp(desde_utc)].copy()
    close_ns = (m1.index.asi8 + np.int64(MIN_NS)).astype(np.int64)
    return pd.DataFrame({
        "close_utc_ns": close_ns,
        "o": m1["open"].to_numpy(np.float64),
        "h": m1["high"].to_numpy(np.float64),
        "l": m1["low"].to_numpy(np.float64),
        "c": m1["close"].to_numpy(np.float64),
        "v": m1["volume"].to_numpy(np.float64),
    })


def _run_verify_exe(args: tuple[str, Path, int, Path, Path]) -> tuple[str, float]:
    tag, csv_path, eval_start_ymd, out_tr, out_dy = args
    t0 = time.perf_counter()
    res = subprocess.run(
        [str(VERIFY_EXE), str(csv_path), str(eval_start_ymd), str(out_tr), str(out_dy)],
        capture_output=True,
        text=True,
    )
    if res.returncode != 0:
        raise RuntimeError(f"VerifyCfdCoreParity failed on {tag}: {res.stderr}\n{res.stdout}")
    return tag, time.perf_counter() - t0


def _portfolio_stats_from_daily(daily_r: pd.Series, total_days: int) -> dict[str, float]:
    """Compute core performance statistics over the evaluation day grid."""
    s = daily_r.fillna(0.0).to_numpy(dtype=np.float64)
    tot = float(s.sum())
    mean_d = float(s.mean()) if len(s) else 0.0
    std_d = float(s.std(ddof=1)) if len(s) > 1 else 0.0
    sharpe = (mean_d / std_d) * np.sqrt(252.0) if std_d > 1e-12 else 0.0
    eq = np.cumsum(s)
    peak = np.maximum.accumulate(np.concatenate(([0.0], eq)))[1:]
    peak = np.maximum(peak, 0.0)
    dd = eq - peak
    max_dd = float(dd.min()) if len(dd) else 0.0
    meses = max(total_days / 21.0, 1e-6)
    calmar = (tot / (meses / 12.0)) / abs(max_dd) if max_dd < -1e-9 else float("nan")
    return {
        "sumR": tot,
        "R_mes": tot / meses,
        "Sharpe": sharpe,
        "MaxDD_R": max_dd,
        "Calmar": calmar,
    }


def _stream_cme_nq_ticks(deltas_s: Sequence[int]) -> tuple[dict[int, pd.DataFrame], dict[int, pd.DataFrame], set[int], set[int]]:
    """Stream K30 + Sellado NQ ticks simultaneously into 12 shifted M1 tables."""
    res_k30 = StreamingShiftResampler(deltas_s)
    k30_dates: set[int] = set()
    pf_k30 = pq.ParquetFile(K30_TICKS)
    print(f"[Exp A] Streaming K30 NQ ticks ({pf_k30.num_row_groups} RGs, {pf_k30.metadata.num_rows:,} rows)...")
    t0 = time.perf_counter()
    for rgi in range(pf_k30.num_row_groups):
        tb = pf_k30.read_row_group(rgi, columns=["ts_utc_ns", "price_ticks", "volume", "trade_date", "outside_regular"])
        df = tb.to_pandas()
        if "outside_regular" in df.columns:
            m = ~df["outside_regular"].to_numpy(bool)
            if not np.all(m):
                df = df[m]
        k30_dates.update(int(x) for x in df["trade_date"].unique() if not sesion_excluida("NQ", int(x)))
        res_k30.feed_chunk(
            df["ts_utc_ns"].to_numpy(np.int64),
            df["price_ticks"].to_numpy(np.float64) * TICK_SIZE_NQ,
            df["volume"].to_numpy(np.float64),
        )
    bars_k30 = res_k30.finish()
    print(f"  K30 done in {time.perf_counter() - t0:.1f}s ({len(k30_dates)} clean sessions).")

    # Sellado NQ: NQ_12-26 (< 20261029) + daily NQ_20261029..NQ_20261113
    res_sell = StreamingShiftResampler(deltas_s)
    sell_dates: set[int] = set()
    sell_roll = SELLADO_DIR / "NQ_12-26_ticks.parquet"
    daily_files = sorted(glob.glob(str(SELLADO_DIR / "NQ_2026*_ticks.parquet")))
    t1 = time.perf_counter()

    pf_roll = pq.ParquetFile(sell_roll)
    for rgi in range(pf_roll.num_row_groups):
        df = pf_roll.read_row_group(rgi, columns=["ts_utc_ns", "price_ticks", "volume", "trade_date"]).to_pandas()
        df = df[df["trade_date"] < 20261029]
        if df.empty:
            continue
        sell_dates.update(int(x) for x in df["trade_date"].unique() if not sesion_excluida("NQ", int(x)))
        res_sell.feed_chunk(
            df["ts_utc_ns"].to_numpy(np.int64),
            df["price_ticks"].to_numpy(np.float64) * TICK_SIZE_NQ,
            df["volume"].to_numpy(np.float64),
        )

    for sf in daily_files:
        df = pd.read_parquet(sf, columns=["ts_utc_ns", "price_ticks", "volume", "trade_date"])
        sell_dates.update(int(x) for x in df["trade_date"].unique() if not sesion_excluida("NQ", int(x)))
        res_sell.feed_chunk(
            df["ts_utc_ns"].to_numpy(np.int64),
            df["price_ticks"].to_numpy(np.float64) * TICK_SIZE_NQ,
            df["volume"].to_numpy(np.float64),
        )
    bars_sell = res_sell.finish()
    print(f"  Sellado NQ done in {time.perf_counter() - t1:.1f}s ({len(sell_dates)} clean sessions).")
    return bars_k30, bars_sell, k30_dates, sell_dates


def run_experiment_a(m1_2023: pd.DataFrame) -> dict[str, object]:
    """Experiment A: sub-minute phase shift delta in {0, 5, ..., 55}s on 322 CME NQ sessions."""
    deltas_s = list(range(0, 60, 5))
    bars_k30, bars_sell, k30_dates, sell_dates = _stream_cme_nq_ticks(deltas_s)
    clean_tick_dates = sorted(k30_dates | sell_dates)
    assert len(clean_tick_dates) == 322, f"Expected 322 clean tick sessions, got {len(clean_tick_dates)}"

    # First run canonical M1 control (2023-01-01..2026-11-17) for exact delta=0 sanity verification
    canon_csv = SCRATCH_WORK / "expA_canon_control.csv"
    canon_tr = SCRATCH_WORK / "expA_canon_control_trades.csv"
    canon_dy = SCRATCH_WORK / "expA_canon_control_daily.csv"
    _write_m1_csv(m1_2023, canon_csv)

    jobs: list[tuple[str, Path, int, Path, Path]] = [
        ("CANON", canon_csv, 20250805, canon_tr, canon_dy)
    ]

    first_k30_ns = int(bars_k30[0]["close_utc_ns"].iloc[0])
    last_k30_ns = int(bars_k30[0]["close_utc_ns"].iloc[-1])
    first_sell_ns = int(bars_sell[0]["close_utc_ns"].iloc[0])
    warmup_base = m1_2023[m1_2023["close_utc_ns"] < first_k30_ns]
    warmup_str = _format_close_utc_col(warmup_base["close_utc_ns"].to_numpy(np.int64))
    bridge_base = m1_2023[(m1_2023["close_utc_ns"] > last_k30_ns) & (m1_2023["close_utc_ns"] < first_sell_ns)]
    bridge_str = _format_close_utc_col(bridge_base["close_utc_ns"].to_numpy(np.int64))

    print("[Exp A] Writing 12 shifted M1 CSV feeds via pyarrow.csv...", flush=True)
    for d in deltas_s:
        k_df = bars_k30[d]
        s_df = bars_sell[d]
        k_str = _format_close_utc_col(k_df["close_utc_ns"].to_numpy(np.int64))
        s_str = _format_close_utc_col(s_df["close_utc_ns"].to_numpy(np.int64))

        combined = pd.concat([warmup_base, k_df, bridge_base, s_df], ignore_index=True)
        combined_str = np.concatenate([warmup_str, k_str, bridge_str, s_str])
        _, uniq_idx = np.unique(combined["close_utc_ns"].to_numpy(np.int64)[::-1], return_index=True)
        # Ensure strictly sorted without duplicates keeping last
        order = np.argsort(combined["close_utc_ns"].to_numpy(np.int64), kind="mergesort")
        c_ns_s = combined["close_utc_ns"].to_numpy(np.int64)[order]
        keep = np.concatenate((c_ns_s[:-1] != c_ns_s[1:], np.array([True], dtype=bool)))
        idx_final = order[keep]
        combined = combined.iloc[idx_final].reset_index(drop=True)
        combined_str = combined_str[idx_final]

        csv_p = SCRATCH_WORK / f"expA_delta_{d:02d}.csv"
        tr_p = SCRATCH_WORK / f"expA_delta_{d:02d}_trades.csv"
        dy_p = SCRATCH_WORK / f"expA_delta_{d:02d}_daily.csv"
        _write_m1_csv(combined, csv_p, close_utc_col=combined_str)
        jobs.append((f"d{d:02d}", csv_p, 20250805, tr_p, dy_p))

    print(f"[Exp A] Running VerifyCfdCoreParity.exe across {len(jobs)} feeds (6 workers)...")
    t0 = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
        for tag, dt in ex.map(_run_verify_exe, jobs):
            pass
    print(f"  All {len(jobs)} C# runs completed in {time.perf_counter() - t0:.1f}s.")

    # Parse Canonical M1 baseline & all 12 delta phases
    clean_set = set(clean_tick_dates)
    modules_order = [
        "R_osc30_end660_ATR50",
        "Z_b15_e20_eff40_ATR50",
        "T_stop100_BE15R_calFalse",
        "V_nm25_noCap_mae30",
        "W_slope_allowReFalse_ATR25",
        "N_d5_fbTrue_ATR25",
        "SOMEOD_ext_NQ",
    ]

    def load_clean(tr_path: Path) -> pd.DataFrame:
        df = pd.read_csv(tr_path)
        return df[df["fecha_int"].isin(clean_set)].copy()

    canon_df = load_clean(canon_tr)
    delta_dfs = {d: load_clean(SCRATCH_WORK / f"expA_delta_{d:02d}_trades.csv") for d in deltas_s}

    # Sanity check delta=0 vs canonical
    sanity = {}
    for port in ["CORE5", "P7", "INDEP"]:
        c_sub = canon_df[canon_df["portfolio"] == port]
        d0_sub = delta_dfs[0][delta_dfs[0]["portfolio"] == port]
        sanity[port] = {
            "canon_n": int(len(c_sub)),
            "delta0_n": int(len(d0_sub)),
            "canon_R": round(float(c_sub["R_neto_mini"].sum()), 2),
            "delta0_R": round(float(d0_sub["R_neto_mini"].sum()), 2),
        }
    print("  [Exp A Sanity canon vs delta=0s]:", sanity)

    # Portfolio summary table across the 12 deltas
    summary_rows = []
    daily_curves: dict[str, dict[int, pd.Series]] = {"CORE5": {}, "P7": {}}
    d0_daily: dict[str, pd.Series] = {}
    for port in ["CORE5", "P7"]:
        for d in deltas_s:
            sub = delta_dfs[d][delta_dfs[d]["portfolio"] == port]
            ser = sub.groupby("fecha_int")["R_neto_mini"].sum().reindex(clean_tick_dates, fill_value=0.0)
            daily_curves[port][d] = ser
            if d == 0:
                d0_daily[port] = ser

        for d in deltas_s:
            sub = delta_dfs[d][delta_dfs[d]["portfolio"] == port]
            ser = daily_curves[port][d]
            st = _portfolio_stats_from_daily(ser, len(clean_tick_dates))
            corr0 = float(np.corrcoef(ser.to_numpy(), d0_daily[port].to_numpy())[0, 1]) if ser.std() > 0 else float("nan")
            summary_rows.append({
                "portfolio": port,
                "delta_s": d,
                "n_trades": int(len(sub)),
                "sumR": round(st["sumR"], 3),
                "R_op": round(st["sumR"] / max(len(sub), 1), 4),
                "R_mes": round(st["R_mes"], 3),
                "Sharpe": round(st["Sharpe"], 3),
                "MaxDD_R": round(st["MaxDD_R"], 3),
                "Calmar": round(st["Calmar"], 3),
                "corr_vs_d0": round(corr0, 5),
                "retention_vs_d0": round(st["sumR"] / d0_daily[port].sum(), 4) if abs(d0_daily[port].sum()) > 1e-9 else float("nan"),
            })

    summary_df = pd.DataFrame(summary_rows)
    summary_df.to_csv(OUT_DIR / "subminute_phase_summary.csv", index=False)

    # Module-level matrix across all 12 deltas (INDEP)
    mod_rows = []
    for mod in modules_order:
        r_d0 = delta_dfs[0][(delta_dfs[0]["portfolio"] == "INDEP") & (delta_dfs[0]["modulo"] == mod)]
        d0_ser = r_d0.groupby("fecha_int")["R_neto_mini"].sum().reindex(clean_tick_dates, fill_value=0.0)
        d0_sum = float(d0_ser.sum())
        for d in deltas_s:
            sub = delta_dfs[d][(delta_dfs[d]["portfolio"] == "INDEP") & (delta_dfs[d]["modulo"] == mod)]
            ser = sub.groupby("fecha_int")["R_neto_mini"].sum().reindex(clean_tick_dates, fill_value=0.0)
            st = _portfolio_stats_from_daily(ser, len(clean_tick_dates))
            corr0 = float(np.corrcoef(ser.to_numpy(), d0_ser.to_numpy())[0, 1]) if ser.std() > 0 and d0_ser.std() > 0 else float("nan")
            mod_rows.append({
                "modulo": mod,
                "delta_s": d,
                "n_trades": int(len(sub)),
                "sumR": round(st["sumR"], 3),
                "R_op": round(st["sumR"] / max(len(sub), 1), 4),
                "MaxDD_R": round(st["MaxDD_R"], 3),
                "Sharpe": round(st["Sharpe"], 3),
                "corr_vs_d0": round(corr0, 5),
                "retention_vs_d0": round(st["sumR"] / d0_sum, 4) if abs(d0_sum) > 1e-9 else float("nan"),
            })
    mod_df = pd.DataFrame(mod_rows)
    mod_df.to_csv(OUT_DIR / "subminute_phase_by_module.csv", index=False)

    return {
        "deltas_s": deltas_s,
        "clean_tick_dates": clean_tick_dates,
        "sanity": sanity,
        "summary_df": summary_df,
        "mod_df": mod_df,
        "daily_curves": daily_curves,
    }


def _run_someod_pure_m5_phases(m1_ny: pd.DataFrame, valid_dates: set[int]) -> pd.DataFrame:
    """Pure M5 boundary phase test for SOMEOD across phases p in {0, 1, 2, 3, 4} minutes.

    Anchor dates/session times remain fixed at 09:30 open and 15:55 EOD, while the 5-minute
    resampling bucket grid shifts `(epoch_min - p) // 5`.
    """
    m1 = m1_ny.copy()
    idx = m1.index
    epoch_min = (idx.asi8 // MIN_NS).astype(np.int64)
    min_of_day = (idx.hour * 60 + idx.minute).to_numpy(np.int32)
    date_int = (idx.year * 10000 + idx.month * 100 + idx.day).to_numpy(np.int32)
    opens = m1["open"].to_numpy(np.float64)
    highs = m1["high"].to_numpy(np.float64)
    lows = m1["low"].to_numpy(np.float64)
    closes = m1["close"].to_numpy(np.float64)

    rows = []
    p0_sum: float | None = None
    for p in range(5):
        b = (epoch_min - p) // 5
        chg = np.flatnonzero(b[1:] != b[:-1]) + 1
        starts = np.concatenate((np.array([0], dtype=np.int64), chg))
        ends = np.concatenate((chg, np.array([len(b)], dtype=np.int64)))

        b_open_px = opens[starts]
        b_high = np.maximum.reduceat(highs, starts)
        b_low = np.minimum.reduceat(lows, starts)
        b_close = closes[ends - 1]
        b_open_mod = min_of_day[starts]
        b_date = date_int[starts]

        # Track M5 indicators: EMA12, EMA120, SMA14(TR)
        ema12 = np.nan
        ema120 = np.nan
        prev_c = np.nan
        tr_buf: list[float] = []
        tr_sum = 0.0
        a12 = 2.0 / 13.0
        a120 = 2.0 / 121.0

        trades_r = []
        trades_date = []

        # State of open trade (1 per day, fill on next M5 bar open or intrabar stops on M5 approx/M1)
        pos_side = 0
        entry_px = 0.0
        stop_px = 0.0
        risk_pts = 0.0
        max_fav = 0.0
        pending_entry = 0
        pending_risk = 0.0
        pending_date = 0
        blocked_day = -1

        # Trigger at first full M5 bar opening in [09:30 .. 09:34] -> 570 <= b_open_mod <= 574
        target_open_mod = 570 + p
        for i in range(len(b_close)):
            if pending_entry != 0 and pos_side == 0:
                pos_side = pending_entry
                entry_px = b_open_px[i]
                risk_pts = max(pending_risk, TICK_SIZE_NQ)
                stop_px = entry_px - pos_side * risk_pts
                max_fav = 0.0
                pending_entry = 0

            h_i, l_i, c_i = b_high[i], b_low[i], b_close[i]
            tr = (h_i - l_i) if np.isnan(prev_c) else max(h_i - l_i, abs(h_i - prev_c), abs(l_i - prev_c))
            prev_c = c_i
            ema12 = c_i if np.isnan(ema12) else a12 * c_i + (1.0 - a12) * ema12
            ema120 = c_i if np.isnan(ema120) else a120 * c_i + (1.0 - a120) * ema120
            tr_buf.append(tr)
            tr_sum += tr
            if len(tr_buf) > 14:
                tr_sum -= tr_buf.pop(0)
            atr14 = (tr_sum / 14.0) if len(tr_buf) == 14 else np.nan

            if pos_side != 0:
                # Check stop hit during M5 bar
                if (pos_side > 0 and l_i <= stop_px) or (pos_side < 0 and h_i >= stop_px):
                    pnl = (stop_px - entry_px) * pos_side
                    r_net = (pnl - 1.545) / risk_pts
                    if 20200101 <= pending_date and pending_date in valid_dates:
                        trades_r.append(r_net)
                        trades_date.append(pending_date)
                    pos_side = 0
                else:
                    fav = (h_i - entry_px) if pos_side > 0 else (entry_px - l_i)
                    if fav > max_fav:
                        max_fav = fav
                    close_mod = b_open_mod[i] + 5
                    if close_mod >= 955:
                        pnl = (c_i - entry_px) * pos_side
                        r_net = (pnl - 1.545) / risk_pts
                        if 20200101 <= pending_date and pending_date in valid_dates:
                            trades_r.append(r_net)
                            trades_date.append(pending_date)
                        pos_side = 0
                    elif not np.isnan(ema120) and max_fav >= 0.5 * risk_pts:
                        cand = round(ema120 * 4.0) * 0.25
                        if pos_side > 0 and cand > stop_px + 0.01 and cand < c_i:
                            stop_px = cand
                        elif pos_side < 0 and cand < stop_px - 0.01 and cand > c_i:
                            stop_px = cand
                continue

            if i >= 121 and not np.isnan(atr14) and atr14 > 0 and not np.isnan(ema12):
                d_i = int(b_date[i])
                if (target_open_mod <= b_open_mod[i] < target_open_mod + 5) and blocked_day != d_i and d_i in valid_dates:
                    side = 1 if c_i > ema12 else (-1 if c_i < ema12 else 0)
                    if side != 0:
                        blocked_day = d_i
                        pending_entry = side
                        pending_risk = max(round((8.0 * atr14) * 4.0) * 0.25, 0.25)
                        pending_date = d_i

        ser = pd.Series(trades_r, index=trades_date).groupby(level=0).sum()
        sum_r = float(ser.sum())
        if p == 0:
            p0_sum = sum_r
        eq = ser.reindex(sorted(valid_dates), fill_value=0.0).cumsum()
        dd = float((eq - eq.cummax()).min())
        rows.append({
            "phase_min": p,
            "n_trades": len(trades_r),
            "sumR": round(sum_r, 3),
            "R_op": round(sum_r / max(len(trades_r), 1), 4),
            "MaxDD_R": round(dd, 3),
            "retention_vs_p0": round(sum_r / p0_sum, 4) if p0_sum else float("nan"),
        })
    df_out = pd.DataFrame(rows)
    df_out.to_csv(OUT_DIR / "htf_phase_someod.csv", index=False)
    return df_out


def run_experiment_b() -> dict[str, object]:
    """Experiment B: Multi-minute shifts dM in {-2,-1,0,+1,+2,+3,+4} over 2020-2026 M1 + pure HTF M5 SOMEOD."""
    print("[Exp B] Loading canonical M1 >= 2018-01-01 for 2020-2026 multi-minute shift test...")
    m1_full = _load_canonical_m1_close("2018-01-01")
    deltas_m = [-2, -1, 0, 1, 2, 3, 4]
    base_ns = m1_full["close_utc_ns"].to_numpy(np.int64)
    jobs: list[tuple[str, Path, int, Path, Path]] = []

    print("[Exp B] Writing 7 shifted M1 CSV feeds via pyarrow.csv...", flush=True)
    for dm in deltas_m:
        shifted_ns = base_ns - np.int64(dm) * np.int64(MIN_NS)
        csv_p = SCRATCH_WORK / f"expB_dm_{dm:+d}.csv"
        tr_p = SCRATCH_WORK / f"expB_dm_{dm:+d}_trades.csv"
        dy_p = SCRATCH_WORK / f"expB_dm_{dm:+d}_daily.csv"
        df_s = pd.DataFrame({
            "close_utc_ns": shifted_ns,
            "o": m1_full["o"].to_numpy(np.float64),
            "h": m1_full["h"].to_numpy(np.float64),
            "l": m1_full["l"].to_numpy(np.float64),
            "c": m1_full["c"].to_numpy(np.float64),
            "v": m1_full["v"].to_numpy(np.float64),
        })
        _write_m1_csv(df_s, csv_p)
        jobs.append((f"dm{dm:+d}", csv_p, 20200101, tr_p, dy_p))

    t0 = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
        for _ in ex.map(_run_verify_exe, jobs):
            pass
    print(f"  Exp B C# runs ({len(jobs)}) done in {time.perf_counter() - t0:.1f}s.")

    # Build clean evaluation day set 20200101..20261117 excluding sesion_excluida
    raw0 = pd.read_csv(SCRATCH_WORK / "expB_dm_+0_trades.csv")
    all_eval_days = sorted({
        int(f)
        for f in raw0["fecha_int"].unique()
        if int(f) >= 20200101 and not sesion_excluida("NQ", int(f)) and a5_bloque(int(f)) != "TERMINAL"
    })
    clean_set = set(all_eval_days)

    modules = [
        "R_osc30_end660_ATR50",
        "Z_b15_e20_eff40_ATR50",
        "T_stop100_BE15R_calFalse",
        "V_nm25_noCap_mae30",
        "W_slope_allowReFalse_ATR25",
        "N_d5_fbTrue_ATR25",
        "SOMEOD_ext_NQ",
    ]
    rows = []
    base_sums: dict[tuple[str, str], float] = {}
    for dm in deltas_m:
        df = pd.read_csv(SCRATCH_WORK / f"expB_dm_{dm:+d}_trades.csv")
        df = df[df["fecha_int"].isin(clean_set)].copy()
        for port in ["CORE5", "P7"]:
            sub = df[df["portfolio"] == port]
            ser = sub.groupby("fecha_int")["R_neto_mini"].sum().reindex(all_eval_days, fill_value=0.0)
            st = _portfolio_stats_from_daily(ser, len(all_eval_days))
            if dm == 0:
                base_sums[("PORT", port)] = st["sumR"]
            b_val = base_sums.get(("PORT", port), st["sumR"])
            rows.append({
                "kind": "PORTFOLIO",
                "name": port,
                "delta_min": dm,
                "n_trades": int(len(sub)),
                "sumR": round(st["sumR"], 3),
                "R_op": round(st["sumR"] / max(len(sub), 1), 4),
                "R_mes": round(st["R_mes"], 3),
                "Sharpe": round(st["Sharpe"], 3),
                "MaxDD_R": round(st["MaxDD_R"], 3),
                "retention_vs_0": round(st["sumR"] / b_val, 4) if abs(b_val) > 1e-9 else float("nan"),
            })
        for mod in modules:
            sub = df[(df["portfolio"] == "INDEP") & (df["modulo"] == mod)]
            ser = sub.groupby("fecha_int")["R_neto_mini"].sum().reindex(all_eval_days, fill_value=0.0)
            st = _portfolio_stats_from_daily(ser, len(all_eval_days))
            if dm == 0:
                base_sums[("MOD", mod)] = st["sumR"]
            b_val = base_sums.get(("MOD", mod), st["sumR"])
            rows.append({
                "kind": "MODULE",
                "name": mod,
                "delta_min": dm,
                "n_trades": int(len(sub)),
                "sumR": round(st["sumR"], 3),
                "R_op": round(st["sumR"] / max(len(sub), 1), 4),
                "R_mes": round(st["R_mes"], 3),
                "Sharpe": round(st["Sharpe"], 3),
                "MaxDD_R": round(st["MaxDD_R"], 3),
                "retention_vs_0": round(st["sumR"] / b_val, 4) if abs(b_val) > 1e-9 else float("nan"),
            })

    # Re-pass once to ensure retention_vs_0 is computed cleanly even for negative delta_min
    b_df = pd.DataFrame(rows)
    zero_map = b_df[b_df["delta_min"] == 0].set_index(["kind", "name"])["sumR"].to_dict()
    b_df["retention_vs_0"] = [
        round(r["sumR"] / zero_map[(r["kind"], r["name"])], 4) if abs(zero_map[(r["kind"], r["name"])]) > 1e-9 else float("nan")
        for _, r in b_df.iterrows()
    ]
    b_df.to_csv(OUT_DIR / "multiminute_shift_summary.csv", index=False)

    # Pure M5 SOMEOD phase on NY M1 2020..2026
    m1_pq = pd.read_parquet(M1_PARQUET)
    if m1_pq.index.tz is not None:
        m1_pq.index = m1_pq.index.tz_convert("America/New_York").tz_localize(None)
    else:
        m1_pq.index = m1_pq.index.tz_localize("UTC").tz_convert("America/New_York").tz_localize(None)
    m1_pq = m1_pq[m1_pq.index >= pd.Timestamp("2019-10-01")].copy()
    someod_df = _run_someod_pure_m5_phases(m1_pq, clean_set)

    return {"multimin_df": b_df, "someod_df": someod_df, "n_eval_days": len(all_eval_days)}


def run_experiment_c(m1_2023: pd.DataFrame, cme_sellado_sub: pd.DataFrame) -> dict[str, object]:
    """Experiment C: Real CFD USATECHIDXUSD tick spread audit & comparison vs CME NQ Sellado."""
    pf_usa = pq.ParquetFile(USATECH_TICKS)
    print(f"[Exp C] Streaming USATECHIDXUSD ticks ({pf_usa.num_row_groups} RGs, {pf_usa.metadata.num_rows:,} rows)...")
    deltas_cfd = [0, 15, 30, 45]
    res_cfd = StreamingShiftResampler(deltas_cfd)

    window_sp: dict[str, list[np.ndarray]] = {
        "ALL": [],
        "OPEN_0930_1000": [],
        "RTH_CORE_1000_1530": [],
        "CLOSE_1530_1600": [],
        "ETH_OTHER": [],
    }
    first_mid = None
    last_ts = None

    for rgi in range(pf_usa.num_row_groups):
        df = pf_usa.read_row_group(rgi, columns=["time_utc_ns", "bid", "ask"]).to_pandas()
        ts = df["time_utc_ns"].to_numpy(np.int64)
        bid = df["bid"].to_numpy(np.float64)
        ask = df["ask"].to_numpy(np.float64)
        mid = 0.5 * (bid + ask)
        sp = ask - bid
        if first_mid is None:
            first_mid = float(mid[0])
        last_ts = int(ts[-1])
        vol = np.ones(len(ts), dtype=np.float64)
        res_cfd.feed_chunk(ts, mid, vol)

        # NY local window classification (vectorized via pd.DatetimeIndex tz_convert)
        dt_ny = pd.to_datetime(ts, unit="ns", utc=True).tz_convert("America/New_York")
        tod_min = dt_ny.hour.to_numpy(np.int32) * 60 + dt_ny.minute.to_numpy(np.int32)
        m_open = (tod_min >= 570) & (tod_min < 600)
        m_core = (tod_min >= 600) & (tod_min < 930)
        m_close = (tod_min >= 930) & (tod_min < 960)
        m_eth = ~(m_open | m_core | m_close)
        window_sp["ALL"].append(sp)
        window_sp["OPEN_0930_1000"].append(sp[m_open])
        window_sp["RTH_CORE_1000_1530"].append(sp[m_core])
        window_sp["CLOSE_1530_1600"].append(sp[m_close])
        window_sp["ETH_OTHER"].append(sp[m_eth])

    bars_cfd = res_cfd.finish()
    spread_rows = []
    med_sp_by_win = {}
    for wname, arrs in window_sp.items():
        v = np.concatenate(arrs) if arrs else np.array([], dtype=np.float64)
        med = float(np.median(v)) if len(v) else 0.0
        med_sp_by_win[wname] = med
        spread_rows.append({
            "window": wname,
            "n_ticks": int(len(v)),
            "mean_pts": round(float(v.mean()), 4),
            "median_pts": round(med, 4),
            "p90_pts": round(float(np.quantile(v, 0.90)), 4),
            "p99_pts": round(float(np.quantile(v, 0.99)), 4),
            "max_pts": round(float(v.max()), 4),
        })
    spread_df = pd.DataFrame(spread_rows)
    print("  [Exp C Spread]:\n", spread_df.to_string(index=False))

    # Splice basis offset at 2026-10-01 00:00 UTC (2026-09-30 23:59 close)
    first_cfd_ns = int(bars_cfd[0]["close_utc_ns"].iloc[0])
    warmup = m1_2023[m1_2023["close_utc_ns"] < first_cfd_ns].copy()
    basis_gap = float(warmup["c"].iloc[-1]) - float(first_mid)
    for col in ["o", "h", "l", "c"]:
        warmup[col] = warmup[col] - basis_gap
    print(f"  [Exp C Splice] Futures->Cash basis gap at 2026-10-01 00:00Z = {basis_gap:+.2f} pts")

    jobs = []
    for d in deltas_cfd:
        combined = pd.concat([warmup, bars_cfd[d]], ignore_index=True)
        combined = combined.sort_values("close_utc_ns").drop_duplicates("close_utc_ns", keep="last").reset_index(drop=True)
        csv_p = SCRATCH_WORK / f"expC_cfd_d{d:02d}.csv"
        tr_p = SCRATCH_WORK / f"expC_cfd_d{d:02d}_trades.csv"
        dy_p = SCRATCH_WORK / f"expC_cfd_d{d:02d}_daily.csv"
        _write_m1_csv(combined, csv_p)
        jobs.append((f"cfd_d{d:02d}", csv_p, 20261001, tr_p, dy_p))

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
        for _ in ex.map(_run_verify_exe, jobs):
            pass

    # Compare over clean 31 Sellado dates 20261001..20261113 (excluding 20261007)
    sellado_dates = sorted({
        int(f) for f in cme_sellado_sub["fecha_int"].unique()
        if 20261001 <= int(f) <= 20261113 and not sesion_excluida("NQ", int(f))
    })
    sell_set = set(sellado_dates)

    def _window_spread_vec(en_ny_col: pd.Series) -> np.ndarray:
        dt = pd.to_datetime(en_ny_col)
        tod = dt.dt.hour.to_numpy() * 60 + dt.dt.minute.to_numpy()
        out = np.full(len(tod), med_sp_by_win["ETH_OTHER"], dtype=np.float64)
        out[(tod >= 570) & (tod < 600)] = med_sp_by_win["OPEN_0930_1000"]
        out[(tod >= 600) & (tod < 930)] = med_sp_by_win["RTH_CORE_1000_1530"]
        out[(tod >= 930) & (tod < 960)] = med_sp_by_win["CLOSE_1530_1600"]
        return out

    comp_rows = []
    for port in ["CORE5", "P7"]:
        cme_p = cme_sellado_sub[cme_sellado_sub["portfolio"] == port]
        comp_rows.append({
            "feed": "CME_NQ_Sellado_d00",
            "portfolio": port,
            "n_trades": int(len(cme_p)),
            "sumR_gross": round(float(cme_p["R_bruto"].sum()), 3),
            "sumR_net": round(float(cme_p["R_neto_mini"].sum()), 3),
            "avg_fric_R": round(float((cme_p["R_bruto"] - cme_p["R_neto_mini"]).mean()), 4) if len(cme_p) else 0.0,
        })
        for d in deltas_cfd:
            cfd_all = pd.read_csv(SCRATCH_WORK / f"expC_cfd_d{d:02d}_trades.csv")
            cfd_p = cfd_all[(cfd_all["portfolio"] == port) & (cfd_all["fecha_int"].isin(sell_set))].copy()
            sp_vec = _window_spread_vec(cfd_p["en_ny"])
            r_net_cfd = cfd_p["R_bruto"].to_numpy(np.float64) - (sp_vec / np.maximum(cfd_p["riesgo_pts"].to_numpy(np.float64), 1.0))
            comp_rows.append({
                "feed": f"CFD_USATECH_d{d:02d}",
                "portfolio": port,
                "n_trades": int(len(cfd_p)),
                "sumR_gross": round(float(cfd_p["R_bruto"].sum()), 3),
                "sumR_net": round(float(r_net_cfd.sum()), 3),
                "avg_fric_R": round(float((cfd_p["R_bruto"].to_numpy(np.float64) - r_net_cfd).mean()), 4) if len(cfd_p) else 0.0,
            })

    comp_df = pd.DataFrame(comp_rows)
    spread_df["section"] = "SPREAD"
    comp_df["section"] = "CFD_VS_CME"
    combined_c = pd.concat([spread_df, comp_df], ignore_index=True)
    combined_c.to_csv(OUT_DIR / "cfd_usatech_spread_and_comparison.csv", index=False)

    return {
        "spread_df": spread_df,
        "comp_df": comp_df,
        "basis_gap": basis_gap,
        "n_sellado_days": len(sellado_dates),
    }


def _plot_exp_a(res_a: dict[str, object]) -> None:
    deltas_s = res_a["deltas_s"]
    summary_df: pd.DataFrame = res_a["summary_df"]
    mod_df: pd.DataFrame = res_a["mod_df"]
    daily_curves: dict[str, dict[int, pd.Series]] = res_a["daily_curves"]

    plt = _plt()
    fig, axes = plt.subplots(2, 2, figsize=(15, 9.5), facecolor=BG_FIG)
    fig.subplots_adjust(hspace=0.34, wspace=0.22, top=0.90, bottom=0.07, left=0.06, right=0.97)
    fig.suptitle(
        "Barrido de Fase Sub-Minuto (delta in {0, 5, ..., 55}s) en 322 Sesiones Reales CME NQ (2025-08 .. 2026-11)",
        color=FG_TEXT,
        fontsize=14,
        fontweight="bold",
    )

    for ax in axes.flat:
        ax.set_facecolor(BG_AX)
        ax.tick_params(colors=MUTED_TEXT, labelsize=9)
        ax.grid(True, color=GRID_COL, alpha=0.45, linewidth=0.7)
        for sp in ax.spines.values():
            sp.set_color("#2e3f47")

    # Top-left: Core5_AltaConv 12-phase equity fan + ensemble mean
    ax = axes[0, 0]
    c5_curves = []
    for d in deltas_s:
        eq = daily_curves["CORE5"][d].cumsum().to_numpy()
        c5_curves.append(eq)
        if d == 0:
            ax.plot(eq, color=ACCENT_GOLD, lw=2.2, label="delta=0s (canonico)", zorder=5)
        else:
            ax.plot(eq, color=ACCENT_TEAL, alpha=0.28, lw=1.0, zorder=2)
    ens5 = np.mean(c5_curves, axis=0)
    ax.plot(ens5, color="#ffffff", lw=1.8, ls="--", label="Promedio 12 fases", zorder=6)
    ax.set_title("Core5_AltaConv: Abanico Equity (12 fases)", color=FG_TEXT, fontsize=11, fontweight="bold")
    ax.set_xlabel("Sesiones reales con ticks (N=322)", color=MUTED_TEXT, fontsize=9)
    ax.set_ylabel("Equity acumulada (R neto mini)", color=MUTED_TEXT, fontsize=9)
    ax.legend(facecolor=BG_AX, edgecolor=GRID_COL, labelcolor=FG_TEXT, fontsize=8.5)

    # Top-right: P_OPT_SF_v2 12-phase equity fan + ensemble mean
    ax = axes[0, 1]
    p7_curves = []
    for d in deltas_s:
        eq = daily_curves["P7"][d].cumsum().to_numpy()
        p7_curves.append(eq)
        if d == 0:
            ax.plot(eq, color=ACCENT_GOLD, lw=2.2, label="delta=0s (canonico)", zorder=5)
        else:
            ax.plot(eq, color=ACCENT_BLUE, alpha=0.28, lw=1.0, zorder=2)
    ens7 = np.mean(p7_curves, axis=0)
    ax.plot(ens7, color="#ffffff", lw=1.8, ls="--", label="Promedio 12 fases", zorder=6)
    ax.set_title("P_OPT_SF_v2 (Core7): Abanico Equity (12 fases)", color=FG_TEXT, fontsize=11, fontweight="bold")
    ax.set_xlabel("Sesiones reales con ticks (N=322)", color=MUTED_TEXT, fontsize=9)
    ax.set_ylabel("Equity acumulada (R neto mini)", color=MUTED_TEXT, fontsize=9)
    ax.legend(facecolor=BG_AX, edgecolor=GRID_COL, labelcolor=FG_TEXT, fontsize=8.5)

    # Bottom-left: Total sumR by phase delta_s (Core5 vs P7)
    ax = axes[1, 0]
    x = np.arange(len(deltas_s))
    w = 0.38
    s5 = summary_df[summary_df["portfolio"] == "CORE5"].sort_values("delta_s")["sumR"].to_numpy()
    s7 = summary_df[summary_df["portfolio"] == "P7"].sort_values("delta_s")["sumR"].to_numpy()
    ax.bar(x - w / 2, s5, width=w, color=ACCENT_TEAL, label=f"Core5 (med={np.median(s5):+.1f}R)")
    ax.bar(x + w / 2, s7, width=w, color=ACCENT_BLUE, label=f"P_OPT_SF_v2 (med={np.median(s7):+.1f}R)")
    ax.axhline(float(s5[0]), color=ACCENT_TEAL, ls=":", lw=1.0, alpha=0.8)
    ax.axhline(0.0, color="#6c7d86", lw=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{d}s" for d in deltas_s])
    ax.set_title("Rendimiento Total (R) por Fase de Apertura delta", color=FG_TEXT, fontsize=11, fontweight="bold")
    ax.set_ylabel("Sum R Neto Mini", color=MUTED_TEXT, fontsize=9)
    ax.legend(facecolor=BG_AX, edgecolor=GRID_COL, labelcolor=FG_TEXT, fontsize=8.5)

    # Bottom-right: Per-module phase dispersion (min / median / max + delta=0)
    ax = axes[1, 1]
    mods = ["T_stop100_BE15R_calFalse", "SOMEOD_ext_NQ", "R_osc30_end660_ATR50", "Z_b15_e20_eff40_ATR50", "N_d5_fbTrue_ATR25", "W_slope_allowReFalse_ATR25", "V_nm25_noCap_mae30"]
    short_names = ["T (ORB15)", "SOMEOD (M5)", "R (M10)", "Z (Zeta)", "N (NDay)", "W (VWAP)", "V (Vault)"]
    y_pos = np.arange(len(mods))
    mins, meds, maxs, d0s = [], [], [], []
    for m in mods:
        vals = mod_df[mod_df["modulo"] == m].sort_values("delta_s")["sumR"].to_numpy()
        mins.append(vals.min())
        meds.append(np.median(vals))
        maxs.append(vals.max())
        d0s.append(vals[0])
    ax.hlines(y_pos, mins, maxs, color=ACCENT_TEAL, lw=4.0, alpha=0.65, label="Rango Min-Max (12 fases)")
    ax.scatter(meds, y_pos, color="#ffffff", s=45, zorder=5, label="Mediana 12 fases")
    ax.scatter(d0s, y_pos, color=ACCENT_GOLD, marker="D", s=40, zorder=6, label="delta=0s")
    ax.axvline(0.0, color=ACCENT_CORAL, ls="--", lw=1.0)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(short_names)
    ax.invert_yaxis()
    ax.set_title("Dispersion por Modulo Independiente (Min / Mediana / Max)", color=FG_TEXT, fontsize=11, fontweight="bold")
    ax.set_xlabel("Sum R Neto Mini (322 dias)", color=MUTED_TEXT, fontsize=9)
    ax.legend(facecolor=BG_AX, edgecolor=GRID_COL, labelcolor=FG_TEXT, fontsize=8.5)

    p1 = OUT_DIR / "bar_phase_shift_subminute_0_55s.png"
    p2 = ARTIFACT_DIR / "bar_phase_shift_subminute_0_55s.png"
    fig.savefig(p1, dpi=150, facecolor=BG_FIG)
    shutil.copy2(p1, p2)
    plt.close(fig)


def _plot_exp_b_c(res_b: dict[str, object], res_c: dict[str, object]) -> None:
    b_df: pd.DataFrame = res_b["multimin_df"]
    someod_df: pd.DataFrame = res_b["someod_df"]
    sp_df: pd.DataFrame = res_c["spread_df"]
    comp_df: pd.DataFrame = res_c["comp_df"]

    plt = _plt()
    fig, axes = plt.subplots(2, 2, figsize=(15, 9.5), facecolor=BG_FIG)
    fig.subplots_adjust(hspace=0.35, wspace=0.22, top=0.90, bottom=0.08, left=0.06, right=0.97)
    fig.suptitle(
        "Desplazamiento Multi-Minuto (2020-2026), Fase Pura M5 SOMEOD y Auditoria CFD USATECHIDXUSD",
        color=FG_TEXT,
        fontsize=14,
        fontweight="bold",
    )

    for ax in axes.flat:
        ax.set_facecolor(BG_AX)
        ax.tick_params(colors=MUTED_TEXT, labelsize=9)
        ax.grid(True, color=GRID_COL, alpha=0.45, linewidth=0.7)
        for sp in ax.spines.values():
            sp.set_color("#2e3f47")

    # Top-left: Multi-minute clock shift for Core5 & P7 + key modules
    ax = axes[0, 0]
    for name, kind, col, lw in [
        ("CORE5", "PORTFOLIO", ACCENT_TEAL, 2.4),
        ("P7", "PORTFOLIO", ACCENT_BLUE, 2.2),
        ("T_stop100_BE15R_calFalse", "MODULE", ACCENT_GOLD, 1.5),
        ("SOMEOD_ext_NQ", "MODULE", ACCENT_CORAL, 1.5),
        ("R_osc30_end660_ATR50", "MODULE", ACCENT_GREEN, 1.5),
    ]:
        sub = b_df[(b_df["kind"] == kind) & (b_df["name"] == name)].sort_values("delta_min")
        ax.plot(sub["delta_min"], sub["retention_vs_0"] * 100.0, marker="o", color=col, lw=lw, label=name.split("_")[0])
    ax.axhline(100.0, color="#ffffff", ls=":", lw=0.9, alpha=0.6)
    ax.axhline(50.0, color=ACCENT_CORAL, ls="--", lw=0.9, alpha=0.6)
    ax.set_title("Retencion (% vs dM=0) ante Shift Reloj {-2..+4 min} (2020-2026)", color=FG_TEXT, fontsize=11, fontweight="bold")
    ax.set_xlabel("Desplazamiento reloj M1 (minutos)", color=MUTED_TEXT, fontsize=9)
    ax.set_ylabel("Retencion sumR (%)", color=MUTED_TEXT, fontsize=9)
    ax.legend(facecolor=BG_AX, edgecolor=GRID_COL, labelcolor=FG_TEXT, fontsize=8.5, ncol=2)

    # Top-right: SOMEOD pure M5 phase p in {0..4} min
    ax = axes[0, 1]
    ax.bar(someod_df["phase_min"], someod_df["sumR"], color=[ACCENT_GOLD if p == 0 else ACCENT_TEAL for p in someod_df["phase_min"]], width=0.55)
    for _, r in someod_df.iterrows():
        ax.text(r["phase_min"], r["sumR"] + 1.5, f"{r['sumR']:+.1f}R\n({r['retention_vs_p0']*100:.0f}%)", ha="center", va="bottom", color=FG_TEXT, fontsize=8.5)
    ax.set_xticks(someod_df["phase_min"])
    ax.set_xticklabels([f"p=+{int(p)}m" for p in someod_df["phase_min"]])
    ax.set_ylim(0, max(someod_df["sumR"].max() * 1.22, 10))
    ax.set_title("SOMEOD: Fase Pura Grilla M5 (sin mover 09:30/15:55)", color=FG_TEXT, fontsize=11, fontweight="bold")
    ax.set_ylabel("Sum R Neto Mini (2020-2026)", color=MUTED_TEXT, fontsize=9)

    # Bottom-left: USATECHIDXUSD real spread profile
    ax = axes[1, 0]
    w_order = ["OPEN_0930_1000", "RTH_CORE_1000_1530", "CLOSE_1530_1600", "ETH_OTHER", "ALL"]
    w_lbl = ["09:30-10:00", "10:00-15:30", "15:30-16:00", "ETH", "Global"]
    sp_sub = sp_df.set_index("window").reindex(w_order)
    x = np.arange(len(w_order))
    ax.bar(x - 0.18, sp_sub["median_pts"], width=0.35, color=ACCENT_TEAL, label="Mediana spread (pts)")
    ax.bar(x + 0.18, sp_sub["p90_pts"], width=0.35, color=ACCENT_CORAL, label="p90 spread (pts)")
    ax.axhline(1.545, color=ACCENT_GOLD, ls="--", lw=1.2, label="Friccion futuros (1.545 pts)")
    ax.set_xticks(x)
    ax.set_xticklabels(w_lbl)
    ax.set_title("USATECHIDXUSD Spread Real Observado (Oct-Nov 2026)", color=FG_TEXT, fontsize=11, fontweight="bold")
    ax.set_ylabel("Puntos Nasdaq", color=MUTED_TEXT, fontsize=9)
    ax.legend(facecolor=BG_AX, edgecolor=GRID_COL, labelcolor=FG_TEXT, fontsize=8.5)

    # Bottom-right: CFD USATECH vs CME NQ Sellado Core5 net comparison
    ax = axes[1, 1]
    c5_c = comp_df[comp_df["portfolio"] == "CORE5"].copy()
    x2 = np.arange(len(c5_c))
    ax.bar(x2 - 0.18, c5_c["sumR_gross"], width=0.35, color=MUTED_TEXT, alpha=0.75, label="R Bruto")
    ax.bar(x2 + 0.18, c5_c["sumR_net"], width=0.35, color=ACCENT_GREEN, label="R Neto real (fut o spread)")
    ax.axhline(0.0, color="#6c7d86", lw=0.8)
    ax.set_xticks(x2)
    ax.set_xticklabels([s.replace("CME_NQ_Sellado_", "CME ").replace("CFD_USATECH_", "CFD ") for s in c5_c["feed"]], rotation=15)
    ax.set_title("Sellado Oct-Nov 2026 (31d): Core5 CME NQ vs CFD USATECH", color=FG_TEXT, fontsize=11, fontweight="bold")
    ax.set_ylabel("Sum R (bruto vs neto)", color=MUTED_TEXT, fontsize=9)
    ax.legend(facecolor=BG_AX, edgecolor=GRID_COL, labelcolor=FG_TEXT, fontsize=8.5)

    p1 = OUT_DIR / "bar_phase_shift_multiminute_htf.png"
    p2 = ARTIFACT_DIR / "bar_phase_shift_multiminute_htf.png"
    fig.savefig(p1, dpi=150, facecolor=BG_FIG)
    shutil.copy2(p1, p2)
    plt.close(fig)


def _write_report(res_a: dict[str, object], res_b: dict[str, object], res_c: dict[str, object]) -> None:
    s_df: pd.DataFrame = res_a["summary_df"]
    m_df: pd.DataFrame = res_a["mod_df"]
    b_df: pd.DataFrame = res_b["multimin_df"]
    someod_df: pd.DataFrame = res_b["someod_df"]
    sp_df: pd.DataFrame = res_c["spread_df"]
    comp_df: pd.DataFrame = res_c["comp_df"]
    sanity = res_a["sanity"]

    c5_a = s_df[s_df["portfolio"] == "CORE5"]
    p7_a = s_df[s_df["portfolio"] == "P7"]
    c5_pos = int((c5_a["sumR"] > 0).sum())
    p7_pos = int((p7_a["sumR"] > 0).sum())

    # Module summary across 12 subminute phases
    mod_sum_lines = []
    for mod in [
        "R_osc30_end660_ATR50",
        "Z_b15_e20_eff40_ATR50",
        "T_stop100_BE15R_calFalse",
        "V_nm25_noCap_mae30",
        "W_slope_allowReFalse_ATR25",
        "N_d5_fbTrue_ATR25",
        "SOMEOD_ext_NQ",
    ]:
        sub = m_df[m_df["modulo"] == mod].sort_values("delta_s")
        vals = sub["sumR"].to_numpy()
        d0_v = float(vals[0])
        ret = (vals.mean() / d0_v * 100.0) if abs(d0_v) > 1e-9 else float("nan")
        corrs = sub[sub["delta_s"] > 0]["corr_vs_d0"].mean()
        pos_cnt = int((vals > 0).sum())
        mod_sum_lines.append(
            f"| `{mod}` | {int(round(sub['n_trades'].mean()))} | {d0_v:+.2f} | {np.median(vals):+.2f} | "
            f"[{vals.min():+.2f}, {vals.max():+.2f}] | {pos_cnt}/12 | {ret:.1f}% | {corrs:.3f} |"
        )

    lines = [
        "# Analisis Bar-Open Phase Shift (CME NQ y CFD USATECHIDXUSD)",
        "",
        f"- **Muestra Experimento A (Sub-minuto `0..55s`)**: `{len(res_a['clean_tick_dates'])}` sesiones reales con ticks CME `NQ` (`291` K30 `2025-08-05..2026-09-25` + `31` Sellado `2026-10-01..2026-11-13`, excluyendo puente M1 y `2026-10-07`). Warmup previo desde `2023-01-01` con M1 canonico.",
        "- **Convencion tecnica sub-minuto**: cada barra desplazada `[k*60+delta, (k+1)*60+delta)` se etiqueta con cierre nominal `(k+1)*60s` (`:00` seg) para preservar `ExactMinute == true` en los motores C# y aislar el efecto puro de mover el corte de las velas.",
        f"- **Sanity Check (`M1 canonico` vs `ticks delta=0s`, 322 dias)**: Core5 `canon={sanity['CORE5']['canon_n']} ({sanity['CORE5']['canon_R']:+.2f}R)` vs `delta0={sanity['CORE5']['delta0_n']} ({sanity['CORE5']['delta0_R']:+.2f}R)`; P7 `canon={sanity['P7']['canon_n']} ({sanity['P7']['canon_R']:+.2f}R)` vs `delta0={sanity['P7']['delta0_n']} ({sanity['P7']['delta0_R']:+.2f}R)`.",
        "",
        "## 1. Experimento A: Barrido Sub-Minuto `delta in {0, 5, ..., 55}s` (322 dias)",
        "",
        f"- **Core5_AltaConv**: `delta=0s = {c5_a.iloc[0]['sumR']:+.2f} R` | mediana 12 fases = `{c5_a['sumR'].median():+.2f} R` (`{c5_a['sumR'].min():+.2f}` .. `{c5_a['sumR'].max():+.2f} R`), **{c5_pos}/12 fases positivas**, retencion media = `{c5_a['retention_vs_d0'].mean()*100:.1f}%`, MaxDD rango = `[{c5_a['MaxDD_R'].min():.2f}, {c5_a['MaxDD_R'].max():.2f}] R`.",
        f"- **P_OPT_SF_v2 (Core7)**: `delta=0s = {p7_a.iloc[0]['sumR']:+.2f} R` | mediana 12 fases = `{p7_a['sumR'].median():+.2f} R` (`{p7_a['sumR'].min():+.2f}` .. `{p7_a['sumR'].max():+.2f} R`), **{p7_pos}/12 fases positivas**, retencion media = `{p7_a['retention_vs_d0'].mean()*100:.1f}%`.",
        "",
        "| Modulo Independiente | N medio | delta=0s (R) | Mediana 12f (R) | Rango [Min, Max] | Fases > 0 | Retencion Media vs d0 | Corr diaria vs d0 |",
        "|---|---:|---:|---:|---|---:|---:|---:|",
        *mod_sum_lines,
        "",
        "## 2. Experimento B: Shifts Multi-Minuto (`2020-2026`) y Fase Pura M5 `SOMEOD`",
        "",
        f"- Evaluado sobre `{res_b['n_eval_days']}` sesiones validas `2020-01-01..2026-11-17` (M1 canonico).",
        "",
        "| Cartera / Modulo | dM=-2m | dM=-1m | dM=0m (Base) | dM=+1m | dM=+2m | dM=+3m | dM=+4m |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for kind, nm in [
        ("PORTFOLIO", "CORE5"),
        ("PORTFOLIO", "P7"),
        ("MODULE", "T_stop100_BE15R_calFalse"),
        ("MODULE", "R_osc30_end660_ATR50"),
        ("MODULE", "Z_b15_e20_eff40_ATR50"),
        ("MODULE", "SOMEOD_ext_NQ"),
        ("MODULE", "N_d5_fbTrue_ATR25"),
        ("MODULE", "W_slope_allowReFalse_ATR25"),
        ("MODULE", "V_nm25_noCap_mae30"),
    ]:
        sub = b_df[(b_df["kind"] == kind) & (b_df["name"] == nm)].set_index("delta_min")
        cells = [
            f"{sub.loc[dm, 'sumR']:+.1f}R ({sub.loc[dm, 'retention_vs_0']*100:.0f}%)"
            for dm in [-2, -1, 0, 1, 2, 3, 4]
        ]
        lines.append(f"| `{nm}` | " + " | ".join(cells) + " |")

    lines += [
        "",
        "### Fase Pura M5 en `SOMEOD` (sin mover 09:30 ni EOD 15:55, `2020-2026`)",
        "",
        "| Fase M5 | N ops | Sum R | R/op | MaxDD R | Retencion vs p=0 |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for _, r in someod_df.iterrows():
        lines.append(
            f"| `p=+{int(r['phase_min'])}m` | {int(r['n_trades'])} | {r['sumR']:+.2f} | {r['R_op']:+.4f} | {r['MaxDD_R']:+.2f} | {r['retention_vs_p0']*100:.1f}% |"
        )

    lines += [
        "",
        "## 3. Experimento C: Auditoria Ticks Reales CFD `USATECHIDXUSD` (`2026-10-01..2026-11-15`)",
        "",
        f"- **Basis futuros vs cash al empalme (`2026-10-01 00:00Z`)**: `{res_c['basis_gap']:+.2f}` pts (warmup nivelado para continuidad de ATR/EMA sin salto).",
        f"- **Comparativa Sellado limpio (`{res_c['n_sellado_days']}` sesiones, `2026-10-01..2026-11-13` excl. `2026-10-07`)** aplicando friccion real por ventana en CFD (`$0` comision, solo spread mediano observado):",
        "",
        "| Ventana Horaria NY | Ticks | Spread Medio | Mediana | p90 | p99 | Max |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for _, r in sp_df.iterrows():
        lines.append(
            f"| `{r['window']}` | {int(r['n_ticks']):,} | {r['mean_pts']:.3f} | {r['median_pts']:.3f} | {r['p90_pts']:.3f} | {r['p99_pts']:.3f} | {r['max_pts']:.2f} |"
        )
    lines += [
        "",
        "| Feed / Fase | Cartera | N ops | Sum R Bruto | Sum R Neto | Friccion media (R) |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for _, r in comp_df.iterrows():
        lines.append(
            f"| `{r['feed']}` | `{r['portfolio']}` | {int(r['n_trades'])} | {r['sumR_gross']:+.2f} | {r['sumR_net']:+.2f} | {r['avg_fric_R']:.4f} |"
        )

    (OUT_DIR / "RESULTADO.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    SCRATCH_WORK.mkdir(parents=True, exist_ok=True)

    print("Loading canonical M1 warmup (>= 2023-01-01)...")
    m1_2023 = _load_canonical_m1_close("2023-01-01")

    res_a = run_experiment_a(m1_2023)
    res_b = run_experiment_b()

    cme_delta0 = pd.read_csv(SCRATCH_WORK / "expA_delta_00_trades.csv")
    cme_sellado_dates = {
        int(f) for f in res_a["clean_tick_dates"] if int(f) >= 20261001
    }
    cme_sellado_sub = cme_delta0[cme_delta0["fecha_int"].isin(cme_sellado_dates)].copy()

    res_c = run_experiment_c(m1_2023, cme_sellado_sub)
    _plot_exp_a(res_a)
    _plot_exp_b_c(res_b, res_c)
    _write_report(res_a, res_b, res_c)
    print(f"DONE -> {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
