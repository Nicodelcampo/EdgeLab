from __future__ import annotations
import numpy as np
from numba import njit

def tick_bars(ts:np.ndarray,px:np.ndarray,n:int,group:np.ndarray|None=None):
    """Barras de `n` eventos. `group` (p. ej. contrato o fecha de trading): las barras no cruzan un cambio de grupo y la cola incompleta se descarta.
    Devuelve (ts_cierre, cierre, grupo de cada barra)."""
    ends=[];g_out=[]
    if group is None:group=np.zeros(len(ts),np.int64)
    cuts=np.r_[0,np.flatnonzero(group[1:]!=group[:-1])+1,len(ts)]
    for a,b in zip(cuts[:-1],cuts[1:]):
        k=(b-a)//n
        if k:ends.append(a+n*np.arange(1,k+1)-1);g_out.append(np.full(k,group[a]))
    if not ends:return np.empty(0,np.int64),np.empty(0),np.empty(0,np.int64)
    e=np.concatenate(ends);return ts[e],px[e],np.concatenate(g_out)

def _ks(a:np.ndarray,b:np.ndarray)->float:
    a=np.sort(a);b=np.sort(b);g=np.concatenate([a,b]);return float(np.max(np.abs(np.searchsorted(a,g,"right")/len(a)-np.searchsorted(b,g,"right")/len(b))))

def match_bar_size(fut_ts:np.ndarray,spot_ts:np.ndarray,n_fut:int=25,candidates:np.ndarray|None=None,session_ns:int=86_400_000_000_000)->dict:
    """Elige cuántos eventos del sustituto forman una barra para que sus tiempos de formación se parezcan a los de la barra de `n_fut` eventos de futuros.
    Estima el punto de partida con la razón de eventos por día y refina con la distancia de Kolmogorov-Smirnov entre las duraciones (log) de las barras,
    calculada SOLO en el solape de tiempo. Las barras de futuros y del sustituto no son la misma cosa: esto iguala su ritmo, no su contenido."""
    lo=max(fut_ts[0],spot_ts[0]);hi=min(fut_ts[-1],spot_ts[-1]);f=fut_ts[(fut_ts>=lo)&(fut_ts<=hi)];s=spot_ts[(spot_ts>=lo)&(spot_ts<=hi)]
    if len(f)<10*n_fut or len(s)<n_fut:raise ValueError("solape insuficiente")
    base=n_fut*len(s)/len(f);cand=candidates if candidates is not None else np.unique(np.maximum(1,np.round(base*np.array([.5,.6,.7,.8,.9,1,1.1,1.25,1.5,1.75,2.])).astype(int)))
    df=np.diff(f[n_fut-1::n_fut]).astype(float);df=np.log(df[df>0]);best=None;rows=[]
    for n in cand:
        ds=np.diff(s[n-1::n]).astype(float);ds=np.log(ds[ds>0]);k=_ks(df,ds);rows.append({"n_spot":int(n),"ks":k,"median_bar_seconds_spot":float(np.exp(np.median(ds))/1e9)})
        if best is None or k<best["ks"]:best=rows[-1]
    return {"n_futures":n_fut,"n_spot_start_estimate":float(base),"best":best,"candidates":rows,"median_bar_seconds_futures":float(np.exp(np.median(df))/1e9),
            "events_per_day":{"futures":float(len(f)/max(1,(hi-lo)/session_ns)),"spot":float(len(s)/max(1,(hi-lo)/session_ns))}}

def sync_resample(bar_close_ns:np.ndarray,spot_ts:np.ndarray,spot_px:np.ndarray)->np.ndarray:
    """Precio del sustituto en el instante de cierre de cada barra de futuros (último valor <= instante). NaN si no hay dato previo."""
    i=np.searchsorted(spot_ts,bar_close_ns,"right")-1;out=np.where(i>=0,spot_px[np.maximum(i,0)],np.nan);return out

@njit(cache=True)
def _ema(x,span):
    o=np.empty(x.size);a=2./(span+1.);o[0]=x[0]
    for i in range(1,x.size):o[i]=a*x[i]+(1-a)*o[i-1]
    return o

