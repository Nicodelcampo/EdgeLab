"""Causal, instrument-neutral MBP-10 observables; no forecast or price outcomes.

Caller publishes completed timestamp groups on the NEXT OBSERVED raw row.
OFI is a consecutive published-endpoint proxy, not an event-level flow tally.
Queue-weighted mid is not a calibrated Stoikov microprice.
"""
from collections import deque
import math


def integer(x, label):
    if type(x) is not int:
        raise ValueError("INTEGER_REQUIRED:" + label)
    return x


def endpoint_ofi(before, after):
    """Cont et al. touch formula applied ONLY to valid published endpoints."""
    old_bid, old_ask = before["bid"][0], before["ask"][0]
    bid, ask = after["bid"][0], after["ask"][0]
    return ((bid[1] if bid[0] >= old_bid[0] else 0)
            - (old_bid[1] if bid[0] <= old_bid[0] else 0)
            - (ask[1] if ask[0] <= old_ask[0] else 0)
            + (old_ask[1] if ask[0] >= old_ask[0] else 0))


def validate_book(bid, ask):
    if len(bid) < 10 or len(ask) < 10:
        raise ValueError("INCOMPLETE_DEPTH")
    for side, order in ((bid, -1), (ask, 1)):
        for i, (tick, size) in enumerate(side[:10]):
            integer(tick, "price_tick")
            if isinstance(size, bool) or not isinstance(size, (int, float)) or \
                    not math.isfinite(size) or size <= 0:
                raise ValueError("NONPOSITIVE_OR_INVALID_VISIBLE_SIZE")
            if i and order * (tick - side[i-1][0]) <= 0:
                raise ValueError("UNORDERED_BOOK")
    if bid[0][0] >= ask[0][0]:
        raise ValueError("CROSSED_BOOK")


