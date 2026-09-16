import numpy as np
import pytest
from edgelab.research.void_revisit_episodes import (
    RevisitSpec,
    RevisitEpisode,
    EpisodeError,
    detect_revisit_episodes,
    episode_record
)

def test_reject_away_reapproach_and_traverse():
    p = [90, 98, 99, 98, 94, 93, 93, 94, 98, 99, 100, 103, 106, 110]
    t = np.arange(len(p), dtype=np.int64) * 10_000_000_000
    e = detect_revisit_episodes(
        t, p, np.ones(len(p)), 100, 110, 1,
        RevisitSpec(approach_ticks=1, rejection_excursion_ticks=6, min_away_seconds=10, max_episode_seconds=300)
    )
    assert len(e) == 1 and e[0].terminal == 'TRAVERSED'
    assert e[0].first_approach_idx < e[0].rejection_confirm_idx < e[0].second_approach_idx < e[0].terminal_idx
    assert e[0].second_entered is True
    assert e[0].reached_25 is True
    assert e[0].reached_50 is True
    assert e[0].reached_75 is True
    assert e[0].reached_100 is True
    assert e[0].traversal_speed_ticks_per_sec is not None
    assert e[0].traversal_speed_ticks_per_sec > 0


def test_second_rejection_is_distinct_terminal():
    p = [90, 99, 98, 94, 93, 93, 98, 99, 98, 94, 93]
    t = np.arange(len(p), dtype=np.int64) * 10_000_000_000
    e = detect_revisit_episodes(
        t, p, np.ones(len(p)), 100, 110, 1,
        RevisitSpec(min_away_seconds=10, max_episode_seconds=300)
    )
    assert len(e) == 1 and e[0].terminal == 'REJECTED_AGAIN'
    assert e[0].terminal_idx is not None
    assert e[0].reached_100 is False


def test_away_time_and_volume_are_required():
    p = [90, 99, 93, 99, 100, 110]
    t = np.arange(len(p), dtype=np.int64) * 1_000_000_000
    assert detect_revisit_episodes(
        t, p, np.ones(len(p)), 100, 110, 1,
        RevisitSpec(min_away_seconds=60, min_away_volume=10, max_episode_seconds=100)
    ) == []


def test_mirrored_short_side():
    p = [120, 111, 112, 116, 117, 117, 112, 111, 110, 105, 100]
    t = np.arange(len(p), dtype=np.int64) * 10_000_000_000
    e = detect_revisit_episodes(
        t, p, np.ones(len(p)), 100, 110, -1,
        RevisitSpec(min_away_seconds=10, max_episode_seconds=300)
    )
    assert len(e) == 1 and e[0].terminal == 'TRAVERSED'
    assert e[0].side == -1
    assert e[0].corridor_lower_tick == 100
    assert e[0].corridor_upper_tick == 110
    assert e[0].reached_100 is True


def test_strict_state_ordering():
    p = [90, 99, 98, 94, 93, 93, 93, 94, 99, 102, 105, 110]
    t = np.arange(len(p), dtype=np.int64) * 10_000_000_000
    e = detect_revisit_episodes(
        t, p, np.ones(len(p)), 100, 110, 1,
        RevisitSpec(min_away_seconds=20, max_episode_seconds=300)
    )
    assert len(e) == 1
    ep = e[0]
    assert ep.first_approach_idx < ep.rejection_confirm_idx <= ep.away_qualified_idx < ep.second_approach_idx < ep.terminal_idx


def test_immediate_first_traversal_excluded():
    # Price approaches lower (99), penetrates and traverses to 110 immediately on first approach
    p = [90, 99, 102, 105, 108, 110, 93, 99, 105]
    t = np.arange(len(p), dtype=np.int64) * 10_000_000_000
    e = detect_revisit_episodes(
        t, p, np.ones(len(p)), 100, 110, 1,
        RevisitSpec(min_away_seconds=10, max_episode_seconds=300)
    )
    assert len(e) == 0


def test_shallow_penetration_classified():
    # Void width = 10 (100 to 110).
    # Price enters to 102 (penetration = 2 ticks = 20% width -> class '0_25')
    p = [90, 99, 102, 97, 94, 93, 93, 98, 99, 105, 110]
    t = np.arange(len(p), dtype=np.int64) * 10_000_000_000
    e = detect_revisit_episodes(
        t, p, np.ones(len(p)), 100, 110, 1,
        RevisitSpec(approach_ticks=1, rejection_excursion_ticks=6, min_away_seconds=10, max_episode_seconds=300)
    )
    assert len(e) == 1
    assert e[0].first_penetration_ticks == 2
    assert e[0].first_penetration_ratio == 0.2
    assert e[0].first_penetration_class == "0_25"
    assert e[0].terminal == "TRAVERSED"


def test_competing_risks_censoring_on_timeout():
    # Price approaches, rejects, qualifies away, re-approaches, but neither traverses nor moves away 6 ticks before deadline
    p = [90, 99, 93, 93, 99, 101, 102, 101, 102]
    t = [0, 10, 20, 40, 50, 60, 70, 80, 150] # deadline at 100s
    t_ns = [x * 1_000_000_000 for x in t]
    e = detect_revisit_episodes(
        t_ns, p, np.ones(len(p)), 100, 110, 1,
        RevisitSpec(min_away_seconds=10, max_episode_seconds=90)
    )
    assert len(e) == 1
    assert e[0].terminal == "CENSORED"
    assert e[0].terminal_idx is None
    assert e[0].second_entered is True
    assert e[0].reached_25 is False


def test_validation_rejects_malformed_inputs():
    with pytest.raises(EpisodeError, match="timestamps must be ordered"):
        detect_revisit_episodes([100, 50], [90, 91], [1.0, 1.0], 100, 110, 1)
    with pytest.raises(EpisodeError, match="invalid geometry/side"):
        detect_revisit_episodes([100, 200], [90, 91], [1.0, 1.0], 110, 100, 1)
    with pytest.raises(EpisodeError, match="negative volume"):
        detect_revisit_episodes([100, 200], [90, 91], [-1.0, 1.0], 100, 110, 1)


def test_episode_record_serialization():
    p = [90, 99, 93, 93, 99, 110]
    t = np.arange(len(p), dtype=np.int64) * 10_000_000_000
    e = detect_revisit_episodes(
        t, p, np.ones(len(p)), 100, 110, 1,
        RevisitSpec(min_away_seconds=10, max_episode_seconds=300)
    )
    assert len(e) == 1
    rec = episode_record(e[0])
    assert isinstance(rec, dict)
    assert rec["terminal"] == "TRAVERSED"
    assert "traversal_speed_ticks_per_sec" in rec
