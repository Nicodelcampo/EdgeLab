from __future__ import annotations
from dataclasses import dataclass
import numpy as np
@dataclass
class BarSeries:
    start_ns:np.ndarray; end_ns:np.ndarray; open_t:np.ndarray; high_t:np.ndarray; low_t:np.ndarray; close_t:np.ndarray; volume:np.ndarray; tick_size:float; kind:str; param:int; tick_bar_idx:np.ndarray
    def __len__(self): return len(self.end_ns)
def session_ids(ts_ns):
    import pandas as pd
    idx=pd.to_datetime(np.asarray(ts_ns,dtype='int64'),unit='ns',utc=True).tz_convert('America/Chicago')
    dias=np.asarray(idx.normalize().view('int64'))//86_400_000_000_000
    return dias+(np.asarray(idx.hour)>=17).astype(np.int64)
def _ohlc(ticks,starts,ends):
    n=len(starts); o=np.empty(n,np.int64); h=np.empty(n,np.int64); lo=np.empty(n,np.int64); c=np.empty(n,np.int64); v=np.empty(n,np.float64); tbi=np.empty(len(ticks),np.int64)
    for b in range(n):
        i0,i1=int(starts[b]),int(ends[b]); p=ticks.price_ticks[i0:i1]
        o[b]=p[0]; c[b]=p[-1]; h[b]=p.max(); lo[b]=p.min(); v[b]=ticks.volume[i0:i1].sum(); tbi[i0:i1]=b
    return o,h,lo,c,v,tbi
def build_tick_bars(ticks,ticks_per_bar,reiniciar_por_sesion=True):
    n=len(ticks); N=int(ticks_per_bar)
    if reiniciar_por_sesion:
        ses=session_ids(ticks.ts_ns); ini=np.r_[0,np.flatnonzero(np.diff(ses))+1]; lens=np.diff(np.r_[ini,n]); base=np.repeat(ini,lens); local=(np.arange(n)-base)//N; offs=np.r_[0,np.cumsum((lens+N-1)//N)[:-1]]; bucket=local+np.repeat(offs,lens)
    else: bucket=np.arange(n)//N
    change=np.flatnonzero(np.diff(bucket))+1; starts=np.r_[0,change]; ends=np.r_[change,n]
    o,h,lo,c,v,tbi=_ohlc(ticks,starts,ends)
    return BarSeries(ticks.ts_ns[starts].astype(np.int64),ticks.ts_ns[ends-1].astype(np.int64),o,h,lo,c,v,ticks.tick_size,'tick',N,tbi)
@dataclass
class Footprints:
    ask:list; bid:list; total:list; n_quote:np.ndarray; n_rule:np.ndarray; has_quotes:bool
def build_footprints(ticks,bars):
    nb=len(bars); ask=[{} for _ in range(nb)]; bid=[{} for _ in range(nb)]; total=[{} for _ in range(nb)]; nq=np.zeros(nb,np.int64); nr=np.zeros(nb,np.int64); last=None; last_dir=0
    for i in range(len(ticks)):
        b=int(bars.tick_bar_idx[i]); p=int(ticks.price_ticks[i]); vol=float(ticks.volume[i]); aq=int(ticks.ask_ticks[i]); bq=int(ticks.bid_ticks[i]); side=0; byq=False
        if aq>0 and bq>0 and aq>=bq:
            if p>=aq: side,byq=1,True
            elif p<=bq: side,byq=-1,True
        if side==0:
            if last is not None: side=1 if p>last else (-1 if p<last else last_dir)
            if side==0: side=1
        last,last_dir=p,side
        if byq: nq[b]+=1
        else: nr[b]+=1
        m=ask[b] if side>0 else bid[b]; m[p]=m.get(p,0.0)+vol; total[b][p]=total[b].get(p,0.0)+vol
    return Footprints(ask,bid,total,nq,nr,True)
