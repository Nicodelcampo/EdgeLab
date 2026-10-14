"""Reproducible interpretation of reviewed aggregate-only zone benchmark outputs."""
import argparse,json,csv,math,hashlib
from pathlib import Path
import pandas as pd
def main():
    root=Path(__file__).resolve().parents[3];docs=root/'docs/research/ops'
    ap=argparse.ArgumentParser();ap.add_argument('--raw-dir',required=True);ap.add_argument('--out-dir',required=True);ap.add_argument('--package-receipt',default=str(docs/'MNQ_ZONE_CONTEXT_PACKAGE_RECEIPT.json'));ap.add_argument('--plan',default=str(docs/'MNQ_ZONE_CONTEXT_PLAN.json'));ap.add_argument('--baseline',default=str(docs/'MNQ_PHENOMENA_MODEL_V4_MODEL_RECEIPT.json'));args=ap.parse_args()
    raw=Path(args.raw_dir);out=Path(args.out_dir);out.mkdir(parents=True,exist_ok=True);body=(raw/'zone-receipt.json').read_bytes();r=json.loads(body);b=json.loads((raw/'boot-receipt.json').read_bytes())
    from tools.research_ops.audits.review_zone_models import review
    verified=review(b,r,json.loads(Path(args.plan).read_bytes()),json.loads(Path(args.package_receipt).read_bytes()),body,baseline=json.loads(Path(args.baseline).read_bytes()))
    (out/'aggregate-review.json').write_text(json.dumps(verified,indent=2)+'\n')
    sessions=r['evaluation_sessions'];models=list(r['mean_session_brier']);mean=r['mean_session_brier'];n=sum(s['scores']['anchors'] for s in sessions)
    comps=[('DENSITY','CONTINUOUS'),('GEOMETRY','DENSITY'),('GEOMETRY','GEOMETRY_CC'),('ARRIVAL','GEOMETRY'),('ARRIVAL','ARRIVAL_CC')]
    rows=[]
    for s in sessions:
     z=s['zone_context'];row={'trade_date':s['trade_date'],'ticks':s['ticks'],'anchors':s['anchors'],'common_usable_anchors':s['common_usable_anchors'],**s['scores']['mean_brier'],**s['paired_deltas'],'AVZ_nearest_present':z['nearest_present_anchors']['AVZP2'],'RACIMO_nearest_present':z['nearest_present_anchors']['RACIMO'],'AVZ_unchanged_at_prior':z['unchanged_snapshot_at_prior_anchors']['AVZP2'],'RACIMO_unchanged_at_prior':z['unchanged_snapshot_at_prior_anchors']['RACIMO'],'inside_both_anchors':round(s['context_feature_mean'][11]*s['scores']['anchors']),'query_hits':z['context_query_hits'],**{'native_'+k:v for k,v in s['native_scene']['capture_counts'].items()}}
     near=s['context_feature_mean'][11]*s['scores']['anchors'];assert math.isclose(near,row['inside_both_anchors'],abs_tol=1e-6)
     rows.append(row)
    f=pd.DataFrame(rows);f['trade_date']=pd.to_datetime(f['trade_date']);nativecols=[c for c in f if c.startswith('native_')];f[nativecols]=f[nativecols].fillna(0).astype(int);f.to_csv(out/'session-scores.csv',index=False)
    comparison={}
    for left,right in comps:
     deltas=[s['scores']['mean_brier'][left]-s['scores']['mean_brier'][right] for s in sessions];delta=sum(deltas)/len(deltas);assert math.isclose(delta,mean[left]-mean[right],abs_tol=1e-12)
     comparison[left+'_MINUS_'+right]={'mean_equal_session_delta':delta,'relative_brier_change_percent':100*delta/mean[right],'improved_sessions':sum(d<0 for d in deltas),'worse_sessions':sum(d>0 for d in deltas),'session_delta_min':min(deltas),'session_delta_max':max(deltas)}
    pooled={}
    for cut in ('phase_direction_scores','proxy_state_scores'):
     groups={}
     for s in sessions:
      for name,g in s[cut].items():
       if name not in groups:groups[name]={'anchors':0,'sum_brier':{m:0. for m in models}}
       t=groups[name];t['anchors']+=g['anchors']
       for m in models:t['sum_brier'][m]+=g['anchors']*g['mean_brier'][m]
     for name,g in groups.items():
      sc={m:g['sum_brier'][m]/g['anchors'] for m in models};pooled.setdefault(cut,{})[name]={'anchors':g['anchors'],'pooled_mean_brier':sc,'geometry_minus_CC':sc['GEOMETRY']-sc['GEOMETRY_CC'],'arrival_minus_CC':sc['ARRIVAL']-sc['ARRIVAL_CC'],'arrival_minus_continuous':sc['ARRIVAL']-sc['CONTINUOUS']}
    assert sum(g['anchors'] for g in pooled['phase_direction_scores'].values())==n
    assert sum(g['anchors'] for g in pooled['proxy_state_scores'].values())==n
    support={'common_evaluation_anchors':n,'common_anchors_independent':False,'nearest_present_anchors':{fam:sum(s['zone_context']['nearest_present_anchors'][fam] for s in sessions) for fam in ('AVZP2','RACIMO')},'unchanged_snapshot_at_prior_anchors':{fam:sum(s['zone_context']['unchanged_snapshot_at_prior_anchors'][fam] for s in sessions) for fam in ('AVZP2','RACIMO')},'inside_both_anchors':int(f['inside_both_anchors'].sum()),'evaluation_native_AVZ_births':sum(s['native_scene']['native_births'] for s in sessions),'evaluation_racimo_carry_or_mixed_observations_excluded':sum(s['native_scene']['capture_counts'].get('racimo_carry_or_mixed_excluded',0) for s in sessions)}
    support['inside_both_share_percent']=100*support['inside_both_anchors']/n
    support['nearest_present_share_percent']={k:100*v/n for k,v in support['nearest_present_anchors'].items()}
    plan=[{'comparison':'capacity-matched geometry/arrival per original calendar session','grain':'one mean paired Brier delta per session, same common rows','population':'10 available original evaluation sessions; overlapping anchors, 2 empty dates explicit','unit':'Brier delta times1000','finding':'Both capacity-matched mean deltas are positive; individual sessions can differ','derivation':'session mean model loss minus matched-control loss, times1000','disposition':'chart','reason':'show sign reversals without hiding mean finding'}, {'comparison':'all7 equal-session mean model scores','grain':'equal-session mean','population':'same10 sessions/common anchors','unit':'three-class sum Brier','finding':'Continuous lowest mean among fixed7; no automatic winner promotion','derivation':'arithmetic mean session Brier','disposition':'table','reason':'lookup and numerical headline, not redundant mean chart'}, {'comparison':'density vs continuous','grain':'mean plus session sign census','population':'same10sessions','unit':'Brier and percent relative change','finding':'positive mean delta, not capacity-matched','derivation':'density−continuous','disposition':'prose','reason':'secondary capacity-changing contrast'}, {'comparison':'phase/direction and proxy state','grain':'pooled anchor-weighted within each disjoint group','population':'groups partition same common anchors; not session-weighted headline','unit':'Brier','finding':'retain any counterexamples and low-support caveats','derivation':'sum(n*groupmean)/sum(n)','disposition':'chart','reason':'pooled RTH prior-flow-negative geometry-vsCC counterexample needs visible scoped contrast; proxy states retained in table, low BOTH16 support'}, {'comparison':'runtime and memory','grain':'one job/process sample','population':'warmup+train+eval, not previous job identical I/O','unit':'seconds/bytes','finding':'bounded single source pass complete, real cost recorded not synthetic speedup','derivation':None,'disposition':'prose','reason':'operational context, no performance comparison with different transport/warmup'}]
    e={'schema':'mnq_zone_context_analysis_v1','source_receipt_sha256':hashlib.sha256((raw/'zone-receipt.json').read_bytes()).hexdigest(),'mean_session_brier':mean,'comparisons':comparison,'support':support,'pooled_group_scores':pooled,'unavailable_evaluation_sessions':r['unavailable_evaluation_sessions'],'timing':{'host_seconds':b['wall_seconds'],'retrieval_seconds':b['retrieval_seconds'],'runner_seconds':r['wall_seconds'],'native_detector_and_primitives_seconds':r['native_detector_and_primitives_seconds'],'fit_seconds':r['fit_seconds'],'host_minutes':b['wall_seconds']/60,'sampled_child_peak_rss_bytes':b['sampled_child_peak_rss_bytes'],'sampled_child_peak_rss_gib':b['sampled_child_peak_rss_bytes']/1024**3,'sampled_not_cgroup_peak':True},'total_ticks':r['total_ticks'],'warmup_ticks':r['warmup_ticks'],'warmup_sessions':r['warmup_sessions'],'context_query_hits':r['context_query_hits'],'visual_plan':plan,'baseline_population_and_scores_matched_prior_v4':verified['prior_v4_population_and_baseline_scores_equal'],'evaluation_outcomes_previously_inspected':True,'zone_specific_null_implemented':False,'first_touch_measured':False,'edge_claim':False,'inference':False,'canonical_brain_written':False}
    e['profile_notes']=['Nested receipt JSON is a multi-grain document, not equal-length tabular arrays; normalize evaluation sessions before profiling','Absent native Counter keys mean zero counted events; only those columns filled0, never response/state missingness','trade_date parsed ISO dates;10 observed sessions span15 calendar days and2 source-empty roster dates, no calendar per-day rates inferred','unobservable_eof=0 constant is observed diagnostic, not zero-imputed response','Boot receipt is one scalar job record; normalize to one CSV row']
    pd.DataFrame([b]).to_csv(out/'boot-job.csv',index=False)
    (out/'analysis.json').write_text(json.dumps(e,indent=2,allow_nan=False)+'\n')
    bydate={s['trade_date']:s for s in sessions};dates=r['requested_evaluation_sessions']
    labels=('Geometría −control igualado','Llegada −control igualado')
    first={'form':'categorical-bars','title':'Geometría empeora en las10sesiones','aside':'Media de cada sesión; positivo = peor Brier;2fechas vacías','labels':[d[5:] for d in dates],'tooltipLabels':dates,'mode':'grouped','orientation':'vertical','axis':{'zero':True},'series':[{'label':label,'valueKind':'number','role':'subject' if label==labels[0] else 'aux','derived':True,'derivationReason':'Media de pérdidas pareadas por sesión menos control igualado, por1000','data':[None if d not in bydate else bydate[d]['paired_deltas'][key]*1000 for d in dates]} for label,key in zip(labels,('GEOMETRY_MINUS_GEOMETRY_CC','ARRIVAL_MINUS_ARRIVAL_CC'))]}
    phasekeys=['OTHER:-1','OTHER:1','RTH:-1','RTH:1'];phase=pooled['phase_direction_scores']
    second={'form':'categorical-bars','title':'Pequeña excepción geométrica en RTH/flujo−','aside':'Pooled ponderado por anclas; no misma media por sesión','labels':['Fuera RTH/−','Fuera RTH/+','RTH/−','RTH/+'],'mode':'grouped','orientation':'vertical','axis':{'zero':True},'series':[{'label':label,'valueKind':'number','role':'subject' if label==labels[0] else 'aux','derived':True,'derivationReason':'Brier ponderado por anclas dentro de cada fase/dirección previa menos su control igualado, por1000','data':[phase[k][key]*1000 for k in phasekeys]} for label,key in zip(labels,('geometry_minus_CC','arrival_minus_CC'))]}
    assert all(s['paired_deltas']['GEOMETRY_MINUS_GEOMETRY_CC']>0 for s in sessions)
    assert phase['RTH:-1']['geometry_minus_CC']<0
    spec={'version':1,'form':'paired-panels','title':'Δ Brier ×1000: contexto sin mejora media','aside':'10/12fechas; positivo = peor; fases no son réplica independiente','colorMap':{labels[0]:'blue',labels[1]:'orange'},'panels':[first,second]}
    (out/'chart-spec.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2)+'\n')
    print('PASS_REVIEWED_AGGREGATE_INTERPRETATION',n,'common anchors',len(sessions),'sessions')

if __name__=='__main__':main()
