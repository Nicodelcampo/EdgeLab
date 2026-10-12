"""Finite target-free engineering pilot. CLI accepts INVENTED tapes only.

No market reader, certificate producer or final scientific confluence atlas.
Thirty-two aligned triads profile the 96-configuration roster; this is NOT the
Cartesian cross-config study. Outputs contain aggregates/hashes, no zone events.
"""
from __future__ import annotations
import argparse
from collections import Counter
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import resource
import time
import numpy as np
from edgelab.bridge.ticks import TickSeries
from edgelab.bridge import bars as B
from .detector_capture import capture_run,_module,_validate_tape
from ._pinned_total_footprint import build_total_footprint_csr_nt8
from .build_target_free_pilot import digest
from .replay import replay_declared

FAMILIES={'avolzonepoi2':'AVZP2','bigtrap2':'BT2','bigtrap2absorption':'BT2A'}


def fingerprint(value):
    """Typed incremental digest of native structures, not a lossy JSON dump."""
    h=hashlib.sha256()
    def token(x):
        b=x.encode();h.update(str(len(b)).encode()+b':'+b)
    def visit(x):
        if isinstance(x,np.ndarray):
            if x.dtype.hasobject:raise ValueError('object array not hashable here')
            token('array:'+x.dtype.str+':'+str(x.shape));h.update(np.ascontiguousarray(x).tobytes());return
        if isinstance(x,np.generic):visit(x.item());return
        if isinstance(x,dict):
            token('dict:'+str(len(x)))
            for k in sorted(x):visit(k);visit(x[k])
        elif isinstance(x,(list,tuple)):
            token(type(x).__name__+':'+str(len(x)))
            for v in x:visit(v)
        elif x is None:token('none')
        elif isinstance(x,bool):token('bool:'+str(x))
        elif isinstance(x,int):token('int:'+str(x))
        elif isinstance(x,float):token('float:'+x.hex())
        elif isinstance(x,str):token('str:'+x)
        else:raise ValueError('unsupported native value type')
    visit(value);return h.hexdigest()


def validate_roster(roster):
    if roster.get('schema')!='mnq_confluence_target_free_pilot_roster_v1':raise ValueError('pilot roster schema')
    copy={k:v for k,v in roster.items() if k!='roster_sha256'}
    if digest(copy)!=roster.get('roster_sha256'):raise ValueError('roster hash mismatch')
    configs=roster.get('configs',[])
    if len(configs)!=96 or len({c['config_sha256'] for c in configs})!=96:raise ValueError('exact distinct 96-config roster required')
    if Counter(c['indicator'] for c in configs)!=Counter({k:32 for k in FAMILIES}):raise ValueError('32 configs per detector')
    for c in configs:
        if digest({k:c[k] for k in ('indicator','bar_spec','params')})!=c['config_sha256']:raise ValueError('config hash mismatch')
    return configs


class Prepared:
    """Lazy shared exact bars + separate aggressive/TOTAL footprints.

    Input-size ceiling is checked before entry. Cache remains process-private.
    There is no market source authority here; cache cannot certify its inputs.
    """
    def __init__(self,ticks,max_tick_count=100000):
        n=_validate_tape(ticks)
        if type(max_tick_count) is not int or max_tick_count<1 or n>max_tick_count:raise ValueError('input tick budget')
        self.ticks=ticks;self.bars={};self.aggressive={};self.total={};self.sessions={};self.counts=Counter();self.seconds=0.
    def get(self,family,spec):
        if family=='BT2A':
            if spec is not None:raise ValueError('BT2A native tape windows only')
            return {}
        if not isinstance(spec,str) or spec.count(':')!=1:raise ValueError('declared bar spec')
        kind,n=spec.split(':');n=int(n)
        if kind not in ('tick','time') or n<1 or n>10000:raise ValueError('bar specification bounds')
        began=time.perf_counter()
        if spec not in self.bars:
            self.bars[spec]=B.build_tick_bars(self.ticks,n) if kind=='tick' else B.build_time_bars(self.ticks,n)
            self.counts['bar_builds']+=1
        else:self.counts['bar_cache_hits']+=1
        bars=self.bars[spec]
        if family=='BT2':
            if spec not in self.aggressive:self.aggressive[spec]=B.build_footprints(self.ticks,bars);self.counts['aggressive_builds']+=1
            else:self.counts['aggressive_cache_hits']+=1
            out={'bars':bars,'footprints':self.aggressive[spec]}
        elif family=='AVZP2':
            if spec not in self.total:
                # Guard copied int64 linearized keys before constructing TOTAL.
                span=int(self.ticks.price_ticks.max())-int(self.ticks.price_ticks.min())+1
                if span<1 or len(bars)*span>np.iinfo(np.int64).max:raise ValueError('TOTAL footprint int64 key overflow')
                self.total[spec]=build_total_footprint_csr_nt8(self.ticks,bars)
                self.sessions[spec]=B.session_ids(bars.end_ns);self.counts['total_builds']+=1
            else:self.counts['total_cache_hits']+=1
            out={'bars':bars,'footprints':self.total[spec],'sessions':self.sessions[spec]}
        else:raise ValueError('unknown family')
        self.seconds+=time.perf_counter()-began
        return out


