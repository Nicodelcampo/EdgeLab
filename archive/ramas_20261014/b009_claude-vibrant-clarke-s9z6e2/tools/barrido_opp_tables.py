"""LOCAL ONLY. Independent-opportunity outcome tables for ANY (weekday, slot, hold, filter, direction), same timing semantics as the replica.
For each CT calendar date D and each 15-minute slot: sign of the recent price change, and net ticks (book fills / bar-open fills) for long & short at each hold."""
import numpy as np,datetime as dt,pandas as pd
from zoneinfo import ZoneInfo
from simple_calendar import SimpleCalendar
CHI=ZoneInfo('America/Chicago');UTC=dt.timezone.utc
MIN=60_000_000_000;HOLDS=(15,30,60,120);SLOTS=[h*100+m for h in range(24) for m in (0,15,30,45)]
cal=SimpleCalendar()
def build_table(t,c,ts,bid,ask,px,date_lo,date_hi,session_filter):
    """t,c: 1-min bar labels(ns)/closes(ticks); ts,bid,ask,px: tick arrays; dates are python date ordinals (CT calendar days).
    session_filter(label_ns)->bool says whether b1 belongs to the segment's sessions."""
    rows=[];ordinals=range(date_lo,date_hi+1)
    base=[];meta=[]
    for o in ordinals:
        d=dt.date.fromordinal(o)
        if d.weekday()>=5:continue
        for si,hm in enumerate(SLOTS):
            B=dt.datetime(d.year,d.month,d.day,hm//100,hm%100,tzinfo=CHI).astimezone(UTC)
            base.append(int(B.timestamp())*10**9);meta.append((o,d.isoweekday(),si))
    base=np.array(base,dtype=np.int64);b1_lab=base+MIN
    i1=np.searchsorted(t,b1_lab);ok=(i1<len(t)-2)
    ok&=np.where(ok,t[np.minimum(i1,len(t)-1)]==b1_lab,False)
    n=len(base);res=dict(date=np.array([m[0] for m in meta]),dow=np.array([m[1] for m in meta]),slot=np.array([m[2] for m in meta]),
        valid=np.zeros(n,bool),sign=np.zeros(n,np.int8),noref=np.zeros(n,bool),b1=b1_lab,b2=np.zeros(n,np.int64))
    idx=np.where(ok)[0]
    # segment membership
    mem=np.array([session_filter(int(b1_lab[k])) for k in idx],bool);idx=idx[mem]
    i1v=i1[idx];b2=t[i1v+1];res['b2'][idx]=b2
    ref=np.searchsorted(t,b1_lab[idx]-15*MIN,'right')-1
    has=ref>=0;delta=np.where(has,c[i1v]-c[np.maximum(ref,0)],0)
    res['sign'][idx]=np.sign(delta);res['noref'][idx]=~has
    ie=np.searchsorted(ts,b2)
    for h in HOLDS:
        x=np.searchsorted(t,b2+h*MIN,'left');okx=x<len(t);tx=t[np.minimum(x,len(t)-1)]
        ix=np.searchsorted(ts,tx);okt=okx&(ie<len(ts))&(ix<len(ts))
        # session guard: remaining minutes from b1 label to session end must be >= hold
        rem=np.array([ ( (cal.session_end(dt.datetime.fromtimestamp(int(l)/1e9,UTC)) or dt.datetime.fromtimestamp(int(l)/1e9,UTC))-dt.datetime.fromtimestamp(int(l)/1e9,UTC)).total_seconds()/60 for l in b1_lab[idx]])
        g=okt&(rem>=h)
        ie_=np.minimum(ie,len(ts)-1);ix_=np.minimum(ix,len(ts)-1)
        res[f'valid{h}']=np.zeros(n,bool);res[f'valid{h}'][idx]=g
        for nm in ('long','short','long_bar','short_bar'):res[f'{nm}{h}']=np.full(n,np.nan);
        res[f'long{h}'][idx]=np.where(g,bid[ix_]-ask[ie_],np.nan)
        res[f'short{h}'][idx]=np.where(g,bid[ie_]-ask[ix_],np.nan)
        res[f'long_bar{h}'][idx]=np.where(g,px[ix_]-px[ie_],np.nan)
        res[f'short_bar{h}'][idx]=np.where(g,px[ie_]-px[ix_],np.nan)
    res['valid']=res['valid15']|res['valid30']|res['valid60']|res['valid120']
    return res
