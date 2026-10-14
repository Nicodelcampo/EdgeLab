"""Bounded synthetic benchmark using the production NumPy/Pandas expressions.
Optional installed CPU research dependencies; never loads market files or executes
source scripts. No end-to-end acceleration claim, all validation included below.
"""
import hashlib,json,platform
from statistics import median
from time import perf_counter
from .context_memo import ContextIdentity,ContextMemo

def run_context_benchmark():
    import numpy as np
    import pandas as pd
    n=16384;calls=8192;repeats=3
    highs=np.asarray([1000+((i*7919)%2003)+(i%31) for i in range(n)],dtype=np.int64)
    lows=np.asarray([1000+((i*7919)%2003) for i in range(n)],dtype=np.int64)
    session_start=(np.arange(n)//4096)*4096
    # Synthetic nanoseconds spanning Chicago DST fall-back; these are NOT data.
    epoch=1793511000000000000
    def range_reader(b):
        past=np.arange(max(int(session_start[b]),b-256),b)
        return int(np.max(highs[past])-np.min(lows[past])) if len(past) else None
    def hour_reader(ts): return int(pd.Timestamp(int(ts),tz='UTC').tz_convert('America/Chicago').hour)
    def digest(x): return hashlib.sha256(json.dumps(x,separators=(',',':')).encode()).hexdigest()
    identity=ContextIdentity(digest([highs.tolist(),lows.tolist(),session_start.tolist()]),digest({'fixture':'SYNTHETIC_ONLY'}),digest({'semantics':'closed256/chicago exact ns'}))
    evidence=[]
    for name,keys in [('repeated',[(i//16,epoch+(i//16)*1000000000) for i in range(calls)]),('unique',[(i,epoch+i*1000000000) for i in range(calls)])]:
        time_sets={'baseline':[],'memo':[]};orders=[];output=None;stats=None
        # Warm imports/readers only. Fresh memo each timed run; never reuse output.
        range_reader(256);hour_reader(epoch)
        for repeat in range(repeats):
            order=('baseline','memo') if repeat%2==0 else ('memo','baseline');orders.append(list(order));results={}
            for method in order:
                t0=perf_counter()
                if method=='baseline': result=[(range_reader(b),hour_reader(t)) for b,t in keys]
                else:
                    memo=ContextMemo(identity,range_reader,hour_reader);result=[memo.context(b,t) for b,t in keys];stats=memo.stats()
                time_sets[method].append(perf_counter()-t0);results[method]=result
            if results['baseline']!=results['memo']: raise ValueError('production-expression parity failed')
            output=results['baseline']
        # Independent check: Python slicing plus datetime/ZoneInfo, no NumPy/Pandas.
        from datetime import datetime,timezone,timedelta
        from zoneinfo import ZoneInfo
        for index in (0,1,16,4095,4096,8191):
            b,t=keys[index];a=max(int(session_start[b]),b-256)
            expected_range=None if a==b else max(map(int,highs[a:b]))-min(map(int,lows[a:b]))
            utc=datetime(1970,1,1,tzinfo=timezone.utc)+timedelta(seconds=t//1000000000)
            expected_hour=utc.astimezone(ZoneInfo('America/Chicago')).hour
            if output[index]!=(expected_range,expected_hour): raise ValueError('independent context check failed')
        med={k:median(v) for k,v in time_sets.items()}
        evidence.append(dict(workload=name,calls=calls,unique_keys=len(set(keys)),input_sha256=digest(keys),output_sha256=digest(output),exact_parity=True,independent_check=True,timing_seconds=time_sets,median_ms={k:v*1000 for k,v in med.items()},order=orders,memo_stats=stats))
    return dict(status='PASS_SYNTHETIC_PRODUCTION_EXPRESSION_PARITY',workloads=evidence,python=platform.python_version(),numpy=np.__version__,pandas=pd.__version__,synthetic_fixture=True,market_data_read=False,active_runner_changed=False,campaign_speedup_established=False,limitations=['shared CPU with active MNQ','small fixed synthetic workloads, not representative measured signal distribution','cache can slow unique keys; not integrated with whole engine','no source or selection certification produced'])
