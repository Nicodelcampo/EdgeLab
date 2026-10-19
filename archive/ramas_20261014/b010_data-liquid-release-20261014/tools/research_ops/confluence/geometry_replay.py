"""Incremental geometry-only replay; no invented price/arrival observations.

Same scope/racimo semantics as declared replay. Inputs are immutable captures and
caller-bound source origin dates. Does not provide data-access authority.
"""
from itertools import groupby
import hashlib
from pathlib import Path
from .episodes import EpisodeStream
from .racimo_asof import RacimoTape,Creation
from . import racimo_asof
from .build_target_free_pilot import digest

class GeometryReplay:
    def __init__(self,*,contract,tape_sha256,racimo_params=(),max_episodes=100000,max_known_zones=1000000,max_records_per_clock=100000,count_only=False):
        self.contract=contract;self.tape_sha=tape_sha256;self.params=racimo_params;self.max_episodes=max_episodes;self.max_known=max_known_zones;self.max_records=max_records_per_clock
        if type(count_only) is not bool:raise ValueError('explicit geometry output mode')
        self.count_only=count_only
        self.racimos={};self.born_scope={};self.retired=set();self.session=None;self.last=None
        self.source_hash=hashlib.sha256(Path(racimo_asof.__file__).read_bytes()).hexdigest()
    def begin_session(self,session):
        if self.session is not None and session<=self.session:raise ValueError('strict session scopes')
        engine=EpisodeStream
        if self.count_only:
            from .geometry_counts import GeometryCountStream
            engine=GeometryCountStream
        self.episodes=engine(contract=self.contract,tape_sha256=self.tape_sha,trade_date=session,max_active=self.max_episodes,max_pairs=self.max_episodes,max_triples=self.max_episodes)
        self.session=session
    def apply(self,c,records,*,origin_date):
        if self.session is None:raise ValueError('declare session before capture')
        if self.last is not None and c<=self.last:raise ValueError('strict observed capture clock')
        if len(records)>self.max_records:raise ValueError('atomic capture budget')
        ups={};rem=set();excluded=0;births={}
        for x in records:
            if x.clock!=c:raise ValueError('single atomic clock')
            if x.kind=='BIRTH':
                if x.key in self.born_scope:raise ValueError('duplicate birth')
                if len(self.born_scope)>=self.max_known:raise ValueError('known zone budget exceeded')
                scope=origin_date(x);self.born_scope[x.key]=scope
                if x.key.family=='AVZP2':births.setdefault(x.key.config_sha256,[]).append(x)
                if scope!=self.session:excluded+=1;continue
                ups[x.key]=x.birth_snapshot()
            elif x.kind in ('REMOVE','TOUCH','CLASSIFY'):
                if x.key not in self.born_scope:raise ValueError('mutation without birth')
                if self.born_scope[x.key]!=self.session:excluded+=1;continue
                if x.kind=='REMOVE':
                    if x.key in ups:del ups[x.key]
                    else:rem.add(x.key)
            else:raise ValueError('unknown capture kind')
        for cfg,zs in births.items():
            for p in self.params:
                rid=digest({'avz_config':cfg,'racimo':p})
                if rid not in self.racimos:self.racimos[rid]=RacimoTape(params=p,config_sha256=rid,build_sha256=self.source_hash,max_zones=self.max_episodes)
                for _,group in groupby(zs,key=lambda x:x.source_bar):
                    cs=[Creation(x.key.zone_id,x.source_bar,x.lo2//2,x.hi2//2,origin_date(x),c) for x in group]
                    for o in self.racimos[rid].observe_batch(cs):
                        key=o.snapshot.key
                        if o.snapshot.revision==0:
                            if key in self.born_scope:raise ValueError('duplicate racimo birth')
                            if len(self.born_scope)>=self.max_known:raise ValueError('known zone budget exceeded')
                            self.born_scope[key]=self.session
                        if key not in self.born_scope:raise ValueError('racimo revision without birth')
                        if key in self.retired or o.spans_sessions or o.member_trade_dates!=(self.session,) or self.born_scope[key]!=self.session:
                            excluded+=1;self.retired.add(key);ups.pop(key,None)
                            if key in self.episodes.join.active:rem.add(key)
                            continue
                        ups[key]=o.snapshot
        ev=self.episodes.apply(c,upserts=tuple(ups.values()),removals=tuple(rem));self.last=c
        return ev,excluded
