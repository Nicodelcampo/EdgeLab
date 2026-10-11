#!/usr/bin/env python3
"""Trace bounded post-expiry source identities; never decode prices or outcomes."""
from pathlib import Path, PureWindowsPath
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo
from collections import Counter
import argparse, hashlib, json
import pyarrow.compute as pc
import pyarrow.parquet as pq
ROOT=Path(__file__).resolve().parents[1]
CONTRACTS={'MNQ_09-25','MNQ_12-25'}
COLS=['ts_utc_ns','sequence','tick_type','instrument','contract','source_file','source_row']
CUTOFF=1790805600000000000

def require(ok, message):
    if not ok:raise ValueError(message)

def digest(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def civil_day_after_expiry_ns(expiry):
    d=date.fromisoformat(expiry)+timedelta(days=1)
    return int(datetime.combine(d,time(),ZoneInfo('America/Chicago')).timestamp())*1_000_000_000

def reported_ct(ts):
    seconds,ns=divmod(ts,1_000_000_000)
    dt=datetime.fromtimestamp(seconds,ZoneInfo('America/Chicago'))
    return dt.strftime('%Y-%m-%dT%H:%M:%S')+f'.{ns:09d}'+dt.strftime('%z')

def select_identities(table, cutoff):
    require(table.column_names==COLS,'unexpected payload columns')
    require(all(table[c].null_count==0 for c in COLS),'unknown identity value')
    return table.filter(pc.greater_equal(table['ts_utc_ns'],cutoff)).to_pylist()

def run(inventory, expiry_evidence, out_dir):
    ev=json.loads(Path(expiry_evidence).read_text());expiry={x['contract']:x['official_reference']['expiry'] for x in ev['files']}
    refs=json.loads((ROOT/'config/research/avzvol_mnq_raw_quality_review_20261010.json').read_text())['files']
    refs={x['candidate_contract']:x['structural_audit'] for x in refs}
    inv=json.loads(Path(inventory).read_text());paths={x['contract']:Path(x['file']) for x in inv}
    require(len(inv)==len(paths)==2 and set(paths)==CONTRACTS,'exact two flagged-contract raw sources required')
    opened={};preflight=[]
    for c,p in paths.items():
        ref=refs[c];require(p.stat().st_size==ref['bytes'] and digest(p)==ref['sha256'],'raw source pin mismatch')
        pf=pq.ParquetFile(p);names=pf.schema_arrow.names
        require(set(COLS)<=set(names) and pf.metadata.num_rows==ref['rows'],'raw source shape mismatch')
        for i in range(pf.num_row_groups):
            rg=pf.metadata.row_group(i)
            for name in COLS:
                st=rg.column(names.index(name)).statistics
                require(st and st.has_min_max and st.has_null_count and st.null_count==0,'unknown source footer statistics')
                if name=='ts_utc_ns':require(st.max<CUTOFF,'reserved source partition')
                if name=='instrument':require(st.min==st.max=='MNQ','wrong instrument')
                if name=='contract':require(st.min==st.max==c.replace('_',' '),'wrong contract')
        opened[c]=pf;preflight.append({'contract':c,'file':p.name,'sha256':ref['sha256'],'bytes':ref['bytes'],'rows':ref['rows']})
    out=Path(out_dir);out.mkdir(parents=True,exist_ok=False)
    plan={'scope':'BOUNDED_SOURCE_IDENTITY_QA_NOT_RESEARCH_REPLAY','columns_read':COLS,
          'all_two_pins_and_all_footer_partitions_checked_before_payload':True,
          'query':'reported UTC interpreted in Chicago civil dates strictly after official expiry date; source clock not certified',
          'row_group_pruning':'only groups with timestamp maximum at or after first following Chicago midnight',
          'prices_volume_quotes_aggressor_outcomes_prohibited':True,
          'original_nt8_text_or_capture_log_verified':False}
    (out/'analysis-plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    rows=[];scans=[]
    for c in sorted(opened):
        pf=opened[c];start=civil_day_after_expiry_ns(expiry[c]);ix=pf.schema_arrow.names.index('ts_utc_ns');groups=[];decoded=0
        for i in range(pf.num_row_groups):
            rg=pf.metadata.row_group(i)
            if rg.column(ix).statistics.max<start:continue
            groups.append(i);t=pf.read_row_group(i,columns=COLS);decoded+=t.num_rows
            selected=select_identities(t,start)
            require(sum(int(v>=start) for v in t['ts_utc_ns'].to_pylist())==len(selected),'independent filter count mismatch')
            for x in selected:
                require(x['instrument']=='MNQ' and x['contract']==c.replace('_',' '),'payload identity mismatch')
                x['candidate_contract']=c;x['row_group_index']=i;x['reported_ct']=reported_ct(x['ts_utc_ns'])
                # Public evidence carries exact basename and full path digest, not private directory.
                path=x.pop('source_file');x['source_file_basename']=PureWindowsPath(path).name
                x['source_file_path_sha256']=hashlib.sha256(path.encode()).hexdigest()
                x['upstream_cause']='UNKNOWN';x['source_row_is_original_text_line_verified']=False
                rows.append(x)
        scans.append({'contract':c,'row_groups_read':groups,'rows_decoded_in_identity_columns_only':decoded,'cutoff_utc_ns':start})
    count=Counter(x['candidate_contract'] for x in rows)
    expected=Counter()
    for f in ev['files']:
        for x in f['flagged_date_records']:
            if x['contract'] in CONTRACTS:expected[x['contract']]+=x['declared_ticks']
    require(count==expected,'physical identity row count does not reconcile with flagged summary; STOP')
    for f in ev['files']:
        for x in f['flagged_date_records']:
            if x['contract'] not in CONTRACTS:continue
            witnesses=[w for w in rows if w['candidate_contract']==x['contract'] and w['reported_ct'][:10]==x['declared_date']]
            require(len(witnesses)==x['declared_ticks'] and min(w['reported_ct'] for w in witnesses)==x['first_ct'] and max(w['reported_ct'] for w in witnesses)==x['last_ct'],'physical date/endpoints differ from summary; STOP')
    result={'schema':'edgelab_avzvol_postexpiry_identity_trace_v1','status':'PHYSICAL_IDENTITY_WITNESSES_FOUND_UPSTREAM_CAUSE_UNKNOWN',
            'plan':plan,'source_pins':preflight,'expiry_evidence_sha256':digest(expiry_evidence),
            'recipe_sha256':digest(__file__),'physical_postexpiry_rows':len(rows),'identity_witnesses':rows,'scan_accounting':scans,
            'independent_filter_checks_completed':True,'physical_count_matches_summary':True,'physical_date_and_endpoints_match_summary':True,
            'source_identity_payload_read':True,
            **{k:False for k in ['raw_price_payload_read','volume_payload_read','outcome_exports_read','new_market_outcomes_computed',
             'economic_outcomes_computed','holdout_payload_read','source_clock_certified','source_quality_certified',
             'upstream_nt8_text_or_log_verified','research_release_authorized','source_rows_excluded','historical_outputs_modified']}}
    (out/'evidence.json').write_text(json.dumps(result,indent=2)+'\n');return result

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ['inventory','expiry-evidence','out-dir']:p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--allow-bounded-source-identity-qa',action='store_true',required=True);a=p.parse_args()
    try:
        r=run(a.inventory,a.expiry_evidence,a.out_dir);print(json.dumps({'status':r['status'],'physical_postexpiry_rows':r['physical_postexpiry_rows'],'witnesses':r['identity_witnesses']}))
    except (ValueError,OSError,KeyError,TypeError) as exc:print(json.dumps({'status':'STOP','reason':str(exc)}));raise SystemExit(2)

if __name__=='__main__':main()
