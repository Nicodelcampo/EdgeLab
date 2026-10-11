#!/usr/bin/env python3
"""Review ALREADY EXPOSED retest geometry to triage entry hypotheses, not trades."""
from pathlib import Path
from importlib.util import spec_from_file_location,module_from_spec
from collections import Counter,defaultdict
import argparse,json,hashlib,math,statistics
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
ROOT=Path(__file__).resolve().parents[1]
spec=spec_from_file_location('review_direction',ROOT/'tools/review_avzvol_exposed_direction.py');core=module_from_spec(spec);spec.loader.exec_module(core)
COLS=['contract','cell','kind','session','clock','t0','te','dir','o2','o3a','o3b','trend','pos','mom100_h']
CATEGORIES=['BOTH_ALIGNED','BOTH_OPPOSED','MIXED','NEUTRAL_OR_ZERO']

def plan():
    return {'scope':'EXPOSED_RETEST_AND_ENTRY_HYPOTHESIS_TRIAGE_NOT_BACKTEST','columns_read':COLS,'blind_or_preregistered':False,'cell_universe':core.CELLS,
      'retest':'O3a 0/1 given observed exit; window-limited absence not permanent absence; original same-session maximum2000 bars',
      'bounce':'O3b 0/1 given retest; one height from exit edge in exit direction versus opposite direction, starting AFTER retest bar, original maximum2000 bars; -2 both barriers same later bar and -1 unresolved are retained',
      'entry_compatible_subset':'pos=0 at original anchor, reported separately without replacing full legacy population',
      'exit_known_cut':'At the hypothetical confirmed-exit decision ONLY, compare observed exit direction with signs of PRIOR500-bar trend and PRIOR100-bar momentum: both aligned, both opposed, mixed, or any zero. All categories retained. dir is unavailable at original anchor; no momentum threshold or optimized lookback',
      'context':'exact contract/session/cell/clock/trend overlap, changing support; equal supported strata per session; not causal matching',
      'weights':'same reviewed direction tool; equal supported sessions, common cells and six contracts; duplicates preserved, all36cells retained',
      'bounds':'within exact groups supporting known bounce contrast, all retests with ambiguous/unresolved outcomes; adversarial binary resolution bounds, NOT confidence intervals or fills',
      'timing':'exported te minus t0 descriptive 25-trade bar counts; median by contract/kind for inside-band anchors with observed exit; no wall-clock conversion or retest timestamp available',
      'no_raw_price_outcomes':True,'no_economic_outcomes':True,'no_holdout':True,'no_entry_or_exit_fills':True,'no_parameter_optimization':True}

def exit_context(d):
    trend=d.trend.to_numpy();mom=np.sign(d.mom100_h.to_numpy());direction=d.dir.to_numpy()
    out=np.full(len(d),'MIXED',dtype=object)
    out[(trend==direction)&(mom==direction)]='BOTH_ALIGNED'
    out[(trend==-direction)&(mom==-direction)]='BOTH_OPPOSED'
    out[(trend==0)|(mom==0)]='NEUTRAL_OR_ZERO'
    out[d.te.to_numpy()<0]='NO_EXIT'
    return out

def bounce_bounds(d,supported,common):
    f=d[d.o3a.eq(1)].copy();f['lower']=f.o3b.eq(1).astype(float);f['upper']=f.o3b.ne(0).astype(float)
    lo=core.aggregate(f,'lower').reindex(supported.index);up=core.aggregate(f,'upper').reindex(supported.index)
    b=pd.DataFrame({'lower':lo.real-up.pseudo,'upper':up.real-lo.pseudo}).groupby(['contract','cell']).mean()
    values=[b.loc[(c,cell)] for c in core.CONTRACTS for cell in common]
    if not values:return None
    # Independent scalar state counts and session means, not pandas mean/bound arrays.
    bins=defaultdict(Counter)
    for c,s,cell,kind,a,code in d[core.KEYS+['kind','o3a','o3b']].itertuples(index=False,name=None):
        if a==1:bins[(c,s,cell,kind)][int(code)]+=1
    cc=defaultdict(list)
    for c,s,cell in supported.index:
        if cell not in common:continue
        r=bins[(c,s,cell,'real')];p=bins[(c,s,cell,'pseudo')];rn=sum(r.values());pn=sum(p.values())
        cc[(c,cell)].append((r[1]/rn-(pn-p[0])/pn,(rn-r[0])/rn-p[1]/pn))
    direct=[(math.fsum(v[0] for v in cc[(c,cell)])/len(cc[(c,cell)]),math.fsum(v[1] for v in cc[(c,cell)])/len(cc[(c,cell)])) for c in core.CONTRACTS for cell in common]
    vals=[100*math.fsum(getattr(v,k) for v in values)/len(values) for k in ['lower','upper']]
    require=max(abs(vals[i]-100*math.fsum(v[i] for v in direct)/len(direct)) for i in [0,1])<1e-10
    core.require(require,'independent retest bounds mismatch')
    return {'lower_gap_pp':vals[0],'upper_gap_pp':vals[1],'population':'all retests in exactly known-bounce supported groups; unresolved and same-bar double hits adversarial; not CI'}

