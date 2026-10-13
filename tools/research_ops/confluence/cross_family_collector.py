"""Causal shared per-profile queries, 18 pairs assembled only at common anchors.

Market arrays never leave Kaggle. Mirrored bands use the observed availability
midquote, not a consumed bar close or a later/final native object.
"""
from collections import Counter
import numpy as np
from .asof_intersections import Clock
from .cross_family_context import ExposureIndex,pair_features
from .observed_print_index import ObservedPrintIndex

class CrossFamilyCollector:
    def __init__(self,st,date,events,roster,plan):
        self.t=st.ticks;self.events=events;self.plan=plan;self.cursor=[0]*len(events)
        self.anchor_ns=np.empty(plan['max_common_anchors_per_session'],dtype=np.int64)
        self.n=0;self.last=None;self.counts=[Counter() for _ in roster['pairs']]
        if len(events)!=len(roster['configs']):raise ValueError('nine aligned event streams')
        lookup={c['config_sha256']:k for k,c in enumerate(roster['configs'])}
        self.pairs=[(lookup[p['left_config_sha256']],lookup[p['right_config_sha256']]) for p in roster['pairs']]
        self.indexes=[[ExposureIndex(c,date,mirror=mirror,max_active=plan['max_active_context'],max_seen=plan['max_seen_context'],max_hits=plan['max_query_hits'],max_total_hits=plan['max_session_context_query_hits']) for c in roster['configs']] for mirror in (False,True)]
        self.prints=ObservedPrintIndex(self.t.price_ticks,max_ticks=plan['max_session_ticks'],max_queries=plan['max_session_print_queries'],max_level_queries=plan['max_session_print_level_queries'])
        self.buffer=np.empty((plan['max_common_anchors_per_session'],2,len(self.pairs),43),dtype=float)
    def __call__(self,row,i,barrier):
        t=self.t;c=Clock(row['timestamp_ns'],row['sequence'])
        if (self.last is not None and c<=self.last) or self.n>=len(self.buffer):raise ValueError('ordered bounded common anchors')
        j=int(np.searchsorted(t.ts_ns,c.ns-20*10**9,side='right'))
        if j>=i:raise ValueError('observable prior endpoint')
        pc=Clock(int(t.ts_ns[j]),int(t.sequence[j]))
        def apply(k,ec,records):
            if ec>c:raise ValueError('future streaming mutation cannot reach anchor')
            birth_i=int(np.searchsorted(t.sequence,ec.sequence))
            if birth_i>=len(t.sequence) or (int(t.ts_ns[birth_i]),int(t.sequence[birth_i]))!=(ec.ns,ec.sequence):raise ValueError('native availability must bind actual current tape record')
            for view in self.indexes:view[k].apply(ec,records,midpoint2=int(t.bid_ticks[birth_i])+int(t.ask_ticks[birth_i]))
            self.cursor[k]+=1
        if hasattr(self.events,'advance'):
            self.events.advance(c,apply)
        else:
            for k,groups in enumerate(self.events):
                pos=self.cursor[k]
                while pos<len(groups) and groups[pos][0]<=c:
                    ec,records=groups[pos];apply(k,ec,records);pos+=1
        kw=dict(midpoint2=int(t.bid_ticks[i])+int(t.ask_ticks[i]),prior_clock=pc,prior_midpoint2=int(t.bid_ticks[j])+int(t.ask_ticks[j]),prior_print2=2*int(t.price_ticks[j]),print2=2*int(t.price_ticks[i]),radius_ticks=barrier,tape=t,anchor_index=int(i),prior_index=j,prints=self.prints)
        for v,view in enumerate(self.indexes):
            cached=[idx.observe(c,**kw) for idx in view]
            for p,(a,b) in enumerate(self.pairs):
                vector,meta=pair_features(cached[a],cached[b],c,row);self.buffer[self.n,v,p]=vector
                if v==0:
                    self.counts[p]['anchors']+=1;self.counts[p]['both_present']+=int(meta['both_present']);self.counts[p]['inside_both']+=int(meta['inside_both']);self.counts[p]['relation:'+meta['relation']]+=1
                    for side,summary in (('AVZ',cached[a]),('BIGTRAP',cached[b])):
                        self.counts[p][side+':post_birth_observed_touch']+=int(summary['arrival'][2]>0)
                        self.counts[p][side+':first_observed_touch_recent_20s']+=int(summary['arrival'][3]>0)
                        self.counts[p][side+':observed_leave_return']+=int(summary['arrival'][4]>0)
                        self.counts[p][side+':observed_gapthrough_without_inside_print']+=int(summary['arrival'][5]>0)
                        origin=summary['arrival'][6];old=summary['arrival'][1];self.counts[p][side+':prior_20s_origin:'+('FROM_ABOVE' if origin<0 else 'FROM_BELOW' if origin>0 else 'ALREADY_INSIDE' if old else 'UNKNOWN')]+=1
        self.anchor_ns[self.n]=c.ns;self.n+=1;self.last=c
    def finish(self,n):
        if self.n!=n:raise ValueError('identical common anchor census across pairs and controls')
        z=self.buffer[:n]
        if not np.isfinite(z).all():raise ValueError('finite crossfamily context')
        meta={'common_anchors':n,'pair_counts':[dict(c) for c in self.counts], 'profile_query_hits':sum(idx.hits for view in self.indexes for idx in view),'print_queries':self.prints.queries,'print_level_queries':self.prints.level_queries,'applied_profile_batches':sum(self.cursor),'post_last_common_anchor_batches':self.events.tail_batches if hasattr(self.events,'advance') else sum(len(g)-p for g,p in zip(self.events,self.cursor)),'profile_mutation_counts':[[dict(idx.counts) for idx in view] for view in self.indexes],'cached_profile_views_per_anchor':sum(map(len,self.indexes)),'primary_pair_count':len(self.pairs),'arrival_scope':'NEAREST_CURRENT_EXPOSURE_ONLY_POST_BIRTH_OBSERVED_PRINTS_NOT_PHYSICAL_PATH','mirrored_null_scope':'SAME_TRIGGER_REFLECTION_NOT_ZONE_FREE_INDEPENDENT_CREATOR'}
        if meta['profile_query_hits']>self.plan['max_session_context_query_hits']:raise ValueError('whole session profile hit cap')
        return z,meta
