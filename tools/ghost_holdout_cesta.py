"""Enmienda 5: cesta 1 MES + 1 RTY + 1 YM, holdout (sesiones >= 2026-07-01). Una sola apertura."""
import sys,os,json,datetime as dt,numpy as np,pandas as pd
sys.path.insert(0,'/tmp/claude-0/ghostlocal');sys.path.insert(0,'/home/user/EdgeLab')
import pyarrow.parquet as pq,pyarrow.compute as pc
from opp_tables import build_table,SLOTS
from edgelab.funnel.schedule_nulls import session_bootstrap,direction_null_total,placebo_schedule_null,exposure_preserving_direction_null
FLAG='/tmp/claude-0/ghostlocal/HOLDOUT_POOLED_USED.flag'
CFG={'MES':dict(tick=1.25,comm=1.90),'RTY':dict(tick=5.0,comm=4.50),'YM':dict(tick=5.0,comm=4.50)}
OOS0=dt.date(2026,7,1).toordinal();SCAN0=dt.date(2026,6,24).toordinal();MIN=60_000_000_000;RAW='/tmp/claude-0/ghostlocal/ho_raw'
rules=json.load(open('/tmp/claude-0/ghostlocal/rules.json'));NR=len(rules);RID={r['id']:i for i,r in enumerate(rules)}
def tdate(t_ns):
    ix=pd.to_datetime(np.asarray(t_ns)-1,unit='ns',utc=True).tz_convert('America/Chicago')+pd.Timedelta(hours=7)
    return np.array([d.toordinal() for d in ix.date])
def read_ticks(fn,cols):
    f=pq.ParquetFile(fn);acc={c:[] for c in cols}
    for g in range(f.metadata.num_row_groups):
        t=f.read_row_group(g,columns=cols+['tick_type']);m=pc.equal(t.column('tick_type'),'trade').to_numpy(zero_copy_only=False)
        for c in cols:acc[c].append(t.column(c).to_numpy()[m])
    return {c:np.concatenate(v) for c,v in acc.items()}
