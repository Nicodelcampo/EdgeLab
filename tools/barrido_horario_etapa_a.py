"""Etapa A del barrido horario (PREREGISTRO_ETAPA_A.md). Solo datos previos al holdout."""
import sys,os,json,subprocess,datetime as dt,numpy as np,pandas as pd
sys.path.insert(0,'/tmp/claude-0/ghostlocal');sys.path.insert(0,'/home/user/EdgeLab')
import pyarrow.parquet as pq,pyarrow.compute as pc
from opp_tables2 import build_table,SLOTS,HOLDS
HOLD=1782856800000000000;MIN=60_000_000_000;NH=len(HOLDS);NC=3;MINN=40;NSIM=20000;SEED=20261006
def tdate(t_ns):
    ix=pd.to_datetime(np.asarray(t_ns)-1,unit='ns',utc=True).tz_convert('America/Chicago')+pd.Timedelta(hours=7)
    return np.array([d.toordinal() for d in ix.date])
def load(c,W,cut=True):
    f=pq.ParquetFile(f'{W}/{c}_ticks.parquet');acc={k:[] for k in('ts_utc_ns','price_ticks','bid_ticks','ask_ticks','volume')}
    for g in range(f.metadata.num_row_groups):
        t=f.read_row_group(g,columns=list(acc)+['tick_type']);m=pc.equal(t.column('tick_type'),'trade').to_numpy(zero_copy_only=False)
        for k in acc:acc[k].append(t.column(k).to_numpy()[m])
    x={k:np.concatenate(v) for k,v in acc.items()};k=np.searchsorted(x['ts_utc_ns'],HOLD)
    return {a:b[:k] for a,b in x.items()}
