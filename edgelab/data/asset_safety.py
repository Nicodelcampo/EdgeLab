"""Read-only asset safety primitives. Never certify missing data by default."""
from __future__ import annotations
import math

class AssetSafetyError(ValueError):pass

def safe_group_ids(groups, cutoff_ns):
    """Select whole groups before STRICT cutoff; mixed/unknown groups stay sealed."""
    if isinstance(cutoff_ns,bool) or not isinstance(cutoff_ns,int) or cutoff_ns<=0:
        raise AssetSafetyError('positive integer UTC-ns cutoff required')
    ids=[];excluded=[]
    for i,g in enumerate(groups):
        lo,hi=g.get('min_ts'),g.get('max_ts')
        if type(lo)!=int or type(hi)!=int or lo<=0 or hi<lo or g.get('null_count')!=0:
            excluded.append({'group':i,'reason':'UNKNOWN_OR_INVALID_TIMESTAMP_STATS'})
        elif hi>=cutoff_ns:
            excluded.append({'group':i,'reason':'RESERVED_OR_MIXED_GROUP'})
        else:ids.append(i)
    return ids,excluded

def audited_volume_rows(sessions):
    """Never turn a missing day into zero; preserve observed zero explicitly."""
    rows=[];seen=set()
    for s in sessions:
        for k in ('root','contract','trade_date','volume','observed','complete_session','audit_status'):
            if k not in s:raise AssetSafetyError('missing session evidence: '+k)
        key=(s['root'],s['contract'],s['trade_date'])
        if key in seen:raise AssetSafetyError('duplicate session identity')
        seen.add(key)
        v=s['volume']
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<0:
            raise AssetSafetyError('invalid traded volume')
        if s['observed'] is not True:raise AssetSafetyError('NOT_OBSERVED is not zero activity')
        if not isinstance(s['complete_session'],bool):raise AssetSafetyError('unknown completeness')
        if s['complete_session'] and s['audit_status']!='COMPLETE_VERIFIED':
            raise AssetSafetyError('unproved complete_session=True')
        rows.append({k:s[k] for k in ('root','contract','trade_date','volume','complete_session')})
    return rows

def validate_mnq_tick_batch(columns, *,expected_contract,previous_key=None):
    """No silent drop/rounding/repair or timestamp-only deduplication.
    UTC/DST, calendar and quote semantics need independent certification.
    """
    required=('ts_utc_ns','sequence','price_ticks','bid_ticks','ask_ticks','volume')
    if any(k not in columns for k in required):raise AssetSafetyError('incomplete canonical tick schema')
    if not expected_contract.startswith('MNQ_'):raise AssetSafetyError('micro/standard identity mismatch')
    n=len(columns['ts_utc_ns'])
    if any(len(v)!=n for v in columns.values()):raise AssetSafetyError('column length mismatch')
    prior=previous_key
    for i in range(n):
        ts,seq,px,bid,ask,vol=(columns[k][i] for k in required)
        if any(isinstance(v,bool) or not isinstance(v,int) for v in (ts,seq,px,bid,ask,vol)):
            raise AssetSafetyError('null, non-integer or coerced tick value')
        if ts<=0 or seq<0 or min(px,bid,ask)<=0 or vol<0 or bid>ask:
            raise AssetSafetyError('invalid MNQ tick/quote/volume geometry')
        key=(ts,seq)
        if prior is not None and key<=prior:
            raise AssetSafetyError('backward/duplicate event identity')
        prior=key
        if 'instrument' in columns and columns['instrument'][i]!='MNQ':
            raise AssetSafetyError('standard/micro mixture')
        if 'contract' in columns and columns['contract'][i] not in (expected_contract,expected_contract.split('_')[1]):
            raise AssetSafetyError('mixed contract payload')
    return prior

def stream_safe_preholdout(path,*,cutoff_ns,expected_contract):
    """Read only fully pre-cutoff groups. Caller pins SHA and dates beforehand.
    Omitted mixed groups never prove a session complete.
    """
    import pyarrow.parquet as pq
    pf=pq.ParquetFile(path)
    idx=pf.schema_arrow.get_field_index('ts_utc_ns')
    if idx<0:raise AssetSafetyError('missing timestamp schema')
    groups=[]
    for i in range(pf.metadata.num_row_groups):
        st=pf.metadata.row_group(i).column(idx).statistics
        groups.append({'min_ts':int(st.min),'max_ts':int(st.max),'null_count':st.null_count}
            if st and st.has_min_max else {})
    selected,excluded=safe_group_ids(groups,cutoff_ns)
    if not selected:raise AssetSafetyError('no fully permitted row groups')
    prior=None
    for batch in pf.iter_batches(row_groups=selected,batch_size=100_000):
        d=batch.to_pydict()
        if any(t>=cutoff_ns for t in d['ts_utc_ns']):raise AssetSafetyError('metadata/payload boundary mismatch')
        prior=validate_mnq_tick_batch(d,expected_contract=expected_contract,previous_key=prior)
        yield batch,{'excluded_groups':excluded,'coverage':'PARTIAL_UNTIL_SESSION_AUDITED'}
