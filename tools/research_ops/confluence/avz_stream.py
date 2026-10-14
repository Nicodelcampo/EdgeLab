"""Stateful AVZP2 bar feed, exact pinned loop, prototype only (racimo_min=0).

No data reader/eligibility, market results, new NT8 parity or speedup certificate.
Caller must produce exact eligible NT8 TOTAL cells/availability. Keeps calibration,
partial W-bar block and OB watching between feeds; discards completed native
blocks/zones after immutable observations. Racimos stay in the separate adapter.
"""
from __future__ import annotations
import ast
from dataclasses import dataclass,replace
from types import MappingProxyType,SimpleNamespace
from functools import lru_cache
import inspect
import math
import numpy as np
from datetime import datetime,timezone
from zoneinfo import ZoneInfo

_CHICAGO=ZoneInfo("America/Chicago")
from .asof_intersections import Clock,ZoneKey
from .detector_capture import Capture,_module,PINS,NAMES
from .build_target_free_pilot import digest

@dataclass(frozen=True)
class BarFeed:
    bar: int
    end_ns: int
    session_id: int
    low_tick: int
    high_tick: int
    levels: np.ndarray
    volumes: np.ndarray
    consumed_tick_index: int
    available: Clock|None

@dataclass(frozen=True)
class Delta:
    records: tuple[Capture,...]
    blocks: tuple
    unavailable_events: int

class _Sink:
    def __init__(self,append):self.append=append

@lru_cache(maxsize=1)
def _stream_code():
    mod=_module('AVZP2');fn=ast.parse(inspect.getsource(mod.run)).body[0]
    loop=next(n for n in fn.body if isinstance(n,ast.For))
    counts={'birth':0,'classify':0,'immediate':0,'block':0}
    class Transform(ast.NodeTransformer):
        def visit_Subscript(self,n):
            n=self.generic_visit(n)
            mapping={'lo_t':'low_tick','hi_t':'high_tick','bucket':'bucket'}
            if isinstance(n.value,ast.Name) and n.value.id in mapping:return ast.parse('feed.'+mapping[n.value.id],mode='eval').body
            if isinstance(n.value,ast.Attribute) and isinstance(n.value.value,ast.Name) and n.value.value.id=='bars' and n.value.attr=='end_ns':return ast.parse('feed.end_ns',mode='eval').body
            return n
        def visit_Assign(self,n):
            names=[t.id for t in n.targets if isinstance(t,ast.Name)]
            if any(isinstance(t,ast.Tuple) and [getattr(x,'id',None) for x in t.elts]==['t','v'] for t in n.targets):n.value=ast.parse('(feed.levels,feed.volumes)',mode='eval').body
            n=self.generic_visit(n)
            if any(isinstance(t,ast.Subscript) and isinstance(t.value,ast.Name) and t.value.id=='z' and isinstance(t.slice,ast.Constant) and t.slice.value=='decided_bar' for t in n.targets):
                counts['classify']+=1;return [n,*ast.parse("_classify(z,b)").body]
            return n
        def visit_If(self,n):
            if ast.unparse(n.test)=='b == 0 or session_id[b] != session_id[b - 1]':n.test=ast.parse('sess_idx < 0 or feed.session_id != _last_session',mode='eval').body
            n=self.generic_visit(n)
            if ast.unparse(n.test)=="p['ob_bars'] > 0":n.orelse.extend(ast.parse('_classify(z,b)').body);counts['immediate']+=1
            return n
        def visit_Expr(self,n):
            n=self.generic_visit(n);c=n.value
            if isinstance(c,ast.Call) and isinstance(c.func,ast.Attribute) and isinstance(c.func.value,ast.Name) and c.func.attr=='append':
                if c.func.value.id=='zones':counts['birth']+=1
                elif c.func.value.id=='blocks':counts['block']+=1
            return n
    transform=Transform();body=[]
    ignored={'n','end','bucket','F_off','F_t','F_v','lo_t','hi_t'}
    for n in fn.body[:fn.body.index(loop)]:
        if isinstance(n,ast.Assign):
            ids={x.id for t in n.targets for x in ast.walk(t) if isinstance(x,ast.Name)}
            if ids&ignored:continue
            if ids=={'zones','blocks','watching','clusters'}:n.value=ast.parse('(_zones,_blocks,[],[])',mode='eval').body
        body.append(n)
    body.extend(ast.parse('_last_session=None').body)
    loop_body=[]
    for n in loop.body:
        transformed=transform.visit(n);loop_body.extend(transformed if isinstance(transformed,list) else [transformed])
    # Save session before the next feed, including the cnt<W continue path.
    loop_body.insert(1,ast.parse('_last_session=feed.session_id').body[0])
    # Budget checks after a completed block (partial blocks are size-bounded by
    # W/max cells per feed; roll pruning remains the unchanged native loop).
    loop_body.extend(ast.parse('_budget(hist,pending,watching)').body)
    before=ast.parse('feed=yield\nif feed is None: return\nb=feed.bar').body
    body.append(ast.While(test=ast.Constant(True),body=before+loop_body,orelse=[]))
    fn.name='stream';fn.args=ast.arguments(posonlyargs=[],args=[ast.arg('params')],kwonlyargs=[],kw_defaults=[],defaults=[]);fn.body=body
    if counts!={'birth':1,'classify':1,'immediate':1,'block':1}:raise ValueError('pinned AVZ stream hook census drift')
    tree=ast.Module(body=[fn],type_ignores=[]);ast.fix_missing_locations(tree)
    return compile(tree,'<pinned-avz-stream>','exec')


