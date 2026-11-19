#!/usr/bin/env python3
"""REGIMEN-FORWARD, adenda de potencia (2026-11-19): tiempo hasta la decisión del e-proceso de la canasta T+R, por bootstrap en bloques de 5
de los días con operación 2021-02-10 → 2026-09-29 (desarrollo), con la media de desarrollo, contraída a la mitad y cero. Descriptivo.
  python tools/regimen_forward_tiempo.py
"""
import sys; sys.path.insert(0,'.'); sys.path.insert(0,'tools')
import numpy as np, pandas as pd
from edgelab.funnel.secuencial import EProceso
from edgelab.research.embudo_runners import friccion
fr=float(friccion("NQ")[0])
t=pd.read_csv("docs/research/m1_largo_20261117/FS_OPS_T2008_NQ.csv.gz"); t=t[t.riesgo>=2]; t["R"]=t.neto/t.riesgo
r=pd.read_csv("docs/research/neto_pistas_20261119/RZ_OPS.csv.gz"); r=r[(r.modulo=="R")&(r.inst=="NQ")&(r.variante=="R_21_100_2.5_660")]
s=0.25*r.atr20; r["R"]=(np.where(r.mae_pts>=s,-s,r.pnl_pts)-fr)/s; r["dia"]=r.ses
d=pd.concat([t[["dia","R"]],r[["dia","R"]]]); d=d[(d.dia>="2021-02-10")&(d.dia<="2026-09-29")]
dias=pd.bdate_range("2021-02-10","2026-09-29").strftime("%Y-%m-%d")
x=d.groupby("dia").R.sum().reindex(dias).fillna(0).to_numpy()
op=d.groupby("dia").R.sum()
print("días hábiles",len(x),"con operación",len(op),"media/día",round(x.mean(),3),"media por día con op",round(op.mean(),3),"sd",round(op.std(),2))
y=op.to_numpy()
rng=np.random.default_rng(1)
for nom,mu in [("dev",y.mean()),("contraída",y.mean()/2),("cero",0.0)]:
    z=np.clip(y-y.mean()+mu,-6,16); res=[]
    for k in range(2000):
        E=EProceso(0.0,-6.0,16.0,"mayor"); Fu=EProceso(0.13,-6.0,16.0,"menor"); c=0;pk=0;dec=None
        pos=rng.integers(len(z))
        for i in range(1500):
            if i%5==0: pos=rng.integers(len(z))
            v=z[(pos+i%5)%len(z)]; E.agregar(v); Fu.agregar(v); c+=v; pk=max(pk,c)
            if E.e_valor>=20 and i>=29: dec=("EDGE",i+1);break
            if Fu.e_valor>=10: dec=("FUT",i+1);break
            if c-pk<=-26: dec=("DD",i+1);break
        res.append(dec or ("NADA",1500))
    R=pd.DataFrame(res,columns=["d","n"]); f=len(op)/len(x)
    print(nom, R.d.value_counts(normalize=True).round(3).to_dict(), "mediana meses (EDGE)", round(R[R.d=="EDGE"].n.median()/f/21,1) if (R.d=="EDGE").any() else None)
