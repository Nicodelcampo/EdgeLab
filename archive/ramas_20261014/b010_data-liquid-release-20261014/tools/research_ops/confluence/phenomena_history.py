"""Bounded causal history for a NEW experiment; no outcomes or market loader.

All observed anchors, including UNKNOWN and later-censored anchors, must be
pushed before a response is read. No existing frozen runner uses this module.
Lag features and proxy paths share the identical observed prefix. Unavailable
lags are zero-filled with explicit masks, never future/interpolated values.
"""
from collections import deque
from datetime import datetime, timezone
import math
import numpy as np
from .asof_intersections import Clock
from .phenomena_transitions import StatePath
from .phenomena_models import FEATURES
from .phenomena_states import STATES

LAGS = (20, 40, 60, 120)
HISTORY_NAMES = FEATURES + tuple(
    name for lag in LAGS for name in
    (tuple(f"lag{lag}s:{f}" for f in FEATURES) +
     (f"lag{lag}s:available", f"lag{lag}s:age_over_120s")))
EXTRA_NAMES = ("A_ONLY", "E_ONLY", "BOTH", "observed_duration_over_120s",
               "A_TO_E_recent", "E_TO_A_recent")
MODEL_SLICES = {
    "STATE": (0, 1, 2), "DURATION": (3,),
    "A_TO_E": (4,), "E_TO_A": (5,), "TRANSITIONS": (4, 5),
    "ALL": (0, 1, 2, 3, 4, 5),
}


