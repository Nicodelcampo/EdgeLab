"""Auditoría de datos de ticks, descriptiva: cuenta e identifica defectos; NO modifica ni excluye nada.
Cualquier regla de exclusión se escribe y se pre-registra aparte, antes de aplicarse (no se elige mirando qué sesiones mejoran un resultado)."""
from __future__ import annotations
import datetime as dt
import numpy as np,pandas as pd
from .data import MIN,tdate_ordinal

CORE_START,CORE_END=8*60+30,15*60       # minutos CT de la franja líquida
def _iso(o:int)->str:return dt.date.fromordinal(int(o)).isoformat()

def tick_level(tk:dict,acc:dict|None,tick_size_note:str="")->dict:
    """Controles sobre los trades (ya ordenados): precios, libro, volumen, saltos y repeticiones."""
    ts=tk["ts_utc_ns"];px=tk["price_ticks"];bid=tk["bid_ticks"];ask=tk["ask_ticks"];vol=tk["volume"];n=len(ts);out={"trades":int(n)}
    if acc:out["file"]={k:v for k,v in acc.items() if not k.startswith("_")}
    sp=(ask-bid).astype(np.float64)
    out["price_le_0"]=int((px<=0).sum());out["bid_or_ask_le_0"]=int(((bid<=0)|(ask<=0)).sum());out["crossed_book"]=int((bid>ask).sum());out["locked_book"]=int((bid==ask).sum())
    out["trade_outside_book"]=int(((px<bid)|(px>ask)).sum());out["volume_le_0"]=int((vol<=0).sum())
    wide=sp>=100
    if wide.any():
        vals,cnt=np.unique(sp[wide],return_counts=True);o=np.argsort(-cnt)[:5]
        hrs=pd.DatetimeIndex(ts[wide].astype("datetime64[ns]")).tz_localize("UTC").tz_convert("America/Chicago").hour
        out["wide_spread_ge_100"]={"n":int(wide.sum()),"most_frequent_values":[{"ticks":float(vals[i]),"n":int(cnt[i])} for i in o],"by_hour_ct":{int(h):int(n) for h,n in zip(*np.unique(hrs,return_counts=True))}}
    out["spread_ticks"]={"p50":float(np.percentile(sp,50)),"p99":float(np.percentile(sp,99)),"p99.9":float(np.percentile(sp,99.9)),"max":float(sp.max()),"ge_20_ticks":int((sp>=20).sum())}
    out["volume"]={"p99.99":float(np.percentile(vol,99.99)),"max":int(vol.max())}
    dts=np.diff(ts);dp=np.abs(np.diff(px)).astype(np.float64);near=dts<60_000_000_000;jm=np.where(near,dp,0.)
    top=np.argsort(-jm)[:5];out["jumps_within_60s_ticks"]={"p99.99":float(np.percentile(jm[near],99.99)) if near.any() else 0.,"max":float(jm.max()) if len(jm) else 0.,
        "top5":[{"ts_utc":str(pd.Timestamp(int(ts[i+1]),tz="UTC")),"ticks":float(jm[i])} for i in top]}
    same=(dts==0)&(np.diff(px)==0)&(np.diff(bid)==0)&(np.diff(ask)==0)&(np.diff(vol)==0)&(np.diff(tk["aggressor"])==0)
    out["consecutive_identical_rows"]=int(same.sum());out["same_ms_timestamp_rows"]=int((dts==0).sum())
    return out

