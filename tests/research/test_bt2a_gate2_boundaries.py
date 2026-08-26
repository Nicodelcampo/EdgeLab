import numpy as np
from edgelab.research.bt2a_execution import scenarios,simulate
from edgelab.research.bt2a_gate2_first_passage import first_passage_scores,first_passage_scores_fast

def test_fast_first_passage_includes_horizon_endpoint():
    price=np.array([100,100,103]); ts=np.arange(3)*1_000_000_000; source=np.arange(3); sessions=np.array(['A']*3)
    fast=first_passage_scores_fast(price,ts,sessions,fill_indices=[0],directions=[1],barrier_ticks=3,tick_cap=2,clock_cap_seconds=None)
    slow=first_passage_scores(price,ts,source,sessions,fill_indices=[0],directions=[1],target_ticks=3,stop_ticks=3,tick_cap=2)
    assert fast.tolist()==slow.tolist()==[1]

def test_execution_exit_is_strictly_after_fill_row():
    price=np.array([100,105,105]); n=len(price)
    data=(np.arange(n)*1_000_000_000,np.arange(100,100+n),price,price,price+1,np.array(['A']*n))
    signal={'event_id':'E','signal_ts_utc_ns':0,'signal_source_row':100,'direction':1,'target_ticks':20,'stop_ticks':1}
    result=simulate([signal],*data,cost=scenarios(0)['ideal'],tick_value_usd=10)
    trade=result['trades'][0]
    assert trade['entry_source_row']==101
    assert trade['exit_source_row']==102
