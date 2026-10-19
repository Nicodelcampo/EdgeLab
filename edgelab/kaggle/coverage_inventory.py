"""Diagnostic coverage inventory; absence NEVER proves zero trades or closure.

Full requested date range, including dates omitted by the resolver. Nominal
17:00 Chicago trade-date windows are labels, NOT reviewed trading calendars.
Only timestamp and identity payload columns are projected. No source mutation,
interpolation, price outcome, liquidity approval or research authorization.
"""
from __future__ import annotations
from collections import Counter
from datetime import date, datetime, time, timedelta, timezone
import json
from pathlib import Path
from zoneinfo import ZoneInfo
from edgelab.kaggle.aggregate_audit import AggregateAuditError, digest

HOLDOUT = date(2026, 10, 1)
CT = ZoneInfo('America/Chicago')
MINUTE_NS = 60 * 10**9


def days(start, end):
    a, b = date.fromisoformat(start), date.fromisoformat(end)
    if a > b or b >= HOLDOUT:
        raise AggregateAuditError('invalid/reserved requested window')
    while a <= b:
        yield a.isoformat()
        a += timedelta(days=1)


def nominal_bounds(day):
    """Elapsed-time window for a trade-date LABEL, not expected market minutes."""
    d = date.fromisoformat(day)
    a = datetime.combine(d-timedelta(days=1), time(17), CT)
    b = datetime.combine(d, time(17), CT)
    return tuple(int(x.astimezone(timezone.utc).timestamp()) * 10**9 for x in (a, b))


def absent_runs(mask, start_ns):
    """Half-open intervals with no aggregate observation; activity stays UNKNOWN."""
    runs = []; first = None
    for i, present in enumerate(list(mask) + [True]):
        if not present and first is None:
            first = i
        elif present and first is not None:
            runs.append({'start_utc_ns': start_ns + first*MINUTE_NS,
                         'end_utc_ns': start_ns + i*MINUTE_NS,
                         'classification': 'UNOBSERVED_ACTIVITY_UNKNOWN'})
            first = None
    return runs


def _ranges(info):
    result = {}
    for name in ('ineligible_low_volume', 'leader_sessions_below_25pct_of_instrument_median'):
        for span in info.get(name, {}).get('ranges', []):
            # Catalog v15 encodes YYYY-MM-DD or YYYY-MM-DD..YYYY-MM-DD.
            if not isinstance(span, str):
                raise AggregateAuditError('invalid catalog exclusion range')
            limits = span.split('..')
            if len(limits) == 1: limits *= 2
            if len(limits) != 2:
                raise AggregateAuditError('invalid catalog exclusion range')
            for d in days(*limits):
                result.setdefault(d, []).append(name)
    return result


def build_daily_inventory(*, plan, resolver, catalog):
    """One record per requested date; reconcile materialization before row I/O."""
    if any(x.get('holdout_first_trade_date') != HOLDOUT.isoformat()
           for x in (plan['spec'], resolver, catalog)):
        raise AggregateAuditError('unreconciled holdout policy')
    planned = {}
    for shard in plan['shards']:
        for r in shard['sessions']:
            key = (r['instrument'], r['date'])
            if key in planned or date.fromisoformat(r['date']) >= HOLDOUT:
                raise AggregateAuditError('duplicate/reserved planned session')
            planned[key] = r
    output = []; seen = set()
    for request in plan['spec']['requests']:
        inst = request['instrument']; info = catalog['instruments'][inst]
        selected = {}
        for s in resolver['instruments'][inst]['sessions']:
            if s['date'] in selected:
                raise AggregateAuditError('duplicate resolver session')
            selected[s['date']] = s
        excluded = _ranges(info)
        for d in days(request['start'], request['end']):
            key = (inst, d)
            if key in seen:
                raise AggregateAuditError('overlapping requests')
            seen.add(key); s = selected.get(d); p = planned.get(key)
            reasons = list(excluded.get(d, []))
            if p:
                if not s or s.get('approved') is not True or reasons or any(p[k] != s[k] for k in ('contract','dataset','file')):
                    raise AggregateAuditError('planned primary/approval/exclusion mismatch')
                state = 'MATERIALIZED_NOT_CERTIFIED'
            elif s and s.get('approved') is True:
                state = 'APPROVED_NOT_MATERIALIZED'
            elif s:
                state = 'REJECTED_BY_RESOLVER'; reasons.append(s.get('reason') or 'reason_not_declared')
            elif reasons:
                state = 'EXCLUDED_BY_CATALOG'
            else:
                state = 'NOT_OBSERVED_CALENDAR_UNVERIFIED'
            if d < info['first_date'] or d > info['last_date']:
                reasons.append('outside_catalog_observed_span')
            output.append({'instrument': inst, 'date': d, 'state': state,
                'reasons': reasons, 'weekday': date.fromisoformat(d).weekday(),
                'contract': s.get('contract') if s else None,
                'source_caveat': s.get('caveat') if s else None,
                'calendar_reviewed': False, 'liquidity_certified': False,
                'raw_ticks_audited': False})
    if set(planned) - seen:
        raise AggregateAuditError('planned session outside requested windows')
    return output


