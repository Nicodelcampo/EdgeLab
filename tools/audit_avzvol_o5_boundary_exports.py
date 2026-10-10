#!/usr/bin/env python3
"""Opt-in internal-label boundary audit of exposed O5; no prices/new endpoints.

Exact anchor-label witnesses ONLY. Absence of witnesses does not clear the
legacy guard: these exports lack a complete bar/session map and prewindow starts.
"""
from pathlib import Path
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
import pandas as pd
import pyarrow.parquet as pq

CATEGORIES = ('last_label_matches_anchor', 'last_label_diff_penultimate_same',
    'last_label_diff_penultimate_unknown', 'last_and_penultimate_labels_diff',
    'last_label_unknown', 'last_label_ambiguous')
COLS = ['contract','cell','kind','session','t0','te','o5']


def require(ok, message):
    if not ok: raise ValueError(message)


def audit_frame(d):
    """Contract-homogeneous exposed rows; no inference of unobserved bar labels."""
    require(d[COLS[:-1]].notna().all().all(), 'missing identities')
    require(d.contract.nunique()==1 and set(d.kind)<={'real','pseudo'},'identity/kind mismatch')
    for col in ['session','t0','te']:
        require(pd.api.types.is_integer_dtype(d[col]),'integer bar/session identity required')
    require((d.t0>=0).all() and (d.session<20261001).all(),'invalid/reserved identity')
    require(not any(math.isinf(float(x)) for x in d.o5),'infinite O5')
    labels=d.groupby('t0',sort=True).session.agg(lambda s: tuple(sorted(set(int(x) for x in s))))
    finite=d.o5.notna()
    require(not (finite & (d.te<0)).any(),'finite O5 with no exit')
    x=d.loc[finite].copy()
    last=x.te+200;penultimate=x.te+199
    last_sets=last.map(labels);pen_sets=penultimate.map(labels)
    counts=Counter();bykind=defaultdict(Counter);witnesses=[]
    categories=[]
    for i,row in enumerate(x.itertuples(index=False)):
        ls,ps=last_sets.iloc[i],pen_sets.iloc[i]
        if not isinstance(ls,tuple):cat='last_label_unknown'
        elif len(ls)!=1:cat='last_label_ambiguous'
        elif ls[0]==row.session:cat='last_label_matches_anchor'
        elif isinstance(ps,tuple) and len(ps)==1:
            cat='last_label_diff_penultimate_same' if ps[0]==row.session else 'last_and_penultimate_labels_diff'
        else:cat='last_label_diff_penultimate_unknown'
        categories.append(cat);counts[cat]+=1;bykind[row.kind][cat]+=1
        if cat.startswith('last_label_diff') or cat=='last_and_penultimate_labels_diff':
            witnesses.append({'contract':row.contract,'cell':row.cell,'kind':row.kind,
                'session':int(row.session),'t0':int(row.t0),'te':int(row.te),
                'last_bar':int(row.te+200),'last_bar_label':int(ls[0]),'category':cat})
    # Independent plain-Python path, not the groupby/map join above.
    direct=defaultdict(set)
    for t,s in zip(d.t0.to_numpy(),d.session.to_numpy()):direct[int(t)].add(int(s))
    independent=Counter()
    for te,s,o in zip(d.te.to_numpy(),d.session.to_numpy(),d.o5.to_numpy()):
        if not math.isfinite(float(o)):continue
        ls=direct.get(int(te)+200);ps=direct.get(int(te)+199)
        if ls is None:cat='last_label_unknown'
        elif len(ls)!=1:cat='last_label_ambiguous'
        elif int(s) in ls:cat='last_label_matches_anchor'
        elif ps is not None and len(ps)==1:
            cat='last_label_diff_penultimate_same' if int(s) in ps else 'last_and_penultimate_labels_diff'
        else:cat='last_label_diff_penultimate_unknown'
        independent[cat]+=1
    require(counts==independent,'independent label audit mismatch')
    full={k:counts[k] for k in CATEGORIES}
    require(sum(full.values())==int(finite.sum()),'finite population does not cross-foot')
    return {'contract':str(d.contract.iloc[0]),'export_rows':len(d),
        'finite_o5_rows':int(finite.sum()),'missing_o5_rows':int((~finite).sum()),
        'unique_anchor_bar_labels':len(labels),
        'ambiguous_anchor_bar_labels':int(sum(len(x)!=1 for x in labels)),
        'finite_row_categories':full,
        'by_kind':{kind:{k:bykind[kind][k] for k in CATEGORIES} for kind in ['real','pseudo']},
        'independent_crosscheck_passed':True},witnesses


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--audit-reference',type=Path,required=True)
    p.add_argument('--audit-reference-sha256',required=True)
    p.add_argument('--inventory',type=Path,required=True)
    p.add_argument('--out-dir',type=Path,required=True)
    p.add_argument('--allow-exposed-output-audit',action='store_true',required=True)
    a=p.parse_args()
    require(hashlib.sha256(a.audit_reference.read_bytes()).hexdigest()==a.audit_reference_sha256,'audit reference pin mismatch')
    pins=json.loads(a.audit_reference.read_text())['covariate_audit']['files']
    inv=json.loads(a.inventory.read_text())
    require(isinstance(inv,list) and len(inv)==len(pins)==6,'exact six pinned exports required')
    paths={Path(x['file']).name:Path(x['file']) for x in inv}
    require(len(paths)==6 and set(paths)=={x['file'] for x in pins},'export universe mismatch')
    opened=[]
    for pin in pins:
        file=paths[pin['file']];pf=pq.ParquetFile(file)
        require(pf.metadata.num_rows==pin['rows'] and set(COLS)<=set(pf.schema_arrow.names),'footer row/schema mismatch')
        idx=pf.schema_arrow.names.index('session')
        for i in range(pf.num_row_groups):
            st=pf.metadata.row_group(i).column(idx).statistics
            require(st and st.has_min_max and st.has_null_count and st.null_count==0 and int(st.max)<20261001,'unknown/reserved footer session')
        opened.append((pin,file,pf))
    for pin,file,pf in opened:
        with file.open('rb') as stream:
            require(hashlib.file_digest(stream,'sha256').hexdigest()==pin['sha256'],'export SHA mismatch')
    # All file metadata/pins pass before ANY event payload.
    a.out_dir.mkdir(parents=True,exist_ok=False)
    records=[];witnesses=[]
    for pin,file,pf in opened:
        r,w=audit_frame(pf.read(columns=COLS).to_pandas())
        require(r['contract']==file.name.removesuffix('_avzp2racgrid.parquet'),'physical contract mismatch')
        r.update(file=file.name,sha256=pin['sha256']);records.append(r);witnesses.extend(w)
    totals={k:sum(r[k] for r in records) for k in ['export_rows','finite_o5_rows','missing_o5_rows','unique_anchor_bar_labels','ambiguous_anchor_bar_labels']}
    totals['finite_row_categories']={k:sum(r['finite_row_categories'][k] for r in records) for k in CATEGORIES}
    totals['exact_last_label_coverage_share']=((totals['finite_o5_rows']-totals['finite_row_categories']['last_label_unknown']-totals['finite_row_categories']['last_label_ambiguous'])/totals['finite_o5_rows']) if totals['finite_o5_rows'] else None
    evidence={'schema':'edgelab_avzvol_exposed_o5_boundary_label_audit_v1',
        'scope':'INTERNAL_LABEL_WITNESSES_ONLY_NOT_FULL_WINDOW_CERTIFICATION',
        'method':'Exact t0->session map from all existing event rows; compare finite O5 last included index te+200 with anchor session. Never interpolate unobserved bars. Penultimate te+199 used only if an exact unambiguous label exists.',
        'grain':'event x cell export rows, not independent events/sessions',
        'source_audit_reference_sha256':a.audit_reference_sha256,'files':records,'totals':totals,
        'all_hashes_and_footers_verified_before_payload':True,
        'independent_crosscheck_passed':True,'new_outcomes_computed':False,
        'existing_o5_values_recomputed_or_corrected':False,'raw_ticks_opened':False,'research_authorized':False,
        'holdout_opened':False,'source_quality_certified':False,
        'absence_of_witnesses_clears_legacy_guard':False,'prewindow_session_coverage_verified':False,
        'private_witness_rows_not_published':True,'original_outputs_modified':False}
    (a.out_dir/'evidence.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n')
    pd.DataFrame(witnesses).to_csv(a.out_dir/'private-witnesses.csv',index=False)
    print(json.dumps(totals,sort_keys=True))

if __name__=='__main__':
    try:main()
    except (ValueError,TypeError,KeyError,OSError) as exc:
        print(json.dumps({'status':'STOP','reason':str(exc)}));raise SystemExit(2)
