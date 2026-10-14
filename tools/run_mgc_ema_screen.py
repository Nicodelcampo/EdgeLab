#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,time
import numpy as np
from numba import njit,prange
ROOT=Path('/data/analysis/mgc/artifacts')/Path('/data/analysis/mgc/artifacts/LATEST').read_text().strip(); OUT=Path('/data/analysis/mgc/ema_screen');OUT.mkdir(parents=True,exist_ok=True)
def load(n):return np.load(ROOT/f'{n}.npy',mmap_mode='r')
C=load('close_ticks'); H=load('high_ticks'); L=load('low_ticks'); BO=load('bid_open_ticks'); AO=load('ask_open_ticks'); BC=load('bid_close_ticks'); AC=load('ask_close_ticks'); CID=load('contract_id'); TD=load('trade_date')
@njit(cache=True)
def ema(x,cid,span):
 o=np.empty(x.size,np.float64);a=2/(span+1.0);o[0]=x[0]
 for i in range(1,x.size):o[i]=x[i] if cid[i]!=cid[i-1] else a*x[i]+(1-a)*o[i-1]
 return o
@njit(cache=True)
def signals(e2,e5,e20,cid):
 idx=np.empty(e2.size,np.int64);d=np.empty(e2.size,np.int8);n=0;warm=0
 for i in range(1,e2.size-1):
  if cid[i]!=cid[i-1]:warm=0
  else:warm+=1
  if warm<2000:continue
  if e2[i]>e5[i] and e2[i-1]<=e5[i-1] and e5[i]>e20[i]:idx[n]=i;d[n]=1;n+=1
  elif e2[i]<e5[i] and e2[i-1]>=e5[i-1] and e5[i]<e20[i]:idx[n]=i;d[n]=-1;n+=1
 return idx[:n],d[:n]
@njit(cache=True)
def replay_one(sig,dirs,h,l,bo,ao,bc,ac,cid,td,sl,tp,mult,fees,maxtr):
 pnl=np.empty(maxtr,np.float64);ent=np.empty(maxtr,np.int64);ext=np.empty(maxtr,np.int64);dr=np.empty(maxtr,np.int8);rs=np.empty(maxtr,np.int8);n=0;free=0
 for k in range(sig.size):
  s=sig[k]; i=s+1
  if i<=free or i>=h.size:continue
  d=dirs[k]*mult; e=ao[i] if d==1 else bo[i]; stop=e-d*sl; targ=e+d*tp; j=i
  while j<h.size and cid[j]==cid[i]:
   # conservative ambiguity: stop before target
   if d==1:
    if l[j]<=stop: x=min(bc[j],stop);reason=1;break
    if h[j]>=targ+1: x=targ;reason=0;break
   else:
    if h[j]>=stop: x=max(ac[j],stop);reason=1;break
    if l[j]<=targ-1: x=targ;reason=0;break
   j+=1
  if j>=h.size or cid[j]!=cid[i]:
   j=min(j-1,h.size-1);x=bc[j] if d==1 else ac[j];reason=2
  pnl[n]=d*(x-e)-fees;ent[n]=i;ext[n]=j;dr[n]=d;rs[n]=reason;n+=1;free=j
 return pnl[:n],ent[:n],ext[:n],dr[:n],rs[:n]
@njit(parallel=True,cache=True)
def grid(sig,dirs,h,l,bo,ao,bc,ac,cid,td,sls,tps,mults,fees):
 n=len(sls);out=np.empty((n,8),np.float64)
 for q in prange(n):
  p,e,x,d,r=replay_one(sig,dirs,h,l,bo,ao,bc,ac,cid,td,sls[q],tps[q],mults[q],fees,sig.size)
  out[q,0]=p.size;out[q,1]=p.sum();out[q,2]=p.mean() if p.size else np.nan;out[q,3]=(p>0).mean() if p.size else np.nan;out[q,4]=(r==0).sum();out[q,5]=(r==1).sum();out[q,6]=(r==2).sum();out[q,7]=p.std() if p.size else np.nan
 return out
def main():
 t=time.time();e2=ema(C,CID,200);e5=ema(C,CID,500);e20=ema(C,CID,2000);sig,d=signals(e2,e5,e20,CID)
 for n,a in [('ema200',e2),('ema500',e5),('ema2000',e20),('signal_bar_idx',sig),('signal_dir',d)]:np.save(ROOT/f'{n}.npy',a)
 slv=[100,150,200];tpv=[150,200,250,300,350,400,450];cfg=[(m,s,tp) for m in (1,-1) for s in slv for tp in tpv]
 sl=np.array([x[1] for x in cfg],np.int64);tp=np.array([x[2] for x in cfg],np.int64);mu=np.array([x[0] for x in cfg],np.int8);res=grid(sig,d,H,L,BO,AO,BC,AC,CID,TD,sl,tp,mu,.5)
 rows=[]
 for c,r in zip(cfg,res):rows.append({'direction':'normal' if c[0]==1 else 'inverse','sl_ticks':c[1],'tp_ticks':c[2],'be':'off','entry':'immediate','trades':int(r[0]),'net_ticks':float(r[1]),'ticks_per_trade':float(r[2]),'win_rate':float(r[3]),'tp_exits':int(r[4]),'sl_exits':int(r[5]),'roll_exits':int(r[6]),'pnl_sd':float(r[7])})
 rows.sort(key=lambda x:x['net_ticks'],reverse=True)
 payload={'schema_version':'mgc_ema_screen_v1','artifact_id':ROOT.name,'signal_definition':'EMA200 crosses EMA500, gated by EMA500 on same side of EMA2000; 2000-bar warmup per contract; decision at bar close','signals':int(sig.size),'grid_pre_registered':{'direction':['normal','inverse'],'entry':['immediate'],'sl_ticks':slv,'tp_ticks':tpv,'be':['off'],'n_configs':len(cfg),'note':'Exact original 126-cell registry was not present in repository snapshot; this immutable 42-cell core grid was fixed before this run.'},'execution':'next 25T bar open at ask/bid; conservative stop-first ambiguity; TP requires one-tick trade-through; no overlap; force flat at roll; fees 0.5 ticks RT','results':rows,'elapsed_s':round(time.time()-t,3)}
 (OUT/'screen.json').write_text(json.dumps(payload,indent=2));print(json.dumps({'signals':sig.size,'configs':len(cfg),'elapsed_s':payload['elapsed_s'],'top5':rows[:5],'headline':[x for x in rows if x['direction']=='normal' and x['sl_ticks']==200 and x['tp_ticks'] in (300,450)]},indent=2))
if __name__=='__main__':main()
