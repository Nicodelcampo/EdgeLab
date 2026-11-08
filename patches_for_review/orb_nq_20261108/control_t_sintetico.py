"""Null simulation; synthetic seeded test, no market data, preregistered seeds 1000..1999."""
import json, runpy
import numpy as np
from scipy.stats import binomtest, t as student_t
from edgelab.research import grilla_masiva as GM
m = runpy.run_path('tests/research/test_criba_maxt.py')
P, data = m['P'], m['_datos']
N=1000
keys=['maxT','Student_Storey','Student_BH','Normal_Storey','Normal_BH']
a=np.zeros((N,len(keys)),dtype=np.int8)
for j, seed in enumerate(range(1000,2000)):
    idx,net,ses=data(seed)
    st=GM.estadisticas(*GM.tensor(P,idx,net),min_n=10)
    # Evaluar la cola t con SciPy, sin depender del parche pendiente de integración.
    # El estadístico, el conteo y la máscara de elegibilidad son los de la base.
    ev=st['evaluable']; st['p']=np.ones(st['p'].shape)
    st['p'][ev]=student_t.sf(st['t'][ev], st['n'][ev]-1)
    mt=GM.criba_maxt(P,idx,net,ses,st,B=299,alfa=.10,seed=seed+7)
    normal=dict(st);normal['p']=np.ones(st['p'].shape)
    ev=st['evaluable']; normal['p'][ev]=GM._cola_superior(st['t'][ev])
    a[j]=[mt['n_nominadas']>0, GM.criba(st,q=.10,metodo='storey')['n_nominadas']>0,
          GM.criba(st,q=.10,metodo='bh')['n_nominadas']>0,
          GM.criba(normal,q=.10,metodo='storey')['n_nominadas']>0,
          GM.criba(normal,q=.10,metodo='bh')['n_nominadas']>0]
    if (j+1)%200==0: print('simulations',j+1,flush=True)
counts={}
for i,k in enumerate(keys):
    n=int(a[:,i].sum()); ci=binomtest(n,N).proportion_ci(confidence_level=.95,method='wilson')
    counts[k]={'n':n,'rate':n/N,'wilson95':[ci.low,ci.high]}
def paired(x,y):
    i=keys.index(x);k=keys.index(y)
    x_only=int(((a[:,i]==1)&(a[:,k]==0)).sum()); y_only=int(((a[:,i]==0)&(a[:,k]==1)).sum())
    return {'x_only':x_only,'y_only':y_only,'delta':float(a[:,i].mean()-a[:,k].mean()),'p_two_sided_exact':float(binomtest(x_only,x_only+y_only,.5).pvalue) if x_only+y_only else 1}
out={'method':'synthetic global null, 160 sessions, seed-specific shared symmetric session factor + Student-t4 per-operation errors; 299 common sign flips; alpha=.10; min_n=10','seeds':[1000,1999], 'runs':N,'counts':counts,'paired_t_storey_vs_maxt':paired('Student_Storey','maxT'),'paired_t_bh_vs_maxt':paired('Student_BH','maxT'),'paired_normal_storey_vs_t_storey':paired('Normal_Storey','Student_Storey'),'note':'Validation sample postulated after seeing prior seeds 0..999; no alpha or ratio threshold changed. Multiple comparisons descriptive. No claim about every dataset.'}
print(json.dumps(out,indent=2))
