"""Descriptive robustness of exposed O5, not new endpoints or certified research."""
from pathlib import Path
from collections import defaultdict
import json, hashlib, math, argparse
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT=Path(__file__).resolve().parents[1]
CONTRACTS=['MNQ_09-25','MNQ_12-25','MNQ_03-26','MNQ_06-26','MNQ_09-26','MNQ_12-26']
CELLS=[f'{m}_{w}_{a}' for m in (4,5,6,8) for w in (250,500,1000) for a in (20,30,45)]
COLS=['contract','cell','kind','session','t0','te','o5']
KEYS=['contract','session','cell']
def require(ok,message):
    if not ok:raise RuntimeError(message)
def groups(d):
    f=d[np.isfinite(d.o5)]
    if f.empty:return pd.DataFrame(columns=['real','pseudo','delta'],index=pd.MultiIndex.from_tuples([],names=KEYS))
    g=f.groupby(KEYS+['kind'],sort=True).o5.mean().unstack('kind').reindex(columns=['real','pseudo'])
    g['delta']=g.real-g.pseudo
    return g

def matrix(g,cells=CELLS):
    idx=pd.MultiIndex.from_product([CONTRACTS,cells],names=['contract','cell'])
    return g.delta.groupby(level=['contract','cell']).mean().reindex(idx)

def scalar(m,contracts=CONTRACTS,cells=None):
    vals=m.loc[pd.IndexSlice[contracts,cells if cells is not None else slice(None)]]
    return math.fsum(float(v) for v in vals)/len(vals) if len(vals) and vals.notna().all() else None

