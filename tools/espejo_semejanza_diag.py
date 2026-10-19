"""Diagnóstico target-free de la semejanza v1 vs v2 de ESPEJO-IND (2026-09-27). Sin desenlaces ni P&L.

Uso: python tools/espejo_semejanza_diag.py ES_09-25.parquet ES_12-25.parquet ES_03-26.parquet
"""
import sys, numpy as np, json
sys.path.insert(0,'tools')
import espejo_macro as EM
from edgelab.bridge.indicators import espejo_impulsos as K
b=EM.es_bars(sys.argv[1:],5,modo='rth')
ses=b.day.astype(str).to_numpy(); last=np.zeros(len(b),bool); last[:-1]=ses[1:]!=ses[:-1]; last[-1]=True
res=K.run(b.t.to_numpy()-300,b.O.to_numpy(),b.H.to_numpy(),b.L.to_numpy(),b.C.to_numpy(),b.V.to_numpy(),ses,last,params=dict(atr_k=3,max_bars=24))
ev=[e for e in res['events'] if e['kind'] in('MIRROR_CANDIDATE','MIRROR_PROGRESS')]
print('impulsos',len(res['impulses']),'eventos vuelta',len(ev))
for x in (0.25,0.5,0.75):
    E=[e for e in ev if e['x']==x]
    corta=np.mean([e['velas_vuelta']<=2 for e in E])
    import itertools
    cols=['vel','efi','forma','ondas','sim_vel','sim_t','sim_v']
    M=np.array([[e[c] for c in cols] for e in E],float); ok=~np.isnan(M).any(1); M=M[ok]
    import pandas as pd
    rho=pd.DataFrame(M).rank().corr().to_numpy()
    print(f'x={x}: n={len(E)} vuelta<=2 velas {corta:.0%}; ondas==0 en v1 {np.mean(M[:,3]==0):.0%}; efi==0 en v1 {np.mean(M[:,1]==0):.0%}')
    print('  spearman sim_t vs forma %.2f, sim_t vs vel %.2f, sim_vel vs vel %.2f, sim_t vs sim_v %.2f, sim_t vs sim_vel %.2f'%(rho[5,2],rho[5,0],rho[4,0],rho[5,6],rho[5,4]))
    for lab,sel in (('<=2 velas',[e for e in E if e['velas_vuelta']<=2]),('>=3 velas',[e for e in E if e['velas_vuelta']>=3])):
        if len(sel)<10: continue
        f=np.array([e['forma'] for e in sel]); st=np.array([e['sim_t'] for e in sel])
        print(f'  {lab}: n={len(sel)} forma v1 valores distintos {len(np.unique(np.round(f[~np.isnan(f)],4)))} | sim_t mediana {np.nanmedian(st):.2f} IQR {np.nanpercentile(st,75)-np.nanpercentile(st,25):.2f}')