def ema_cross_signals(close:np.ndarray,fast:int=200,mid:int=500,slow:int=2000,warmup:int|None=None,group:np.ndarray|None=None):
    """La señal de la EMA de MGC: la rápida cruza a la intermedia y la intermedia está del mismo lado que la lenta; decisión al cierre de la barra.
    Con `group` la EMA se reinicia en cada cambio (contrato) y se exige `warmup` barras (por omisión `slow`). Devuelve (índices de barra, dirección ±1)."""
    n=len(close);g=np.zeros(n,np.int64) if group is None else group;w=slow if warmup is None else warmup;idx=[];dr=[]
    cuts=np.r_[0,np.flatnonzero(g[1:]!=g[:-1])+1,n]
    for a,b in zip(cuts[:-1],cuts[1:]):
        c=close[a:b].astype(np.float64)
        if len(c)<=w+1:continue
        e1=_ema(c,fast);e2=_ema(c,mid);e3=_ema(c,slow)
        for i in range(max(1,w),len(c)-1):
            if e1[i]>e2[i] and e1[i-1]<=e2[i-1] and e2[i]>e3[i]:idx.append(a+i);dr.append(1)
            elif e1[i]<e2[i] and e1[i-1]>=e2[i-1] and e2[i]<e3[i]:idx.append(a+i);dr.append(-1)
    return np.array(idx,np.int64),np.array(dr,np.int8)

def signal_agreement(ts_a,dir_a,ts_b,dir_b,tol_s:float)->dict:
    """Emparejamiento uno a uno (misma dirección, a menos de `tol_s` segundos). Devuelve coincidencias, precisión y exhaustividad de B respecto de A."""
    tol=int(tol_s*1e9);ia=ib=0;m=0;opp=0
    while ia<len(ts_a) and ib<len(ts_b):
        d=ts_b[ib]-ts_a[ia]
        if abs(d)<=tol:
            if dir_a[ia]==dir_b[ib]:m+=1
            else:opp+=1
            ia+=1;ib+=1
        elif d<-tol:ib+=1
        else:ia+=1
    na,nb=len(ts_a),len(ts_b);p=m/nb if nb else 0.;r=m/na if na else 0.
    return {"signals_reference":na,"signals_proxy":nb,"matched_same_direction":m,"matched_opposite_direction":opp,"precision":p,"recall":r,"f1":(2*p*r/(p+r) if p+r else 0.)}

def outcome_agreement(ts_a,dir_a,px_a_ts,px_a,ts_b,dir_b,px_b_ts,px_b,hold_s:list[float],day_ns:int=86_400_000_000_000)->dict:
    """Resultado a horizonte fijo de TODAS las señales de cada serie, agregado por día: correlación diaria entre referencia y sustituto y media por señal.
    Es independiente del emparejamiento exacto de señales."""
    def run(ts,d,pts,px,h):
        t1=ts+int(h*1e9);i0=np.searchsorted(pts,ts,"right")-1;i1=np.searchsorted(pts,t1,"right")-1;ok=(i0>=0)&(i1>i0)&(t1<=pts[-1])
        return ts[ok],(d[ok]*(px[i1[ok]]-px[i0[ok]])).astype(float)
    out={}
    for h in hold_s:
        ta,ra=run(ts_a,dir_a,px_a_ts,px_a,h);tb,rb=run(ts_b,dir_b,px_b_ts,px_b,h)
        da=ta//day_ns;db=tb//day_ns;days=np.union1d(da,db)
        sa=np.array([ra[da==d].sum() for d in days]);sb=np.array([rb[db==d].sum() for d in days])
        c=float(np.corrcoef(sa,sb)[0,1]) if len(days)>2 and sa.std()>0 and sb.std()>0 else float("nan")
        out[str(int(h))]={"days":int(len(days)),"signals_reference":int(len(ra)),"signals_proxy":int(len(rb)),"mean_per_signal_reference":float(ra.mean()) if len(ra) else None,"mean_per_signal_proxy":float(rb.mean()) if len(rb) else None,"daily_pnl_correlation":c}
    return out
