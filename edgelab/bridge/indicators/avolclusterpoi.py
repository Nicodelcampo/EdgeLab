# -*- coding: utf-8 -*-
"""aVolClusterPOI research kernel v0.5.

One max-mass cluster per block. OFF_PRICE is the level object.
AT_PRICE is occupation, not support/resistance. No QualityScore gate,
no target/stop, no BigTrap2.

Parity note (2026-08-14): SessionProfile mirrors nt8/aVolClusterPOI.cs:
LookbackSessions is FIFO by complete SESSION, not by individual score, and the
first complete session is retained. Buckets use (bar close - 1 second), exactly
as GetTimeBucket() in the C# contract.
"""
from __future__ import annotations

import math
from collections import defaultdict, deque

NAME = "aVolClusterPOI"
VERSION = "0.5"
RESEARCH_DEFAULTS = dict(
    window_bars=10,
    median_multiplier=2.0,
    max_gap_ticks=1,
    min_cluster_ticks=2,
    time_bucket_minutes=30,
    lookback_sessions=20,
    detection_percentile=98.0,
    min_samples_per_bucket=20,
    max_age_bars=0,
    one_cluster_per_block=True,
)

NS = 1_000_000_000


def empirical_quantile(sorted_asc, p):
    values = list(sorted_asc)
    n = len(values)
    if n == 0:
        return None
    k = int(math.ceil(float(p) * n))
    k = min(max(k, 1), n)
    return values[k - 1]


