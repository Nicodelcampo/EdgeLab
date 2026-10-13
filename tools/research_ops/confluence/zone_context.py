"""Bounded causal zone context, without an all-pairs graph or outcome access.

Scope = snapshots recognized to date from same-session births. Not native zone
liveness, a touch detector, a trade signal, or a mechanism-negative classifier.
Integer HALF-tick lattice: occupancy counts closed integer coordinates.
"""
from bisect import bisect_left, bisect_right, insort
from datetime import date, datetime
import math
from .asof_intersections import Clock, Snapshot, _Node, _put, _delete, _intersect

FAMILIES = ('AVZP2', 'RACIMO')
DENSITY_NAMES = tuple(f'{f}:{k}' for f in FAMILIES for k in
                      ('log_count', 'log_sum_width_cells', 'local_union_fraction', 'log_local_count'))
GEOMETRY_NAMES = ('AVZP2:signed_nearest_gap', 'RACIMO:signed_nearest_gap',
                  'joint_local_union_fraction', 'inside_both')
ARRIVAL_NAMES = ('AVZP2:distance_reduction', 'RACIMO:distance_reduction',
                 'AVZP2:unchanged_snapshot_at_prior', 'RACIMO:unchanged_snapshot_at_prior')


def union_cells(intervals):
    """Exact closed-lattice union; point bands occupy one half-tick cell."""
    total = 0; high = None
    for lo, hi in sorted(intervals):
        if high is None or lo > high + 1:
            total += hi - lo + 1; high = hi
        elif hi > high:
            total += hi - high; high = hi
    return total


def union_segments(intervals):
    out = []
    for lo, hi in sorted(intervals):
        if not out or lo > out[-1][1] + 1: out.append([lo, hi])
        elif hi > out[-1][1]: out[-1][1] = hi
    return out


def joint_cells(left, right):
    """Two-pointer intersection of unions, never pair materialization."""
    a = union_segments(left); b = union_segments(right); i = j = total = 0
    while i < len(a) and j < len(b):
        lo = max(a[i][0], b[j][0]); hi = min(a[i][1], b[j][1])
        if hi >= lo: total += hi - lo + 1
        if a[i][1] < b[j][1]: i += 1
        else: j += 1
    return total


def signed_gap(s, midpoint2):
    if midpoint2 < s.lo2: return s.lo2 - midpoint2
    if midpoint2 > s.hi2: return s.hi2 - midpoint2
    return 0