def summarize_scope(d):
    retest,_,_=core.summarize(d,'retest')
    bounce,g,c=core.summarize(d,'bounce')
    context,_,_=core.summarize(d,'bounce',core.KEYS+['clock','trend'])
    return {'retest_given_exit':retest,'bounce_given_resolved_retest':bounce,'bounce_context_exact_strata':context,'bounce_same_context_overlap_unstratified':core.same_overlap_base(d,'bounce',core.KEYS+['clock','trend']),'bounce_unresolved_adversarial_bounds':bounce_bounds(d,g,c)}

def exit_delay_summary(bars):
    if not len(bars):return {'median_exit_delay_25_trade_bars':None,'q90_exit_delay_25_trade_bars':None}
    values=sorted(int(v) for v in bars);require=all(v>0 for v in values);core.require(require,'nonpositive observed exit delay')
    position=.9*(len(values)-1);lo=math.floor(position);hi=math.ceil(position);direct_q=values[lo]+(values[hi]-values[lo])*(position-lo)
    med=float(np.median(bars));q90=float(np.quantile(bars,.9))
    core.require(math.isclose(med,statistics.median(values),abs_tol=1e-12) and math.isclose(q90,direct_q,abs_tol=1e-10),'independent exit delay quantile mismatch')
    return {'median_exit_delay_25_trade_bars':med,'q90_exit_delay_25_trade_bars':q90}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['inventory','historical-stage-source','out-dir']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--allow-exposed-entry-hypothesis-review',action='store_true',required=True);a=p.parse_args()
    core.require(core.digest(a.historical_stage_source)==core.STAGE_SHA,'historical code mismatch')
    ref=ROOT/'docs/infra/AVZVOL_AUDIT_20261010.json';core.require(core.digest(ref)==core.AUDIT_SHA,'export reference mismatch')
    pins={r['file']:r for r in json.loads(ref.read_text())['covariate_audit']['files']};inv=json.loads(a.inventory.read_text());paths={Path(r['file']).name:Path(r['file']) for r in inv}
    core.require(len(inv)==len(paths)==6 and set(paths)==set(pins),'exact export universe required');opened={}
    for name,file in paths.items():
        pf=pq.ParquetFile(file);core.require(pf.metadata.num_rows==pins[name]['rows'] and set(COLS)<=set(pf.schema_arrow.names),'export shape mismatch')
        for i in range(pf.num_row_groups):
            s=pf.metadata.row_group(i).column(pf.schema_arrow.names.index('session')).statistics
            core.require(s and s.has_min_max and s.has_null_count and s.null_count==0 and int(s.max)<20261001,'reserved/unknown partition')
        core.require(core.digest(file)==pins[name]['sha256'],'export bytes mismatch');opened[name]=pf
    a.out_dir.mkdir(parents=True,exist_ok=False);(a.out_dir/'analysis-plan.json').write_text(json.dumps(plan(),indent=2)+'\n');frames=[];profiles=[]
    for name,pf in opened.items():
        d=pf.read(columns=COLS).to_pandas();c=name.removesuffix('_avzp2racgrid.parquet')
        core.require(d.notna().all().all() and set(d.contract)=={c} and set(d.kind)<={'real','pseudo'} and set(d.cell)<=set(core.CELLS),'export identity')
        core.require(set(d.o2)<={-1,0,1} and set(d.o3a)<={-1,0,1} and set(d.o3b)<={-2,-1,0,1} and set(d.dir)<={-1,0,1} and set(d.trend)<={-1,0,1} and set(d.pos)<={-1,0,1},'invalid coded value')
        core.require(((d.te<0)==d.dir.eq(0)).all() and (d.loc[d.te<0,['o2','o3a','o3b']]==-1).all().all(),'no exit contradiction')
        core.require(d.loc[d.te>=0,'o3a'].isin([0,1]).all() and d.loc[d.o3a.eq(0),'o3b'].eq(-1).all() and (d.loc[d.te>=0,'te']>d.loc[d.te>=0,'t0']).all(),'retest/exit contradiction')
        core.require(np.isfinite(d.mom100_h).all(),'unknown prior momentum')
        profiles.append({'contract':c,'rows':len(d),'nulls':0,'duplicate_full_export_columns_retained':int(d.duplicated().sum())});frames.append(d)
    d=pd.concat(frames,ignore_index=True)
    d['retest']=np.where(d.te>=0,d.o3a,np.nan);d['bounce']=d.o3b.where(d.o3b.isin([0,1]),np.nan)
    d['continuation']=d.o2.where(d.o2.isin([0,1]),np.nan);d['exit_context']=exit_context(d)
    inside=d[d.pos.eq(0)].copy();scopes={'all_legacy_anchors':summarize_scope(d),'inside_band_anchors':summarize_scope(inside)}
    contexts=[]
    for category in CATEGORIES:
        q=inside[inside.exit_context.eq(category)]
        cont,_,_=core.summarize(q,'continuation');b,_,_=core.summarize(q,'bounce')
        contexts.append({'category':category,'real_rows':int(q.kind.eq('real').sum()),'pseudo_rows':int(q.kind.eq('pseudo').sum()),'continuation':cont,'resolved_bounce':b})
    ledger=[];timing=[]
    for scope,q in [('all_legacy_anchors',d),('inside_band_anchors',inside)]:
        for c in core.CONTRACTS:
            for kind in ['real','pseudo']:
                x=q[q.contract.eq(c)&q.kind.eq(kind)];r=x[x.o3a.eq(1)]
                row={'scope':scope,'contract':c,'kind':kind,'rows':len(x),'no_exit':int((x.te<0).sum()),'observed_exit':int((x.te>=0).sum()),'observed_retest':len(r),'no_observed_retest_within_window':int(x.o3a.eq(0).sum()),'bounce_first':int(r.o3b.eq(1).sum()),'opposite_excursion_first':int(r.o3b.eq(0).sum()),'same_bar_both':int(r.o3b.eq(-2).sum()),'unresolved_after_retest':int(r.o3b.eq(-1).sum())}
                core.require(row['rows']==row['no_exit']+row['observed_exit'] and row['observed_exit']==row['observed_retest']+row['no_observed_retest_within_window'] and row['observed_retest']==sum(row[k] for k in ['bounce_first','opposite_excursion_first','same_bar_both','unresolved_after_retest']),'ledger cross-foot')
                ledger.append(row)
                if scope=='inside_band_anchors':
                    z=x[x.te>=0];bars=(z.te-z.t0).to_numpy()
                    timing.append({'contract':c,'kind':kind,'observed_exit_rows':len(z),**exit_delay_summary(bars)})
    # Independent native row-count ledger, separate from vector masks.
    count=Counter()
    for kind,te,ra,rb in d[['kind','te','o3a','o3b']].itertuples(index=False,name=None):
        count[(kind,'rows')]+=1;count[(kind,'observed_retest')]+=int(ra==1);count[(kind,'same_bar_both')]+=int(ra==1 and rb==-2);count[(kind,'unresolved_after_retest')]+=int(ra==1 and rb==-1)
    for kind in ['real','pseudo']:
        for key in ['rows','observed_retest','same_bar_both','unresolved_after_retest']:core.require(sum(r[key] for r in ledger if r['scope']=='all_legacy_anchors' and r['kind']==kind)==count[(kind,key)],'independent ledger mismatch')
    result={'schema':'edgelab_exposed_entry_hypothesis_triage_v1','plan':plan(),'all_six_pins_and_footers_before_payload':True,'source_export_reference_sha256':core.AUDIT_SHA,'source_stage_sha256':core.STAGE_SHA,'reviewed_aggregation_helper_sha256':core.digest(ROOT/'tools/review_avzvol_exposed_direction.py'),'profile':profiles,'rows':len(d),'accounting':ledger,'scopes':scopes,'inside_band_exit_contexts':contexts,'inside_band_exit_delay_bar_counts':timing,'independent_numeric_checks_completed':True,
      'comparison_plan':[{'grain':'six contracts retest/bounce','population':'declared legacy or inside-band supported groups; each endpoint has own conditional denominator','unit':'percent/percentage points','disposition':'chart','reason':'separate retest frequency from conditional post-retest barriers; upload capability currently unavailable'},{'grain':'four exit-known sign categories','population':'inside-band anchors with observed exit','unit':'rates and support','disposition':'table','reason':'retain all declared categories; never label strongest context a discovered entry rule'},{'grain':'retest same-bar both/unresolved','population':'all observed retests','unit':'row count','disposition':'prose','reason':'prevents treating geometry as an executable win probability'},{'grain':'exit delay','population':'inside-band anchors with observed exit','unit':'25-trade bars','disposition':'table','reason':'not wall time or retest entry latency'}],
      **{k:False for k in ['raw_price_payload_read','new_market_price_outcomes_computed','economic_outcomes_computed','holdout_payload_read','entries_backtested','fills_or_costs_simulated','causal_zone_effect_validated','controls_zone_free_certified','formal_inference_executed','entry_rule_promoted','research_release_authorized','historical_outputs_modified']}}
    (a.out_dir/'evidence.json').write_text(json.dumps(result,indent=2)+'\n')
    for scope,x in scopes.items():print(scope,{k:v['headline'] if isinstance(v,dict) and 'headline' in v else v for k,v in x.items()})
    for r in contexts:print('context',r['category'],r['real_rows'],r['pseudo_rows'],r['continuation']['headline'],r['resolved_bounce']['headline'])
    print('ledger',ledger);print('timing',timing)
if __name__=='__main__':
    try:main()
    except (ValueError,TypeError,KeyError,OSError) as e:print(json.dumps({'status':'STOP','reason':str(e)}));raise SystemExit(2)
