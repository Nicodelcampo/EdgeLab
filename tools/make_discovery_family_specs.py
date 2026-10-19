#!/usr/bin/env python3
"""Genera las especificaciones por familia (config/discovery/families/*.json) y los grupos de activos. Cada familia = una hipótesis económica."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from edgelab.discovery.spec import GridSpec,Condition,spec_dict,spec_hash
W3=(15,30,60)
def C(f,op,th=0.):return Condition(f,op,th)
def sign(f):return [C(f,"gt",0.),C(f,"lt",0.)]
def zb(f):return [C(f,"zgt",1.),C(f,"zlt",-1.)]
def build(name,singles,pair_rules,seed):
    conds=[];index={}
    for c in singles:
        if c.key() not in index:index[c.key()]=len(conds);conds.append(c)
    pairs=[]
    for a,b in pair_rules:
        i,j=index[a.key()],index[b.key()]
        if i==j:continue
        pairs.append((min(i,j),max(i,j)))
    pairs=sorted(set(pairs));s=GridSpec(name=name,holds=(15,30,60,120),conditions=tuple(conds),pairs=tuple(pairs),min_trades=40,n_sims=20000,seed=seed);s.validate();return s
fam={}
# 1) Momentum: continuación o reversión tras un movimiento reciente
s1=[c for W in W3 for f in (f"mom_{W}",) for c in sign(f)+zb(f)];fam["f1_momentum"]=build("f1_momentum",s1,[],20261012)
# 2) VWAP: reversión o continuación según la distancia al valor
s2=[c for W in W3 for f in (f"vwapdev_{W}",) for c in sign(f)+zb(f)];fam["f2_vwap"]=build("f2_vwap",s2,[],20261013)
# 3) Flujo y absorción: desequilibrio por agresor, volumen por recorrido, esfuerzo/resultado; pares con momentum
s3=[];p3=[]
for W in W3:
    s3+=sign(f"imb_{W}")+zb(f"imb_{W}")+[C(f"absorb_{W}","zgt",1.),C(f"absorb_{W}","zlt",-1.)]+[C(f"effort_{W}","zgt",1.),C(f"effort_{W}","zlt",-1.)]+sign(f"mom_{W}")
    for a in sign(f"imb_{W}"):
        for b in sign(f"mom_{W}"):p3.append((a,b))
    for b in sign(f"mom_{W}"):p3.append((C(f"absorb_{W}","zgt",1.),b))
    for b in sign(f"imb_{W}"):p3.append((C(f"absorb_{W}","zgt",1.),b));p3.append((C(f"effort_{W}","zgt",1.),b))
fam["f3_flujo_absorcion"]=build("f3_flujo_absorcion",s3,p3,20261014)
# 4) Régimen: rango y spread como filtros de momentum y VWAP
s4=[];p4=[]
for W in W3:
    s4+=[C(f"rng_{W}","zgt",1.),C(f"rng_{W}","zlt",-1.),C(f"spread_{W}","zgt",1.)]+sign(f"mom_{W}")+sign(f"vwapdev_{W}")
    for a in zb(f"rng_{W}"):
        for b in sign(f"mom_{W}")+sign(f"vwapdev_{W}"):p4.append((a,b))
    for b in sign(f"mom_{W}"):p4.append((C(f"spread_{W}","zgt",1.),b))
fam["f4_regimen"]=build("f4_regimen",s4,p4,20261015)
# 5) Medias: distancia a una EMA (W barras de 1 min) como filtro de régimen, con pares frente a momentum
s5=[];p5=[]
for E in (20,50,200):s5+=sign(f"emadev_{E}")+zb(f"emadev_{E}")
for W in W3:s5+=sign(f"mom_{W}")
for E in (50,200):
    for a in sign(f"emadev_{E}"):
        for W in W3:
            for b in sign(f"mom_{W}"):p5.append((a,b))
fam["f5_medias"]=build("f5_medias",s5,p5,20261016)
out=Path("config/discovery/families");out.mkdir(parents=True,exist_ok=True);summary={}
for k,s in fam.items():
    (out/f"{k}.json").write_text(json.dumps(spec_dict(s),indent=1));summary[k]={"conditions":len(s.conditions),"pairs":len(s.pairs),"cells_per_asset":s.n_cells(),"hash":spec_hash(s)}
(Path("config/discovery")/"groups.json").write_text(json.dumps({"GC":["GC"],"ZB":["ZB"],"FX":["6E","6J"]},indent=1))
(Path("config/discovery")/"families_summary.json").write_text(json.dumps(summary,indent=1))
print(json.dumps(summary,indent=1));print("total celdas por activo:",sum(v["cells_per_asset"] for v in summary.values()))
