from pathlib import Path
from collections import Counter
import json,hashlib,sys,argparse
import numpy as np
import pandas as pd
ap=argparse.ArgumentParser(description="Audit one exported MNQ V2 session without price outcomes")
for k in ('v2','v1','code-root','book-module','catalog','out','zip'):ap.add_argument('--'+k,required=True)
a=ap.parse_args()
D=Path(a.out);D.mkdir(parents=True,exist_ok=True);R=Path(a.v2);V1=Path(a.v1);C=Path(a.code_root)
sys.path.insert(0,str(C));from streaming_escalonadas import PriceConfirmed
read=lambda p:[json.loads(x) for x in p.open()]
bars=read(R/'20260629_bars_private.jsonl');signals=read(R/'20260629_signals_private.jsonl')
b1=read(V1/'20260629_bars_private.jsonl');s1=read(V1/'20260629_signals_private.jsonl')
receipt=json.loads((R/'evidence.json').read_text());count=receipt['sessions']['20260629']['counts']
assert receipt['sessions']['20260629']['input_qa']==json.loads((V1/'evidence.json').read_text())['sessions']['20260629']['input_qa']
assert len(bars)==count['bars']==len(b1)==19569
assert len(signals)==count['signals']==len(s1)==31
source_hashes={}
for label,path in [('code_sha256',C/'mnq_l2_prepare_v2.py'),('detector_sha256',C/'streaming_escalonadas.py'),('book_module_sha256',Path(a.book_module)),('catalog_sha256',Path(a.catalog))]:
 raw=path.read_bytes();lf=raw.replace(b'\r\n',b'\n');crlf=lf.replace(b'\n',b'\r\n')
 assert hashlib.sha256(crlf).hexdigest()==receipt[label]
 source_hashes[label]={'received':receipt[label],'canonical_lf':hashlib.sha256(lf).hexdigest(),'match':'EXACT_CRLF_BYTES'}
geom=('id','kind','side','det_i','own_first_i','det_nivel_tick','det_precio_tick','picos_known','available_bar_i')
assert [{k:s[k] for k in geom} for s in signals]==[{k:s[k] for k in geom} for s in s1]
engine=PriceConfirmed();replayed=[]
for i,b in enumerate(bars):
 assert b['bar_i']==i and b['n_last']==150
 assert all(b[k]==b1[i][k] for k in ('open_tick','high_tick','low_tick','close_tick','close_ts_us','bar_close_row'))
 assert b['low_tick']<=min(b['open_tick'],b['close_tick'])<=max(b['open_tick'],b['close_tick'])<=b['high_tick']
 assert b['available_row'] is None or b['available_row']>b['snapshot_asof_row']>=b['bar_close_row']
 assert b['available_ts_us'] is None or b['available_ts_us']>b['snapshot_ts_us']>=b['close_ts_us']
 assert b['available_utc_ns'] is None or b['available_utc_ns']==(b['available_ts_us']+10800000000)*1000
 replayed.extend(engine.append(b['high_tick'],b['low_tick'],b['close_tick'],b['close_ts_us']/1e6))
assert [{k:s[k] for k in geom} for s in replayed]==[{k:s[k] for k in geom} for s in signals]
assert count['eligible_last_prints']==len(bars)*150+count['partial_prints_at_end']
assert count['groups']==sum(v for k,v in count.items() if k.startswith('groups_reason_'))
assert count['invalid_book_groups']==sum(count.get('groups_reason_'+k,0) for k in ('UNORDERED','INCOMPLETE_DEPTH','CROSSED_OR_MISSING_TOUCH'))
for s in signals:
 b=bars[s['det_i']];q=s['picos_known'][-1];meta=bars[q]['_high' if s['kind']=='H' else '_low']
 assert s['pico_association_known_at_row']==s['available_row']==b['available_row']
 assert s['pico_observation']==meta['observation'] and s['pico_pre_observation']==meta['pre_observation']
 assert meta['price_tick']==s['det_nivel_tick']
 assert meta['source_row']<=b['bar_close_row']<s['available_row']
 pre=s['pico_pre_observation'];post=s['pico_observation']
 if pre:
  assert pre['available_row']<=meta['source_row']
  assert pre['snapshot_asof_row']<pre['available_row']
  assert pre['snapshot_ts_us']<pre['available_ts_us']<=meta['ts_us']
  assert pre['snapshot_age_ms']==(meta['ts_us']-pre['snapshot_ts_us'])/1000
 if post:
  assert meta['source_row']<=post['snapshot_asof_row']<post['available_row']<=s['available_row']
  assert post['snapshot_ts_us']<post['available_ts_us']
 for obs in (s,pre,post):
  if obs and obs['level_visible'] is True:
   assert obs['level_size']>0 and 1<=obs['level_depth']<=10
   assert obs['defense_mask']==(obs['recoveries_level_10s']>=2)
  if obs and (not obs['book_valid'] or obs['level_visible'] is not True):assert obs['defense_mask'] is None