class AsOfFeatures:
    def __init__(self, instrument, window_us=10_000_000):
        if not isinstance(instrument, str) or not instrument:
            raise ValueError("EXPLICIT_INSTRUMENT_REQUIRED")
        integer(window_us, "window_us")
        if window_us <= 0:
            raise ValueError("POSITIVE_WINDOW_REQUIRED")
        self.instrument = instrument
        self.window_us = window_us
        self.current = None
        self.last_good = None
        self.flows = deque()
        self.valid_start_us = None
        self.last_available_row = -1
        self.last_snapshot_ts = None

    def publish(self, bid, ask, snapshot_asof_row, snapshot_ts_us,
                available_row, available_ts_us, gate="PASS"):
        for label, value in (("snapshot_asof_row", snapshot_asof_row),
                             ("snapshot_ts_us", snapshot_ts_us),
                             ("available_row", available_row),
                             ("available_ts_us", available_ts_us)):
            integer(value, label)
        if not 0 <= snapshot_asof_row < available_row:
            raise ValueError("NEXT_OBSERVED_ROW_REQUIRED")
        if available_ts_us <= snapshot_ts_us:
            raise ValueError("NEXT_TIMESTAMP_PUBLICATION_REQUIRED")
        if available_row <= self.last_available_row:
            raise ValueError("PUBLICATION_ROW_INVERSION_OR_DUPLICATE")
        if self.last_snapshot_ts is not None and snapshot_ts_us <= self.last_snapshot_ts:
            raise ValueError("ATOMIC_GROUP_CLOCK_INVERSION_OR_DUPLICATE")
        self.last_available_row = available_row
        self.last_snapshot_ts = snapshot_ts_us
        meta = dict(instrument=self.instrument,
                    snapshot_asof_row=snapshot_asof_row,
                    snapshot_ts_us=snapshot_ts_us, available_row=available_row,
                    available_ts_us=available_ts_us,
                    publication_mode="OBSERVED_NEXT_TIMESTAMP_ROW", gate=gate)
        if gate == "PASS":
            try:
                validate_book(bid, ask)
            except ValueError as error:
                meta["gate"] = str(error)
        if meta["gate"] != "PASS":
            self.current = dict(meta=meta, values=None)
            self.last_good = None
            self.valid_start_us = None
            self.flows.clear()
            return
        now = dict(bid=tuple((int(p), float(q)) for p, q in bid[:10]),
                   ask=tuple((int(p), float(q)) for p, q in ask[:10]))
        if self.valid_start_us is None:
            self.valid_start_us = snapshot_ts_us
        if self.last_good is not None:
            self.flows.append((snapshot_ts_us, endpoint_ofi(self.last_good, now)))
        while self.flows and self.flows[0][0] <= snapshot_ts_us - self.window_us:
            self.flows.popleft()
        bp, bq = now["bid"][0]
        ap, aq = now["ask"][0]
        mid = (bp + ap) / 2
        weighted_mid = (ap*bq + bp*aq) / (bq+aq)
        full_window = snapshot_ts_us-self.valid_start_us >= self.window_us
        observed_sum = sum(e for _, e in self.flows)
        values = dict(spread_ticks=ap-bp,
                      weighted_mid_minus_mid_ticks=weighted_mid-mid,
                      endpoint_ofi_window=observed_sum if full_window else None,
                      endpoint_ofi_observed_prefix_sum=observed_sum,
                      endpoint_ofi_observations=len(self.flows),
                      history_span_us=snapshot_ts_us-self.valid_start_us,
                      full_window_available=full_window,
                      window_us=self.window_us)
        for n in (1, 3, 10):
            bv = sum(q for _, q in now["bid"][:n])
            av = sum(q for _, q in now["ask"][:n])
            values["queue_imbalance_" + str(n)] = (bv-av)/(bv+av)
            values["visible_depth_" + str(n)] = bv+av
        values["endpoint_ofi_per_touch_depth"] = \
            values["endpoint_ofi_window"]/(bq+aq) if full_window else None
        self.current = dict(meta=meta, values=values, book=now)
        self.last_good = now

    def sample(self, decision_row, decision_ts_us, direction=None,
               target_tick=None, target_side=None, max_age_us=None,
               instrument=None):
        integer(decision_row, "decision_row")
        integer(decision_ts_us, "decision_ts_us")
        if instrument is not None and instrument != self.instrument:
            raise ValueError("CROSS_INSTRUMENT_JOIN_FORBIDDEN")
        if direction is not None and (type(direction) is not int or direction not in (-1, 1)):
            raise ValueError("DIRECTION_MUST_BE_PLUS_OR_MINUS_ONE")
        if max_age_us is not None:
            integer(max_age_us, "max_age_us")
            if max_age_us < 0:
                raise ValueError("NEGATIVE_MAX_AGE")
        if (target_tick is None) != (target_side is None):
            raise ValueError("TARGET_TICK_AND_SIDE_REQUIRED_TOGETHER")
        if target_tick is not None:
            integer(target_tick, "target_tick")
            if target_side not in ("bid", "ask"):
                raise ValueError("EXPLICIT_TARGET_BOOK_SIDE_REQUIRED")
        out = dict(instrument=self.instrument, decision_row=decision_row,
                   decision_ts_us=decision_ts_us, direction=direction,
                   forecast_computed=False, outcomes_computed=False,
                   values=None, target_observation=None)
        if self.current is None:
            out["gate"] = "NO_PUBLISHED_SNAPSHOT"
            return out
        meta = self.current["meta"]
        if meta["available_row"] > decision_row or meta["available_ts_us"] > decision_ts_us:
            raise ValueError("FUTURE_SNAPSHOT_FORBIDDEN")
        out.update(meta)
        out["snapshot_age_us"] = decision_ts_us-meta["snapshot_ts_us"]
        if meta["gate"] != "PASS":
            return out
        if max_age_us is not None and out["snapshot_age_us"] > max_age_us:
            out["gate"] = "STALE_SNAPSHOT"
            return out
        out["values"] = dict(self.current["values"])
        if direction is not None:
            for name in ("queue_imbalance_1", "queue_imbalance_3", "queue_imbalance_10",
                         "weighted_mid_minus_mid_ticks", "endpoint_ofi_window",
                         "endpoint_ofi_per_touch_depth"):
                value = out["values"][name]
                out["values"]["directional_" + name] = direction*value if value is not None else None
        if target_tick is not None:
            levels = self.current["book"][target_side]
            match = [(i+1, size) for i, (tick, size) in enumerate(levels) if tick == target_tick]
            out["target_observation"] = dict(
                side=target_side, price_tick=target_tick,
                visible=bool(match), depth=match[0][0] if match else None,
                visible_size=match[0][1] if match else None,
                status="VISIBLE" if match else "UNKNOWN_NOT_IN_VISIBLE_TEN_LEVELS")
        return out