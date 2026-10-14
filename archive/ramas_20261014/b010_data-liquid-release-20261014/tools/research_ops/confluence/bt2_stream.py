"""Pinned BT2 loop suspended per bar; no loader, outcomes, renderer, or resets."""
from __future__ import annotations
import ast
from dataclasses import dataclass
from types import SimpleNamespace,MappingProxyType
from functools import lru_cache
import hashlib
import math
from .detector_capture import _capture_tree,_module,Capture,PINS,NAMES
from .asof_intersections import Clock,ZoneKey
from .build_target_free_pilot import digest

@dataclass(frozen=True)
class AggressiveBar:
    bar: int
    end_ns: int
    low_t: int
    high_t: int
    close_t: int
    volume: float
    ask: dict
    bid: dict
    n_quote: int
    n_rule: int
    consumed_tick_index: int
    available: Clock|None

@dataclass(frozen=True)
class BarDelta:
    records: tuple[Capture,...]
    unavailable_events: int

@lru_cache(maxsize=2)
def _stream_code(collect_diagnostics):
    fn=_capture_tree('BT2').body[0];cut=next(i for i,n in enumerate(fn.body) if isinstance(n,ast.For) and ast.unparse(n.target)=='b')
    counts={'log':0,'all_zones':0,'continue':0,'omitted_payload':0}
    class Transform(ast.NodeTransformer):
        in_main=False
        def visit_Call(self,n):
            n=self.generic_visit(n)
            if not collect_diagnostics and isinstance(n.func,ast.Name) and n.func.id=='log_event':
                n.args[1]=ast.Constant(value='');counts['omitted_payload']+=1
            return n
        def visit_Subscript(self,n):
            n=self.generic_visit(n)
            if isinstance(n.value,ast.Attribute) and isinstance(n.value.value,ast.Name) and n.value.value.id in ('bars','footprints'):
                return ast.Attribute(value=ast.Name(id='feed',ctx=ast.Load()),attr=n.value.attr,ctx=ast.Load())
            return n
        def visit_FunctionDef(self,n):
            if n.name=='log_event':
                counts['log']+=1;n.body=ast.parse(('_log(etype,payload)\n' if collect_diagnostics else '')+'_observe_log(etype,zone,bar,t_ns,reason)').body;return n
            return self.generic_visit(n)
        def visit_Expr(self,n):
            if ast.unparse(n)=='all_zones.append(z)':counts['all_zones']+=1;return None
            return self.generic_visit(n)
        def visit_Continue(self,n):
            if self.in_main:counts['continue']+=1;return ast.Return(value=None)
            return n
    tr=Transform();body=[tr.visit(n) for n in fn.body[:cut]]
    body+=ast.parse('feed=None').body
    loop=fn.body[cut];process_body=ast.parse('nonlocal feed\nfeed=_next_feed\nb=feed.bar').body
    tr.in_main=True
    process_body.extend(tr.visit(n) for n in loop.body)
    process_body+=ast.parse('_budget(len(active))').body
    process=ast.FunctionDef(name='process',args=ast.arguments(posonlyargs=[],args=[ast.arg('_next_feed')],kwonlyargs=[],kw_defaults=[],defaults=[]),body=process_body,decorator_list=[])
    body.append(process);body+=ast.parse('return process, lambda: len(active)').body
    fn.body=body;fn.name='bar_engine'
    if counts!={'log':1,'all_zones':1,'continue':2,'omitted_payload':0 if collect_diagnostics else 6}:raise ValueError('BT2 stream hook census drift')
    tree=ast.Module(body=[fn],type_ignores=[]);ast.fix_missing_locations(tree)
    return compile(tree,'<pinned-bt2-bar-stream>','exec')

