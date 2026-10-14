#!/usr/bin/env python3
from pathlib import Path
import json,numpy as np,sys
sys.path.insert(0,'/data/EdgeLab')
from tools.run_mgc_tick_exact_finalists import replay
BR=Path('/data/analysis/mgc/artifacts')/Path('/data/analysis/mgc/artifacts/LATEST').read_text().strip();TR=Path('/data/analysis/mgc/tick_arrays')/Path('/data/analysis/mgc/tick_arrays/LATEST').read_text().strip();OUT=Path('/data/analysis/mgc/validation')
def l(r,n):return np.load(r/f'{n}.npy',mmap_mode='r')
SIG=l(BR,'signal_bar_idx');SD=l(BR,'signal_dir');END=l(BR,'tick_end_idx');P=l(TR,'price_ticks');B=l(TR,'bid_ticks');A=l(TR,'ask_ticks');CID=l(TR,'contract_id')
def synthetic():
 p=np.array([100,100,111,90,100,100,89,110],np.int32);b=p-1;a=p+1;cid=np.zeros(8,np.int16);td=np.ones(8,np.int32);sig=np.array([0,4]);sd=np.array([1,-1],np.int8);end=np.arange(8,dtype=np.int64)
 pnl,en,ex,d,r=replay(sig,sd,end,p,b,a,cid,td,10,10,1,.5)
 # long enters 101, TP=111 requires 112 so instead SL at tick3; short enters 99, TP=89 requires 88, SL at tick7
 return bool(len(pnl)==2 and np.all(r==1) and np.all(pnl<0) and np.all(ex==np.array([3,7])))
def verify_file(tp,limit=200):
 z=np.load(f'/data/analysis/mgc/tick_exact/normal_sl200_tp{tp}.npz');en=z['entry_i'];ex=z['exit_i'];dr=z['direction'];rs=z['reason'];pnl=z['pnl_ticks'];free=-1;k=0;checked=0;errs=[]
 for q,sbar in enumerate(SIG):
  i=int(END[sbar])+1
  if i<=free:continue
  if k>=len(en):break
  if i!=int(en[k]):errs.append(f'entry {k}');break
  d=int(dr[k]);e=int(A[i] if d==1 else B[i]);stop=e-d*200;targ=e+d*tp;j=i+1;expected_r=2;expected_x=None
  while j<len(P) and CID[j]==CID[i]:
   lp=int(P[j])
   if d==1 and lp<=stop: expected_r=1;expected_x=min(int(B[j]),stop);break
   if d==1 and lp>=targ+1: expected_r=0;expected_x=targ;break
   if d==-1 and lp>=stop: expected_r=1;expected_x=max(int(A[j]),stop);break
   if d==-1 and lp<=targ-1: expected_r=0;expected_x=targ;break
   j+=1
  if expected_x is None:j=min(j-1,len(P)-1);expected_x=int(B[j] if d==1 else A[j])
  expected_p=d*(expected_x-e)-.5
  if j!=int(ex[k]) or expected_r!=int(rs[k]) or expected_p!=float(pnl[k]):errs.append(f'exit/pnl {k}');break
  free=int(ex[k]);k+=1;checked+=1
  if checked>=limit:break
 return {'passed':not errs,'checked_trades':checked,'errors':errs}
def main():
 out={'schema_version':'mgc_stateful_kernel_verification_v1','synthetic_pass':synthetic(),'independent_python_path_checks':{str(tp):verify_file(tp) for tp in (300,400,450)},'note':'Independent pure-Python first-hit scan verifies causality, stop-before-target tie policy, trade-through, adverse quote fill, PnL and non-overlap on first 200 trades of each finalist.'};out['passed']=out['synthetic_pass'] and all(v['passed'] for v in out['independent_python_path_checks'].values());(OUT/'kernel_verification.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
if __name__=='__main__':main()
