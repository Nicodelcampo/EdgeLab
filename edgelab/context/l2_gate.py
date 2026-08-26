"""Causal L1/L2 -> four-context GATE foundation.

The stream is reconstructed strictly by ``source_row``.  Minute [t,t+1) is
published at t+1.  No outcome, future return, P&L, MAE or MFE is computed.

The three base climates (calm/normal/volatile) come from an HMM3 checkpoint
trained only on explicitly declared earlier sessions.  ``toxic`` is a sticky
L2 flow-stress overlay.  It deliberately is *not* named VPIN: the available
feed supports real BBO OFI and trade-flow imbalance, but this implementation
does not claim the volume-bucket construction or incremental validity of VPIN.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
import math
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd

from .hmm3 import HMM3Config, MODEL_FAMILY, digest, fit_hmm3, forward_filter

L1_CODES = {
    0: "ASK", 1: "BID", 2: "LAST", 3: "OPENING", 4: "HIGH",
    5: "DAILY_VOLUME", 6: "LOW", 7: "SETTLEMENT", 8: "OPEN_INTEREST",
}
L2_SIDES = {0: "ASK", 1: "BID"}
L2_OPERATIONS = {0: "ADD", 1: "UPDATE", 2: "REMOVE"}
FINAL_STATES = ("calm", "normal", "volatile", "toxic")
STATE_GROUP = {"calm": "G-operable", "normal": "G-operable",
               "volatile": "G-stress", "toxic": "G-stress"}
TOXIC_FEATURES = (
    "abs_ofi_normalized", "abs_tape_imbalance", "spread_ticks_close",
    "l2_remove_rate", "depth_depletion_ratio",
)


def _array(table: Any, name: str, dtype=None) -> np.ndarray:
    if isinstance(table, pd.DataFrame):
        values = table[name].to_numpy()
    elif isinstance(table, Mapping):
        values = np.asarray(table[name])
    else:
        values = np.asarray(getattr(table, name))
    return values.astype(dtype, copy=False) if dtype is not None else values


def _require_columns(table: Any, required: Sequence[str], label: str) -> None:
    if isinstance(table, pd.DataFrame):
        present = set(table.columns)
    elif isinstance(table, Mapping):
        present = set(table)
    else:
        present = set(vars(table))
    missing = [name for name in required if name not in present]
    if missing:
        raise ValueError(f"{label}: missing columns {missing}")


@dataclass
class BookSide:
    is_bid: bool
    levels: list[tuple[int, int]] = field(default_factory=list)
    valid: bool = True
    invalid_events: int = 0

    def reset(self) -> None:
        self.levels.clear()
        self.valid = False

    def _ordered(self) -> bool:
        prices = [value[0] for value in self.levels]
        if self.is_bid:
            return all(a > b for a, b in zip(prices, prices[1:]))
        return all(a < b for a, b in zip(prices, prices[1:]))

    def apply(self, operation: int, level: int, price_tick: int, size: int, *,
              strict: bool, bootstrap: bool) -> dict[str, int | bool]:
        if operation not in L2_OPERATIONS or level < 0 or size < 0 or price_tick <= 0:
            raise ValueError("invalid L2 operation payload")
        previous_price = previous_size = None
        if level < len(self.levels):
            previous_price, previous_size = self.levels[level]
        output: dict[str, int | bool] = {
            "valid": True, "removed_size": 0, "added_size": 0,
            "replenished_size": 0, "depleted_size": 0,
        }
        invalid = False
        if operation == 0:
            if level > len(self.levels):
                invalid = True
            else:
                self.levels.insert(level, (price_tick, size))
                output["added_size"] = size
        elif operation == 1:
            if level < len(self.levels):
                self.levels[level] = (price_tick, size)
                if previous_price == price_tick and previous_size is not None:
                    delta = size - previous_size
                    if delta > 0:
                        output["replenished_size"] = delta
                    elif delta < 0:
                        output["depleted_size"] = -delta
            elif bootstrap and level == len(self.levels):
                self.levels.append((price_tick, size))
                output["added_size"] = size
            else:
                invalid = True
        else:
            if level < len(self.levels):
                _, removed = self.levels.pop(level)
                output["removed_size"] = removed
                output["depleted_size"] = removed
            else:
                invalid = True
        if not invalid and not self._ordered():
            invalid = True
        if invalid:
            self.invalid_events += 1
            output["valid"] = False
            if strict and not bootstrap:
                raise ValueError("L2 book invariant failed after synchronization")
            self.reset()
        elif self.levels:
            self.valid = True
        return output


@dataclass
class L2Book:
    min_ready_levels: int = 2
    max_depth: int = 11
    strict: bool = False
    asks: BookSide = field(default_factory=lambda: BookSide(False))
    bids: BookSide = field(default_factory=lambda: BookSide(True))
    ever_ready: bool = False
    crossed_events: int = 0
    locked_events: int = 0

    @property
    def ready(self) -> bool:
        ready = (self.asks.valid and self.bids.valid
                 and len(self.asks.levels) >= self.min_ready_levels
                 and len(self.bids.levels) >= self.min_ready_levels)
        if ready:
            self.ever_ready = True
        return ready

    def apply(self, side: int, operation: int, level: int,
              price_tick: int, size: int) -> dict[str, int | bool]:
        if side not in L2_SIDES:
            raise ValueError(f"invalid L2 side {side}")
        target = self.asks if side == 0 else self.bids
        result = target.apply(operation, level, price_tick, size,
                              strict=self.strict, bootstrap=not self.ever_ready)
        if len(target.levels) > self.max_depth:
            del target.levels[self.max_depth:]
        if self.ready:
            best_ask = self.asks.levels[0][0]
            best_bid = self.bids.levels[0][0]
            if best_bid > best_ask:
                self.crossed_events += 1
                result["valid"] = False
                if self.strict:
                    raise ValueError("crossed L2 book")
                self.asks.reset()
                self.bids.reset()
            elif best_bid == best_ask:
                self.locked_events += 1
        return result

    def snapshot(self, levels: int = 5) -> dict[str, float | int | bool | None]:
        ready = self.ready
        if not ready:
            return {"book_ready": False, "l2_best_bid_tick": None,
                    "l2_best_ask_tick": None, "depth_bid_top5": None,
                    "depth_ask_top5": None, "depth_imbalance_top5": None}
        bid_depth = sum(size for _, size in self.bids.levels[:levels])
        ask_depth = sum(size for _, size in self.asks.levels[:levels])
        total = bid_depth + ask_depth
        return {
            "book_ready": True,
            "l2_best_bid_tick": self.bids.levels[0][0],
            "l2_best_ask_tick": self.asks.levels[0][0],
            "depth_bid_top5": bid_depth,
            "depth_ask_top5": ask_depth,
            "depth_imbalance_top5": ((bid_depth - ask_depth) / total
                                      if total > 0 else 0.0),
        }


class MinuteAccumulator:
    def __init__(self, minute_id: int):
        self.minute_id = minute_id
        self.first_ts_us = None
        self.last_ts_us = None
        self.last_source_row = None
        self.l1_counts = Counter()
        self.l2_counts = Counter()
        self.ofi_sum = self.ofi_abs_sum = 0.0
        self.buy_volume = self.sell_volume = self.unclassified_volume = 0.0
        self.price_change_count = 0
        self.mid_path = self.mid_sq_path = 0.0
        self.last_mid = None
        self.added_size = self.removed_size = 0
        self.replenished_size = self.depleted_size = 0
        self.crossed_l1 = self.locked_l1 = 0

    def touch(self, ts_us: int, source_row: int) -> None:
        if self.first_ts_us is None:
            self.first_ts_us = ts_us
        self.last_ts_us = ts_us
        self.last_source_row = source_row

    def observe_mid(self, mid: float | None) -> None:
        if mid is None or not math.isfinite(mid):
            return
        if self.last_mid is not None and mid != self.last_mid:
            change = mid - self.last_mid
            self.mid_path += abs(change)
            self.mid_sq_path += change * change
            self.price_change_count += 1
        self.last_mid = mid


def _valid_bbo(bid_tick, ask_tick) -> bool:
    return (bid_tick is not None and ask_tick is not None
            and bid_tick > 0 and ask_tick > 0 and bid_tick <= ask_tick)


def _finalize_minute(acc, book, *, session, instrument, contract,
                     bid_tick, ask_tick, bid_size, ask_size):
    snap = book.snapshot()
    valid_bbo = _valid_bbo(bid_tick, ask_tick)
    mid = (bid_tick + ask_tick) / 2.0 if valid_bbo else None
    spread = ask_tick - bid_tick if valid_bbo else None
    trade_volume = acc.buy_volume + acc.sell_volume
    ofi_norm = acc.ofi_sum / acc.ofi_abs_sum if acc.ofi_abs_sum > 0 else 0.0
    tape = ((acc.buy_volume - acc.sell_volume) / trade_volume
            if trade_volume > 0 else 0.0)
    l2_total = sum(acc.l2_counts.values())
    total_change = acc.added_size + acc.removed_size + acc.replenished_size + acc.depleted_size
    row = {
        "instrument": instrument, "contract": contract, "cme_session": session,
        "clock_semantics": "NT8_WALL_CLOCK_INTERPRETED_AS_UTC_REFERENCE_UNRESOLVED",
        "minute_id": acc.minute_id, "minute_start_us": acc.minute_id * 60_000_000,
        "data_window_end_us": acc.last_ts_us,
        "feature_available_at_us": (acc.minute_id + 1) * 60_000_000,
        "available_source_row": acc.last_source_row,
        "event_count": sum(acc.l1_counts.values()) + l2_total,
        "event_rate_per_second": (sum(acc.l1_counts.values()) + l2_total) / 60.0,
        "l1_quote_count": acc.l1_counts[0] + acc.l1_counts[1],
        "l1_trade_count": acc.l1_counts[2],
        "l1_non_signal_stat_count": sum(acc.l1_counts[code] for code in range(3, 9)),
        "l2_add_count": acc.l2_counts[0], "l2_update_count": acc.l2_counts[1],
        "l2_remove_count": acc.l2_counts[2],
        "l2_remove_rate": acc.l2_counts[2] / l2_total if l2_total else 0.0,
        "bid_tick_close": bid_tick, "ask_tick_close": ask_tick,
        "bid_size_close": bid_size, "ask_size_close": ask_size,
        "mid_tick_close": mid, "spread_ticks_close": spread,
        "rv_ticks_1m": math.sqrt(acc.mid_sq_path),
        "mid_path_ticks_1m": acc.mid_path, "price_change_count": acc.price_change_count,
        "ofi": acc.ofi_sum, "ofi_abs": acc.ofi_abs_sum,
        "ofi_normalized": ofi_norm, "abs_ofi_normalized": abs(ofi_norm),
        "aggressive_buy_volume": acc.buy_volume,
        "aggressive_sell_volume": acc.sell_volume,
        "unclassified_trade_volume": acc.unclassified_volume,
        "tape_imbalance": tape, "abs_tape_imbalance": abs(tape),
        "l2_added_size": acc.added_size, "l2_removed_size": acc.removed_size,
        "l2_replenished_size": acc.replenished_size,
        "l2_depleted_size": acc.depleted_size,
        "depth_depletion_ratio": ((acc.removed_size + acc.depleted_size) / total_change
                                  if total_change else 0.0),
        "l1_crossed_count": acc.crossed_l1, "l1_locked_count": acc.locked_l1,
        "l2_crossed_count_cumulative": book.crossed_events,
        "l2_locked_count_cumulative": book.locked_events,
        "book_invalid_events_cumulative": book.asks.invalid_events + book.bids.invalid_events,
        **snap,
    }
    row["wall_clock_minute_of_day_unresolved"] = int((acc.minute_id % 1440 + 1440) % 1440)
    return row


def extract_minute_features(l2: Any, l1: Any, *, session: str,
                            instrument: str = "GC", contract: str = "GC 06-26",
                            min_ready_levels: int = 2, max_depth: int = 11,
                            strict_book: bool = False):
    _require_columns(l2, ("side", "operation", "level", "price_tick", "size",
                          "source_row", "ts_us"), "l2")
    _require_columns(l1, ("side", "price_tick", "size", "source_row", "ts_us"), "l1")
    l2_data = {name: _array(l2, name, np.int64) for name in
               ("side", "operation", "level", "price_tick", "size", "source_row", "ts_us")}
    l1_data = {name: _array(l1, name, np.int64) for name in
               ("side", "price_tick", "size", "source_row", "ts_us")}
    for label, data in (("l2", l2_data), ("l1", l1_data)):
        if len(data["source_row"]) and np.any(np.diff(data["source_row"]) <= 0):
            raise ValueError(f"{label}.source_row must be strictly increasing")
        if len(data["ts_us"]) and np.any(np.diff(data["ts_us"]) < 0):
            raise ValueError(f"{label}.ts_us must be non-decreasing")
    if len(np.intersect1d(l2_data["source_row"], l1_data["source_row"], assume_unique=True)):
        raise ValueError("L1/L2 source_row overlap")

    book = L2Book(min_ready_levels=min_ready_levels, max_depth=max_depth, strict=strict_book)
    bid_tick = ask_tick = bid_size = ask_size = None
    previous_trade_tick = previous_trade_sign = None
    rows = []
    acc = None
    l2_index = l1_index = 0
    l1_side_counts = Counter()

    def ensure_acc(ts_us):
        nonlocal acc
        minute = int(ts_us // 60_000_000)
        if acc is None:
            acc = MinuteAccumulator(minute)
        elif minute != acc.minute_id:
            rows.append(_finalize_minute(acc, book, session=session, instrument=instrument,
                                         contract=contract, bid_tick=bid_tick, ask_tick=ask_tick,
                                         bid_size=bid_size, ask_size=ask_size))
            acc = MinuteAccumulator(minute)
        return acc

    while l2_index < len(l2_data["source_row"]) or l1_index < len(l1_data["source_row"]):
        take_l2 = (l1_index >= len(l1_data["source_row"]) or
                   (l2_index < len(l2_data["source_row"])
                    and l2_data["source_row"][l2_index] < l1_data["source_row"][l1_index]))
        if take_l2:
            source_row = int(l2_data["source_row"][l2_index])
            ts_us = int(l2_data["ts_us"][l2_index])
            current = ensure_acc(ts_us); current.touch(ts_us, source_row)
            operation = int(l2_data["operation"][l2_index]); current.l2_counts[operation] += 1
            change = book.apply(int(l2_data["side"][l2_index]), operation,
                                int(l2_data["level"][l2_index]),
                                int(l2_data["price_tick"][l2_index]),
                                int(l2_data["size"][l2_index]))
            current.added_size += int(change["added_size"])
            current.removed_size += int(change["removed_size"])
            current.replenished_size += int(change["replenished_size"])
            current.depleted_size += int(change["depleted_size"])
            l2_index += 1
        else:
            source_row = int(l1_data["source_row"][l1_index])
            ts_us = int(l1_data["ts_us"][l1_index])
            current = ensure_acc(ts_us); current.touch(ts_us, source_row)
            side = int(l1_data["side"][l1_index])
            price_tick = int(l1_data["price_tick"][l1_index]); size = int(l1_data["size"][l1_index])
            if side not in L1_CODES:
                raise ValueError(f"invalid L1 MarketDataType {side}")
            current.l1_counts[side] += 1; l1_side_counts[side] += 1
            if side == 0:
                old_price, old_size = ask_tick, ask_size
                if old_price is not None and old_size is not None:
                    increment = (-size if price_tick <= old_price else 0) + (old_size if price_tick >= old_price else 0)
                    current.ofi_sum += increment; current.ofi_abs_sum += abs(increment)
                ask_tick, ask_size = price_tick, size
            elif side == 1:
                old_price, old_size = bid_tick, bid_size
                if old_price is not None and old_size is not None:
                    increment = (size if price_tick >= old_price else 0) - (old_size if price_tick <= old_price else 0)
                    current.ofi_sum += increment; current.ofi_abs_sum += abs(increment)
                bid_tick, bid_size = price_tick, size
            elif side == 2:
                sign = 0
                if _valid_bbo(bid_tick, ask_tick):
                    if price_tick >= ask_tick: sign = 1
                    elif price_tick <= bid_tick: sign = -1
                if sign == 0 and previous_trade_tick is not None:
                    if price_tick > previous_trade_tick: sign = 1
                    elif price_tick < previous_trade_tick: sign = -1
                    else: sign = int(previous_trade_sign or 0)
                if sign > 0: current.buy_volume += size
                elif sign < 0: current.sell_volume += size
                else: current.unclassified_volume += size
                previous_trade_tick, previous_trade_sign = price_tick, sign
            if bid_tick is not None and ask_tick is not None:
                if bid_tick > ask_tick: current.crossed_l1 += 1
                elif bid_tick == ask_tick: current.locked_l1 += 1
            current.observe_mid((bid_tick + ask_tick) / 2.0 if _valid_bbo(bid_tick, ask_tick) else None)
            l1_index += 1
    if acc is not None:
        rows.append(_finalize_minute(acc, book, session=session, instrument=instrument,
                                     contract=contract, bid_tick=bid_tick, ask_tick=ask_tick,
                                     bid_size=bid_size, ask_size=ask_size))
    features = pd.DataFrame(rows)
    if len(features):
        features = features.sort_values("minute_id", kind="mergesort").reset_index(drop=True)
        returns = features["mid_tick_close"].astype(float).diff()
        features["mid_return_ticks"] = returns
        features["rv_ticks_15m"] = returns.pow(2).rolling(15, min_periods=5).sum().pow(0.5)
        path = returns.abs().rolling(10, min_periods=10).sum()
        net = (features["mid_tick_close"].astype(float) - features["mid_tick_close"].astype(float).shift(10)).abs()
        features["efficiency_ratio_10m"] = (net / path.replace(0, np.nan)).clip(0, 1)
        depth = features["depth_bid_top5"].astype(float) + features["depth_ask_top5"].astype(float)
        features["log_depth_top5"] = np.log1p(depth)
        required = list(HMM3Config().feature_names) + list(TOXIC_FEATURES)
        no_new_cross = (features["l2_crossed_count_cumulative"].diff().fillna(
            features["l2_crossed_count_cumulative"]) == 0)
        features["feature_eligible"] = (features["book_ready"].fillna(False)
                                         & features[required].notna().all(axis=1)
                                         & (features["l1_crossed_count"] == 0) & no_new_cross)
        if not (features["data_window_end_us"] <= features["feature_available_at_us"]).all():
            raise AssertionError("feature published before its source window closed")
    diagnostics = {
        "session": session, "l2_rows": int(len(l2_data["source_row"])),
        "l1_rows": int(len(l1_data["source_row"])),
        "source_rows_total": int(len(l2_data["source_row"]) + len(l1_data["source_row"])),
        "l1_side_counts": {str(code): int(l1_side_counts[code]) for code in range(9)},
        "minute_rows": int(len(features)),
        "eligible_minutes": int(features["feature_eligible"].sum()) if len(features) else 0,
        "book_invalid_events": int(book.asks.invalid_events + book.bids.invalid_events),
        "l2_crossed_events": int(book.crossed_events), "l2_locked_events": int(book.locked_events),
        "outcomes_computed": False,
    }
    return features, diagnostics


def _training_frame(features, sessions, config):
    selected = features[features["cme_session"].astype(str).isin([str(v) for v in sessions])
                        & features["feature_eligible"].astype(bool)].copy()
    selected = selected.sort_values(["cme_session", "minute_id"], kind="mergesort")
    selected = selected.dropna(subset=list(config.feature_names) + list(TOXIC_FEATURES))
    if len(selected) < 30: raise ValueError("insufficient finite training minutes")
    return selected


def _robust_calibration(frame):
    calibration = {}; standardized = []
    for name in TOXIC_FEATURES:
        values = frame[name].to_numpy(dtype=float); median = float(np.median(values))
        q25, q75 = np.quantile(values, [0.25, 0.75]); scale = float(max(q75 - q25, 1e-9))
        calibration[name] = {"median": median, "iqr": scale}
        standardized.append(np.clip((values - median) / scale, 0.0, 4.0))
    score = np.sort(np.vstack(standardized).T, axis=1)[:, -3:].mean(axis=1)
    calibration["entry_threshold_q90"] = float(np.quantile(score, 0.90))
    calibration["release_threshold_q75"] = float(np.quantile(score, 0.75))
    calibration["definition"] = "mean_of_top3_positive_train_only_robust_z_clipped_0_4"
    return calibration


def _toxicity_score(frame, calibration):
    values = []
    for name in TOXIC_FEATURES:
        params = calibration[name]
        z = (frame[name].to_numpy(dtype=float) - float(params["median"])) / float(params["iqr"])
        values.append(np.clip(z, 0.0, 4.0))
    return np.sort(np.vstack(values).T, axis=1)[:, -3:].mean(axis=1)


def fit_regime4_model(features, *, train_sessions, code_identity,
                      config=None, base_confirm_bars=3, base_min_posterior=0.45,
                      toxic_confirm_bars=2, toxic_release_bars=3):
    config = config or HMM3Config(); train = _training_frame(features, train_sessions, config)
    checkpoint = fit_hmm3(train[list(config.feature_names)].to_numpy(dtype=float),
                          train["cme_session"].astype(str).tolist(),
                          code_identity=code_identity, config=config)
    unsigned = {
        "schema": "edgelab.context.l2_regime4_model/1.0.0", "model_family": MODEL_FAMILY,
        "base_hmm_checkpoint": checkpoint, "state_names": list(FINAL_STATES),
        "state_groups": STATE_GROUP, "train_sessions": [str(v) for v in train_sessions],
        "training_rows": int(len(train)),
        "toxicity_overlay": {"name": "l2_flow_toxicity_overlay_not_vpin",
            "features": list(TOXIC_FEATURES), "calibration": _robust_calibration(train),
            "entry_confirm_bars": int(toxic_confirm_bars),
            "release_confirm_bars": int(toxic_release_bars)},
        "sticky": {"base_confirm_bars": int(base_confirm_bars),
                   "base_min_posterior": float(base_min_posterior)},
        "causal_contract": "checkpoint_fit_on_declared_prior_sessions; forward_filter_only; minute_published_at_end",
        "outcomes_accessed": False, "code_identity": code_identity,
    }
    model_hash = digest(unsigned)
    return {**unsigned, "model_sha256": model_hash,
            "model_id": f"{MODEL_FAMILY}:{model_hash[:16]}"}


def validate_regime4_model(model):
    unsigned = {k: v for k, v in model.items() if k not in {"model_sha256", "model_id"}}
    model_hash = digest(unsigned)
    if model_hash != model.get("model_sha256"): raise ValueError("regime4 model hash mismatch")
    if model.get("model_id") != f"{MODEL_FAMILY}:{model_hash[:16]}":
        raise ValueError("model_id does not identify all model bytes")
    if tuple(model.get("state_names", ())) != FINAL_STATES: raise ValueError("invalid four-state vocabulary")


def _eligible_segments(frame):
    eligible = frame[frame["feature_eligible"].astype(bool)].copy()
    eligible = eligible.sort_values(["cme_session", "minute_id"], kind="mergesort")
    segment_ids = []; previous_session = previous_minute = None; segment = 0
    for row in eligible.itertuples(index=False):
        session = str(row.cme_session); minute = int(row.minute_id)
        if session != previous_session or previous_minute is None or minute != previous_minute + 1:
            segment += 1
        segment_ids.append(f"{session}#{segment}")
        previous_session, previous_minute = session, minute
    return eligible, segment_ids


def label_regime4(features, model, *, evaluation_sessions=None):
    validate_regime4_model(model); output = features.copy().reset_index(drop=True)
    output["context_state"] = pd.Series([None] * len(output), dtype="string")
    output["context_group"] = pd.Series([None] * len(output), dtype="string")
    output["context_as_of_ok"] = False
    output["context_fail_reason"] = np.where(output["feature_eligible"], "", "FEATURE_NOT_ELIGIBLE")
    output["context_model_id"] = str(model["model_id"])
    for name in ("p_calm", "p_normal", "p_volatile", "flow_toxicity_score"): output[name] = np.nan
    eligible, segment_ids = _eligible_segments(output)
    if not len(eligible): return output
    checkpoint = model["base_hmm_checkpoint"]; names = list(checkpoint["feature_names"])
    posterior = forward_filter(eligible[names].to_numpy(dtype=float), segment_ids, checkpoint)
    scores = _toxicity_score(eligible, model["toxicity_overlay"]["calibration"])
    entry = float(model["toxicity_overlay"]["calibration"]["entry_threshold_q90"])
    release = float(model["toxicity_overlay"]["calibration"]["release_threshold_q75"])
    base_confirm = int(model["sticky"]["base_confirm_bars"]); pmin = float(model["sticky"]["base_min_posterior"])
    toxic_confirm = int(model["toxicity_overlay"]["entry_confirm_bars"])
    toxic_release = int(model["toxicity_overlay"]["release_confirm_bars"])
    final = []; current_base = 1; pending_base = None; pending_count = 0
    toxic = False; toxic_high = toxic_low = 0; previous_segment = None
    for idx, segment_id in enumerate(segment_ids):
        if segment_id != previous_segment:
            current_base = int(np.argmax(posterior[idx])); pending_base = None
            pending_count = toxic_high = toxic_low = 0; toxic = False
        proposal = int(np.argmax(posterior[idx]))
        if proposal != current_base and posterior[idx, proposal] >= pmin:
            if pending_base == proposal: pending_count += 1
            else: pending_base, pending_count = proposal, 1
            if pending_count >= base_confirm:
                current_base = proposal; pending_base = None; pending_count = 0
        else: pending_base = None; pending_count = 0
        if not toxic:
            toxic_high = toxic_high + 1 if scores[idx] >= entry else 0
            if toxic_high >= toxic_confirm: toxic = True; toxic_low = 0
        else:
            toxic_low = toxic_low + 1 if scores[idx] < release else 0
            if toxic_low >= toxic_release: toxic = False; toxic_high = 0
        final.append("toxic" if toxic else ("calm", "normal", "volatile")[current_base])
        previous_segment = segment_id
    positions = eligible.index.to_numpy()
    output.loc[positions, "context_state"] = final
    output.loc[positions, "context_group"] = [STATE_GROUP[v] for v in final]
    output.loc[positions, "context_as_of_ok"] = True; output.loc[positions, "context_fail_reason"] = ""
    output.loc[positions, ["p_calm", "p_normal", "p_volatile"]] = posterior
    output.loc[positions, "flow_toxicity_score"] = scores
    if evaluation_sessions is None: output["evaluation_eligible"] = output["context_as_of_ok"]
    else:
        allowed = {str(v) for v in evaluation_sessions}
        output["evaluation_eligible"] = output["context_as_of_ok"] & output["cme_session"].astype(str).isin(allowed)
    return output


def attach_context_at_t0(events, contexts, *, require_source_row=True, max_age_minutes=2):
    event_required = {"event_id", "instrument", "contract", "cme_session"}
    context_required = {"instrument", "contract", "cme_session", "context_state",
                        "context_model_id", "context_as_of_ok", "feature_available_at_us",
                        "available_source_row"}
    event_required.add("source_row" if require_source_row else "event_ts_us")
    missing_event = sorted(event_required - set(events.columns)); missing_context = sorted(context_required - set(contexts.columns))
    if missing_event or missing_context: raise ValueError(f"missing event={missing_event} context={missing_context}")
    if events["event_id"].astype(str).duplicated().any(): raise ValueError("duplicate event_id")
    keys = ["instrument", "contract", "cme_session"]
    grouped = {tuple(str(v) for v in key): group.copy()
               for key, group in contexts[contexts["context_as_of_ok"]].groupby(keys, sort=False)}
    rows = []; failures = Counter()
    for event in events.to_dict("records"):
        key = tuple(str(event[name]) for name in keys); group = grouped.get(key)
        chosen = None; reason = ""
        if group is None or not len(group): reason = "NO_CONTEXT_KEY"
        elif require_source_row:
            group = group.sort_values("available_source_row", kind="mergesort")
            values = group["available_source_row"].to_numpy(dtype=np.int64)
            pos = int(np.searchsorted(values, int(event["source_row"]), side="left") - 1)
            if pos < 0: reason = "NO_PRIOR_CONTEXT"
            else: chosen = group.iloc[pos]
        else:
            group = group.sort_values("feature_available_at_us", kind="mergesort")
            values = group["feature_available_at_us"].to_numpy(dtype=np.int64)
            pos = int(np.searchsorted(values, int(event["event_ts_us"]), side="right") - 1)
            if pos < 0: reason = "NO_PRIOR_CONTEXT"
            else:
                chosen = group.iloc[pos]
                if int(event["event_ts_us"]) - int(chosen["feature_available_at_us"]) > max_age_minutes * 60_000_000:
                    reason = "STALE_CONTEXT"; chosen = None
        out = dict(event); ok = chosen is not None and not reason
        out["context_as_of_ok"] = ok; out["context_fail_reason"] = reason
        if ok:
            for name in ("context_state", "context_group", "context_model_id",
                         "feature_available_at_us", "available_source_row", "p_calm",
                         "p_normal", "p_volatile", "flow_toxicity_score"):
                out[f"context_{name}" if name.startswith("p_") or name == "flow_toxicity_score" else name] = chosen.get(name)
        else: failures[reason] += 1
        rows.append(out)
    result = pd.DataFrame(rows)
    report = {"n_events": int(len(result)), "n_as_of_ok": int(result["context_as_of_ok"].sum()) if len(result) else 0,
              "coverage": float(result["context_as_of_ok"].mean()) if len(result) else 0.0,
              "fail_reasons": dict(failures), "join_key": "source_row" if require_source_row else "ts_us",
              "outcomes_accessed": False}
    return result, report


def target_free_report(labels):
    valid = labels[labels["context_as_of_ok"]].copy()
    counts = {state: int((valid["context_state"] == state).sum()) for state in FINAL_STATES}
    transitions = {a: {b: 0 for b in FINAL_STATES} for a in FINAL_STATES}
    runs = []; flips = possible = 0
    for _, session in valid.groupby("cme_session", sort=False):
        states = session.sort_values("minute_id")["context_state"].astype(str).tolist()
        if not states: continue
        run = 1
        for previous, current in zip(states, states[1:]):
            possible += 1; transitions[previous][current] += 1
            if current == previous: run += 1
            else: runs.append(run); run = 1; flips += 1
        runs.append(run)
    by_session = {str(s): {state: int((g["context_state"] == state).sum()) for state in FINAL_STATES}
                  for s, g in valid.groupby("cme_session", sort=True)}
    return {"schema": "edgelab.context.l2_target_free_report/1.0.0",
        "minutes_by_state": counts, "minutes_by_session_state": by_session,
        "sessions_by_state": {state: int(valid.loc[valid["context_state"] == state, "cme_session"].nunique()) for state in FINAL_STATES},
        "mean_persistence_minutes": float(np.mean(runs)) if runs else None,
        "median_persistence_minutes": float(np.median(runs)) if runs else None,
        "flip_rate": flips / possible if possible else None, "transition_counts": transitions,
        "eligible_minutes": int(len(valid)), "total_minutes": int(len(labels)),
        "coverage": float(len(valid) / len(labels)) if len(labels) else 0.0,
        "corr_with_zone_width": "NOT_MEASURED_EVENT_INPUT_ABSENT",
        "vpin": "NOT_IMPLEMENTED; flow_toxicity_overlay_not_vpin",
        "outcomes_accessed": False, "returns_computed": False,
        "pnl_computed": False, "edge_declared": False}
