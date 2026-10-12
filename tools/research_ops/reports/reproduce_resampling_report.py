"""Portable reproduction of previously published technical aggregate evidence.
No new market analysis, private rows, network, authority or workload launch.
"""
import json,hashlib,statistics,csv,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
import argparse
ap=argparse.ArgumentParser(description='Reproduce saved aggregate report; no market data or execution.')
ap.add_argument('--input',type=Path,default=ROOT/'docs/research/ops/MNQ_RESAMPLING_REPLAY_AGGREGATE.json')
ap.add_argument('--output-dir',type=Path,required=True)
args=ap.parse_args();OUT=args.output_dir.resolve()
if OUT.is_relative_to(ROOT):raise ValueError('output directory must be outside repo to preserve committed evidence')
OUT.mkdir(parents=True,exist_ok=True)
from tools.research_ops.benchmarks.mnq_resampling_replay import PLAN,plan_hash
raw=args.input;x=json.loads(raw.read_bytes())
assert x['schema']=='mnq_resampling_technical_replay_v1' and x['plan']==PLAN and x['plan_sha256']==plan_hash()
assert x['source_checkpoint']=='4e3ecb3cdd2b005272547c3cec94b47de548e9c8'
assert x['cells']==60 and x['empty_cells']==20 and x['outer_seconds']<=900
assert x['exact_parity'] is True and all(x[k] is False for k in ['full_pipeline_parity','private_rows_exported','old_job_rss_measured','validated_edge','adoption_authorized'])
for p,h in x['program_sha256'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h
rows=[];digests=[]
for i,p in enumerate(x['pairs']):
 assert p['pair']==i+1 and p['order']==(['candidate','baseline'] if i==1 else ['baseline','candidate'])
 for method in ['baseline','candidate']:
  v=p[method];assert v['method']==method and 0<v['ru_maxrss_bytes']<PLAN['memory_bytes']
  assert [r['label'] for r in v['runs']]==['cold','warm']
  for r in v['runs']:
   assert 0<r['seconds']<120;digests.append(r['digest']);rows.append({'pair':i+1,'method':method,'pass':r['label'],'seconds':r['seconds'],'ru_maxrss_bytes':v['ru_maxrss_bytes']})
assert len(rows)==12 and len(set(digests))==1
with open(OUT/'replay-times.csv','w') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
medians={};ratios={};ranges={}
for label in ['cold','warm']:
 medians[label]={method:statistics.median(r['seconds'] for r in rows if r['pass']==label and r['method']==method) for method in ['baseline','candidate']}
 ratios[label]=medians[label]['baseline']/medians[label]['candidate']
 # Independent median check: direct sorted raw nested values, no flattened rows.
 for method in ['baseline','candidate']:
  v=sorted(next(r['seconds'] for r in p[method]['runs'] if r['label']==label) for p in x['pairs']);assert v[1]==medians[label][method]
 paired=[next(r['seconds'] for r in p['baseline']['runs'] if r['label']==label)/next(r['seconds'] for r in p['candidate']['runs'] if r['label']==label) for p in x['pairs']];ranges[label]=[min(paired),max(paired)]
e={'schema':'mnq_resampling_technical_replay_interpretation_v1','raw_aggregate_sha256':hashlib.sha256(raw.read_bytes()).hexdigest(),'kernel_id':138361151,'version':1,'execution_output_id':357734641,'url':'https://www.kaggle.com/code/nicolasbuttaro/edgelab-mnq-0926-resampling-technical-replay','source_checkpoint':x['source_checkpoint'],'observed_status':'COMPLETE','exact_result_digest':digests[0],'cells':60,'nonempty_cells':40,'sessions':46,'draws':10000,'private_input_rows':x['private_input_rows'],'medians_seconds':medians,'ratio_of_medians':ratios,'paired_speedup_range':ranges,'outer_seconds':x['outer_seconds'],'prepare_seconds':x['prepare_seconds'],'worker_ru_maxrss_bytes':[min(r['ru_maxrss_bytes'] for r in rows),max(r['ru_maxrss_bytes'] for r in rows)],'rss_caveat':'Self-reported Linux isolated-process high-water counter includes process creation/import/load, potentially inherited pre-exec footprint. Identical counters provide no memory-improvement evidence. Not historical whole-job telemetry or authenticated custody.','population':'Prespecified primary-geometry session resampling only; 60 cells including20 empty; 3pairs cold/warm. No CI or full-pipeline speedup inference.','full_pipeline_parity':False,'adoption_authorized':False,'validated_edge':False,'holdout_opened':False,'pnl_computed':False,'comparison_plan':[{'grain':'first/second compute pass','population':'fixed60cells per fresh worker','unit':'seconds median across3pairs','finding':f"Candidate {ratios['cold']:.2f}x cold / {ratios['warm']:.2f}x warm on this resampling substep only",'derivation':'separate per-method median; ratio of medians','disposition':'chart','reason':'Same input/output digest, same units and fixed scope'},{'grain':'worker','population':'six fresh processes','unit':'bytes Linux ru_maxrss','finding':'identical counters; no memory-improvement evidence','disposition':'prose','reason':'inherited highwater caveat; not an optimization measure'}]}
(OUT/'replay-interpretation.json').write_text(json.dumps(e,indent=2)+'\n')
spec={'version':1,'form':'categorical-bars','mode':'grouped','title':'Remuestreo: ~3,38× más rápido, con paridad exacta','aside':'Mediana de 3 pares · segundos para las mismas 60 celdas · no mide la corrida completa','labels':['Primer pase','Segundo pase'],'axis':{'zero':True},'series':[{'label':'Cálculo congelado','valueKind':'number','role':'base','data':[medians[p]['baseline'] for p in ['cold','warm']]},{'label':'Candidato','valueKind':'number','role':'subject','data':[medians[p]['candidate'] for p in ['cold','warm']]}]}
(OUT/'replay-chart-spec.json').write_text(json.dumps(spec,ensure_ascii=False))
print(json.dumps({'medians':medians,'speedups':ratios,'pair_ranges':ranges,'rss':e['worker_ru_maxrss_bytes'],'outer_seconds':e['outer_seconds']},indent=2))
