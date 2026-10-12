"""Kaggle-only target-free pilot: 96 detectors + 32 aligned geometry triads.

No outcome/P&L, arrival labels, ranking or canonical Brain writes. Existing
exploratory scope, full native params/history. Private captures in temporary
SQLite; only aggregate engineering/density/geometry receipts are outputs.
"""
from __future__ import annotations
import argparse,bisect,hashlib,heapq,json,sqlite3,time
from collections import Counter
from datetime import datetime,timezone
from itertools import groupby
from functools import lru_cache
from pathlib import Path
import numpy as np
from .build_target_free_pilot import digest
from .detector_capture import Capture,PINS,NAMES
from .asof_intersections import Clock,ZoneKey
from .session_primitives import SessionPrimitives
from .kaggle_session_reader import iter_sessions
from .bt2_stream import BT2Stream
from .bt2a_stream import BT2AStream,TickChunk
from .avz_stream import AVZStream
from .geometry_replay import GeometryReplay

DAY=86400000000000
FAMILY={v:k for k,v in NAMES.items()}

def trade_date(ns):return _trade_date_hour(ns//3600000000000)

@lru_cache(maxsize=8192)
def _trade_date_hour(hour):
    from zoneinfo import ZoneInfo
    from datetime import timedelta
    d=datetime.fromtimestamp(hour*3600,timezone.utc).astimezone(ZoneInfo('America/Chicago'))
    return str(d.date()+timedelta(days=int(d.hour>=17)))

class PrivateStore:
    def __init__(self,path,configs,*,max_records=3000000,max_bytes=1610612736):
        self.db=sqlite3.connect(path);self.db.execute('pragma journal_mode=DELETE');self.db.execute('pragma temp_store=FILE')
        self.db.execute('create table caps(cfg integer,ns integer,seq integer,ord integer,payload text)')
        self.configs=configs;self.max_records=max_records;self.max_bytes=max_bytes;self.rows=0;self.pending=[];self.counts=[Counter() for _ in configs];self.target_counts=[Counter() for _ in configs];self.hashes=[hashlib.sha256() for _ in configs];self.unavailable=[0]*len(configs)
    def add(self,cfg,delta,target):
        self.unavailable[cfg]+=delta.unavailable_events
        for x in delta.records:
            if self.rows>=self.max_records:raise ValueError('private capture budget; no truncation')
            payload=json.dumps([x.kind,x.key.zone_id,x.consumed_tick_index,x.source_bar,x.lo2,x.hi2,x.side,x.properties,x.reason],separators=(',',':'))
            self.pending.append((cfg,x.clock.ns,x.clock.sequence,self.rows,payload));self.rows+=1
            self.hashes[cfg].update(f'{x.clock.ns}|{x.clock.sequence}|{payload}\n'.encode());self.counts[cfg][x.kind]+=1
            if trade_date(x.clock.ns)==target:self.target_counts[cfg][x.kind]+=1
        if len(self.pending)>=5000:self.flush()
    def flush(self):
        self.db.executemany('insert into caps values(?,?,?,?,?)',self.pending);self.pending=[];self.db.commit()
        size=self.db.execute('pragma page_count').fetchone()[0]*self.db.execute('pragma page_size').fetchone()[0]
        if size>self.max_bytes:raise ValueError('private storage budget; no truncation')
    def ready(self):self.flush();self.db.execute('create index cfg_clock on caps(cfg,ns,seq,ord)');self.db.commit();self.flush()
    def records(self,cfg):
        c=self.configs[cfg];family=FAMILY[c['indicator']]
        for ns,seq,_,p in self.db.execute('select ns,seq,ord,payload from caps where cfg=? order by ns,seq,ord',(cfg,)):
            kind,zid,idx,bar,lo,hi,side,props,reason=json.loads(p)
            yield Capture(kind,ZoneKey(family,c['config_sha256'],PINS[family],zid),Clock(ns,seq),idx,bar,lo,hi,side,tuple(tuple(x) for x in props),reason)

def run_pilot(path,roster,plan,private_root,*,deadline_seconds=6600):
    if plan['scope']!='EXISTING_EXPLORATORY_TARGET_FREE_DENSITY_GEOMETRY' or plan['outcomes'] or plan['holdout_access']:raise ValueError('fixed target-free exploratory plan')
    configs=roster['configs']
    if len(configs)!=96 or any(sum(c['indicator']==v for c in configs)!=32 for v in NAMES.values()):raise ValueError('fixed 96 config roster')
    start=time.monotonic();times=Counter();bounds=[];streams={};store=PrivateStore(Path(private_root)/'captures-private.sqlite',configs,max_records=plan['max_capture_records'],max_bytes=plan['max_private_bytes']);primitives=SessionPrimitives(max_ticks=plan['max_session_ticks']);target=plan['target_session']
    def guard():
        if time.monotonic()-start>deadline_seconds:raise TimeoutError('cooperative pilot deadline')
    for i,c in enumerate(configs):
        f=FAMILY[c['indicator']]
        streams[i]=BT2AStream(params=c['params'],tick_size=.25) if f=='BT2A' else (BT2Stream(params=c['params'],bar_spec=c['bar_spec'],tick_size=.25) if f=='BT2' else AVZStream(params=c['params'],bar_spec=c['bar_spec']))
        if streams[i].config!=c['config_sha256']:raise ValueError('stream config identity drift')
    reader=iter(iter_sessions(path,start_ns=plan['start_ns'],end_ns=plan['end_ns'],max_session_ticks=plan['max_session_ticks'],max_total_ticks=plan['max_total_ticks']))
    total=0;target_ticks=0;session_count=0
    while True:
        guard();at=time.monotonic()
        try:st=next(reader)
        except StopIteration:break
        times['reader_seconds']+=time.monotonic()-at;t=st.ticks;date=trade_date(int(t.ts_ns[0]));n=len(t)
        if date>target:raise ValueError('unexpected session beyond target')
        bounds.append((st.first_index,st.first_index+n,date));total+=n;target_ticks+=n if date==target else 0;session_count+=1
        at=time.monotonic();primitives.begin(st);times['classification_seconds']+=time.monotonic()-at
        for spec in sorted({c['bar_spec'] for c in configs if c['bar_spec']}):
            guard();at=time.monotonic();bt,av=primitives.build(spec);times['primitives_seconds']+=time.monotonic()-at
            for i,c in enumerate(configs):
                if c['bar_spec']!=spec:continue
                feeds=bt if FAMILY[c['indicator']]=='BT2' else av;at=time.monotonic()
                for k,feed in enumerate(feeds):
                    if k%2000==0:guard()
                    store.add(i,streams[i].push(feed),target)
                times[FAMILY[c['indicator']]+'_seconds']+=time.monotonic()-at
            del bt,av
        # Input session IDs computed once, then shared among all BT2A configs.
        ids=np.full(n,st.session_id,dtype=np.int64)
        for i,c in enumerate(configs):
            if FAMILY[c['indicator']]!='BT2A':continue
            guard();at=time.monotonic()
            for k in range(0,n,100000):
                guard();z=min(k+100000,n);chunk=TickChunk(*(getattr(t,name)[k:z] for name in ('ts_ns','price_ticks','volume','bid_ticks','ask_ticks','sequence')),ids[k:z],st.first_index+k)
                store.add(i,streams[i].push(chunk),target)
            times['BT2A_seconds']+=time.monotonic()-at
        primitives.end();store.flush();print('SESSION_COMPLETE',date,n,store.rows,flush=True)
    for i,c in enumerate(configs):
        if FAMILY[c['indicator']]=='BT2A':store.add(i,streams[i].finish(),target)
        elif FAMILY[c['indicator']]=='AVZP2':streams[i].close()
    if target_ticks==0:raise ValueError('target session not observed; no empty-success claim')
    store.ready();starts=[b[0] for b in bounds]
    def origin(x):
        pos=bisect.bisect_right(starts,x.consumed_tick_index)-1
        if pos<0 or x.consumed_tick_index>=bounds[pos][1]:raise ValueError('capture consumption outside supplied scope')
        return bounds[pos][2]
    families={f:[i for i,c in enumerate(configs) if FAMILY[c['indicator']]==f] for f in NAMES}
    params=roster['racimo_configs']
    triads=[];at=time.monotonic()
    for rank in range(32):
        guard();indices=[families[f][rank] for f in ('AVZP2','BT2','BT2A')]
        actor=GeometryReplay(contract=plan['contract'],tape_sha256=plan['pin']['sha256'],racimo_params=params,max_episodes=50000,max_known_zones=300000)
        counts=Counter();excluded=0;processed=0
        merged=heapq.merge(*(store.records(i) for i in indices),key=lambda x:x.clock)
        for c,group in groupby(merged,key=lambda x:x.clock):
            if processed%2000==0:guard()
            date=trade_date(c.ns)
            if actor.session!=date:actor.begin_session(date)
            ev,ex=actor.apply(c,tuple(group),origin_date=origin);processed+=1
            if date==target:
                excluded+=ex
                for e in ev:
                    signature='+'.join(sorted(s.key.family for s in e.episode.components))
                    counts[e.action+':'+signature]+=1
        triads.append({'aligned_triad_index':rank,'config_sha256':[configs[i]['config_sha256'] for i in indices],'target_geometry_counts':dict(counts),'scope_excluded_target_records':excluded,'capture_clocks_processed':processed})
        print('GEOMETRY_TRIAD_COMPLETE',rank,flush=True)
    times['geometry_seconds']=time.monotonic()-at
    result={'schema':'mnq_confluence_market_engineering_pilot_v1','status':'TARGET_FREE_MARKET_PILOT_COMPLETE_NOT_VALIDATED_EDGE','contract':plan['contract'],'source_pin':plan['pin'],'plan_sha256':digest(plan),'roster_sha256':digest(roster),'target_session':target,'scope':'EXPLORATORY_SELECTED_TARGET_WITH_EXISTING_WARMUP_WINDOW','sessions_processed':session_count,'ticks_processed':total,'target_ticks':target_ticks,'configs_completed':96,'aligned_triads_completed':32,'full_cartesian_coverage':False,'stage_seconds':dict(times),'wall_seconds':time.monotonic()-start,'config_counts':[{'config_sha256':c['config_sha256'],'indicator':c['indicator'],'bar_spec':c['bar_spec'],'all_capture_counts':dict(store.counts[i]),'target_capture_counts':dict(store.target_counts[i]),'unobservable_eof_events':store.unavailable[i],'ordered_private_capture_sha256':store.hashes[i].hexdigest()} for i,c in enumerate(configs)],'geometry_triads':triads,'arrival_labels_evaluated':False,'occupancy_nulls_evaluated':False,'outcomes_evaluated':False,'pnl_computed':False,'holdout_opened':False,'source_quality_certified':False,'indicator_parity_percent_measured':None,'raw_ticks_or_events_exported':False,'selection_by_outcomes':False,'canonical_brain_written':False,'inference_or_edge_claim':False}
    store.db.close();return result

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--root',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();plan=json.loads((a.root/'docs/research/ops/MNQ_CONFLUENCE_MARKET_PILOT_PLAN.json').read_bytes());roster=json.loads((a.root/'docs/research/ops/MNQ_CONFLUENCE_TARGET_FREE_PILOT_ROSTER.json').read_bytes())
    # Market entrypoint cannot execute in the assistant computer sandbox.
    if not Path('/kaggle/working').is_dir():raise RuntimeError('KAGGLE_ONLY entrypoint')
    result=run_pilot(a.source,roster,plan,a.root,deadline_seconds=plan['deadline_seconds']);a.out.write_text(json.dumps(result,indent=2)+'\n');print(result['status'],flush=True)
if __name__=='__main__':main()
