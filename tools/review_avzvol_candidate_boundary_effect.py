#!/usr/bin/env python3
"""Opt-in sensitivity of ALREADY EXPOSED O5 to candidate post-boundary witnesses.
No raw ticks/prices, new outcome, formal inference or source/census certification.
"""
from pathlib import Path
from collections import defaultdict
import argparse,hashlib,json,math
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
ROOT=Path(__file__).resolve().parents[1]
CONTRACTS=['MNQ_09-25','MNQ_12-25','MNQ_03-26','MNQ_06-26','MNQ_09-26','MNQ_12-26']
CELLS=[f'{m}_{w}_{a}' for m in (4,5,6,8) for w in (250,500,1000) for a in (20,30,45)]
KEYS=['contract','session','cell']
AUDIT_SHA='1611277b3dc6f6393e0c6f280201359f488b8352e80a23bf9c77149e8152192e'

def require(ok,message):
    if not ok:raise ValueError(message)

def digest(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def groups(d):
    f=d[np.isfinite(d.o5)]
    g=f.groupby(KEYS+['kind']).o5.mean().unstack('kind').reindex(columns=['real','pseudo'])
    g['delta']=g.real-g.pseudo;return g

def panel(g,cells):
    ix=pd.MultiIndex.from_product([CONTRACTS,cells],names=['contract','cell'])
    return g.delta.groupby(level=['contract','cell']).mean().reindex(ix)

def interpret(v):
    return {'log_gap':v,'relative_geometric_gap_percent':100*math.expm1(v) if v is not None else None}

def value(p):
    return math.fsum(p)/len(p) if len(p) and p.notna().all() else None

def direct_groups(d):
    raw=defaultdict(list)
    for c,s,cell,k,o in zip(d.contract,d.session,d.cell,d.kind,d.o5):
        if math.isfinite(float(o)):raw[(c,int(s),cell,k)].append(float(o))
    result={}
    for c,s,cell,k in raw:
        if k=='real' and (c,s,cell,'pseudo') in raw:
            r=raw[(c,s,cell,'real')];p=raw[(c,s,cell,'pseudo')]
            result[(c,s,cell)]=math.fsum(r)/len(r)-math.fsum(p)/len(p)
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['map-evidence','map-dir','export-inventory','out-dir']:p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--map-evidence-sha256',required=True)
    p.add_argument('--allow-exposed-o5-review',action='store_true',required=True)
    a=p.parse_args();require(digest(a.map_evidence)==a.map_evidence_sha256,'candidate evidence pin mismatch')
    evidence=json.loads(a.map_evidence.read_text())
    require(evidence['status']=='CANDIDATE_TIMESTAMP_MAP_ONLY_NOT_CERTIFIED' and len(evidence['files'])==6,'wrong candidate evidence')
    require(evidence['all_twelve_pins_and_footers_before_payload'] is True,'missing candidate preflight')
    require(not evidence['holdout_payload_opened'] and not evidence['source_quality_certified'],'unexpected source scope')
    ref=ROOT/'docs/infra/AVZVOL_AUDIT_20261010.json';require(digest(ref)==AUDIT_SHA,'export reference pin mismatch')
    pins={r['file']:r for r in json.loads(ref.read_text())['covariate_audit']['files']}
    inv=json.loads(a.export_inventory.read_text());paths={Path(r['file']).name:Path(r['file']) for r in inv}
    require(len(inv)==len(paths)==6 and set(paths)==set(pins),'exact export universe required')
    records={r['contract']:r for r in evidence['files']};require(set(records)==set(CONTRACTS),'candidate universe mismatch')
    opened={};maps={}
    for name,file in paths.items():
        pf=pq.ParquetFile(file);require(pf.metadata.num_rows==pins[name]['rows'],'export rows mismatch')
        for k in range(pf.num_row_groups):
            st=pf.metadata.row_group(k).column(pf.schema_arrow.names.index('session')).statistics
            require(st and st.has_min_max and st.has_null_count and st.null_count==0 and int(st.max)<20261001,'reserved export footer')
        require(digest(file)==pins[name]['sha256'],'export SHA mismatch');opened[name]=pf
    # Every private map verified BEFORE any exposed O5 values.
    for c in CONTRACTS:
        r=records[c];file=a.map_dir/(c+'-private-map.npz')
        require(r['all_export_anchors_align'] and digest(file)==r['private_map_sha256'],'candidate map alignment/SHA mismatch')
        with np.load(file,allow_pickle=False) as m:maps[c]={k:m[k] for k in ['end_ns','session','clock']}
        m=maps[c];require(len(m['session'])==r['historical_logged_bar_count']==r['candidate_bar_count'],'map count mismatch')
        require(len(m['end_ns'])==len(m['session'])==len(m['clock']) and int(m['end_ns'].max())<pd.Timestamp('2026-09-30T22:00:00Z').value,'map shape/holdout')
        require((m['session']<20261001).all() and (np.diff(m['session'])>=0).all(),'unknown/nonmonotonic candidate sessions')
    frames=[];removed=[];direct_count=0
    for c in CONTRACTS:
        d=opened[c+'_avzp2racgrid.parquet'].read(columns=['contract','cell','kind','session','clock','t0','te','o5']).to_pandas()
        m=maps[c];label=m['session'];t=d.t0.to_numpy();te=d.te.to_numpy();s=d.session.to_numpy()
        require(set(d.contract)=={c} and (t>=0).all() and (t<len(label)).all(),'anchor identity')
        require(np.array_equal(label[t],s) and np.array_equal(m['clock'][t],d.clock.to_numpy()),'anchor mismatch')
        finite=np.isfinite(d.o5);require(not np.isinf(d.o5).any() and not (finite&(te<0)).any(),'invalid O5 annotation')
        require((te[finite]>t[finite]).all() and (te[finite]<len(label)).all(),'candidate exit identity mismatch')
        require(np.array_equal(label[te[finite]],s[finite]),'candidate exit session mismatch')
        require((te<=np.iinfo(np.int64).max-200).all(),'overflow')
        within=(te>=0)&(te+200<len(label));keep=np.zeros(len(d),dtype=bool)
        k=np.flatnonzero(within & finite)
        keep[k]=(label[te[k]+1]==s[k])&(label[te[k]+200]==s[k])
        # Monotonic labels make endpoint equality sufficient; verify ALL 200
        # values independently for every unique exit/session anyway.
        direct={}
        for i in np.flatnonzero(finite):
            pair=(int(te[i]),int(s[i]))
            if pair not in direct:
                direct[pair]=bool(pair[0]>=0 and pair[0]+200<len(label) and all(int(v)==pair[1] for v in label[pair[0]+1:pair[0]+201]))
            require(bool(keep[i])==direct[pair],'independent mask mismatch');direct_count+=int(not direct[pair])
        d['candidate_keep']=keep
        removed.append({'contract':c,'excluded_rows':int((finite&~keep).sum()),'excluded_real_rows':int((finite&~keep&d.kind.eq('real')).sum()),'excluded_pseudo_rows':int((finite&~keep&d.kind.eq('pseudo')).sum())})
        frames.append(d)
    d=pd.concat(frames,ignore_index=True);g=groups(d);initial=panel(g,CELLS)
    common=[cell for cell in CELLS if initial.xs(cell,level='cell').notna().all()]
    require(len(common)==31,'fixed development panel changed')
    f=d[d.candidate_keep];fg=groups(f);base=panel(g,common);filtered=panel(fg,common)
    supported=fg[fg.delta.notna()].index
    samegroupbase=panel(g.reindex(supported),common)
    primary=value(base);changed=value(filtered);paired=value(samegroupbase)
    require(abs(primary-(-0.06700330861123599))<1e-12,'original O5 baseline changed')
    # Numeric headlines checked independently from raw EXPOSED values, lists/fsum.
    check=[]
    for frame,target,wanted_groups in [(d,primary,None),(f,changed,None),(d,paired,set(supported))]:
        bins=defaultdict(list)
        for (c,s,cell),v in direct_groups(frame).items():
            if cell in common and (wanted_groups is None or (c,s,cell) in wanted_groups):bins[(c,cell)].append(v)
        vals=[math.fsum(bins[(c,cell)])/len(bins[(c,cell)]) if bins[(c,cell)] else None for c in CONTRACTS for cell in common]
        expected=math.fsum(vals)/len(vals) if all(v is not None for v in vals) else None
        require((expected is None)==(target is None) and (target is None or abs(expected-target)<1e-12),'independent effect mismatch')
        check.append(abs(expected-target) if target is not None else 0)
    cells=[{'cell':cell,'original':interpret(value(base.xs(cell,level='cell'))),'candidate_boundary_excluded':interpret(value(filtered.xs(cell,level='cell')))} for cell in common]
    changes=int(sum(np.sign(r['original']['log_gap'])!=np.sign(r['candidate_boundary_excluded']['log_gap']) for r in cells if r['candidate_boundary_excluded']['log_gap'] is not None))
    totals={'export_rows':len(d),'finite_o5_rows':int(np.isfinite(d.o5).sum()),'missing_o5_rows':int(d.o5.isna().sum()),'excluded_candidate_cross_rows':sum(r['excluded_rows'] for r in removed),'excluded_real_rows':sum(r['excluded_real_rows'] for r in removed),'excluded_pseudo_rows':sum(r['excluded_pseudo_rows'] for r in removed),'fixed_cells':len(common),'lost_supported_session_cell_groups':len(g[g.delta.notna()].index.difference(supported)),'original':interpret(primary),'candidate_boundary_excluded':interpret(changed),'original_same_filtered_support_groups':interpret(paired),'cell_sign_changes':changes,'independent_max_numeric_difference':max(check)}
    require(totals['excluded_candidate_cross_rows']==direct_count==evidence['totals']['legacy_guard_last_bar_cross_witness_rows'],'candidate witness count changed')
    totals['change_in_geometric_gap_percentage_points']=100*(math.expm1(changed)-math.expm1(primary)) if changed is not None else None
    a.out_dir.mkdir(parents=True,exist_ok=False)
    result={'schema':'edgelab_exposed_o5_candidate_boundary_sensitivity_v1','scope':'EXPOSED_O5_SENSITIVITY_ONLY_NOT_CORRECTED_CAUSAL_ESTIMATE','candidate_evidence_sha256':a.map_evidence_sha256,'source_export_audit_sha256':AUDIT_SHA,'totals':totals,'excluded_by_contract':removed,'cells':cells,'all_maps_and_export_pins_before_o5_payload':True,'all_candidate_masks_and_effects_independently_checked':True,**{k:False for k in ['new_price_outcomes_computed','economic_outcomes_computed','source_quality_certified','historical_consumption_attested','prewindow_verified','causal_controls_verified','formal_inference_executed','original_outputs_modified','research_release_authorized']}}
    (a.out_dir/'evidence.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(totals,indent=2))

if __name__=='__main__':
    try:main()
    except (ValueError,TypeError,KeyError,OSError) as exc:
        print(json.dumps({'status':'STOP','reason':str(exc)}));raise SystemExit(2)
