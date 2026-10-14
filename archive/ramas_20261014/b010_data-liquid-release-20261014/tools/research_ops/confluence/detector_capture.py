"""Observe births/lifecycle from pinned detector source, without changing outputs.

No market loader, permission, outcome or NT8 parity certification. Inputs must
already pass external source/split gates. Hook locations are hash-bound. Captured
records copy primitive values immediately; returned mutable native zones are NOT
features. Build/tape scope must be bound separately by the caller.

Tick bars use actual tick_bar_idx membership, never (bar+1)*N. Time bars are
conservatively available only at the first observed tape record at/after their
close; EOF time bars lacking that record produce diagnostics, not a birth.
"""
from __future__ import annotations
import ast
from dataclasses import dataclass
from functools import lru_cache
import hashlib
import inspect
import math
from pathlib import Path
from .asof_intersections import Clock,ZoneKey,Snapshot
from .build_target_free_pilot import digest

PINS={'BT2':'59cc63904cf9c1a58d97f7fb4e847dd23c0105e4a6516e9681785da30f053c72',
      'BT2A':'0a0f312de5e1b4350a2a102cc051f2d6fd9484696c2a4762dc6f3006c1c54757',
      'AVZP2':'2aca439365296ad3d2c3071f4321dccf49ff1aef8625db10945b7856ca748184'}
NAMES={'BT2':'bigtrap2','BT2A':'bigtrap2absorption','AVZP2':'avolzonepoi2'}

@dataclass(frozen=True)
class Capture:
    kind: str
    key: ZoneKey
    clock: Clock
    consumed_tick_index: int
    source_bar: int
    lo2: int
    hi2: int
    side: int
    properties: tuple
    reason: str=''
    def birth_snapshot(self):
        if self.kind!='BIRTH':raise ValueError('only births create revision zero')
        return Snapshot(self.key,0,self.clock,self.clock,self.lo2,self.hi2,self.side)

@dataclass(frozen=True)
class Receipt:
    records: tuple[Capture,...]
    unavailable_time_events: int
    source_sha256: str
    parameter_sha256: str
    availability_policy: str
    confirms_market_eligibility: bool=False


def _module(family):
    if family=='BT2':from edgelab.bridge.indicators import bigtrap2 as mod
    elif family=='BT2A':from edgelab.bridge.indicators import bigtrap2absorption as mod
    elif family=='AVZP2':from . import _pinned_avzp2 as mod
    else:raise ValueError('unsupported detector')
    raw=Path(mod.__file__).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=PINS[family]:raise ValueError('detector source changed; review hook locations before use')
    return mod

def _capture_tree(family):
    mod=_module(family);tree=ast.parse(inspect.getsource(mod.run));counts={'birth':0,'remove':0,'classify':0,'log':0,'signature':0}
    class Hooks(ast.NodeTransformer):
        in_tape_loop=False
        def visit_For(self,n):
            is_tape=family=='BT2A' and ast.unparse(n.target)=='i' and ast.unparse(n.iter)=='range(n_ticks)'
            before=self.in_tape_loop
            if is_tape:
                self.in_tape_loop=True;counts['tape_loop']=counts.get('tape_loop',0)+1
            n=self.generic_visit(n);self.in_tape_loop=before
            return n
        def visit_FunctionDef(self,n):
            if family=='BT2' and n.name=='log_event':
                n=self.generic_visit(n);n.body.extend(ast.parse("_observe_log(etype, zone, bar, t_ns, reason)").body);counts['log']+=1;return n
            if family=='BT2A' and n.name=='update_active_zones':
                n.args.args.extend([ast.arg(arg='_current_tick_index'),ast.arg(arg='_available_index')]);counts['signature']+=1
            if family=='BT2A' and n.name=='flush_block':
                n.args.args.append(ast.arg(arg='_available_index'));counts['flush_signature']=counts.get('flush_signature',0)+1
            return self.generic_visit(n)
        def visit_Call(self,n):
            n=self.generic_visit(n)
            if family=='BT2A' and isinstance(n.func,ast.Name):
                if n.func.id=='update_active_zones':n.args.extend([ast.parse('blk[-1]',mode='eval').body,ast.Name(id='_available_index',ctx=ast.Load())])
                elif n.func.id=='flush_block':
                    n.args.append(ast.Name(id='i',ctx=ast.Load()) if self.in_tape_loop else ast.Constant(value=None));counts['flush_call']=counts.get('flush_call',0)+1
            return n
        def visit_Expr(self,n):
            n=self.generic_visit(n);v=n.value
            if not isinstance(v,ast.Call) or not isinstance(v.func,ast.Attribute) or not isinstance(v.func.value,ast.Name):return n
            target,op=v.func.value.id,v.func.attr
            if family=='BT2A' and target=='active_zones' and op=='append':
                counts['birth']+=1;return [n,*ast.parse("_observe_raw('BIRTH', z_entry, b_idx, int(blk[-1]), int(blk_ts[-1]), _available_index)").body]
            if family=='BT2A' and target=='active_zones' and op=='remove':
                counts['remove']+=1;return [n,*ast.parse("_observe_raw('REMOVE', z, bar_idx, int(_current_tick_index), int(t_ns), _available_index)").body]
            if family=='AVZP2' and target=='zones' and op=='append':
                counts['birth']+=1;return [n,*ast.parse("_observe_avz('BIRTH', z, b)").body]
            return n
        def visit_If(self,n):
            n=self.generic_visit(n)
            if family=='AVZP2' and ast.unparse(n.test)=="p['ob_bars'] > 0":
                n.orelse.extend(ast.parse("_observe_avz('CLASSIFY', z, b)").body);counts['immediate']=counts.get('immediate',0)+1
            return n
        def visit_Assign(self,n):
            n=self.generic_visit(n)
            if family=='AVZP2' and any(isinstance(t,ast.Subscript) and isinstance(t.value,ast.Name) and t.value.id=='z' and isinstance(t.slice,ast.Constant) and t.slice.value=='decided_bar' for t in n.targets):
                counts['classify']+=1;return [n,*ast.parse("_observe_avz('CLASSIFY', z, b)").body]
            return n
    tree=Hooks().visit(tree);ast.fix_missing_locations(tree)
    expected={'BT2':{'log':1},'BT2A':{'birth':1,'remove':2,'signature':1,'flush_signature':1,'flush_call':3,'tape_loop':1},'AVZP2':{'birth':1,'classify':1,'immediate':1}}[family]
    if {k:v for k,v in counts.items() if v}!=expected:raise ValueError('hook location census drift')
    return tree

