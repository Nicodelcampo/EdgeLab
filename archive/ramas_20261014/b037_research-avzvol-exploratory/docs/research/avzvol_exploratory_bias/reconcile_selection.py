"""Reconcile full-file QA with catalog.v15 selected date+contract identities.
No new price outcomes. Warmup membership based on nominal Chicago17 session
intervals: candidate overlap, NOT exact tick membership at window boundaries.
"""
import csv,hashlib,json
from pathlib import Path
import pandas as pd
R=Path('/data/raw/avzvol-selected-risk');O=Path('/data/analysis/avzvol-selected-risk');resolver_path=Path('/data/raw/es-roll-repair/catalog/RESOLVER.json')
meta=json.loads((R/'metadata-review.json').read_text());auth=json.loads((R/'pr111-authorization.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(resolver_path)==next(p['measured_sha256'] for p in meta['document_input_pins'] if p['role']=='resolver')
csv_bytes=(R/'session-risk-summary.csv').read_bytes();local_csv_pin=auth['evidence_sha256']['session-risk-summary.csv']
assert b'\r\n' not in csv_bytes and hashlib.sha256(csv_bytes.replace(b'\n',b'\r\n')).hexdigest()==local_csv_pin
# Published derived text normalized CRLF->LF; NOT a raw-tick change. Record both pins.
resolver=json.loads(resolver_path.read_text());t=pd.read_csv(R/'session-risk-summary.csv');assert not t.duplicated(['contract','session_label']).any();t['day']=pd.to_datetime(t.session_label,format='%Y-%m-%d');a=pd.DataFrame(resolver['instruments']['MNQ']['sessions']);a=a[a.approved.eq(True)].copy();assert len(a)==261 and not a.duplicated(['contract','date']).any()
u=t.merge(a[['contract','date','trades','dataset','file']],left_on=['contract','session_label'],right_on=['contract','date'],how='left',validate='one_to_one');assert len(u)==len(t)==560
selected=u.trades.notna();assert selected.sum()==261;assert u.loc[selected,'rows'].eq(u.loc[selected,'trades']).all()
lookup={r['contract']:r for r in meta['contracts']};cohorts=[];boundary=[]
for r in u[selected].to_dict('records'):
 assert r['dataset']==lookup[r['contract']]['candidate_dataset_ref'].split('/')[-1]
 assert r['file']=='MNQ/'+r['contract']+'_ticks_ext.parquet'
 assert pd.Timestamp(r['session_label'])<pd.Timestamp('2026-10-01')
for contract,g in u[selected].groupby('contract'):
 assert len(g)==lookup[contract]['approved_session_count']
for r in u.to_dict('records'):
 info=lookup[r['contract']];d=pd.Timestamp(r['session_label']);s=(d-pd.Timedelta(days=1)+pd.Timedelta(hours=17)).tz_localize('America/Chicago').tz_convert('UTC').value;e=(d+pd.Timedelta(hours=17)).tz_localize('America/Chicago').tz_convert('UTC').value
 lo=info['legacy_read_window_start_utc_ns'];first=info['first_approved_midnight_utc_ns'];hi=info['legacy_read_window_end_utc_ns_exclusive']
 uncertain=any(s<x<e for x in (lo,first,hi));boundary.append(uncertain)
 if pd.notna(r['trades']):cohort='SELECTED_EVENT_SESSION'
 elif s<first and e>lo:cohort='NONSELECTED_WARMUP_CANDIDATE'
 elif s<hi and e>first:cohort='NONSELECTED_EVENT_WINDOW_CANDIDATE'
 else:cohort='OUTSIDE_DECLARED_READ_WINDOW'
 cohorts.append(cohort)
u['cohort']=cohorts;u['window_boundary_straddles_nominal_session']=boundary
# Independent path: direct CSV dictionary lookup, no merge/groupby.
bykey={(r['contract'],r['session_label']):r for r in csv.DictReader((R/'session-risk-summary.csv').open())}
for r in a.to_dict('records'):assert int(bykey[(r['contract'],r['date'])]['rows'])==int(r['trades'])
assert sum(int(bykey[(r['contract'],r['date'])]['rows'])<2500 for r in a.to_dict('records'))==0
pairs={(r['contract'],r['date']) for r in a.to_dict('records')};thin_keys={(r['contract'],r['session_label']) for r in csv.DictReader((R/'session-risk-summary.csv').open()) if int(r['rows'])<2500};assert len(thin_keys)==153 and not (pairs & thin_keys)
metrics=[]
for c,g in u.groupby('cohort',sort=False):metrics.append(dict(cohort=c,sessions=len(g),thin_lt2500_sessions=int(g.rows.lt(2500).sum()),source_session_rows=int(g.rows.sum()),max_adjacent_jump_ticks=int(g.max_adjacent_price_jump_ticks.max()),within_session_gaps_gt60s=int(g.gaps_gt_60s.sum()),boundary_straddling_nominal_sessions=int(g.window_boundary_straddles_nominal_session.sum())))
s=u[selected];maxrow=u.loc[u.max_adjacent_price_jump_ticks.idxmax()];known_extra=u.loc[u.max_adjacent_price_jump_ticks.eq(1419),['contract','session_label','cohort','rows']].to_dict('records');assert len(known_extra)==1 and known_extra[0]['cohort']=='NONSELECTED_WARMUP_CANDIDATE'
evidence=dict(scope='RECONCILIATION_OF_PUBLISHED_RAW_QA_WITH_PINNED_CATALOG_SELECTION_NO_NEW_OUTCOMES',input_pins=dict(resolver_sha256=sha(resolver_path),session_risk_summary_sha256=sha(R/'session-risk-summary.csv'),original_local_summary_crlf_sha256=local_csv_pin,derived_csv_transport_note='published LF bytes differ from local CRLF pin; exact CRLF reconstruction verified; original source unchanged',metadata_review_sha256=sha(R/'metadata-review.json'),qa_commit='b9155170cb63e6a8f42976969379eb322f2f78da',metadata_commit='4579f5512b150a440d0bd6ea3115a5032ec8d0f0'),all_sessions=560,selected_sessions=len(s),selected_unique_dates=s.session_label.nunique(),selected_count_discrepancies=0,all_thin_sessions=153,selected_thin_sessions=0,selected_min_rows=int(s.rows.min()),selected_max_jump_ticks=int(s.max_adjacent_price_jump_ticks.max()),extreme_jump_1419_membership=known_extra,cohorts=metrics,selected_sessions_by_contract=s.groupby('contract').size().to_dict(),selected_same_timestamp_adjacent=int(s.equal_timestamp_adjacent.sum()),selected_rows=int(s.rows.sum()),selected_zero_duration_bar_fraction=None,interpretation=['full-file thin activity is not a selected-universe defect','1419tick jump is outside selected event sessions but is a potential warmup exposure','catalog selected dates are distinct; full-file cross-contract overlap cannot be applied to this population','matching totals do not prove intraday completeness or full source certification','catalog selection declared retrospective components; selected-universe analysis descriptive/exploratory, not automatic asof strategy','warmup/read-window cohorts use nominal session overlap; full source-session counts NOT ticks inside those windows','no computed missing-data rate: gaps can reflect inactivity; no10second gap deletion applied'],checks=['all261 identities/direct CSV counts independently matched','all153 thin-session keys disjoint from selected key set','no merge inflation or duplicate keys','all560 source-session categories exhaustive/disjoint'],comparison_plan=[dict(grain='source contract-session',unit='count',finding='zero of153 thin sessions belongs to261 selected sessions',disposition='prose',reason='single corrected scope claim'),dict(grain='nominal warmup interval and source-session',unit='candidate sessions',finding='extreme jump can affect warmup despite not being an outcome session',disposition='table',reason='interval boundary caveat prevents claiming exact tick membership')])
u.drop(columns=['day']).to_csv(O/'session-cohort-reconciliation.csv',index=False);s[['contract','session_label','dataset','file','trades']].to_csv(O/'selected-event-sessions.csv',index=False);(O/'evidence.json').write_text(json.dumps(evidence,indent=2,ensure_ascii=False))
print(json.dumps({k:evidence[k] for k in ['selected_sessions','selected_unique_dates','selected_count_discrepancies','selected_thin_sessions','selected_min_rows','selected_max_jump_ticks','extreme_jump_1419_membership','cohorts']},indent=2))
