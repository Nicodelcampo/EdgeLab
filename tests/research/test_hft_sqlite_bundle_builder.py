import importlib.util,json,sqlite3
from pathlib import Path
import pytest
MODULE=Path(__file__).resolve().parents[2]/'tools'/'build_hft_corridor_bundle_from_sqlite.py'; spec=importlib.util.spec_from_file_location('sqlite_bundle',MODULE); builder=importlib.util.module_from_spec(spec); spec.loader.exec_module(builder)
def db():
 con=sqlite3.connect(':memory:'); con.execute('CREATE TABLE hft_ticks_v2 (instrument TEXT,contract TEXT,session_id TEXT,tick_seq INTEGER,timestamp_ns INTEGER,price_ticks INTEGER,volume REAL)'); con.execute('CREATE TABLE hft_zones_v2 (instrument TEXT,contract TEXT,session_id TEXT,zone_seq INTEGER,start_ts_ns INTEGER,end_ts_ns INTEGER,available_ts_ns INTEGER,direction INTEGER,price_lower REAL,price_upper REAL,height_ticks REAL,termination_reason TEXT NOT NULL,vol REAL,volume_rate REAL,buy_vol REAL,sell_vol REAL,cvd_sweep REAL,no_move_vol REAL,max_level_ticks INTEGER,parameter_manifest_sha256 TEXT,indicator_source_sha256 TEXT)')
 for i in range(1,5): con.execute('INSERT INTO hft_ticks_v2 VALUES (?,?,?,?,?,?,?)',('NQ JUN26','NQ 06-26','20260601',i,100+i,80000+i,1.0))
 con.execute('INSERT INTO hft_zones_v2 VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',('NQ JUN26','NQ 06-26','20260601',1,101,102,103,1,20000.25,20000.75,2.0,'REVERSAL',10.,100.,6.,4.,2.,1.,80002,'a'*64,'b'*64)); con.commit(); return con
def test_preflight_and_bundle_are_causal():
 con=db(); pre=builder.preflight(con,'NQ JUN26'); assert pre['holdout_ticks']==pre['holdout_zones']==0; payload=builder.build(con,'NQ JUN26',.25,100); assert payload['meta']['volume_by_level_status']=='UNAVAILABLE_FAIL_CLOSED'; assert payload['zones'][0]['available_ts']==103; assert payload['zones'][0]['id']=='NQ 06-26:20260601:1:1'
def test_tick_at_holdout_fails_closed():
 con=db(); con.execute('UPDATE hft_ticks_v2 SET timestamp_ns=? WHERE tick_seq=4',(builder.HOLDOUT_START_NS,));
 with pytest.raises(ValueError,match='holdout firewall'): builder.preflight(con,'NQ JUN26')
def test_zone_availability_at_holdout_fails_closed():
 con=db(); con.execute('UPDATE hft_zones_v2 SET available_ts_ns=?',(builder.HOLDOUT_START_NS,));
 with pytest.raises(ValueError,match='holdout firewall'): builder.preflight(con,'NQ JUN26')
def test_bundle_manifest_carries_source_hash(tmp_path):
 payload=builder.build(db(),'NQ JUN26',.25,100); out=tmp_path/'bundle.js'; manifest=builder.write_bundle(payload,out,'f'*64); assert manifest['meta']['source_sqlite_sha256']=='f'*64; assert json.loads(out.with_suffix('.manifest.json').read_text())['meta']['holdout_rows_decoded']==0
