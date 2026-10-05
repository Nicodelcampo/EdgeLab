#!/usr/bin/env python3
"""Enmienda P1 (REVISION_EMBUDO_DISCOVERY_Y_PLAN_ORO_20261004.md §3.2/§4): H1 (celda congelada) y H2 (corto sin condición) a las 04:15 CT sobre XAU/USD spot,
muestra nueva 2022-07-01 a 2025-07-31. Nulo de dirección por sesión, 20.000 sorteos, semilla 20261011, unilateral, Holm sobre H1 y H2. Una sola corrida."""
import sys,json,datetime as dt
from pathlib import Path
import numpy as np,pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parent))
import barrido_horario_etapa_c_spot as C
from zoneinfo import ZoneInfo
SEED=20261011;OUT=Path("docs/research/barrido_horario_20261004")
df=pd.read_parquet("/data/spot/xauusd_0712utc_2022_2025.parquet");t=df["time_utc_ns"].to_numpy()//1_000_000;A=df["ask"].to_numpy(np.float64);B=df["bid"].to_numpy(np.float64)
def session_ticks(d):
    base=int(dt.datetime(d.year,d.month,d.day,7,tzinfo=C.UTC).timestamp())*1000;i=np.searchsorted(t,base);j=np.searchsorted(t,base+5*3600_000);return (t[i:j],A[i:j],B[i:j]) if j>i else None
C.session_ticks=session_ticks
def holm(p):
    o=np.argsort(p);n=len(p);adj=np.empty(n);run=0.
    for r,i in enumerate(o):run=max(run,min(1.,(n-r)*p[i]));adj[i]=run
    return adj
def season(d):return "verano_EEUU" if dt.datetime(d.year,d.month,d.day,12,tzinfo=ZoneInfo("America/Chicago")).utcoffset()==dt.timedelta(hours=-5) else "invierno_EEUU"
def main():
    R=[];d=dt.date(2022,7,1)
    while d<=dt.date(2025,7,31):
        if d.weekday()<5:
            r=C.one(d)
            if r:R.append(r)
        d+=dt.timedelta(days=1)
    el=[r for r in R if r["eligible"]];up=[r for r in el if r["up"]];dn=[r for r in el if (not r["up"]) and r["delta_usd"]<0]
    out={"window":["2022-07-01","2025-07-31"],"weekdays_with_data":len(R),"eligible_sessions":len(el),"ineligible_n":len(R)-len(el),"max_exit_delay_s":max(r["exit_delay_s"] for r in el),"median_spread_usd":float(np.median([r["spread_usd"] for r in el]))}
    a1=[(r["short"]-r["long"])/2 for r in up];z1,p1=C.signflip(a1,SEED);a2=[(r["short"]-r["long"])/2 for r in el];z2,p2=C.signflip(a2,SEED)
    ad=holm(np.array([p1,p2]));m1=float(np.mean([r["short"] for r in up]));m2=float(np.mean([r["short"] for r in el]))
    out["H1_celda_congelada"]={"trades":len(up),"mean_net_ticks":m1,"std":float(np.std([r["short"] for r in up])),"win_rate":float(np.mean([r["short"]>0 for r in up])),"z":z1,"p_one_sided":p1,"p_holm":float(ad[0]),"decision":"Replica" if (m1>0 and ad[0]<=0.05) else "No replica"}
    out["H2_corto_sin_condicion"]={"trades":len(el),"mean_net_ticks":m2,"std":float(np.std([r["short"] for r in el])),"win_rate":float(np.mean([r["short"]>0 for r in el])),"z":z2,"p_one_sided":p2,"p_holm":float(ad[1]),"decision":"Replica" if (m2>0 and ad[1]<=0.05) else "No replica"}
    def grp(rows,keyf,field="short"):
        g={}
        for r in rows:g.setdefault(keyf(r),[]).append(r[field])
        return {k:{"trades":len(v),"mean":float(np.mean(v))} for k,v in sorted(g.items())}
    dd=lambda r:dt.date.fromisoformat(r["date"])
    out["descriptivo"]={"H1_por_anio":grp(up,lambda r:r["date"][:4]),"H2_por_anio":grp(el,lambda r:r["date"][:4]),"H1_por_estacion":grp(up,lambda r:season(dd(r))),"H2_por_estacion":grp(el,lambda r:season(dd(r))),
        "largo_tras_bajada":{"trades":len(dn),"mean_net_ticks":float(np.mean([r["long"] for r in dn])) if dn else None},"H2_largo_sin_condicion_espejo":float(np.mean([r["long"] for r in el]))}
    (OUT/"etapaP1_H1H2.json").write_text(json.dumps(out,indent=1));print(json.dumps(out,indent=1))
if __name__=="__main__":main()
