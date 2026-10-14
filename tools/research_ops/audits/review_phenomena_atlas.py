"""Aggregate-only closeout/analysis; never load private feature streams or ticks."""
import csv,json,hashlib
from pathlib import Path
from collections import Counter
import numpy as np
import argparse
from tools.research_ops.confluence.build_target_free_pilot import digest
ap=argparse.ArgumentParser(description='Reproduce aggregate atlas coverage, not remote authentication or scientific validation')
ap.add_argument('--evidence-dir',type=Path,default=Path(__file__).resolve().parents[3]/'docs/research/ops')
ap.add_argument('--raw-dir',type=Path,help='Optional folder with boot-receipt.json and atlas-receipt.json')
ap.add_argument('--out-dir',type=Path,required=True)
args=ap.parse_args();docs=args.evidence_dir;out=args.out_dir;out.mkdir(parents=True,exist_ok=True)
def load(p):
    p=Path(p)
    if p.stat().st_size>1048576:raise ValueError('aggregate file budget')
    return json.loads(p.read_bytes())
def raw_file(name):
    if args.raw_dir:return args.raw_dir/name
    return docs/('MNQ_PHENOMENA_ATLAS_BOOT_RECEIPT.json' if name=='boot-receipt.json' else 'MNQ_PHENOMENA_ATLAS_RECEIPT.json')
b=load(raw_file('boot-receipt.json'));a=load(raw_file('atlas-receipt.json'));p=load(docs/'MNQ_PHENOMENA_ATLAS_PACKAGE_RECEIPT.json');l=load(docs/'MNQ_PHENOMENA_ATLAS_LAUNCH.json');idc=load(docs/'MNQ_PHENOMENA_ATLAS_REMOTE_IDENTITY_CHECK.json');plan=load(docs/'MNQ_PHENOMENA_ATLAS_PLAN.json')
assert b['exit_code']==0 and b['stop_reason'] is None and b['transport_pin_verified']
for k in ('source_commit','bundle_sha256','plan_sha256'):assert b[k]==p[k]==l['job'][k]
assert idc['exact_request_source_verified'] and idc['notebook_source_sha256']==p['notebook_text_sha256']
assert hashlib.sha256((raw_file('atlas-receipt.json')).read_bytes()).hexdigest()==b['atlas_receipt_sha256']
assert a['plan_sha256']==p['plan_sha256']==digest(plan) and a['session_count']==3
assert [s['trade_date'] for s in a['sessions']]==plan['target_sessions']
assert all(a[k] is False for k in ('state_classification','outcomes','inference','raw_exported','private_rows_persisted','canonical_brain_written','holdout_opened','pnl'))
rows=[];primary=[];all_ticks=0;all_anchors=0
for s in a['sessions']:
 all_ticks+=s['measurement']['ticks'];all_anchors+=s['measurement']['anchors']
 for w,v in s['atlas'].items():
  n=s['measurement']['anchors'];nc=v['status_counts'].get('MEASURABLE_PAIR',0);unknown=v['status_counts'].get('UNKNOWN_PAIR',0)
  assert n==v['anchor_denominator']==nc+unknown
  for field in ('exclusive_reason_counts','joint_window_status_counts','direction_counts'):assert sum(v[field].values())==n
  assert s['measurement']['windows'][w]==v['status_counts']
  assert int(np.array(v['pressure_progress_cell_counts']).sum())==nc
  # Independent headline path through exclusive reasons, not status counts.
  assert nc==v['exclusive_reason_counts'].get('MEASURABLE_PAIR',0)
  counts=v['exclusive_reason_counts'];cg=counts.get('CURRENT_GAP_UNKNOWN',0);pg=counts.get('PRIOR_GAP_UNKNOWN',0);other=unknown-cg-pg;assert other>=0
  row={'trade_date':s['trade_date'],'window_seconds':int(w),'anchors':n,'measurable':nc,'unknown':unknown,'measurable_percent':100*nc/n,'current_gap_unknown':cg,'prior_gap_unknown':pg,'other_unknown':other};rows.append(row)
  for x in v['measurable_metrics'].values():assert x['count']==nc and ((x['quantiles'] is None)==(nc<100))
  if w=='20':
   m=np.array(v['pressure_progress_cell_counts']);cells=int(m[3:,2:4].sum());decay=int(m[:2,:].sum())
   primary.append({**row,'gap_share_of_unknown':(cg+pg)/unknown,'median_pressure_ratio':v['measurable_metrics']['pressure_ratio']['quantiles']['0.5'],
                   'median_directed_progress_ticks':v['measurable_metrics']['directed_progress_ticks']['quantiles']['0.5'],
                   'median_signed_volume_coverage_current_measurable':v['measurable_metrics']['current_signed_volume_coverage']['quantiles']['0.5'],
                   'median_mean_trade_size_ratio':v['measurable_metrics']['mean_trade_size_ratio']['quantiles']['0.5'],
                   'pressure_ratio_ge1_progress_in_neg2_to_2_count':cells,'pressure_ratio_lt_half_count':decay,
                   'these_continuous_cells_are_not_AE_labels':True})
