"""One aggregate-only analysis and independent score reconciliation."""
import json,csv,math,sys,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from tools.research_ops.audits.review_phenomena_models import review
from tools.research_ops.confluence.phenomena_models import MODELS,EVAL
ap=argparse.ArgumentParser();ap.add_argument('--raw-dir',required=True);ap.add_argument('--out-dir',required=True);ap.add_argument('--package-receipt',required=True);args=ap.parse_args();r=ROOT;d=r/'docs/research/ops';raw=Path(args.raw_dir);out=Path(args.out_dir);out.mkdir(parents=True,exist_ok=True);b=(raw/'model-receipt.json').read_bytes();x=json.loads(b);boot=json.loads((raw/'boot-receipt.json').read_bytes());pkg=json.loads(Path(args.package_receipt).read_bytes());plan=json.loads((d/'MNQ_PHENOMENA_MODEL_AVAILABLE_PLAN.json').read_bytes());e=review(boot,x,plan,pkg,b);ev=x['evaluation_sessions'];means=e['mean_session_brier'];labels={'PRIOR':'Frecuencias históricas','CONTINUOUS':'Componentes continuos','CONTINUOUS_CC':'Componentes + capacidad','CONTINUOUS_A':'Componentes + A','CONTINUOUS_E':'Componentes + E','CONTINUOUS_AE':'Componentes + A/E'}
rows=[]
for s in ev:
 row={'trade_date':s['trade_date'],'usable_anchors':s['common_usable_anchors'],**s['scores']['mean_brier'],'AE_minus_CONTINUOUS':s['paired_delta_AE_minus_CONTINUOUS'],'AE_minus_CC':s['paired_delta_AE_minus_CC']};rows.append(row)
with (out/'session-scores.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
# Different aggregation path: phase cells reconstruct native session loss, then
# equal-session means. Independent of receipt's top-level mean fields.
independent={m:sum(sum(g['anchors']*g['mean_brier'][m] for g in s['phase_direction_scores'].values())/s['common_usable_anchors'] for s in ev)/len(ev) for m in MODELS}
assert all(math.isclose(independent[m],means[m],abs_tol=1e-12) for m in MODELS)
states={}
for name in ('A_ONLY','E_ONLY','BOTH','NEITHER'):
 gs=[s['proxy_state_scores'][name] for s in ev if name in s['proxy_state_scores']];n=sum(g['anchors'] for g in gs);loss={m:sum(g['anchors']*g['mean_brier'][m] for g in gs)/n for m in MODELS};states[name]={'usable_anchors':n,'pooled_anchor_weighted_brier':loss,'AE_minus_CONTINUOUS':loss['CONTINUOUS_AE']-loss['CONTINUOUS'],'not_equal_session_headline':True}
phases={}
for key in sorted(set(k for s in ev for k in s['phase_direction_scores'])):
 gs=[s['phase_direction_scores'][key] for s in ev if key in s['phase_direction_scores']];n=sum(g['anchors'] for g in gs);phases[key]={'usable_anchors':n,'AE_minus_CONTINUOUS_anchor_weighted':sum(g['anchors']*(g['mean_brier']['CONTINUOUS_AE']-g['mean_brier']['CONTINUOUS']) for g in gs)/n,'not_equal_session_headline':True}
bydate={s['trade_date']:s for s in ev};componentsgain=means['PRIOR']-means['CONTINUOUS'];dAE=means['CONTINUOUS_AE']-means['CONTINUOUS'];dCC=means['CONTINUOUS_AE']-means['CONTINUOUS_CC'];dE=means['CONTINUOUS_E']-means['CONTINUOUS']
e.update(usable_anchors=sum(s['common_usable_anchors'] for s in ev),evaluation_anchors=sum(s['anchors'] for s in ev),models_display=[{'model':m,'label':labels[m],'mean_session_brier':means[m],'display_6dp':format(means[m],'.6f')} for m in MODELS],components_gain_brier=componentsgain,components_relative_reduction_pct=componentsgain/means['PRIOR']*100,components_better_than_prior_sessions=sum(s['scores']['mean_brier']['CONTINUOUS']<s['scores']['mean_brier']['PRIOR'] for s in ev),AE_minus_CONTINUOUS=dAE,AE_minus_CC=dCC,E_minus_CONTINUOUS=dE,E_better_than_CONTINUOUS_sessions=sum(s['scores']['mean_brier']['CONTINUOUS_E']<s['scores']['mean_brier']['CONTINUOUS'] for s in ev),state_results=states,phase_direction_results=phases,wall_seconds={'retrieval':boot['retrieval_seconds'],'runner':x['wall_seconds'],'host':boot['wall_seconds'],'queue_included':False},ticks=x['total_ticks'],independent_phase_reconstructed_mean=independent)
finding=f"A/E empeora la pérdida media y sólo mejora frente a componentes en {e['AE_better_than_CONTINUOUS_sessions']}/{len(ev)} sesiones"
e['comparison_plan']=[{'grain':'available_preselected_session','population':'identical common usable anchors each session','unit':'Brier difference','finding':finding,'derivation':'AE loss minus continuous and capacity-control loss; chart values scaled ×1000','disposition':'chart','reason':'session signs and reversals prevent hiding instability in tiny pooled means'},{'grain':'equal-session mean','population':'all available preselected sessions','unit':'Brier [0,2]','finding':'Continuous components outperform prior; adding A/E does not','disposition':'table','reason':'native absolute scores give six-model context without redundant second plot'},{'grain':'proxy state and phase/direction','population':'same usable anchors within each state/cell','unit':'counts and anchor-weighted Brier','finding':'AE pooled loss worsens in every state and phase/direction; BOTH sparse','disposition':'prose','reason':'support and subgroup checks; not interchangeable with equal-session headline'}]
e['source']='Private Kaggle kernel138420049 version4, exact source ec12e334, aggregate-only exports';(out/'analysis.json').write_text(json.dumps(e,indent=2,allow_nan=False)+'\n')
# Figure contains original calendar and nulls for empty source ranges.
series=[]
for label,key,role in [('Frente a componentes','paired_delta_AE_minus_CONTINUOUS','subject'),('Frente al control de capacidad','paired_delta_AE_minus_CC','base')]:
 series.append({'label':label,'valueKind':'number','role':role,'data':[bydate[date][key]*1000 if date in bydate else None for date in EVAL],'derived':True,'derivationReason':'1000 × (Brier A/E menos Brier comparador), sobre exactamente las mismas anclas por sesión'})
values=[v for s in series for v in s['data'] if v is not None];floor=min(min(values)*1.15,-.01)
spec={'version':1,'form':'multiline','title':finding,'aside':f'{len(ev)}/12 sesiones disponibles · diferencia Brier ×1000; negativo favorece A/E','labels':[date[5:] for date in EVAL],'tooltipLabels':list(EVAL),'axis':{'floor':floor,'referenceLine':{'value':0,'label':'Sin mejora (0)'}},'series':series};(out/'chart-spec.json').write_text(json.dumps(spec,indent=2,allow_nan=False)+'\n')
print(json.dumps({k:e[k] for k in ('usable_anchors','components_relative_reduction_pct','AE_minus_CONTINUOUS','AE_minus_CC','E_minus_CONTINUOUS','AE_better_than_CONTINUOUS_sessions','E_better_than_CONTINUOUS_sessions','ticks','wall_seconds')},indent=2))
