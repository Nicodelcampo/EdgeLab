"""Causal 25-trade-bar EMA3 research primitives.

Research only. Signals use completed bars; fills are evaluated on subsequent
raw ticks/quotes. Prices are integer exchange ticks. No holdout access here.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable, Sequence

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class GridCell:
    direction: str
    pullback_ticks: int
    pullback_timeout_bars: int
    stop_ticks: int
    target_ticks: int
    breakeven_ticks: int | None
    slippage_ticks_side: int = 1

    def __post_init__(self) -> None:
        if self.direction not in {"NORMAL", "INVERTED"}:
            raise ValueError("direction")
        ints = (self.pullback_ticks, self.pullback_timeout_bars, self.stop_ticks,
                self.target_ticks, self.slippage_ticks_side)
        if any(x < 0 for x in ints) or self.stop_ticks <= 0 or self.target_ticks <= 0:
            raise ValueError("non-positive grid value")
        if self.breakeven_ticks is not None and (
            self.breakeven_ticks <= 0 or self.breakeven_ticks >= self.target_ticks
        ):
            raise ValueError("BE must be positive and strictly below target")

    @property
    def cell_id(self) -> str:
        be = "OFF" if self.breakeven_ticks is None else str(self.breakeven_ticks)
        return (f"{self.direction}_PB{self.pullback_ticks}x{self.pullback_timeout_bars}_"
                f"SL{self.stop_ticks}_TP{self.target_ticks}_BE{be}_S{self.slippage_ticks_side}")


def frozen_grid() -> list[GridCell]:
    """Pre-registered 108-cell grid, including inverted-direction placebo."""
    out: list[GridCell] = []
    for direction in ("NORMAL", "INVERTED"):
        for pb in (0, 25, 50):
            for sl in (90, 200, 300):
                for tp in (150, 300, 450):
                    for be in (None, 90):
                        out.append(GridCell(direction, pb, 20, sl, tp, be))
    assert len(out) == 108
    return out


def ema(values: Sequence[float], period: int) -> np.ndarray:
    x = np.asarray(values, dtype=np.float64)
    if period <= 0 or len(x) == 0:
        raise ValueError("period/values")
    y = np.empty_like(x)
    y[0] = x[0]
    a = 2.0 / (period + 1.0)
    for i in range(1, len(x)):
        y[i] = y[i - 1] + a * (x[i] - y[i - 1])
    return y


def build_25t_bars(ticks: pd.DataFrame, trades_per_bar: int = 25) -> pd.DataFrame:
    """Build bars from ordered trade rows; never cross contract or trade_date."""
    req = {"ts_ns", "price_ticks", "bid_ticks", "ask_ticks", "contract", "trade_date"}
    if not req.issubset(ticks.columns):
        raise ValueError(f"missing columns {sorted(req-set(ticks.columns))}")
    if ticks.empty:
        return pd.DataFrame()
    t = ticks.sort_values(["contract", "trade_date", "ts_ns"], kind="stable").copy()
    if t[list(req)].isna().any().any():
        raise ValueError("null required field")
    if (t.price_ticks <= 0).any() or (t.ask_ticks <= t.bid_ticks).any():
        raise ValueError("invalid price/quote")
    if (t.groupby(["contract", "trade_date"], sort=False).ts_ns.diff().dropna() < 0).any():
        raise ValueError("clock inversion")
    t["bar_no"] = t.groupby(["contract", "trade_date"], sort=False).cumcount() // trades_per_bar
    g = t.groupby(["contract", "trade_date", "bar_no"], sort=False, observed=True)
    b = g.agg(
        start_ns=("ts_ns", "first"), close_ns=("ts_ns", "last"),
        open=("price_ticks", "first"), high=("price_ticks", "max"),
        low=("price_ticks", "min"), close=("price_ticks", "last"),
        trade_count=("price_ticks", "size"),
        start_row=("_row", "first") if "_row" in t else ("ts_ns", "size"),
        end_row=("_row", "last") if "_row" in t else ("ts_ns", "size"),
    ).reset_index()
    if "_row" not in t:
        sizes = b.trade_count.to_numpy(int)
        b["end_row"] = np.cumsum(sizes) - 1
        b["start_row"] = b.end_row - sizes + 1
    b["complete"] = b.trade_count.eq(trades_per_bar)
    return b


def add_emas(bars: pd.DataFrame, periods: tuple[int, int, int] = (200, 500, 2000)) -> pd.DataFrame:
    out = bars.copy()
    for p in periods:
        out[f"ema{p}"] = np.nan
    for _, ix in out.groupby("contract", sort=False).groups.items():
        loc = np.asarray(list(ix), dtype=int)
        close = out.loc[loc, "close"].to_numpy(float)
        for p in periods:
            out.loc[loc, f"ema{p}"] = ema(close, p)
    return out


def cross_events(bars: pd.DataFrame, burnin_bars: int = 6000) -> list[dict]:
    """EMA200/500 cross, with both averages on the same side of EMA2000."""
    b = add_emas(bars)
    out: list[dict] = []
    for contract, q in b.groupby("contract", sort=False):
        q = q.reset_index(drop=False)
        for i in range(max(2, burnin_bars), len(q)):
            row, prev = q.iloc[i], q.iloc[i - 1]
            if not bool(row.complete) or not bool(prev.complete):
                continue
            up = prev.ema200 <= prev.ema500 and row.ema200 > row.ema500
            down = prev.ema200 >= prev.ema500 and row.ema200 < row.ema500
            above = row.ema200 > row.ema2000 and row.ema500 > row.ema2000
            below = row.ema200 < row.ema2000 and row.ema500 < row.ema2000
            side = 1 if up and above else -1 if down and below else 0
            if side:
                out.append({
                    "event_id": f"{contract}|{row.trade_date}|{int(row.bar_no)}|{int(row.close_ns)}",
                    "contract": contract, "trade_date": str(row.trade_date),
                    "bar_index": int(row["index"]), "bar_no": int(row.bar_no),
                    "signal_ns": int(row.close_ns), "signal_close_ticks": float(row.close),
                    "normal_side": side,
                })
    return out


def simulate_cell(
    ticks: pd.DataFrame, bars: pd.DataFrame, events: Iterable[dict], cell: GridCell,
    commission_rt_ticks: float = 2.4,
) -> pd.DataFrame:
    """One-position tick replay. Pullback is market-after-touch, never passive."""
    t = ticks.sort_values("ts_ns", kind="stable").reset_index(drop=True)
    ts = t.ts_ns.to_numpy(np.int64)
    last = t.price_ticks.to_numpy(float)
    bid = t.bid_ticks.to_numpy(float)
    ask = t.ask_ticks.to_numpy(float)
    valid = (bid > 0) & (ask > bid)
    bar_by_index = bars.reset_index(drop=False).set_index("index")
    rows: list[dict] = []
    next_free = -1
    for ev in sorted(events, key=lambda z: z["signal_ns"]):
        side = ev["normal_side"] * (1 if cell.direction == "NORMAL" else -1)
        j = int(np.searchsorted(ts, ev["signal_ns"], side="right"))
        if j >= len(t) or j <= next_free:
            continue
        if cell.pullback_ticks:
            threshold = ev["signal_close_ticks"] - side * cell.pullback_ticks
            try:
                signal_bar = int(bar_by_index.loc[ev["bar_index"], "bar_no"])
            except KeyError:
                continue
            scope = bars[(bars.contract == ev["contract"]) &
                         (bars.trade_date.astype(str) == ev["trade_date"]) &
                         (bars.bar_no <= signal_bar + cell.pullback_timeout_bars)]
            if scope.empty:
                touched = np.array([], dtype=int)
            else:
                eligible = ts[j:] <= int(scope.close_ns.max())
                touched = np.flatnonzero(eligible & (
                    (last[j:] <= threshold) if side > 0 else (last[j:] >= threshold)
                ))
            if touched.size == 0:
                rows.append({**ev, "cell_id": cell.cell_id, "status": "NO_PULLBACK"})
                continue
            j = j + int(touched[0]) + 1
        while j < len(t) and not valid[j]:
            j += 1
        if j >= len(t):
            rows.append({**ev, "cell_id": cell.cell_id, "status": "NO_ENTRY_QUOTE"})
            continue
        entry = ask[j] + cell.slippage_ticks_side if side > 0 else bid[j] - cell.slippage_ticks_side
        stop = entry - side * cell.stop_ticks
        target = entry + side * cell.target_ticks
        be_active = False
        be_trigger = None if cell.breakeven_ticks is None else entry + side * cell.breakeven_ticks
        exit_i = None
        reason = "OPEN"
        exit_px = np.nan
        for k in range(j + 1, len(t)):
            if t.contract.iloc[k] != ev["contract"] or str(t.trade_date.iloc[k]) != ev["trade_date"]:
                exit_i = k - 1
                reason = "SESSION_END"
                exit_px = (bid[exit_i] if side > 0 else ask[exit_i]) - side * cell.slippage_ticks_side
                break
            if not valid[k]:
                continue
            stop_hit = last[k] <= stop if side > 0 else last[k] >= stop
            target_hit = bid[k] >= target if side > 0 else ask[k] <= target
            if stop_hit:
                exit_i = k
                reason = "BE" if be_active else "SL"
                exit_px = (bid[k] if side > 0 else ask[k]) - side * cell.slippage_ticks_side
                break
            if target_hit:
                exit_i = k
                reason = "TP"
                exit_px = (bid[k] if side > 0 else ask[k]) - side * cell.slippage_ticks_side
                break
            if be_trigger is not None and not be_active:
                trigger_hit = last[k] >= be_trigger if side > 0 else last[k] <= be_trigger
                if trigger_hit:
                    be_active = True
                    stop = entry
        if exit_i is None:
            rows.append({**ev, "cell_id": cell.cell_id, "status": "UNKNOWN_EXIT"})
            break
        gross = side * (exit_px - entry)
        rows.append({
            **ev, "cell_id": cell.cell_id, "status": "COMPLETE", "side": side,
            "entry_ns": int(ts[j]), "exit_ns": int(ts[exit_i]),
            "entry_ticks": float(entry), "exit_ticks": float(exit_px),
            "reason": reason, "gross_ticks": float(gross),
            "net_ticks": float(gross - commission_rt_ticks),
            "be_active": bool(be_active),
        })
        next_free = exit_i
    return pd.DataFrame(rows)


def grid_manifest() -> list[dict]:
    return [asdict(c) | {"cell_id": c.cell_id} for c in frozen_grid()]
