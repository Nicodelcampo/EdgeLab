"""Exact-four completed-bar geometry. No backfill, fills or price outcomes.

Distinct causal peaks in disjoint blocks. The fourth confirmation either
emits one immutable zone or rejects the block. Later peaks never rescue it.
"""
from __future__ import annotations
from collections import Counter
import copy
import math


def validate_params(p):
    required=("w","max_gap","max_step","min_pull","dmax","total_min","step_min",
              "confirmation_mode","confirm_ticks")
    if any(k not in p for k in required):raise ValueError("INCOMPLETE_EXACT4_PARAMS")
    for k in ("w","max_gap","max_step","min_pull","total_min","step_min"):
        if isinstance(p[k],bool) or not isinstance(p[k],int) or p[k]<0:
            raise ValueError("NONNEGATIVE_INTEGER_REQUIRED:"+k)
    if p["w"]<1 or p["max_gap"]<1:raise ValueError("POSITIVE_W_GAP_REQUIRED")
    if p["dmax"] is not None and (isinstance(p["dmax"],bool) or
        not isinstance(p["dmax"],int) or p["dmax"]<1):raise ValueError("DMAX_FAIL")
    if p["confirmation_mode"] not in ("precio","velas"):raise ValueError("MODE_FAIL")
    if p["confirmation_mode"]=="precio" and (isinstance(p["confirm_ticks"],bool) or
        not isinstance(p["confirm_ticks"],int) or p["confirm_ticks"]<1):
        raise ValueError("CONFIRM_TICKS_FAIL")
    return copy.deepcopy(p)


