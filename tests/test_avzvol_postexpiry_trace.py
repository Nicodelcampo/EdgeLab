"""Invented identity-only tables; prices and outcomes are forbidden."""
from pathlib import Path
from importlib.util import spec_from_file_location,module_from_spec
import pyarrow as pa
import pytest
spec=spec_from_file_location('trace',Path(__file__).resolve().parents[1]/'tools/trace_avzvol_postexpiry_identities.py')
m=module_from_spec(spec);spec.loader.exec_module(m)

def table():
    return pa.table({'ts_utc_ns':[10,20,30],'sequence':[0,1,2], 'tick_type':['trade']*3,
      'instrument':['MNQ']*3,'contract':['MNQ 09-25']*3,'source_file':['invented.utc.txt']*3,'source_row':[0,1,2]})

def test_exact_identity_columns_and_independent_filter():
    assert len(m.select_identities(table(),20))==2
    assert not m.select_identities(table(),31)

def test_extra_price_column_stops():
    with pytest.raises(ValueError,match='unexpected payload'):
        m.select_identities(table().append_column('price_ticks',pa.array([1,2,3])),20)

def test_unknown_identity_stops():
    t=table().set_column(6,'source_row',pa.array([0,None,2]))
    with pytest.raises(ValueError,match='unknown identity'):m.select_identities(t,20)

def test_ct_nanoseconds_preserved_not_original_clock_certified():
    assert m.reported_ct(1758489344084163900)=='2025-09-21T16:15:44.084163900-0500'

def test_following_civil_midnight_has_dst_offset():
    from datetime import datetime,timezone
    expected=int(datetime(2025,9,20,5,tzinfo=timezone.utc).timestamp())*10**9
    assert m.civil_day_after_expiry_ns('2025-09-19')==expected
