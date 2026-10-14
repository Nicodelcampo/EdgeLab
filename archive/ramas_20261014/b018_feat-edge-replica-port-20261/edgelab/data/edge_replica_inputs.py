"""Streaming MNQ input adapter; explicit calendar, no invented empty bars.
Use ONLY behind run_verified_shadow and a custody/embargo-safe source reader.
Calendar pins are integrity checks, not independent calendar adjudication.
"""
from __future__ import annotations
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
import hashlib,json
from strategies.edge_replica import Bar
from edgelab.data.asset_safety import validate_mnq_tick_batch
NS=1_000_000_000
MINUTE=60*NS

def calendar_digest(calendar):
    return hashlib.sha256(json.dumps(calendar,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def _utc(ns):
    return datetime.fromtimestamp(ns//NS,tz=timezone.utc)

def make_shadow_reader(source_reader,*,calendar,expected_calendar_sha256,cutoff_ns,report):
    """source_reader(permission) yields canonical tick dicts, bounded BEFORE read.
    Calendar: list of {contract,regime_id,trade_date,open_ns,close_ns,status}.
    No fallback to weekday-only calendars. Each session is explicitly censored
    and independently reset; this is a diagnostic admission policy, not claimed
    parity with a continuous NT8 chart across missing/terminal sessions.
    """
    if type(cutoff_ns)!=int or cutoff_ns<=0:raise ValueError('explicit cutoff required')
    if not calendar or calendar_digest(calendar)!=expected_calendar_sha256:
        raise ValueError('missing or mismatched calendar')
    lookup={}
    for s in calendar:
        key=(s['contract'],s['trade_date'],s['regime_id'])
        if key in lookup:raise ValueError('duplicate calendar identity')
        if s['status']!='VERIFIED' or type(s['open_ns'])!=int or type(s['close_ns'])!=int:
            raise ValueError('calendar not verified')
        if not 0<s['open_ns']<s['close_ns']<cutoff_ns:
            raise ValueError('invalid or sealed calendar interval')
        close_ct=_utc(s['close_ns']).astimezone(ZoneInfo('America/Chicago'))
        if type(s['trade_date'])!=int or int(close_ct.strftime('%Y%m%d'))!=s['trade_date'] or close_ct.weekday()>=5:
            raise ValueError('calendar trade-date/close mismatch')
        if s['open_ns']%MINUTE or s['close_ns']%MINUTE:
            raise ValueError('minute-aligned calendar required')
        lookup[key]=s
    report.update(calendar_sha256=expected_calendar_sha256,fill_model='ASSUMED_NOT_BROKER_VERIFIED',
                  empty_bars_fabricated=0,session_reset_policy='EXPLICIT_SESSION_DIAGNOSTIC',sessions=[])
    def reader(permissions):
        chosen=[];seen=set()
        # Complete all admission checks before any source callback.
        for p in permissions:
            key=(p['contract'],p['trade_date'],p['regime_id'])
            if key in seen or key not in lookup:raise ValueError('missing/duplicate admitted session')
            if not p['contract'].startswith('MNQ_'):raise ValueError('MNQ required')
            seen.add(key);chosen.append((p,lookup[key]))
        if not chosen:raise ValueError('no admitted sessions')
        for permission,s in chosen:
            rows=[];prior=None;current=None;stat={'trade_date':s['trade_date'],'contract':s['contract'],
                'regime_id':s['regime_id'],'ticks':0,'bars':0,'missing_minutes':0,
                'terminal_policy':'CENSOR_UNRESOLVED_NO_RETROSPECTIVE_FILL'}
            def flush():
                if current is None:return
                end=(current['bucket']+1)*MINUTE
                if end>s['close_ns']:raise ValueError('bar crosses declared session close')
                rows.append((Bar(_utc(end),current['close'],_utc(s['close_ns']),
                                 s['contract'],s['regime_id']),s['trade_date']))
                stat['bars']+=1
            for tick in source_reader(permission):
                if any(k not in tick for k in ('instrument','contract','source_file','source_row')):
                    raise ValueError('canonical identity/lineage required')
                if not isinstance(tick['source_file'],str) or not tick['source_file'] or type(tick['source_row'])!=int or tick['source_row']<0:
                    raise ValueError('invalid original source identity')
                identity={k:tick[k] for k in ('ts_utc_ns','sequence','source_file','source_row')}
                if stat['ticks']==0:stat['first_event']=identity
                stat['last_event']=identity
                cols={k:[v] for k,v in tick.items()}
                prior=validate_mnq_tick_batch(cols,expected_contract=s['contract'],previous_key=prior)
                ts=tick['ts_utc_ns']
                if not s['open_ns']<=ts<s['close_ns'] or ts>=cutoff_ns:
                    raise ValueError('source returned out-of-session or sealed tick')
                if tick.get('tick_type')!='trade':raise ValueError('trade tick semantics required')
                bucket=ts//MINUTE
                if current is None or current['bucket']!=bucket:
                    if current is not None:
                        stat['missing_minutes']+=bucket-current['bucket']-1
                    flush();current={'bucket':bucket,'close':tick['price_ticks']}
                else:current['close']=tick['price_ticks']
                stat['ticks']+=1
            flush()
            if not rows:raise ValueError('no admitted ticks; missing is not zero')
            # Count boundary holes as well. Counts do NOT certify completeness.
            stat['missing_minutes']+=(int(rows[0][0].end.timestamp())*NS-MINUTE-s['open_ns'])//MINUTE
            stat['missing_minutes']+=(s['close_ns']-int(rows[-1][0].end.timestamp())*NS)//MINUTE
            stat['missing_minutes']=int(stat['missing_minutes'])
            stat['complete_session_certified_by_adapter']=False
            report['sessions'].append(stat)
            yield rows
    return reader
