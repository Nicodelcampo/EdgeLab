"""Target-free episode labelling for rejection -> excursion -> re-approach of a frozen void."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Sequence
import numpy as np

class EpisodeError(ValueError): pass

@dataclass(frozen=True)
class RevisitSpec:
    approach_ticks: int = 1
    rejection_excursion_ticks: int = 6
    min_away_seconds: float = 60.0
    min_away_volume: float = 0.0
    min_away_trades: int = 0
    crossing_buffer_ticks: int = 0
    max_episode_seconds: float = 3600.0
    max_first_penetration_ratio: float = 0.50  # Allow shallow penetration up to 50% without full traversal

@dataclass(frozen=True)
class RevisitEpisode:
    side: int
    first_approach_idx: int
    rejection_confirm_idx: int
    away_qualified_idx: int
    second_approach_idx: int
    terminal_idx: int | None
    terminal: str
    elapsed_away_seconds: float
    volume_away: float
    max_excursion_ticks: int
    corridor_lower_tick: int
    corridor_upper_tick: int
    trades_away: int = 0
    first_penetration_ticks: int = 0
    first_penetration_ratio: float = 0.0
    first_penetration_class: str = "none"  # "none" | "0_25" | "25_50" | "50_plus"
    second_entered: bool = False
    second_max_penetration_ticks: int = 0
    second_max_penetration_ratio: float = 0.0
    reached_25: bool = False
    reached_50: bool = False
    reached_75: bool = False
    reached_100: bool = False
    time_to_25_s: float | None = None
    time_to_50_s: float | None = None
    time_to_75_s: float | None = None
    time_to_100_s: float | None = None
    ticks_to_terminal: int = 0
    volume_to_terminal: float = 0.0
    traversal_speed_ticks_per_sec: float | None = None


def _validate(ts: np.ndarray, px: np.ndarray, vol: np.ndarray) -> None:
    if len(ts) != len(px) or len(ts) != len(vol) or len(ts) == 0:
        raise EpisodeError("aligned non-empty arrays required")
    if np.any(ts[1:] < ts[:-1]):
        raise EpisodeError("timestamps must be ordered")
    if np.any(vol < 0):
        raise EpisodeError("negative volume")


def detect_revisit_episodes(
    ts_ns: Sequence[int],
    price_ticks: Sequence[int],
    volume: Sequence[float],
    lower_tick: int,
    upper_tick: int,
    side: int,
    spec: RevisitSpec = RevisitSpec()
) -> list[RevisitEpisode]:
    """Detect non-overlapping causal episodes around geometry frozen at episode start.

    side=+1 approaches from below and traverses above upper; side=-1 mirrors it.
    A first approach reaches near boundary, may penetrate partially without full traversal,
    travels the required excursion away, remains/trades away enough to qualify, and then
    re-approaches. Terminal is TRAVERSED, REJECTED_AGAIN or CENSORED.
    This labels structural microstructural state transitions, never P&L or trading rules.
    """
    if side not in (-1, 1) or lower_tick >= upper_tick:
        raise EpisodeError("invalid geometry/side")
    t = np.asarray(ts_ns, np.int64)
    p = np.asarray(price_ticks, np.int64)
    v = np.asarray(volume, float)
    _validate(t, p, v)

    near = lower_tick if side == 1 else upper_tick
    far = upper_tick if side == 1 else lower_tick
    width = upper_tick - lower_tick

    approach = lambda x: (x >= near - spec.approach_ticks and x < far) if side == 1 else (x <= near + spec.approach_ticks and x > far)
    away_dist = lambda x: (near - x) if side == 1 else (x - near)
    penetration = lambda x: max(0, int(x - near)) if side == 1 else max(0, int(near - x))
    traversed = lambda x: (x >= far + spec.crossing_buffer_ticks) if side == 1 else (x <= far - spec.crossing_buffer_ticks)

    out = []
    i = 0
    n = len(t)

    while i < n:
        # Search for first approach
        while i < n and not approach(p[i]):
            i += 1
        if i >= n:
            break

        a = i
        deadline = t[a] + int(spec.max_episode_seconds * 1e9)
        j = a
        max_first_pen = 0
        confirmed_reject = False

        while j < n and t[j] <= deadline:
            # If price traversed immediately on first approach, it's not a rejection episode
            if traversed(p[j]):
                break

            pen = penetration(p[j])
            max_first_pen = max(max_first_pen, pen)

            # If penetration exceeds allowable threshold without excursion, discard
            if pen > spec.max_first_penetration_ratio * width:
                break

            # Check if rejection excursion distance is satisfied
            if away_dist(p[j]) >= spec.rejection_excursion_ticks:
                confirmed_reject = True
                break
            j += 1

        if not confirmed_reject or j >= n or t[j] > deadline:
            i = max(a + 1, j + 1)
            continue

        reject = j
        first_pen_ratio = max_first_pen / max(1, width)
        if max_first_pen == 0:
            first_pen_class = "none"
        elif first_pen_ratio <= 0.25:
            first_pen_class = "0_25"
        elif first_pen_ratio <= 0.50:
            first_pen_class = "25_50"
        else:
            first_pen_class = "50_plus"

        # Away qualification phase
        vol_away = 0.0
        trades_away = 0
        max_exc = int(away_dist(p[reject]))
        k = reject
        qualified = None

        while k < n and t[k] <= deadline:
            dist = int(away_dist(p[k]))
            max_exc = max(max_exc, dist)
            vol_away += float(v[k])
            trades_away += 1
            elapsed = (t[k] - t[reject]) / 1e9

            # Premature re-approach check: price returned to approach boundary before qualifying
            if dist < spec.rejection_excursion_ticks and approach(p[k]) and qualified is None:
                break

            if (elapsed >= spec.min_away_seconds and
                vol_away >= spec.min_away_volume and
                trades_away >= spec.min_away_trades):
                qualified = k
                break
            k += 1

        if qualified is None:
            i = max(a + 1, k)
            continue

        # Search for second approach
        r = qualified + 1
        while r < n and t[r] <= deadline and not approach(p[r]):
            dist = int(away_dist(p[r]))
            max_exc = max(max_exc, dist)
            vol_away += float(v[r])
            trades_away += 1
            r += 1

        if r >= n or t[r] > deadline:
            # Censored while waiting for second approach
            c_idx = min(r, n - 1)
            out.append(RevisitEpisode(
                side=side,
                first_approach_idx=a,
                rejection_confirm_idx=reject,
                away_qualified_idx=qualified,
                second_approach_idx=c_idx,
                terminal_idx=None,
                terminal="CENSORED",
                elapsed_away_seconds=(t[c_idx] - t[reject]) / 1e9,
                volume_away=vol_away,
                max_excursion_ticks=max_exc,
                corridor_lower_tick=lower_tick,
                corridor_upper_tick=upper_tick,
                trades_away=trades_away,
                first_penetration_ticks=max_first_pen,
                first_penetration_ratio=first_pen_ratio,
                first_penetration_class=first_pen_class,
                second_entered=False,
                second_max_penetration_ticks=0,
                second_max_penetration_ratio=0.0,
                reached_25=False, reached_50=False, reached_75=False, reached_100=False,
                time_to_25_s=None, time_to_50_s=None, time_to_75_s=None, time_to_100_s=None,
                ticks_to_terminal=c_idx - a + 1,
                volume_to_terminal=0.0,
                traversal_speed_ticks_per_sec=None
            ))
            break

        # Reached second approach at index r
        second_entered = False
        second_max_pen = 0
        reached_25 = False
        reached_50 = False
        reached_75 = False
        reached_100 = False
        time_25 = None
        time_50 = None
        time_75 = None
        time_100 = None
        terminal = None
        q = r

        while q < n and t[q] <= deadline:
            pen = penetration(p[q])
            if pen > 0:
                second_entered = True
            second_max_pen = max(second_max_pen, pen)
            ratio = second_max_pen / max(1, width)

            if not reached_25 and ratio >= 0.25:
                reached_25 = True
                time_25 = (t[q] - t[r]) / 1e9
            if not reached_50 and ratio >= 0.50:
                reached_50 = True
                time_50 = (t[q] - t[r]) / 1e9
            if not reached_75 and ratio >= 0.75:
                reached_75 = True
                time_75 = (t[q] - t[r]) / 1e9
            if not reached_100 and ratio >= 1.0:
                reached_100 = True
                time_100 = (t[q] - t[r]) / 1e9

            if traversed(p[q]):
                terminal = (q, "TRAVERSED")
                break
            if away_dist(p[q]) >= spec.rejection_excursion_ticks:
                terminal = (q, "REJECTED_AGAIN")
                break
            q += 1

        if terminal:
            term_idx, term_status = terminal
            vol_term = float(np.sum(v[r:term_idx + 1]))
            tks_term = term_idx - r + 1
        else:
            term_idx = None
            term_status = "CENSORED"
            c_end = min(q, n - 1)
            vol_term = float(np.sum(v[r:c_end + 1]))
            tks_term = c_end - r + 1

        speed = None
        if term_status == "TRAVERSED" and term_idx is not None:
            elapsed_traversal = max(1e-6, (t[term_idx] - t[r]) / 1e9)
            speed = width / elapsed_traversal

        out.append(RevisitEpisode(
            side=side,
            first_approach_idx=a,
            rejection_confirm_idx=reject,
            away_qualified_idx=qualified,
            second_approach_idx=r,
            terminal_idx=term_idx,
            terminal=term_status,
            elapsed_away_seconds=(t[r] - t[reject]) / 1e9,
            volume_away=vol_away,
            max_excursion_ticks=max_exc,
            corridor_lower_tick=lower_tick,
            corridor_upper_tick=upper_tick,
            trades_away=trades_away,
            first_penetration_ticks=max_first_pen,
            first_penetration_ratio=first_pen_ratio,
            first_penetration_class=first_pen_class,
            second_entered=second_entered,
            second_max_penetration_ticks=second_max_pen,
            second_max_penetration_ratio=second_max_pen / max(1, width),
            reached_25=reached_25,
            reached_50=reached_50,
            reached_75=reached_75,
            reached_100=reached_100,
            time_to_25_s=time_25,
            time_to_50_s=time_50,
            time_to_75_s=time_75,
            time_to_100_s=time_100,
            ticks_to_terminal=tks_term,
            volume_to_terminal=vol_term,
            traversal_speed_ticks_per_sec=speed
        ))

        i = (term_idx + 1) if term_idx is not None else n

    return out


def episode_record(ep: RevisitEpisode) -> dict:
    return asdict(ep)
