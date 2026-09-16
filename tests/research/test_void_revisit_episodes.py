import numpy as np
from edgelab.research.void_revisit_episodes import *

def test_reject_away_reapproach_and_traverse():
    p=[90,98,99,98,94,93,93,94,98,99,100,103,106,110]
    t=np.arange(len(p),dtype=np.int64)*10_000_000_000
    e=detect_revisit_episodes(t,p,np.ones(len(p)),100,110,1,RevisitSpec(approach_ticks=1,rejection_excursion_ticks=6,min_away_seconds=10,max_episode_seconds=300))
    assert len(e)==1 and e[0].terminal=='TRAVERSED'
    assert e[0].first_approach_idx<e[0].rejection_confirm_idx<e[0].second_approach_idx<e[0].terminal_idx
    assert e[0].stage_at_censoring is None

def test_second_rejection_is_distinct_terminal():
    p=[90,99,98,94,93,93,98,99,98,94,93]
    t=np.arange(len(p),dtype=np.int64)*10_000_000_000
    e=detect_revisit_episodes(t,p,np.ones(len(p)),100,110,1,RevisitSpec(min_away_seconds=10,max_episode_seconds=300))
    assert len(e)==1 and e[0].terminal=='REJECTED_AGAIN'
    assert e[0].stage_at_censoring is None

def test_away_time_and_volume_are_required():
    p=[90,99,93,99,100,110]; t=np.arange(len(p),dtype=np.int64)*1_000_000_000
    # Price enters 99, rejects to 93, but leaves before min_away_seconds=60 is met:
    e = detect_revisit_episodes(t,p,np.ones(len(p)),100,110,1,RevisitSpec(min_away_seconds=60,min_away_volume=10,max_episode_seconds=100))
    # Array ends before qualification, so it is recorded as censored in away accumulation
    assert len(e) == 1
    assert e[0].terminal == 'CENSORED_DATA_EDGE'
    assert e[0].stage_at_censoring == 'AWAY_ACCUMULATING'

def test_mirrored_short_side():
    p=[120,111,112,116,117,117,112,111,110,105,100]
    t=np.arange(len(p),dtype=np.int64)*10_000_000_000
    e=detect_revisit_episodes(t,p,np.ones(len(p)),100,110,-1,RevisitSpec(min_away_seconds=10,max_episode_seconds=300))
    assert len(e)==1 and e[0].terminal=='TRAVERSED'

def test_censored_contract_roll_at_terminal_phase():
    p = [90, 98, 99, 98, 94, 93, 93, 94, 98, 99, 99, 98, 97]
    t = np.arange(len(p), dtype=np.int64) * 10_000_000_000
    rolls = [False] * len(p)
    rolls[11] = True
    e = detect_revisit_episodes(t, p, np.ones(len(p)), 100, 110, 1,
                                RevisitSpec(min_away_seconds=10, max_episode_seconds=300),
                                state_reset_flags=rolls)
    assert len(e) == 1
    assert e[0].terminal == 'CENSORED_CONTRACT_ROLL'
    assert e[0].terminal_idx == 11
    assert e[0].stage_at_censoring == 'SECOND_APPROACH'

def test_censored_session_end_at_terminal_phase():
    p = [90, 98, 99, 98, 94, 93, 93, 94, 98, 99, 99, 98, 97]
    t = np.arange(len(p), dtype=np.int64) * 10_000_000_000
    sessions = [20260603] * 10 + [20260604] * 3
    e = detect_revisit_episodes(t, p, np.ones(len(p)), 100, 110, 1,
                                RevisitSpec(min_away_seconds=10, max_episode_seconds=300),
                                session_ids=sessions)
    assert len(e) == 1
    assert e[0].terminal == 'CENSORED_SESSION_END'
    assert e[0].terminal_idx == 10
    assert e[0].stage_at_censoring == 'SECOND_APPROACH'

def test_censored_max_followup():
    p = [90, 98, 99, 98, 94, 93, 93, 94, 98, 99, 99, 99, 99]
    t = np.arange(len(p), dtype=np.int64) * 10_000_000_000
    e = detect_revisit_episodes(t, p, np.ones(len(p)), 100, 110, 1,
                                RevisitSpec(min_away_seconds=10, max_episode_seconds=95))
    assert len(e) == 1
    assert e[0].terminal == 'CENSORED_MAX_FOLLOWUP'
    assert e[0].stage_at_censoring == 'SECOND_APPROACH'

def test_censored_data_edge():
    p = [90, 98, 99, 98, 94, 93, 93, 94, 98, 99, 99]
    t = np.arange(len(p), dtype=np.int64) * 10_000_000_000
    e = detect_revisit_episodes(t, p, np.ones(len(p)), 100, 110, 1,
                                RevisitSpec(min_away_seconds=10, max_episode_seconds=500))
    assert len(e) == 1
    assert e[0].terminal == 'CENSORED_DATA_EDGE'
    assert e[0].stage_at_censoring == 'SECOND_APPROACH'

