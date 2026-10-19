#!/usr/bin/env python3
"""EMA 200/500/2000 de MGC reproducida en XAU/USD spot (enmienda P1 §4.2): prueba primaria T2 (información direccional bruta por horizonte, sin SL/TP).
Muestra spot 2022-07-01 a 2025-10-07 (anterior al primer día de MGC usado, 2025-10-08). Barras de N=13 eventos de spot (N elegido por KS en el solape: equivalence_spot_vs_mgc.json),
señal de `ema_cross_signals`, entrada en el tick siguiente al cierre de barra, retorno = dirección × (mid(t+h) − mid(entrada)) en ticks de 0,1 USD, h ∈ {15m,30m,1h,2h,4h},
truncado al fin de la sesión (16:00 CT). Nulo: dirección sorteada por sesión, 200.000 sorteos, semilla 20261012, máximo de z sobre 5 horizontes, umbral 0,05.
LÍMITE DECLARADO: la equivalencia de formación de barras con MGC dio SOLO_PRECIO (RESULTADO_EQUIVALENCIA.md); el spot dispara ≈ 1,7 veces más señales y su momento no coincide."""
import sys,json
from pathlib import Path
import numpy as np,pandas as pd,pyarrow.parquet as pq,pyarrow.compute as pc
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from edgelab.equivalence import ema_cross_signals
from edgelab.discovery.data import tdate_ordinal
from edgelab.discovery.pipeline import session_end_ns
N=13;NSIM=200_000;SEED=20261012;HZ={"15m":15,"30m":30,"1h":60,"2h":120,"4h":240};TICK=0.1;MIN=60_000_000_000
LO=int(pd.Timestamp("2022-07-01",tz="UTC").value);HI=int(pd.Timestamp("2025-10-07 22:00",tz="UTC").value)      # 22:00 UTC = 17:00 CT del 2025-10-07: cierra la sesión anterior al 2025-10-08
def load():
    f=pq.ParquetFile("/data/spot/XAUUSD_ticks.parquet");T=[];M=[]
    for g in range(f.metadata.num_row_groups):
        t=f.read_row_group(g,columns=["time_utc_ns","bid","ask"]);ts=t.column("time_utc_ns").to_numpy()
        if ts[-1]<LO or ts[0]>=HI:continue
        k=(ts>=LO)&(ts<HI)
        if k.any():T.append(ts[k]);M.append(((t.column("bid").to_numpy()[k]+t.column("ask").to_numpy()[k])/2.0))
    return np.concatenate(T),np.concatenate(M)
def main():
    ts,mid=load();n=len(ts);ends=np.arange(N-1,n,N);close=mid[ends];i,d=ema_cross_signals(close,200,500,2000)
    ent=ends[i]+1;ok=ent<n;i,d,ent=i[ok],d[ok].astype(np.float64),ent[ok];td=tdate_ordinal(ts[ent]);send=session_end_ns(td);last=np.searchsorted(ts,send,"right")-1
    rets={}
    for k,m in HZ.items():
        j=np.minimum(np.searchsorted(ts,ts[ent]+m*MIN,side="left"),last);j=np.maximum(j,ent);rets[k]=d*(mid[j]-mid[ent])/TICK
    D=np.unique(td);inv=np.searchsorted(D,td);S={k:np.bincount(inv,weights=v,minlength=len(D)) for k,v in rets.items()};sdn={k:float(np.sqrt((S[k]**2).sum())) for k in S}
    rng=np.random.default_rng(SEED);eps=rng.choice(np.array([-1.,1.]),size=(NSIM,len(D)));Z=np.stack([eps@S[k]/sdn[k] for k in HZ],axis=1);real={k:float(rets[k].sum()/sdn[k]) for k in HZ}
    out={"sample_utc":[str(pd.Timestamp(LO,tz="UTC")),str(pd.Timestamp(HI,tz="UTC"))],"ticks":int(n),"bar_events":N,"bars":int(len(ends)),"signals":int(len(ent)),"sessions_with_signals":int(len(D)),"horizons":{},"nsim":NSIM,"seed":SEED,"holdout_opened":False}
    for k_,k in enumerate(HZ):out["horizons"][k]={"mean_ticks":float(rets[k].mean()),"z":real[k],"p_one_sided":float((np.sum(Z[:,k_]>=real[k])+1)/(NSIM+1)),"long_mean":float(rets[k][d>0].mean()),"short_mean":float(rets[k][d<0].mean()),"long_n":int((d>0).sum()),"short_n":int((d<0).sum())}
    mx=max(real.values());out["max_z"]=mx;out["p_max"]=float((np.sum(Z.max(1)>=mx)+1)/(NSIM+1));out["decision"]="información direccional detectable (p_max ≤ 0,05)" if out["p_max"]<=0.05 else "sin información direccional distinguible del azar (p_max > 0,05)"
    yr={}
    for y in np.unique(pd.to_datetime(ts[ent]).year):
        m=pd.to_datetime(ts[ent]).year==y;yr[int(y)]={"signals":int(m.sum()),"mean_ticks_1h":float(rets["1h"][m].mean()),"mean_ticks_4h":float(rets["4h"][m].mean())}
    out["por_anio_descriptivo"]=yr
    Path("docs/research/equivalence_20261004/ema_spot_T2.json").write_text(json.dumps(out,indent=1));print(json.dumps(out,indent=1))
if __name__=="__main__":main()
