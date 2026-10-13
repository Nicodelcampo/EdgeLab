"""Native streams advanced to a requested observed prefix; no session event store.

Bar primitives remain bounded/shared by spec. Immutable mutation batches are
applied and released immediately. All native history and final residual work
survive boundaries exactly; the untouched rest of a session is drained after
its final common anchor, not mistaken for exposure at earlier anchors.
"""
from collections import Counter
from datetime import datetime
import time
import numpy as np
from .cross_family_scene import CrossFamilyScene
from .cross_family_context import FAMILY
from .bt2a_stream import TickChunk

class StreamingScene(CrossFamilyScene):
    def __init__(self,roster,plan):
        super().__init__(roster,plan,semantic_capture_only=True);self.open_session=None
    def session(self,st,date,*,retain):
        if self.open_session is not None:raise ValueError('drain current native session before next')
        self.guard();self.ticks+=len(st.ticks)
        if self.ticks>self.plan['max_total_ticks']:raise ValueError('crossfamily total ticks')
        self.progress=dict(substage='CLASSIFY',profile_index=None,capture_records_retained=0,capture_records_by_kind={})
        f=time.monotonic();self.primitives.begin(st);self.times['classify']+=time.monotonic()-f;feeds={}
        for spec in self.plan['bar_specs']:
            self.progress.update(substage='BUILD_PRIMITIVES',profile_index=None);f=time.monotonic();feeds[spec]=self.primitives.build(spec);self.times['primitives']+=time.monotonic()-f
        cursor=SessionCursor(self,st,date,feeds);self.open_session=cursor
        if not retain:cursor.finish()
        return cursor,cursor.diag

class SessionCursor:
    def __init__(self,scene,st,date,feeds):
        self.scene=scene;self.st=st;self.feeds=feeds;self.positions=[0]*9;self.tick_positions=[0]*9;self.closed=False;self.last=None;self.counts=[Counter() for _ in range(9)];self.mutations=0;self.peak=0;self.tail_batches=0
        self.ids=np.full(len(st.ticks),st.session_id,dtype=np.int64)
        end=int(datetime.fromisoformat(date+'T22:00:00+00:00').timestamp())*10**9;self.start=end-86400*10**9;self.end=end
        self.diag={'trade_date':date,'ticks':len(st.ticks),'capture_records_retained':0,'config_counts':[], 'whole_session_event_store':False,'peak_pending_mutation_records':0,'total_causal_mutations_processed':0,'post_last_anchor_mutation_batches':0}
    def __len__(self):return 9
    def _records(self,k,delta,consumer):
        counter=self.counts[k];counter['unobservable_eof']+=delta.unavailable_events;groups=[];pending=0
        for r in delta.records:
            counter[r.kind]+=1
            if r.kind not in ('BIRTH','REMOVE'):counter['diagnostic_only_not_retained']+=1;continue
            if not self.start<=r.clock.ns<self.end:counter['outside_current_availability']+=1;continue
            primary=self.st.first_index<=r.consumed_tick_index<self.st.first_index+len(self.st.ticks)
            if not groups or groups[-1][0]!=r.clock:groups.append((r.clock,[]))
            groups[-1][1].append((r,primary));pending+=1
        self.peak=max(self.peak,pending);self.mutations+=pending
        if pending>self.scene.plan['max_pending_mutation_records']:raise ValueError('bounded pending mutation batch; no truncation')
        self.scene.progress.update(capture_records_retained=pending,capture_records_by_kind={x:sum(r.kind==x for _,rs in groups for r,_ in rs) for x in ('BIRTH','REMOVE')})
        for clock,records in groups:
            if consumer is None:self.tail_batches+=1
            else:consumer(k,clock,records)
        # No references to this batch survive here, except native state and
        # copied causal exposure snapshots in the consumer.
    def _advance_profile(self,k,target,consumer):
        scene=self.scene;c=scene.configs[k];f=FAMILY[c['indicator']];scene.progress.update(substage='NATIVE_'+f,profile_index=k)
        if f!='BT2A':
            feeds=self.feeds[c['bar_spec']][1 if f=='AVZP2' else 0];pos=self.positions[k]
            while pos<len(feeds):
                feed=feeds[pos]
                if target is not None and (feed.available is None or feed.available>target):break
                if pos%2000==0:scene.guard()
                began=time.monotonic();d=scene.streams[k].push(feed);scene.times[f]+=time.monotonic()-began;self._records(k,d,consumer);pos+=1
            self.positions[k]=pos
        else:
            t=self.st.ticks;pos=self.tick_positions[k];end=len(t) if target is None else int(np.searchsorted(t.sequence,target.sequence,side='right'))
            while pos<end:
                scene.guard();z=min(pos+100000,end);chunk=TickChunk(*(getattr(t,name)[pos:z] for name in ('ts_ns','price_ticks','volume','bid_ticks','ask_ticks','sequence')),self.ids[pos:z],self.st.first_index+pos)
                began=time.monotonic();d=scene.streams[k].push(chunk);scene.times[f]+=time.monotonic()-began;self._records(k,d,consumer);pos=z
            self.tick_positions[k]=pos
    def advance(self,clock,consumer):
        if self.closed or (self.last is not None and clock<=self.last):raise ValueError('strict requested streaming prefix')
        for k in range(9):self._advance_profile(k,clock,consumer)
        self.last=clock
    def finish(self):
        if self.closed:raise ValueError('session drained once')
        for k in range(9):self._advance_profile(k,None,None)
        self.scene.primitives.end();self.closed=True;self.scene.open_session=None;self.feeds.clear();self.ids=None
        self.diag.update(config_counts=[dict(c) for c in self.counts],capture_records_retained=0,peak_pending_mutation_records=self.peak,total_causal_mutations_processed=self.mutations,post_last_anchor_mutation_batches=self.tail_batches)
        self.scene.progress.update(substage='DONE',profile_index=None)
        return self.diag
