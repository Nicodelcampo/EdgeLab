# -*- coding: utf-8 -*-
"""aVolClusterPOI research kernel.

Cluster-mass anomaly versus the same session-relative time bucket.
No QualityScore gate, no LONG/SHORT, no target/stop, no BigTrap2.
"""
from __future__ import annotations

import math
from collections import defaultdict, deque

NAME = "aVolClusterPOI"
RESEARCH_DEFAULTS = dict(
    window_bars=10,
    median_multiplier=2.0,
    max_gap_ticks=1,
    min_cluster_ticks=2,
    time_bucket_minutes=30,
    lookback_sessions=20,
    detection_percentile=98.0,
    min_samples_per_bucket=20,
)


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


def cluster_hot_ticks(cells, median_multiplier, max_gap_ticks, min_cluster_ticks):
    """cells: dict[tick -> volume]. Returns list of (ticks, score)."""
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


def detect_block(cells, history_scores, params=None):
    p = {**RESEARCH_DEFAULTS, **(params or {})}
    clusters = cluster_hot_ticks(
        cells, p["median_multiplier"], p["max_gap_ticks"], p["min_cluster_ticks"]
    )
    best = max((score for _ticks, score in clusters), default=0.0)
    hist = sorted(history_scores or [])
    if len(hist) < int(p["min_samples_per_bucket"]):
        return dict(best_score=best, threshold=None, zones=[], abstain="warmup")
    thresh = empirical_quantile(hist, p["detection_percentile"] / 100.0)
    zones = []
    if thresh is not None and thresh > 0:
        for ticks, score in clusters:
            if score >= thresh:
                zones.append(dict(lower_tick=ticks[0], upper_tick=ticks[-1], score=score, threshold=thresh))
    return dict(best_score=best, threshold=thresh, zones=zones, abstain=None)


class SessionProfile:
    """Prior complete sessions only. Current session stays pending until roll."""

    def __init__(self, lookback_sessions=20):
        self.lookback = int(lookback_sessions)
        self.history = defaultdict(deque)
        self.pending = defaultdict(list)
        self.first_roll_done = False

    def commit(self):
        if not self.first_roll_done:
            self.pending.clear()
            self.first_roll_done = True
            return
        for bucket, scores in self.pending.items():
            q = self.history[bucket]
            q.extend(scores)
            while len(q) > self.lookback:
                q.popleft()
        self.pending = defaultdict(list)

    def add_block(self, bucket, best_score):
        self.pending[int(bucket)].append(float(best_score))

    def history_scores(self, bucket):
        return list(self.history.get(int(bucket), ()))
