#!/usr/bin/env python3
"""Audit all 200 existing post-window bar labels, never optimize/filter O5 effects.

Exact exported anchor annotations only: UNKNOWN is not a data hole or zero.
No prices, corrected outcome, pre-window map or scientific certification.
"""
from pathlib import Path
from collections import Counter, defaultdict
from bisect import bisect_left, bisect_right
import argparse
import hashlib
import json
import math
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

COLS=['contract','cell','kind','session','t0','te','o5']
CATEGORIES=('FULL_POSTWINDOW_ANNOTATED_SAME_SESSION','PARTIAL_OR_UNKNOWN_POSTWINDOW',
            'CONTRADICTORY_OBSERVED_SESSION_LABEL','AMBIGUOUS_OBSERVED_LABEL')

def require(ok,message):
    if not ok:raise ValueError(message)

def audit_frame(d):
    require(d[COLS[:-1]].notna().all().all(),'missing identities')
    require(d.contract.nunique()==1 and set(d.kind)<={'real','pseudo'},'identity/kind mismatch')
    for col in ('session','t0','te'):
        require(pd.api.types.is_integer_dtype(d[col]),'integer identities required')
    require((d.t0>=0).all() and (d.session<20261001).all(),'invalid/reserved identities')
    require(not np.isinf(d.o5).any(),'infinite existing O5')
    finite=np.isfinite(d.o5);require(not (finite & (d.te<0)).any(),'finite O5 without exit')
    require((d.te <= np.iinfo(np.int64).max-200).all(),'bar index overflow')
    x=d.loc[finite]
    # Distinct physical bar indices, NOT number of repeated event/cell rows.
    labels=d.groupby('t0',sort=True).session.agg(lambda a:tuple(sorted(set(int(v) for v in a))))
    indices=labels.index.to_numpy(dtype=np.int64)
    unique=np.array([len(v)==1 for v in labels],dtype=bool)
    single=np.array([v[0] if len(v)==1 else -1 for v in labels],dtype=np.int64)
    left=np.searchsorted(indices,x.te.to_numpy()+1,side='left')
    right=np.searchsorted(indices,x.te.to_numpy()+200,side='right')
    known=right-left
    ambiguous_prefix=np.r_[0,np.cumsum(~unique)]
    ambiguous=ambiguous_prefix[right]-ambiguous_prefix[left]
    contrary=np.zeros(len(x),dtype=np.int64)
    for session in x.session.unique():
        mask=x.session.to_numpy()==session
        p=np.r_[0,np.cumsum(unique & (single!=session))]
        contrary[mask]=p[right[mask]]-p[left[mask]]
    categories=np.where(contrary>0,CATEGORIES[2],np.where(ambiguous>0,CATEGORIES[3],
        np.where(known==200,CATEGORIES[0],CATEGORIES[1])))
    # Independent dictionaries + bisect, no vectorized prefix sums; cache by exit/session.
    mapping=defaultdict(set)
    for t,s in zip(d.t0,d.session):mapping[int(t)].add(int(s))
    keys=sorted(mapping);cache={};independent=[]
    for te,s in zip(x.te,x.session):
        pair=(int(te),int(s))
        if pair not in cache:
            lo=bisect_left(keys,pair[0]+1);hi=bisect_right(keys,pair[0]+200)
            observed=[mapping[i] for i in keys[lo:hi]]
            wrong=sum(len(v)==1 and pair[1] not in v for v in observed)
            unclear=sum(len(v)!=1 for v in observed)
            cat=CATEGORIES[2] if wrong else CATEGORIES[3] if unclear else CATEGORIES[0] if len(observed)==200 else CATEGORIES[1]
            cache[pair]=(cat,len(observed),wrong,unclear)
        independent.append(cache[pair])
    require(all((str(cat),int(n),int(w),int(a))==row for cat,n,w,a,row in
        zip(categories,known,contrary,ambiguous,independent)),'independent window-label check mismatch')
    counts=Counter(categories);full={c:counts[c] for c in CATEGORIES}
    bykind={k:{c:int(((x.kind.to_numpy()==k)&(categories==c)).sum()) for c in CATEGORIES} for k in ('real','pseudo')}
    require(sum(full.values())==len(x),'finite counts do not cross-foot')
    buckets={'zero':int((known==0).sum()),'one_to_49':int(((known>0)&(known<50)).sum()),
             '50_to_199':int(((known>=50)&(known<200)).sum()),'all_200':int((known==200).sum())}
    require(sum(buckets.values())==len(x),'coverage bins do not cross-foot')
    return {'contract':str(d.contract.iloc[0]),'export_rows':len(d),'finite_o5_rows':len(x),
        'missing_o5_rows':int((~finite).sum()),'unique_anchor_bar_labels':len(labels),
        'ambiguous_anchor_bar_labels':int((~unique).sum()),'finite_row_categories':full,
        'by_kind':bykind,'distinct_observed_bar_count_buckets':buckets,
        'min_distinct_observed_bars':int(known.min()) if len(x) else None,
        'max_distinct_observed_bars':int(known.max()) if len(x) else None,
        'independent_crosscheck_passed':True}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--audit-reference',type=Path,required=True)
    p.add_argument('--audit-reference-sha256',required=True)
    p.add_argument('--inventory',type=Path,required=True)
    p.add_argument('--out-dir',type=Path,required=True)
    p.add_argument('--allow-exposed-output-audit',action='store_true',required=True)
    a=p.parse_args()
    require(hashlib.sha256(a.audit_reference.read_bytes()).hexdigest()==a.audit_reference_sha256,'reference pin mismatch')
    pins=json.loads(a.audit_reference.read_text())['covariate_audit']['files']
    inv=json.loads(a.inventory.read_text())
    require(isinstance(inv,list) and len(inv)==len(pins)==6,'exact six exports required')
    paths={Path(x['file']).name:Path(x['file']) for x in inv}
    require(len(paths)==6 and set(paths)=={x['file'] for x in pins},'universe mismatch')
    opened=[]
    for pin in pins:
        file=paths[pin['file']];pf=pq.ParquetFile(file)
        require(pf.metadata.num_rows==pin['rows'] and set(COLS)<=set(pf.schema_arrow.names),'footer schema/rows mismatch')
        i=pf.schema_arrow.names.index('session')
        for k in range(pf.num_row_groups):
            st=pf.metadata.row_group(k).column(i).statistics
            require(st and st.has_min_max and st.has_null_count and st.null_count==0 and int(st.max)<20261001,'unknown/reserved footer')
        opened.append((pin,file,pf))
    for pin,file,pf in opened:
        with file.open('rb') as stream:require(hashlib.file_digest(stream,'sha256').hexdigest()==pin['sha256'],'export SHA mismatch')
    a.out_dir.mkdir(parents=True,exist_ok=False)
    records=[]
    for pin,file,pf in opened:
        r=audit_frame(pf.read(columns=COLS).to_pandas())
        require(r['contract']==file.name.removesuffix('_avzp2racgrid.parquet'),'physical contract mismatch')
        r.update(file=file.name,sha256=pin['sha256']);records.append(r)
    totals={k:sum(r[k] for r in records) for k in ('export_rows','finite_o5_rows','missing_o5_rows','unique_anchor_bar_labels','ambiguous_anchor_bar_labels')}
    totals['finite_row_categories']={k:sum(r['finite_row_categories'][k] for r in records) for k in CATEGORIES}
    totals['distinct_observed_bar_count_buckets']={k:sum(r['distinct_observed_bar_count_buckets'][k] for r in records) for k in records[0]['distinct_observed_bar_count_buckets']}
    totals['full_postwindow_annotation_coverage_share']=totals['finite_row_categories'][CATEGORIES[0]]/totals['finite_o5_rows'] if totals['finite_o5_rows'] else None
    evidence={'schema':'edgelab_avzvol_o5_postwindow_label_audit_v1',
        'scope':'FULL_POSTWINDOW_INTERNAL_ANNOTATION_CHECK_ONLY_NOT_MARKET_CERTIFICATION',
        'method':'For each existing finite O5, inspect ALL distinct observed t0 indices in inclusive [te+1,te+200]; 200 exact unambiguous same-session labels required. No interpolation. Contradictory unambiguous labels take precedence over ambiguous labels, then complete versus partial coverage.',
        'grain':'event x cell export rows, not independent events or sessions',
        'source_audit_reference_sha256':a.audit_reference_sha256,'files':records,'totals':totals,
        'all_hashes_and_footers_verified_before_payload':True,'independent_crosscheck_passed':True,
        **{k:False for k in ('new_outcomes_computed','existing_o5_values_recomputed_or_corrected',
            'raw_ticks_opened','holdout_opened','research_authorized','source_quality_certified',
            'absence_of_witnesses_clears_legacy_guard','prewindow_coverage_verified',
            'causal_controls_verified','original_outputs_modified','economic_outcomes_computed')},
        'comparison_plan':[{'question':'Can existing annotations verify complete post-windows?',
            'grain':'all finite exposed event/cell rows','unit':'row counts with exact label coverage',
            'disposition':'prose','reason':'QA coverage result; no filtered effect or optimization; inline artifact delivery unavailable'}]}
    (a.out_dir/'evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')
    print(json.dumps(totals,sort_keys=True))

if __name__=='__main__':
    try:main()
    except (ValueError,TypeError,KeyError,OSError) as exc:
        print(json.dumps({'status':'STOP','reason':str(exc)}));raise SystemExit(2)
