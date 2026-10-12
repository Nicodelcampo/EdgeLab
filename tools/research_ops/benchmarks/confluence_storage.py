"""Fresh-DB synthetic paired storage microbenchmark, not market speed evidence."""
import argparse,hashlib,json,tempfile,time,statistics
from pathlib import Path
from types import SimpleNamespace
from tools.research_ops.confluence.market_pilot import PrivateStore
from tools.research_ops.confluence.compact_store import ClusteredPrivateStore
from tools.research_ops.confluence.detector_capture import Capture,PINS
from tools.research_ops.confluence.asof_intersections import Clock,ZoneKey

def run(*,records=100000,pairs=3):
    if type(records) is not int or not 1000<=records<=200000 or type(pairs) is not int or not 3<=pairs<=5:raise ValueError('bounded benchmark')
    sources=('tools/research_ops/confluence/market_pilot.py','tools/research_ops/confluence/compact_store.py','tools/research_ops/benchmarks/confluence_storage.py')
    source_pins={n:hashlib.sha256(Path(n).read_bytes()).hexdigest() for n in sources}
    configs=[{'indicator':'bigtrap2','config_sha256':hashlib.sha256(str(i).encode()).hexdigest()} for i in range(96)]
    tape=[(j%96,Capture(('BIRTH','TOUCH','CLASSIFY','REMOVE')[j%4],ZoneKey('BT2',configs[j%96]['config_sha256'],PINS['BT2'],str(j//4)),Clock(1781586000000000000+j//6,j%6),j,j//25,100+j%20,120+j%20,(-1,0,1)[j%3],(('size',float(j%101)),('sample','invented')), 'close' if j%4==3 else '')) for j in range(records)]
    rows=[];started=time.monotonic();reference=None
    with tempfile.TemporaryDirectory() as d:
        for pair in range(pairs):
            for name,cls in ([('baseline',PrivateStore),('clustered',ClusteredPrivateStore)] if pair%2==0 else [('clustered',ClusteredPrivateStore),('baseline',PrivateStore)]):
                if time.monotonic()-started>180:raise TimeoutError('synthetic benchmark budget')
                p=Path(d)/f'{pair}-{name}.sqlite';at=time.perf_counter();s=cls(p,configs,max_records=records,max_bytes=512*1024*1024)
                for cfg,c in tape:s.add(cfg,SimpleNamespace(records=(c,),unavailable_events=0),'2026-06-16')
                s.ready();write=time.perf_counter()-at;size=p.stat().st_size
                at=time.perf_counter();h=hashlib.sha256();read_rows=0
                for cfg in range(96):
                    for c in s.records(cfg):h.update(repr(c).encode());read_rows+=1
                read=time.perf_counter()-at;seal=([x.hexdigest() for x in s.hashes],h.hexdigest(),s.counts,s.target_counts,read_rows)
                if reference is None:reference=seal
                if seal!=reference or read_rows!=records:raise ValueError('ordered-output parity failure')
                rows.append({'pair':pair,'variant':name,'write_index_seconds':write,'read_reconstruct_seconds':read,'total_seconds':write+read,'database_bytes':size,'logical_replay_sha256':h.hexdigest()});s.db.close()
    med={name:{key:statistics.median(x[key] for x in rows if x['variant']==name) for key in ('write_index_seconds','read_reconstruct_seconds','total_seconds','database_bytes')} for name in ('baseline','clustered')}
    if source_pins!={n:hashlib.sha256(Path(n).read_bytes()).hexdigest() for n in sources}:raise ValueError('benchmark source changed while running')
    return {'schema':'confluence_storage_microbenchmark_v1','status':'SYNTHETIC_PARITY_ONLY_NOT_ADOPTED','records_per_variant':records,'configs':96,'paired_fresh_databases':pairs,'measurements':rows,'medians':med,'baseline_over_candidate_total_ratio':med['baseline']['total_seconds']/med['clustered']['total_seconds'],'candidate_over_baseline_bytes_ratio':med['clustered']['database_bytes']/med['baseline']['database_bytes'],'all_ordered_outputs_equal':True,'cold_warm_os_cache_controlled':False,'whole_job_or_peak_rss_measured':False,'market_data_read':False,'full_pipeline_speedup_measured':False,'candidate_activated':False,'source_sha256':source_pins}

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.out.exists():raise ValueError('new benchmark output required')
    r=run();a.out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:r[k] for k in ('status','records_per_variant','all_ordered_outputs_equal','baseline_over_candidate_total_ratio','candidate_over_baseline_bytes_ratio')}))
if __name__=='__main__':main()
