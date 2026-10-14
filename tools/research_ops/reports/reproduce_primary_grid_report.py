"""Portable reproduction of previously published technical aggregate evidence.
No new market analysis, private rows, network, authority or workload launch.
"""
import json,hashlib,csv,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
import argparse
ap=argparse.ArgumentParser(description='Reproduce saved aggregate report; no market data or execution.')
ap.add_argument('--input',type=Path,default=ROOT/'docs/research/ops/FULL_PRIMARY_GRID_AGGREGATE.json')
ap.add_argument('--output-dir',type=Path,required=True)
args=ap.parse_args();OUT=args.output_dir.resolve()
if OUT.is_relative_to(ROOT):raise ValueError('output directory must be outside repo to preserve committed evidence')
OUT.mkdir(parents=True,exist_ok=True)
from tools.research_ops.audits.review_primary_grid_receipt import review,PROGRAMS
raw=args.input;j=json.loads(raw.read_bytes());h=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
r=review(raw,expected_receipt_sha256=h(raw),expected_source_commit='8d08c657ac8eba76abe9959bd80a037f97e466a6',expected_program_sha256={p:h((ROOT/p)) for p in PROGRAMS})
names={'input_load_and_identity':'Carga e identidad','frozen_draws_and_weights':'Sorteos y pesos','count_formation':'Formación de conteos','resampling_and_metrics':'Remuestreo y métricas','reference_compare_and_hash':'Comparación y hashes'}
rows=sorted([{'stage':k,'label':names[k],'seconds':v} for k,v in j['stage_seconds'].items()],key=lambda r:r['seconds'],reverse=True)
assert rows[0]['stage']=='resampling_and_metrics' and len(rows)==5
# Separate direct nested-raw maximum/sum check, not from sorted chart rows.
assert max(j['stage_seconds'],key=j['stage_seconds'].get)==rows[0]['stage']
assert abs(sum(row['seconds'] for row in rows)-sum(j['stage_seconds'].values()))<1e-9
unassigned=j['wall_seconds']-sum(j['stage_seconds'].values());assert 0<=unassigned<1
with open(OUT/'full-grid-stages.csv','w') as f:
 w=csv.DictWriter(f,fieldnames=['stage','label','seconds']);w.writeheader();w.writerows(rows)
e={'schema':'mnq_full_primary_grid_interpretation_v1','aggregate_sha256':h(raw),'kernel_id':138362721,'version':1,'execution_output_id':357738247,'url':'https://www.kaggle.com/code/nicolasbuttaro/edgelab-mnq-full-primary-grid-parity','review':r,'rows_checked':11340,'nonempty_rows':11340-j['empty_rows'],'empty_rows':j['empty_rows'],'fields_per_row':19,'field_comparisons':11340*19,'scope':'All primary-effects rows for fixed primary geometry MNQ09-26 only, from already-thinned events. Excludes detector/features/thinning/matched/incremental/full campaign.','stage_seconds':j['stage_seconds'],'wall_seconds':j['wall_seconds'],'outer_seconds':j['outer_seconds'],'unassigned_seconds':unassigned,'technical_replay_ru_maxrss_bytes':j['ru_maxrss_bytes'],'memory_caveat':'Self high-water for this technical replay, not original job or authenticated custody. 4GiB address-space cap is not proof of historical RSS.','performance_caveat':'Candidate-only single replay; not cold/warm paired full-grid speed test, no full-pipeline speedup estimate.','adoption_authorized':False,'validated_edge':False,'holdout_opened':False,'pnl_computed':False,'comparison_plan':[{'grain':'instrumented stage','population':'one existing-input primary-grid technical replay','unit':'wall seconds','finding':'Resampling/metrics is the largest measured substep of this replay, not the longevity detector','derivation':'direct fixed stage counters; maximum cross-check','disposition':'chart','reason':'show where time remained after candidate; explicitly limited scope'}]}
(OUT/'full-grid-interpretation.json').write_text(json.dumps(e,indent=2)+'\n')
s={'version':1,'form':'categorical-bars','mode':'grouped','orientation':'horizontal','subjectIndex':0,'title':'Remuestreo: 42,2 s del replay técnico','aside':'MNQ09-26 · 11.340 filas · segundos por etapa · detector y features no medidos','labels':[r['label'] for r in rows],'axis':{'zero':True},'series':[{'label':'Tiempo del replay','valueKind':'number','role':'subject','data':[r['seconds'] for r in rows]}]}
(OUT/'full-grid-chart-spec.json').write_text(json.dumps(s,ensure_ascii=False))
print('Coverage checked:',e['rows_checked'],'rows;',e['field_comparisons'],'field comparisons; missing bands preserved')
