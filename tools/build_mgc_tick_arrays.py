#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,time
import numpy as np, pyarrow.parquet as pq
SRC=Path('/data/analysis/mgc/mgc_ticks_canonical_preholdout.parquet'); ROOT=Path('/data/analysis/mgc/tick_arrays')
COLS=['ts_utc_ns','price_ticks','bid_ticks','ask_ticks','trade_date','state_reset_flag']
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(8<<20),b''):h.update(b)
 return h.hexdigest()
def main():
 t=time.time();pf=pq.ParquetFile(SRC);n=pf.metadata.num_rows; src=sha(SRC); roll=pf.schema_arrow.metadata[b'roll_schedule_sha256'].decode(); code=sha(Path(__file__)); aid=hashlib.sha256(f'{src}|ticks|{code}'.encode()).hexdigest()[:20];out=ROOT/aid;out.mkdir(parents=True,exist_ok=True)
 specs={'ts_utc_ns':np.int64,'price_ticks':np.int32,'bid_ticks':np.int32,'ask_ticks':np.int32,'trade_date':np.int32,'contract_id':np.int16}; mm={k:np.lib.format.open_memmap(out/f'{k}.npy',mode='w+',dtype=v,shape=(n,)) for k,v in specs.items()}; pos=0;cid=-1
 for b in pf.iter_batches(batch_size=1_000_000,columns=COLS):
  a=[b.column(i).to_numpy(zero_copy_only=False) for i in range(len(COLS))];m=b.num_rows
  for k,x in zip(COLS[:5],a[:5]):mm[k][pos:pos+m]=x
  reset=a[5]; inc=reset.astype(np.int16,copy=True)
  if cid<0 and m and not bool(reset[0]): inc[0]=1
  ids=(cid+np.cumsum(inc,dtype=np.int32)).astype(np.int16)
  if m: cid=int(ids[-1])
  mm['contract_id'][pos:pos+m]=ids;pos+=m
 for x in mm.values():x.flush()
 files={k:{'file':f'{k}.npy','dtype':str(v),'shape':[n],'sha256':sha(out/f'{k}.npy')} for k,v in specs.items()}
 man={'schema_version':'mgc_tick_arrays_v1','artifact_id':aid,'immutable':True,'source_sha256':src,'roll_schedule_sha256':roll,'holdout_first_trade_date':20260401,'holdout_opened':False,'rows':n,'files':files,'builder_sha256':code,'elapsed_s':round(time.time()-t,3)};(out/'manifest.json').write_text(json.dumps(man,indent=2));(ROOT/'LATEST').write_text(aid+'\n');print(json.dumps({'artifact_dir':str(out),'rows':n,'elapsed_s':man['elapsed_s']},indent=2))
if __name__=='__main__':main()
