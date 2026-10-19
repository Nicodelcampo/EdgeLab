"""Bounded aggregate acquisition planning and local failure review.
No remote signer, raw payload access, retry, scheduling or canonical writing.
URL issuing/authentication remains with MCP; host verifies immutable source.
"""
import hashlib,re
from .build_target_free_pilot import digest
from .failure_telemetry import CATEGORIES,SITES,TYPES
from ..learning_outbox import _json
from ..remote_watch import identity
MAX_BYTES=1048576
BASE='confluence-market-pilot/'
FILES={'boot-receipt.json','pilot-receipt.json','failure-receipt.json','aggregate-progress.log','partial-receipt.json'}

def acquisition_plan(snapshot,attempt):
    key=identity(attempt);row=snapshot['state']['attempts'][key]
    if row['identity']!=attempt or row['status'] not in ('COMPLETE','ERROR','CANCELLED') or not row['terminal_observed']:raise ValueError('bound terminal attempt required')
    names=['boot-receipt.json','aggregate-progress.log']
    optional=['partial-receipt.json']
    if row['status']=='COMPLETE':names.append('pilot-receipt.json')
    else:optional.append('failure-receipt.json')
    return {'schema':'confluence_acquisition_plan_v1','identity':attempt,'api_status':row['status'],'required_paths':[BASE+n for n in names],'optional_paths':[BASE+n for n in optional],'max_bytes_per_file':MAX_BYTES,'max_files':4,'max_total_bytes':4*MAX_BYTES,'download_all_allowed':False,'inventory_completeness_inferred':False,'execution_allowed':False,'canonical_brain_written':False}

def bounded_json(raw):
    if type(raw) is not bytes or len(raw)>MAX_BYTES:raise ValueError('bounded aggregate bytes required')
    value=_json(raw)
    if type(value) is not dict:raise ValueError('aggregate object required')
    return value

def review_failure(boot_bytes,failure_bytes,progress_bytes,*,package,plan):
    b=bounded_json(boot_bytes);f=bounded_json(failure_bytes)
    if type(progress_bytes) is not bytes or len(progress_bytes)>MAX_BYTES:raise ValueError('bounded progress')
    if b['status']!='MARKET_PILOT_FAILED_NO_EDGE_CLAIM' or b['source_commit']!=package['source_commit'] or b['bundle_sha256']!=package['bundle_sha256']:raise ValueError('wrong failed attempt binding')
    if b.get('exit_code')==0 and b.get('stop_reason') is None:raise ValueError('conflicting success')
    if hashlib.sha256(failure_bytes).hexdigest()!=b['failure_receipt_sha256']:raise ValueError('failure seal mismatch')
    base={'schema','status','failure_category','plan_sha256','holdout_opened','raw_payload_exported','outcomes_or_edge_claim'}
    diagnostic={'exception_type','exception_site','exception_line'}
    if set(f) not in (base,base|diagnostic):raise ValueError('closed failure receipt')
    if f['schema']!='mnq_confluence_market_failure_v1' or f['status']!='FAILED_NO_COMPLETE_CENSUS' or f['plan_sha256']!=digest(plan) or f['plan_sha256']!=package['plan_sha256']:raise ValueError('wrong failure plan/schema')
    if f['failure_category'] not in CATEGORIES or b['failure_category']!=f['failure_category']:raise ValueError('unknown/conflicting category')
    for k in ('holdout_opened','raw_payload_exported','outcomes_or_edge_claim'):
        if f[k] is not False:raise ValueError('failure scope overclaim')
    for k in ('holdout_opened','outcomes_computed','pnl_computed','raw_exported','source_quality_certified','new_dataset_quality_audit'):
        if b[k] is not False:raise ValueError('boot scope overclaim')
    if diagnostic<=set(f):
        if f['exception_type'] not in TYPES|{'OTHER_EXCEPTION'} or f['exception_site'] not in set(SITES.values())|{'UNCLASSIFIED_SITE'}:raise ValueError('closed exception diagnostic')
        if f['exception_line'] is not None and (type(f['exception_line']) is not int or f['exception_line']<1):raise ValueError('source line integer')
    sessions=[];triads=[];last_date='';last_rows=0;failed=False
    for line in progress_bytes.decode('utf8').splitlines():
        if failed:raise ValueError('progress after terminal failure')
        m=re.fullmatch(r'SESSION_COMPLETE (\d{4}-\d{2}-\d{2}) (\d+) (\d+)',line)
        if m:
            date,ticks,rows=m.group(1),int(m.group(2)),int(m.group(3))
            from datetime import date as Date
            Date.fromisoformat(date)
            if triads or not last_date<date<=plan['target_session'] or date>='2026-10-01' or not 0<ticks<=plan['max_session_ticks'] or not last_rows<=rows<=plan['max_capture_records']:raise ValueError('progress scope/order/budget')
            sessions.append({'session':date,'ticks':ticks,'cumulative_capture_rows':rows});last_date=date;last_rows=rows;continue
        m=re.fullmatch(r'GEOMETRY_TRIAD_COMPLETE (\d+)',line)
        if m:
            i=int(m.group(1))
            if last_date!=plan['target_session'] or i!=len(triads) or i>=32:raise ValueError('triad progress order')
            triads.append(i);continue
        if line=='PILOT_FAILED '+f['failure_category']:failed=True;continue
        raise ValueError('non-aggregate progress rejected')
    if sum(s['ticks'] for s in sessions)>plan['max_total_ticks']:raise ValueError('total tick budget')
    return {'schema':'confluence_failed_closeout_review_v1','status':'FAILURE_PRESERVED_NOT_COMPLETE_CENSUS','failure_category':f['failure_category'],'specific_root_cause_known':False,'source_commit':package['source_commit'],'bundle_sha256':package['bundle_sha256'],'plan_sha256':digest(plan),'artifact_sha256':{'boot':hashlib.sha256(boot_bytes).hexdigest(),'failure':hashlib.sha256(failure_bytes).hexdigest(),'progress':hashlib.sha256(progress_bytes).hexdigest()},'sessions_reported_complete':len(sessions),'last_completed_session':last_date or None,'geometry_triads_reported_complete':triads,'stage_times_available':False,'inventory_complete':False,'remote_custody_authenticated':False,'scientific_results_or_edge_verified':False,'canonical_brain_written':False,'automatic_retry_allowed':False}

