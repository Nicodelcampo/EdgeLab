"""Bounded independent Python reference on real episodes, no optimized passage.
Selection for SOFTWARE validation only: short resolved tapes, status-stratified
across five cells. Does not estimate performance or select strategy thresholds.
"""
import importlib.util,json,hashlib
from pathlib import Path
import numpy as np,pandas as pd,pyarrow.parquet as pq
P=Path('/data/analysis/avzvol-pilot');file='/data/raw/avzvol-ticks/MNQ_12-26_ticks_ext.parquet';s=importlib.util.spec_from_file_location('ref',P/'reference_partial_return.py');ref=importlib.util.module_from_spec(s);s.loader.exec_module(ref)
t=pd.read_csv(P/'episode-results.csv',dtype={n:'Int64' for n in ['trigger_ns','outcome_ns','trigger_source_sequence','outcome_source_sequence','anchor_source_sequence','session_last_source_sequence']});checks=[]
# Deterministic seed to avoid cherry-picking market validation cases by win rate.
c=t[t.gap_policy.eq('no_gap_censor')&t.signal&t.status.isin(['TARGET_FIRST','OPPOSITE_FIRST'])].copy();c=c[(c.outcome_source_sequence-c.anchor_source_sequence).between(1,15000)]
for (cell,status),g in c.groupby(['cell','status']):
 for _,r in g.sample(n=min(3,len(g)),random_state=28103).iterrows():
  a=int(r.anchor_source_sequence);z=int(r.outcome_source_sequence);table=pq.read_table(file,columns=['ts_utc_ns','price_ticks','sequence'],filters=[('sequence','>=',a),('sequence','<=',z)],use_threads=False);ns,px,seq=[table.column(n).to_numpy() for n in table.column_names]
  assert seq[0]==a and seq[-1]==z and np.all(np.diff(seq)==1);assert len(px)==z-a+1
  b0=int(r.bar);tape=[ref.Trade(int(seq[i]),int(ns[i]),b0+(i+24)//25,int(px[i]),r.session) for i in range(len(px))]
  expected=ref.evaluate(tape,ref.Zone(r.zone,int(r.low),int(r.high),a),ref.Rule(int(r.min_distance_ticks),float(r.retracement_fraction),'touch',2000))
  assert expected['status']==r.status and expected['trigger_seq']==int(r.trigger_source_sequence);assert expected['trigger_ns']==int(r.trigger_ns);assert expected['outcome_seq']==z and expected['outcome_ns']==int(r.outcome_ns);assert expected['frozen_target']==int(r.target_ticks) and expected['frozen_opposite']==int(r.opposite_ticks)
  checks.append(dict(cell=cell,status=status,rows=len(px),trigger_and_outcome_sequences_match=True,timestamps_exact_integer_match=True,symmetric_barriers_match=True))
assert len(checks)>=20
# Independent summary recomputation from rows, not trusting precomputed rates.
raw=list(__import__('csv').DictReader((P/'episode-results.csv').open()));summary=list(__import__('csv').DictReader((P/'rule-summary.csv').open()));lookup={}
for r in raw:
 k=(r['cell'],r['min_distance_ticks'],r['retracement_fraction'],r['gap_policy']);d=lookup.setdefault(k,dict(formations=0,signals=0,target_first=0,opposite_first=0));d['formations']+=1;d['signals']+=r['signal']=='True';d['target_first']+=r['status']=='TARGET_FIRST';d['opposite_first']+=r['status']=='OPPOSITE_FIRST'
for r in summary:
 d=lookup[(r['cell'],r['min_distance_ticks'],r['retracement_fraction'],r['gap_policy'])]
 for k in d:assert d[k]==int(r[k])
 assert int(r['unresolved'])==d['signals']-d['target_first']-d['opposite_first']
 if d['target_first']+d['opposite_first']:assert abs(float(r['resolved_target_fraction'])-d['target_first']/(d['target_first']+d['opposite_first']))<1e-14
out=dict(status='PASS_BOUNDED_MARKET_REFERENCE',market_tapes_checked=len(checks),reference_algorithm='Python reference evaluate; exact raw source sequence interval; no numba passage used',software_validation_sample_not_performance_population=True,market_checks=checks,summary_groups_independently_recounted=len(summary),episode_rows_independently_recounted=len(raw),scope_leakage_events=sum((r['contract'],r['session']) not in {(a['contract'],a['session_label']) for a in __import__('csv').DictReader(open('/data/analysis/avzvol-selected-risk/selected-event-sessions.csv'))} for r in raw))
assert out['scope_leakage_events']==0;(P/'market-reference-verification.json').write_text(json.dumps(out,indent=2));print('Market reference',len(checks),'tapes;180summary groups independently recounted;0scope leakage')
