"""Enmienda 6: cesta 1 ES + 1 NQ, sesiones completas del catálogo (2026-07-01 a 2026-09-25). Una sola apertura."""
import sys,os,json,datetime as dt,numpy as np
sys.path.insert(0,'/tmp/claude-0/ghostlocal');sys.path.insert(0,'/home/user/EdgeLab')
sys.argv=[sys.argv[0]]+sys.argv[1:]
import holdout_pooled as H
from opp_tables import build_table,SLOTS
FLAG='/tmp/claude-0/ghostlocal/HOLDOUT_ESNQ_USED.flag';RAW='/tmp/claude-0/ghostlocal/ho_raw2';CAT='/tmp/claude-0/ghostlocal/esnq/x'
CFG={'ES':dict(tick=12.5,comm=4.50),'NQ':dict(tick=5.0,comm=4.50)}
OOS0=H.OOS0;MIN=H.MIN;rules=H.rules;NR=H.NR;RID=H.RID
def run_asset(A):
    tick=CFG[A]['tick'];comm=CFG[A]['comm']/tick;ORDER=[f'{A}_09-26',f'{A}_12-26']
    cat=json.load(open(f'{CAT}/{A}_ext_2026q3_sessions_catalog.json'));by={}
    for s in cat['sessions']:
        d=dt.datetime.strptime(s['trade_date'],'%Y%m%d').date().toordinal();by[d]=ORDER.index(s['contract'].replace(' ','_'))
    elig=set(by);bars={};cache={}
    for c in ORDER:
        x=H.read_ticks(f'{RAW}/{c}_ticks.parquet',['ts_utc_ns','price_ticks','bid_ticks','ask_ticks','volume']);ts=x['ts_utc_ns'];assert np.all(np.diff(ts)>=0)
        cache[c]={'ts':ts,'px':x['price_ticks'].astype(np.int64),'bid':x['bid_ticks'].astype(np.int64),'ask':x['ask_ticks'].astype(np.int64)}
        lab=(ts//MIN+1)*MIN;ub,st=np.unique(lab,return_index=True);en=np.r_[st[1:],len(ts)]
        bars[c]=(ub,x['price_ticks'][en-1].astype(np.int64),H.tdate(ub))
    segs=[]
    for r in (0,1):
        ds=sorted(d for d,k in by.items() if k==r)
        if ds:segs.append([r,ds[0],ds[-1]])
    tabs=[]
    for r,d0,d1 in segs:
        c=ORDER[r];t,cl,td=bars[c];tk=cache[c];tdmap=dict(zip(t.tolist(),td.tolist()))
        sf=lambda lab,lo=d0,hi=d1,m=tdmap:lo<=m.get(lab,-1)<=hi
        tab=build_table(t,cl,tk['ts'],tk['bid'],tk['ask'],tk['px'],d0-1,d1,sf);tab['sess']=np.where(tab['b1']>0,H.tdate(np.where(tab['b1']>0,tab['b1'],1)),0);tabs.append(tab)
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
            mm=tab['valid'+str(r['hold'])].copy();mm&=(tab['dow']==r['dow']) if r['dow']!=0 else (tab['dow']<=5)
            if r['cond']!=0:mm&=(tab['sign']==r['cond'])&~tab['noref']
            kk=np.where(mm&elg)[0]
            S[RID[r['id']]]+=np.bincount(tab['slot'][kk],weights=(tab[('long' if r['direction']==1 else 'short')+str(r['hold'])][kk]-comm)*tick,minlength=96)
    return {k:np.array(v) for k,v in rows.items()},S,{'segments':[(ORDER[r],dt.date.fromordinal(a).isoformat(),dt.date.fromordinal(b).isoformat()) for r,a,b in segs],'catalog_sessions':len(elig),'comm_ticks':comm}
if __name__=='__main__':
    if os.path.exists(FLAG):raise SystemExit('holdout ES/NQ ya consumido')
    open(FLAG,'w').write('opened once')
    parts=[];meta={};per={}
    for A in CFG:
        rows,S,m=run_asset(A);parts.append((rows,S));meta[A]=m
        per[A]={'trades':int(len(rows['sess'])),'mean_net_usd':float(rows['plus'].mean()) if len(rows['sess']) else None,'always_long_usd':float(rows['long'].mean()) if len(rows['sess']) else None,'sessions':int(len(np.unique(rows['sess'])))}
    sess,rid,dirs,agg=H.combine(parts);act=np.array([SLOTS.index(r['hhmm']) for r in rules]);Sx=sum(p[1] for p in parts)
    assert abs(Sx[np.arange(NR),act].sum()-agg['plus'].sum())<1e-6*max(1.,abs(agg['plus'].sum())),'placebo total != real total'
    res={'basket':'1 ES + 1 NQ','meta':meta,'per_asset':per,'pooled':H.evaluate(sess,dirs,agg,Sx,act)}
    json.dump(res,open('/tmp/claude-0/ghostlocal/holdout_esnq.json','w'),indent=1,default=float);print(json.dumps(res,indent=1,default=float))
