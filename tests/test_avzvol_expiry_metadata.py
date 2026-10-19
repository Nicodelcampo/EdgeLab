"""Invented metadata and official-table fixtures; no tick/price/outcome payload."""
from pathlib import Path
from importlib.util import spec_from_file_location, module_from_spec
from datetime import date,datetime,timezone
import pytest
spec=spec_from_file_location('expiry',Path(__file__).resolve().parents[1]/'tools/review_avzvol_expiry_metadata.py')
m=module_from_spec(spec);spec.loader.exec_module(m)

def ns(day):
    dt=datetime.fromisoformat(day+'T12:00:00+00:00')
    return int(dt.timestamp())*1_000_000_000+123456700

def row(day,n=1):
    return {'ticks':n,'first':ns(day),'last':ns(day),'max_gap_s':0.}

def test_later_date_flagged_same_day_not_adjudicated():
    r={'20250919':row('2025-09-19',2),'20250921':row('2025-09-21',3)}
    q=m.summarize('MNQ_09-25',r,{'expiry':'2025-09-19','customary_roll':'2025-09-15'},set())
    assert q['declared_ticks_total']==5 and len(q['flagged_date_records'])==1
    assert q['flagged_date_records'][0]['declared_ticks']==3
    assert q['flagged_date_records'][0]['cause']=='UNKNOWN_NEEDS_UPSTREAM_EXPORT_TRACE'
    assert not q['flagged_date_records'][0]['excluded']

def test_selected_conflict_retained_not_silently_repaired():
    q=m.summarize('MNQ_09-25',{'20250921':row('2025-09-21')},{'expiry':'2025-09-19'}, {('2025-09-21','MNQ_09-25')})
    assert q['flagged_date_records'][0]['approved_in_resolver_for_this_contract']

def test_nanoseconds_and_dst_context_preserved():
    q=m.summarize('MNQ_09-25',{'20250921':row('2025-09-21')},{'expiry':'2025-09-19'},set())
    assert q['flagged_date_records'][0]['first_ct']=='2025-09-21T07:00:00.123456700-0500'

def test_june_exception_not_generic_rule():
    q=m.summarize('MNQ_06-26',{'20260618':row('2026-06-18')},{'expiry':'2026-06-18'},set())
    assert m.third_friday(2026,6)==date(2026,6,19)
    assert not q['generic_rule_agrees'] and not q['flagged_date_records']

@pytest.mark.parametrize('day',['2026-10-01','2026-10-02'])
def test_reserved_dates_stop(day):
    with pytest.raises(ValueError,match='reserved'):
        m.summarize('MNQ_12-26',{day.replace('-',''):row(day)},{'expiry':'2026-12-18'},set())

def test_unknown_count_stops():
    r=row('2025-09-21');r['ticks']=None
    with pytest.raises(ValueError,match='unknown metadata'):
        m.summarize('MNQ_09-25',{'20250921':r},{'expiry':'2025-09-19'},set())

def test_wrong_or_incomplete_reference_stops():
    for source in [{'url':'https://example.com','text':''},{'url':m.CME_URL,'text':'|2026 |6 |6/18 |6/15 |6/12 |6/8 |'}]:
        with pytest.raises(ValueError):m.parse_cme_reference(source)

def test_all_six_official_rows_with_exception():
    text='\n'.join(['|2025 |9 |9/19 |9/15 |9/12 |9/8 |','|2025 |12 |12/19 |12/15 |12/12 |12/8 |',
                     '|2026 |3 |3/20 |3/16 |3/13 |3/9 |','|2026 |6 |6/18 |6/15 |6/12 |6/8 |',
                     '|2026 |9 |9/18 |9/14 |9/11 |9/7 |','|2026 |12 |12/18 |12/14 |12/11 |12/7 |'])
    q=m.parse_cme_reference({'url':m.CME_URL,'text':text})
    assert list(q)==m.CONTRACTS and q['MNQ_06-26']['expiry']=='2026-06-18'
