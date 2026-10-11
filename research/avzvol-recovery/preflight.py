import csv,json,hashlib,pathlib,sys
import pandas as pd,pyarrow.parquet as pq
P=pathlib.Path('/data/recovery');A=pathlib.Path('/data/raw/avzvol-selected-risk/pr111-authorization.json');a=json.load(open(A));m=json.load(open(P/'fixed-manifest.json'));s=pathlib.Path('/data/analysis/avzvol-selected-risk/selected-event-sessions.csv');assert a['gates']['user_exploratory_authorized'] and not a['holdout_access_authorized'] and not a['pnl_or_promotion_authorized'];assert hashlib.sha256(s.read_bytes()).hexdigest()==m['source_selection_sha256'];rows=list(csv.DictReader(s.open()));assert len(rows)==261 and len({(r['contract'],r['session_label']) for r in rows})==261
sys.path.insert(0,'/data/analysis/avzvol-pilot');from run_pilot import CUTOFF
result=[]
for pin in a['files']:
 p=pathlib.Path('/data/raw/avzvol-ticks')/pin['file'];assert p.stat().st_size==pin['bytes'];h=hashlib.file_digest(p.open('rb'),'sha256').hexdigest();assert h==pin['sha256'];pf=pq.ParquetFile(p);assert pf.metadata.num_rows==pin['rows'];assert pf.schema_arrow.names==['ts_utc_ns','ts_local_ns','sequence','price_ticks','bid_ticks','ask_ticks','volume','aggressor','tick_type','instrument','contract','source_file','source_row']
 for i in range(pf.metadata.num_row_groups):
  rg=pf.metadata.row_group(i)
  for col in pf.schema_arrow.names:assert rg.column(pf.schema_arrow.names.index(col)).statistics.null_count==0
  st=rg.column(0).statistics;assert st.max<CUTOFF
  for col,val in [('instrument','MNQ'),('contract',pin['contract'].replace('_',' '))]:
   st=rg.column(pf.schema_arrow.names.index(col)).statistics;assert st.min==st.max==val
 sel=[r for r in rows if r['contract']==pin['contract']];assert [r['session_label'] for r in sel]==m['event_dates'][pin['contract']];pd.to_datetime([r['session_label'] for r in sel],format='%Y-%m-%d',errors='raise')
 result.append(dict(contract=pin['contract'],sha256=h,bytes=p.stat().st_size,rows=pf.metadata.num_rows,row_groups=pf.metadata.num_row_groups,selected_dates=len(sel),footer_cutoff_and_contract_pass=True,prior_structural_audit_reused_only_for_byte_identical_sources=True))
for n in ['test-evidence.json','cache-test-evidence.json','schema-test-evidence.json','matrix-test-evidence.json','matrix-batch-test-evidence.json']:
 d=json.load(open('/data/analysis/avzvol-longevity/'+n));assert d['status']=='PASS',d
f=json.load(open('/data/analysis/avzvol-focus/test-evidence.json'));assert f['status']=='PASS';out=dict(status='PASS_EXACT_RECOVERY_PREFLIGHT',base_commit='798411780dad69eedc865153ae84a5e819d5ae03',selection_sha256=m['source_selection_sha256'],files=result,total_raw_rows=sum(x['rows'] for x in result),selected_date_contract_rows=len(rows),holdout_opened=False,source_certified=False,original_sources_modified=False,profile_warning_resolution='session_label strictly parsed as calendar labels, not UTC instants; do not interpret trade-count sum/calendar-span as a daily market rate',structural_claim='prior streaming QA remains applicable because bytes are identical; current pass rechecks hashes/footer, runtime prepare rechecks stream order/counts/selection',tests_rerun=True)
(P/'preflight.json').write_text(json.dumps(out,indent=2)+'\n');print('PREFLIGHT_PASS',len(result),out['total_raw_rows'],len(rows),flush=True)