def interpret(x):
    return {'log_gap':x,'relative_geometric_ratio':math.exp(x) if x is not None else None,
        'relative_geometric_gap_percent':100*math.expm1(x) if x is not None else None}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inventory', type=Path, required=True)
    parser.add_argument('--out-dir', type=Path, required=True)
    parser.add_argument('--audit-reference-sha256', required=True)
    parser.add_argument('--allow-exposed-o5-review', action='store_true')
    args=parser.parse_args()
    if not args.allow_exposed_o5_review:parser.error('Explicit exposed-O5 opt-in required')
    OUT=args.out_dir
    OUT.mkdir(parents=True,exist_ok=False)
    plan={'study_id':'AVZVOL-EXPOSED-ROBUSTNESS-1','scope':'Post-exposure descriptive sensitivity of existing O5 only; no new price endpoints/inference/certification',
        'universe':CELLS,'main_panel':'intersection of cells computable in all six contracts, fixed before deletions',
        'weights':'Within contract/session/cell finite real mean minus finite legacy-pseudo mean; equal supported sessions within each contract/cell, then equal contracts and cells',
        'leave_one_contract_out':'Each of the six contracts removed in turn, retaining the same fixed cell universe',
        'leave_one_date_out':'Each observed export session date label removed across ALL contracts/cells, not just one event/cell. Any lost contract/cell support makes fixed panel not computable; record, do not shrink panel',
        'endpoint_sensitivity':'Exact annotated last index te+200 has same exported session label as anchor; not complete-window quality proof. Keep known-end observations only, then require real/pseudo common support. If panel incomplete report it; secondary complete-cell subset compares filtered values to baseline on the EXACT SAME supported contract/session/cell groups',
        'missingness':'No imputation; retain existing missing/unsupported counts; pseudo replacement duplicates preserved',
        'geometric_interpretation':'exp(mean log-gap) = weighted geometric ratio of the ORIGINAL post/pre range ratios, real relative to legacy pseudo; NOT absolute future range or constant-time volatility',
        'no_economic_outcomes':True,'no_raw_ticks':True,'no_new_outcomes':True,'no_pvalues_or_CIs':True,
        'zone_free_proof':False,'blind_or_preregistered':False,'source_quality_certified':False,
        'original_outputs_modified':False}
    (OUT/'analysis-plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    audit=ROOT/'docs/infra/AVZVOL_AUDIT_20261010.json'
    require(hashlib.sha256(audit.read_bytes()).hexdigest()==args.audit_reference_sha256,'audit reference pin mismatch')
    pins=json.loads(audit.read_text())['covariate_audit']['files']
    inv=json.loads(args.inventory.read_text())
    paths={Path(x['file']).name:Path(x['file']) for x in inv}
    require(len(paths)==len(pins)==6 and set(paths)=={x['file'] for x in pins},'six-export universe mismatch')
    opened=[]
    for pin in pins:
        file=paths[pin['file']];pf=pq.ParquetFile(file)
        require(pf.metadata.num_rows==pin['rows'] and set(COLS)<=set(pf.schema_arrow.names),'footer row/schema mismatch')
        i=pf.schema_arrow.names.index('session')
        for k in range(pf.num_row_groups):
            st=pf.metadata.row_group(k).column(i).statistics
            require(st and st.has_min_max and st.has_null_count and st.null_count==0 and int(st.max)<20261001,'reserved/unknown export footer')
        opened.append((pin,file,pf))
    for pin,file,pf in opened:
        with file.open('rb') as f:require(hashlib.file_digest(f,'sha256').hexdigest()==pin['sha256'],'source pin mismatch')
    frames=[]
    for pin,file,pf in opened:
        d=pf.read(columns=COLS).to_pandas()
        require(set(d.contract)=={file.name.removesuffix('_avzp2racgrid.parquet')},'contract mismatch')
        require(d[COLS[:-1]].notna().all().all() and set(d.kind)<={'real','pseudo'},'invalid annotations')
        require(not np.isinf(d.o5).any() and not (d.o5.notna() & (d.te<0)).any(),'invalid O5')
        require(set(d.cell)<=set(CELLS),'cell universe mismatch')
        frames.append(d)
    d=pd.concat(frames,ignore_index=True);g=groups(d);m=matrix(g)
    previous=pd.read_csv(ROOT/'docs/research/avzvol_exposed_o5_review_20261010/contract-cells.csv').set_index(['contract','cell']).delta_equal_session_mean
    require(np.allclose(m,previous.reindex(m.index),equal_nan=True,atol=1e-12,rtol=0),'original means changed')
    common=[cell for cell in CELLS if m.xs(cell,level='cell').notna().all()]
    require(len(common)==31,'original fixed panel changed')
    base=scalar(m,cells=common)
    # Independent direct accumulation of raw exposed values, not pandas groupby.
    raw=defaultdict(list)
    for c,s,cell,k,o in zip(d.contract,d.session,d.cell,d.kind,d.o5):
        if math.isfinite(float(o)):raw[(c,int(s),cell,k)].append(float(o))
    direct_groups={}
    for c,s,cell,k in raw:
        if k=='real' and (c,s,cell,'pseudo') in raw:
            r=raw[(c,s,cell,'real')];p=raw[(c,s,cell,'pseudo')]
            direct_groups[(c,s,cell)]=math.fsum(r)/len(r)-math.fsum(p)/len(p)
    direct_bins=defaultdict(list)
    for (c,s,cell),v in direct_groups.items():direct_bins[(c,cell)].append((s,v))
    def direct_matrix(exclude_date=None):
        result={}
        for c in CONTRACTS:
            for cell in common:
                vals=[v for s,v in direct_bins.get((c,cell),[]) if s!=exclude_date]
                result[(c,cell)]=math.fsum(vals)/len(vals) if vals else None
        return result

    dm=direct_matrix();direct_base=math.fsum(dm.values())/len(dm)
    require(abs(base-direct_base)<1e-12,'independent main mismatch')
    maxcheck=abs(base-direct_base)
    loco=[];cell_loco=defaultdict(list)
    for excluded in CONTRACTS:
        remaining=[c for c in CONTRACTS if c!=excluded]
        value=scalar(m,contracts=remaining,cells=common)
        checked=math.fsum(v for (c,cell),v in dm.items() if c!=excluded)/(5*len(common))
        maxcheck=max(maxcheck,abs(value-checked));require(abs(value-checked)<1e-12,'independent LOCO mismatch')
        loco.append({'excluded_contract':excluded,**interpret(value)})
        for cell in common:cell_loco[cell].append(float(m.xs(cell,level='cell').drop(excluded).mean()))
    # Remove whole observed date label across contracts and cells. Private dates stay private.
    date_cases=[];cell_date=defaultdict(list);cell_null=defaultdict(int)
    for day in sorted(int(x) for x in d.session.unique()):
        mm=matrix(g[g.index.get_level_values('session')!=day],common)
        value=scalar(mm,cells=common);checked=direct_matrix(day)
        missing=[(c,cell) for (c,cell),v in checked.items() if v is None]
        require((value is None)==bool(missing),'fixed universe missingness mismatch')
        if value is not None:
            direct_value=math.fsum(checked.values())/len(checked)
            maxcheck=max(maxcheck,abs(value-direct_value));require(abs(value-direct_value)<1e-12,'independent date deletion mismatch')
        date_cases.append({'private_session_label':day,'log_gap':value,'lost_contract_cell_count':len(missing)})
        for cell in common:
            vals=mm.xs(cell,level='cell')
            if vals.notna().all():cell_date[cell].append(float(vals.mean()))
            else:cell_null[cell]+=1
    pd.DataFrame(date_cases).to_csv(OUT/'private-date-deletions.csv',index=False)
    valid=[r['log_gap'] for r in date_cases if r['log_gap'] is not None]
    cell_rob=[]
    for cell in common:
        value=float(m.xs(cell,level='cell').mean());lo=cell_loco[cell];dates=cell_date[cell]
        cell_rob.append({'cell':cell,'baseline_log_gap':value,
            'contract_delete_min':min(lo),'contract_delete_max':max(lo),
            'contract_delete_sign_changes':sum(np.sign(v)!=np.sign(value) for v in lo),
            'date_delete_min':min(dates) if dates else None,'date_delete_max':max(dates) if dates else None,
            'date_delete_sign_changes':sum(np.sign(v)!=np.sign(value) for v in dates),
            'date_delete_not_computable':cell_null[cell]})
    # Exact-label endpoint sensitivity: no interpolation; all old rows form label map.
    keep=np.zeros(len(d),dtype=bool);ambiguous=0
    for contract in CONTRACTS:
        mask=d.contract==contract;x=d.loc[mask]
        mapping=x.groupby('t0').session.agg(lambda x:tuple(sorted(set(int(v) for v in x))))
        ambiguous+=sum(len(v)!=1 for v in mapping)
        unique=mapping[mapping.map(len)==1].map(lambda x:x[0])
        endpoint=(x.te+200).map(unique)
        keep[np.flatnonzero(mask.to_numpy())]=np.isfinite(x.o5)&endpoint.eq(x.session)
    filtered=d.loc[keep];fg=groups(filtered);fm=matrix(fg,common)
    known_cells=[cell for cell in common if fm.xs(cell,level='cell').notna().all()]
    filtered_support=fg[fg.delta.notna()]
    matched_original=g.reindex(filtered_support.index)
    matched_m=matrix(matched_original,common)
    secondary=scalar(fm,cells=known_cells) if known_cells else None
    paired_base=scalar(matched_m,cells=known_cells) if known_cells else None
    secondary_contracts=[]
    for c in CONTRACTS:
        secondary_contracts.append({'contract':c,
            'baseline_full_fixed_panel':float(m.xs(c,level='contract').reindex(common).mean()),
            'secondary_complete_cell_count':len(known_cells),
            'baseline_same_supported_groups':float(matched_m.xs(c,level='contract').reindex(known_cells).mean()) if known_cells else None,
            'known_endpoint_same_supported_groups':float(fm.xs(c,level='contract').reindex(known_cells).mean()) if known_cells else None})
    endpoint_cells=[]
    for cell in common:
        complete=cell in known_cells
        before=float(matched_m.xs(cell,level='cell').mean()) if complete else None
        after=float(fm.xs(cell,level='cell').mean()) if complete else None
        endpoint_cells.append({'cell':cell,'status':'COMPUTABLE' if complete else 'NOT_COMPUTABLE',
            'full_panel_baseline':interpret(float(m.xs(cell,level='cell').mean())),
            'same_groups_baseline':interpret(before),'same_groups_known_endpoint':interpret(after),
            'sign_changed': bool(np.sign(before)!=np.sign(after)) if complete else None,
            'supported_contract_count':int(fm.xs(cell,level='cell').notna().sum()),
            'supported_group_count':int((filtered_support.index.get_level_values('cell')==cell).sum())})
    for row in secondary_contracts:
        row['same_groups_baseline_interpretation']=interpret(row['baseline_same_supported_groups'])
        row['same_groups_known_endpoint_interpretation']=interpret(row['known_endpoint_same_supported_groups'])
    finite=int(np.isfinite(d.o5).sum())
    # Endpoint-filter accounting independently using a plain exact-label dictionary.
    labelmap=defaultdict(set)
    for c,t,s in zip(d.contract,d.t0,d.session):labelmap[(c,int(t))].add(int(s))
    keep_direct=[math.isfinite(float(o)) and labelmap.get((c,int(te)+200))=={int(s)} for c,s,te,o in zip(d.contract,d.session,d.te,d.o5)]
    require(np.array_equal(keep,np.array(keep_direct,dtype=bool)),'independent endpoint filter mismatch')
    require(int(keep.sum())==19466 and ambiguous==0,'previous endpoint audit changed')
    summary={'baseline':{**interpret(base),'common_cells':common,'cell_count':len(common),'contracts':6},
        'leave_one_contract_out':{'cases':loco,'all_negative':all(r['log_gap']<0 for r in loco),
            'min_log_gap':min(r['log_gap'] for r in loco),'max_log_gap':max(r['log_gap'] for r in loco),
            'cells_with_sign_change':sum(r['contract_delete_sign_changes']>0 for r in cell_rob)},
        'leave_one_date_out':{'observed_label_cases':len(date_cases),'computable_cases':len(valid),
            'not_computable_cases':len(date_cases)-len(valid),'negative_cases':sum(v<0 for v in valid),
            'positive_cases':sum(v>0 for v in valid),'min_log_gap':min(valid),'max_log_gap':max(valid),
            'cells_with_sign_change':sum(r['date_delete_sign_changes']>0 for r in cell_rob)},
        'known_endpoint_sensitivity':{'all_export_rows':len(d),'finite_o5_rows':finite,'endpoint_known_matching_rows':int(keep.sum()),
            'finite_rows_by_kind':{k:int((np.isfinite(d.o5)&d.kind.eq(k)).sum()) for k in ('real','pseudo')},
            'kept_rows_by_kind':{k:int(filtered.kind.eq(k).sum()) for k in ('real','pseudo')},
            'secondary_cell_sign_changes':sum(row['sign_changed'] is True for row in endpoint_cells),
            'coverage_of_finite_rows':int(keep.sum())/finite,'ambiguous_anchor_labels':int(ambiguous),
            'fixed_31_cell_6_contract_panel_log_gap':scalar(fm,cells=common),
            'complete_cells_in_secondary_panel':known_cells,'secondary_cell_count':len(known_cells),
            'same_supported_groups_baseline':interpret(paired_base),'same_supported_groups_known_endpoint':interpret(secondary),
            'supported_group_count_all_secondary_cells':int(len(filtered_support[filtered_support.index.get_level_values('cell').isin(known_cells)])),
            'paired_group_baseline_is_full_original_population':False,
            'endpoint_selection_is_causal_or_quality_proof':False},
        'existing_missing_o5_rows':len(d)-finite,'independent_max_numeric_difference':maxcheck}
    evidence={'schema':'edgelab_avzvol_exposed_o5_robustness_v1','plan':plan,
        'source_audit_reference_sha256':hashlib.sha256(audit.read_bytes()).hexdigest(),
        'files':[{'file':pin['file'],'sha256':pin['sha256'],'rows':pin['rows']} for pin,file,pf in opened],
        'global_preflight_before_payload':True,'summary':summary,'cell_sensitivity':cell_rob,
        'endpoint_cell_sensitivity':endpoint_cells,'contract_sensitivity':secondary_contracts,'private_date_rows_not_published':True,
        'all_primary_deletions_and_endpoint_filter_independently_checked':True,
        'comparison_plan':[{'question':'Does overall exposed O5 depend on one contract?',
            'grain':'fixed 31-cell equal-contract equal-supported-session mean', 'unit':'log real-minus-legacy-pseudo O5 gap',
            'disposition':'chart','reason':'baseline and all six contract deletions in one common-unit categorical view'},
            {'question':'Does one date or one cell reverse the descriptive pattern?', 'disposition':'prose',
             'reason':'deletion-range and cell exceptions, not confidence intervals'},
            {'question':'Can endpoint-annotated rows certify the original result?', 'disposition':'prose',
             'reason':'fixed panel may lose support; selected-row sensitivity is not a clean corrected estimate'}]}
    summary['leave_one_date_out']['min_geometric_gap_percent']=100*math.expm1(min(valid))
    summary['leave_one_date_out']['max_geometric_gap_percent']=100*math.expm1(max(valid))
    (OUT/'evidence.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2,default=lambda x:x.item())+'\n')
    pd.DataFrame(cell_rob).to_csv(OUT/'cell-sensitivity.csv',index=False)
    pd.DataFrame(secondary_contracts).to_csv(OUT/'contract-sensitivity.csv',index=False)
    print(json.dumps({'baseline':summary['baseline']['relative_geometric_gap_percent'], 'date_deletions':summary['leave_one_date_out'], 'endpoint_sign_changes':summary['known_endpoint_sensitivity']['secondary_cell_sign_changes'], 'by_kind':summary['known_endpoint_sensitivity']['kept_rows_by_kind']},indent=2,default=lambda x:x.item()))

if __name__=="__main__":
    main()
