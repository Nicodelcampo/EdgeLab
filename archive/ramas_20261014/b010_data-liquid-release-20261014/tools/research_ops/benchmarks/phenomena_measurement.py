"""Synthetic only, single-pair engineering comparator; no market gain claim."""
import json,resource,time,hashlib
from unittest.mock import patch
import numpy as np
from tools.research_ops.confluence import phenomena as P
import argparse
p=argparse.ArgumentParser();p.add_argument('--out',required=True);args=p.parse_args()
n=500000;seq=np.arange(n,dtype=np.int64);ns=1781575200000000000+seq*10000000;px=10000+(seq%79);b=px-(seq%2);a=b+1;v=1+seq%9
class NaiveRange:
 def __init__(self,x):self.x=x
 def query(self,l,z):return self.x[l:z].min().item(),self.x[l:z].max().item()
def run(cls):
 start=time.perf_counter();h=hashlib.sha256()
 with patch.object(P,'RangeIndex',cls):
  m=P.ClockMeasurements()
  for r in m.measure(ns,seq,px,v,b,a,trade_date='2026-06-16'):h.update(json.dumps(r,sort_keys=True).encode())
 return {'seconds':time.perf_counter()-start,'logical_sha256':h.hexdigest(),'anchors':m.summary['anchors']}
base=run(NaiveRange);candidate=run(P.BlockedRangeIndex);assert base['logical_sha256']==candidate['logical_sha256']
r={'schema':'phenomena_synthetic_benchmark_v1','scope':'INVENTED_TAPE_NOT_MARKET_SPEEDUP','ticks':n,'baseline':base,'blocked_candidate':candidate,'order':'NAIVE_THEN_BLOCKED_SINGLE_PROCESS_SINGLE_PAIR_NOT_COLD_CACHE','logical_parity':True,'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'rss_scope':'WHOLE_SYNTHETIC_PROCESS_NOT_PER_VARIANT','whole_kaggle_speedup_measured':False}
open(args.out,'w').write(json.dumps(r,indent=2)+'\n')
print(json.dumps({'synthetic_logical_parity':True,'anchors':base['anchors'],'runtime_seconds_total':base['seconds']+candidate['seconds']}))
