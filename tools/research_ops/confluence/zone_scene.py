"""Native AVZ/racimo history -> immutable session-local context batches.

Native calibration and racimo membership survive sessions. Primary exposure
must be created/recognized in the current session; mixed-session revisions
remove the primary racimo permanently. CLASSIFY is counted, never backfilled.
No retained pair/triple graph, SQLite capture store, label, or output file.
"""
from collections import Counter
from datetime import datetime
import time
from .avz_stream import AVZStream
from .racimo_asof import RacimoTape, Creation
from .session_primitives import SessionPrimitives
from .detector_capture import PINS
from .build_target_free_pilot import digest

class ZoneScene:
    def __init__(self, plan):
        c=plan['avzp2_config'];self.plan=plan
        self.stream=AVZStream(params=c['params'],bar_spec=c['bar_spec'])
        if self.stream.config!=c['config_sha256']:raise ValueError('fixed dense AVZ identity')
        p=plan['racimo_params'];self.racimo=RacimoTape(params=p,config_sha256=digest(p),
                      build_sha256=PINS['AVZP2'],max_zones=plan['max_racimo_history'])
        self.primitives=SessionPrimitives(max_ticks=plan['max_session_ticks'],max_cells=plan['max_footprint_cells'])
        self.started=time.monotonic();self.total_ticks=0

    def session(self, st, trade_date, *, retain):
        p=self.plan;self.total_ticks+=len(st.ticks)
        if self.total_ticks>p['max_total_ticks']:raise ValueError('zone total tick budget')
        self.primitives.begin(st);bt,feeds=self.primitives.build(p['avzp2_config']['bar_spec']);del bt
        end=int(datetime.fromisoformat(trade_date+'T22:00:00+00:00').timestamp())*10**9;start=end-86400*10**9
        events={};eligible=set();retired=set();counts=Counter();births=0;blocks=0;event_count=0
        for feed in feeds:
            if time.monotonic()-self.started>p['wall_seconds']:raise TimeoutError('zone wall budget')
            delta=self.stream.push(feed);blocks+=len(delta.blocks);counts['unobservable_eof']+=delta.unavailable_events
            zs=[r for r in delta.records if r.kind=='BIRTH'];births+=len(zs)
            for r in delta.records:counts[r.kind]+=1
            # Keep original detector order for the pinned legacy racimo tie rule.
            creations=tuple(Creation(r.key.zone_id,r.source_bar,r.lo2//2,r.hi2//2,trade_date,r.clock) for r in zs)
            obs=self.racimo.observe_batch(creations) if creations else ()
            if not retain:continue
            for r in zs:
                if not start<=r.clock.ns<end:
                    counts['AVZ_availability_outside_primary_session']+=1;continue
                u,rem=events.setdefault(r.clock,([],[]));u.append(r.birth_snapshot());event_count+=1;counts['primary_AVZ_births']+=1
            for o in obs:
                s=o.snapshot;k=s.key
                valid=start<=s.available.ns<end and start<=s.recognized.ns<end and not o.spans_sessions and o.member_trade_dates==(trade_date,)
                if not valid:
                    counts['racimo_carry_or_mixed_excluded']+=1
                    if k in eligible:
                        events.setdefault(s.available,([],[]))[1].append(k);eligible.remove(k);retired.add(k);event_count+=1
                    continue
                if k in retired:counts['racimo_retired_no_resurrection']+=1;continue
                if k not in eligible:
                    if s.revision!=0:counts['racimo_preexisting_revision_excluded']+=1;continue
                    eligible.add(k)
                events.setdefault(s.available,([],[]))[0].append(s);event_count+=1;counts['primary_racimo_snapshots']+=1
            if event_count>p['max_session_context_events']:
                raise ValueError('session context event budget; no truncation')
        self.primitives.end()
        ordered=[(c,tuple(u),tuple(r)) for c,(u,r) in sorted(events.items())]
        return ordered,{'trade_date':trade_date,'ticks':len(st.ticks),'native_blocks':blocks,'native_births':births,
                        'native_history_values':self.stream.history_values,'racimo_history_zones':len(self.racimo.zones),
                        'capture_counts':dict(counts),'context_batches':len(ordered),'context_mutations':sum(len(u)+len(r) for _,u,r in ordered)}