def run_asset(A,test=False):
    tick=CFG[A]['tick'];comm=CFG[A]['comm']/tick;ORDER=[f'{A}_09-26',f'{A}_12-26']
    bars={};daily={};cache={}
    for c in ORDER:
        x=read_ticks(f'{RAW}/{c}_ticks.parquet',['ts_utc_ns','price_ticks','bid_ticks','ask_ticks','volume']);ts=x['ts_utc_ns'];assert np.all(np.diff(ts)>=0)
        cache[c]={'ts':ts,'px':x['price_ticks'].astype(np.int64),'bid':x['bid_ticks'].astype(np.int64),'ask':x['ask_ticks'].astype(np.int64)}
        lab=(ts//MIN+1)*MIN;ub,st=np.unique(lab,return_index=True);en=np.r_[st[1:],len(ts)]
        t=ub;cl=x['price_ticks'][en-1].astype(np.int64);v=np.add.reduceat(x['volume'].astype(np.int64),st);td=tdate(t)
        bars[c]=(t,cl,td);u,inv=np.unique(td,return_inverse=True);daily[c]=dict(zip(u.tolist(),np.bincount(inv,weights=v).tolist()))
    # mediana del 09-26 en julio-agosto para el umbral de roll
    jv=[v for d,v in daily[ORDER[0]].items() if OOS0<=d<=dt.date(2026,8,31).toordinal() and v>0];thr=0.05*float(np.median(jv))
    alld=sorted({d for c in ORDER for d in daily[c] if d>=SCAN0});cur=0;regime={};prev=None
    for d in alld:
        if prev is not None and cur+1<len(ORDER):
            v1=daily[ORDER[cur+1]].get(prev,0.);v0=daily[ORDER[cur]].get(prev,0.)
            if v1>=thr and v1>v0>0:cur+=1
        regime[d]=cur if daily[ORDER[cur]].get(d,0.)>0 else None;prev=d
    segs=[]
    for d in alld:
        r=regime[d]
        if r is None:continue
        if segs and segs[-1][0]==r and d-segs[-1][2]<=5:segs[-1][2]=d
        else:segs.append([r,d,d])
    tabs=[]
    for r,d0,d1 in segs:
        c=ORDER[r];t,cl,td=bars[c];tk=cache[c];tdmap=dict(zip(t.tolist(),td.tolist()))
        sf=lambda lab,lo=d0,hi=d1,m=tdmap:lo<=m.get(lab,-1)<=hi
        tab=build_table(t,cl,tk['ts'],tk['bid'],tk['ask'],tk['px'],d0-1,d1,sf);tab['sess']=np.where(tab['b1']>0,tdate(np.where(tab['b1']>0,tab['b1'],1)),0);tabs.append(tab)
    med={}
    for c in ORDER:
        vv=[v for d,v in daily[c].items() if d>=OOS0 and v>0];med[c]=float(np.median(vv)) if vv else 0.
    elig=set()
    for r,d0,d1 in segs:
        c=ORDER[r]
        for d in range(d0,d1+1):
            if daily[c].get(d,0.)>=0.5*med[c]:elig.add(d)
    def fire_mask(tab,r):
        m=(tab['slot']==SLOTS.index(r['hhmm']))&tab[f"valid{r['hold']}"]
        m&=(tab['dow']==r['dow']) if r['dow']!=0 else (tab['dow']<=5)
        if r['cond']!=0:m&=(tab['sign']==r['cond'])&~tab['noref']
        return m
    rows=dict(sess=[],rid=[],plus=[],minus=[],dir=[],long=[]);S=np.zeros((NR,96))
    for tab in tabs:
        elg=np.array([int(s) in elig and int(s)>=OOS0 for s in tab['sess']])
        for r in rules:
            m=fire_mask(tab,r);k=np.where(m&elg)[0]
            if len(k):
                own=('long' if r['direction']==1 else 'short')+str(r['hold']);opp=('short' if r['direction']==1 else 'long')+str(r['hold'])
                rows['sess']+=tab['sess'][k].tolist();rows['rid']+=[RID[r['id']]]*len(k);rows['plus']+=((tab[own][k]-comm)*tick).tolist();rows['minus']+=((tab[opp][k]-comm)*tick).tolist()
                rows['dir']+=[r['direction']]*len(k);rows['long']+=((tab['long'+str(r['hold'])][k]-comm)*tick).tolist()
            # placebo: misma regla en cualquier franja
            mm=tab['valid'+str(r['hold'])].copy();mm&=(tab['dow']==r['dow']) if r['dow']!=0 else (tab['dow']<=5)
            if r['cond']!=0:mm&=(tab['sign']==r['cond'])&~tab['noref']
            kk=np.where(mm&elg)[0]
            S[RID[r['id']]]+=np.bincount(tab['slot'][kk],weights=(tab[('long' if r['direction']==1 else 'short')+str(r['hold'])][kk]-comm)*tick,minlength=96)
    return {k:np.array(v) for k,v in rows.items()},S,{'segments':[(ORDER[r],dt.date.fromordinal(a).isoformat(),dt.date.fromordinal(b).isoformat()) for r,a,b in segs],'threshold_roll':thr,'median':med,'eligible_sessions':len(elig)}
def combine(parts):
    """parts: lista de (rows,S). Cesta: suma por (regla, sesión); pata ausente aporta 0."""
    keys={}
    for rows,_ in parts:
        for s,r in zip(rows['sess'].tolist(),rows['rid'].tolist()):keys.setdefault((s,r),len(keys))
    n=len(keys);agg={k:np.zeros(n) for k in('plus','minus','long')};dirs=np.zeros(n,int);sess=np.zeros(n,int);rid=np.zeros(n,int)
    for (s,r),i in keys.items():sess[i]=s;rid[i]=r
    for rows,_ in parts:
        idx=np.array([keys[(s,r)] for s,r in zip(rows['sess'].tolist(),rows['rid'].tolist())],int)
        for k in agg:np.add.at(agg[k],idx,rows[k])
        dirs[idx]=rows['dir']
    return sess,rid,dirs,agg
def evaluate(sess,dirs,agg,S,act):
    b=session_bootstrap(agg['plus'],sess,5000,1);dn=direction_null_total(agg['plus'],agg['minus'],sess,5000,2)
    ex=exposure_preserving_direction_null(agg['plus'],agg['minus'],dirs,sess,3000,3);pl=placebo_schedule_null(S,act,2000,4)
    return {'trades':int(len(sess)),'sessions':b['n_sessions'],'mean_net_usd':b['mean'],'ci95_usd':[b['ci_low'],b['ci_high']],'always_long_mean_usd':float(agg['long'].mean()),
            'p_direction_null':dn['p'],'p_exposure_preserving':ex['p'],'p_placebo_schedule':pl['p']}
if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='selftest':
        rng=np.random.default_rng(0);mk=lambda:({'sess':np.array([5,5,6]),'rid':np.array([0,1,0]),'plus':np.array([1.,2,3]),'minus':np.array([-1.,-2,-3]),'dir':np.array([1,-1,1]),'long':np.array([1.,-2,3])},np.zeros((NR,96)))
        a,b=mk(),mk();b[0]['sess']=np.array([5,6,6]);b[0]['rid']=np.array([0,0,1])
        s,r,d,g=combine([a,b]);print(len(s),g['plus'].sum(),a[0]['plus'].sum()+b[0]['plus'].sum());assert abs(g['plus'].sum()-(a[0]['plus'].sum()+b[0]['plus'].sum()))<1e-12
        print('selftest ok');sys.exit()
    if os.path.exists(FLAG):raise SystemExit('holdout pooled already consumed')
    open(FLAG,'w').write('opened once')
    parts=[];meta={};per={}
    for A in CFG:
        rows,S,m=run_asset(A);parts.append((rows,S));meta[A]=m
        per[A]={'trades':int(len(rows['sess'])),'mean_net_usd':float(rows['plus'].mean()) if len(rows['sess']) else None,'always_long_usd':float(rows['long'].mean()) if len(rows['sess']) else None,'sessions':int(len(np.unique(rows['sess'])))}
    sess,rid,dirs,agg=combine(parts);act=np.array([SLOTS.index(r['hhmm']) for r in rules]);Sx=sum(p[1] for p in parts)
    assert abs(Sx[np.arange(NR),act].sum()-agg['plus'].sum())<1e-6*max(1.,abs(agg['plus'].sum())),'placebo total != real total'
    res={'basket':'1 MES + 1 RTY + 1 YM','meta':meta,'per_asset':per,'pooled':evaluate(sess,dirs,agg,Sx,act)}
    json.dump(res,open('/tmp/claude-0/ghostlocal/holdout_pooled.json','w'),indent=1,default=float);print(json.dumps(res,indent=1,default=float))