@lru_cache(maxsize=3)
def _code(family):
    return compile(_capture_tree(family),f'<pinned-capture-{family}>','exec')

def _validate_tape(ticks):
    import numpy as np
    n=len(ticks)
    if not n:raise ValueError('nonempty declared tape required')
    for name in ('ts_ns','price_ticks','volume','bid_ticks','ask_ticks','sequence'):
        a=np.asarray(getattr(ticks,name))
        if a.ndim!=1 or len(a)!=n or a.dtype.kind not in 'iuf' or not np.isfinite(a).all():raise ValueError('complete finite aligned tape declarations required')
        if name!='volume' and (a.dtype.kind not in 'iu'):raise ValueError('integer tape prices/clocks/sequence required')
    if np.any(ticks.ts_ns<=0) or np.any(ticks.ts_ns[1:]<ticks.ts_ns[:-1]) or np.any(ticks.sequence<0) or np.any(ticks.sequence[1:]<=ticks.sequence[:-1]):raise ValueError('strict sequence and nonretrograde time required')
    if np.any(ticks.volume<0) or np.any(ticks.bid_ticks<=0) or np.any(ticks.ask_ticks<ticks.bid_ticks):raise ValueError('valid quotes/volume required; no quote fabrication')
    if type(ticks.tick_size) not in (int,float) or not math.isfinite(ticks.tick_size) or ticks.tick_size<=0:raise ValueError('positive finite tick size')
    return n

def _bar_availability(ticks,bars):
    import numpy as np
    membership=np.asarray(bars.tick_bar_idx)
    n=len(ticks)
    if membership.ndim!=1 or len(membership)!=n or membership.dtype.kind not in 'iu' or np.any(membership<0) or np.any(np.diff(membership)<0):raise ValueError('actual ordered complete tape/bar membership required')
    if set(map(int,np.unique(membership)))!=set(range(len(bars.end_ns))):raise ValueError('missing bar membership')
    last=np.r_[np.flatnonzero(np.diff(membership)),n-1].astype(int)
    if len(last)!=len(bars.end_ns):raise ValueError('membership/bar shape mismatch')
    clocks=[]
    for b,i in enumerate(last):
        end=int(bars.end_ns[b])
        if bars.kind=='tick':
            if end!=int(ticks.ts_ns[i]):raise ValueError('tick close differs from actual member')
            first=0 if b==0 else int(last[b-1])+1
            count=int(i)-first+1
            if count>int(bars.param):raise ValueError('tick-bar member count exceeds spec')
            if count<int(bars.param):
                j=int(i)+1
                clocks.append(None if j>=n else (int(i),Clock(int(ticks.ts_ns[j]),int(ticks.sequence[j]))))
            else:clocks.append((int(i),Clock(end,int(ticks.sequence[i]))))
        elif bars.kind=='time':
            if int(ticks.ts_ns[i])>=end:raise ValueError('time-bar member outside half-open close')
            j=int(i)+1
            if j>=n:clocks.append(None)
            elif int(ticks.ts_ns[j])<end:raise ValueError('next member before time close')
            else:clocks.append((int(i),Clock(int(ticks.ts_ns[j]),int(ticks.sequence[j]))))
        else:raise ValueError('only tick/time bars')
    return clocks

