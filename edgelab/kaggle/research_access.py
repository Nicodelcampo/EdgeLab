"""Opt-in research access guard. Catalog approval alone is NEVER sufficient.

Legacy v15 retrospective masks are unsupported for causal research. This module
opens only metadata until reviewed campaign evidence validates EVERY materialized
session for the requested instrument. The legacy consumer reads the whole file,
so partial-file authorization must fail rather than read then filter.
"""
from __future__ import annotations
import json
import re
from pathlib import Path
from datetime import date, timedelta
from edgelab.data.research_data_gate import DataEligibilityError, require_research_eligibility
from edgelab.kaggle.aggregate_audit import digest

CAUSAL_SELECTION_POLICY = 'previous_complete_session_causal_eligibility_v1'


def require_research_store(*, store, resolver, instrument, expected_manifest_sha256,
        expected_resolver_sha256, certificate, regime_manifest, liquidity_limits,
        expected_certificate_sha256, expected_regime_sha256, expected_liquidity_limits_sha256):
    """Require externally reviewed/pinned quality, causal masks and D-1 liquidity.

    Returns metadata decisions, never a certificate. Does not authenticate authority.
    The current published v15 resolver cannot pass: its full-sample/current-session
    mask must be reconciled in a new independently reviewed artifact, not relabeled.
    """
    root=Path(store)
    if digest(root/'manifest.json')!=expected_manifest_sha256 or digest(resolver)!=expected_resolver_sha256:
        raise DataEligibilityError('aggregate/canonical metadata pins mismatch')
    m=json.loads((root/'manifest.json').read_text());listed={x['path']:x['sha256'] for x in m['files']}
    if 'plan.json' not in listed or digest(root/'plan.json')!=listed['plan.json']:
        raise DataEligibilityError('aggregate plan mismatch')
    plan=json.loads((root/'plan.json').read_text());catalog=json.loads(Path(resolver).read_text())
    if catalog.get('selection_policy_id')!=CAUSAL_SELECTION_POLICY:
        raise DataEligibilityError('RETROSPECTIVE_OR_UNVERIFIED_SELECTION_MASK: catalog approval is not causal research eligibility')
    if not isinstance(certificate,dict) or certificate.get('aggregate_store_manifest_sha256')!=expected_manifest_sha256:
        raise DataEligibilityError('missing reviewed certificate binding aggregate artifact')
    if certificate.get('aggregate_structural_status')!='PASS':
        raise DataEligibilityError('aggregate structure not independently reviewed')
    rows=[r for s in plan['shards'] for r in s['sessions'] if r['instrument']==instrument]
    if not rows or len({r['date'] for r in rows})!=len(rows):
        raise DataEligibilityError('missing/duplicate materialized session')
    decisions=[]
    for row in sorted(rows,key=lambda r:r['date']):
        day=int(date.fromisoformat(row['date']).strftime('%Y%m%d'))
        decision=require_research_eligibility(certificate=certificate,regime_manifest=regime_manifest,
            root=instrument,trade_date=day,liquidity_limits=liquidity_limits,
            expected_certificate_sha256=expected_certificate_sha256,expected_regime_sha256=expected_regime_sha256,
            expected_liquidity_limits_sha256=expected_liquidity_limits_sha256)
        if decision['contract']!=row['contract']:
            raise DataEligibilityError('aggregate contract differs from causal regime')
        choices=[r for r in catalog['instruments'][instrument]['sessions'] if r['date']==row['date']]
        if len(choices)!=1 or choices[0].get('approved') is not True or any(choices[0].get(k)!=row[k] for k in ('contract','dataset','file')):
            raise DataEligibilityError('aggregate primary selection mismatch')
        if choices[0].get('caveat'):
            session=certificate['sessions'][f"{instrument}|{row['contract']}|{day}"]
            if session.get('source_conflict_resolution')!='PASS':
                raise DataEligibilityError('unresolved source conflict/caveat')
        decisions.append(decision)
    return decisions