class AVZStream:
    def __init__(self,*,params,bar_spec,max_history_values=1000000,max_watching=100000,max_records_per_bar=100000,max_levels_per_bar=10000):
        mod=_module('AVZP2')
        if set(params)-set(mod.DEFAULTS):raise ValueError('unknown params')
        self.params=MappingProxyType({**mod.DEFAULTS,**params})
        if self.params['racimo_min']!=0:raise ValueError('stream prototype requires separate racimo adapter, native racimo_min=0')
        if self.params['window_bars']<1 or self.params['lookback_sessions']<1 or self.params['min_samples']<1:raise ValueError('native positive calibration/window required')
        if not isinstance(bar_spec,str) or bar_spec.count(':')!=1 or bar_spec.split(':')[0] not in ('tick','time') or int(bar_spec.split(':')[1])<1:raise ValueError('explicit bar spec')
        for n in (max_history_values,max_watching,max_records_per_bar,max_levels_per_bar):
            if type(n) is not int or n<1:raise ValueError('explicit positive stream limits')
        self.config=digest({'indicator':NAMES['AVZP2'],'bar_spec':bar_spec,'params':dict(self.params)});self.max_history=max_history_values;self.max_watching=max_watching;self.max_records=max_records_per_bar;self.max_levels=max_levels_per_bar
        self.identity={};self.ordinal=0;self.last=None;self.current=None;self.closed=False;self.poisoned=False;self.history_values=0;self.watching_count=0
        env=dict(mod.__dict__);env.update(_zones=_Sink(self._birth),_blocks=_Sink(self._block),_classify=self._classify,_budget=self._budget)
        exec(_stream_code(),env);self.generator=env['stream'](self.params);next(self.generator)
    def _capture(self,kind,z,b):
        if self.current.available is None:self.unavailable+=1;return
        if len(self.records)>=self.max_records:raise ValueError('bar capture budget exceeded')
        if kind=='BIRTH':zid=f'{b}:{self.ordinal}';self.ordinal+=1;self.identity[id(z)]=zid
        else:
            if id(z) not in self.identity:raise ValueError('classification without observed birth')
            zid=self.identity.pop(id(z))
        props=tuple((k,z[k].item() if isinstance(z[k],np.generic) else z[k]) for k in ('levels','score','thresh','samples','state','decided_bar'))
        if any(isinstance(v,float) and not math.isfinite(v) for _,v in props):raise ValueError('nonfinite capture property')
        self.records.append(Capture(kind,ZoneKey('AVZP2',self.config,PINS['AVZP2'],zid),self.current.available,self.current.consumed_tick_index,int(b),2*int(z['low_tick']),2*int(z['high_tick']),0,props))
    def _birth(self,z):self._capture('BIRTH',z,self.current.bar)
    def _classify(self,z,b):self._capture('CLASSIFY',z,b)
    def _block(self,x):self.blocks.append(x)
    def _budget(self,hist,pending,watching):
        self.history_values=sum(len(v) for v in hist.values())+sum(len(v) for v in pending.values());self.watching_count=len(watching)
        if self.history_values>self.max_history or len(watching)>self.max_watching:raise ValueError('stream state budget exceeded; no pruning beyond native rule')
    def push(self,feed):
        if self.closed or self.poisoned:raise ValueError('closed/poisoned stream; rebuild verified state')
        if not isinstance(feed,BarFeed) or any(type(getattr(feed,n)) is not int for n in ('bar','end_ns','session_id','low_tick','high_tick','consumed_tick_index')):raise ValueError('typed bar declaration')
        if feed.bar!=(self.last.bar+1 if self.last else 0) or feed.end_ns<=0 or feed.high_tick<feed.low_tick or feed.consumed_tick_index<0:raise ValueError('ordered complete bar declaration')
        if self.last and (feed.end_ns<self.last.end_ns or feed.session_id<self.last.session_id or feed.consumed_tick_index<=self.last.consumed_tick_index):raise ValueError('retrograde bar/member/session')
        if feed.available is not None and (not isinstance(feed.available,Clock) or feed.available.ns<feed.end_ns or (self.last and self.last.available and feed.available<=self.last.available)):raise ValueError('causal strict bar availability')
        t=np.asarray(feed.levels);v=np.asarray(feed.volumes)
        if t.ndim!=1 or v.ndim!=1 or len(t)!=len(v) or len(t)>self.max_levels or t.dtype.kind not in 'iu' or v.dtype.kind not in 'iuf' or not np.isfinite(v).all() or np.any(v<0):raise ValueError('bounded exact TOTAL cells')
        if len(t) and (np.any(t[1:]<=t[:-1]) or np.any(t<feed.low_tick) or np.any(t>feed.high_tick)):raise ValueError('sorted unique OHLC-clipped TOTAL cells')
        # Never keep a caller-owned mutable batch buffer in the W-bar state.
        feed=replace(feed,levels=t.copy(),volumes=v.copy())
        # Exact integer-second floor: float ns->seconds could round a record
        # 1 ns before a minute boundary into the next minute.
        local=datetime.fromtimestamp(feed.end_ns//1000000000,timezone.utc).astimezone(_CHICAGO)
        bucket=(local.hour*60+local.minute)//max(1,int(self.params['bucket_min']))
        self.current=feed;self.records=[];self.blocks=[];self.unavailable=0
        try:
            self.generator.send(SimpleNamespace(**feed.__dict__,bucket=bucket));self.last=feed
            if feed.available is None:self.close()
            return Delta(tuple(self.records),tuple(self.blocks),self.unavailable)
        except BaseException:self.poisoned=True;self.generator.close();raise
    def close(self):self.generator.close();self.closed=True
