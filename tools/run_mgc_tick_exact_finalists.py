#!/usr/bin/env python3
from pathlib import Path
import json,time
import numpy as np
from numba import njit
BROOT=Path('/data/analysis/mgc/artifacts')/Path('/data/analysis/mgc/artifacts/LATEST').read_text().strip();TROOT=Path('/data/analysis/mgc/tick_arrays')/Path('/data/analysis/mgc/tick_arrays/LATEST').read_text().strip();OUT=Path('/data/analysis/mgc/tick_exact');OUT.mkdir(parents=True,exist_ok=True)
def l(r,n):return np.load(r/f'{n}.npy',mmap_mode='r')
SIG=l(BROOT,'signal_bar_idx');SD=l(BROOT,'signal_dir');END=l(BROOT,'tick_end_idx');P=l(TROOT,'price_ticks');B=l(TROOT,'bid_ticks');A=l(TROOT,'ask_ticks');CID=l(TROOT,'contract_id');TD=l(TROOT,'trade_date')
@njit(cache=True)
def replay(sig,sd,end,p,b,a,cid,td,sl,tp,mult,fees):
 nmax=sig.size; pnl=np.empty(nmax,np.float64);en=np.empty(nmax,np.int64);ex=np.empty(nmax,np.int64);dr=np.empty(nmax,np.int8);rs=np.empty(nmax,np.int8);n=0;free=-1
 for k in range(sig.size):
  dec=end[sig[k]]; i=dec+1
  if i<=free or i>=p.size:continue
  d=sd[k]*mult;e=a[i] if d==1 else b[i];stop=e-d*sl;targ=e+d*tp;j=i+1
  while j<p.size and cid[j]==cid[i]:
   lp=p[j]
   if d==1:
    if lp<=stop:x=min(b[j],stop);r=1;break
    if lp>=targ+1:x=targ;r=0;break
   else:
    if lp>=stop:x=max(a[j],stop);r=1;break
    if lp<=targ-1:x=targ;r=0;break
   j+=1
  if j>=p.size or cid[j]!=cid[i]:j=min(j-1,p.size-1);x=b[j] if d==1 else a[j];r=2
  pnl[n]=d*(x-e)-fees;en[n]=i;ex[n]=j;dr[n]=d;rs[n]=r;n+=1;free=j
 return pnl[:n],en[:n],ex[:n],dr[:n],rs[:n]
def main():
 t=time.time();rows=[]
 for sl,tp in [(200,300),(200,400),(200,450)]:
  pnl,en,ex,d,r=replay(SIG,SD,END,P,B,A,CID,TD,sl,tp,1,.5);np.savez_compressed(OUT/f'normal_sl{sl}_tp{tp}.npz',pnl_ticks=pnl,entry_i=en,exit_i=ex,direction=d,reason=r,entry_trade_date=TD[en],exit_trade_date=TD[ex],contract_id=CID[en])
  rows.append({'direction':'normal','sl_ticks':sl,'tp_ticks':tp,'trades':int(len(pnl)),'net_ticks':float(pnl.sum()),'ticks_per_trade':float(pnl.mean()),'win_rate':float((pnl>0).mean()),'tp_exits':int((r==0).sum()),'sl_exits':int((r==1).sum()),'roll_exits':int((r==2).sum())})
 out={'schema_version':'mgc_tick_exact_finalists_v1','bar_artifact_id':BROOT.name,'tick_artifact_id':TROOT.name,'signals':int(len(SIG)),'execution':'EdgeLab causal next-tick bid/ask; TP one-tick trade-through; stop by last filled at adverse bid/ask; non-overlap; forced flat at contract roll; 0.5 tick RT fee','holdout_opened':False,'results':rows,'elapsed_s':round(time.time()-t,3)};(OUT/'results.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
if __name__=='__main__':main()