def require_requested_coverage(*, certificate, instrument, start, end, materialized_dates):
    """Validate complete daily declarations INSIDE an externally pinned certificate.

    Call only after require_research_store pins the entire certificate. This is a
    consistency guard, NOT calendar verification or authentication. Diagnostics
    from coverage_inventory can NEVER substitute for independently reviewed data.
    Includes every calendar date: no silent missing holiday/weekend/session.
    """
    a, b = date.fromisoformat(start), date.fromisoformat(end)
    if a > b or b >= date(2026, 10, 1):
        raise DataEligibilityError('invalid/reserved coverage window')
    review = certificate.get('coverage_review')
    if not isinstance(review, dict) or review.get('schema') != 'edgelab_reviewed_daily_coverage_v1':
        raise DataEligibilityError('missing independently reviewed daily coverage')
    for field in ('calendar_sha256', 'interval_evidence_sha256'):
        if not isinstance(review.get(field), str) or not re.fullmatch('[0-9a-f]{64}', review[field]):
            raise DataEligibilityError('missing reviewed calendar/interval evidence reference')
    records = review.get('dates')
    if not isinstance(records, list):
        raise DataEligibilityError('coverage dates must be explicit records')
    by_key = {}
    for row in records:
        if not isinstance(row, dict) or not isinstance(row.get('instrument'), str) or not isinstance(row.get('date'), str):
            raise DataEligibilityError('invalid coverage identity')
        try: date.fromisoformat(row['date'])
        except ValueError: raise DataEligibilityError('invalid coverage date') from None
        key = (row['instrument'], row['date'])
        if key in by_key: raise DataEligibilityError('duplicate daily coverage')
        by_key[key] = row
    reviewed = []
    while a <= b:
        d = a.isoformat(); row = by_key.get((instrument, d))
        if row is None: raise DataEligibilityError('undeclared date in requested coverage: ' + d)
        ref = row.get('evidence_sha256')
        if not isinstance(ref, str) or not re.fullmatch('[0-9a-f]{64}', ref):
            raise DataEligibilityError('missing daily coverage evidence reference')
        status = row.get('status')
        if status == 'VERIFIED_SCHEDULED_CLOSED':
            if d in materialized_dates: raise DataEligibilityError('observations conflict with declared closure')
        elif status == 'VERIFIED_OPEN_COMPLETE':
            if d not in materialized_dates: raise DataEligibilityError('expected open session is missing')
            if row.get('interval_review') != 'PASS' or type(row.get('unresolved_intervals')) is not int or row['unresolved_intervals'] != 0:
                raise DataEligibilityError('unresolved observation intervals')
        else:
            raise DataEligibilityError('unverified/excluded coverage cannot be silently removed')
        reviewed.append(d); a += timedelta(days=1)
    return reviewed


def load_research_bars(*, start, end, seconds, **evidence):
    """Guarded consumer. All source-file sessions require authority, not just window.

    No implicit fallback to legacy loader when this fails. Caller-approved dates must
    exclude D2 and every sealed campaign partition. This module cannot authenticate
    that approval; hashes and declarations are external prerequisites, not grants.
    """
    if date.fromisoformat(start)>date.fromisoformat(end):
        raise DataEligibilityError('invalid requested dates')
    require_research_store(**evidence)  # BEFORE price file hashing/deserialization.
    # Whole-file authorization already validated above. Installed-wheel capable.
    import pandas as pd
    root=Path(evidence['store']);manifest=json.loads((root/'manifest.json').read_text())
    listed={x['path']:x['sha256'] for x in manifest['files']}
    instrument=evidence['instrument']
    if seconds not in (1,30,60):raise DataEligibilityError('invalid frequency')
    name=f'{instrument}__{seconds}s.parquet'
    for n in ('results.json','attestation.json'):
        if n not in listed or digest(root/n)!=listed[n]:
            raise DataEligibilityError('reviewed artifact file hash mismatch')
    result=json.loads((root/'results.json').read_text());attest=json.loads((root/'attestation.json').read_text())
    if result.get('status')!='PASS_INTEGRITY_NOT_EDGE' or attest.get('scope')!='infrastructure_only':
        raise DataEligibilityError('artifact was not integrity-only')
    if any(attest.get(k) is not False for k in ('holdout_touched','future_price_path_accessed','first_touch_accessed','pnl_accessed')):
        raise DataEligibilityError('incomplete artifact attestation')
    plan=json.loads((root/'plan.json').read_text())
    if not any(r['instrument']==instrument and r['start']<=start<=end<=r['end'] for r in plan['spec']['requests']):
        raise DataEligibilityError('window outside materialized request')
    expected={(r['date'],r['contract']) for s in plan['shards'] for r in s['sessions'] if r['instrument']==instrument}
    wanted={(d,c) for d,c in expected if start<=d<=end}
    if not wanted:raise DataEligibilityError('no approved session in requested window')
    require_requested_coverage(certificate=evidence['certificate'], instrument=instrument,
        start=start, end=end, materialized_dates={d for d,c in expected})
    # Only now hash/deserialize the price artifact, after full window coverage.
    if name not in listed or digest(root/name)!=listed[name]:
        raise DataEligibilityError('reviewed artifact file hash mismatch')
    table=pd.read_parquet(root/name)
    if set(zip(table.session_date,table.contract))!=expected or table.duplicated(['session_date','contract','bucket_utc_ns']).any():
        raise DataEligibilityError('artifact coverage/uniqueness changed')
    return table[(table.session_date>=start)&(table.session_date<=end)].copy()