def capture_run(family,ticks,*,bars=None,footprints=None,sessions=None,params=None,max_records=100000):
    """Return (native result, immutable receipt), with no data-access authority.

    Calling code must run source/session/holdout gates BEFORE supplying arrays.
    This adapter itself verifies declarations only. Full native outputs/logs are
    retained for regression; production streaming/IO is still future work.
    """
    n=_validate_tape(ticks);mod=_module(family)
    if type(max_records) is not int or max_records<1:raise ValueError('record budget required')
    if params and (not isinstance(params,dict) or set(params)-set(mod.DEFAULTS)):raise ValueError('unknown/renderer parameter rejected')
    p={**mod.DEFAULTS,**(params or {})}
    if family in ('BT2','AVZP2'):
        if bars is None or footprints is None:raise ValueError('prepared bars/footprints required')
        clocks=_bar_availability(ticks,bars);bar_spec=f'{bars.kind}:{bars.param}'
    else:clocks=None;bar_spec=None
    config=digest({'indicator':NAMES[family],'bar_spec':bar_spec,'params':p})
    records=[];unavailable=0;ordinal=0
    def add(kind,z,b,i,clock,reason=''):
        nonlocal ordinal
        if len(records)>=max_records:raise ValueError('capture budget exceeded; no partial receipt')
        if family=='AVZP2':
            if kind=='BIRTH':zid=f'{b}:{ordinal}';ordinal+=1;identity_by_object[id(z)]=zid
            else:
                if id(z) not in identity_by_object:raise ValueError('classification without observed birth')
                zid=identity_by_object[id(z)]
            lo2,hi2=2*int(z['low_tick']),2*int(z['high_tick']);side=0
            props=tuple((k,z[k]) for k in ('levels','score','thresh','samples','state','decided_bar'))
        else:
            zid=z['id'];a=2*float(z['lo'])/ticks.tick_size;h=2*float(z['hi'])/ticks.tick_size
            if not math.isfinite(a+h) or abs(a-round(a))>1e-7 or abs(h-round(h))>1e-7:raise ValueError('native zone not half-tick geometry')
            lo2,hi2=int(round(a)),int(round(h));side=-1 if z['is_bull'] else 1
            keys=('vol','touches') if family=='BT2' else ('vol','nrows','frac','a_score','a_thr','touches')
            props=tuple((k,z[k]) for k in keys)
        # primitive immutable copy; no mutable final-state references.
        def scalar(v):
            if hasattr(v,'item'):v=v.item()
            if v is not None and type(v) not in (int,float,bool,str):raise ValueError('nonprimitive capture property')
            if isinstance(v,float) and not math.isfinite(v):raise ValueError('nonfinite capture property')
            return v
        props=tuple((k,scalar(v)) for k,v in props)
        records.append(Capture(kind,ZoneKey(family,config,PINS[family],str(zid)),clock,int(i),int(b),lo2,hi2,side,props,reason))
    def observe_log(etype,z,b,t_ns,reason):
        nonlocal unavailable
        mapping={'ZONE_CREATED':'BIRTH','ZONE_TOUCHED':'TOUCH','ZONE_INVALIDATED':'REMOVE','ZONE_EXPIRED':'REMOVE'}
        if etype not in mapping:return
        if int(t_ns)!=int(bars.end_ns[b]):raise ValueError('native bar/event close mismatch')
        at=clocks[b]
        if at is None:unavailable+=1;return
        i,c=at;add(mapping[etype],z,b,i,c,reason)
    def observe_raw(kind,z,b,i,t_ns,available_index):
        nonlocal unavailable
        if not 0<=i<n or t_ns!=int(ticks.ts_ns[i]):raise ValueError('bucket event/member mismatch')
        if available_index is None:
            unavailable+=1;return
        if not i<=available_index<n:raise ValueError('bucket availability precedes consumption')
        add(kind,z,b,i,Clock(int(ticks.ts_ns[available_index]),int(ticks.sequence[available_index])),z.get('end_reason') or '')
    identity_by_object={}
    def observe_avz(kind,z,b):
        nonlocal unavailable
        at=clocks[b]
        if at is None:unavailable+=1;return
        i,c=at;add(kind,z,b,i,c)
    env=dict(mod.__dict__);env.update(_observe_log=observe_log,_observe_raw=observe_raw,_observe_avz=observe_avz)
    exec(_code(family),env)
    if family=='AVZP2':
        if sessions is None:raise ValueError('explicit aligned detector sessions required')
        native=env['run'](bars,footprints,sessions,p)
    elif family=='BT2':native=env['run'](ticks,bars,footprints,p)
    else:native=env['run'](ticks,params=p)
    policy='FULL_TICK_MEMBER_CLOSE_PARTIAL_AFTER_NEXT_OBSERVATION' if clocks is None or bars.kind=='tick' else 'FIRST_OBSERVED_TICK_AT_OR_AFTER_TIME_CLOSE'
    return native,Receipt(tuple(records),unavailable,PINS[family],config,policy)
