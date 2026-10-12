"""Observed-tick first passage prototype, not a scientific preregistration.

Labels remain PRIVATE for market inputs. No P&L, intrabar interpolation or
entry fill. Heaps share one tape traversal across anchors; horizon/gap/EOF and
session censoring are explicit, never imputed to a negative label.
"""
from dataclasses import dataclass
from datetime import date
import heapq
from .asof_intersections import Clock

@dataclass(frozen=True)
class Label:
    anchor_id: str
    trade_date: str
    origin: Clock
    resolved: Clock
    origin_index: int
    resolved_index: int
    status: str
    future_observations: int
    usable_response: bool

@dataclass(frozen=True)
class _Pending:
    id: str
    session: str
    clock: Clock
    index: int
    reference2: int

class FirstPassage:
    def __init__(self,*,distance_ticks,horizon_ticks,max_gap_ns,max_pending=100000,max_anchors=1000000):
        for v in (distance_ticks,horizon_ticks,max_pending,max_anchors):
            if type(v) is not int or v<1:raise ValueError('positive label parameters/budgets')
        if max_gap_ns is not None and (type(max_gap_ns) is not int or max_gap_ns<1):raise ValueError('explicit gap policy or None')
        self.d2=2*distance_ticks;self.horizon=horizon_ticks;self.gap=max_gap_ns;self.max_pending=max_pending;self.max_anchors=max_anchors
        self.upper=[];self.lower=[];self.deadlines=[];self.active={};self.seen=set();self.current=None;self.closed=False;self.poisoned=False
    def _resolve(self,id,status,clock,index):
        x=self.active.pop(id,None)
        if x is None:return None
        return Label(id,x.session,x.clock,clock,x.index,index,status,index-x.index,status in ('UP_FIRST','DOWN_FIRST','HORIZON_NO_PASSAGE'))
    def _all(self,status,clock,index):return tuple(self._resolve(id,status,clock,index) for id in sorted(self.active))
    def _compact(self):
        n=len(self.active)
        if not n:self.upper.clear();self.lower.clear();self.deadlines.clear();return
        if max(map(len,(self.upper,self.lower,self.deadlines)))>3*n+1000:
            self.upper=[(x.reference2+self.d2,x.id) for x in self.active.values()];self.lower=[(-(x.reference2-self.d2),x.id) for x in self.active.values()];self.deadlines=[(x.index+self.horizon,x.id) for x in self.active.values()]
            for h in (self.upper,self.lower,self.deadlines):heapq.heapify(h)
    def observe(self,clock,price2,*,index,trade_date):
        if self.closed or self.poisoned:raise ValueError('closed/poisoned labeler')
        if not isinstance(clock,Clock) or type(price2) is not int or price2%2 or type(index) is not int or index<0:raise ValueError('observed whole-tick point/index required')
        old=self.current
        if old and (clock<=old[0] or clock.ns<old[0].ns or index!=old[2]+1):raise ValueError('strict contiguous observed tape')
        if old is None or trade_date!=old[3]:
            d=date.fromisoformat(trade_date)
            if str(d)!=trade_date or d>=date(2026,10,1) or (old and trade_date<=old[3]):raise ValueError('canonical preholdout session')
        try:
            out=[]
            if old and trade_date!=old[3]:out.extend(self._all('SESSION_CENSORED',clock,index))
            elif old and self.gap is not None and clock.ns-old[0].ns>self.gap:out.extend(self._all('GAP_CENSORED',clock,index))
            for heap,edge,status in ((self.upper,price2,'UP_FIRST'),(self.lower,-price2,'DOWN_FIRST')):
                while heap and heap[0][0]<=edge:
                    _,id=heapq.heappop(heap);r=self._resolve(id,status,clock,index)
                    if r:out.append(r)
            # A passage on the final eligible observation wins over no-passage.
            while self.deadlines and self.deadlines[0][0]<=index:
                _,id=heapq.heappop(self.deadlines);r=self._resolve(id,'HORIZON_NO_PASSAGE',clock,index)
                if r:out.append(r)
            self.current=(clock,price2,index,trade_date);self._compact();return tuple(sorted(out,key=lambda x:x.anchor_id))
        except BaseException:self.poisoned=True;raise
    def register(self,anchor_id):
        if self.closed or self.poisoned or self.current is None:raise ValueError('observe actual anchor tick first')
        if not isinstance(anchor_id,str) or not 0<len(anchor_id)<=128 or anchor_id in self.seen:raise ValueError('unique bounded anchor ID')
        if len(self.active)>=self.max_pending or len(self.seen)>=self.max_anchors:raise ValueError('label budget; no truncation')
        c,p,i,s=self.current;x=_Pending(anchor_id,s,c,i,p);self.active[anchor_id]=x;self.seen.add(anchor_id)
        heapq.heappush(self.upper,(p+self.d2,anchor_id));heapq.heappush(self.lower,(-(p-self.d2),anchor_id));heapq.heappush(self.deadlines,(i+self.horizon,anchor_id))
    def finish(self):
        if self.closed or self.poisoned:raise ValueError('closed/poisoned labeler')
        self.closed=True
        if self.current is None:return ()
        c,_,i,_=self.current;out=self._all('EOF_CENSORED',c,i);self._compact();return out
