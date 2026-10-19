"""Bounded canonical_tick_v1 structural QA; NOT sanitation/completeness approval.

Local sequences and source rows do not prove upstream exchange continuity.
Repeated timestamps are legitimate; never deduplicate by timestamp/content.
Publisher checksum reconciliation is provenance, not independent authority.
"""
from __future__ import annotations
from collections import Counter
from pathlib import Path
from edgelab.kaggle.aggregate_audit import AggregateAuditError, digest


def audit_canonical_tick_file(*, path, expected_sha256, expected_bytes, expected_rows,
                              instrument, contract, batch_size=65536, include_clock_diagnostics=False):
    import numpy as np
    import pandas as pd
    import pyarrow as pa
    import pyarrow.parquet as pq
    if type(batch_size) is not int or not 1 <= batch_size <= 262144:
        raise AggregateAuditError('invalid bounded batch size')
    path = Path(path)
    if not isinstance(expected_sha256,str) or len(expected_sha256)!=64 or path.stat().st_size!=expected_bytes or digest(path)!=expected_sha256:
        raise AggregateAuditError('pinned raw file mismatch')
    pf = pq.ParquetFile(path)
    ints = ['ts_utc_ns','ts_local_ns','sequence','price_ticks','bid_ticks','ask_ticks','volume','source_row']
    text = ['aggressor','tick_type','instrument','contract','source_file']
    required = ints+text
    for n in required:
        if n not in pf.schema_arrow.names: raise AggregateAuditError('missing canonical tick column')
    if any(not pa.types.is_integer(pf.schema_arrow.field(n).type) for n in ints):
        raise AggregateAuditError('noninteger canonical tick field')
    if pf.metadata.num_rows != expected_rows: raise AggregateAuditError('raw footer row count mismatch')
    cutoff = pd.Timestamp('2026-09-30 17:00',tz='America/Chicago').tz_convert('UTC').value
    # Full footer preflight before any payload. Contract names are source literals.
    source_max = 0
    for j in range(pf.num_row_groups):
        rg=pf.metadata.row_group(j);cols={rg.column(k).path_in_schema:rg.column(k) for k in range(rg.num_columns)}
        for n in required:
            st=cols[n].statistics
            if st is None or not st.has_min_max or not st.has_null_count or st.null_count:
                raise AggregateAuditError('unknown/null canonical footer')
        if cols['ts_utc_ns'].statistics.max >= cutoff:
            raise AggregateAuditError('raw group overlaps holdout')
        if any(cols[n].statistics.min != wanted or cols[n].statistics.max != wanted
               for n,wanted in [('instrument',instrument),('contract',contract),('tick_type','trade')]):
            raise AggregateAuditError('mixed/unapproved raw identity or tick type')
        st=cols['source_row'].statistics
        if st.min < 0:
            raise AggregateAuditError('source identity outside bounded audit capacity')
        source_max=max(source_max,st.max)
    errors=Counter();warnings=Counter();seen={};last_ts=None;last_seq=None;rows=0
    trade_dates=set();aggressors=Counter();offsets=Counter();totals={};clock_minutes={}
    if type(include_clock_diagnostics) is not bool:
        raise AggregateAuditError("invalid clock diagnostic flag")
    # Bitmaps: exact source_file+source_row duplicate detection, including nonadjacent.
    # Bound total bitmap allocation; fail rather than approximate uniqueness.
    max_bitmap_bytes=128*1024*1024
    bitmap_bytes=4096; page_bits=bitmap_bytes*8; allocated_bytes=0
    for batch in pf.iter_batches(batch_size=batch_size,columns=required):
        t=batch.to_pandas();rows+=len(t)
        errors['null_required_rows']+=int(t.isna().any(axis=1).sum())
        if t.isna().any().any(): raise AggregateAuditError('null canonical payload')
        ns=t.ts_utc_ns.to_numpy();seq=t.sequence.to_numpy()
        errors['backward_timestamps']+=int((np.diff(ns)<0).sum()) + int(last_ts is not None and len(ns)>0 and ns[0]<last_ts)
        warnings['repeated_timestamps_legitimate']+=int((np.diff(ns)==0).sum()) + int(last_ts is not None and len(ns)>0 and ns[0]==last_ts)
        errors['nonincreasing_local_sequence']+=int((np.diff(seq)<=0).sum()) + int(last_seq is not None and len(seq)>0 and seq[0]<=last_seq)
        warnings['local_sequence_discontinuities_not_upstream_proof']+=int((np.diff(seq)>1).sum()) + int(last_seq is not None and len(seq)>0 and seq[0]>last_seq+1)
        if len(ns):last_ts=int(ns[-1]);last_seq=int(seq[-1])
        errors['invalid_timestamp_precision']+=int((ns%100 != 0).sum())
        errors['nonpositive_price_or_quote']+=int((t[['price_ticks','bid_ticks','ask_ticks']]<=0).any(axis=1).sum())
        errors['crossed_book']+=int((t.bid_ticks>t.ask_ticks).sum())
        warnings['locked_book']+=int((t.bid_ticks==t.ask_ticks).sum())
        errors['nonpositive_trade_volume']+=int((t.volume<=0).sum())
        errors['wrong_identity']+=int(((t.instrument!=instrument)|(t.contract!=contract)|(t.tick_type!='trade')).sum())
        errors['invalid_aggressor']+=int((~t.aggressor.isin(['buy','sell','unclassified','unknown'])).sum())
        warnings['unclassified_or_unknown_aggressor']+=int(t.aggressor.isin(['unclassified','unknown']).sum())
        aggressors.update(t.aggressor.value_counts().to_dict())
        offsets.update((t.ts_utc_ns-t.ts_local_ns).value_counts().to_dict())
        for source,g in t.groupby('source_file',sort=False):
            ids=g.source_row.to_numpy()
            if not isinstance(source,str) or not source.strip() or (ids<0).any() or (ids>source_max).any():
                raise AggregateAuditError('invalid source identity payload')
            pages=seen.setdefault(source,{})
            unique=np.unique(ids)
            errors['duplicate_source_identity']+=len(ids)-len(unique)
            page_ids=unique//page_bits
            for page in np.unique(page_ids):
                local=unique[page_ids==page]%page_bits
                if page not in pages:
                    if allocated_bytes+bitmap_bytes>max_bitmap_bytes:
                        raise AggregateAuditError('identity bitmap memory bound exceeded')
                    pages[page]=np.zeros(bitmap_bytes,dtype=np.uint8)
                    allocated_bytes+=bitmap_bytes
                bitmap=pages[page];byte_ids=local//8;bit_ids=local%8
                errors['duplicate_source_identity']+=int(((bitmap[byte_ids] >> bit_ids) & 1).sum())
                np.bitwise_or.at(bitmap,byte_ids,(1 << bit_ids).astype(np.uint8))
        ct=pd.to_datetime(t.ts_utc_ns,unit='ns',utc=True).dt.tz_convert('America/Chicago')
        # Vector calendar LABEL conversion. No per-row formatted date strings or
        # floating-point volume sums. Labels are not reviewed exchange calendars.
        hours=ct.dt.hour.to_numpy()
        local_days=ct.dt.tz_localize(None).to_numpy(dtype='datetime64[D]').astype(np.int64)
        day_ids=local_days+(hours>=17).astype(np.int64)
        unique,inverse=np.unique(day_ids,return_inverse=True)
        quantities=np.zeros(len(unique),dtype=np.int64)
        counts=np.bincount(inverse,minlength=len(unique))
        np.add.at(quantities,inverse,t.volume.to_numpy(dtype=np.int64))
        clock=(hours==16)
        for i,day_id in enumerate(unique):
            day=str(np.datetime64(int(day_id),'D'))
            if day>='2026-10-01':raise AggregateAuditError('reserved raw payload date')
            trade_dates.add(day);acc=totals.setdefault(day,{'trades':0,'volume':0})
            acc['trades']+=int(counts[i]);acc['volume']+=int(quantities[i])
            if include_clock_diagnostics:
                picked=(inverse==i)&clock
                acc['clock_band_16_to_17_CT_trade_rows']=acc.get('clock_band_16_to_17_CT_trade_rows',0)+int(picked.sum())
                clock_minutes.setdefault(day,set()).update((ns[picked]//(60*10**9)).tolist())
    if include_clock_diagnostics:
        for day,acc in totals.items():
            acc['clock_band_16_to_17_CT_observed_minutes']=len(clock_minutes[day])
    report={'schema':'edgelab_canonical_tick_structural_audit_v1','file':path.name,
        'sha256':expected_sha256,'bytes':expected_bytes,'rows':rows,'instrument':instrument,'contract':contract,
        'status':'FAIL_RAW_STRUCTURE' if any(errors.values()) else 'PASS_RAW_STRUCTURE_ONLY',
        'errors':dict(errors),'warnings':dict(warnings),'aggressor_counts':dict(aggressors),
        'source_identity_files':len(seen),'identity_bitmap_bytes':allocated_bytes,'first_trade_date':min(trade_dates),'last_trade_date':max(trade_dates),
        'observed_trade_dates':len(trade_dates),'footer_preflight_passed':True,
        'utc_minus_local_ns_counts':{str(k):v for k,v in offsets.items()},
        'timezone_independently_verified':False,'quote_aggressor_provenance_verified':False,
        'exchange_continuity_verified':False,'calendar_completeness_verified':False,
        'liquidity_certified':False,'research_allowed':False,'promotion_allowed':False,
        'price_outcomes_computed':False,'deduplicated_or_rewritten':False,
        'clock_diagnostics_enabled':include_clock_diagnostics,
        'clock_band_16_to_17_CT_trade_rows':sum(v.get('clock_band_16_to_17_CT_trade_rows',0) for v in totals.values()) if include_clock_diagnostics else None,
        'clock_band_16_to_17_CT_observed_minutes':sum(len(v) for v in clock_minutes.values()) if include_clock_diagnostics else None}
    return report,totals
