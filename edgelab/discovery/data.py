"""Ticks canónicos -> barras de 1 minuto -> serie continua causal con sesiones elegibles."""
from __future__ import annotations
import numpy as np,pandas as pd
MIN=60_000_000_000
AGG={"buy":1,"sell":-1}

def tdate_ordinal(t_ns:np.ndarray)->np.ndarray:
    """Fecha de trading CME (sesión 17:00-16:00 CT) como ordinal de Python, para sellos en ns UTC (el sello se corre 1 ns atrás)."""
    ix=pd.to_datetime(np.asarray(t_ns)-1,unit="ns",utc=True).tz_convert("America/Chicago")+pd.Timedelta(hours=7)
    return (ix.normalize().tz_localize(None).values.astype("datetime64[D]").astype(np.int64)+719163)

def load_ticks(path:str,cut_ns:int|None=None,audit:dict|None=None)->dict:
    """Lee un parquet canónico (ts_utc_ns, price_ticks, bid_ticks, ask_ticks, volume, aggressor, tick_type). Solo trades.
    `audit` (opcional, dict vacío): se llena con contadores de filas y de tipos para la auditoría; no cambia lo que se devuelve."""
    import pyarrow.parquet as pq,pyarrow.compute as pc
    f=pq.ParquetFile(path);cols=["ts_utc_ns","price_ticks","bid_ticks","ask_ticks","volume","aggressor","tick_type"]
    names=set(f.schema_arrow.names);extra=[c for c in("sequence","source_row") if c in names] if audit is not None else []
    acc={c:[] for c in cols[:-2]};ag=[]
    if audit is not None:audit.update({"rows":0,"tick_type":{},"aggressor":{},"sequence_not_increasing":0,"source_row_not_consecutive":0,"_last_seq":None,"_last_src":None})
    for g in range(f.metadata.num_row_groups):
        t=f.read_row_group(g,columns=cols+extra);m=pc.equal(t.column("tick_type"),"trade").to_numpy(zero_copy_only=False)
        for c in cols[:-2]:acc[c].append(t.column(c).to_numpy()[m])
        a=t.column("aggressor").to_pandas()[m];ag.append(a.map(AGG).fillna(0).astype(np.int8).to_numpy())
        if audit is not None:
            audit["rows"]+=t.num_rows
            for k,col in(("tick_type","tick_type"),("aggressor","aggressor")):
                for v,n in t.column(col).to_pandas().value_counts(dropna=False).items():audit[k][str(v)]=audit[k].get(str(v),0)+int(n)
            for c,key,cond in(("sequence","sequence_not_increasing",lambda d:d<=0),("source_row","source_row_not_consecutive",lambda d:d!=1)):
                if c in extra:
                    x=t.column(c).to_numpy();prev=audit["_last_seq" if c=="sequence" else "_last_src"]
                    x=np.r_[prev,x] if prev is not None else x;audit[key]+=int(cond(np.diff(x)).sum());audit["_last_seq" if c=="sequence" else "_last_src"]=int(x[-1])
    out={c:np.concatenate(v) for c,v in acc.items()};out["aggressor"]=np.concatenate(ag)
    if not np.all(np.diff(out["ts_utc_ns"])>=0):raise ValueError("ticks fuera de orden temporal")
    if cut_ns is not None:
        k=int(np.searchsorted(out["ts_utc_ns"],cut_ns))
        if audit is not None:audit["trades_after_cut_dropped"]=int(len(out["ts_utc_ns"])-k)
        out={c:v[:k] for c,v in out.items()}
    if audit is not None:audit.pop("_last_seq",None);audit.pop("_last_src",None)
    return out

def minute_bars(tk:dict)->dict:
    """Barras de 1 min con sello de CIERRE (convención NinjaTrader). Incluye volumen comprador/vendedor, VWAP y spread medio."""
    ts=tk["ts_utc_ns"];lab=(ts//MIN+1)*MIN;t,st=np.unique(lab,return_index=True);en=np.r_[st[1:],len(ts)]
    px=tk["price_ticks"].astype(np.int64);v=tk["volume"].astype(np.float64);ag=tk["aggressor"]
    sp=(tk["ask_ticks"]-tk["bid_ticks"]).astype(np.float64)
    return {"t":t,"o":px[st],"h":np.maximum.reduceat(px,st),"l":np.minimum.reduceat(px,st),"c":px[en-1],
            "vol":np.add.reduceat(v,st),"buy":np.add.reduceat(np.where(ag>0,v,0.),st),"sell":np.add.reduceat(np.where(ag<0,v,0.),st),
            "pv":np.add.reduceat(px*v,st),"spread":np.add.reduceat(sp,st)/(en-st),"n":(en-st).astype(np.float64)}

def daily_volume(bars:dict)->dict[int,float]:
    td=tdate_ordinal(bars["t"]);u,inv=np.unique(td,return_inverse=True);return dict(zip(u.tolist(),np.bincount(inv,weights=bars["vol"]).tolist()))

def continuous_segments(daily:dict[str,dict[int,float]],order:list[str],min_rel_volume:float=0.5):
    """Contrato líder = el de mayor volumen en la sesión completa ANTERIOR; monótono hacia adelante, sin retroceso ni ajuste de precios.
    Devuelve (segmentos [idx_contrato, d0, d1], sesiones elegibles {fecha: idx_contrato}). Elegible = volumen >= min_rel_volume x mediana del contrato como líder."""
    alld=sorted({d for c in order for d in daily[c]});cur=0;regime={};prev=None
    for d in alld:
        if prev is not None and cur+1<len(order) and daily[order[cur+1]].get(prev,0.)>daily[order[cur]].get(prev,0.)>0:cur+=1
        regime[d]=cur if daily[order[cur]].get(d,0.)>0 else None;prev=d
    segs=[]
    for d in alld:
        r=regime[d]
        if r is None:continue
        if segs and segs[-1][0]==r and d-segs[-1][2]<=5:segs[-1][2]=d
        else:segs.append([r,d,d])
    med={}
    for c_i,c in enumerate(order):
        vv=[daily[c][d] for r,d0,d1 in segs if r==c_i for d in range(d0,d1+1) if daily[c].get(d,0.)>0];med[c_i]=float(np.median(vv)) if vv else 0.
    elig={}
    for r,d0,d1 in segs:
        for d in range(d0,d1+1):
            if daily[order[r]].get(d,0.)>=min_rel_volume*med[r] and daily[order[r]].get(d,0.)>0:elig[d]=r
    return segs,elig
