#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,platform,time
from pathlib import Path
import numpy as np, pyarrow.parquet as pq
SRC=Path('/data/analysis/mgc/mgc_ticks_canonical_preholdout.parquet'); OUTROOT=Path('/data/analysis/mgc/artifacts'); BAR_N=25
COLS=['ts_utc_ns','price_ticks','bid_ticks','ask_ticks','volume','trade_date','state_reset_flag']
NAMES=['ts_start_ns','ts_end_ns','open_ticks','high_ticks','low_ticks','close_ticks','bid_open_ticks','ask_open_ticks','bid_close_ticks','ask_close_ticks','volume','trade_date','contract_id','tick_start_idx','tick_end_idx']
def sha256(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(8<<20),b''): h.update(b)
 return h.hexdigest()
def main():
 t=time.time(); pf=pq.ParquetFile(SRC); outs=[[] for _ in NAMES]; carry=None; global_idx=0; cid=-1; dropped=0
 def emit(a, base):
  nonlocal cid,dropped
  ts,p,bid,ask,vol,td,reset=a; n=len(td); usable=(n//BAR_N)*BAR_N; dropped+=n-usable
  if n and (bool(reset[0]) or cid<0): cid+=1
  if not usable:return
  ts=ts[:usable].reshape(-1,BAR_N); p=p[:usable].reshape(-1,BAR_N); bid=bid[:usable].reshape(-1,BAR_N); ask=ask[:usable].reshape(-1,BAR_N); vol=vol[:usable].reshape(-1,BAR_N); nb=p.shape[0]
  vals=[ts[:,0],ts[:,-1],p[:,0],p.max(1),p.min(1),p[:,-1],bid[:,0],ask[:,0],bid[:,-1],ask[:,-1],vol.sum(1,dtype=np.int64),np.full(nb,int(td[0]),np.int32),np.full(nb,cid,np.int16),base+np.arange(nb,dtype=np.int64)*BAR_N,base+np.arange(nb,dtype=np.int64)*BAR_N+(BAR_N-1)]
  for o,v in zip(outs,vals):o.append(np.ascontiguousarray(v))
 for batch in pf.iter_batches(batch_size=1_000_000,columns=COLS,use_threads=True):
  a=[batch.column(i).to_numpy(zero_copy_only=False) for i in range(len(COLS))]
  if carry is not None:
   a=[np.concatenate((x,y)) for x,y in zip(carry,a)]; base=global_idx-len(carry[0])
  else: base=global_idx
  td=a[5]; cuts=np.flatnonzero(td[1:]!=td[:-1])+1; starts=np.r_[0,cuts]; ends=np.r_[cuts,len(td)]
  carry=None
  for k,(s,e) in enumerate(zip(starts,ends)):
   if k==len(starts)-1:
    usable=((e-s)//BAR_N)*BAR_N
    if usable: emit([x[s:s+usable] for x in a],base+s)
    carry=[x[s+usable:e] for x in a]
   else: emit([x[s:e] for x in a],base+s)
  global_idx += batch.num_rows
 if carry is not None: dropped+=len(carry[0])
 arrays=[np.concatenate(x) if x else np.array([],dtype=np.int64) for x in outs]
 source_sha=sha256(SRC); roll=pf.schema_arrow.metadata[b'roll_schedule_sha256'].decode(); code_sha=sha256(Path(__file__)); artifact_id=hashlib.sha256(f'{source_sha}|{roll}|25|{code_sha}'.encode()).hexdigest()[:20]; out=OUTROOT/artifact_id; out.mkdir(parents=True,exist_ok=True); files={}
 for name,a in zip(NAMES,arrays):
  p=out/f'{name}.npy'; np.save(p,a,allow_pickle=False); files[name]={'file':p.name,'dtype':str(a.dtype),'shape':list(a.shape),'sha256':sha256(p)}
 manifest={'schema_version':'mgc_25t_arrays_v1','artifact_id':artifact_id,'immutable':True,'created_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'source':str(SRC),'source_sha256':source_sha,'roll_schedule_sha256':roll,'bar_spec':{'type':'trade_count','trades_per_bar':25,'session_boundary_policy':'reset_and_drop_incomplete_tail'},'holdout_first_trade_date':20260401,'holdout_opened':False,'rows_ticks':int(pf.metadata.num_rows),'rows_bars':int(len(arrays[0])),'dropped_session_tail_ticks':int(dropped),'files':files,'builder_sha256':code_sha,'runtime':{'python':platform.python_version(),'numpy':np.__version__}}
 (out/'manifest.json').write_text(json.dumps(manifest,indent=2)); (OUTROOT/'LATEST').write_text(artifact_id+'\n'); print(json.dumps({'artifact_dir':str(out),'bars':len(arrays[0]),'dropped_tail_ticks':dropped,'elapsed_s':round(time.time()-t,3)},indent=2))
if __name__=='__main__':main()