class Exact4:
    """Integer-tick inputs known ONLY at completed-bar publication.

    Rows/times in returned events are logical bar indices/times, not raw/live
    availability. A caller must attach observed publication rows before trading.
    Events returned to callers are copies; no mutable internal event is exposed.
    """
    def __init__(self,params):
        self.p=validate_params(params)
        self.h=[];self.l=[];self.c=[];self.t=[];self.minus_l=[];self.minus_h=[]
        self.session=None
        self.segment_start=0;self.stats=Counter();self._events=[];self._rejections=[]
        self.states={k:self._state() for k in (1,-1)}

    @staticmethod
    def _state():
        return dict(candidates=[],members=[],confirmed=[],last=None,P=None)

    @property
    def events(self):return copy.deepcopy(self._events)

    @property
    def rejections(self):return copy.deepcopy(self._rejections)

    def _close(self,st,reason):
        if st["members"]:
            self.stats["incomplete_blocks_"+reason]+=1
            self.stats["incomplete_peaks_"+reason]+=len(st["members"])
        st.update(members=[],confirmed=[],last=None,P=None)

    def _accept(self,kind,q,j):
        st=self.states[kind];p=self.p
        x=self.h if kind==1 else self.minus_l
        y=self.l if kind==1 else self.minus_h
        if st["last"] is not None and q<=st["last"]:
            self.stats["duplicate_or_older_confirmation"]+=1;return None
        if st["last"] is not None:
            prior=st["last"]
            pull=st["P"]-min(y[prior+1:q],default=st["P"])
            step=st["P"]-x[q]
            if x[q]>st["P"] or step>p["max_step"] or pull<p["min_pull"]:
                self.stats["ineligible_peak"]+=1;return None
        st["members"].append(q);st["confirmed"].append(j)
        st["last"]=q;st["P"]=x[q];self.stats["eligible_peaks"]+=1
        if len(st["members"])<4:return None
        assert len(st["members"])==4 and len(set(st["members"]))==4
        members=tuple(st["members"]);conf=tuple(st["confirmed"])
        reasons=[]
        if p["dmax"] is not None and members[-1]-members[0]>p["dmax"]:reasons.append("duration")
        if abs(x[members[-1]]-x[members[0]])<p["total_min"]:reasons.append("total_step")
        if max(abs(x[b]-x[a]) for a,b in zip(members,members[1:]))<p["step_min"]:
            reasons.append("individual_step")
        # Consume all four even on rejection; keep structural last-peak anchor
        # to preserve the chain's gap/break/step rules across disjoint blocks.
        st["members"]=[];st["confirmed"]=[]
        if reasons:
            self._rejections.append(dict(kind="H" if kind==1 else "L",
                members=list(members),det_i=j,reasons=reasons))
            self.stats["rejected_four_blocks"]+=1;return None
        level=self.h[q] if kind==1 else self.l[q]
        e=dict(id=f'{"H" if kind==1 else "L"}:{members[0]}',
            kind="H" if kind==1 else "L",session_id=self.session,
            members=list(members),members_known_at=list(conf),n_peaks=4,
            det_pico=4,pico4_i=q,pico4_known_bar_i=j,det_i=j,
            logical_available_bar_i=j,logical_available_time=self.t[j],
            level_tick=level,trigger_tick=level-kind*p["confirm_ticks"]
                if p["confirmation_mode"]=="precio" else None,
            lower_tick=min(self.h[v] if kind==1 else self.l[v] for v in members),
            upper_tick=max(self.h[v] if kind==1 else self.l[v] for v in members),
            confirmation_mode=p["confirmation_mode"],
            publication_scope="COMPLETED_BAR_LOGICAL_ONLY_CALLER_MUST_ATTACH_RAW_AVAILABILITY",
            outcome_computed=False)
        self._events.append(e);self.stats["zones"]+=1
        self.stats["zones_"+e["kind"]]+=1
        return copy.deepcopy(e)

    def append(self,h,l,c,t,session_id=None):
        if any(isinstance(v,bool) or not isinstance(v,(int,float)) or
            not math.isfinite(float(v)) for v in (h,l,c,t)):raise ValueError("NONFINITE_BAR")
        if any(int(v)!=v for v in (h,l,c)):raise ValueError("INTEGER_TICKS_REQUIRED")
        if h<l or not l<=c<=h:raise ValueError("OHLC_FAIL")
        if self.t and t<self.t[-1]:raise ValueError("CLOCK_INVERSION")
        j=len(self.t)
        session_change=bool(self.t) and session_id!=self.session
        gap=bool(self.t) and t-self.t[-1]>1800
        if session_change or gap:
            for st in self.states.values():
                self._close(st,"session" if session_change else "gap")
                st["candidates"]=[]
            self.segment_start=j
        self.session=session_id
        self.h.append(int(h));self.l.append(int(l));self.c.append(int(c));self.t.append(t)
        self.minus_l.append(-int(l));self.minus_h.append(-int(h))
        new=[];p=self.p
        for kind in (1,-1):
            x=self.h if kind==1 else self.minus_l
            y=self.l if kind==1 else self.minus_h
            st=self.states[kind]
            if st["last"] is not None and (
                (x[j]>st["P"] and j>st["last"]) or j-st["last"]>p["max_gap"]):
                self._close(st,"break_or_timeout")
                st["candidates"]=[]
            if p["confirmation_mode"]=="precio":
                confirmed=[];alive=[]
                for q in st["candidates"]:
                    if j>=q+60 or x[j]>x[q]:continue
                    if x[q]-y[j]>=p["confirm_ticks"]:confirmed.append(q)
                    else:alive.append(q)
                st["candidates"]=alive
            else:
                q=j-p["w"]
                confirmed=([q] if q-p["w"]>=self.segment_start and
                    all(x[q]>=x[q-d] and x[q]>=x[q+d] for d in range(1,p["w"]+1))
                    else [])
            for q in sorted(confirmed):
                event=self._accept(kind,q,j)
                if event is not None:new.append(event)
            if p["confirmation_mode"]=="precio" and j-p["w"]>=self.segment_start and \
                all(x[j]>=x[j-d] for d in range(1,p["w"]+1)):
                st["candidates"].append(j)
        return new

    def finish_diagnostic(self):
        """EOF censors partial blocks; it never confirms a pending price peak."""
        for st in self.states.values():
            self._close(st,"eof");st["candidates"]=[]
        return dict(self.stats)