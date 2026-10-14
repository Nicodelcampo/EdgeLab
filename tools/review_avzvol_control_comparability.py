#!/usr/bin/env python3
"""Outcome-blind covariate and support QA of exposed controls; not causal matching."""
from pathlib import Path
from collections import Counter
import argparse,json,hashlib,math
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
ROOT=Path(__file__).resolve().parents[1]
AUDIT_SHA='1611277b3dc6f6393e0c6f280201359f488b8352e80a23bf9c77149e8152192e'
FEATURES=['occ','h','amp','trend_h','mom100_h','vol_occ','vol_100','dur_occ','dur_100']
COLS=['contract','cell','kind','session','clock','trend','t0']+FEATURES
KEYS=['contract','session','cell','clock','trend']
CONTRACTS=['MNQ_09-25','MNQ_12-25','MNQ_03-26','MNQ_06-26','MNQ_09-26','MNQ_12-26']
CELLS=[f'{m}_{w}_{a}' for m in (4,5,6,8) for w in (250,500,1000) for a in (20,30,45)]
def require(ok,message):
    if not ok:raise ValueError(message)
def digest(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def frozen_plan():
    return {'scope':'EXPOSED_COVARIATES_AND_CANDIDATE_HISTORY_ONLY_NO_OUTCOMES','columns_read':COLS,'outcome_columns_prohibited':['te','dir','o2','o3a','o3b','mx_h','o4','o5'],
      'exact_strata':KEYS,'features':FEATURES,'nonfinite_policy':'retain accounting, joint complete-covariate support subset only; no imputation',
      'weights':'all cells retained; common cells in six contracts for diagnostic panel; equal contracts/cells, supported sessions then supported clock/trend strata, equal rows per kind in stratum',
      'smd_definition':'weighted mean real minus pseudo divided by sqrt((weighted population variance real + pseudo)/2); zero variance and equal means gives zero, unequal means undefined',
      'candidate_history':'t0 minus500 for trend, minus499 for occupancy/activity; minus100 for momentum, minus99 for activity; complete timestamp map labels only, no price reconstruction or exclusion by this flag',
      'collision':'pseudo shares exact contract/session/cell/t0 with observed real export anchor; separately any-cell overlap; not detector-negative classification or full contamination prevalence',
      'effect_guided_filtering':False,'calipers_chosen':False,'scientific_acceptance_thresholds_chosen':False,'blind_confirmation':False,'subgroup_review':'weighted SMD separately per contract; no numerical acceptance threshold selected'}
def support_weights(d):
    complete=np.isfinite(d[FEATURES]).all(axis=1)
    f=d.loc[complete].copy()
    counts=f.groupby(KEYS+['kind']).size().unstack('kind').reindex(columns=['real','pseudo']).fillna(0)
    supported=counts[(counts.real>0)&(counts.pseudo>0)]
    combos=set((r[0],r[2]) for r in supported.index)
    common=[cell for cell in CELLS if all((c,cell) in combos for c in CONTRACTS)]
    ix=pd.MultiIndex.from_frame(f[KEYS]);f=f.loc[ix.isin(supported.index)&f.cell.isin(common)].copy()
    if not len(f):return f,counts,supported,common
    nrow=f.groupby(KEYS+['kind']).size().rename('nrow').reset_index();f=f.merge(nrow,on=KEYS+['kind'],validate='many_to_one')
    unique=f[KEYS].drop_duplicates();ns=unique.groupby(KEYS[:3]).size().rename('nstrata').reset_index();f=f.merge(ns,on=KEYS[:3],validate='many_to_one')
    nq=unique[KEYS[:3]].drop_duplicates().groupby(['contract','cell']).size().rename('nsessions').reset_index();f=f.merge(nq,on=['contract','cell'],validate='many_to_one')
    f['weight']=1/(len(CONTRACTS)*len(common)*f.nsessions*f.nstrata*f.nrow)
    require(all(abs(v-1)<1e-12 for v in f.groupby('kind').weight.sum()),'weights do not sum to one per kind')
    return f,counts,supported,common

def smd(mu_r,var_r,mu_p,var_p):
    scale=math.sqrt(max(0,(var_r+var_p)/2))
    return (mu_r-mu_p)/scale if scale else (0. if mu_r==mu_p else None)
def balance(f):
    result=[]
    for feature in FEATURES:
        moments={}
        for kind in ['real','pseudo']:
            q=f[f.kind.eq(kind)];x=q[feature].to_numpy();w=q.weight.to_numpy()
            mu=float(np.dot(w,x));var=float(np.dot(w,(x-mu)**2))
            # Independent scalar list/fsum, not the vector weighted implementation.
            check_mu=math.fsum(float(a)*float(b) for a,b in zip(x,w));check_var=math.fsum(float(b)*(float(a)-check_mu)**2 for a,b in zip(x,w))
            require(math.isclose(mu,check_mu,rel_tol=1e-12,abs_tol=1e-10) and math.isclose(var,check_var,rel_tol=1e-12,abs_tol=1e-10),'independent weighted moment mismatch')
            moments[kind]={'mean':mu,'variance':var,'rows':len(q)}
        rr=f[f.kind.eq('real')][feature];pp=f[f.kind.eq('pseudo')][feature]
        result.append({'feature':feature,'weighted':moments,'weighted_smd':smd(moments['real']['mean'],moments['real']['variance'],moments['pseudo']['mean'],moments['pseudo']['variance']),
          'same_panel_unweighted_smd':smd(float(rr.mean()),float(rr.var(ddof=0)),float(pp.mean()),float(pp.var(ddof=0)))})
    return result

def collision_counts(d):
    real=d[d.kind.eq('real')]
    exact=set(map(tuple,real[['contract','session','cell','t0']].to_numpy()))
    anycell=set(map(tuple,real[['contract','session','t0']].to_numpy()))
    pseudo=d[d.kind.eq('pseudo')];out=[]
    for c in CONTRACTS:
        q=pseudo[pseudo.contract.eq(c)]
        e=sum(tuple(x) in exact for x in q[['contract','session','cell','t0']].to_numpy())
        a=sum(tuple(x) in anycell for x in q[['contract','session','t0']].to_numpy())
        out.append({'contract':c,'pseudo_rows':len(q),'same_cell_real_anchor_overlap_rows':e,'any_cell_real_anchor_overlap_rows':a,'distinct_pseudo_same_cell_anchor_count':len(set(tuple(x) for x in q[['contract','session','cell','t0']].to_numpy() if tuple(x) in exact))})
    return out

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ['inventory','map-evidence','map-dir','out-dir']:p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--map-evidence-sha256',required=True);p.add_argument('--allow-exposed-covariate-review',action='store_true',required=True);a=p.parse_args()
    ref=ROOT/'docs/infra/AVZVOL_AUDIT_20261010.json';require(digest(ref)==AUDIT_SHA,'export reference mismatch')
    require(digest(a.map_evidence)==a.map_evidence_sha256,'candidate map evidence mismatch');ev=json.loads(a.map_evidence.read_text())
    require(ev['status']=='CANDIDATE_TIMESTAMP_MAP_ONLY_NOT_CERTIFIED' and not ev['holdout_payload_opened'],'invalid candidate scope')
    records={r['contract']:r for r in ev['files']};require(set(records)==set(CONTRACTS),'map universe mismatch')
    inv=json.loads(a.inventory.read_text());paths={Path(x['file']).name:Path(x['file']) for x in inv};pins={r['file']:r for r in json.loads(ref.read_text())['covariate_audit']['files']}
    require(len(inv)==len(paths)==6 and set(paths)==set(pins),'export universe mismatch');opened={};maps={}
    for name,file in paths.items():
        pf=pq.ParquetFile(file);require(pf.metadata.num_rows==pins[name]['rows'] and set(COLS)<=set(pf.schema_arrow.names),'schema/rows mismatch')
        for i in range(pf.num_row_groups):
            s=pf.metadata.row_group(i).column(pf.schema_arrow.names.index('session')).statistics
            require(s and s.has_min_max and s.has_null_count and s.null_count==0 and int(s.max)<20261001,'reserved/unknown partition')
        require(digest(file)==pins[name]['sha256'],'export bytes mismatch');opened[name]=pf
    for c in CONTRACTS:
        r=records[c];file=a.map_dir/(c+'-private-map.npz');require(r['all_export_anchors_align'] and digest(file)==r['private_map_sha256'],'map SHA/alignment mismatch')
        with np.load(file,allow_pickle=False) as m:
            labels=m['session'];end=m['end_ns'];clock=m['clock']
        require(len(labels)==r['candidate_bar_count']==r['historical_logged_bar_count'] and (np.diff(labels)>=0).all() and int(end.max())<pd.Timestamp('2026-09-30T22:00:00Z').value,'map structure/holdout mismatch')
        maps[c]=(labels,clock)
    a.out_dir.mkdir(parents=True,exist_ok=False);(a.out_dir/'analysis-plan.json').write_text(json.dumps(frozen_plan(),indent=2)+'\n')
    frames=[];history=[];profiles=[]
    for name,pf in opened.items():
        d=pf.read(columns=COLS).to_pandas();c=name.removesuffix('_avzp2racgrid.parquet');require(set(d.contract)=={c} and set(d.kind)<={'real','pseudo'} and set(d.cell)<=set(CELLS),'identity mismatch')
        require(d[COLS[:7]].notna().all().all() and set(d.trend)<={-1,0,1},'invalid anchor identities')
        labels,clock=maps[c];t=d.t0.to_numpy();require((t>=0).all() and (t<len(labels)).all() and np.array_equal(labels[t],d.session) and np.array_equal(clock[t],d.clock),'map anchor mismatch')
        hist={}
        for lookback in [99,100,499,500]:
            within=np.zeros(len(d),bool);ix=np.flatnonzero(t>=lookback);within[ix]=labels[t[ix]-lookback]==labels[t[ix]]
            hist[lookback]=within
        for kind in ['real','pseudo']:
            mask=d.kind.eq(kind).to_numpy();history.append({'contract':c,'kind':kind,'rows':int(mask.sum()),'insufficient_index_for_501_bar_history':int((mask&(t<500)).sum()),**{f'candidate_history_{lb+1}_bars_not_within_anchor_session':int((mask&~v).sum()) for lb,v in hist.items()}})
        profiles.append({'contract':c,'nonfinite_by_feature':{f:int((~np.isfinite(d[f])).sum()) for f in FEATURES},'joint_nonfinite_rows':int((~np.isfinite(d[FEATURES]).all(axis=1)).sum()),'duplicate_full_covariate_rows_retained':int(d.duplicated().sum())})
        frames.append(d)
    d=pd.concat(frames,ignore_index=True);f,counts,supported,common=support_weights(d)
    ledger=[]
    panel_counts=f.groupby(['contract','kind']).size().to_dict() if len(f) else {}
    for c in CONTRACTS:
        for kind in ['real','pseudo']:
            q=d[d.contract.eq(c)&d.kind.eq(kind)];complete=np.isfinite(q[FEATURES]).all(axis=1)
            ix=pd.MultiIndex.from_frame(q.loc[complete,KEYS]);shared=ix.isin(supported.index)
            ledger.append({'contract':c,'kind':kind,'rows':len(q),'complete_covariates':int(complete.sum()),'exact_shared_stratum_rows_all_cells':int(shared.sum()),'panel_rows_common_cells':int(panel_counts.get((c,kind),0))})
    collision=collision_counts(d)
    exact_real=pd.MultiIndex.from_frame(d.loc[d.kind.eq('real'),['contract','session','cell','t0']]).unique()
    require(sum(r['same_cell_real_anchor_overlap_rows'] for r in collision)==int(pd.MultiIndex.from_frame(d.loc[d.kind.eq('pseudo'),['contract','session','cell','t0']]).isin(exact_real).sum()),'independent anchor overlap mismatch')
    subgroup=[]
    for c in CONTRACTS:
        q=f[f.contract.eq(c)].copy()
        if len(q):
            q['weight']=q.weight/q.groupby('kind').weight.transform('sum')
            subgroup.append({'contract':c,'balance':balance(q)})
    # Counts also reconstructed from group counts, independent of membership row masks.
    require(sum(r['exact_shared_stratum_rows_all_cells'] for r in ledger if r['kind']=='real')==int(supported.real.sum()),'real shared count mismatch')
    require(sum(r['exact_shared_stratum_rows_all_cells'] for r in ledger if r['kind']=='pseudo')==int(supported.pseudo.sum()),'pseudo shared count mismatch')
    result={'schema':'edgelab_exposed_control_comparability_v1','plan':frozen_plan(),'all_export_and_map_pins_before_covariate_payload':True,'source_export_reference_sha256':AUDIT_SHA,'candidate_map_evidence_sha256':a.map_evidence_sha256,
      'totals':{'rows':len(d),'common_cells':len(common),'common_cell_names':common,'all_exact_strata':len(counts),'shared_exact_strata':len(supported),'real_only_strata':int(((counts.real>0)&(counts.pseudo==0)).sum()),'pseudo_only_strata':int(((counts.pseudo>0)&(counts.real==0)).sum()),'panel_rows':len(f),'same_cell_real_anchor_overlap_pseudo_rows':sum(r['same_cell_real_anchor_overlap_rows'] for r in collision),'any_cell_real_anchor_overlap_pseudo_rows':sum(r['any_cell_real_anchor_overlap_rows'] for r in collision)},
      'profile':profiles,'support_accounting':ledger,'candidate_history_accounting':history,'anchor_overlap':collision,'balance':balance(f) if len(f) else [],'balance_by_contract':subgroup,'independent_moments_and_support_counts_checked':True,'anchor_overlap_independently_checked':True,
      'comparison_plan':[{'grain':'nine covariates, same supported panel','population':'joint finite covariates and exact shared strata, six contracts/common cells','unit':'standardized mean difference','disposition':'chart','reason':'largest absolute residual differences in pre-anchor covariates; full nine-feature CSV retains remainder'},{'grain':'same-cell anchor overlap','population':'all legacy pseudo rows','unit':'row count','disposition':'prose','reason':'direct witness of nonexclusive positive anchors, not true zone-free prevalence or causal state'},{'grain':'candidate prehistory session labels','population':'all rows by kind','unit':'row count','disposition':'table','reason':'structural witness only; not source certification or an outcome filter'}],
      **{k:False for k in ['outcome_payload_columns_read','new_market_outcomes_computed','raw_price_payload_read','economic_outcomes_computed','holdout_payload_read','zone_free_census_verified','source_quality_certified','asof_feature_windows_certified','formal_inference_executed','matching_policy_approved','research_release_authorized','historical_outputs_modified']}}
    (a.out_dir/'evidence.json').write_text(json.dumps(result,indent=2)+'\n')
    print('totals',result['totals']);print('support',ledger);print('balance',[(r['feature'],r['weighted_smd'],r['same_panel_unweighted_smd']) for r in result['balance']]);print('history',history)
if __name__=='__main__':
    try:main()
    except (ValueError,TypeError,KeyError,OSError) as e:print(json.dumps({'status':'STOP','reason':str(e)}));raise SystemExit(2)
