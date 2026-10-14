from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
import json,sys,time
import numpy as np
import pyarrow.parquet as pq
import pyarrow.dataset as ds
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from edgelab.bridge.ticks import TickSeries
from edgelab.bridge.indicators import bigtrap2absorption as bt2
from edgelab.research.ym_bt2a_density_corridors import causal_zone_from_bt2,density_profile
from edgelab.research.ym_wall_contact_orderflow import aggressor_sign
from edgelab.research.nq_target_free import month_slices,quantiles as q,DISCOVERY_END_NS
RAW=Path('/data/raw/nq-kaggle/extracted');OUT=Path('/data/analysis/nq-prior-density-target-free');OUT.mkdir(parents=True,exist_ok=True);FILES=['NQ_09-25_ticks.parquet','NQ_12-25_ticks.parquet','NQ_03-26_ticks.parquet'];COLS=['ts_utc_ns','sequence','price_ticks','bid_ticks','ask_ticks','volume','aggressor'];MAX_TICKS_PER_SLICE=1_000_000
def file_hash(p):
 h=sha256()
 with open(p,'rb')as f:
  for b in iter(lambda:f.read(8<<20),b''):h.update(b)
 return h.hexdigest()
def bounds(p):
 pf=pq.ParquetFile(p);idx=pf.schema_arrow.names.index('ts_utc_ns');stats=[pf.metadata.row_group(i).column(idx).statistics for i in range(pf.metadata.num_row_groups)];return min(int(x.min)for x in stats if x),max(int(x.max)for x in stats if x)
start=time.time();slices=[];A={k:[]for k in('width','strength','volume','fraction','density1','density4','confluence1','confluence4','prior_density1','prior_density4','prior_confluence1','prior_confluence4','delta_density1','delta_density4')};source_hashes={};tot={'ticks':0,'zones':0,'buy':0,'sell':0,'unclassified':0,'mismatch':0}
for name in FILES:
 p=RAW/name;source_hashes[name]=file_hash(p);mn,mx=bounds(p)
 for month,a,b in month_slices(mn,mx):
  t=ds.dataset(str(p),format='parquet').scanner(columns=COLS,filter=(ds.field('ts_utc_ns')>=a)&(ds.field('ts_utc_ns')<b)).head(MAX_TICKS_PER_SLICE)
  if not t.num_rows:continue
  def col(k,d=None):
   x=t[k].to_numpy(zero_copy_only=False);return x.astype(d,copy=False)if d else x
  ts=col('ts_utc_ns',np.int64);seq=col('sequence',np.int64);px=col('price_ticks',np.int64);bid=col('bid_ticks',np.int64);ask=col('ask_ticks',np.int64);vol=col('volume',np.float64);agg=np.asarray(t['aggressor'].to_pylist(),dtype=object);contract=str(pq.ParquetFile(p).read_row_group(0,columns=['contract'])['contract'][0].as_py());raw=sorted(bt2.run(TickSeries(ts,px,vol,bid,ask,seq,1.,'NQ',contract,str(p)),params=bt2.DEFAULTS)['zones'],key=lambda z:int(z['sig_idx']));zones=[causal_zone_from_bt2(z,ts)for z in raw];sgn=aggressor_sign(px,bid,ask);explicit=np.where(agg=='buy',1,np.where(agg=='sell',-1,0)).astype(np.int8);classified=explicit!=0;metrics={k:[]for k in A};dirs={'long':0,'short':0}
  for i,z in enumerate(zones):
   dirs[z.direction]+=1;metrics['width'].append(z.hi_ticks-z.lo_ticks);metrics['strength'].append(z.strength_ratio);metrics['volume'].append(z.volume);metrics['fraction'].append(z.trap_fraction);center=(z.lo_ticks+z.hi_ticks)/2;hist=zones[:i+1];prior=zones[:i]
   for sigma,dk,ck,pdk,pck,ddk in((1.,'density1','confluence1','prior_density1','prior_confluence1','delta_density1'),(4.,'density4','confluence4','prior_density4','prior_confluence4','delta_density4')):
    total=float(density_profile(hist,asof_idx=z.available_idx,asof_ns=z.available_ns,origin_price_ticks=center,trade_direction=z.direction,offsets=[0],sigma_ticks=sigma,scope='support')[0]);pre=float(density_profile(prior,asof_idx=z.available_idx,asof_ns=z.available_ns,origin_price_ticks=center,trade_direction=z.direction,offsets=[0],sigma_ticks=sigma,scope='support')[0]);metrics[dk].append(total);metrics[pdk].append(pre);metrics[ddk].append(total-pre);metrics[ck].append(sum(1 for old in hist if old.direction==z.direction and old.available_idx<=z.available_idx and max(old.lo_ticks-center,center-old.hi_ticks,0)<=sigma));metrics[pck].append(sum(1 for old in prior if old.direction==z.direction and old.available_idx<z.available_idx and max(old.lo_ticks-center,center-old.hi_ticks,0)<=sigma))
  buy=int(np.sum(explicit==1));sell=int(np.sum(explicit==-1));unc=int(np.sum(explicit==0));mm=int(np.sum(classified&(sgn!=explicit)));row={'file':name,'contract':contract,'month':month,'ticks':len(ts),'zones':len(zones),'direction_counts':dirs,'aggressor':{'buy':buy,'sell':sell,'unclassified':unc,'inferred_mismatch_count':mm,'inferred_mismatch_rate':mm/max(1,buy+sell)}}
  for k,v in metrics.items():row[k+'_quantiles']=q(v);A[k]+=v
  slices.append(row);tot['ticks']+=len(ts);tot['zones']+=len(zones);tot['buy']+=buy;tot['sell']+=sell;tot['unclassified']+=unc;tot['mismatch']+=mm;print(json.dumps({'file':name,'month':month,'ticks':len(ts),'zones':len(zones)}),flush=True)
summary={'schema':'nq_bt2a_prior_density_target_free_v1','episode_id':'EPISODE-NQ-BT2A-PRIOR-DENSITY-009','unit_of_analysis':'contract_month_reset_first_1000000_ticks','sampling_contract':'FIRST_1000000_TICKS_PER_CONTRACT_MONTH','max_ticks_per_slice':MAX_TICKS_PER_SLICE,'formation_spec':'tick_count:25','discovery_end_exclusive_ns':DISCOVERY_END_NS,'outcomes_accessed':False,'validation_accessed':False,'holdout_accessed':False,'source_hashes':source_hashes,'totals':tot|{'mismatch_rate':tot['mismatch']/max(1,tot['buy']+tot['sell'])},'aggregate':{k+'_quantiles':q(v)for k,v in A.items()},'slices':slices,'runtime_seconds':time.time()-start,'completed_at_utc':datetime.now(timezone.utc).isoformat()};raw=json.dumps(summary,sort_keys=True,separators=(',',':')).encode();summary['evidence_sha256']=sha256(raw).hexdigest();(OUT/'summary.json').write_text(json.dumps(summary,indent=2,sort_keys=True));print(json.dumps({'ticks':tot['ticks'],'zones':tot['zones'],'slices':len(slices),'mismatch_rate':summary['totals']['mismatch_rate'],'evidence_sha256':summary['evidence_sha256'],'runtime_seconds':round(summary['runtime_seconds'],2)},indent=2),flush=True)