def audit_coverage(*, store, resolver, catalog, expected_manifest_sha256,
                   expected_resolver_sha256, expected_catalog_sha256, batch_size=65536):
    """Return public summary and PRIVATE daily/interval diagnostic inventory.

    Pins bind provenance, not approval authority. Immutable source and truthful
    footer stats required. Hashing is byte I/O, not row/price deserialization.
    Zero-observation intervals cannot be classified without raw/calendar evidence.
    """
    import numpy as np
    import pyarrow as pa
    import pyarrow.parquet as pq
    if type(batch_size) is not int or not 1 <= batch_size <= 262144:
        raise AggregateAuditError('invalid bounded batch size')
    root = Path(store)
    for path, pin in ((root/'manifest.json', expected_manifest_sha256),
                      (Path(resolver), expected_resolver_sha256),
                      (Path(catalog), expected_catalog_sha256)):
        if not isinstance(pin, str) or len(pin) != 64 or digest(path) != pin:
            raise AggregateAuditError('pinned metadata hash mismatch')
    manifest = json.loads((root/'manifest.json').read_text())
    entries = manifest['files']; listed = {r['path']: r for r in entries}
    if len(listed) != len(entries) or 'plan.json' not in listed or digest(root/'plan.json') != listed['plan.json']['sha256']:
        raise AggregateAuditError('duplicate manifest entry/plan hash mismatch')
    plan = json.loads((root/'plan.json').read_text())
    inventory = build_daily_inventory(plan=plan, resolver=json.loads(Path(resolver).read_text()),
                                      catalog=json.loads(Path(catalog).read_text()))
    expected = {(r['instrument'], r['date']): r for r in inventory if r['state'] == 'MATERIALIZED_NOT_CERTIFIED'}
    masks = {}; bounds = {}
    for key in expected:
        a, b = nominal_bounds(key[1]); bounds[key] = (a, b)
        masks[key] = np.zeros((b-a)//MINUTE_NS, dtype=bool)
    cutoff = nominal_bounds(HOLDOUT.isoformat())[0]
    files = []; ready = []
    columns = ['session_date', 'contract', 'bucket_utc_ns']
    # ALL files/groups checked before first payload batch.
    for inst in sorted({r['instrument'] for r in inventory}):
        name = f'{inst}__1s.parquet'; path = root/name
        item = listed.get(name)
        if not item or path.stat().st_size != item['bytes'] or digest(path) != item['sha256']:
            raise AggregateAuditError('pinned primary file mismatch')
        pf = pq.ParquetFile(path)
        for n in columns + ['first_ts_utc_ns', 'last_ts_utc_ns']:
            if n not in pf.schema_arrow.names:
                raise AggregateAuditError('missing identity/time column')
        if not pa.types.is_integer(pf.schema_arrow.field('bucket_utc_ns').type):
            raise AggregateAuditError('noninteger timestamp')
        permitted = [d for i, d in expected if i == inst]
        if not permitted:
            raise AggregateAuditError('instrument has no materialized sessions')
        for j in range(pf.num_row_groups):
            rg = pf.metadata.row_group(j)
            cols = {rg.column(k).path_in_schema: rg.column(k) for k in range(rg.num_columns)}
            for n in columns + ['first_ts_utc_ns', 'last_ts_utc_ns']:
                st = cols[n].statistics
                if st is None or not st.has_min_max or not st.has_null_count or st.null_count:
                    raise AggregateAuditError('unverified identity/time footer')
            sd = cols['session_date'].statistics
            if not min(permitted) <= sd.min <= sd.max <= max(permitted):
                raise AggregateAuditError('unapproved/reserved footer dates')
            if any(cols[n].statistics.max >= cutoff for n in ('bucket_utc_ns','first_ts_utc_ns','last_ts_utc_ns')):
                raise AggregateAuditError('footer overlaps holdout')
        ready.append((inst, name, pf, item['sha256']))
    for inst, name, pf, sha in ready:
        count = 0; last = None; seen_sessions = set()
        for batch in pf.iter_batches(batch_size=batch_size, columns=columns):
            t = batch.to_pandas(); count += len(t)
            if t.isna().any().any():
                raise AggregateAuditError('null identity/time row')
            for (d, contract), g in t.groupby(['session_date','contract'], sort=False):
                key = (inst, d)
                if key not in expected or contract != expected[key]['contract']:
                    raise AggregateAuditError('unplanned row identity')
                seen_sessions.add(key); a, b = bounds[key]; ns = g.bucket_utc_ns.to_numpy()
                if ((ns < a) | (ns >= b) | (ns >= cutoff) | (ns % 10**9 != 0)).any():
                    raise AggregateAuditError('invalid row time/session')
                if (np.diff(ns) <= 0).any():
                    raise AggregateAuditError('duplicate/nonmonotonic timestamp')
                masks[key][np.unique((ns-a)//MINUTE_NS)] = True
            # Enforce ordering across groups and batches, not just within each date.
            keys = list(zip(t.session_date, t.contract, t.bucket_utc_ns))
            if any(y <= x for x, y in zip(keys, keys[1:])) or (keys and last is not None and keys[0] <= last):
                raise AggregateAuditError('duplicate/unsorted identity keys')
            if keys: last = keys[-1]
        if seen_sessions != {k for k in expected if k[0] == inst}:
            raise AggregateAuditError('materialized session absent from file')
        files.append({'file': name, 'sha256': sha, 'identity_timestamp_rows_read': count,
                      'payload_columns': columns, 'price_payload_columns_read': 0})
    for r in inventory:
        key = (r['instrument'], r['date'])
        if key in masks:
            mask = masks[key]; r['nominal_label_minutes'] = len(mask)
            r['minutes_with_observations'] = int(mask.sum())
            r['minutes_without_observations'] = int((~mask).sum())
            r['unobserved_intervals'] = absent_runs(mask, bounds[key][0])
            # Clock-band diagnostic ONLY, not a verified maintenance classification.
            import pandas as pd
            clock = pd.to_datetime(bounds[key][0]+np.arange(len(mask))*MINUTE_NS,unit='ns',utc=True).tz_convert('America/Chicago')
            r['observed_minutes_in_16_to_17_chicago_clock_band'] = int(mask[clock.hour == 16].sum())
        else:
            r['minutes_with_observations'] = None
            r['minutes_without_observations'] = None
            r['unobserved_intervals'] = None
    summary = {'schema': 'edgelab_coverage_diagnostic_v1',
        'status': 'BLOCKED_UNREVIEWED_CALENDAR_RAW_AND_LIQUIDITY',
        'research_allowed': False, 'promotion_allowed': False,
        'calendar_reviewed': False, 'raw_ticks_audited': False, 'liquidity_certified': False,
        'manifest_sha256': expected_manifest_sha256, 'resolver_sha256': expected_resolver_sha256,
        'catalog_sha256': expected_catalog_sha256, 'holdout_first_trade_date': HOLDOUT.isoformat(),
        'requests': plan['spec']['requests'], 'files': files, 'instruments': {},
        'interpretation': 'Nominal 17:00 Chicago trade-date label windows are NOT expected trading calendars; absent intervals remain UNKNOWN, including possible maintenance/holidays. No zero filling.'}
    for inst in sorted({r['instrument'] for r in inventory}):
        rows = [r for r in inventory if r['instrument'] == inst]
        observed = [r for r in rows if r['state'] == 'MATERIALIZED_NOT_CERTIFIED']
        unknown = [r for r in rows if r['state'] == 'NOT_OBSERVED_CALENDAR_UNVERIFIED']
        summary['instruments'][inst] = {'requested_dates': len(rows), 'states': dict(Counter(r['state'] for r in rows)),
            'unobserved_calendar_unverified_weekdays': sum(r['weekday'] < 5 for r in unknown),
            'outside_catalog_span_dates': sum('outside_catalog_observed_span' in r['reasons'] for r in rows),
            'materialized_source_caveat_sessions': sum(bool(r['source_caveat']) for r in observed),
            'observed_minutes_in_16_to_17_chicago_clock_band': sum(r['observed_minutes_in_16_to_17_chicago_clock_band'] for r in observed),
            'sessions_with_observations_in_16_to_17_chicago_clock_band': sum(r['observed_minutes_in_16_to_17_chicago_clock_band'] > 0 for r in observed),
            'nominal_label_minutes': sum(r['nominal_label_minutes'] for r in observed),
            'minutes_with_observations': sum(r['minutes_with_observations'] for r in observed),
            'minutes_without_observations_unknown_activity': sum(r['minutes_without_observations'] for r in observed),
            'unobserved_intervals': sum(len(r['unobserved_intervals']) for r in observed),
            'longest_unobserved_interval_minutes': max(((s['end_utc_ns']-s['start_utc_ns'])//MINUTE_NS for r in observed for s in r['unobserved_intervals']), default=0),
            'first_materialized_date': min(r['date'] for r in observed), 'last_materialized_date': max(r['date'] for r in observed)}
    return summary, inventory
