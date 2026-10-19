"""EdgeReplica NT8 logical-state shadow port; NOT a broker or PnL evaluator.
Bar end timestamps are explicit aware UTC. Original next-bar fills are ASSUMED,
not observed. Future tick-exact execution must use independent broker traces.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from bisect import bisect_right
from zoneinfo import ZoneInfo
import json, math
from pathlib import Path

CHICAGO=ZoneInfo('America/Chicago')
@dataclass(frozen=True)
class Rule:
    id:int; dow:int; hhmm:int; direction:int; hold:int; cond:int
@dataclass(frozen=True)
class Bar:
    end:datetime
    close_ticks:int
    session_end:datetime
    contract:str
    regime_id:str

def load_rules(path):
    obj=json.loads(Path(path).read_text())
    rules=tuple(Rule(*r) for r in obj['rules'])
    if len(rules)!=60 or [r.id for r in rules]!=list(range(1,61)):
        raise ValueError('exact 60-rule source snapshot required')
    for r in rules:
        if r.dow not in range(6) or r.direction not in (-1,1) or r.cond not in (-1,0,1) or r.hold not in (15,30,60) or not 0<=r.hhmm//100<=23 or not 0<=r.hhmm%100<=59:
            raise ValueError('invalid source rule')
    return rules

def shadow_events(bars, rules, *, contracts=1, session_margin=0):
    """Reproduce CS step order on one unbroken contract/regime.
    Includes assumed fills and terminal unresolved state. No fees, returns,
    trading evidence or assertion of NinjaTrader managed-order acceptance.
    """
    if not 1<=contracts<=100 or not 0<=session_margin<=120:
        raise ValueError('CS parameter range')
    bars=list(bars);rules=tuple(rules)
    if len({r.id for r in rules})!=len(rules):raise ValueError('duplicate rule ids')
    for i,b in enumerate(bars):
        if b.end.tzinfo is None or b.session_end.tzinfo is None:
            raise ValueError('naive timestamps prohibited')
        if b.end.utcoffset()!=timedelta(0) or b.session_end.utcoffset()!=timedelta(0):
            raise ValueError('bar timestamps must be aware UTC')
        if b.end.second or b.end.microsecond or b.session_end<b.end:
            raise ValueError('invalid bar-end/session metadata')
        if isinstance(b.close_ticks,bool) or not isinstance(b.close_ticks,int):
            raise ValueError('canonical integer tick price required')
        if not b.contract.startswith('MNQ_') or not b.regime_id:
            raise ValueError('MNQ identity and regime are mandatory')
        if i and (b.end<=bars[i-1].end or (b.contract,b.regime_id)!=(bars[i-1].contract,bars[i-1].regime_id)):
            raise ValueError('unordered or mixed-regime stream; split and censor boundary')
    times=[b.end for b in bars]
    schedule={}
    for r in rules:schedule.setdefault(r.hhmm,[]).append(r)
    positions={};pending=[];submitted=[];fired=set();events=[]
    def emit(kind,r,i,**extra):
        events.append({'event':kind,'rule_id':r.id,'direction':r.direction,'bar_index':i,
            'at_utc':bars[i].end.isoformat(),'contract':bars[i].contract,
            'regime_id':bars[i].regime_id,'quantity':contracts,**extra})
    for i,b in enumerate(bars):
        if i<1:continue
        for kind,r,submission in submitted:
            if kind=='exit':
                positions.pop(r.id,None);emit('ASSUMED_EXIT_FILL',r,i)
            else:
                for rid,(other,_s) in list(positions.items()):
                    if other.direction!=r.direction:
                        emit('ASSUMED_REVERSAL_CLOSE',other,i,by_rule_id=r.id)
                        del positions[rid]
                positions[r.id]=(r,submission)
                emit('ASSUMED_ENTRY_FILL',r,i,submission_utc=submission.isoformat())
        submitted=[]
        for rid,(r,submission) in list(positions.items()):
            if b.end>=submission+timedelta(minutes=r.hold):
                emit('SUBMIT_EXIT',r,i,order_name=f'EXPERIMENT-{r.id}x')
                submitted.append(('exit',r,None))
        for r in pending:
            emit('SUBMIT_ENTRY',r,i,order_name=f'EXPERIMENT-{r.id}')
            submitted.append(('entry',r,b.end))
        pending=[]
        local=(b.end-timedelta(minutes=1)).astimezone(CHICAGO)
        if local.date()<datetime(2024,1,1).date() or local.isoweekday()>=6:continue
        hm=local.hour*100+local.minute
        due=schedule.get(hm,())
        ref=bisect_right(times,b.end-timedelta(minutes=15),0,i)-1
        has_ref=ref>=max(0,i-4999)
        delta=b.close_ticks-bars[ref].close_ticks if has_ref else 0
        sign=(delta>0)-(delta<0)
        remaining=(b.session_end-b.end).total_seconds()/60
        for r in due:
            key=(r.id,local.date())
            if (r.dow and r.dow!=local.isoweekday()) or key in fired:continue
            permitted=remaining>=r.hold+session_margin
            passes=r.cond==0 or (has_ref and sign==r.cond)
            if permitted and passes:
                pending.append(r);fired.add(key)
                emit('SIGNAL',r,i,reference_bar_index=(ref if has_ref else None),
                    condition_sign=sign,remaining_session_minutes=remaining)
    return {'status':'LOGICAL_SHADOW_ONLY','asserts_edge':False,
        'holdout_opened':False,'observed_broker_fills':False,'events':events,
        'unresolved':{'positions':sorted(positions),'pending_entries':[r.id for r in pending],
            'submitted_orders':[{'kind':k,'rule_id':r.id} for k,r,s in submitted]}}

def run_verified_shadow(*,reader,rules,root,trade_dates,certificate,regime_manifest,
        liquidity_limits,expected_certificate_sha256,expected_regime_sha256,
        contracts=1,session_margin=0):
    """Eligibility BEFORE reader invocation. Reader must avoid sealed groups."""
    if root!='MNQ':raise ValueError('other assets require separate preregistered transfer')
    from edgelab.data.contract_regime import validate_contract_regime
    from edgelab.data.research_data_gate import require_research_eligibility
    validate_contract_regime(regime_manifest)
    permissions=[require_research_eligibility(certificate=certificate,regime_manifest=regime_manifest,
        root=root,trade_date=d,liquidity_limits=liquidity_limits,
        expected_certificate_sha256=expected_certificate_sha256,expected_regime_sha256=expected_regime_sha256)
        for d in trade_dates]
    if not permissions:raise ValueError('no approved sessions')
    allowed={(p['contract'],p['trade_date'],p['regime_id']) for p in permissions}
    outputs=[]
    for segment in reader(permissions):
        segment=list(segment)
        for bar,trade_date in segment:
            if (bar.contract,trade_date,bar.regime_id) not in allowed:
                raise ValueError('reader returned unapproved asset/session')
        outputs.append(shadow_events([b for b,d in segment],rules,contracts=contracts,session_margin=session_margin))
    return outputs
