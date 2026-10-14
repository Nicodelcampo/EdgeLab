#!/usr/bin/env python3
"""Etapa C con el dataset unificado de Dukascopy (enmienda C3): usa la misma función `one` de barrido_horario_etapa_c_spot.py, con ticks leídos del parquet.
Paso 1 (calibración de la fuente, spot vs GC, abril a junio de 2026) y Paso 2 (decisión, 2026-07-01 a 2026-09-30, UNA sola vez). Semilla 20261008."""
import sys,json,datetime as dt
from pathlib import Path
import numpy as np,pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]));sys.path.insert(0,str(Path(__file__).resolve().parent))
import barrido_horario_etapa_c_spot as C
from edgelab.discovery import cache as CA,pipeline as P,spec as S
OUT=Path("docs/research/barrido_horario_20261004")
TS=None
def load():
    global TS
    df=pd.read_parquet("/data/spot/xauusd_2026H.parquet");TS=(df["time_utc_ns"].to_numpy()//1_000_000,df["ask"].to_numpy(np.float64),df["bid"].to_numpy(np.float64))
def session_ticks(d):
    base=int(dt.datetime(d.year,d.month,d.day,7,tzinfo=C.UTC).timestamp())*1000;t,a,b=TS;i=np.searchsorted(t,base);j=np.searchsorted(t,base+5*3600_000)
    return (t[i:j],a[i:j],b[i:j]) if j>i else None
C.session_ticks=session_ticks
def run(lo,hi):
    R=[];d=lo
    while d<=hi:
        if d.weekday()<5:
            r=C.one(d)
            if r:R.append(r)
        d+=dt.timedelta(days=1)
    return R
def gc_side():
    asset=json.loads(Path("config/discovery/assets/GC.json").read_text());bars,rows,order,segs,elig,_,_=CA.load_cache(asset,"/data/cache/discovery")
    from edgelab.discovery import load_spec
    base=load_spec("config/discovery/families/f1_momentum.json");sp=base.__class__(**{**base.__dict__,"conditions":(S.Condition("mom_15","gt",0.),),"pairs":(),"include_none":True,"commission_ticks":asset["commission_usd_rt"]/asset["tick_value_usd"]});T=P.build(sp,None,bars,order,segs,elig,rows=rows)
    si=list(T.slots).index(415);hi=list(T.holds).index(15)
    k=T.cond_keys.index("mom_15:gt:0");out={}
    for i,dd in enumerate(T.dates):
        if np.isfinite(T.ns[i,si,hi]):out[dt.date.fromordinal(int(dd))]={"up":bool(T.masks[i,si,k]),"short":float(T.ns[i,si,hi])}
    return out
def main():
    load();res={}
    # ---- Paso 1: calibración de la fuente (abril a junio de 2026), antes de mirar la ventana de decisión
    g=gc_side();R1=[r for r in run(dt.date(2026,4,1),dt.date(2026,6,30)) if r["eligible"]];both=[(r,g[dt.date.fromisoformat(r["date"])]) for r in R1 if dt.date.fromisoformat(r["date"]) in g]
    agree=float(np.mean([r["up"]==x["up"] for r,x in both])) if both else float("nan");trig=[(r,x) for r,x in both if r["up"] and x["up"]]
    corr=float(np.corrcoef([r["short"] for r,_ in trig],[x["short"] for _,x in trig])[0,1]) if len(trig)>2 else float("nan")
    ok=bool(agree>=0.85 and corr>=0.6);res["paso1_calibracion"]={"sessions_both":len(both),"sign_agreement_up":agree,"threshold_agreement":0.85,"trades_both_trigger":len(trig),"corr_net_short":corr,"threshold_corr":0.6,"fuente_equivalente":ok}
    print(json.dumps(res["paso1_calibracion"],indent=1))
    if not ok:
        res["paso2_decision"]="NO INFORMATIVA: la fuente spot no es equivalente (regla del pre-registro); no se calcula ni se reporta la ventana de decisión";(OUT/"etapaC_spot_decision.json").write_text(json.dumps(res,indent=1));print(res["paso2_decision"]);return
    # ---- Paso 2: decisión, UNA sola vez
    R=run(dt.date(2026,7,1),dt.date(2026,9,30));el=[r for r in R if r["eligible"]];up=[r for r in el if r["up"]];dn=[r for r in el if (not r["up"]) and r["delta_usd"]<0]
    out={"window":["2026-07-01","2026-09-30"],"sessions_in_window":len(R),"eligible_sessions":len(el),"ineligible":[r["date"] for r in R if not r["eligible"]],"max_exit_delay_s":max(r["exit_delay_s"] for r in el),"median_spread_usd":float(np.median([r["spread_usd"] for r in el]))}
    adv=[(r["short"]-r["long"])/2 for r in up];z,p=C.signflip(adv);m=float(np.mean([r["short"] for r in up]))
    out["primary"]={"trades":len(up),"mean_net_ticks":m,"std_net_ticks":float(np.std([r["short"] for r in up])),"win_rate":float(np.mean([r["short"]>0 for r in up])),"z":z,"p_one_sided":p,"decision":"Replica" if (m>0 and p<=0.05) else ("No replica" if m<=0 else "Inconcluso")}
    adv=[(r["short"]-r["long"])/2 for r in el];z2,p2=C.signflip(adv,C.SEED+1)
    mon={}
    for r in up:mon.setdefault(r["date"][:7],[]).append(r["short"])
    out["secondary"]={"short_no_cond":{"trades":len(el),"mean_net_ticks":float(np.mean([r["short"] for r in el])),"z":z2,"p_one_sided":p2},"long_after_down":{"trades":len(dn),"mean_net_ticks":float(np.mean([r["long"] for r in dn])) if dn else None},"mean_net_by_month_primary":{k:{"trades":len(v),"mean":float(np.mean(v))} for k,v in sorted(mon.items())}}
    res["paso2_decision"]=out;(OUT/"etapaC_spot_decision.json").write_text(json.dumps(res,indent=1));print(json.dumps(out,indent=1))
if __name__=="__main__":main()
