import json, pathlib, collections
import numpy as np
from datetime import datetime, timezone
CACHE=pathlib.Path(r"C:\Users\nicoc\AppData\Local\Temp\claude\C--Users-nicoc-OneDrive-Escritorio-Repositorios---Edges\89905be6-498d-439f-8be3-00dd77a7ceaa\scratchpad\b9cache152")
CHAIN=["GC 02-26","GC 04-26","GC 06-26","GC 08-26"]
ROLLS={"20260129":("GC 02-26","GC 04-26"),"20260330":("GC 04-26","GC 06-26"),"20260528":("GC 06-26","GC 08-26")}
DST_O=int(datetime(2025,11,2,7,0,tzinfo=timezone.utc).timestamp())*10**9
DST_I=int(datetime(2026,3,8,8,0,tzinfo=timezone.utc).timestamp())*10**9
NS_H=3_600_000_000_000
def sesd(ts): return (((ts+np.where((ts<DST_O)|(ts>=DST_I),-5,-6)*NS_H)+7*NS_H)//86_400_000_000_000).astype(np.int64)
def d2s(d):   return datetime.fromtimestamp(int(d)*86400,tz=timezone.utc).strftime("%Y%m%d")
print("=== AUDITORIA DE LOS 4 ROLLS ===\n")
print("  chequeo 1: ninguna sesion asignada a dos contratos (one_contract_per_session)")
asig={}
BOUND={"GC 02-26":("20251126","20260128"),"GC 04-26":("20260129","20260327"),
       "GC 06-26":("20260330","20260527"),"GC 08-26":("20260528","20260630")}
dup=0
for c,(d0,d1) in BOUND.items():
    z=np.load(CACHE/f"{c.replace(' ','_')}.npz"); T=z["tick_ts"]
    ds=[d2s(x) for x in np.unique(sesd(T))]
    for d in ds:
        if d0<=d<=d1:
            if d in asig: print("    DUPLICADA:",d,asig[d],"y",c); dup+=1
            asig[d]=c
print("    sesiones totales: %d   duplicadas: %d  -> %s"%(len(asig),dup,"OK" if dup==0 else "FALLA"))
print("\n  chequeo 2: los bordes son contiguos, sin huecos ni solapes")
ds=sorted(asig); prev=None; ok=True
for c in CHAIN:
    sub=[d for d in ds if asig[d]==c]
    if not sub: continue
    print("    %-10s %3d ses  %s -> %s"%(c,len(sub),sub[0],sub[-1]))
    if prev and sub[0]<=prev: print("      SOLAPE con el anterior"); ok=False
    prev=sub[-1]
print("    contiguidad:","OK" if ok else "FALLA")
print("\n  chequeo 3: monotonia (sin volver atras)")
seq=[asig[d] for d in ds]; orden=[CHAIN.index(x) for x in seq]
print("    monotono no decreciente:","OK" if all(b>=a for a,b in zip(orden,orden[1:])) else "FALLA")
print("\n  chequeo 4: la sesion de roll pertenece al sucesor")
for f,(pre,suc) in ROLLS.items():
    print("    %s -> asignada a %-10s  esperado %-10s  %s"%(f,asig.get(f,"?"),suc,"OK" if asig.get(f)==suc else "FALLA"))
json.dump({"sesiones":len(asig),"duplicadas":dup,"contiguo":ok,
           "asignacion":{k:asig[k] for k in ds}},
  open(r"C:\ProyectosQuant\EdgeLab\docs\research\AUDITORIA_ROLLS_152.json","w",encoding="utf-8"),indent=2)
print("\n  artefacto: docs/research/AUDITORIA_ROLLS_152.json")
