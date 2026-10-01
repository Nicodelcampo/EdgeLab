from pathlib import Path
import importlib.util,json
import numpy as np,pandas as pd
import census as c
p=c.p
# 1000 bars before and across declaredRTH windows; synthetic only.
tf=5;p.STEP=tf*60*c.NS;start=pd.Timestamp('2025-10-04T10:00:00Z').value//p.STEP;k=np.arange(start,start+1300);price=10000+np.arange(len(k))*2
b=p.indicators(pd.DataFrame({'bucket':k,'o':price,'h':price+3,'l':price-3,'c':price,'n':20}));days={'20251007'};tests=[]
for H in [120,60,30]:
 for thr in [1.,.5]:
  raw,ev=c.events(b,'RTY','SYNTH',days,tf,thr,H);assert len(raw)>0 and len(ev)>0;assert len(raw)>=len(ev)
  for i in [1150,1200,1250]:
   bb=p.indicators(b.iloc[:i+1][['bucket','o','h','l','c','n']].copy());_,pev=c.events(bb,'RTY','SYNTH',days,tf,thr,H);assert pev==[e for e in ev if e['signal_ns']<=int(b.close_ns.iloc[i])]
  tests.append({'H':H,'K':thr,'prefix_nonoverlap':True})
r1,_=c.events(b,'RTY','SYNTH',days,tf,1,120);r05,_=c.events(b,'RTY','SYNTH',days,tf,.5,120);assert {x['signal_ns'] for x in r1}<={x['signal_ns'] for x in r05};tests.append({'nested_raw':True})
# Replay only entryquotes: tie250ms is rejected, >250ms chosen; outside30sec missing.
class Batch:
 def __init__(self,t):self.t=t
 def to_pandas(self):return self.t
s=1_000_000_000;t=pd.DataFrame({'ts_utc_ns':[s+250000000,s+250000001,s+31*c.NS],'bid_ticks':[10,10,10],'ask_ticks':[11,11,11]})
old=p.scan;p.scan=lambda *a:[Batch(t.iloc[:0]),Batch(t),Batch(t.iloc[:0])];good,bad=c.quote_entries([{'signal_ns':s}],None);assert good[s]['lag_s']>.25 and good[s]['lag_s']<.251
p.scan=lambda *a:[Batch(t.iloc[2:])];good,bad=c.quote_entries([{'signal_ns':s}],None);assert not good;p.scan=old;tests.append({'quote_boundary_strict':True})
# Exact frozenlegacy event equivalence on synthetic bars, no evaluator invoked.
sp=importlib.util.spec_from_file_location('legacy','/data/analysis/cross_momentum_20261001/entry.py');legacy=importlib.util.module_from_spec(sp);sp.loader.exec_module(legacy);legacy.STEP=p.STEP;legacy.MODE='MOM';evold=legacy.make_events(b,'RTY','SYNTH',days,5);_,ev=c.events(b,'RTY','SYNTH',days,5,1.,120);assert [(x['signal_ns'],x['direction'],x['U']) for x in evold]==[(x['signal_ns'],x['direction'],x['U']) for x in ev];tests.append({'synthetic_legacy_parity':True})
Path(__file__).with_name('selftests.json').write_text(json.dumps({'checks':tests,'all_pass':True,'synthetic_only':True,'no_outcomes':True},indent=2));print('PASS',len(tests),'testgroups; 18prefixchecks; nooutcomes')
