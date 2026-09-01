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
    """Mirror of C# GetTimeBucket(Time[0]) for SessionRelative mode.

    NT8 anchors the bucket at ``barCloseTime.AddSeconds(-1)``. Without the
    subtraction, blocks closing exactly at :30/:00 are assigned to the next
    bucket in Python and parity is impossible.
    """
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
                score = sum(cells[t] for t in current)
                clusters.append((list(current), score))
            current = [tick]
    if len(current) >= int(min_cluster_ticks):
        score = sum(cells[t] for t in current)
        clusters.append((list(current), score))
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


def detect_block(cells, history_scores, params=None, close_tick=None):
    p = {**RESEARCH_DEFAULTS, **(params or {})}
    clusters = cluster_hot_ticks(
        cells, p["median_multiplier"], p["max_gap_ticks"], p["min_cluster_ticks"]
    )
    best = max((score for _ticks, score in clusters), default=0.0)
    hist = sorted(history_scores or [])
    if len(hist) < int(p["min_samples_per_bucket"]):
        return dict(best_score=best, threshold=None, zones=[], abstain="warmup")
    thresh = empirical_quantile(hist, p["detection_percentile"] / 100.0)
    passing = []
    if thresh is not None and thresh > 0:
        passing = [(ticks, score) for ticks, score in clusters if score >= thresh]
    if not passing:
        return dict(best_score=best, threshold=thresh, zones=[], abstain=None)
    ticks, score = max(passing, key=lambda item: item[1])
    kind, direction, distance = classify_kind(close_tick, ticks[0], ticks[-1])
    zone = dict(
        lower_tick=ticks[0],
        upper_tick=ticks[-1],
        score=score,
        threshold=thresh,
        kind=kind,
        event_type="AT_PRICE_CREATED" if kind == "AT_PRICE" else "ZONE_CREATED",
    )
    if direction is not None:
        zone["direction"] = direction
        zone["distance_ticks"] = distance
    return dict(best_score=best, threshold=thresh, zones=[zone], abstain=None)


class SessionProfile:
    """Prior complete sessions only; FIFO is by SESSION, matching the C#.

    ``history[bucket]`` stores one list per complete session. A 30-minute
    bucket normally receives three scores (three disjoint 10-bar blocks) per
    session. The previous Python implementation flattened scores into a deque
    capped at ``lookback``, retaining only ~6-7 sessions when lookback=20; it
    also discarded the first complete session. Both behaviors contradicted
    ``nt8/aVolClusterPOI.cs::CommitSession``.
    """

    def __init__(self, lookback_sessions=20):
        self.lookback = int(lookback_sessions)
        # bucket -> deque[(global_session_index, list[score])]
        self.history = defaultdict(deque)
        self.pending = defaultdict(list)
        self.session_index = 0

    def commit(self):
        current = self.session_index
        for bucket, scores in self.pending.items():
            self.history[int(bucket)].append((current, list(map(float, scores))))
        # C# prunes EVERY bucket by global Session index, even when that bucket
        # was absent in the session just committed.
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


def run(ticks, bars, footprints, params=None):
    """Uniform entrypoint for tools/paridad_oraculo.py's KERNELS dict.

    This kernel exposes primitives only (SessionProfile, detect_block,
    cluster_hot_ticks) -- no run() existed before, no bars/footprints
    construction, no session iteration. This is that orchestration, written
    fresh against the primitives above (not against
    edgelab/research/avolcluster_nq_zone_builder.py's build_session_creation_events,
    which computes the time bucket without the "-1 second" anchor adjustment
    that session_relative_bucket() above documents as required for parity --
    reusing that path would have silently reintroduced the exact off-by-one
    bug it exists to avoid).

    Emits zones in the schema edgelab.bridge.parity.match_zones consumes
    (id/top/bottom/created_ms/state/touches), the same shape already used by
    edgelab/bridge/indicators/avolcellpoi2.py::run() -- including the
    "(tick - 0.5) * tick_size" boundary convention parity.py's _geom_ticks
    depends on for exact half-tick geometry comparison.

    This kernel does not track zone lifecycle (no FIRST_TOUCH,
    ZONE_INVALIDATED): every zone comes back state="ACTIVE", touches=0,
    ended_ms=None. Mature NT8 zones that touched or invalidated will show as
    STATE_ORDER_DIFF/FEATURE_DIFF (WARN, non-blocking) against this -- that is
    the kernel's real, declared coverage, not a bug in this adapter.
    """
    from edgelab.bridge.sessions import session_begin_ns, session_end_ns

    p = {**RESEARCH_DEFAULTS, **(params or {})}
    window = int(p["window_bars"])
    tick_size = float(ticks.tick_size)

    n_bars = len(bars.close_t)
    if n_bars == 0:
        return dict(indicator=NAME, params=p, zones=[])

    # Group bar indices by CME ETH session (17:00 CT -> 16:00 CT), same
    # calendar edgelab/bridge/sessions.py documents as replicating NT8's
    # SessionIterator with the CME US Index/FX Futures ETH template.
    session_of_bar = [session_end_ns(int(bars.end_ns[b])) for b in range(n_bars)]
    sessions_in_order: list[int] = []
    seen = set()
    for s in session_of_bar:
        if s not in seen:
            seen.add(s)
            sessions_in_order.append(s)

    profile = SessionProfile(lookback_sessions=int(p["lookback_sessions"]))
    all_zones: list[dict] = []
    zone_seq = 0

    for sess_end in sessions_in_order:
        bar_indices = [b for b in range(n_bars) if session_of_bar[b] == sess_end]
        if not bar_indices:
            continue
        sess_begin = session_begin_ns(int(bars.end_ns[bar_indices[0]]))
        n_blocks = len(bar_indices) // window
        for block_i in range(n_blocks):
            block_bars = bar_indices[block_i * window:(block_i + 1) * window]
            cells: dict[int, float] = {}
            for b in block_bars:
                for price_tick, volume in footprints.total[int(b)].items():
                    t = int(price_tick)
                    cells[t] = cells.get(t, 0.0) + float(volume)
            end_bar = block_bars[-1]
            bucket = session_relative_bucket(
                int(bars.end_ns[end_bar]), sess_begin, int(p["time_bucket_minutes"])
            )
            history_scores = profile.history_scores(bucket)
            result = detect_block(
                cells, history_scores, params=p, close_tick=int(bars.close_t[end_bar]),
            )
            profile.add_block(bucket, result["best_score"])
            for zone in result.get("zones", []):
                if zone.get("kind") != "OFF_PRICE":
                    continue
                zone_seq += 1
                lo_t, hi_t = int(zone["lower_tick"]), int(zone["upper_tick"])
                all_zones.append(dict(
                    id=str(zone_seq),
                    indicator=NAME,
                    top=(hi_t + 0.5) * tick_size,
                    bottom=(lo_t - 0.5) * tick_size,
                    created_ms=int(bars.end_ns[end_bar]) // 1_000_000,
                    created_bar=int(end_bar),
                    ended_ms=None,
                    state="ACTIVE",
                    kind="avol_cluster_off_price",
                    touches=0,
                    end_reason=None,
                    timeline=[],
                ))
        profile.commit()

    return dict(indicator=NAME, params=p, zones=all_zones)
