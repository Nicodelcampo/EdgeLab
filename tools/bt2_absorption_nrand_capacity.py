import sys, json, pathlib, time, collections
import numpy as np
from datetime import datetime, timezone
sys.path.insert(0, r"C:\ProyectosQuant\EdgeLab")
from edgelab.bridge.indicators.bigtrap2absorption import run as run_abs, DEFAULTS
from tools.sweep_bigtrap2_tickframes import load_canonical_ticks
BASE=pathlib.Path(r"C:\Users\nicoc\OneDrive\Documentos\DataNT8")
CACHE=pathlib.Path(r"C:\Users\nicoc\AppData\Local\Temp\claude\C--Users-nicoc-OneDrive-Escritorio-Repositorios---Edges\89905be6-498d-439f-8be3-00dd77a7ceaa\scratchpad\b9cache152")
CACHE.mkdir(exist_ok=True)
CHAIN={"GC 02-26":("20251126","20260128"),"GC 04-26":("20260129","20260327"),
       "GC 06-26":("20260330","20260527"),"GC 08-26":("20260528","20260630")}
DST_O=int(datetime(2025,11,2,7,0,tzinfo=timezone.utc).timestamp())*10**9
DST_I=int(datetime(2026,3,8,8,0,tzinfo=timezone.utc).timestamp())*10**9
NS_H=3_600_000_000_000; H_TK=2000; H_S=900*10**9
def ctl(ts):  return ts + np.where((ts<DST_O)|(ts>=DST_I),-5,-6)*NS_H
def bins(ts): return ((((ctl(ts)//10**9)%86400)//60-1020)%1440)//30
def sesd(ts): return ((ctl(ts)+7*NS_H)//86_400_000_000_000).astype(np.int64)
def d2s(d):   return datetime.fromtimestamp(int(d)*86400,tz=timezone.utc).strftime("%Y%m%d")

for c,(d0,d1) in CHAIN.items():
    f=CACHE/f"{c.replace(' ','_')}_zones.npz"
    if f.exists(): print(f"[cache] zonas {c}",flush=True); continue
    t0=time.time(); print(f"=== zonas {c} ===",flush=True)
    ticks,_,_,_,_,_=load_canonical_ticks(BASE/f"{c}.Last.txt",tick_size=0.10,max_ticks=None)
    p=dict(DEFAULTS); p["ScoreMode"]="AbsMagnitude"
    res=run_abs(ticks,params=p)
    zs=[int(z["sig_ts"]) for z in res.get("zones",[])]
    sd=[1 if z["side"]=="trapped_sellers" else 0 for z in res.get("zones",[])]
    np.savez_compressed(f, sig=np.array(zs,dtype=np.int64), side=np.array(sd,dtype=np.int8))
    print(f"    {len(zs)} zonas en {time.time()-t0:.0f}s",flush=True); del ticks,res

rep={"_meta":{"universo":"152 sesiones, 4 rolls rule-based (ENMIENDA_UNIVERSO_GATE1_2026-08-23)",
     "horizon_ticks":H_TK,"horizon_seg":900,
     "strata":"sesion CME x contrato x bin30_CT x cap_driver",
     "regla":"ancla elegible = tick cuyo horizonte completo cae dentro de la misma sesion CME"},
     "por_contrato":{},"estratos_flacos":[],"resumen":{}}
tot_ev=tot_str=flacos=0; ratios=[]
for c,(d0,d1) in CHAIN.items():
    z=np.load(CACHE/f"{c.replace(' ','_')}.npz"); T=z["tick_ts"]
    SIG=np.load(CACHE/f"{c.replace(' ','_')}_zones.npz")["sig"]
    sdT=sesd(T); days=np.unique(sdT); days=days[[d0<=d2s(x)<=d1 for x in days]]
    mT=np.isin(sdT,days); idx=np.flatnonzero(mT)
    fin=np.searchsorted(sdT,sdT[idx],side="right")-1
    i_tk=idx+H_TK; i_cl=np.searchsorted(T,T[idx]+H_S,side="left")
    i_end=np.minimum(i_tk,i_cl); cap=np.where(i_tk<=i_cl,0,1)
    elig=(i_end<=fin)&(i_end<len(T)); ok=idx[elig]
    capd=collections.Counter(zip(sdT[ok].tolist(),bins(T[ok]).tolist(),cap[elig].tolist()))
    pos=np.searchsorted(T,SIG); pos=pos[(pos>0)&(pos<len(T))]
    pe=pos[np.isin(sdT[pos],days)]
    ec=np.where(pe+H_TK<=np.searchsorted(T,T[pe]+H_S,side="left"),0,1)
    ev=collections.Counter(zip(sdT[pe].tolist(),bins(T[pe]).tolist(),ec.tolist()))
    nf=0
    for k,ne in ev.items():
        na=capd.get(k,0)-1; tot_ev+=ne; tot_str+=1; ratios.append(na/ne if ne else 0)
        if na<ne:
            nf+=1; flacos+=1
            rep["estratos_flacos"].append({"contrato":c,"sesion":d2s(k[0]),"bin":int(k[1]),
              "hora_ct":"%02d:%02d"%(((17*60+k[1]*30)//60)%24,(k[1]*30)%60),
              "cap_driver":"ticks" if k[2]==0 else "clock","eventos":int(ne),"anclas":int(na)})
    rep["por_contrato"][c]={"sesiones":len(days),"eventos":int(sum(ev.values())),
      "estratos_con_evento":len(ev),"estratos_flacos":nf,
      "anclas_elegibles":int(elig.sum()),"ticks_en_ventana":int(mT.sum()),
      "cap_driver_ticks_pct":round(100*float((ec==0).mean()),1) if len(ec) else None}
    print(f"  {c}: {len(days)} ses, {sum(ev.values())} eventos, {len(ev)} estratos, {nf} flacos",flush=True)
r=np.array(ratios)
rep["resumen"]={"eventos_totales":tot_ev,"estratos_con_evento":tot_str,"estratos_flacos":flacos,
  "veredicto":"PRECONDITION_FAILED_SPARSE_STRATUM" if flacos else "N_RAND_CAPACITY_OK",
  "anclas_por_evento_min":float(r.min()),"p01":float(np.percentile(r,1)),
  "p10":float(np.percentile(r,10)),"p50":float(np.percentile(r,50))}
pathlib.Path(r"C:\ProyectosQuant\EdgeLab\docs\research\NRAND_CAPACIDAD_ESTRATOS.json").write_text(
  json.dumps(rep,indent=2,ensure_ascii=False),encoding="utf-8")
print("\n=== %s ==="%rep["resumen"]["veredicto"])
print("  eventos=%d estratos=%d flacos=%d"%(tot_ev,tot_str,flacos))
print("  anclas/evento: min %.0f | p01 %.0f | p10 %.0f | p50 %.0f"%(r.min(),np.percentile(r,1),np.percentile(r,10),np.percentile(r,50)))
