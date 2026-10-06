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
    if isinstance(max_hold_bars, bool) or not isinstance(max_hold_bars, (int, np.integer)) or max_hold_bars < 0:
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


def bounded_batches(sig, dirs, high, low, bid_open, ask_open, sls, tps,
                    multipliers=None, max_hold_bars=200, fees=.5,
                    backend='auto', max_matrix_bytes=512*1024*1024):
    """Bound one returned matrix using worst-case float64, not GPU float32.

    This is NOT a total host/device/process memory ceiling: price arrays,
    transfers, allocator pools, and caller-retained batches are additional.
    Reject a budget unable to fit one column; do not silently exceed it.
    """
    from .screen import iter_screen_batches
    if len(sls) != len(tps) or len(sig) != len(dirs):
        raise ValueError('signal/configuration lengths disagree')
    if any(np.asarray(a).ndim != 1 for a in (sig, dirs, high, low, bid_open, ask_open, sls, tps)):
        raise ValueError('screen inputs must be 1D')
    if any(len(a) != len(high) for a in (low, bid_open, ask_open)):
        raise ValueError('bar array lengths disagree')
    if not np.isin(dirs, [-1, 1]).all():
        raise ValueError('directions must be +/-1')
    if np.any(np.asarray(sls) <= 0) or np.any(np.asarray(tps) <= 0):
        raise ValueError('SL/TP must be positive')
    if not isinstance(max_matrix_bytes, (int, np.integer)) or max_matrix_bytes <= 0:
        raise ValueError('matrix budget must be a positive integer')
    if not len(sig) or not len(sls):
        return
    if len(sig)*8 > max_matrix_bytes:
        raise ValueError('matrix budget cannot fit one float64 column; chunk signals explicitly')
    for start, end, matrix, device in iter_screen_batches(
            sig, dirs, high, low, bid_open, ask_open, sls, tps,
            multipliers, max_hold_bars, fees, backend,
            max_matrix_bytes=max_matrix_bytes//2):
        if matrix.nbytes > max_matrix_bytes:
            raise RuntimeError('screen backend exceeded matrix budget')
        yield start, end, matrix, device
