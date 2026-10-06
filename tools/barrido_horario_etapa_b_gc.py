"""Etapa B GC (PREREGISTRO_ETAPA_B_GC.md). Solo datos previos al holdout."""
import sys,os,json,itertools,datetime as dt,numpy as np,pandas as pd
sys.path.insert(0,'/tmp/claude-0/ghostlocal');sys.path.insert(0,'/home/user/EdgeLab')
from numba import njit
from zoneinfo import ZoneInfo
from simple_calendar import SimpleCalendar
import stageA_scan as A
ORDER=['GC_12-25','GC_02-26','GC_04-26','GC_06-26','GC_08-26'];W='/data/raw/GC';MIN=60_000_000_000;COMM=4.5/10.0
CHI=ZoneInfo('America/Chicago');UTC=dt.timezone.utc;cal=SimpleCalendar()
SL=[400,415,430,445];KS=[1,10,20];HZ=[5,10,15,20,30,45,60];STOPS=[0,10,20,30,50];TARGS=[0,10,20,30,50]
NSIM=20000;SEED=20261007
def prepare():
    cache={};bars={};daily={}
    for c in ORDER:
        x=A.load(c,W);ts=x['ts_utc_ns'];assert np.all(np.diff(ts)>=0)
        cache[c]={'ts':ts,'px':x['price_ticks'].astype(np.int64),'bid':x['bid_ticks'].astype(np.int64),'ask':x['ask_ticks'].astype(np.int64)}
        lab=(ts//MIN+1)*MIN;ub,st=np.unique(lab,return_index=True);en=np.r_[st[1:],len(ts)]
        cl=x['price_ticks'][en-1].astype(np.int64);v=np.add.reduceat(x['volume'].astype(np.int64),st);td=A.tdate(ub);bars[c]=(ub,cl,td)
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
    return cache,bars,segs,elig,daily
@njit(cache=True)
def sim_items(px,bid,ask,ie,ixs,valid,stops,targs):
    n=ie.size;out=np.full((n,2,7,5,5),np.nan,np.float64)
    for k in range(n):
        i=ie[k];maxix=0
        for hh in range(7):
            if valid[k,hh] and ixs[k,hh]>maxix:maxix=ixs[k,hh]
        for d in range(2):
            e=bid[i] if d==0 else ask[i]
            for si in range(5):
                for ti in range(5):
                    S=stops[si];T=targs[ti];trig=-1;x=0.;j=i+1
                    while j<maxix:
                        lp=px[j]
                        if d==0:
                            if S>0 and lp>=e+S:
                                x=max(float(ask[j]),float(e+S));trig=j;break
                            if T>0 and lp<=e-T-1:
                                x=float(e-T);trig=j;break
                        else:
                            if S>0 and lp<=e-S:
                                x=min(float(bid[j]),float(e-S));trig=j;break
                            if T>0 and lp>=e+T+1:
                                x=float(e+T);trig=j;break
                        j+=1
                    for hh in range(7):
                        if not valid[k,hh]:continue
                        ix=ixs[k,hh]
                        if trig>=0 and trig<ix:xx=x
                        else:xx=float(ask[ix]) if d==0 else float(bid[ix])
                        out[k,d,hh,si,ti]=(float(e)-xx) if d==0 else (xx-float(e))
    return out
def collect(cache,bars,segs,elig):
    items=[]
    for r,d0,d1 in segs:
        c=ORDER[r];t,cl,td=bars[c];tk=cache[c];tdmap=dict(zip(t.tolist(),td.tolist()));ts=tk['ts']
        for o in range(d0-1,d1+1):
            d=dt.date.fromordinal(o)
            if d.weekday()>=5:continue
            for hm in SL:
                B=dt.datetime(d.year,d.month,d.day,hm//100,hm%100,tzinfo=CHI).astimezone(UTC);base=int(B.timestamp())*10**9;b1=base+MIN
                i1=int(np.searchsorted(t,b1))
                if i1>=len(t)-2 or t[i1]!=b1:continue
                sess=tdmap.get(b1,-1)
                if not(d0<=sess<=d1) or sess not in elig:continue
                ref=int(np.searchsorted(t,b1-15*MIN,'right'))-1;hasref=ref>=0;delta=int(cl[i1]-cl[ref]) if hasref else 0
                b2=int(t[i1+1]);ie=int(np.searchsorted(ts,b2))
                if ie>=len(ts)-1:continue
                L=dt.datetime.fromtimestamp(b1/1e9,UTC);rem=((cal.session_end(L) or L)-L).total_seconds()/60
                ixs=[];val=[]
                for h in HZ:
                    x=int(np.searchsorted(t,b2+h*MIN,'left'));ok=x<len(t)
                    if ok:ix=int(np.searchsorted(ts,int(t[x])));ok=ix<len(ts)
                    else:ix=0
                    ixs.append(ix);val.append(bool(ok and rem>=h))
                items.append(dict(c=c,sess=sess,slot=hm,delta=delta,hasref=hasref,ie=ie,ixs=ixs,val=val,b2=b2))
    return items
def main():
    cache,bars,segs,elig,daily=prepare();items=collect(cache,bars,segs,elig);print('items',len(items),flush=True)
    out=np.full((len(items),2,7,5,5),np.nan)
    for c in ORDER:
        idx=[k for k,it in enumerate(items) if it['c']==c]
        if not idx:continue
        tk=cache[c];ie=np.array([items[k]['ie'] for k in idx],np.int64);ixs=np.array([items[k]['ixs'] for k in idx],np.int64);val=np.array([items[k]['val'] for k in idx],np.bool_)
        out[idx]=sim_items(tk['px'],tk['bid'],tk['ask'],ie,ixs,val,np.array(STOPS,np.int64),np.array(TARGS,np.int64))
    out=out-COMM  # comisión de ida y vuelta, ambos lados
    # --- sesiones y partición (misma que la etapa A)
    RA=np.load('/tmp/claude-0/ghostlocal/stageA_rows_GC.npz');sessA=np.unique(RA['sess']);cut=int(len(sessA)*0.7);bound=sessA[cut-1]
    isessions=np.array([it['sess'] for it in items]);sessions=np.unique(np.r_[sessA,isessions]);S=len(sessions);sidx=np.searchsorted(sessions,isessions)
    is_mask=sessions<=bound
    slot_arr=np.array([it['slot'] for it in items]);delta=np.array([it['delta'] for it in items]);hasref=np.array([it['hasref'] for it in items]);val=np.array([it['val'] for it in items])
    V=list(itertools.product(range(4),range(3),range(7),range(5),range(5)));nv=len(V);Os=np.zeros((S,nv));Ol=np.zeros((S,nv));used=np.zeros((S,nv),bool)
    for vi,(a,b,h,st,tg) in enumerate(V):
        m=(slot_arr==SL[a])&hasref&(delta>=KS[b])&val[:,h]
        if m.any():
            Os[sidx[m],vi]=out[m,0,h,st,tg];Ol[sidx[m],vi]=out[m,1,h,st,tg];used[sidx[m],vi]=True
    nvar=used.sum(0);Dm=(Os-Ol)/2;Vv=(Dm**2).sum(0);okv=(nvar>=20)&(Vv>0)
    z=np.where(okv,Dm.sum(0)/np.sqrt(np.where(Vv>0,Vv,1)),0.);rng=np.random.default_rng(SEED);mx=np.empty(NSIM)
    Ds=Dm[:,okv]/np.sqrt(Vv[okv])
    for a in range(0,NSIM,2000):
        e=rng.choice(np.array([-1.,1.]),size=(min(2000,NSIM-a),S));mx[a:a+2000]=(e@Ds).max(1)   # unilateral: ventaja de la dirección corta
    real_max=float(z[okv].max());pmax=float((np.sum(mx>=real_max)+1)/(NSIM+1))
    base=V.index((1,0,2,0,0));bm=used[:,base]
    # --- validación contra etapa A
    ma=(RA['slot']==415)&(RA['hi']==2)&(RA['ci']==1);print('validación base: trades',int(bm.sum()),'neto corto medio',float(Os[bm,base].mean()),'| etapa A:',int(ma.sum()),float(np.nanmean(RA['ns'][ma])),flush=True)
    res={'items':len(items),'sessions':int(S),'n_variants_eval':int(okv.sum()),'B2':{'real_max_z':real_max,'null_max_q95':float(np.quantile(mx,.95)),'p_max':pmax},'baseline':{'trades':int(bm.sum()),'mean_net_short':float(Os[bm,base].mean()),'z':float(z[base]),'stageA_trades':int(ma.sum()),'stageA_mean_net':float(np.nanmean(RA['ns'][ma]))}}
    # --- B1
    os_b=Os[bm,base];sb=sessions[bm];isb=is_mask[bm];ctr=np.array([items[k]['c'] for k in np.flatnonzero((slot_arr==415)&hasref&(delta>=1)&val[:,2])])
    sl_it=(slot_arr==415)&hasref&(delta>=1)&val[:,2];sess_it=isessions[sl_it]
    r1=dict(is_mean_plus2=float((os_b[isb]-2).mean()),oos_mean_plus2=float((os_b[~isb]-2).mean()),n_is=int(isb.sum()),n_oos=int((~isb).sum()))
    r1['R1']=bool(r1['is_mean_plus2']>0 and r1['oos_mean_plus2']>0)
    srt=np.sort(os_b)[::-1];r1['mean_without_top5']=float(srt[5:].mean());r1['R2']=bool(r1['mean_without_top5']>0)
    nb=[];
    for a in range(3):
        for hh in (2,4,6):
            vi=V.index((a,0,hh,0,0))
            if vi!=base:nb.append(dict(slot=SL[a],hold=HZ[hh],z=float(z[vi]),n=int(nvar[vi]),mean_net=float(Os[used[:,vi],vi].mean()) if used[:,vi].any() else None))
    r1['neighbors']=nb;r1['same_sign']=int(sum(1 for n_ in nb if n_['z']>0));r1['R3']=bool(r1['same_sign']>=6)
    bycn={};
    for c in ORDER:
        mm=ctr==c
        if mm.sum()>=1:bycn[c]={'n':int(mm.sum()),'mean_net':float(os_b[mm].mean())}
    big={k:v for k,v in bycn.items() if v['n']>=15};r1['by_contract']=bycn;r1['R4']=bool(len(big)>0 and sum(v['mean_net']>0 for v in big.values())>len(big)/2)
    ords=np.array([dt.date.fromordinal(int(s)).strftime('%Y-%m') for s in sb]);r1['by_month']={m_:{'n':int((ords==m_).sum()),'mean_net':float(os_b[ords==m_].mean())} for m_ in sorted(set(ords))}
    r1['frac_sessions_positive']=float((os_b>0).mean())
    # descriptivo: corto sin condición; largo tras bajada
    m_none=(slot_arr==415)&val[:,2];r1['short_no_cond']={'n':int(m_none.sum()),'mean_net':float(out[m_none,0,2,0,0].mean())}
    m_dn=(slot_arr==415)&hasref&(delta<=-1)&val[:,2];r1['long_after_down']={'n':int(m_dn.sum()),'mean_net':float(out[m_dn,1,2,0,0].mean())}
    r1['B1_robust']=bool(r1['R1'] and r1['R2'] and r1['R3'] and r1['R4']);res['B1']=r1
    # --- B2: réplica con selección en el 70 %
    ISm=is_mask;Dis=Dm[ISm];Vis=(Dis**2).sum(0);okis=(used[ISm].sum(0)>=15)&(Vis>0);zis=np.where(okis,Dis.sum(0)/np.sqrt(np.where(Vis>0,Vis,1)),-9)
    best=int(np.argmax(zis));Do=Dm[~ISm][:,best];Vo=(Do**2).sum();zo=float(Do.sum()/np.sqrt(Vo)) if Vo>0 else 0.
    E=np.random.default_rng(SEED+1).choice(np.array([-1.,1.]),size=(20000,len(Do)));nul=(E@Do)/np.sqrt(Vo) if Vo>0 else np.zeros(20000)
    a,b_,h,st,tg=V[best];res['B2']['selected_in_IS']={'slot':SL[a],'k':KS[b_],'hold':HZ[h],'stop':STOPS[st],'target':TARGS[tg],'z_is':float(zis[best]),'z_oos':zo,'p_oos':float((np.sum(nul>=zo)+1)/(20001)),'oos_n':int(used[~ISm][:,best].sum()),'oos_mean_net':float(Os[~ISm][used[~ISm][:,best],best].mean()) if used[~ISm][:,best].any() else None,'is_n':int(used[ISm][:,best].sum())}
    top=np.argsort(-z)[:15];res['B2']['top15_full']=[dict(slot=SL[V[t][0]],k=KS[V[t][1]],hold=HZ[V[t][2]],stop=STOPS[V[t][3]],target=TARGS[V[t][4]],z=float(z[t]),n=int(nvar[t]),mean_net=float(Os[used[:,t],t].mean())) for t in top]
    res['B2']['n_z_gt_2']=int((z[okv]>2).sum());res['B2']['frac_variants_positive_mean_net']=float(np.mean([Os[used[:,v],v].mean()>0 for v in range(nv) if okv[v]]))
    res['B2']['decision']='mejora detectada' if (pmax<=0.05 and res['B2']['selected_in_IS']['p_oos']<=0.05 and (res['B2']['selected_in_IS']['oos_mean_net'] or -1)>0) else 'ninguna variante se distingue de la celda base'
    # --- B0
    ie=np.array([it['ie'] for it in items]);ix60=np.array([it['ixs'][6] for it in items]);cc=np.array([it['c'] for it in items]);b0={}
    nt=[];sp=[];jmp=[];cnt=0
    for k,it in enumerate(items):
        if it['slot']!=415 or not it['val'][6]:continue
        tk=cache[it['c']];s0,s1=it['ie'],it['ixs'][6];nt.append(s1-s0);w=tk['px'][s0:s1+1].astype(np.int64);sp.append(float(np.median((tk['ask'][s0:s1+1]-tk['bid'][s0:s1+1]))));jmp.append(int(np.abs(np.diff(w)).max()) if len(w)>1 else 0)
    nt=np.array(nt);b0={'items_slot415_valid60':int(len(nt)),'ticks_in_window_p10_median_p90':[float(np.percentile(nt,10)),float(np.median(nt)),float(np.percentile(nt,90))],'frac_sessions_lt100_ticks':float((nt<100).mean()),'median_spread_ticks_in_window':float(np.median(sp)),'max_tick_jump_ticks':int(max(jmp))}
    allsp=np.concatenate([(cache[c]['ask'][::5000]-cache[c]['bid'][::5000]) for c in ORDER]);b0['median_spread_all_day_ticks']=float(np.median(allsp))
    b0['sessions_eligible']=len(elig);b0['by_contract_items']={c:int((cc==c).sum()) for c in ORDER}
    b0['flag']=bool(b0['frac_sessions_lt100_ticks']>0.10 or b0['max_tick_jump_ticks']>100);res['B0']=b0
    json.dump(res,open('/tmp/claude-0/ghostlocal/stageB_GC.json','w'),indent=1,default=float);print(json.dumps(res,indent=1,default=float))
if __name__=='__main__':main()
