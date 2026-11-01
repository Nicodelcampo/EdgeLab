import json,os,numpy as np,polars as pl
S={'cvgap-cfd-nq':48.7089,'cvgap-nq':78.0207,'u1-oro-grilla':10.7017,'u1-racimos-grilla-nq':33.9181,'u1-ym-grilla':88.0515,'u1-zonas-avcl-nq':17.2718,'u1-zonas-nq':74.4533}
def run(v):
    L=[]
    for c,s in S.items():
        f=f'{v}_res/{c}.json'
        if not os.path.exists(f): print('falta',f);continue
        o=json.load(open(f))['operaciones'];L.append(pl.DataFrame({'ses':o['ses'],'tx':o['t_exit'],'r':[x/s for x in o['neto']]},schema={'ses':pl.Int64,'tx':pl.Float64,'r':pl.Float64}))
    if not L: return
    a=pl.concat(L).sort('tx')
    dia={}
    for (s,),g in a.group_by('ses',maintain_order=True):
        ac=0
        for r in g['r']:
            ac+=r
            if ac<=-2: break
        dia[s]=ac
    k=sorted(dia);x=np.array([dia[i] for i in k]);K=np.array(k)
    for n,m in (('OOS',K>=20260401),('Q2',(K>=20260401)&(K<20260701)),('Q3',K>=20260701)):
        y=x[m];e=y.cumsum();print(v,n,round(y.sum(),1),round(y.mean()/y.std(ddof=1)*len(y)**.5,2),round((e-np.maximum.accumulate(np.r_[0,e])[1:]).min(),1))
run('cie');run('c2r')

def serie(v):
    L=[]
    for c,s in S.items():
        f=f'{v}_res/{c}.json'
        if os.path.exists(f):
            o=json.load(open(f))['operaciones'];L.append(pl.DataFrame({'ses':o['ses'],'tx':o['t_exit'],'r':[x/s for x in o['neto']]},schema={'ses':pl.Int64,'tx':pl.Float64,'r':pl.Float64}))
    d={}
    for (s,),g in pl.concat(L).sort('tx').group_by('ses',maintain_order=True):
        ac=0
        for r in g['r']:
            ac+=r
            if ac<=-2: break
        d[s]=ac
    k=sorted(x for x in d if x>=20260401);return np.array([d[i] for i in k])
def sim(x,u,dd,ob,dias,h,N=20000,B=5):
    rng=np.random.default_rng(7);y=x-(1-h)*x.mean();s=rng.integers(0,len(x),(N,dias//B+1))
    i=((s[:,:,None]+np.arange(B))%len(x)).reshape(N,-1)[:,:dias];e=(y[i]*u).cumsum(1);m=np.maximum.accumulate(np.c_[np.zeros(N),e],1)[:,1:]
    br=e-m<=-dd;w=e>=ob;b=np.where(br.any(1),br.argmax(1),10**6);g=np.where(w.any(1),w.argmax(1),10**6)
    return round((g<b).mean(),3),round((b<g).mean(),3)
print('variante cuenta u: pasa/quema con hair 1, .5, 0')
for v in('cie','c2r'):
    x=serie(v);print(v,round(x.mean(),3),round(x.std(),2))
    for nm,dd,ob,di,us in(('50K',2000,3000,60,(50,100,150)),('AXI',7,7,120,(.1,.2,.3))):
        for u in us: print(nm,u,*[sim(x,u,dd,ob,di,h) for h in(1,.5,0)])