class ZoneContext:
    """Session-local bounded endpoint + treap index; no retained pair graph.

    Endpoint insert/delete use Python list movement (O(N)), not a claimed hard
    O(log N) update. Local query is output-sensitive; budget overflow fails the
    entire instance, without truncation. Snapshot revision invalidates a 20s
    approach comparison until that *unchanged snapshot* existed at its origin.
    """
    def __init__(self, *, trade_date, max_active=20000, max_seen=100000, max_query_hits=20000, max_total_query_hits=10000000):
        d = date.fromisoformat(trade_date)
        if d.isoformat() != trade_date or d >= date(2026, 10, 1): raise ValueError('preholdout context session')
        for n in (max_active, max_seen, max_query_hits, max_total_query_hits):
            if type(n) is not int or n < 1: raise ValueError('positive context capacities')
        if max_seen < max_active: raise ValueError('seen capacity below active')
        self.end_ns = int(datetime.fromisoformat(trade_date + 'T22:00:00+00:00').timestamp()) * 10**9
        self.start_ns = self.end_ns - 86400 * 10**9
        self.trade_date = trade_date; self.max_active = max_active; self.max_seen = max_seen
        self.max_query_hits = max_query_hits; self.max_total_query_hits = max_total_query_hits; self.active = {}; self.seen = set()
        self.roots = {f: None for f in FAMILIES}; self.lower = {f: [] for f in FAMILIES}
        self.upper = {f: [] for f in FAMILIES}; self.width = {f: 0 for f in FAMILIES}
        self.clock = self.anchor_clock = None; self.poisoned = False
        self.query_hits = self.mutation_count = self.anchor_count = 0

    def _live(self):
        if self.poisoned: raise ValueError('poisoned context')

    def _drop(self, old):
        f = old.key.family
        self.roots[f] = _delete(self.roots[f], (old.lo2, old.key))
        for arr, coord in ((self.lower[f], old.lo2), (self.upper[f], old.hi2)):
            i = bisect_left(arr, coord)
            if i == len(arr) or arr[i] != coord: raise ValueError('endpoint index drift')
            arr.pop(i)
        self.width[f] -= old.hi2 - old.lo2 + 1

    def apply(self, clock, *, upserts=(), removals=()):
        self._live()
        if not isinstance(clock, Clock) or not self.start_ns <= clock.ns < self.end_ns:
            raise ValueError('context clock outside bound natural session')
        if self.clock is not None and clock <= self.clock:
            raise ValueError('strict atomic context clocks')
        if self.anchor_clock is not None and clock <= self.anchor_clock:
            raise ValueError('mutation cannot arrive after anchor at same/earlier clock')
        ups = tuple(upserts); rem = tuple(removals)
        if any(not isinstance(s, Snapshot) or s.key.family not in FAMILIES for s in ups):
            raise ValueError('typed AVZP2/racimo snapshots only')
        keys = [s.key for s in ups]
        if len(set(keys)) != len(keys) or len(set(rem)) != len(rem) or set(keys) & set(rem):
            raise ValueError('duplicate/conflicting context batch')
        if any(k not in self.active for k in rem): raise ValueError('unknown context removal')
        new = 0
        for s in ups:
            if s.available != clock: raise ValueError('snapshot availability differs from batch')
            old = self.active.get(s.key)
            if old:
                if s.revision != old.revision + 1 or s.recognized != old.recognized:
                    raise ValueError('exact revision and immutable recognition required')
            else:
                if s.key in self.seen or s.revision != 0 or s.recognized != clock:
                    raise ValueError('no resurrection/backdated birth')
                new += 1
        if len(self.active) - len(rem) + new > self.max_active or len(self.seen) + new > self.max_seen:
            self.poisoned = True; raise ValueError('context capacity; no truncation')
        try:
            for k in rem: self._drop(self.active.pop(k))
            for s in ups:
                if s.key in self.active: self._drop(self.active[s.key])
                f = s.key.family; self.active[s.key] = s; self.seen.add(s.key)
                self.roots[f] = _put(self.roots[f], _Node(s))
                insort(self.lower[f], s.lo2); insort(self.upper[f], s.hi2)
                self.width[f] += s.hi2 - s.lo2 + 1
            self.clock = clock; self.mutation_count += len(ups) + len(rem)
        except BaseException:
            self.poisoned = True; raise

    def _query(self, family, lo, hi, work):
        out = []
        for s in _intersect(self.roots[family], lo, hi):
            work[0] += 1
            if work[0] > self.max_query_hits or self.query_hits + work[0] > self.max_total_query_hits:
                self.poisoned = True; raise ValueError('context query capacity; no truncation')
            out.append(s)
        return out

    def _nearest(self, family, midpoint2, local, work):
        inside = [s for s in local if s.lo2 <= midpoint2 <= s.hi2]
        if inside: return min(inside, key=lambda s: (s.hi2 - s.lo2, s.key))
        lo = self.lower[family]; hi = self.upper[family]; candidates = []
        a = bisect_right(hi, midpoint2) - 1; b = bisect_left(lo, midpoint2)
        distances = []
        if a >= 0: distances.append(midpoint2 - hi[a])
        if b < len(lo): distances.append(lo[b] - midpoint2)
        if not distances: return None
        dist = min(distances)
        # Endpoint ties are resolved by fixed geometry/identity, not arrival/outcome.
        for coordinate in (midpoint2 - dist, midpoint2 + dist):
            candidates.extend(self._query(family, coordinate, coordinate, work))
        return min(candidates, key=lambda s: (abs(signed_gap(s, midpoint2)), s.hi2 - s.lo2, s.key))

    def observe(self, clock, *, midpoint2, prior_clock, prior_midpoint2, radius_ticks):
        self._live()
        if not isinstance(clock, Clock) or not isinstance(prior_clock, Clock) or prior_clock >= clock:
            raise ValueError('ordered typed anchor/prior clocks')
        if not self.start_ns <= prior_clock.ns <= clock.ns < self.end_ns:
            raise ValueError('anchor/prior outside bound natural session')
        if self.clock is not None and self.clock > clock: raise ValueError('future snapshot at anchor')
        if self.anchor_clock is not None and clock <= self.anchor_clock: raise ValueError('strict anchor clocks')
        if any(type(v) is not int for v in (midpoint2, prior_midpoint2, radius_ticks)) or radius_ticks < 1:
            raise ValueError('integer midpoint and positive whole-tick radius')
        radius2 = 2 * radius_ticks; lo = midpoint2 - radius2; hi = midpoint2 + radius2
        domain = hi - lo + 1; work = [0]; density = []; geometry = []; arrival_delta = []; existed = []
        intervals = {}; inside = {}; nearest_present = {}
        for f in FAMILIES:
            hits = self._query(f, lo, hi, work)
            clipped = [(max(lo, s.lo2), min(hi, s.hi2)) for s in hits]; intervals[f] = clipped
            density.extend((math.log1p(len(self.lower[f])), math.log1p(self.width[f]),
                            union_cells(clipped) / domain, math.log1p(len(hits))))
            near = self._nearest(f, midpoint2, hits, work); nearest_present[f] = near is not None
            geometry.append(0. if near is None else math.tanh(signed_gap(near, midpoint2) / radius2))
            inside[f] = any(s.lo2 <= midpoint2 <= s.hi2 for s in hits)
            old = near is not None and near.available <= prior_clock
            existed.append(float(old))
            delta = (abs(signed_gap(near, prior_midpoint2)) - abs(signed_gap(near, midpoint2))) / radius2 if old else 0.
            arrival_delta.append(math.tanh(delta))
        geometry.extend((joint_cells(intervals['AVZP2'], intervals['RACIMO']) / domain,
                         float(inside['AVZP2'] and inside['RACIMO'])))
        self.anchor_clock = clock; self.anchor_count += 1; self.query_hits += work[0]
        return {'density': tuple(density), 'geometry': tuple(geometry),
                'arrival': tuple(arrival_delta + existed), 'nearest_present': nearest_present,
                'scope': 'SAME_SESSION_RECOGNIZED_SNAPSHOTS_NOT_NATIVE_LIVENESS',
                'arrival_scope': '20S_ENDPOINT_APPROACH_NOT_FIRST_TOUCH_OR_TRAVERSED_PATH'}
