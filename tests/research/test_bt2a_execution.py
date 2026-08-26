import numpy as np
from edgelab.research.bt2a_execution import scenarios,simulate

def stream(prices,sessions=None):
 n=len(prices); last=np.asarray(prices,dtype=np.int64); bid=last.copy(); ask=last+1
 return np.arange(n,dtype=np.int64)*1_000_000_000,np.arange(100,100+n,dtype=np.int64),last,bid,ask,np.asarray(sessions or ['A']*n)
def signal(row=100,ts=0,direction=1,target=3,stop=2,event='E',seconds=None):
 return {'event_id':event,'signal_ts_utc_ns':ts,'signal_source_row':row,'direction':direction,'target_ticks':target,'stop_ticks':stop,'time_stop_seconds':seconds}

def test_target_and_strict_next_fill():
 data=stream([100,100,105]); r=simulate([signal()],*data,cost=scenarios(0)['ideal'],tick_value_usd=10)
 t=r['trades'][0]; assert t['entry_source_row']==101 and t['exit_reason']=='target' and t['net_ticks']==3

def test_stop_first():
 data=stream([100,100,97]); r=simulate([signal()],*data,cost=scenarios(0)['ideal'],tick_value_usd=10)
 assert r['trades'][0]['exit_reason']=='stop'

def test_time_stop_and_session_close():
 data=stream([100,100,101,101]); r=simulate([signal(target=20,stop=20,seconds=1)],*data,cost=scenarios(0)['ideal'],tick_value_usd=10)
 assert r['trades'][0]['exit_reason']=='time_stop'
 data=stream([100,100,101,101],['A','A','A','B']); r=simulate([signal(target=20,stop=20)],*data,cost=scenarios(0)['ideal'],tick_value_usd=10)
 assert r['trades'][0]['exit_reason']=='session_close'

def test_single_position_rejects_overlap():
 data=stream([100,100,100,100,100]); signals=[signal(event='A',target=50,stop=50),signal(row=101,ts=1_000_000_000,event='B',target=50,stop=50)]
 r=simulate(signals,*data,cost=scenarios(0)['ideal'],tick_value_usd=10)
 assert any(x['reason']=='position_open' for x in r['rejected'])

def test_cost_identity_and_monotonic_scenarios():
 data=stream([100,100,110]); net=[]
 for name,cost in scenarios(2.5).items():
  r=simulate([signal()],*data,cost=cost,tick_value_usd=10); t=r['trades'][0]
  assert abs(t['net_ticks']-(t['gross_ticks']-t['spread_ticks']-t['slippage_ticks']))<1e-9
  assert abs(t['net_usd']-(t['net_ticks']*10-t['commission_usd']))<1e-9; net.append(t['net_usd'])
 assert net[0]>=net[1]>=net[2]>=net[3]
