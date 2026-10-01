import json
import numpy as np
import pandas as pd
import pyarrow as pa
from run_economic import match_controls,candidates,net_fields,add_execution_fields,NS
from economic import replay,costs

def signal(i='s',ns=0,U=10,day='20251007',direction=1):
    return dict(id=i,asset='RTY',contract='RTY12',day=day,tf=1,signal_ns=ns,U=U,direction=direction,separated=True)
def batch(ts,bid,ask):
    return pa.RecordBatch.from_pydict(dict(ts_utc_ns=pa.array(ts,type=pa.int64()),bid_ticks=pa.array(bid,type=pa.float64()),ask_ticks=pa.array(ask,type=pa.float64())))
def test_matching_boundaries_and_no_returns():
    s=signal()
    pool=[signal(str(i),ns=i*NS,U=u,day=d,direction=side) for i,u,d,side in [
        (1860,10,'20251007',1),(1861,5,'20251007',1),(3600,20,'20251007',1),
        (3601,10,'20251007',1),(1900,4.99,'20251007',1),(2000,10,'20251008',1),(2100,10,'20251007',-1)]]
    mp,c=match_controls([s],pool);assert set(mp['s'])=={'1861','3600'}
    for z in pool:z['future_return']=10**10
    assert mp==match_controls([s],pool)[0]
def test_matching_deterministic_max5():
    s=signal();pool=[signal(str(i),i*NS) for i in range(1900,1950)]
    a=match_controls([s],pool)[0];assert a==match_controls([s],list(reversed(pool)))[0] and len(a['s'])==5
def test_matching_never_cross_contract_day_in_provided_pool():
    s=signal();other=dict(signal('o',2000*NS),contract='RTY03')
    assert not match_controls([s],[signal('c',1900*NS,day='20251008'),other])[1]
def test_latency_and_halfhour_exact_execution():
    s=signal();add_execution_fields([s])
    replay([s],[batch([250000000,250000001,1800250000001],[100,100,104],[101,101,105])])
    assert s['status']=='COMPLETE' and s['entry_ns']==250000001 and s['gross_ticks']==3
def test_short_quote_side_and_fees():
    s=signal(direction=-1);add_execution_fields([s])
    replay([s],[batch([NS,1801*NS],[100,96],[101,97])])
    m={'costs':{'RTY':{'tick_value_usd':5,'commission_side_usd':2.25}}}
    net_fields([s],m);assert abs(s['net_base_ticks']-.1)<1e-9 and abs(s['net_base_usd']-.5)<1e-9
def test_censored_exit_not_zero_trade():
    s=signal();add_execution_fields([s]);replay([s],[batch([NS],[100],[101])])
    assert s['status']=='UNKNOWN_EXIT_EOF' and 'gross_ticks' not in s
def test_no_entry():
    s=signal();add_execution_fields([s]);replay([s],[batch([31*NS],[100],[101])])
    assert s['status']=='NO_ENTRY_QUOTE_WITHIN30S'
def test_filter_no_rescheduling():
    rows=[dict(signal(str(i),i*2000*NS),separated=bool(i%2)) for i in range(5)]
    assert [s['signal_ns'] for s in rows if s['separated']]==[2000*NS,6000*NS]