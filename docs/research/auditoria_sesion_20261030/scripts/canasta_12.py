import json,glob,os,numpy as np,polars as pl
C=20260401
def ops(f):
    o=json.load(open(f))['operaciones'];return pl.DataFrame({'ses':o['ses'],'n':o['neto']},schema={'ses':pl.Int64,'n':pl.Float64})
def sh(d):
    s=d.filter(pl.col('ses')<C).group_by('ses').agg(pl.col('n').sum())['n'];return s.mean()/s.std() if len(s)>2 and s.std() else -9
fr=[];rows=[]
for f in sorted(glob.glob('bt_res/*.json')):
    c=os.path.basename(f)[:-5]
    if c.startswith('bt_') : continue
    a=ops(f);t=f'btt_res/{c}.json';b=ops(t) if os.path.exists(t) else None
    con=b is not None and round(sh(b),3)>round(sh(a),3);d=b if con else a
    r=d.filter(pl.col('ses')<C)['n'].std();d=d.with_columns((pl.col('n')/r).alias('r'),pl.lit(c).alias('c'))
    o=d.filter(pl.col('ses')>=C);rows.append((c,'tope' if con else 'sin',round(sh(a),3),round(sh(b),3) if b is not None else None,o.height,round(o['r'].mean(),3)));fr.append(d)
for x in rows: print(x)
a=pl.concat([x.select('ses','r','c') for x in fr]);o=a.filter(pl.col('ses')>=C);s=o.group_by('ses').agg(pl.col('r').sum())['r']
print('canasta OOS ops',o.height,'media',round(o['r'].mean(),3),'ses',len(s),'t_ses',round(s.mean()/s.std()*len(s)**.5,2),'R total',round(s.sum(),1),'peor dia',round(s.min(),2))
# Límite: distribución diaria sobre DESC+OOS y bootstrap por bloques de sesión
d=a.group_by('ses').agg(pl.col('r').sum()).sort('ses')['r'].to_numpy()
print('dias',len(d),'media',round(d.mean(),3),'sd',round(d.std(),3),'p1',round(np.percentile(d,1),2),'p5',round(np.percentile(d,5),2),'min',round(d.min(),2))
eq=d.cumsum();print('DD hist',round((eq-np.maximum.accumulate(eq)).min(),1))
oo=o.group_by('ses').agg(pl.col('r').sum()).sort('ses')['r'].to_numpy()
print('solo OOS media',round(oo.mean(),3),'sd',round(oo.std(),3))
rng=np.random.default_rng(7)
def sim(x,R,lim,obj,dd,N=20000,dias=60,B=5,hair=1.0):
    ok=ruin=dq=0
    for _ in range(N):
        i=[];
        while len(i)<dias:
            s=rng.integers(0,len(x)-B+1);i+=range(s,s+B)
        p=(x[i[:dias]]-(1-hair)*x.mean())*R;p=np.where(p<-lim,-lim,p)  # stop diario
        e=p.cumsum();m=np.maximum.accumulate(np.r_[0,e])[1:]
        br=np.where(e-m<=-dd)[0];w=np.where(e>=obj)[0]
        b=br[0] if len(br) else 10**6;g=w[0] if len(w) else 10**6
        if g<b: ok+=1
        elif b<10**6: ruin+=1
    return ok/N,ruin/N
for nom,x in (('todo',d),('OOS',oo)):
  for hair in (1,.5,0):
    for pctR in (.1,.25,.5,.75,1.):
      for lim in (2.,3.):
        print(nom,'hair',hair,'riesgo%/R',pctR,'stop%',lim,*sim(x,pctR,lim,8.,10.,N=4000,hair=hair))
