"""Invented dense geometry benchmark; each engine in a fresh subprocess."""
import argparse,hashlib,json,resource,subprocess,sys,time
from collections import Counter
from pathlib import Path
from tools.research_ops.confluence.asof_intersections import Clock,ZoneKey,Snapshot
from tools.research_ops.confluence.episodes import EpisodeStream
from tools.research_ops.confluence.geometry_counts import GeometryCountStream

def worker(mode,n):
 cls=EpisodeStream if mode=='reference' else GeometryCountStream
 s=cls(contract='INVENTED',tape_sha256='a'*64,trade_date='2026-06-16',max_pairs=150000 if mode=='reference' else 50000)
 h=hashlib.sha256();total=Counter();start=time.perf_counter()
 for i in range(2*n):
  c=Clock(100+i,i);key=ZoneKey('AVZP2' if i<n else 'BT2','a'*64,'b'*64,str(i));x=Snapshot(key,0,c,c,0,10)
  events=s.apply(c,upserts=[x]);counts=Counter(e.action+':'+ '+'.join(sorted(z.key.family for z in e.episode.components)) for e in events) if mode=='reference' else events
  total.update(counts);h.update(json.dumps(dict(counts),sort_keys=True).encode())
 return {'mode':mode,'seconds':time.perf_counter()-start,'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'logical_counts_sha256':h.hexdigest(),'counts':dict(total),'active_zones':len(s.join.active),'retained_live_pairs':len(s.pairs) if mode=='reference' else 0,'peak_affected_pairs':None if mode=='reference' else s.peak_affected_pairs}

def main():
 p=argparse.ArgumentParser();p.add_argument('--worker',choices=['reference','candidate']);p.add_argument('--out',required=True);p.add_argument('--zones-per-family',type=int,default=240);a=p.parse_args()
 if not 1<=a.zones_per_family<=300:raise ValueError('bounded invented fixture')
 if a.worker:r=worker(a.worker,a.zones_per_family)
 else:
  results=[]
  for mode in ('reference','candidate'):
   dest=Path(a.out).with_suffix('.'+mode+'.json');subprocess.run([sys.executable,'-m',__spec__.name,'--worker',mode,'--out',str(dest),'--zones-per-family',str(a.zones_per_family)],check=True,timeout=120);results.append(json.loads(dest.read_bytes()))
  assert results[0]['logical_counts_sha256']==results[1]['logical_counts_sha256']
  r={'schema':'geometry_counts_synthetic_benchmark_v1','scope':'INVENTED_PAIR_DENSITY_NOT_MARKET_SPEEDUP','results':results,'logical_count_parity':True,'declared_capacity_change':'REFERENCE_EXPANDED_LIVE_CAP_150000_FOR_ORACLE; CANDIDATE_AFFECTED_CLOCK_CAP_50000','full_episode_identity_parity_claimed':False,'market_job_speedup_measured':False,'fixture_limitation':'DENSE_PAIRS_ONLY; random mixed families/triples/revisions checked separately in unit tests','replicates':1,'cache_order':'ONE_FRESH_PROCESS_PER_ENGINE_REFERENCE_THEN_CANDIDATE','data_exported':False}
 Path(a.out).write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