class BT2Stream:
    def __init__(self,*,params,bar_spec,tick_size,max_active=100000,max_records_per_bar=100000,max_cells_per_bar=10000,collect_diagnostics=False):
        mod=_module('BT2')
        if not isinstance(params,dict) or set(params)-set(mod.DEFAULTS):raise ValueError('unknown/renderer params')
        if type(tick_size) not in (int,float) or not math.isfinite(tick_size) or tick_size<=0:raise ValueError('positive tick size')
        if not isinstance(bar_spec,str) or bar_spec.count(':')!=1 or bar_spec.split(':')[0] not in ('tick','time') or int(bar_spec.split(':')[1])<1:raise ValueError('explicit bar spec')
        for x in (max_active,max_records_per_bar,max_cells_per_bar):
            if type(x) is not int or x<1:raise ValueError('positive limits')
        if type(collect_diagnostics) is not bool:raise ValueError('explicit diagnostic mode')
        self.params=MappingProxyType({**mod.DEFAULTS,**params});self.tick_size=tick_size
        self.config=digest({'indicator':NAMES['BT2'],'bar_spec':bar_spec,'params':dict(self.params)})
        self.max_active=max_active;self.max_records=max_records_per_bar;self.max_cells=max_cells_per_bar
        self.current=None;self.last=None;self.closed=False;self.poisoned=False;self.log_hash=hashlib.sha256();self.log_count=0
        env=dict(mod.__dict__);env.update(_log=self._log,_observe_log=self._observe,_budget=self._budget)
        exec(_stream_code(collect_diagnostics),env)
        self.process,self.state_size=env['bar_engine'](SimpleNamespace(tick_size=tick_size),None,None,dict(self.params))
    def _log(self,kind,payload):self.log_hash.update(f'{kind}|{payload}\n'.encode());self.log_count+=1
    def _budget(self,n):
        if n>self.max_active:raise ValueError('active zone budget; no pruning')
    def _observe(self,etype,z,b,t_ns,reason):
        mapping={'ZONE_CREATED':'BIRTH','ZONE_TOUCHED':'TOUCH','ZONE_INVALIDATED':'REMOVE','ZONE_EXPIRED':'REMOVE'}
        if etype not in mapping:return
        if t_ns!=self.current.end_ns or b!=self.current.bar:raise ValueError('native event/feed mismatch')
        if self.current.available is None:self.unavailable+=1;return
        if len(self.records)>=self.max_records:raise ValueError('capture budget; no truncation')
        lo=2*float(z['lo'])/self.tick_size;hi=2*float(z['hi'])/self.tick_size
        if not math.isfinite(lo+hi) or abs(lo-round(lo))>1e-7 or abs(hi-round(hi))>1e-7:raise ValueError('native half-tick geometry')
        self.records.append(Capture(mapping[etype],ZoneKey('BT2',self.config,PINS['BT2'],str(z['id'])),self.current.available,self.current.consumed_tick_index,int(b),int(round(lo)),int(round(hi)),-1 if z['is_bull'] else 1,tuple((k,z[k]) for k in ('vol','touches')),reason))
    def push(self,feed):
        if self.closed or self.poisoned:raise ValueError('closed/poisoned stream')
        if not isinstance(feed,AggressiveBar) or any(type(getattr(feed,k)) is not int for k in ('bar','end_ns','low_t','high_t','close_t','n_quote','n_rule','consumed_tick_index')):raise ValueError('typed bar fields')
        if feed.bar!=(self.last.bar+1 if self.last else 0) or feed.end_ns<=0 or feed.consumed_tick_index<0 or not feed.low_t<=feed.close_t<=feed.high_t or min(feed.n_quote,feed.n_rule)<0:raise ValueError('complete ordered bar')
        if self.last and (feed.end_ns<self.last.end_ns or feed.consumed_tick_index<=self.last.consumed_tick_index):raise ValueError('retrograde bar')
        if feed.available is not None and (not isinstance(feed.available,Clock) or feed.available.ns<feed.end_ns or (self.last and self.last.available and feed.available<=self.last.available)):raise ValueError('causal strict availability')
        if not isinstance(feed.volume,(int,float)) or not math.isfinite(feed.volume) or feed.volume<0:raise ValueError('bar volume')
        for d in (feed.ask,feed.bid):
            if not isinstance(d,dict) or len(d)>self.max_cells or any(type(k) is not int or not feed.low_t<=k<=feed.high_t or not isinstance(v,(int,float)) or not math.isfinite(v) or v<0 for k,v in d.items()):raise ValueError('bounded aggressive cells')
        # Native state never retains these maps; no raw batch reference survives.
        self.current=feed;self.records=[];self.unavailable=0
        try:
            self.process(feed);self.last=feed
            if feed.available is None:self.closed=True
            return BarDelta(tuple(self.records),self.unavailable)
        except BaseException:self.poisoned=True;raise
