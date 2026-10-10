"""Bounded structural audit of pinned aggregates. Never a tick sanitizer/certificate.

Reads approved preholdout aggregates for QA only, no returns, fills, P&L or trials.
Row-group identity/time metadata must pass before any row is deserialized. Footer
I/O is not byte-level isolation; immutable source and truthful audited stats required.
"""
from __future__ import annotations
from collections import Counter
from datetime import date
import hashlib
import json
from pathlib import Path

class AggregateAuditError(ValueError):
    pass


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()


def audit_aggregate_store(*, store, resolver, expected_manifest_sha256,
                          expected_resolver_sha256, batch_size=65536):
    """Return structural checks and private session totals. NEVER certify research.

    Externally pinned manifest and resolver hashes are mandatory. Report contains no
    price values. Per-session volume/trade totals are returned separately for local
    reconciliation, not automatically published or used for source selection.
    """
    import numpy as np
    import pandas as pd
    import pyarrow as pa
    import pyarrow.parquet as pq
    if type(batch_size) is not int or not 1 <= batch_size <= 262144:
        raise AggregateAuditError('invalid bounded batch size')
    root=Path(store);res_path=Path(resolver)
    for p,pin in [(root/'manifest.json',expected_manifest_sha256),(res_path,expected_resolver_sha256)]:
        if not isinstance(pin,str) or len(pin)!=64 or digest(p)!=pin:
            raise AggregateAuditError('externally pinned metadata hash mismatch')
    manifest=json.loads((root/'manifest.json').read_text());cat=json.loads(res_path.read_text())
    listed={x['path']:x for x in manifest['files']}
    if 'plan.json' not in listed or digest(root/'plan.json')!=listed['plan.json']['sha256']:
        raise AggregateAuditError('plan hash mismatch')
    plan=json.loads((root/'plan.json').read_text())
    if cat.get('holdout_first_trade_date')!='2026-10-01' or plan['spec']['holdout_first_trade_date']!='2026-10-01':
        raise AggregateAuditError('unreconciled holdout policy')
    rows=[x for shard in plan['shards'] for x in shard['sessions']]
    if any(x['date'] >= '2026-10-01' for x in rows):
        raise AggregateAuditError('reserved session in plan')
    wanted={}
    for row in rows:
        key=(row['instrument'],row['date'])
        if key in wanted:raise AggregateAuditError('duplicate planned session')
        matches=[r for r in cat['instruments'][row['instrument']]['sessions'] if r['date']==row['date']]
        if len(matches)!=1 or matches[0].get('approved') is not True:
            raise AggregateAuditError('unapproved planned session')
        m=matches[0]
        if any(row[k]!=m[k] for k in ('contract','dataset','file')):
            raise AggregateAuditError('planned primary differs from pinned catalog')
        wanted[key]=m
    cutoff=pd.Timestamp('2026-09-30 17:00',tz='America/Chicago').tz_convert('UTC').value
    report={'scope':'aggregate structural QA only; not raw-tick sanitation or independent liquidity review',
            'manifest_sha256':expected_manifest_sha256,'resolver_sha256':expected_resolver_sha256,
            'holdout_first_trade_date':'2026-10-01','selected_sessions':len(wanted),
            'price_outcomes_computed':False,'promotion_allowed':False,
            'research_allowed':False,'liquidity_certified':False,'raw_ticks_audited':False,'files':[]}
    totals={}; all_errors=Counter()
    fields=['open','high','low','close','volume','trades','buy_volume','sell_volume','unknown_volume',
            'signed_volume','bucket_utc_ns','available_utc_ns','first_ts_utc_ns','last_ts_utc_ns']
    for inst in sorted({x['instrument'] for x in rows}):
        expected={d:m for (i,d),m in wanted.items() if i==inst}
        for seconds in (1,30,60):
            name=f'{inst}__{seconds}s.parquet';path=root/name
            if name not in listed or digest(path)!=listed[name]['sha256']:
                raise AggregateAuditError('primary file hash mismatch: '+name)
            if path.stat().st_size != listed[name]['bytes']:
                raise AggregateAuditError('primary file size mismatch')
            pf=pq.ParquetFile(path);schema=pf.schema_arrow
            required=['session_date','contract','bid_ticks','ask_ticks']+fields
            if any(n not in schema.names for n in required):raise AggregateAuditError('missing aggregate columns')
            if any(not pa.types.is_integer(schema.field(n).type) for n in fields):
                raise AggregateAuditError('aggregate integer field type mismatch')
            # ALL groups preflighted before any payload. Reject mixed/unapproved sessions.
            for i in range(pf.num_row_groups):
                rg=pf.metadata.row_group(i)
                cols={rg.column(j).path_in_schema:rg.column(j) for j in range(rg.num_columns)}
                for c in ('session_date','contract','first_ts_utc_ns','last_ts_utc_ns'):
                    s=cols[c].statistics
                    if s is None or not s.has_min_max or not s.has_null_count or s.null_count!=0:
                        raise AggregateAuditError('unknown/null identity/time statistics')
                a=cols['session_date'].statistics.min;b=cols['session_date'].statistics.max
                if a> b or b >= '2026-10-01' or a < min(expected) or b > max(expected):
                    raise AggregateAuditError('unapproved/reserved row group date range')
                if any(cols[n].statistics.max >= cutoff for n in ('first_ts_utc_ns','last_ts_utc_ns')):
                    raise AggregateAuditError('row group overlaps holdout timestamp')
            errors=Counter();warnings=Counter();local={};last_key=None;count=0
            for batch in pf.iter_batches(batch_size=batch_size,columns=required):
                t=batch.to_pandas();count+=len(t)
                errors['null_required_rows']+=int(t[['session_date','contract']+fields].isna().any(axis=1).sum())
                vals=t[fields].to_numpy()
                errors['nonfinite_required_rows']+=int((~np.isfinite(vals)).any(axis=1).sum())
                errors['negative_volume_rows']+=int((t[['volume','buy_volume','sell_volume','unknown_volume']]<0).any(axis=1).sum())
                errors['nonpositive_trades_rows']+=int((t.trades<=0).sum())
                errors['nonpositive_price_rows']+=int((t[['open','high','low','close']]<=0).any(axis=1).sum())
                errors['invalid_ohlc_rows']+=int(((t.low>t.high)|(t.open<t.low)|(t.open>t.high)|(t.close<t.low)|(t.close>t.high)).sum())
                errors['volume_decomposition_rows']+=int((t.volume != t.buy_volume+t.sell_volume+t.unknown_volume).sum())
                errors['signed_volume_rows']+=int((t.signed_volume != t.buy_volume-t.sell_volume).sum())
                ns=seconds*10**9
                errors['invalid_bar_time_rows']+=int(((t.bucket_utc_ns%ns!=0)|(t.available_utc_ns != t.bucket_utc_ns+ns)|
                     (t.first_ts_utc_ns<t.bucket_utc_ns)|(t.last_ts_utc_ns>=t.available_utc_ns)|(t.last_ts_utc_ns<t.first_ts_utc_ns)).sum())
                errors['unplanned_contract_rows']+=int((t.contract != t.session_date.map({d:r['contract'] for d,r in expected.items()})).sum())
                for time in ('first_ts_utc_ns','last_ts_utc_ns'):
                    ct=pd.to_datetime(t[time],unit='ns',utc=True).dt.tz_convert('America/Chicago')
                    session=(ct.dt.normalize().dt.tz_localize(None)+pd.to_timedelta((ct.dt.hour>=17).astype(int),unit='D')).dt.strftime('%Y-%m-%d')
                    errors['session_timestamp_mismatch_rows']+=int((session != t.session_date).sum())
                keys=list(zip(t.session_date,t.contract,t.bucket_utc_ns))
                errors['duplicate_or_unsorted_keys']+=sum(b<=a for a,b in zip(keys,keys[1:]))
                if keys:
                    if last_key is not None and keys[0]<=last_key:errors['duplicate_or_unsorted_keys']+=1
                    last_key=keys[-1]
                q=t[['bid_ticks','ask_ticks']];valid=q.notna().all(axis=1)
                warnings['missing_quote_rows']+=int((~valid).sum())
                errors['nonfinite_quote_rows']+=int(((~np.isfinite(q)) & q.notna()).any(axis=1).sum())
                errors['fractional_quote_rows']+=int(((q%1 != 0)&q.notna()).any(axis=1).sum())
                errors['nonpositive_quote_rows']+=int(((q<=0)&q.notna()).any(axis=1).sum())
                errors['crossed_quote_rows']+=int((valid & (t.bid_ticks>t.ask_ticks)).sum())
                warnings['locked_quote_rows']+=int((valid & (t.bid_ticks==t.ask_ticks)).sum())
                for day,g in t.groupby('session_date'):
                    sums=local.setdefault(day,{n:0 for n in ('trades','volume','buy_volume','sell_volume','unknown_volume','signed_volume')})
                    for n in sums:sums[n]+=int(g[n].sum())
            errors['session_coverage_mismatch']=int(set(local)!=set(expected))
            errors['catalog_totals_mismatch_sessions']=sum(local.get(d,{}).get('trades')!=m['trades'] or local.get(d,{}).get('volume')!=m['volume'] for d,m in expected.items())
            if count!=pf.metadata.num_rows:raise AggregateAuditError('stream count mismatch')
            totals[(inst,seconds)]=local;all_errors.update(errors)
            report['files'].append({'file':name,'rows':count,'sessions':len(local),
                 'sha256':listed[name]['sha256'],'errors':dict(errors),'warnings':dict(warnings),
                 'schema_integer_fields_verified':True,'footer_preflight_passed':True})
    for inst in sorted({i for i,_ in wanted}):
        all_errors['cross_frequency_totals_mismatch']+=sum(totals[(inst,s)]!=totals[(inst,1)] for s in (30,60))
    report['errors']={k:v for k,v in all_errors.items() if v}
    report['status']='FAIL_AGGREGATE_STRUCTURE' if report['errors'] else 'PASS_AGGREGATE_STRUCTURE_ONLY'
    report['research_status']='BLOCKED_UNCERTIFIED_QUALITY_AND_CAUSAL_LIQUIDITY'
    return report,totals
