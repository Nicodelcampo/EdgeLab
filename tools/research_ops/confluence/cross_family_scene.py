"""Nine native streams, two shared bar specs, one chunk per source/session.

No Cartesian zone graph, outcome selection, detector reset or history pruning.
Immutable ordered Capture records only; BT2A residual observations from prior
session remain nonprimary. Config clocks/removal semantics retained exactly.
"""
from collections import Counter,defaultdict
from datetime import datetime
import time
import numpy as np
from .avz_stream import AVZStream
from .bt2_stream import BT2Stream
from .bt2a_stream import BT2AStream,TickChunk
from .session_primitives import SessionPrimitives
from .cross_family_context import FAMILY

class CrossFamilyScene:
    def __init__(self,roster,plan,*,semantic_capture_only=False):
        if type(semantic_capture_only) is not bool:raise ValueError('explicit semantic capture policy')
        self.semantic_capture_only=semantic_capture_only
        self.configs=roster['configs'];self.plan=plan;self.started=time.monotonic();self.ticks=0
        self.primitives=SessionPrimitives(max_ticks=plan['max_session_ticks'],max_cells=plan['max_footprint_cells'])
        self.streams=[];self.times=Counter();self.progress={}
        self.footprint_cache=None
        if plan.get('shared_bt2a_footprints') is True:
            from .bt2a_footprint_cache import BucketFootprintCache
            self.footprint_cache=BucketFootprintCache()
        tick_size=plan.get('tick_size',.25)
        for c in self.configs:
            f=FAMILY[c['indicator']]
            stream=AVZStream(params=c['params'],bar_spec=c['bar_spec']) if f=='AVZP2' else BT2Stream(params=c['params'],bar_spec=c['bar_spec'],tick_size=tick_size) if f=='BT2' else BT2AStream(params=c['params'],tick_size=tick_size,footprint_cache=self.footprint_cache)
            if stream.config!=c['config_sha256']:raise ValueError('nine native profile hashes')
            self.streams.append(stream)
    def guard(self):
        if time.monotonic()-self.started>self.plan['wall_seconds']:raise TimeoutError('crossfamily native wall')
    def session(self,st,date,*,retain):
        self.progress=dict(substage='READ_SESSION',profile_index=None,capture_records_retained=0,capture_records_by_kind={});self.guard();self.ticks+=len(st.ticks)
        if self.ticks>self.plan['max_total_ticks']:raise ValueError('crossfamily total ticks')
        end=int(datetime.fromisoformat(date+'T22:00:00+00:00').timestamp())*10**9;start=end-86400*10**9
        records=[[] for _ in self.configs];counts=[Counter() for _ in self.configs];stored=0
        def capture(k,delta):
            nonlocal stored
            counts[k]['unobservable_eof']+=delta.unavailable_events
            for r in delta.records:
                counts[k][r.kind]+=1
                if not retain:continue
                if self.semantic_capture_only and r.kind not in ('BIRTH','REMOVE'):
                    counts[k]['diagnostic_only_not_retained']+=1;continue
                # Source range is immutable global row membership, not inferred from final object.
                primary=st.first_index<=r.consumed_tick_index<st.first_index+len(st.ticks)
                if not start<=r.clock.ns<end:counts[k]['outside_current_availability']+=1;continue
                records[k].append((r,primary));stored+=1
                self.progress['capture_records_retained']=stored
                kinds=self.progress['capture_records_by_kind'];kinds[r.kind]=kinds.get(r.kind,0)+1
                if stored>self.plan['max_session_capture_records']:self.progress.update(substage='CAPTURE',profile_index=k)
                if stored>self.plan['max_session_capture_records']:raise ValueError('nine config capture capacity no truncation')
        self.progress.update(substage='CLASSIFY');f=time.monotonic();self.primitives.begin(st);self.times['classify']+=time.monotonic()-f
        for spec in self.plan['bar_specs']:
            self.progress.update(substage='BUILD_PRIMITIVES',profile_index=None);f=time.monotonic();bt,av=self.primitives.build(spec);self.times['primitives']+=time.monotonic()-f
            for k,c in enumerate(self.configs):
                if c['bar_spec']!=spec:continue
                self.progress.update(substage='NATIVE_'+FAMILY[c['indicator']],profile_index=k);f=time.monotonic();feeds=av if FAMILY[c['indicator']]=='AVZP2' else bt
                for j,feed in enumerate(feeds):
                    if j%2000==0:self.guard()
                    capture(k,self.streams[k].push(feed))
                self.times[FAMILY[c['indicator']]]+=time.monotonic()-f
            del bt,av
        t=st.ticks;ids=np.full(len(t),st.session_id,dtype=np.int64)
        # Shared immutable chunk views, including ids, among BT2A configurations.
        for j in range(0,len(t),100000):
            self.guard();z=min(j+100000,len(t));chunk=TickChunk(*(getattr(t,name)[j:z] for name in ('ts_ns','price_ticks','volume','bid_ticks','ask_ticks','sequence')),ids[j:z],st.first_index+j)
            for k,c in enumerate(self.configs):
                if FAMILY[c['indicator']]!='BT2A':continue
                self.progress.update(substage='NATIVE_BT2A',profile_index=k);f=time.monotonic();capture(k,self.streams[k].push(chunk));self.times['BT2A']+=time.monotonic()-f
        self.progress.update(substage='GROUP_EVENTS',profile_index=None);self.primitives.end();events=[]
        for rs in records:
            # Preserve same-clock native event order; sorting is stable, no reordering of tape.
            rs.sort(key=lambda x:x[0].clock);groups=[]
            for r,primary in rs:
                if not groups or groups[-1][0]!=r.clock:groups.append((r.clock,[]))
                groups[-1][1].append((r,primary))
            events.append(groups)
        self.progress.update(substage='DONE')
        return events,{'trade_date':date,'ticks':len(t),'capture_records_retained':stored,'config_counts':[dict(c) for c in counts]}
    def finish(self):
        """Flush only true EOF; diagnostics cannot become retroactive features."""
        receipts=[]
        for c,stream in zip(self.configs,self.streams):
            if FAMILY[c['indicator']]=='BT2A':
                d=stream.finish()
                if d.records:raise ValueError('EOF residual cannot acquire an observed clock')
                receipts.append({'config_sha256':c['config_sha256'],'unobservable_eof':d.unavailable_events})
            elif FAMILY[c['indicator']]=='AVZP2':stream.close()
        return receipts
