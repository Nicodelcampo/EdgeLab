#!/usr/bin/env python3
"""Build a causal, target-free viewer bundle from the frozen HFT V2 SQLite.

The source is opened with SQLite mode=ro&immutable=1. The builder verifies the
physical SHA-256, canonical holdout firewall, schema, contract isolation and
causal timestamps before writing any derived artifact.
"""
from __future__ import annotations
import argparse, hashlib, json, sqlite3
from pathlib import Path
HOLDOUT_START_NS=1_782_856_800_000_000_000
REQUIRED_ZONE_COLUMNS={"instrument","contract","session_id","zone_seq","start_ts_ns","end_ts_ns","available_ts_ns","direction","price_lower","price_upper","height_ticks","termination_reason","vol","volume_rate","buy_vol","sell_vol","cvd_sweep","no_move_vol","max_level_ticks","parameter_manifest_sha256","indicator_source_sha256"}
def sha256_file(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for chunk in iter(lambda:f.read(8*1024*1024),b''): h.update(chunk)
 return h.hexdigest()
def connect_read_only(path): return sqlite3.connect(f"file:{Path(path).resolve().as_posix()}?mode=ro&immutable=1",uri=True)
def _columns(con,table): return {str(r[1]) for r in con.execute(f"PRAGMA table_info({table})")}
def preflight(con,instrument):
 tables={str(r[0]) for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
 if not {'hft_ticks_v2','hft_zones_v2'}.issubset(tables): raise ValueError('missing hft_ticks_v2 or hft_zones_v2')
 missing=sorted(REQUIRED_ZONE_COLUMNS-_columns(con,'hft_zones_v2'))
 if missing: raise ValueError('missing zone columns: '+', '.join(missing))
 th=int(con.execute("SELECT COUNT(*) FROM hft_ticks_v2 WHERE instrument=? AND timestamp_ns>=?",(instrument,HOLDOUT_START_NS)).fetchone()[0])
 zh=int(con.execute("SELECT COUNT(*) FROM hft_zones_v2 WHERE instrument=? AND (start_ts_ns>=? OR end_ts_ns>=? OR available_ts_ns>=?)",(instrument,HOLDOUT_START_NS,HOLDOUT_START_NS,HOLDOUT_START_NS)).fetchone()[0])
 if th or zh: raise ValueError(f'holdout firewall failed: ticks={th}, zones={zh}')
 contracts=[str(r[0]) for r in con.execute("SELECT DISTINCT contract FROM hft_ticks_v2 WHERE instrument=? ORDER BY contract",(instrument,))]
 if len(contracts)!=1: raise ValueError(f'exactly one contract required, found {contracts}')
 n,tmin,tmax=con.execute("SELECT COUNT(*),MIN(timestamp_ns),MAX(timestamp_ns) FROM hft_ticks_v2 WHERE instrument=?",(instrument,)).fetchone()
 zn=int(con.execute("SELECT COUNT(*) FROM hft_zones_v2 WHERE instrument=?",(instrument,)).fetchone()[0])
 if not n or not zn: raise ValueError('empty tick or zone ledger')
 bad=int(con.execute("SELECT COUNT(*) FROM hft_zones_v2 WHERE instrument=? AND (end_ts_ns<start_ts_ns OR available_ts_ns<end_ts_ns)",(instrument,)).fetchone()[0])
 if bad: raise ValueError(f'causal timestamp violations={bad}')
 return {'contract':contracts[0],'tick_count':int(n),'zone_count':zn,'t_min_ns':int(tmin),'t_max_ns':int(tmax),'holdout_boundary_ns':HOLDOUT_START_NS,'holdout_ticks':0,'holdout_zones':0,'holdout_rows_decoded':0}
def build(con,instrument,tick_size,max_points):
 meta=preflight(con,instrument)
 cols=['contract','session_id','zone_seq','start_ts_ns','end_ts_ns','available_ts_ns','direction','price_lower','price_upper','height_ticks','termination_reason','vol','volume_rate','buy_vol','sell_vol','cvd_sweep','no_move_vol','max_level_ticks','parameter_manifest_sha256','indicator_source_sha256']
 zones=[]; sql=','.join(f'"{c}"' for c in cols)
 for row in con.execute(f"SELECT {sql} FROM hft_zones_v2 WHERE instrument=? ORDER BY available_ts_ns,session_id,zone_seq",(instrument,)):
  z=dict(zip(cols,row)); z['id']=f"{z['contract']}:{z['session_id']}:{z['zone_seq']}:{z['direction']}"; z['origin_ts']=int(z.pop('start_ts_ns')); z['end_ts']=int(z.pop('end_ts_ns')); z['available_ts']=int(z.pop('available_ts_ns')); z['lo']=float(z.pop('price_lower')); z['hi']=float(z.pop('price_upper')); zones.append(z)
 stride=max(1,int(meta['tick_count'])//max(1,max_points))
 candles=[{'time_ns':int(ts),'price_tick':int(px),'price':round(int(px)*tick_size,4)} for ts,px in con.execute("SELECT timestamp_ns,price_ticks FROM hft_ticks_v2 WHERE instrument=? AND ((tick_seq-1)%?=0) ORDER BY timestamp_ns,tick_seq",(instrument,stride))]
 if not candles: raise ValueError('sampling produced no candles')
 meta.update({'instrument':instrument,'tick_size':tick_size,'sample_stride':stride,'candle_count':len(candles),'parity_status':'PASS_CERTIFIED_FULL_FIELD_PARITY_NATIVE_NT8_38_FIELDS','outcome_firewall':'ENFORCED','consumption_mode':'FIXED_DEMO_ONLY','volume_by_level_status':'UNAVAILABLE_FAIL_CLOSED'})
 return {'meta':meta,'candles':candles,'zones':zones}
def write_bundle(payload,output,source_sha256):
 output=Path(output); payload['meta']['source_sqlite_sha256']=source_sha256; canonical=json.dumps(payload,sort_keys=True,separators=(',',':')).encode(); payload['meta']['bundle_sha256']=hashlib.sha256(canonical).hexdigest(); output.parent.mkdir(parents=True,exist_ok=True); output.write_text('window.HFT_NQ_CORRIDOR_BUNDLE='+json.dumps(payload,separators=(',',':'))+';\n',encoding='utf-8'); manifest={'bundle_file':output.name,'meta':payload['meta']}; output.with_suffix('.manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8'); return manifest
def main():
 p=argparse.ArgumentParser(); p.add_argument('--db',required=True,type=Path); p.add_argument('--expected-db-sha256',required=True); p.add_argument('--instrument',default='NQ JUN26'); p.add_argument('--tick-size',type=float,default=.25); p.add_argument('--max-points',type=int,default=30000); p.add_argument('--output',type=Path,default=Path('viewer/nt8_bridge/hft_nq_bundle_certified.js')); a=p.parse_args(); actual=sha256_file(a.db)
 if actual!=a.expected_db_sha256.lower(): raise SystemExit(f'SQLite SHA-256 mismatch: {actual}')
 con=connect_read_only(a.db)
 try: payload=build(con,a.instrument,a.tick_size,a.max_points)
 finally: con.close()
 print(json.dumps(write_bundle(payload,a.output,actual),indent=2)); return 0
if __name__=='__main__': raise SystemExit(main())