def session_level(bars:dict,sessions_hint:set[int]|None=None)->dict:
    """Estadística por sesión de trading a partir de las barras de 1 min (cada barra lleva el nº de ticks)."""
    t=bars["t"];td=tdate_ordinal(t);u,st=np.unique(td,return_index=True);en=np.r_[st[1:],len(t)]
    loc=pd.DatetimeIndex(t.astype("datetime64[ns]")).tz_localize("UTC").tz_convert("America/Chicago");mod=(loc.hour*60+loc.minute).to_numpy()
    nb=en-st;ticks=np.add.reduceat(bars["n"],st);vol=np.add.reduceat(bars["vol"],st)
    first=mod[st];last=mod[en-1];rows=[]
    gap=np.r_[0,np.diff(t)]//MIN
    for k,d in enumerate(u):
        sl=slice(st[k],en[k]);g=gap[sl].copy();g[0]=0;core=(mod[sl]>=CORE_START)&(mod[sl]<=CORE_END);gc=g[core]
        rows.append({"td":int(d),"date":_iso(d),"bars":int(nb[k]),"ticks":int(ticks[k]),"volume":float(vol[k]),"first_ct_min":int(first[k]),"last_ct_min":int(last[k]),
                     "max_gap_min":int(g.max()),"max_core_gap_min":int(gc.max()) if len(gc) else 0})
    med_t=float(np.median([r["ticks"] for r in rows])) if rows else 0.;flags=[]
    for r in rows:
        f=[]
        if r["ticks"]<0.25*med_t:f.append("pocos_ticks(<25% de la mediana)")
        if r["last_ct_min"]<15*60+55:f.append("termina_antes_de_15:55_CT")
        if r["first_ct_min"]>18*60 and r["first_ct_min"]<CORE_START:f.append("empieza_despues_de_18:00_CT")
        if r["max_core_gap_min"]>=5:f.append(f"hueco_{r['max_core_gap_min']}min_en_08:30-15:00_CT")
        if f:flags.append({"td":r["td"],"date":r["date"],"flags":f,"ticks":r["ticks"],"bars":r["bars"]})
    return {"sessions":len(rows),"median_ticks_per_session":med_t,"flagged":flags,"n_flagged":len(flags),"per_session":rows}

def asset_level(daily:dict,bars:dict,order:list[str],segs,elig:dict,tick_size_note:str="")->dict:
    """Calendario, rolls y elegibilidad de la serie continua."""
    alld=sorted({d for c in order for d in daily[c]});present=set(alld);lo,hi=alld[0],alld[-1]
    from pandas.tseries.holiday import USFederalHolidayCalendar
    from dateutil.easter import easter
    hol={d.date().toordinal() for d in USFederalHolidayCalendar().holidays(_iso(lo),_iso(hi))}
    gf=set()
    for y in range(dt.date.fromordinal(lo).year,dt.date.fromordinal(hi).year+1):gf.add((easter(y)-dt.timedelta(days=2)).toordinal())
    miss=[]
    for d in range(lo,hi+1):
        if dt.date.fromordinal(d).weekday()<5 and d not in present:miss.append({"date":_iso(d),"note":"feriado federal de EE.UU." if d in hol else ("Viernes Santo" if d in gf else "SIN DATOS (no es feriado conocido)")})
    rolls=[]
    for k in range(1,len(segs)):
        r,d0,_=segs[k];old=order[segs[k-1][0]];new=order[r];prev=[d for d in range(d0-1,d0-8,-1) if d in daily[old] and d in daily[new]]
        rec={"from":old,"to":new,"first_date":_iso(d0)}
        if prev:
            p=prev[0];to=tdate_ordinal(bars_c(bars,old)["t"]);tn=tdate_ordinal(bars_c(bars,new)["t"])
            rec.update({"prev_session":_iso(p),"volume_old":daily[old][p],"volume_new":daily[new][p]})
            io=np.where(to==p)[0];inn=np.where(tn==p)[0]
            if len(io) and len(inn):
                common=np.intersect1d(bars_c(bars,old)["t"][io],bars_c(bars,new)["t"][inn])
                if len(common):
                    c_old=bars_c(bars,old)["c"][np.searchsorted(bars_c(bars,old)["t"],common[-1])];c_new=bars_c(bars,new)["c"][np.searchsorted(bars_c(bars,new)["t"],common[-1])]
                    rec["price_gap_ticks_new_minus_old"]=int(c_new-c_old);rec["last_common_minute_utc"]=str(pd.Timestamp(int(common[-1]),tz="UTC"))
        rolls.append(rec)
    ineligible=[_iso(d) for r,d0,d1 in segs for d in range(d0,d1+1) if d in daily[order[r]] and d not in elig]
    return {"first_date":_iso(lo),"last_date":_iso(hi),"trade_dates_with_data":len(present),"missing_weekdays":miss,"n_missing_without_known_reason":sum(1 for m in miss if m["note"].startswith("SIN")),
            "segments":[(order[r],_iso(a),_iso(b)) for r,a,b in segs],"rolls":rolls,"eligible_sessions":len(elig),"ineligible_low_volume":ineligible}

def bars_c(bars,c):return bars[c]
