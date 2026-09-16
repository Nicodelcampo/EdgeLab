import numpy as np
from edgelab.research.void_revisit_episodes import *

def test_reject_away_reapproach_and_traverse():
    p=[90,98,99,98,94,93,93,94,98,99,100,103,106,110]
    t=np.arange(len(p),dtype=np.int64)*10_000_000_000
    e=detect_revisit_episodes(t,p,np.ones(len(p)),100,110,1,RevisitSpec(approach_ticks=1,rejection_excursion_ticks=6,min_away_seconds=10,max_episode_seconds=300))
    assert len(e)==1 and e[0].terminal=='TRAVERSED'
    assert e[0].first_approach_idx<e[0].rejection_confirm_idx<e[0].second_approach_idx<e[0].terminal_idx

def test_second_rejection_is_distinct_terminal():
    p=[90,99,98,94,93,93,98,99,98,94,93]
    t=np.arange(len(p),dtype=np.int64)*10_000_000_000
    e=detect_revisit_episodes(t,p,np.ones(len(p)),100,110,1,RevisitSpec(min_away_seconds=10,max_episode_seconds=300))
    assert len(e)==1 and e[0].terminal=='REJECTED_AGAIN'

def test_away_time_and_volume_are_required():
    p=[90,99,93,99,100,110]; t=np.arange(len(p),dtype=np.int64)*1_000_000_000
    assert detect_revisit_episodes(t,p,np.ones(len(p)),100,110,1,RevisitSpec(min_away_seconds=60,min_away_volume=10,max_episode_seconds=100))==[]

def test_mirrored_short_side():
    p=[120,111,112,116,117,117,112,111,110,105,100]
    t=np.arange(len(p),dtype=np.int64)*10_000_000_000
    e=detect_revisit_episodes(t,p,np.ones(len(p)),100,110,-1,RevisitSpec(min_away_seconds=10,max_episode_seconds=300))
    assert len(e)==1 and e[0].terminal=='TRAVERSED'
