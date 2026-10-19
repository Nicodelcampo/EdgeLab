import json
import pytest
from run_extension import merge_population
from extension_stats import inference
def test_merge_sorted_preserves_original_objects():
    old=[dict(id='a',day='20251007',signal_ns=2,profit=5)]
    new=[dict(id='b',day='20250804',signal_ns=1,profit=-3)]
    rows,days=merge_population(new,old,['20250804'],['20251007'])
    assert [r['id'] for r in rows]==['b','a'] and old[0]['profit']==5
    assert days==['20250804','20251007']
def test_overlap_calendar_fails_closed():
    with pytest.raises(AssertionError,match='OVERLAPPING_CALENDARS'):
        merge_population([],[],['20251007'],['20251007'])
def test_duplicate_ids_fail_closed():
    with pytest.raises(AssertionError,match='DUPLICATE_SIGNAL'):
        merge_population([dict(id='x',day='a',signal_ns=1)],[dict(id='x',day='b',signal_ns=2)],['a'],['b'])
def test_foreign_day_fails_closed():
    with pytest.raises(AssertionError):
        merge_population([dict(id='x',day='z',signal_ns=1)],[],['a'],['b'])
def test_small_block_studentized_remains_blocked():
    days=[str(i) for i in range(43)]
    rows=[dict(day=d,x=(i%7)-2.) for i,d in enumerate(days)]
    m={'bootstrap_replicates':100,'studentized_replicates':100}
    r=inference(rows,days,'x',123,m)
    assert r['n_sessions']==43 and r['studentized_bonf20']['status']=='BLOCKED'
    assert 'diagnostic_lower_bonf20' in r and 'diagnostic_lower_bonf12' not in r
def test_statistical_adapter_has_no_strategy_tuning():
    from pathlib import Path
    s=Path('extension_stats.py').read_text()
    assert '.05/20' in s and '.05/142' in s and '.05/12' not in s and 'def detect' not in s