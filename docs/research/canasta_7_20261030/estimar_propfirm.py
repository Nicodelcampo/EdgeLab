"""Estimación de propfirm para una canasta congelada. No lee datos: recibe carpetas con JSON de operaciones (neto, ses, t_exit).
Uso: estimar_propfirm.py <carpeta_ref> [carpeta_holdout] ; ref = OOS previo, holdout = resultado sellado ya abierto por su acta.
Micros enteros y valor por punto se aplican por regla; la serie es USD por sesión con freno por hora de cierre."""
import json,os,sys,numpy as np,polars as pl
# regla: (instrumento, USD por punto, sin uso). neto ya viene descontando la fricción de la campaña: no se resta otra vez.
R={'cvgap-cfd-nq':('MNQ',2,2.2),'cvgap-nq':('MNQ',2,2.2),'u1-zonas-avcl-nq':('MNQ',2,2.2),'u1-zonas-nq':('MNQ',2,2.2),'u1-racimos-grilla-nq':('MNQ',2,2.2),'u1-oro-grilla':('MGC',10,2.5),'u1-ym-grilla':('MYM',.5,1.5)}
CUENTAS={'50K':dict(cap=50000,dd=2000,ob=3000,dias=60,trail='eod'),'AXI7':dict(cap=50000,dd=3500,ob=3500,dias=120,trail='no'),'AXI10':dict(cap=50000,dd=5000,ob=3500,dias=120,trail='no')}
def dia(car,micros,freno_usd,desde=0):
    L=[]
    for c,(ins,pv,fr) in R.items():
        f=f'{car}/{c}.json'
        if not os.path.exists(f): print('falta',f);continue
        o=json.load(open(f))['operaciones'];L.append(pl.DataFrame({'ses':o['ses'],'tx':o['t_exit'],'u':[n*pv*micros for n in o['neto']]},schema={'ses':pl.Int64,'tx':pl.Float64,'u':pl.Float64}))
    a=pl.concat(L).filter(pl.col('ses')>=desde).sort('tx');d={}
    for (s,),g in a.group_by('ses',maintain_order=True):
        ac=0.
        for u in g['u']:
            ac+=u
            if ac<=-freno_usd: break
        d[s]=ac
    return np.array([d[k] for k in sorted(d)])
def sim(x,c,mu=None,N=20000,B=5,seed=7):
    rng=np.random.default_rng(seed);y=x-x.mean()+(x.mean() if mu is None else mu);s=rng.integers(0,len(x),(N,c['dias']//B+1))
    i=((s[:,:,None]+np.arange(B))%len(x)).reshape(N,-1)[:,:c['dias']];e=y[i].cumsum(1)
    m=np.maximum.accumulate(np.c_[np.zeros(N),e],1)[:,1:] if c['trail']=='eod' else 0*e
    br=e-m<=-c['dd'];w=e>=c['ob'];b=np.where(br.any(1),br.argmax(1),10**6);g=np.where(w.any(1),w.argmax(1),10**6)
    return (g<b).mean(),(b<g).mean()
def res(x):
    e=x.cumsum();return dict(ses=len(x),usd=round(x.sum()),t=round(x.mean()/x.std(ddof=1)*len(x)**.5,2),dd=round((e-np.maximum.accumulate(np.r_[0,e])[1:]).min()))
if __name__=='__main__':
    ref=sys.argv[1];ho=sys.argv[2] if len(sys.argv)>2 else None
    for micros,fr in ((1,300),(1,10**9)):
        x=dia(ref,micros,fr,20260401);print('REF',micros,'freno',fr,res(x))
        h=dia(ho,micros,fr) if ho else None
        if h is not None: print('HOLDOUT',res(h))
        # media: referencia, mitad, cero y, con holdout, promedio ponderado por sesiones con el holdout entero y referencia a la mitad
        mus={'ref':x.mean(),'mitad':x.mean()/2,'cero':0.}
        if h is not None: mus['combinada']=(h.sum()+.5*x.sum())/(len(h)+.5*len(x)*2)
        for n,c in CUENTAS.items():
            print(n,{k:tuple(round(float(v),3) for v in sim(x,c,m)) for k,m in mus.items()})
