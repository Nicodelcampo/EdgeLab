"""Exact bounded natural-session primitives, no data reader/permission.

Shared by bar spec, not by detector config. Integer-volume source only (exact
float64 sums); global aggressive tick-rule state and NT8 TOTAL timestamp carry
survive session boundaries. Time:1 primary bars align with native CME boundaries.
"""
from __future__ import annotations
from dataclasses import dataclass
from types import SimpleNamespace
import numpy as np
from edgelab.bridge import bars as B
from .detector_capture import _validate_tape
from ._pinned_total_footprint import build_total_footprint_csr_nt8
from .asof_intersections import Clock
from .avz_stream import BarFeed
from .bt2_stream import AggressiveBar

@dataclass(frozen=True)
class SessionTape:
    ticks: object
    first_index: int
    next_clock: Clock|None
    session_id: int

class SessionPrimitives:
    def __init__(self,*,max_ticks=5000000,max_same_ns=100000,max_cells=3000000):
        for v in (max_ticks,max_same_ns,max_cells):
            if type(v) is not int or v<1:raise ValueError('positive primitive budgets')
        self.max_ticks=max_ticks;self.max_same=max_same_ns;self.max_cells=max_cells
        self.last_price=None;self.last_dir=0;self.previous=None;self.next_index=0;self.bar_offsets={};self.carries={};self.prepared_specs=set();self.poisoned=False
    def begin(self,st):
        if self.poisoned:raise ValueError('poisoned primitives')
        if not isinstance(st,SessionTape) or st.first_index!=self.next_index:raise ValueError('contiguous natural-session tape')
        t=st.ticks;n=len(t)
        if not 0<n<=self.max_ticks:raise ValueError('session tick budget; no truncation')
        _validate_tape(t)
        ses=B.session_ids(t.ts_ns)
        if np.any(ses!=st.session_id):raise ValueError('single native session required')
        if self.previous is not None and (self.previous.next_clock is None or self.previous.next_clock!=Clock(int(t.ts_ns[0]),int(t.sequence[0]))):raise ValueError('next session differs from declared lookahead')
        if self.previous is not None and (st.session_id<=self.previous.session_id or int(t.ts_ns[0])<int(self.previous.ticks.ts_ns[-1]) or int(t.sequence[0])<=int(self.previous.ticks.sequence[-1])):raise ValueError('ordered session boundary')
        if st.next_clock is not None and (st.next_clock<=Clock(int(t.ts_ns[-1]),int(t.sequence[-1])) or st.next_clock.ns<int(t.ts_ns[-1])):raise ValueError('causal next observation')
        v=np.asarray(t.volume,dtype=np.float64)
        if np.any(v!=np.floor(v)) or v.sum()>2**53:raise ValueError('exact integer-volume source required')
        tail=n-int(np.searchsorted(t.ts_ns,t.ts_ns[-1],side='left'))
        if tail>self.max_same:raise ValueError('timestamp cohort budget; no clipping')
        px=np.asarray(t.price_ticks);aq=np.asarray(t.ask_ticks);bq=np.asarray(t.bid_ticks)
        quote=np.where(px>=aq,1,np.where(px<=bq,-1,0)).astype(np.int8)
        prev=np.r_[px[0] if self.last_price is None else self.last_price,px[:-1]]
        movement=np.where(px>prev,1,np.where(px<prev,-1,0)).astype(np.int8)
        candidate=np.where(quote!=0,quote,movement).astype(np.int8)
        if candidate[0]==0:candidate[0]=self.last_dir or 1
        idx=np.maximum.accumulate(np.where(candidate!=0,np.arange(n),0))
        self.sides=candidate[idx];self.quoted=quote!=0
        self.last_price=int(px[-1]);self.last_dir=int(self.sides[-1]);self.current=st;self.prepared_specs=set();self.next_index+=n
    def end(self):
        # Only boundary scalar/cohort state survives. No previous-session arrays.
        t=self.current.ticks
        self.previous=SessionTape(SimpleNamespace(ts_ns=np.array([t.ts_ns[-1]]),sequence=np.array([t.sequence[-1]])),self.current.first_index,self.current.next_clock,self.current.session_id)
        self.current=None;self.sides=None;self.quoted=None
    def build(self,spec):
        if self.poisoned or self.current is None:raise ValueError('begin natural session first')
        if spec in self.prepared_specs:raise ValueError('build once per spec and share result')
        try:return self._build(spec)
        except BaseException:self.poisoned=True;raise
    def _build(self,spec):
        kind,size=spec.split(':');size=int(size)
        if kind not in ('tick','time') or size<1 or (kind=='time' and size!=1):raise ValueError('pilot supports native ticks and time:1 only')
        st=self.current;t=st.ticks;n=len(t)
        bars=B.build_tick_bars(t,size) if kind=='tick' else B.build_time_bars(t,size)
        nb=len(bars);offset=self.bar_offsets.get(spec,0);lasts=np.r_[np.flatnonzero(np.diff(bars.tick_bar_idx)),n-1];starts=np.r_[0,lasts[:-1]+1]
        # Aggressive footprints: classification once/session; exact cell sums.
        px=np.asarray(t.price_ticks);vol=np.asarray(t.volume,dtype=np.float64);pmin=int(px.min());width=int(px.max())-pmin+1
        if nb*2*width>np.iinfo(np.int64).max:raise ValueError('aggressive cell key overflow')
        keys=(bars.tick_bar_idx*2+(self.sides>0))*width+(px-pmin)
        uk,inv=np.unique(keys,return_inverse=True)
        if len(uk)>self.max_cells:raise ValueError('footprint cell budget')
        values=np.bincount(inv,weights=vol);ubs=(uk//width)//2;asks=(uk//width)%2;levels=uk%width+pmin
        maps_a=[{} for _ in range(nb)];maps_b=[{} for _ in range(nb)]
        for b,a,p,v in zip(ubs,asks,levels,values):(maps_a if a else maps_b)[int(b)][int(p)]=float(v)
        nq=np.bincount(bars.tick_bar_idx,weights=self.quoted.astype(np.int64),minlength=nb).astype(np.int64);nr=(lasts-starts+1)-nq
        # Carry exactly the previous final timestamp members assigned beyond its
        # last native bar. Do not reset NT8 subseries at a session/batch boundary.
        carry=self.carries.get(spec)
        if carry is None:total_t=t
        else:total_t=SimpleNamespace(ts_ns=np.r_[carry[0],t.ts_ns],price_ticks=np.r_[carry[1],px],volume=np.r_[carry[2],vol])
        total=build_total_footprint_csr_nt8(total_t,bars)
        if len(total.ticks)>self.max_cells:raise ValueError('TOTAL cell budget')
        close=int(t.ts_ns[-1]);left=int(np.searchsorted(bars.end_ns,close,side='left'));right=int(np.searchsorted(bars.end_ns,close,side='right'))
        tail_start=int(np.searchsorted(t.ts_ns,close,side='left'));skip=max(0,right-left-1) if right-left>1 else 0
        # Time bars with close>last ns keep the last timestamp in that same bar;
        # it is not carry. No earlier cohort can be assigned to a future bar.
        if right==nb:
            cs=tail_start+skip;self.carries[spec]=(t.ts_ns[cs:].copy(),px[cs:].copy(),vol[cs:].copy())
        else:self.carries[spec]=None
        sessions=B.session_ids(bars.end_ns);bt=[];av=[]
        for b,last in enumerate(lasts):
            end=int(bars.end_ns[b]);available=None
            if kind=='tick' and int(last-starts[b]+1)==size:available=Clock(end,int(t.sequence[last]))
            elif int(last)+1<n:available=Clock(int(t.ts_ns[last+1]),int(t.sequence[last+1]))
            else:available=st.next_clock
            if available is not None and available.ns<end:raise ValueError('time bar spans undeclared session boundary')
            cells,vs=total.bar_cells(b);bi=offset+b;ci=st.first_index+int(last)
            bt.append(AggressiveBar(bi,end,int(bars.low_t[b]),int(bars.high_t[b]),int(bars.close_t[b]),float(bars.volume[b]),maps_a[b],maps_b[b],int(nq[b]),int(nr[b]),ci,available))
            av.append(BarFeed(bi,end,int(sessions[b]),int(bars.low_t[b]),int(bars.high_t[b]),cells,vs,ci,available))
        self.bar_offsets[spec]=offset+nb;self.prepared_specs.add(spec)
        return bt,av
