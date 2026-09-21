import pytest
from edgelab.research.ym_bt2a_economic_search import *
from edgelab.research.ym_bt2a_retest_pilot import Tick

def ticks(*prices,start=101,session="S1"):return [Tick(start+i,i+1,price*2,session) for i,price in enumerate(prices)]
def entry(price=100,direction="long"):return Tick(100,0,price*2,"S1"),direction

def test_frozen_grid_sizes():
 assert len(entry_policy_grid_v2())==132; assert len(coarse_exit_grid_v1())==54; assert len(refinement_exit_grid_v1())==5760

def test_long_target_uses_frozen_limit_price():
 e,d=entry();o=simulate_trade(entry=e,future_ticks=ticks(102,106,109),direction=d,spec=ExitSpec("X",4,6,10),cost_ticks=2);assert (o.exit_reason,o.exit_price_half_ticks,o.gross_ticks,o.net_ticks)==("TARGET",212,6,4)
def test_short_target_is_symmetric():
 e,_=entry();o=simulate_trade(entry=e,future_ticks=ticks(98,94,90),direction="short",spec=ExitSpec("X",4,6,10),cost_ticks=2);assert (o.exit_reason,o.gross_ticks,o.net_ticks)==("TARGET",6,4)
def test_stop_gap_uses_observed_worse_price():
 e,d=entry();o=simulate_trade(entry=e,future_ticks=ticks(99,93),direction=d,spec=ExitSpec("X",4,20,10),cost_ticks=2);assert (o.exit_reason,o.gross_ticks,o.net_ticks)==("STOP",-7,-9)
def test_break_even_activates_and_locks_profit():
 e,d=entry();o=simulate_trade(entry=e,future_ticks=ticks(103,106,104,101),direction=d,spec=ExitSpec("X",8,20,10,6,1),cost_ticks=2);assert o.break_even_activated and o.exit_reason=="BREAK_EVEN";assert (o.gross_ticks,o.net_ticks)==(1,-1)
def test_time_exit_and_session_end_are_distinct():
 e,d=entry();spec=ExitSpec("X",20,20,2);assert simulate_trade(entry=e,future_ticks=ticks(101,102,103),direction=d,spec=spec,cost_ticks=0).exit_reason=="TIME_EXIT";assert simulate_trade(entry=e,future_ticks=ticks(101),direction=d,spec=spec,cost_ticks=0).exit_reason=="SESSION_END"
def test_same_identity_is_not_a_post_entry_fill():
 e,d=entry();o=simulate_trade(entry=e,future_ticks=[Tick(100,0,300,"S1")],direction=d,spec=ExitSpec("X",4,4,10),cost_ticks=0);assert o.state=="CENSORED" and o.exit_reason=="NO_POST_ENTRY_TICK"
def test_invalid_break_even_is_rejected():
 with pytest.raises(ValueError):validate_exit_spec(ExitSpec("X",4,4,10,4,4))
def test_summary():
 e,d=entry();spec=ExitSpec("X",4,4,10);out=[simulate_trade(entry=e,future_ticks=ticks(104),direction=d,spec=spec,cost_ticks=2),simulate_trade(entry=e,future_ticks=ticks(96),direction=d,spec=spec,cost_ticks=2)];s=summarize_net_ticks(out);assert s["trades"]==2 and s["mean"]==-2 and s["win_rate"]==.5