def test_all_censoring_terminals_in_valid_set():
    for term in ["TRAVERSED", "REJECTED_AGAIN", "CENSORED_SESSION_END",
                 "CENSORED_CONTRACT_ROLL", "CENSORED_DATA_EDGE", "CENSORED_MAX_FOLLOWUP"]:
        assert term in VALID_TERMINALS

# ==================== CRITICAL EDGE CASES REQUESTED IN AUDIT ====================

def test_roll_during_first_approach_emits_censored_episode():
    # First approach at index 1 (p=99). Before rejection excursion (6 ticks) is reached, roll occurs at index 2.
    p = [90, 99, 98, 97]
    t = np.arange(len(p), dtype=np.int64) * 10_000_000_000
    rolls = [False, False, True, False]
    e = detect_revisit_episodes(t, p, np.ones(len(p)), 100, 110, 1,
                                RevisitSpec(rejection_excursion_ticks=6),
                                state_reset_flags=rolls)
    assert len(e) == 1
    assert e[0].terminal == 'CENSORED_CONTRACT_ROLL'
    assert e[0].stage_at_censoring == 'FIRST_APPROACH'
    assert e[0].terminal_idx == 2
    assert e[0].rejection_confirm_idx is None

def test_roll_during_away_accumulation_emits_censored_episode():
    # First approach at index 1 (p=99), rejection confirmed at index 2 (p=93, excursion=7 >= 6).
    # Roll occurs at index 3 before min_away_seconds=60 is satisfied (only 10s elapsed).
    p = [90, 99, 93, 92, 92]
    t = np.arange(len(p), dtype=np.int64) * 10_000_000_000
    rolls = [False, False, False, True, False]
    e = detect_revisit_episodes(t, p, np.ones(len(p)), 100, 110, 1,
                                RevisitSpec(rejection_excursion_ticks=6, min_away_seconds=60),
                                state_reset_flags=rolls)
    assert len(e) == 1
    assert e[0].terminal == 'CENSORED_CONTRACT_ROLL'
    assert e[0].stage_at_censoring == 'AWAY_ACCUMULATING'
    assert e[0].terminal_idx == 3
    assert e[0].rejection_confirm_idx == 2
    assert e[0].away_qualified_idx is None

def test_roll_at_exact_second_approach_tick():
    # Approached (idx 1), rejected (idx 2), qualified away (idx 4).
    # At index 5, price reaches near boundary (p[5]=99 >= 99), BUT rolls[5] is True!
    p = [90, 99, 93, 93, 93, 99, 90]
    t = np.arange(len(p), dtype=np.int64) * 10_000_000_000
    rolls = [False, False, False, False, False, True, False]
    e = detect_revisit_episodes(t, p, np.ones(len(p)), 100, 110, 1,
                                RevisitSpec(min_away_seconds=20, rejection_excursion_ticks=6),
                                state_reset_flags=rolls)
    assert len(e) == 1
    assert e[0].terminal == 'CENSORED_CONTRACT_ROLL'
    assert e[0].terminal_idx == 5
    assert e[0].stage_at_censoring == 'AWAY_QUALIFIED'
    assert e[0].second_approach_idx is None

def test_roll_and_traversal_on_same_tick_prioritizes_roll():
    # Approached (idx 1), rejected (idx 2), qualified away (idx 4), second approach at index 5 (p=99).
    # At index 6, price jumps to 115 (which would traverse 110), BUT rolls[6] is True!
    # Roll MUST take strict precedence: CENSORED_CONTRACT_ROLL, NEVER TRAVERSED.
    p = [90, 99, 93, 93, 93, 99, 115]
    t = np.arange(len(p), dtype=np.int64) * 10_000_000_000
    rolls = [False, False, False, False, False, False, True]
    e = detect_revisit_episodes(t, p, np.ones(len(p)), 100, 110, 1,
                                RevisitSpec(min_away_seconds=20, rejection_excursion_ticks=6),
                                state_reset_flags=rolls)
    assert len(e) == 1
    assert e[0].terminal == 'CENSORED_CONTRACT_ROLL'
    assert e[0].terminal_idx == 6
    assert e[0].stage_at_censoring == 'SECOND_APPROACH'
    assert e[0].terminal != 'TRAVERSED'

def test_isolated_session_right_boundary_reason():
    # Single session array ends with episode active.
    # When right_boundary_reason='SESSION_END', must record CENSORED_SESSION_END, not CENSORED_DATA_EDGE.
    p = [90, 99, 93, 93, 93, 99, 99]
    t = np.arange(len(p), dtype=np.int64) * 10_000_000_000
    e = detect_revisit_episodes(t, p, np.ones(len(p)), 100, 110, 1,
                                RevisitSpec(min_away_seconds=20, rejection_excursion_ticks=6),
                                right_boundary_reason='SESSION_END')
    assert len(e) == 1
    assert e[0].terminal == 'CENSORED_SESSION_END'
    assert e[0].stage_at_censoring == 'SECOND_APPROACH'