assert all_ticks==a['total_ticks']
p0=load(docs/'MNQ_PHENOMENA_P0_MEASUREMENT_RECEIPT.json');last=a['sessions'][-1]
assert last['private_measurement_stream_sha256']==p0['private_feature_sha256']
assert {k:v for k,v in last['measurement'].items() if k!='seconds'}=={k:v for k,v in p0['measurement'].items() if k!='seconds'}
with (out/'phenomena_atlas_coverage.csv').open('w') as f:
 writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
pooled={'anchors':sum(r['anchors'] for r in primary),'measurable':sum(r['measurable'] for r in primary),'unknown':sum(r['unknown'] for r in primary),'gaps_first_failure':sum(r['current_gap_unknown']+r['prior_gap_unknown'] for r in primary)}
pooled['measurable_percent']=100*pooled['measurable']/pooled['anchors'];pooled['gap_share_of_unknown']=pooled['gaps_first_failure']/pooled['unknown']
e={'schema':'phenomena_atlas_aggregate_analysis_v1','job':l['job'],'kernel_slug':l['kernel_slug'],'status':'COMPLETE_AGGREGATE_RECEIPT_CHECKS_PASS_NOT_EDGE','receipt_sha256':b['atlas_receipt_sha256'],'total_ticks':all_ticks,'total_anchors':all_anchors,'host_wall_seconds':b['wall_seconds'],'retrieval_seconds':b['retrieval_seconds'],'runner_wall_seconds':a['wall_seconds'],'measured_runner_peak_rss_bytes':a['measured_runner_peak_rss_bytes'],'rss_scope':a['rss_scope'],'primary20':primary,'pooled_primary20':pooled,'all_window_coverage':rows,'same_session_P0_stream_hash_match':True,'profile_resolution':'Raw JSON is nested aggregate object; profiler cannot infer tabular grain. Derived coverage CSV has one session/window row; raw immutable and no observations dropped.','inference':False,'state_classification':False,'outcomes':False,'holdout_opened':False,'pnl':False,'canonical_brain_written':False,'interpretation':'Gaps dominate UNKNOWN under unchanged max_gap2s; this is observational coverage of current/prior tape, not feed corruption or absence of A/E. Measurable-only distributions are activity-conditioned.','next_scope':'Fix a classification/response protocol with coverage strata; predeclare any gap sensitivity as distinct proxy, never retroactively relabel atlas. Three sessions cannot establish transportability or statistical edge.'}
e['comparison_plan']=[{'grain':'3 sessions, W20','population':'all occupied5sanchors','unit':'percent of anchors','finding':f"Medible share ranges{min(r['measurable_percent'] for r in primary):.1f}% to{max(r['measurable_percent'] for r in primary):.1f}% across the three fixed sessions.",'derivation':'exclusive counts/anchor totals','disposition':'chart','reason':'Coverage differences determine feasible scientific population; pooled gap-first-failure share is one contextual prose number, not a second composition plot.'},{'grain':'session, W20','population':'measurable pairs only','unit':'ratios/ticks/counts','finding':'Continuous pressure/progress and decay cells exist; not classified A/E or future effects.','derivation':'exact raw aggregate quantiles and fixed grid','disposition':'table','reason':'Quantiles of different units should not be pooled or plotted as one scale.'},{'grain':'run','population':'one finite atlas','unit':'seconds/ticks','finding':'Three sessions measured without indicators or state fitting.','derivation':'receipt direct fields','disposition':'prose','reason':'No comparable-speedup claim versus different jobs.'}]
(out/'phenomena_atlas_evidence.json').write_text(json.dumps(e,indent=2)+'\n')
labels=[r['trade_date'][8:]+'/'+r['trade_date'][5:7] for r in primary]
spec={'version':1,'form':'categorical-bars','title':('La cobertura medible de 20s va de '+f"{min(r['measurable_percent'] for r in primary):.1f}% a {max(r['measurable_percent'] for r in primary):.1f}%").replace('.',','),
      'aside':'Tres sesiones MNQ de junio2026, con gap máximo fijo de2s y porcentaje sobre todas las anclas de cada sesión',
      'orientation':'vertical','mode':'grouped','labels':labels,'tooltipLabels':[r['trade_date']+' · '+str(r['anchors'])+' anclas' for r in primary],
      'axis':{'zero':True,'cap':100},'subjectIndex':2,'derived':True,'derivationReason':'100 × pares MEASURABLE_PAIR / todas las anclas de la misma sesión y W20',
      'series':[{'label':'Anclas con par medible','valueKind':'percent','role':'subject','data':[r['measurable_percent'] for r in primary]}]}
(out/'phenomena_atlas_coverage_chart.json').write_text(json.dumps(spec))
print(json.dumps({'ticks':all_ticks,'anchors':all_anchors,'host_seconds':b['wall_seconds'],'pooled20':pooled},indent=2))
