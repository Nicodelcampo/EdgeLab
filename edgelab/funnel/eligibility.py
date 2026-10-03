"""EF0 eligibility: automatic checks before any hypothesis is run. Unknown is not a pass."""
from __future__ import annotations

PASS,FAIL,UNKNOWN='PASS','FAIL','UNKNOWN'


def check_eligibility(build,regime,*,expected_contracts=(),clock_certified=None,costs_declared=False,min_sessions=60):
    """build: canonical build manifest dict. regime: contract-regime manifest dict.

    expected_contracts: contracts that SHOULD exist in the date span (e.g. every listed month).
    clock_certified: True/False/None (None = nobody certified it).
    Returns {'eligible': bool, 'checks': [...]}; eligible requires every check PASS (UNKNOWN blocks).
    """
    checks=[];add=lambda name,status,detail='':checks.append({'check':name,'status':status,'detail':detail})
    b=build.get('build',{});add('timestamps_monotonic',PASS if b.get('timestamp_backwards')==0 else FAIL,f"backwards={b.get('timestamp_backwards')}")
    add('no_duplicate_keys',PASS if b.get('duplicate_ts_sequence')==0 else FAIL,f"dups={b.get('duplicate_ts_sequence')}")
    out=build.get('output',{});add('output_hash_present',PASS if out.get('sha256') else FAIL,'')
    srcs=build.get('source_files',[]);add('source_hashes_present',PASS if srcs and all(s.get('sha256') for s in srcs) else FAIL,f'{len(srcs)} files')
    hold=build.get('holdout_first_trade_date') or regime.get('source_identity',{}).get('holdout_first_trade_date')
    dates=regime.get('calendar_trade_dates',[])
    add('holdout_excluded',(PASS if hold and dates and max(dates)<hold else (UNKNOWN if not hold else FAIL)),f'max_date={max(dates) if dates else None} holdout={hold}')
    add('roll_policy_strict_monotonic',PASS if regime.get('strict_crossover') and regime.get('monotonic_expiry') else FAIL,regime.get('policy_id',''))
    add('roll_causal_lag',PASS if int(regime.get('signal_lag_sessions',0))>=1 else FAIL,f"lag={regime.get('signal_lag_sessions')}")
    add('no_price_adjustment',PASS if regime.get('price_adjustment','').startswith('NONE') else UNKNOWN,regime.get('price_adjustment',''))
    have={c['contract'] for c in regime.get('contracts',[])};miss=sorted(set(expected_contracts)-have)
    add('contract_coverage',(UNKNOWN if not expected_contracts else (PASS if not miss else FAIL)),f'missing={miss}')
    add('session_count',PASS if len(dates)>=min_sessions else FAIL,f'{len(dates)} sessions (min {min_sessions})')
    add('clock_certified',PASS if clock_certified is True else (FAIL if clock_certified is False else UNKNOWN),'')
    add('costs_declared',PASS if costs_declared else UNKNOWN,'')
    return {'eligible':all(c['status']==PASS for c in checks),'checks':checks,'blocking':[c['check'] for c in checks if c['status']!=PASS]}