def median_upper(values):
    if not values:
        return None
    ordered = sorted(values)
    return ordered[len(ordered) // 2]


def session_relative_bucket(block_end_ns, session_begin_ns, bucket_minutes=30):
    """Mirror of C# GetTimeBucket(Time[0]) for SessionRelative mode."""
    span = int(bucket_minutes) * 60 * NS
    anchor_ns = int(block_end_ns) - NS
    return int((anchor_ns - int(session_begin_ns)) // span)


def cluster_hot_ticks(cells, median_multiplier, max_gap_ticks, min_cluster_ticks):
    if len(cells) < 3:
        return []
    med = median_upper(cells.values())
    if med is None:
        return []
    hot = sorted(tick for tick, vol in cells.items() if vol >= med * float(median_multiplier))
    if not hot:
        return []
    clusters = []
    current = [hot[0]]
    for tick in hot[1:]:
        gap = tick - current[-1] - 1
        if gap <= int(max_gap_ticks):
            current.append(tick)
        else:
            if len(current) >= int(min_cluster_ticks):
                clusters.append((list(current), sum(cells[t] for t in current)))
            current = [tick]
    if len(current) >= int(min_cluster_ticks):
        clusters.append((list(current), sum(cells[t] for t in current)))
    return clusters


def classify_kind(close_tick, lower_tick, upper_tick):
    if close_tick is None:
        return "OFF_PRICE", None, None
    close_tick = int(close_tick)
    if close_tick > upper_tick:
        return "OFF_PRICE", 1, close_tick - upper_tick
    if close_tick < lower_tick:
        return "OFF_PRICE", -1, lower_tick - close_tick
    return "AT_PRICE", 0, 0


def _cluster_records(clusters):
    return [dict(lower_tick=int(ticks[0]), upper_tick=int(ticks[-1]),
                 score=float(score), count=len(ticks), ticks=[int(t) for t in ticks])
            for ticks, score in clusters]


def detect_block(cells, history_scores, params=None, close_tick=None):
    """Detect one block and expose a lossless, target-free diagnostic record.

    Historical public keys (best_score, threshold, zones, abstain) are
    preserved. Added fields mirror the optional NT8 block diagnostic and make
    CREATE and every ABSTAIN directly replayable.
    """
    p = {**RESEARCH_DEFAULTS, **(params or {})}
    hist = sorted(history_scores or [])
    hist_count = len(hist)
    enough_history = hist_count >= int(p["min_samples_per_bucket"])

    if len(cells) < 3:
        return dict(best_score=0.0, threshold=None, zones=[],
                    abstain="warmup" if not enough_history else None,
                    median=None, hot_threshold=None, history_samples=hist_count,
                    decision="ABSTAIN_FEW_CELLS", clusters=[], selected_cluster=None)

    median = median_upper(cells.values())
    hot_threshold = median * float(p["median_multiplier"])
    clusters = cluster_hot_ticks(cells, p["median_multiplier"], p["max_gap_ticks"],
                                 p["min_cluster_ticks"])
    best = max((score for _ticks, score in clusters), default=0.0)
    threshold = (empirical_quantile(hist, p["detection_percentile"] / 100.0)
                 if enough_history else None)
    base = dict(best_score=best, threshold=threshold, zones=[],
                abstain="warmup" if not enough_history else None,
                median=median, hot_threshold=hot_threshold,
                history_samples=hist_count, clusters=_cluster_records(clusters),
                selected_cluster=None)

    if threshold is None:
        base["decision"] = "ABSTAIN_NO_HISTORY"
        return base
    if not clusters:
        base["decision"] = "ABSTAIN_NO_CLUSTER"
        return base
    passing = [(ticks, score) for ticks, score in clusters
               if threshold > 0 and score >= threshold]
    if not passing:
        base["decision"] = "ABSTAIN_BELOW_THRESHOLD"
        return base

    ticks, score = max(passing, key=lambda item: item[1])
    kind, direction, distance = classify_kind(close_tick, ticks[0], ticks[-1])
    zone = dict(lower_tick=ticks[0], upper_tick=ticks[-1], score=score,
                threshold=threshold, kind=kind,
                event_type="AT_PRICE_CREATED" if kind == "AT_PRICE" else "ZONE_CREATED")
    if direction is not None:
        zone["direction"] = direction
        zone["distance_ticks"] = distance
    base["zones"] = [zone]
    base["abstain"] = None
    base["decision"] = "CREATE"
    base["selected_cluster"] = dict(lower_tick=int(ticks[0]), upper_tick=int(ticks[-1]),
                                    score=float(score), count=len(ticks),
                                    ticks=[int(t) for t in ticks])
    return base


class SessionProfile:
    """Prior complete sessions only; FIFO is by SESSION, matching the C#."""

    def __init__(self, lookback_sessions=20):
        self.lookback = int(lookback_sessions)
        self.history = defaultdict(deque)
        self.pending = defaultdict(list)
        self.session_index = 0

    def commit(self):
        current = self.session_index
        for bucket, scores in self.pending.items():
            self.history[int(bucket)].append((current, list(map(float, scores))))
        min_session = current - self.lookback + 1
        for q in self.history.values():
            while q and q[0][0] < min_session:
                q.popleft()
        self.pending = defaultdict(list)
        self.session_index += 1

    def add_block(self, bucket, best_score):
        self.pending[int(bucket)].append(float(best_score))

    def history_scores(self, bucket):
        sessions = self.history.get(int(bucket), ())
        return [score for _session, session_scores in sessions for score in session_scores]

    def history_session_count(self, bucket):
        return len(self.history.get(int(bucket), ()))


def run(ticks, bars, footprints, params=None, debug_trace=False):
    """Uniform entrypoint; debug_trace exports every complete block."""
    from edgelab.bridge.sessions import session_begin_ns, session_end_ns

    p = {**RESEARCH_DEFAULTS, **(params or {})}
    window = int(p["window_bars"])
    tick_size = float(ticks.tick_size)
    n_bars = len(bars.close_t)
    if n_bars == 0:
        out = dict(indicator=NAME, params=p, zones=[])
        if debug_trace:
            out["block_trace"] = []
        return out

    session_of_bar = [session_end_ns(int(bars.end_ns[b])) for b in range(n_bars)]
    sessions_in_order, seen = [], set()
    for session_end in session_of_bar:
        if session_end not in seen:
            seen.add(session_end)
            sessions_in_order.append(session_end)

    profile = SessionProfile(lookback_sessions=int(p["lookback_sessions"]))
    all_zones, block_trace = [], []
    zone_seq = 0
    for sess_end in sessions_in_order:
        bar_indices = [b for b in range(n_bars) if session_of_bar[b] == sess_end]
        if not bar_indices:
            continue
        sess_begin = session_begin_ns(int(bars.end_ns[bar_indices[0]]))
        n_blocks = len(bar_indices) // window
        for block_i in range(n_blocks):
            block_bars = bar_indices[block_i * window:(block_i + 1) * window]
            cells = {}
            for b in block_bars:
                for price_tick, volume in footprints.total[int(b)].items():
                    tick = int(price_tick)
                    cells[tick] = cells.get(tick, 0.0) + float(volume)
            end_bar = block_bars[-1]
            bucket = session_relative_bucket(int(bars.end_ns[end_bar]), sess_begin,
                                             int(p["time_bucket_minutes"]))
            history_scores = profile.history_scores(bucket)
            result = detect_block(cells, history_scores, params=p,
                                  close_tick=int(bars.close_t[end_bar]))
            profile.add_block(bucket, result["best_score"])
            block_zone_ids = []
            for zone in result.get("zones", []):
                if zone.get("kind") != "OFF_PRICE":
                    continue
                zone_seq += 1
                lo_t, hi_t = int(zone["lower_tick"]), int(zone["upper_tick"])
                zid = str(zone_seq)
                block_zone_ids.append(zid)
                all_zones.append(dict(id=zid, indicator=NAME,
                                      top=(hi_t + 0.5) * tick_size,
                                      bottom=(lo_t - 0.5) * tick_size,
                                      created_ms=int(bars.end_ns[end_bar]) // 1_000_000,
                                      created_bar=int(end_bar), ended_ms=None,
                                      state="ACTIVE", kind="avol_cluster_off_price",
                                      touches=0, end_reason=None, timeline=[]))
            if debug_trace:
                block_trace.append(dict(
                    session_end_ns=int(sess_end), session_index=int(profile.session_index),
                    block_index=int(block_i), end_bar=int(end_bar),
                    block_end_ns=int(bars.end_ns[end_bar]), bucket=int(bucket),
                    n_cells=len(cells), cells={int(k): float(v) for k, v in cells.items()},
                    median=result.get("median"), hot_threshold=result.get("hot_threshold"),
                    best_score=result.get("best_score"), threshold=result.get("threshold"),
                    history_samples=result.get("history_samples"),
                    n_history_scores=len(history_scores), decision=result.get("decision"),
                    clusters=result.get("clusters", []),
                    selected_cluster=result.get("selected_cluster"),
                    abstain=result.get("abstain"), close_tick=int(bars.close_t[end_bar]),
                    zone_ids=block_zone_ids))
        profile.commit()
    out = dict(indicator=NAME, params=p, zones=all_zones)
    if debug_trace:
        out["block_trace"] = block_trace
    return out
