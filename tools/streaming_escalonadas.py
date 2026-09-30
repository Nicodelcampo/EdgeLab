"""Causal completed-bar emission of the existing price-confirmed geometry."""
from __future__ import annotations
import math

PARAMS = dict(w=2, max_gap=15, max_step=25, min_pull=62, nmin=3,
              dmax=35, total_min=0, step_min=0, confirm_ticks=25)


def known_pivot(x, q, w):
    return q >= w and q+w < len(x) and all(
        x[q] >= x[q-d] and x[q] >= x[q+d] for d in range(1,w+1))


def backfill(pk, x, t, p):
    pk=list(pk)
    while True:
        first=pk[0];best=None
        for q in range(first-1,max(first-p["max_gap"],0)-1,-1):
            if t[q+1]-t[q]>1800:break
            if not known_pivot(x,q,p["w"]):continue
            step=x[q]-x[first]
            if -1e-9<=step<=p["max_step"] and max(x[q+1:first],default=-1e18)<=x[q]+1e-9:
                best=q;break
        if best is None:return pk
        pk=[best]+pk


class PriceConfirmed:
    """Prices are integer ticks. No final-series geometry leaks into an event."""
    def __init__(self, params=None):
        self.p=dict(PARAMS if params is None else params)
        self.h=[];self.l=[];self.c=[];self.t=[]
        self.minus_l=[];self.minus_h=[]
        self.states={s:dict(candidates=[],own=[],conf=[],P=None,emitted=False) for s in (1,-1)}
        self.events=[]

    def append(self,h,l,c,t):
        if not all(math.isfinite(float(v)) for v in (h,l,c,t)):raise ValueError("NONFINITE_BAR")
        if h<l or not l<=c<=h:raise ValueError("OHLC_FAIL")
        if self.t and t<self.t[-1]:raise ValueError("CLOCK_INVERSION")
        self.h.append(h);self.l.append(l);self.c.append(c);self.t.append(t)
        self.minus_l.append(-l);self.minus_h.append(-h)
        j=len(self.t)-1;new=[];p=self.p
        for kind in (1,-1):
            x=self.h if kind==1 else self.minus_l
            y=self.l if kind==1 else self.minus_h
            st=self.states[kind]
            gap=j>0 and self.t[j]-self.t[j-1]>1800
            if st["own"] and (gap or (x[j]>st["P"]+1e-9 and j>st["own"][-1])
                              or j-st["own"][-1]>p["max_gap"]):
                st["own"]=[];st["conf"]=[];st["P"]=None;st["emitted"]=False
            confirmed=[];alive=[]
            for q in st["candidates"]:
                if gap or j>=q+60 or x[j]>x[q]+1e-9:continue
                if x[q]-y[j]>=p["confirm_ticks"]-1e-9:confirmed.append(q)
                else:alive.append(q)
            st["candidates"]=alive
            for q in sorted(confirmed):
                if st["own"] and q<=st["own"][-1]:continue
                if not st["own"]:
                    st["own"]=[q];st["conf"]=[j];st["P"]=x[q];st["emitted"]=False
                else:
                    prior=st["own"][-1]
                    pull=st["P"]-min(y[prior+1:q],default=st["P"])
                    step=st["P"]-x[q]
                    if x[q]<=st["P"]+1e-9 and step<=p["max_step"] and pull>=p["min_pull"]:
                        st["own"].append(q);st["conf"].append(j);st["P"]=x[q]
                if len(st["own"])>=p["nmin"] and not st["emitted"]:
                    pk=backfill(st["own"],x,self.t,p)
                    passes=(pk[-1]-pk[0]<=p["dmax"] and
                            abs(x[pk[-1]]-x[pk[0]])>=p["total_min"]-1e-9 and
                            max((abs(x[b]-x[a]) for a,b in zip(pk,pk[1:])),default=0)>=p["step_min"]-1e-9)
                    if passes:
                        level=self.h[q] if kind==1 else self.l[q]
                        event={"id":f'{"H" if kind==1 else "L"}:{st["own"][0]}',
                               "kind":"H" if kind==1 else "L","side":-kind,
                               "det_i":j,"own_first_i":st["own"][0],
                               "det_nivel_tick":level,
                               "det_precio_tick":level-kind*p["confirm_ticks"],
                               "picos_known":list(pk),"available_bar_i":j}
                        self.events.append(event);new.append(event);st["emitted"]=True
            # q=j is only eligible for confirmation in a later bar.
            if j>=p["w"] and all(x[j]>=x[j-d] for d in range(1,p["w"]+1)):
                st["candidates"].append(j)
        return new