stages={}
for label,key in [('antes_del_extremo','pico_pre_observation'),('grupo_del_extremo_publicado','pico_observation'),('confirmacion_zona',None)]:
 obs=[s if key is None else s[key] for s in signals]
 states=Counter('snapshot_o_libro_no_disponible' if not o or not o['book_valid'] else
  'nivel_fuera_top10' if not o['level_visible'] else 'filtro_true' if o['defense_mask'] else 'visible_filtro_false' for o in obs)
 visible=sum(bool(o and o['book_valid'] and o['level_visible']) for o in obs)
 # Independent pandas path includes all31, never null-as-zero for filter truth.
 frame=pd.DataFrame([o or {} for o in obs]);verified=int(((frame['book_valid']==True)&(frame['level_visible']==True)).sum())
 assert visible==verified and sum(states.values())==31
 stages[label]={'states':dict(states),'observable':visible,'denominator':31,'fraction':visible/31,'filter_true':int((frame['defense_mask']==True).sum()),'filter_unknown':int(frame['defense_mask'].isna().sum())}
assert stages['antes_del_extremo']['observable']==count['signals_peak_pre_observable']==26
assert stages['grupo_del_extremo_publicado']['observable']==count['signals_peak_observable']==17
assert stages['confirmacion_zona']['filter_true']==count['signals_defense_mask']==1
ages=[s['pico_pre_observation']['snapshot_age_ms'] for s in signals if s['pico_pre_observation']]
lag=[(s['available_ts_us']-s['pico_observation']['available_ts_us'])/1e6 for s in signals if s['pico_observation']]
bar_reasons=Counter(b['book_gate_reason'] for b in bars if not b['book_valid'])
# Distinguish actual validity and structural reason if publication were diagnostic-only.
agg={
 'scope':'MNQ_V2_FIRST_SESSION_TARGETFREE_AUDIT_NOT_FINANCIAL_OR_FULL52_GO',
 'session':'20260629','contract':'MNQ_09-26','zip_sha256':hashlib.sha256(Path(a.zip).read_bytes()).hexdigest(),
 'input_files':{p.name:{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(R.iterdir()) if p.is_file()},
 'source_code_provenance':source_hashes,'raw_MNQ_independently_rehashed_here':False,
 'whole_export_order_geometry_publication_checks':'PASS_UNDER_DECLARED_SOURCE_CLOCK_AND_EXPORTER_CONTRACT',
 'raw_next_timestamp_rows_not_in_attachment':True,'all_19569_bars_geometry_equal_V1':True,'all31_signals_geometry_equal_V1_and_replay':True,
 'export_receipt_counts':count,'stages':stages,
 'bars_book_valid':sum(b['book_valid'] for b in bars),'bars_book_unavailable':sum(not b['book_valid'] for b in bars),
 'bar_unavailable_structural_reasons':dict(bar_reasons),
 'pre_extreme_snapshot_age_ms':{'n':len(ages),'median':float(np.median(ages)),'p95':float(np.quantile(ages,.95)),'maximum':float(max(ages))},
 'delay_from_extreme_group_publication_to_zone_seconds':{'n':len(lag),'median':float(np.median(lag)),'maximum':float(max(lag))},
 'publication_diagnostic_only_signals':sum(s['publication_mode']!='OBSERVED_NEXT_TIMESTAMP_ROW' for s in signals),
 'current_signal_filter_unchanged_from_v1':all(s['defense_mask']==a['defense_mask'] for s,a in zip(signals,s1)),
 'no_returns_costs_MFE_MAE_fills_or_future_targets':True,
 'decision':'FIRST_SESSION_QA_AND_OBSERVABILITY_PASS; HISTORY_FEATURE_CANDIDATE_NOT_APPROVED_FILTER; freeze diagnostics and sample plan before wider run',
 'profiler_caveats':'Single-session constants expected; unknown signal mask and non-targeted bar level fields are missing by design, not zeros.',
 'comparison_plan':[{'grain':'same31 zone events at three observation times','population':'all31 signals including unknowns','unit':'observable signals','finding':'26before,17closed-extreme-group,4zone-confirmation','derivation':'explicit visible&&valid, pandas independent recount','disposition':'chart','reason':'time-of-observation materially changes measurement support'},
 {'grain':'one session','population':'bar coverage and gate groups separately','unit':'counts by different grains','disposition':'prose','reason':'do not mix bar and timestamp-group denominators'},
 {'grain':'same31signals','population':'feature masks by stage','unit':'true/false/unknown','disposition':'table','reason':'observability must not imply positive defense or edge'}]}
(D/'evidence_aggregate.json').write_text(json.dumps(agg,indent=2)+'\n')
spec={'version':1,'form':'categorical-bars','title':'MNQ: 26 de 31 niveles son observables antes del extremo del pico','aside':'Mismas 31 señales; observabilidad no equivale a defensa ni ventaja','orientation':'horizontal','mode':'grouped','subjectIndex':0,'axis':{'zero':True},'labels':['Antes del extremo','Grupo del extremo publicado','Confirmación de la zona'],'series':[{'label':'Señales con nivel observable','valueKind':'count','role':'subject','data':[stages[k]['observable'] for k in stages]}]}
(D/'chart_spec.json').write_text(json.dumps(spec,indent=2));print(json.dumps({'stages':stages,'bar_unavailable_reasons':dict(bar_reasons),'snapshot_age_ms':agg['pre_extreme_snapshot_age_ms'],'publication_delays_seconds':agg['delay_from_extreme_group_publication_to_zone_seconds']},indent=2))
