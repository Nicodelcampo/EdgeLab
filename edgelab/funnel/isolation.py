"""Outcome isolation for exploratory D0/D1; never reads D2 prices."""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np

@dataclass(frozen=True)
class StageWindow:
    signal_positions: np.ndarray
    bar_start: int
    bar_stop: int
    excluded_boundary_signals: int

    def local_signals(self, signal_idx):
        return np.asarray(signal_idx, dtype=np.int64)[self.signal_positions] - self.bar_start


def stage_window(trade_dates, signal_idx, stage_dates, max_hold_bars=200):
    """Use only complete horizons wholly inside one chronological partition.

    The existing kernel visits entry through entry+hold, inclusive (hold+1
    bars). Exclude incomplete horizons instead of imputing a timeout outcome.
    Only calendar labels and signal indices are read here, not prices.
    """
    td = np.asarray(trade_dates)
    sig = np.asarray(signal_idx)
    if td.ndim != 1 or not len(td) or np.any(td[1:] < td[:-1]):
        raise ValueError('trade_dates must be nonempty, 1D and chronological')
    if sig.ndim != 1 or sig.dtype.kind not in 'iu' or np.any(sig < 0) or np.any(sig >= len(td)):
        raise ValueError('signal indices must be integer indices inside bars')
    if isinstance(max_hold_bars, bool) or not isinstance(max_hold_bars, (int, np.integer)) or max_hold_bars < 0 or max_hold_bars >= np.iinfo(np.int32).max:
        raise ValueError('max_hold_bars must be a nonnegative integer')
    bars = np.flatnonzero(np.isin(td, stage_dates))
    if not len(bars):
        return StageWindow(np.empty(0, np.int64), 0, 0, 0)
    start, stop = int(bars[0]), int(bars[-1]) + 1
    if len(bars) != stop - start:
        raise ValueError('stage must occupy a contiguous chronological bar range')
    entry = sig.astype(np.int64) + 1
    in_stage = (entry >= start) & (entry < stop)
    eligible = in_stage & (entry + int(max_hold_bars) < stop)
    return StageWindow(np.flatnonzero(eligible), start, stop, int(np.count_nonzero(in_stage & ~eligible)))


def bounded_batches(*args, **kwargs):
    """Compatibility name; the public iterator owns one-matrix budgeting."""
    from .screen import iter_screen_batches
    yield from iter_screen_batches(*args, **kwargs)