def synthetic_fixture(*,sessions=25,ticks_per_session=1200,seed=2026101104):
    if type(sessions) is not int or not 1<=sessions<=40 or type(ticks_per_session) is not int or not 5<=ticks_per_session<=2500:raise ValueError('bounded invented fixture')
    n=sessions*ticks_per_session;rng=np.random.default_rng(seed)
    # July dates are synthetic declarations, not real calendar approval. Keep
    # price range bounded but nontrivial; alternate quoted aggressor direction.
    px=20000+np.cumsum(rng.integers(-1,2,size=n,dtype=np.int64));v=rng.integers(1,101,size=n).astype(float)
    side=rng.integers(0,2,size=n,dtype=np.int64);bid=px-side;ask=bid+1
    base=np.datetime64('2026-07-01T14:00:00','ns').astype(np.int64)
    ts=base+np.repeat(np.arange(sessions,dtype=np.int64)*86400000000000,ticks_per_session)+np.tile(np.arange(ticks_per_session,dtype=np.int64)*100000000, sessions)
    ticks=TickSeries(ts,px,v,bid,ask,np.arange(n,dtype=np.int64),.25,instrument='SYN',contract='SYN',source='INVENTED_IN_MEMORY')
    dates=np.repeat(np.arange(sessions),ticks_per_session)
    days=[str(np.datetime64('2026-07-01')+np.timedelta64(int(s),'D')) for s in dates]
    return ticks,days


