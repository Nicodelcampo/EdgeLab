"""Connect immutable detector captures -> racimos -> episodes -> arrivals.

DECLARED ARRAY REPLAY, not a market reader, source certificate, split firewall
or approved Kaggle runner. The caller must bind immutable eligible sources and
all date/split policies before supplying arrays. Each Frame is PRIVATE if its
inputs are market-derived. Export only separately reviewed aggregate receipts.
"""
from __future__ import annotations
from dataclasses import dataclass
from itertools import groupby
import heapq
import hashlib
from pathlib import Path
from .asof_intersections import Clock
from .detector_capture import _validate_tape,PINS
from .episodes import EpisodeStream
from .arrival import ArrivalObserver,Tick
from .racimo_asof import RacimoTape,Creation
from . import racimo_asof
from .build_target_free_pilot import digest

@dataclass(frozen=True)
class Frame:
    trade_date: str
    clock: Clock
    episode_events: tuple
    arrivals: tuple
    scope_excluded_records: int


def replay_declared(ticks,receipts,*,contract,tape_sha256,trade_dates,racimo_params=(),window_ticks=256,max_records_per_clock=100000,max_episodes=100000,max_known_zones=1000000):
    """Yield private Frames; no future labels, P&L or data-file access.

    Sessions are caller declarations, never a self-generated permission. First
    touch/revisit comes from actual point observations. Closed-session exposure
    is dropped explicitly while racimo detector history stays causal across
    sessions. No silent carry into primary scope or imputed absence.
    """
    n=_validate_tape(ticks)
    if len(trade_dates)!=n or any(trade_dates[i]<trade_dates[i-1] for i in range(1,n)):raise ValueError('ordered aligned session declarations')
    if type(max_records_per_clock) is not int or max_records_per_clock<1:raise ValueError('batch budget required')
    if type(max_known_zones) is not int or max_known_zones<1:raise ValueError('known zone budget required')
    streams=[]
    for r in receipts:
        if r.source_sha256 not in PINS.values():raise ValueError('unrecognized capture source')
        if any(x.key.build_sha256!=r.source_sha256 or x.key.config_sha256!=r.parameter_sha256 for x in r.records):raise ValueError('receipt/key build or config mismatch')
        if any(r.records[i].clock<r.records[i-1].clock for i in range(1,len(r.records))):raise ValueError('capture records not ordered')
        streams.append(iter(r.records))
    # Merge receipts without a global configuration x tick cube.
    merged=heapq.merge(*streams,key=lambda x:x.clock);groups=iter(groupby(merged,key=lambda x:x.clock));pending=next(groups,None)
    racimos={};born_scope={};retired_primary=set();active_scope=None;source_hash=hashlib.sha256(Path(racimo_asof.__file__).read_bytes()).hexdigest()
    for i in range(n):
        c=Clock(int(ticks.ts_ns[i]),int(ticks.sequence[i]));session=trade_dates[i]
        if session!=active_scope:
            # Constructors reject canonical reserved trade dates. They do not
            # enforce other external reserved folds or certify CME calendars.
            episodes=EpisodeStream(contract=contract,tape_sha256=tape_sha256,trade_date=session,max_active=max_episodes,max_pairs=max_episodes,max_triples=max_episodes)
            arrivals=ArrivalObserver(trade_date=session,window_ticks=window_ticks,max_episodes=max_episodes,max_candidates=max_episodes)
            active_scope=session
        records=[]
        if pending and pending[0]<c:raise ValueError('capture availability missing from supplied tape')
        if pending and pending[0]==c:
            for x in pending[1]:
                if len(records)>=max_records_per_clock:raise ValueError('atomic capture batch overflow')
                if not 0<=x.consumed_tick_index<=i:raise ValueError('future consumed tick')
                if int(ticks.ts_ns[x.consumed_tick_index])>c.ns:raise ValueError('future consumed timestamp')
                records.append(x)
            pending=next(groups,None)
        ups={};rem=set();excluded=0;avz_births={}
        for x in records:
            if x.kind=='BIRTH':
                if x.key in born_scope:raise ValueError('duplicate birth across receipts')
                if len(born_scope)>=max_known_zones:raise ValueError('known zone budget exceeded; no silent pruning')
                born_scope[x.key]=trade_dates[x.consumed_tick_index]
                if x.key.family=='AVZP2':avz_births.setdefault(x.key.config_sha256,[]).append(x)
                if born_scope[x.key]!=session:excluded+=1;continue
                ups[x.key]=x.birth_snapshot()
            elif x.kind in ('REMOVE','TOUCH','CLASSIFY'):
                if x.key not in born_scope:raise ValueError('state mutation without captured birth')
                if born_scope[x.key]!=session:excluded+=1;continue
                if x.kind=='REMOVE':
                    if x.key in ups:del ups[x.key]
                    else:rem.add(x.key)
                # TOUCH/CLASSIFY stay in the immutable capture receipt. This
                # prototype does not feed final states or turn them into births.
            else:raise ValueError('unknown capture event')
        for cfg,births in avz_births.items():
            for p in racimo_params:
                rid=digest({'avz_config':cfg,'racimo':p})
                if rid not in racimos:racimos[rid]=RacimoTape(params=p,config_sha256=rid,build_sha256=source_hash,max_zones=max_episodes)
                # A detector may produce multiple zones per bar. Preserve
                # original birth order, never sort by price or zone ID.
                for _,zs in groupby(births,key=lambda x:x.source_bar):
                    creations=[Creation(x.key.zone_id,x.source_bar,x.lo2//2,x.hi2//2,trade_dates[x.consumed_tick_index],c) for x in zs]
                    obs=racimos[rid].observe_batch(creations)
                    for o in obs:
                        key=o.snapshot.key
                        if o.snapshot.revision==0:
                            if key in born_scope:raise ValueError('duplicate racimo birth')
                            if len(born_scope)>=max_known_zones:raise ValueError('known zone budget exceeded; no silent pruning')
                            born_scope[key]=session
                        if key not in born_scope:raise ValueError('racimo revision without birth')
                        if key in retired_primary or o.spans_sessions or o.member_trade_dates!=(session,) or born_scope[key]!=session:
                            excluded+=1
                            # Only changed observations need scope checks. End
                            # active primary exposure immediately, without an
                            # O(configurations x active zones) full-state scan.
                            retired_primary.add(key)
                            ups.pop(key,None)
                            if key in episodes.join.active:rem.add(key)
                            continue
                        ups[key]=o.snapshot
        ev=episodes.apply(c,upserts=tuple(ups.values()),removals=tuple(rem))
        # Explicit proxy for the smoke path: quote-classified side only. Unknown
        # interior prints remain unknown instead of tick-rule fabrication.
        px=int(ticks.price_ticks[i]);aq=int(ticks.ask_ticks[i]);bq=int(ticks.bid_ticks[i]);side=1 if px>=aq else (-1 if px<=bq else 0)
        anchors=arrivals.observe(Tick(c,2*px,float(ticks.volume[i]),side),ev)
        yield Frame(session,c,ev,anchors,excluded)
    if pending is not None:raise ValueError('unconsumed capture beyond supplied tape')
