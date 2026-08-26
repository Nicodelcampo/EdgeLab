from __future__ import annotations
import math
import numpy as np
from .bars import session_ids
DEFAULTS=dict(TapeWindowTicks=25,ScoreMode='AbsMagnitude',AbsorptionPct=90.0,AbsorptionLookback=500,MinHistoryBuckets=200,RequireFlowSideMatch=True,ImbalanceMode='Diagonal',TrapVolumeSource='AggressiveSide',TicksPerRow=1,ImbalanceRatio=3.0,MinStackedRows=2,MinTrapFrac=0.20,MinDeltaFilter=0.0,MinTrapVolume=0.0,MinExportVolume=1.0,UseWickFilter=True,WickZonePct=30.0,InvalidationMode='CloseThrough',MaxAgeBars=2000,MaxTouches=0,DrawZoneBand=True)
def _percentile(arr,q):
    if not arr:return float('nan')
    if len(arr)==1:return float(arr[0])
    tmp=sorted(arr);pos=max(0.,min(100.,float(q)))/100.*(len(tmp)-1);lo=int(math.floor(pos));hi=int(math.ceil(pos));return float(tmp[lo] if lo==hi else tmp[lo]+(tmp[hi]-tmp[lo])*(pos-lo))
def run(ticks,bars=None,footprints=None,params=None,chart_tz='UTC'):
    p={**DEFAULTS,**(params or {})};N=max(2,int(p['TapeWindowTicks']));look=max(10,int(p['AbsorptionLookback']));minhist=max(1,int(p['MinHistoryBuckets']));ring=[];zones=[];n=len(ticks.ts_ns);bar_seq=0;tick_size=float(ticks.tick_size);sess=session_ids(ticks.ts_ns);cuts=np.flatnonzero(np.diff(sess))+1;session_starts=np.r_[0,cuts];session_ends=np.r_[cuts,n]
    for session_start,session_end in zip(session_starts,session_ends):
      for st in range(int(session_start),int(session_end),N):
        en=min(st+N,int(session_end));residual=(en-st)<N;idx=np.arange(st,en,dtype=np.int64);px=ticks.price_ticks[idx];vol=ticks.volume[idx];bid=ticks.bid_ticks[idx];ask=ticks.ask_ticks[idx];bar_seq+=1;amap={};bmap={};flow=0.0
        for k in range(len(idx)):
            pr=int(px[k]);v=float(vol[k]);aq=int(ask[k]);bq=int(bid[k]);side=0
            if aq>0 and bq>0 and aq>=bq:
                if pr>=aq:side=1
                elif pr<=bq:side=-1
            if side==0:
                if k>0:side=1 if pr>int(px[k-1]) else (-1 if pr<int(px[k-1]) else 1)
                else:side=1
            m=amap if side>0 else bmap;m[pr]=m.get(pr,0.0)+v;flow+=v if side>0 else -v
        dt=float(int(px[-1])-int(px[0]));denom=1.0+abs(dt) if str(p['ScoreMode'])!='AbsDirectional' else 1.0+max(0.0,(1 if flow>0 else (-1 if flow<0 else 0))*dt);score=abs(flow)/denom
        if float(p['AbsorptionPct'])<=0:passed=True;thr=0.0
        elif len(ring)>=minhist:thr=_percentile(ring,float(p['AbsorptionPct']));passed=score>=thr
        else:thr=float('nan');passed=False
        if residual:passed=False
        rt=max(1,int(p['TicksPerRow']));ra={};rb={}
        for tk,v in amap.items():r=tk//rt;ra[r]=ra.get(r,0.0)+v
        for tk,v in bmap.items():r=tk//rt;rb[r]=rb.get(r,0.0)+v
        keys=sorted(set(ra)|set(rb));close2=2*int(px[-1]);hi=float(np.max(px))*tick_size;lo=float(np.min(px))*tick_size;rng=hi-lo;wh=hi-rng*float(p['WickZonePct'])/100.;wl=lo+rng*float(p['WickZonePct'])/100.;runs_by={}
        for side_name in ('buy','sell'):
            runs=[];cur=None;prev=None
            for r in keys:
                a=ra.get(r,0.0);b=rb.get(r,0.0);skip=abs(a-b)<float(p['MinDeltaFilter'])
                if str(p['ImbalanceMode'])=='Diagonal':br=a/max(rb.get(r-1,0.0),1.0);sr=b/max(ra.get(r+1,0.0),1.0)
                else:br=a/max(b,1.0);sr=b/max(a,1.0)
                rowp=(r*rt+(rt-1)/2.)*tick_size;row2=2*r*rt+(rt-1);q=(not skip and a>=1 and br>=float(p['ImbalanceRatio']) and row2>close2 and (not p['UseWickFilter'] or (rng>0 and rowp>=wh))) if side_name=='buy' else (not skip and b>=1 and sr>=float(p['ImbalanceRatio']) and row2<close2 and (not p['UseWickFilter'] or (rng>0 and rowp<=wl)));vv=(a if side_name=='buy' else b) if str(p['TrapVolumeSource'])=='AggressiveSide' else a+b
                if q:
                    if cur is not None and r==prev+1:cur['hi']=r;cur['vol']+=vv;cur['nrows']+=1
                    else:
                        if cur is not None:runs.append(cur)
                        cur={'lo':r,'hi':r,'vol':vv,'nrows':1}
                    prev=r
                elif cur is not None:runs.append(cur);cur=None;prev=None
            if cur is not None:runs.append(cur)
            runs_by[side_name]=runs
        if passed:
            flow_side=1 if flow>0 else (-1 if flow<0 else 0);barvol=float(np.sum(vol))
            for isbull,runs,match in ((True,runs_by['buy'],flow_side==1),(False,runs_by['sell'],flow_side==-1)):
                if p['RequireFlowSideMatch'] and not match:continue
                cand=[r for r in runs if r['nrows']>=int(p['MinStackedRows'])]
                if not cand:continue
                best=max(cand,key=lambda r:r['vol'])
                if best['vol']<=0 or best['vol']<float(p['MinExportVolume']) or best['vol']<float(p['MinTrapVolume']) or best['vol']/max(barvol,1.0)<float(p['MinTrapFrac']):continue
                zones.append({'id':f"{bar_seq}_{'B' if isbull else 'S'}",'dir':'short' if isbull else 'long','sig_idx':int(en-1),'sig_ts':int(ticks.ts_ns[en-1]),'a_score':score,'a_thr':thr})
        if not residual:
            if len(ring)>=look:ring.pop(0)
            ring.append(score)
    return {'zones':zones,'n_zones':len(zones),'params':p,'events':[]}