def run_synthetic_pilot(roster,*,sessions=25,ticks_per_session=1200,deadline_seconds=900,max_total_records=200000,max_episodes=10000,verify_native=True,progress=None):
    """No supplied tape argument: caller cannot smuggle market data into mode."""
    configs=validate_roster(roster)
    for v in (deadline_seconds,max_total_records,max_episodes):
        if type(v) is not int or v<1:raise ValueError('positive explicit budgets')
    start=time.perf_counter();ticks,days=synthetic_fixture(sessions=sessions,ticks_per_session=ticks_per_session)
    tape_sha=fingerprint({k:getattr(ticks,k) for k in ('ts_ns','price_ticks','volume','bid_ticks','ask_ticks','sequence')})
    prepared=Prepared(ticks);receipts={};rows=[];total=0
    def check():
        if time.perf_counter()-start>deadline_seconds:raise TimeoutError('pilot deadline exceeded')
    for c in configs:
        check();family=FAMILIES[c['indicator']];args=prepared.get(family,c['bar_spec']);began=time.perf_counter()
        native,r=capture_run(family,ticks,params=c['params'],max_records=max_total_records-total,**args)
        elapsed=time.perf_counter()-began;output_sha=fingerprint(native);reference_s=None
        if verify_native:
            check();m=_module(family);began=time.perf_counter()
            if family=='AVZP2':ref=m.run(args['bars'],args['footprints'],args['sessions'],c['params'])
            elif family=='BT2':ref=m.run(ticks,args['bars'],args['footprints'],c['params'])
            else:ref=m.run(ticks,params=c['params'])
            reference_s=time.perf_counter()-began
            if fingerprint(ref)!=output_sha:raise ValueError('hook/native exact output mismatch')
            del ref
        del native
        total+=len(r.records)
        if total>max_total_records:raise ValueError('total capture budget; no truncation')
        receipts[c['config_sha256']]=r
        counts=Counter(x.kind for x in r.records)
        rows.append({'config_sha256':c['config_sha256'],'family':family,'capture_seconds':elapsed,'native_reference_seconds':reference_s,'exact_native_output_verified':bool(verify_native),'native_output_sha256':output_sha,'capture_sha256':fingerprint([asdict(x) for x in r.records]),'record_counts':dict(counts),'unavailable_close_events':r.unavailable_time_events})
        if progress:progress('CONFIG_COMPLETE',len(rows))
    groups=[[c for c in configs if c['indicator']==name] for name in FAMILIES];triads=[]
    for idx in range(32):
        check();cs=[g[idx] for g in groups];rs=[receipts[c['config_sha256']] for c in cs];events=Counter();arrivals=Counter();excluded=0;stream_sha=hashlib.sha256();began=time.perf_counter()
        for j,frame in enumerate(replay_declared(ticks,rs,contract='SYN',tape_sha256=tape_sha,trade_dates=days,racimo_params=roster['racimo_configs'],window_ticks=256,max_episodes=max_episodes,max_known_zones=max_total_records)):
            if j%1024==0:check()
            excluded+=frame.scope_excluded_records
            for e in frame.episode_events:events[str(len(e.episode.components))+'_'+e.action]+=1
            for a in frame.arrivals:arrivals[a.kind]+=1
            if frame.episode_events or frame.arrivals:stream_sha.update(fingerprint(asdict(frame)).encode())
        triads.append({'configs':[c['config_sha256'] for c in cs],'replay_seconds':time.perf_counter()-began,'episode_event_counts':dict(events),'arrival_counts':dict(arrivals),'scope_excluded_records':excluded,'nonempty_frame_stream_sha256':stream_sha.hexdigest()})
        if progress:progress('TRIAD_COMPLETE',len(triads))
    check()
    return {'schema':'mnq_confluence_synthetic_pilot_receipt_v1','status':'SYNTHETIC_COMPLETE_NOT_MNQ_RESULTS','market_data_read':False,'holdout_opened':False,'outcomes_computed':False,'pnl_computed':False,'source_eligibility_certified':False,'synthetic_fixture':{'sessions':sessions,'ticks_per_session':ticks_per_session,'n_ticks':len(ticks),'seed':2026101104,'sha256':tape_sha},'roster_sha256':roster['roster_sha256'],'coverage':'96_DETECTORS_32_ALIGNED_TRIADS_NOT_CARTESIAN','configs':rows,'triads':triads,'prepared_counts':dict(prepared.counts),'prepared_seconds':prepared.seconds,'wall_seconds':time.perf_counter()-start,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'memory_measurement_scope':'LINUX_SINGLE_PROCESS_RUSAGE_NOT_CGROUP','budgets':{'deadline_seconds':deadline_seconds,'max_total_records':max_total_records,'max_episodes':max_episodes},'market_speedup_claimed':False}


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--roster',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--sessions',type=int,default=25);ap.add_argument('--ticks-per-session',type=int,default=1200);ap.add_argument('--deadline-seconds',type=int,default=900);a=ap.parse_args()
    if a.out.exists():raise ValueError('new receipt path required')
    r=run_synthetic_pilot(json.loads(a.roster.read_bytes()),sessions=a.sessions,ticks_per_session=a.ticks_per_session,deadline_seconds=a.deadline_seconds,progress=lambda k,n:print(k,n,flush=True))
    r['receipt_sha256']=digest(r);a.out.write_text(json.dumps(r,indent=2,allow_nan=False)+'\n');print(r['status'],flush=True)
if __name__=='__main__':main()