def review_partial(boot_bytes,partial_bytes,*,package,plan,roster):
    import math
    from ..post_run import _sha
    b=bounded_json(boot_bytes);p=bounded_json(partial_bytes)
    if b['source_commit']!=package['source_commit'] or b['bundle_sha256']!=package['bundle_sha256'] or hashlib.sha256(partial_bytes).hexdigest()!=b.get('partial_receipt_sha256'):raise ValueError('partial physical/source binding')
    fields={'schema','status','stage','source_pin_sha256','plan_sha256','roster_sha256','target_session','sessions_processed','ticks_processed','target_ticks','capture_rows','stage_seconds','storage_nested_seconds','wall_seconds','config_prefix_counts','geometry_triads_reported_complete','complete_census','outcomes_evaluated','holdout_opened','raw_ticks_or_events_exported','canonical_brain_written','inference_or_edge_claim'}
    if set(p)!=fields or p['schema']!='mnq_confluence_partial_v1' or p['status']!='PARTIAL_NOT_COMPLETE_CENSUS' or p['stage'] not in ('SESSION_DETECTORS_COMPLETE','CAPTURE_INDEX_READY','GEOMETRY_TRIAD_COMPLETE'):raise ValueError('closed partial receipt')
    if (p['source_pin_sha256'],p['plan_sha256'],p['roster_sha256'],p['target_session'])!=(digest(plan['pin']),digest(plan),digest(roster),plan['target_session']):raise ValueError('partial scope binding')
    for k in ('complete_census','outcomes_evaluated','holdout_opened','raw_ticks_or_events_exported','canonical_brain_written','inference_or_edge_claim'):
        if p[k] is not False:raise ValueError('partial overclaim')
    for k in ('sessions_processed','ticks_processed','target_ticks','capture_rows'):
        if type(p[k]) is not int or p[k]<0:raise ValueError('integer census')
    if not p['target_ticks']<=p['ticks_processed']<=plan['max_total_ticks'] or p['capture_rows']>plan['max_capture_records']:raise ValueError('partial budgets')
    for group,allowed in [('stage_seconds',{'reader_seconds','classification_seconds','primitives_seconds','BT2_seconds','AVZP2_seconds','BT2A_seconds','geometry_seconds'}),('storage_nested_seconds',{'capture_encode_hash_seconds','insert_commit_seconds','index_seconds'})]:
        if type(p[group]) is not dict or set(p[group])-allowed:raise ValueError('closed stage timings')
        if any(type(v) not in (int,float) or not math.isfinite(v) or v<0 for v in p[group].values()):raise ValueError('finite timing')
    if type(p['wall_seconds']) not in (int,float) or not math.isfinite(p['wall_seconds']) or p['wall_seconds']<0 or sum(p['stage_seconds'].values())>p['wall_seconds']+1e-6:raise ValueError('wall/stage timing scope')
    rows=p['config_prefix_counts']
    if len(rows)!=96 or len(roster['configs'])!=96:raise ValueError('partial fixed roster')
    total=0
    for row,c in zip(rows,roster['configs']):
        if set(row)!={'config_sha256','all_capture_counts','target_capture_counts','ordered_prefix_capture_sha256'} or row['config_sha256']!=c['config_sha256']:raise ValueError('partial config identity')
        _sha(row['ordered_prefix_capture_sha256']);a=row['all_capture_counts'];t=row['target_capture_counts']
        if type(a) is not dict or type(t) is not dict or set(a)-{'BIRTH','TOUCH','CLASSIFY','REMOVE'} or set(t)-set(a):raise ValueError('closed capture kinds')
        if any(type(v) is not int or v<0 for v in a.values()) or any(type(v) is not int or not 0<=v<=a[k] for k,v in t.items()):raise ValueError('partial count bounds')
        total+=sum(a.values())
    if total!=p['capture_rows']:raise ValueError('partial capture crossfoot')
    tris=p['geometry_triads_reported_complete']
    if type(tris) is not list or any(type(i) is not int for i in tris) or len(tris)>32 or tris!=list(range(len(tris))):raise ValueError('partial triad prefix')
    return {'schema':'confluence_partial_review_v1','status':'PASS_AGGREGATE_PREFIX_NOT_COMPLETE_CENSUS','partial_bytes_sha256':hashlib.sha256(partial_bytes).hexdigest(),'prefix_configs_checked':96,'capture_rows':p['capture_rows'],'geometry_triads_reported_complete':tris,'timing_scope':'STORAGE_NESTED_DO_NOT_ADD_TO_STAGE_TOTAL','complete_census':False,'scientific_edge_verified':False,'canonical_brain_written':False}