class CausalHistory:
    def __init__(self, *, research_dates, max_anchors=250000):
        dates = tuple(research_dates)
        if not dates or len(set(dates)) != len(dates):
            raise ValueError("unique explicit development dates")
        self.bounds = {}
        for d in dates:
            if d >= "2026-10-01":
                raise ValueError("closed holdout")
            end = int(datetime.fromisoformat(d + "T22:00:00+00:00").timestamp()) * 10**9
            if datetime.fromtimestamp(end // 10**9, timezone.utc).date().isoformat() != d:
                raise ValueError("canonical research date")
            self.bounds[d] = (end - 86400 * 10**9, end)
        if type(max_anchors) is not int or max_anchors < 1:
            raise ValueError("positive anchor cap")
        self.max_anchors = max_anchors
        self.path = StatePath()
        self.rows = deque()
        self.last = None
        self.date = None
        self.count = 0
        self.thin_ns = None
        self.poisoned = False

    def push(self, clock, trade_date, state, *, direction, continuous):
        if self.poisoned:
            raise ValueError("history poisoned; no successful partial continuation")
        try:
            return self._push(clock, trade_date, state, direction, continuous)
        except Exception:
            self.poisoned = True
            raise

    def _push(self, clock, trade_date, state, direction, continuous):
        bounds = self.bounds.get(trade_date)
        if (not isinstance(clock, Clock) or not bounds or
                not bounds[0] <= clock.ns < bounds[1] or state not in STATES):
            raise ValueError("explicit natural-session observed prefix")
        if self.last is not None and clock <= self.last:
            raise ValueError("strict history clock")
        if self.count >= self.max_anchors:
            raise ValueError("history anchor cap; no truncation")
        if direction is not None and (type(direction) is not int or direction not in (-1, 1)):
            raise ValueError("signed observed direction")
        if state != "UNKNOWN" and direction is None:
            raise ValueError("known proxy requires observed orientation")
        if continuous is not None:
            x = np.array(continuous, dtype=float, copy=True)
            if state == "UNKNOWN" or x.shape != (len(FEATURES),) or not np.isfinite(x).all():
                raise ValueError("finite common continuous vector")
        else:
            x = None
        new_session = self.date != trade_date
        gap = self.last is not None and clock.ns - self.last.ns > 10 * 10**9
        if new_session or gap:
            self.rows.clear()
        if new_session:
            self.thin_ns = None
        path = self.path.push(clock, trade_date, state, direction=direction)
        # First actual observed anchor, NOT first anchor with a usable future.
        thin = self.thin_ns is None or clock.ns - self.thin_ns >= 60 * 10**9
        if thin:
            self.thin_ns = clock.ns
        oldest = clock.ns - 125 * 10**9
        while self.rows and self.rows[0][0].ns < oldest:
            self.rows.popleft()
        if len(self.rows) >= 128:
            raise ValueError("5-second grid history capacity; no dropped anchors")
        base = None
        cc = None
        if x is not None:
            parts = [x]
            lag_values = []
            lag_present = []
            for lag in LAGS:
                target = clock.ns - lag * 10**9
                candidate = next((r for r in reversed(self.rows) if r[0].ns <= target), None)
                available = (candidate is not None and candidate[1] is not None and
                             target - candidate[0].ns <= 5 * 10**9)
                value = candidate[1] if available else np.zeros(len(FEATURES))
                age = (clock.ns - candidate[0].ns) / (120 * 10**9) if available else 0.
                parts.extend((value, np.array([float(available), age])))
                lag_values.append(value)
                lag_present.append(available)
            base = np.concatenate(parts)
            # Fixed smooth capacity controls use the SAME history as proxies.
            # All six extras have same-dimensional comparators, no eval tuning.
            ix = {name: i for i, name in enumerate(FEATURES)}
            pressure = ix["pressure_ratio:log1p"]
            progress = ix["progress:signed_log1p"]
            count = ix["trade_count_ratio:log1p"]
            prior_progress = ix["prior_progress:signed_log1p"]
            old = lag_values[0]
            has_old = float(lag_present[0])
            cc = np.array([
                math.tanh(x[pressure]) * math.tanh(x[progress]),
                math.tanh(x[count]) * math.tanh(x[prior_progress]),
                math.tanh(x[pressure]) * math.tanh(x[count]),
                has_old * math.tanh(x[progress] - old[progress]),
                has_old * math.tanh(old[pressure] - x[pressure]),
                has_old * math.tanh(x[pressure] - old[pressure]),
            ])
        extra = np.array([
            float(state == "A_ONLY"), float(state == "E_ONLY"), float(state == "BOTH"),
            (path["duration_seconds"] or 0.) / 120.,
            float(path["A_TO_E_observed_within_cap"]),
            float(path["E_TO_A_observed_within_cap"]),
        ])
        self.rows.append((clock, x))
        self.last, self.date = clock, trade_date
        self.count += 1
        return {"path": path, "base": base, "capacity": cc, "extras": extra,
                "retained_for_60s_sensitivity": thin, "observed_anchor_count": self.count}


def design(base, capacity, extras, name):
    """Equal-dimensional, prespecified comparisons on a common scored population."""
    base, capacity, extras = (np.asarray(v, float) for v in (base, capacity, extras))
    n = len(base)
    if (base.shape != (n, len(HISTORY_NAMES)) or capacity.shape != (n, 6) or
            extras.shape != (n, 6) or
            any(not np.isfinite(v).all() for v in (base, capacity, extras))):
        raise ValueError("finite common history design")
    if name == "HISTORY":
        return base
    kind, sep, family = name.partition(":")
    if not sep or kind not in ("PROXY", "CAPACITY") or family not in MODEL_SLICES:
        raise ValueError("fixed history representation")
    addition = extras if kind == "PROXY" else capacity
    return np.column_stack((base, addition[:, MODEL_SLICES[family]]))


def split_eligible(clock, *, split_ns, partition, horizon_ns=60000000000,
                   embargo_ns=60000000000):
    """Purging depends ONLY on fixed clock+horizon, never observed exit time."""
    if (not isinstance(clock, Clock) or type(split_ns) is not int or split_ns <= 0 or
            horizon_ns != 60000000000 or type(horizon_ns) is not int or
            embargo_ns != 60000000000 or type(embargo_ns) is not int):
        raise ValueError("fixed 60s purge and embargo")
    if partition == "TRAIN":
        return clock.ns + horizon_ns <= split_ns - embargo_ns
    if partition == "EVAL":
        return clock.ns >= split_ns + embargo_ns
    raise ValueError("explicit chronological partition")