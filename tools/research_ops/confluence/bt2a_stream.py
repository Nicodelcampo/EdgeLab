"""BT2A causal bucket engine: pinned detector rules, bounded tick buffering.

No data loader/permission or NT8 certification. Keeps native absorption history
and active zones across chunk boundaries. Omits fills/render outputs: neither
changes detector rules; observability is captured separately. EOF residuals do
not create observable removals. Caller supplies approved session declarations.
"""
from __future__ import annotations
import ast
from dataclasses import dataclass
from functools import lru_cache
from types import SimpleNamespace,MappingProxyType
import hashlib
import math
import numpy as np
from .detector_capture import _capture_tree,_module,Capture,PINS,NAMES
from .asof_intersections import Clock,ZoneKey
from .build_target_free_pilot import digest

@dataclass(frozen=True)
class TickChunk:
    ts_ns: np.ndarray
    price_ticks: np.ndarray
    volume: np.ndarray
    bid_ticks: np.ndarray
    ask_ticks: np.ndarray
    sequence: np.ndarray
    sessions: np.ndarray
    first_index: int

@dataclass(frozen=True)
class ChunkDelta:
    records: tuple[Capture,...]
    unavailable_events: int
    buckets_processed: int

@lru_cache(maxsize=2)
def _bucket_code(collect_diagnostics):
    fn=_capture_tree('BT2A').body[0]
    cut=next(i for i,n in enumerate(fn.body) if isinstance(n,ast.For) and ast.unparse(n.target)=='i' and ast.unparse(n.iter)=='range(n_ticks)')
    body=[];counts={'pending':0,'log':0,'omitted_log':0,'omitted_diagnostics':0}
    class Trim(ast.NodeTransformer):
        def visit_Assign(self,n):
            names={x.id for t in n.targets for x in ast.walk(t) if isinstance(x,ast.Name)}
            if not collect_diagnostics and names & {'t_start_iso','t_end_iso','trade_date','dur_ms','last_bid','last_ask','spread_ticks','mid0','mid1','d_ticks_mid'}:
                counts['omitted_diagnostics']+=1;return None
            return self.generic_visit(n)
        def visit_Expr(self,n):
            if not collect_diagnostics and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Name) and n.value.func.id=='log_event':
                counts['omitted_log']+=1;return None
            if ast.unparse(n)=='pending_fills.append(z_entry)':counts['pending']+=1;return None
            return self.generic_visit(n)
        def visit_FunctionDef(self,n):
            if n.name=='log_event':
                # Same content without retaining CSV/seq strings or FILL logs.
                counts['log']+=1;n.body=ast.parse('_log(t_ns,ev_type,payload)').body;return n
            return self.generic_visit(n)
    tr=Trim()
    for n in fn.body[:cut]:
        if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ('n_ticks','s_ids') for t in n.targets):continue
        body.append(tr.visit(n))
    body.extend(ast.parse('return flush_block, lambda: (len(abs_ring),len(active_zones))').body)
    fn.body=body;fn.name='bucket_engine'
    if counts!={'pending':1,'log':1,'omitted_log':0 if collect_diagnostics else 6,'omitted_diagnostics':0 if collect_diagnostics else 10}:raise ValueError('BT2A stream census drift')
    tree=ast.Module(body=[fn],type_ignores=[]);ast.fix_missing_locations(tree)
    return compile(tree,'<pinned-bt2a-bucket-stream>','exec')

_FIELDS=('ts_ns','price_ticks','volume','bid_ticks','ask_ticks','sequence','sessions')

