"""One computation of all prespecified comparisons from bounded aggregate only."""
import argparse,csv,json,math,hashlib,statistics
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--receipt',required=True);p.add_argument('--roster',required=True);p.add_argument('--out',required=True);args=p.parse_args();receipt=Path(args.receipt);O=Path(args.out);O.mkdir(parents=True,exist_ok=True)
r=json.loads(receipt.read_bytes());roster=json.loads(Path(args.roster).read_bytes());assert r['status']=='DEVELOPMENT_CROSSFAMILY_COMPLETE_NOT_EDGE' and r['raw_exported'] is False;ev=r['evaluation_sessions'];assert len(ev)==10
configs=roster['configs'];lookup={c['config_sha256']:i for i,c in enumerate(configs)};contrasts=[('DENSITY','CONTINUOUS'),('GEOMETRY','GEOMETRY_CC'),('ARRIVAL','ARRIVAL_CC'),('INTERACTION','INTERACTION_CC'),('INTERACTION','MIRROR_FULL')]
def label(p):
 a=lookup[p['left_config_sha256']];b=lookup[p['right_config_sha256']];return f'A{a+1}×'+('B'+str(b-2) if b<6 else 'X'+str(b-5))
summary=[];session=[];cuts=[]
for j,p in enumerate(r['pairs']):
 n=sum(s['common_usable_anchors'] for s in ev);meta=[s['crossfamily_context']['pair_counts'][j] for s in ev];means={m:sum(s['pairs'][j]['scores']['mean_brier'][m] for s in ev)/len(ev) for m in p['mean_session_brier']};assert all(math.isclose(means[k],v,abs_tol=1e-12,rel_tol=0) for k,v in p['mean_session_brier'].items());row={'pair':label(p),'pair_sha256':p['pair_sha256'],'right_family':p['right_indicator'],'anchors_pooled':n,'available_sessions':len(ev),'both_present_pooled':sum(m['both_present'] for m in meta),'inside_both_pooled':sum(m['inside_both'] for m in meta),'continuous_brier':means['CONTINUOUS'],'full_brier':means['INTERACTION'],'full_minus_continuous_x1000':1000*(means['INTERACTION']-means['CONTINUOUS'])}
 for a,b in contrasts:
  name=a+'_MINUS_'+b;ds=[s['pairs'][j]['paired_deltas'][name] for s in ev];d=sum(ds)/len(ds);assert math.isclose(d,p['paired_delta_equal_session_mean'][name],abs_tol=1e-12,rel_tol=0);row[name+'_x1000']=d*1000;row[name+'_improved_sessions']=sum(v<0 for v in ds);row[name+'_worsened_sessions']=sum(v>0 for v in ds);row[name+'_ties']=sum(v==0 for v in ds)
 for s in ev:
  q=s['pairs'][j];base={'pair':label(p),'trade_date':s['trade_date'],'anchors':s['common_usable_anchors']};session.append({**base,**{k+'_x1000':v*1000 for k,v in q['paired_deltas'].items()},'full_minus_continuous_x1000':1000*(q['scores']['mean_brier']['INTERACTION']-q['scores']['mean_brier']['CONTINUOUS'])})
 for grain in ('phase_direction_scores','proxy_state_scores','scenario_scores'):
  names=sorted(set(k for s in ev for k in s['pairs'][j][grain]))
  for name in names:
   cells=[s['pairs'][j][grain][name] for s in ev if name in s['pairs'][j][grain]];support=sum(c['anchors'] for c in cells);z={'pair':label(p),'grain':grain,'cut':name,'pooled_anchors':support,'support_sessions':len(cells)}
   for a,b in contrasts:z[a+'_MINUS_'+b+'_x1000']=1000*sum(c['anchors']*(c['mean_brier'][a]-c['mean_brier'][b]) for c in cells)/support
   cuts.append(z)
 summary.append(row)
def write(name,rows):
 with (O/name).open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
write('pair_summary.csv',summary);write('session_deltas.csv',session);write('descriptive_cuts.csv',cuts)
plan=[{'comparison':a+'_MINUS_'+b,'grain':'pair/equal-weight evaluation session','population':'same original common anchors, all18pairs,10available dates','unit':'delta3class Brier×1000','derivation':'mean over sessions of paired mean losses','disposition':'table_and_chart_if_finding_carrying','reason':'matched-capacity contrasts separate added geometry/arrival/interactions from more nonlinear bases; density against common continuous baseline'} for a,b in contrasts]
plan+=[{'comparison':'phase/proxy/scenario cuts','grain':'pooled common anchor by cut within pair','population':'overlapping anchors and non-independent cuts, support reported','unit':'delta3class Brier×1000','derivation':'anchor-weighted within-cut mean loss difference','disposition':'table plus consequential exceptions in prose/chart','reason':'do not replace equal-session headline with favorable selected pooled subgroup'}]
evidence={'schema':'crossfamily_v3_descriptive_analysis_v1','source_receipt_sha256':hashlib.sha256(receipt.read_bytes()).hexdigest(),'available_sessions':len(ev),'missing_dates':[x['trade_date'] for x in r['unavailable_evaluation_sessions']],'anchors_pooled':sum(s['common_usable_anchors'] for s in ev),'baseline':r['baseline_mean_session_brier'],'pair_summary':summary,'all_descriptive_cuts_retained':len(cuts),'comparison_plan':plan,'native_stage_seconds':r['native_stage_seconds'],'fit_seconds':r['fit_seconds'],'wall_seconds':r['wall_seconds'],'runner_rss_bytes':r['measured_runner_peak_rss_bytes'],'peak_pending_mutation_records':max(s['native_scene'].get('peak_pending_mutation_records',0) for s in r['training_sessions']+ev),'max_total_mutations_in_a_selected_session':max(s['native_scene'].get('total_causal_mutations_processed',0) for s in r['training_sessions']+ev),'holdout_opened':False,'confirmation':False,'edge_claim':False,'canonical_brain_written':False}
fullcuts=[]
for j,pair in enumerate(summary):
 for grain in ('phase_direction_scores','proxy_state_scores','scenario_scores'):
  for name in sorted(set(k for s in ev for k in s['pairs'][j][grain])):
   cells=[s['pairs'][j][grain][name] for s in ev if name in s['pairs'][j][grain]];den=sum(c['anchors'] for c in cells)
   fullcuts.append({'pair':pair['pair'],'grain':grain,'cut':name,'support_anchors':den,'support_sessions':len(cells),'full_minus_continuous_pooled_x1000':1000*sum(c['anchors']*(c['mean_brier']['INTERACTION']-c['mean_brier']['CONTINUOUS']) for c in cells)/den})
evidence['full_vs_baseline_descriptive_cuts']=fullcuts
(O/'analysis.json').write_text(json.dumps(evidence,indent=2,allow_nan=False)+'\n')
print(json.dumps({'sessions':len(ev),'anchors':evidence['anchors_pooled'],'baseline':evidence['baseline'],'wall_seconds':r['wall_seconds'],'rows':len(summary),'cut_rows':len(cuts)},indent=2))
for x in summary:print(x['pair'],*[(a+'−'+b,round(x[a+'_MINUS_'+b+'_x1000'],6),x[a+'_MINUS_'+b+'_improved_sessions']) for a,b in contrasts], 'FULL−C',round(x['full_minus_continuous_x1000'],6))
