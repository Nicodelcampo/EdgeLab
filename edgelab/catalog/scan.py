"""Escaneo de un parquet de ticks en una sola pasada: esquema, rango, tipos de tick, y un perfil por minuto (etiqueta de cierre, nº de trades, volumen)
del que salen las estadísticas por sesión de trading. No modifica nada y no guarda ticks."""
from __future__ import annotations
import numpy as np
from ..discovery.data import MIN,tdate_ordinal

TS_CANDIDATES=("ts_utc_ns","timestamp_ns","ts_ns","ts","time_utc_ns")

def scan_parquet(path:str)->dict:
    import pyarrow.parquet as pq,pyarrow.compute as pc
    f=pq.ParquetFile(path);names=list(f.schema_arrow.names);out={"columns":names,"rows":int(f.metadata.num_rows),"row_groups":int(f.metadata.num_row_groups),"schema":{n:str(f.schema_arrow.field(n).type) for n in names}}
    md=f.schema_arrow.metadata or {};out["parquet_metadata_keys"]=sorted(k.decode() for k in md.keys())[:20]
    ts_col=next((c for c in TS_CANDIDATES if c in names),None)
    if ts_col=="time_utc_ns" and "bid_close" in names:return _scan_m1(f,out)       # barras M1 bid/ask (p. ej. Dukascopy)
    pcol="price_ticks" if "price_ticks" in names else ("last" if "last" in names else None)
    quote_only=pcol is None and "bid" in names and "ask" in names               # ticks de cotización sin operaciones (spot)
    if quote_only:pcol="mid"
    if ts_col is None or pcol is None:out["recognized"]=False;return out
    out["price_column"]=pcol;bcol,acol=("bid_ticks","ask_ticks") if "bid_ticks" in names else ("bid","ask")
    out["recognized"]=True;has_tt="tick_type" in names;has_c="contract" in names;has_ag="aggressor" in names;has_v="volume" in names;has_ba=bcol in names and acol in names
    cols=[ts_col]+([] if quote_only else [pcol])+(["volume"] if has_v else [])+(["tick_type"] if has_tt else [])+(["contract"] if has_c else [])+([bcol,acol] if has_ba else [])+(["aggressor"] if has_ag else [])
    labs=[];cnts=[];vols=[];tt={};contracts=set();ag={};pxmin=None;pxmax=None;tmin=None;tmax=None;nontrade=0;badba=0;nobook=0;unsorted=0;prev=None;nrows=0;ntr=0
    for g in range(f.metadata.num_row_groups):
        t=f.read_row_group(g,columns=cols);nrows+=t.num_rows
        if has_tt:
            for v,n in zip(*np.unique(np.asarray(pc.fill_null(t.column("tick_type"),"NULL").to_pylist(),dtype=object).astype(str),return_counts=True)):tt[str(v)]=tt.get(str(v),0)+int(n)
            m=pc.equal(t.column("tick_type"),"trade").to_numpy(zero_copy_only=False)
        else:m=np.ones(t.num_rows,bool)
        if has_c:contracts.update(str(x) for x in pc.unique(t.column("contract")).to_pylist())
        if quote_only and "mid" not in t.column_names:pass
        tc=t.column(ts_col)
        if "timestamp" in str(tc.type):tc=tc.cast("int64");out["timestamp_type"]=str(f.schema_arrow.field(ts_col).type)
        ts=tc.to_numpy()[m]
        if len(ts)==0:continue
        if prev is not None and ts[0]<prev:unsorted+=1
        unsorted+=int((np.diff(ts)<0).sum());prev=int(ts[-1]);px=((t.column("bid").to_numpy()[m]+t.column("ask").to_numpy()[m])/2.0) if quote_only else t.column(pcol).to_numpy()[m];ntr+=len(ts)
        pxmin=float(px.min()) if pxmin is None else min(pxmin,float(px.min()));pxmax=float(px.max()) if pxmax is None else max(pxmax,float(px.max()))
        tmin=int(ts.min()) if tmin is None else min(tmin,int(ts.min()));tmax=int(ts.max()) if tmax is None else max(tmax,int(ts.max()))
        vol=t.column("volume").to_numpy()[m].astype(np.float64) if has_v else np.ones(len(ts))
        lab=(ts//MIN+1);u,inv=np.unique(lab,return_inverse=True);labs.append(u*MIN);cnts.append(np.bincount(inv).astype(np.int64));vols.append(np.bincount(inv,weights=vol))
        if has_ba:
            b=t.column(bcol).to_numpy()[m];a=t.column(acol).to_numpy()[m];badba+=int((b>a).sum());nobook+=int(((b<=0)|(a<=0)).sum())
        if has_ag:
            for v,n in zip(*np.unique(np.asarray(t.column("aggressor").to_pylist(),dtype=object).astype(str)[m],return_counts=True)):ag[str(v)]=ag.get(str(v),0)+int(n)
    out.update({"quote_only":bool(quote_only),"trades":int(ntr),"tick_types":tt,"contracts_in_file":sorted(contracts),"aggressor":ag,"price_ticks_min":pxmin,"price_ticks_max":pxmax,"ts_utc_first":tmin,"ts_utc_last":tmax,
                "unsorted_events":int(unsorted),"crossed_book":int(badba),"no_book_le_0":int(nobook),"has_book":bool(has_ba),"has_aggressor":bool(has_ag)})
    if not labs:out["days"]=[];return out
    L=np.concatenate(labs);C=np.concatenate(cnts);V=np.concatenate(vols);uL,inv=np.unique(L,return_inverse=True);C=np.bincount(inv,weights=C);V=np.bincount(inv,weights=V);td=tdate_ordinal(uL)
    days=[]
    for d in np.unique(td):
        k=td==d;days.append({"td":int(d),"minutes":int(k.sum()),"trades":int(C[k].sum()),"volume":float(V[k].sum()),"first_ts":int(uL[k][0]-MIN),"last_ts":int(uL[k][-1])})
    out["days"]=days;return out


def _scan_m1(f,out:dict)->dict:
    """Barras M1: una fila por minuto con inicio en UTC. Reporta por sesión el nº de barras y las que tienen volumen > 0."""
    import numpy as np
    t=f.read(columns=["time_utc_ns","bid_vol","ask_vol"]);ts=t.column("time_utc_ns").to_numpy();vol=t.column("bid_vol").to_numpy()+t.column("ask_vol").to_numpy()
    lab=ts+MIN;td=tdate_ordinal(lab);days=[]
    for d in np.unique(td):
        k=td==d;days.append({"td":int(d),"minutes":int(k.sum()),"trades":int((vol[k]>0).sum()),"volume":float(vol[k].sum()),"first_ts":int(ts[k][0]),"last_ts":int(ts[k][-1])})
    out.update({"recognized":True,"kind":"m1_bars","trades":int(len(ts)),"tick_types":{},"contracts_in_file":[],"aggressor":{},"price_ticks_min":None,"price_ticks_max":None,"ts_utc_first":int(ts[0]),"ts_utc_last":int(ts[-1]),
                "unsorted_events":int((np.diff(ts)<0).sum()),"crossed_book":0,"no_book_le_0":0,"has_book":True,"has_aggressor":False,"quote_only":True,"days":days});return out