class BT2AStream:
    def __init__(self,*,params,tick_size,max_active=100000,max_records_per_chunk=200000,max_chunk_ticks=100000,max_buffer_ticks=1000,max_history_values=5000,collect_diagnostics=False):
        mod=_module('BT2A')
        if not isinstance(params,dict) or set(params)-set(mod.DEFAULTS):raise ValueError('unknown detector params')
        self.params=MappingProxyType({**mod.DEFAULTS,**params})
        if type(tick_size) not in (int,float) or not math.isfinite(tick_size) or tick_size<=0:raise ValueError('positive tick size')
        for v in (max_active,max_records_per_chunk,max_chunk_ticks,max_buffer_ticks,max_history_values):
            if type(v) is not int or v<1:raise ValueError('positive explicit stream limits')
        if type(collect_diagnostics) is not bool:raise ValueError('explicit diagnostic mode')
        if max(10,int(self.params['AbsorptionLookback']))>max_history_values:raise ValueError('native history exceeds budget; no shortening')
        self.window=max(2,int(self.params['TapeWindowTicks']))
        if self.window>max_buffer_ticks:raise ValueError('native tape window exceeds buffer budget; no shortening')
        self.max_active=max_active;self.max_records=max_records_per_chunk;self.max_chunk=max_chunk_ticks
        self.config=digest({'indicator':NAMES['BT2A'],'bar_spec':None,'params':dict(self.params)})
        self.ticks=SimpleNamespace(tick_size=float(tick_size));self.current=None;self.buffer=None;self.session=None;self.last_clock=None;self.last_session=None;self.next_index=0
        self.closed=False;self.poisoned=False;self.log_hash=hashlib.sha256();self.log_count=0;self.total_buckets=0
        env=dict(mod.__dict__);env.update(_observe_raw=self._observe,_log=self._log)
        exec(_bucket_code(collect_diagnostics),env);self.flush,self.state_sizes=env['bucket_engine'](self.ticks,params=dict(self.params))
    def _log(self,t_ns,kind,payload):
        # Ordered normalized native detector diagnostics, no FILL/order labels.
        self.log_hash.update(f'{kind}|{payload}\n'.encode());self.log_count+=1
    def _observe(self,kind,z,b,i,t_ns,available_index):
        if t_ns!=int(self.current['ts_ns'][i]):raise ValueError('native bucket/member mismatch')
        clock=self.available
        if clock is None:self.unavailable+=1;return
        if clock.ns<int(t_ns):raise ValueError('availability before consumption')
        if len(self.records)>=self.max_records:raise ValueError('chunk capture budget; no truncation')
        lo=2*float(z['lo'])/self.ticks.tick_size;hi=2*float(z['hi'])/self.ticks.tick_size
        if abs(lo-round(lo))>1e-7 or abs(hi-round(hi))>1e-7:raise ValueError('half-tick zone geometry')
        props=[]
        for k in ('vol','nrows','frac','a_score','a_thr','touches'):
            v=z[k].item() if isinstance(z[k],np.generic) else z[k]
            if isinstance(v,float) and not math.isfinite(v):raise ValueError('nonfinite capture')
            props.append((k,v))
        self.records.append(Capture(kind,ZoneKey('BT2A',self.config,PINS['BT2A'],str(z['id'])),clock,int(self.current['indices'][i]),int(b),int(round(lo)),int(round(hi)),-1 if z['is_bull'] else 1,tuple(props),z.get('end_reason') or ''))
    def _process(self,data,residual,available):
        self.current=data;self.available=available
        for k in _FIELDS[:-1]:setattr(self.ticks,k,data[k])
        self.flush(list(range(len(data['ts_ns']))),residual,int(data['sessions'][0]),None if available is None else len(data['ts_ns'])-1)
        history,active=self.state_sizes()
        if active>self.max_active:raise ValueError('active zone budget exceeded; no pruning')
        if history>max(10,int(self.params['AbsorptionLookback'])):raise ValueError('native history bound violated')
        self.total_buckets+=1;self.processed+=1
        self.current=None
        for k in _FIELDS[:-1]:setattr(self.ticks,k,None)
    def _append(self,data):
        if self.buffer is None:self.buffer={k:v.copy() for k,v in data.items()}
        else:self.buffer={k:np.concatenate((self.buffer[k],data[k])) for k in data}
    def _validate(self,chunk):
        if not isinstance(chunk,TickChunk) or type(chunk.first_index) is not int or chunk.first_index!=self.next_index:raise ValueError('contiguous absolute chunk indices required')
        arrays={k:np.asarray(getattr(chunk,k)) for k in _FIELDS};n=len(arrays['ts_ns'])
        if not 0<n<=self.max_chunk:raise ValueError('nonempty bounded chunk')
        for k,a in arrays.items():
            if a.ndim!=1 or len(a)!=n or a.dtype.kind not in ('iuf' if k=='volume' else 'iu') or not np.isfinite(a).all():raise ValueError('aligned numeric chunk')
        t=arrays['ts_ns'];sq=arrays['sequence'];ss=arrays['sessions']
        if np.any(t<=0) or np.any(t[1:]<t[:-1]) or np.any(sq<0) or np.any(sq[1:]<=sq[:-1]) or np.any(ss[1:]<ss[:-1]):raise ValueError('ordered clocks and sessions')
        first=Clock(int(t[0]),int(sq[0]))
        if self.last_clock and (first<=self.last_clock or int(sq[0])<=self.last_clock.sequence or int(t[0])<self.last_clock.ns):raise ValueError('retrograde chunk boundary')
        if self.last_session is not None and int(ss[0])<self.last_session:raise ValueError('retrograde session')
        if np.any(arrays['volume']<0) or np.any(arrays['bid_ticks']<=0) or np.any(arrays['ask_ticks']<arrays['bid_ticks']):raise ValueError('native quote/volume format; no fabrication')
        if chunk.first_index+n>np.iinfo(np.int64).max:raise ValueError('absolute index overflow')
        arrays['indices']=np.arange(chunk.first_index,chunk.first_index+n,dtype=np.int64)
        return arrays,n
    def push(self,chunk):
        if self.closed or self.poisoned:raise ValueError('closed/poisoned stream')
        data,n=self._validate(chunk);self.records=[];self.unavailable=0;self.processed=0
        try:
            # Split only at true session boundaries and native TapeWindowTicks.
            edges=np.r_[0,np.flatnonzero(np.diff(data['sessions']))+1,n]
            for begin,end in zip(edges[:-1],edges[1:]):
                pos=int(begin);end=int(end);sess=int(data['sessions'][pos])
                if self.session is not None and sess!=self.session and self.buffer is not None:
                    self._process(self.buffer,True,Clock(int(data['ts_ns'][pos]),int(data['sequence'][pos])));self.buffer=None
                self.session=sess
                while pos<end:
                    have=0 if self.buffer is None else len(self.buffer['ts_ns']);take=min(self.window-have,end-pos)
                    self._append({k:v[pos:pos+take] for k,v in data.items()});pos+=take
                    if len(self.buffer['ts_ns'])==self.window:
                        self._process(self.buffer,False,Clock(int(self.buffer['ts_ns'][-1]),int(self.buffer['sequence'][-1])));self.buffer=None
            self.last_clock=Clock(int(data['ts_ns'][-1]),int(data['sequence'][-1]));self.last_session=int(data['sessions'][-1]);self.next_index+=n
            return ChunkDelta(tuple(self.records),self.unavailable,self.processed)
        except BaseException:self.poisoned=True;raise
    def finish(self):
        if self.closed or self.poisoned:raise ValueError('closed/poisoned stream')
        self.records=[];self.unavailable=0;self.processed=0
        try:
            if self.buffer is not None:self._process(self.buffer,True,None);self.buffer=None
            self.closed=True;return ChunkDelta(tuple(self.records),self.unavailable,self.processed)
        except BaseException:self.poisoned=True;raise
    @property
    def buffered_ticks(self):return 0 if self.buffer is None else len(self.buffer['ts_ns'])
