"""Pinned exploratory source footer preflight, not a market reader or certificate.

Hash physical bytes; inspect metadata only. No Parquet payload deserialization,
source sanitation, calendar certification, session selection or execution authority.
Real sources may be passed ONLY inside Kaggle under an approved exploratory scope.
"""
from __future__ import annotations
import hashlib
import math
from pathlib import Path
import stat
from .build_target_free_pilot import digest

COLUMNS=('ts_utc_ns','price_ticks','volume','bid_ticks','ask_ticks','sequence')
# Trade date 2026-10-01 begins 2026-09-30 17:00 America/Chicago (22:00 UTC).
HOLDOUT_OPEN_NS=1790805600000000000


def validate_pin(pin):
    if not isinstance(pin,dict) or set(pin)!={'contract','file','dataset','version','sha256','bytes','rows','max_ns'}:raise ValueError('exact source pin contract required')
    if not isinstance(pin['sha256'],str) or len(pin['sha256'])!=64 or any(c not in '0123456789abcdef' for c in pin['sha256']):raise ValueError('source SHA256 pin')
    if any(type(pin[k]) is not int or pin[k]<=0 for k in ('version','bytes','rows','max_ns')):raise ValueError('positive source measurements required')
    if pin['bytes']>2*1024**3 or pin['max_ns']>=HOLDOUT_OPEN_NS:raise ValueError('source outside bounded preholdout scope')
    for k in ('file','contract','dataset'):
        if not isinstance(pin[k],str) or not pin[k] or len(pin[k])>256:raise ValueError('bounded source identity')
    if '/' in pin['file'] or '\\' in pin['file'] or pin['file'] in ('.','..'):raise ValueError('pinned basename only')
    return digest(pin)


def inspect_footer(path,pin):
    """No payload read; truthful footer and old source-risk review remain external."""
    pin_sha=validate_pin(pin);file=Path(path)
    if file.name!=pin['file'] or not stat.S_ISREG(file.stat().st_mode):raise ValueError('pinned regular source file required')
    import pyarrow.parquet as pq
    with file.open('rb') as handle:
        handle.seek(0,2)
        if handle.tell()!=pin['bytes']:raise ValueError('source size mismatch')
        handle.seek(0);h=hashlib.sha256()
        for chunk in iter(lambda:handle.read(1024*1024),b''):h.update(chunk)
        if h.hexdigest()!=pin['sha256']:raise ValueError('source bytes mismatch')
        handle.seek(0);pf=pq.ParquetFile(handle);md=pf.metadata;schema=pf.schema_arrow
        if md.num_rows!=pin['rows'] or md.num_row_groups<1:raise ValueError('source rows mismatch')
        present=set(schema.names);missing=sorted(set(COLUMNS)-present);issues=[];mins=[];maxs=[];seq_ranges=[];row_counts=[];unknown_stats=0
        kinds={f.name:str(f.type) for f in schema}
        for name in COLUMNS:
            if name not in present:continue
            if name=='volume':
                if kinds[name] not in ('float','double','int64','int32','uint64','uint32'):issues.append('VOLUME_TYPE_UNSUPPORTED')
            elif kinds[name] not in ('int64','int32','uint64','uint32'):issues.append(name.upper()+'_NOT_INTEGER')
        for i in range(md.num_row_groups):
            group=md.row_group(i);row_counts.append(group.num_rows);cols={group.column(j).path_in_schema:group.column(j) for j in range(group.num_columns)}
            for name in COLUMNS:
                if name not in cols:continue
                stats=cols[name].statistics
                if stats is None or not stats.has_null_count:unknown_stats+=1
                elif stats.null_count:issues.append(name.upper()+'_DECLARED_NULLS')
            for name,collection in [('ts_utc_ns',None),('sequence',seq_ranges)]:
                if name not in cols:continue
                stats=cols[name].statistics
                if stats is None or not stats.has_min_max:unknown_stats+=1;continue
                a,z=int(stats.min),int(stats.max)
                if a>z:issues.append(name.upper()+'_REVERSED_RANGE')
                if name=='ts_utc_ns':mins.append(a);maxs.append(z)
                else:collection.append((a,z))
        if missing:issues.append('REQUIRED_COLUMNS_MISSING')
        if len(mins)!=md.num_row_groups:issues.append('TIME_COVERAGE_STATS_UNKNOWN')
        if maxs and (max(maxs)!=pin['max_ns'] or max(maxs)>=HOLDOUT_OPEN_NS):issues.append('TIME_PIN_OR_HOLDOUT_MISMATCH')
        if mins and any(mins[i]<maxs[i-1] for i in range(1,len(mins))):issues.append('GROUP_TIME_RANGES_OVERLAP_NONMONOTONICALLY')
        if len(seq_ranges)!=md.num_row_groups:issues.append('SEQUENCE_STATS_UNKNOWN')
        elif any(seq_ranges[i][0]<=seq_ranges[i-1][1] for i in range(1,len(seq_ranges))):issues.append('GROUP_SEQUENCE_RANGES_NOT_STRICT')
        if unknown_stats:issues.append('FOOTER_STATS_INCOMPLETE')
        out={'schema':'mnq_confluence_source_footer_receipt_v1','status':'PASS_PINNED_FOOTER_ONLY_NOT_MARKET_APPROVAL' if not issues else 'BLOCKED_FOOTER_REQUIREMENTS','pin':pin,'pin_sha256':pin_sha,'physical_bytes_sha256':h.hexdigest(),'physical_bytes_hashed':True,'price_payload_deserialized':False,'market_trials_executed':0,'holdout_opened':False,'pnl_computed':False,'execution_allowed':False,'source_quality_certified':False,'columns':[{'name':f.name,'type':str(f.type),'nullable':f.nullable} for f in schema],'required_columns_missing':missing,'row_groups':md.num_row_groups,'rows':md.num_rows,'row_group_rows_min':min(row_counts),'row_group_rows_max':max(row_counts),'time_min_ns':min(mins) if mins else None,'time_max_ns':max(maxs) if maxs else None,'footer_stats_unknown_fields':unknown_stats,'issues':sorted(set(issues)),'quote_validity':'NOT_ESTABLISHED_BY_FOOTER','calendar_liquidity_and_session_authority':'NOT_ESTABLISHED_BY_FOOTER'}
        out['receipt_sha256']=digest(out);return out