def build(A,DS,ORDER,tick,comm_usd):
    W=f'/data/raw/{A}';os.makedirs(W,exist_ok=True);comm=comm_usd/tick;cache={};bars={};daily={}
    for c in ORDER:
        fn=f'{W}/{c}_ticks.parquet'
        if not os.path.exists(fn):subprocess.run(['curl','-sS','-L','-f','-o',fn,f'https://www.kaggle.com/api/v1/datasets/download/nicolasbuttaro/{DS}/{c}_ticks.parquet'],check=True)
        x=load(c,W);ts=x['ts_utc_ns'];assert np.all(np.diff(ts)>=0)
        cache[c]={'ts':ts,'px':x['price_ticks'].astype(np.int64),'bid':x['bid_ticks'].astype(np.int64),'ask':x['ask_ticks'].astype(np.int64)}
        lab=(ts//MIN+1)*MIN;ub,st=np.unique(lab,return_index=True);en=np.r_[st[1:],len(ts)]
        cl=x['price_ticks'][en-1].astype(np.int64);v=np.add.reduceat(x['volume'].astype(np.int64),st);td=tdate(ub);bars[c]=(ub,cl,td)
        u,inv=np.unique(td,return_inverse=True);daily[c]=dict(zip(u.tolist(),np.bincount(inv,weights=v).tolist()))
    alld=sorted({d for c in ORDER for d in daily[c]});cur=0;regime={};prev=None
    for d in alld:
        if prev is not None and cur+1<len(ORDER) and daily[ORDER[cur+1]].get(prev,0.)>daily[ORDER[cur]].get(prev,0.)>0:cur+=1
        regime[d]=cur if daily[ORDER[cur]].get(d,0.)>0 else None;prev=d
    segs=[]
    for d in alld:
        r=regime[d]
        if r is None:continue
        if segs and segs[-1][0]==r and d-segs[-1][2]<=5:segs[-1][2]=d
        else:segs.append([r,d,d])
    med={}
    for c in ORDER:
        vv=[daily[c][d] for r,d0,d1 in segs if ORDER[r]==c for d in range(d0,d1+1) if daily[c].get(d,0.)>0];med[c]=float(np.median(vv)) if vv else 0.
    elig=set()
    for r,d0,d1 in segs:
        c=ORDER[r]
        for d in range(d0,d1+1):
            if daily[c].get(d,0.)>=0.5*med[c]:elig.add(d)
    cols={k:[] for k in('sess','slot','sign','noref')};vals={f'{n}{h}':[] for n in('valid','long_bar','long','short') for h in HOLDS}
    for r,d0,d1 in segs:
        c=ORDER[r];t,cl,td=bars[c];tk=cache[c];tdmap=dict(zip(t.tolist(),td.tolist()))
        sf=lambda lab,lo=d0,hi=d1,m=tdmap:lo<=m.get(lab,-1)<=hi
        tab=build_table(t,cl,tk['ts'],tk['bid'],tk['ask'],tk['px'],d0-1,d1,sf)
        sess=np.where(tab['b1']>0,tdate(np.where(tab['b1']>0,tab['b1'],1)),0)
        for k,v in(('sess',sess),('slot',tab['slot']),('sign',tab['sign']),('noref',tab['noref'])):cols[k].append(v)
        for key in vals:vals[key].append(tab[key])
    cols={k:np.concatenate(v) for k,v in cols.items()};vals={k:np.concatenate(v) for k,v in vals.items()}
    el=np.array([int(s) in elig for s in cols['sess']])
    rows=[]
    for hi,h in enumerate(HOLDS):
        ok=el&vals[f'valid{h}']&np.isfinite(vals[f'long_bar{h}'])
        s=cols['sess'][ok];lb=vals[f'long_bar{h}'][ok].astype(float)
        u,inv=np.unique(s,return_inverse=True);mu=np.bincount(inv,weights=lb)/np.bincount(inv);rt=lb-mu[inv]
        sg=cols['sign'][ok];nr=cols['noref'][ok]
        for ci,cond in enumerate((0,1,-1)):
            m=np.ones(ok.sum(),bool) if cond==0 else ((sg==cond)&~nr)
            rows.append(dict(sess=s[m],slot=cols['slot'][ok][m],hi=np.full(m.sum(),hi),ci=np.full(m.sum(),ci),rt=rt[m],nl=vals[f'long{h}'][ok][m].astype(float)-comm,ns=vals[f'short{h}'][ok][m].astype(float)-comm))
    R={k:np.concatenate([r[k] for r in rows]) for k in rows[0]}
    return R,{'segments':[(ORDER[r],dt.date.fromordinal(a).isoformat(),dt.date.fromordinal(b).isoformat()) for r,a,b in segs],'eligible_sessions':len(elig),'median_vol':med,'comm_ticks':comm,'rows':int(len(R['sess']))}
def matrices(R,sessions):
    idx=np.searchsorted(sessions,R['sess']);D=len(sessions);ncell=96*NH*NC
    cell=(R['slot']*NH+R['hi'])*NC+R['ci'];flat=idx*ncell+cell
    M=np.bincount(flat,weights=R['rt'],minlength=D*ncell).reshape(D,ncell);N=np.bincount(flat,minlength=D*ncell).reshape(D,ncell)
    return M,N
def scan(M,N,nsim=NSIM,seed=SEED,minn=MINN):
    use=N.sum(0)>=minn;Mu=M[:,use];V=(Mu**2).sum(0);ok=V>0;Mu=Mu[:,ok];V=V[ok];S=Mu.sum(0);z=S/np.sqrt(V)
    rng=np.random.default_rng(seed);D=Mu.shape[0];Ms=Mu/np.sqrt(V);mx=np.empty(nsim);ch=2000
    for a in range(0,nsim,ch):
        e=rng.choice(np.array([-1.,1.]),size=(min(ch,nsim-a),D));mx[a:a+ch]=np.abs(e@Ms).max(1)
    real=float(np.abs(z).max());cells=np.flatnonzero(use)[ok]
    return {'n_cells':int(len(z)),'real_max_abs_z':real,'null_max_q95':float(np.quantile(mx,.95)),'p_max':float((np.sum(mx>=real)+1)/(nsim+1))},z,cells,S
def decode(c):ci=c%NC;hi=(c//NC)%NH;slot=c//(NC*NH);return SLOTS[slot],HOLDS[hi],('none','up','down')[ci]
def replicate(R,sessions,z_cells_fn):
    cut=int(len(sessions)*0.7);isS,osS=sessions[:cut],sessions[cut:]
    a=R['sess']<=isS[-1];Ri={k:v[a] for k,v in R.items()};Ro={k:v[~a] for k,v in R.items()}
    Mi,Ni=matrices(Ri,isS);r,zi,ci,Si=scan(Mi,Ni,nsim=2000);top=np.argsort(-np.abs(zi))[:5]
    Mo,No=matrices(Ro,osS);out=[];rng=np.random.default_rng(SEED+1);D=len(osS);E=rng.choice(np.array([-1.,1.]),size=(20000,D))
    for t in top:
        c=int(ci[t]);sg=1. if Si[t]>0 else -1.;col=Mo[:,c];V=(col**2).sum()
        zo=sg*col.sum()/np.sqrt(V) if V>0 else np.nan;nul=sg*(E@col)/np.sqrt(V) if V>0 else np.zeros(20000)
        p=float((np.sum(nul>=zo)+1)/(len(nul)+1)) if V>0 else 1.
        # media neta real tick a tick (todas las sesiones) en la dirección elegida
        slot,hold,cond=decode(c);m=((R['slot']*NH+R['hi'])*NC+R['ci'])==c;net=np.nanmean(R['nl'][m] if sg>0 else R['ns'][m]) if m.any() else np.nan
        out.append({'slot':slot,'hold':hold,'cond':cond,'dir':'long' if sg>0 else 'short','z_is':float(zi[t]),'z_oos':float(zo),'p_oos':p,'oos_n':int(No[:,c].sum()),'net_real_mean_ticks_all_sessions':float(net),'trades_all':int(m.sum())})
    ps=np.array([o['p_oos'] for o in out]);order=np.argsort(ps);adj=np.empty(len(ps));run=0.
    for rank,i in enumerate(order):run=max(run,(len(ps)-rank)*ps[i]);adj[i]=min(1.,run)
    for o,a_ in zip(out,adj):o['p_holm']=float(a_)
    return out
if __name__=='__main__':
    A,DS,ORD,tick,comm=sys.argv[1],sys.argv[2],sys.argv[3].split(','),float(sys.argv[4]),float(sys.argv[5])
    R,meta=build(A,DS,ORD,tick,comm);sessions=np.unique(R['sess']);np.savez_compressed(f'/tmp/claude-0/ghostlocal/stageA_rows_{A}.npz',**R)
    M,N=matrices(R,sessions);res,z,cells,S=scan(M,N);top=np.argsort(-np.abs(z))[:10]
    res.update({'asset':A,'meta':meta,'sessions':int(len(sessions)),'top_cells':[dict(zip(('slot','hold','cond'),decode(int(cells[t]))),z=float(z[t]),sum_r_ticks=float(S[t])) for t in top]})
    res['replication']=replicate(R,sessions,None);json.dump(res,open(f'/tmp/claude-0/ghostlocal/stageA_{A}.json','w'),indent=1,default=float);print(json.dumps(res,indent=1,default=float))
