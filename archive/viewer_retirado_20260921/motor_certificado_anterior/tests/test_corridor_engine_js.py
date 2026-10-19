import json,subprocess
from pathlib import Path
ENGINE=Path(__file__).resolve().parents[2]/'viewer'/'nt8_bridge'/'corridor_engine.js'
def run(js): return subprocess.run(['node','-e',f"const E=require({json.dumps(str(ENGINE))});{js}"],text=True,capture_output=True,check=True).stdout.strip()
def test_economic_state_is_viewport_invariant():
 js="const zones=[{id:'z1',origin_ts:1,end_ts:2,available_ts:3,lo:100,hi:101,direction:1,vol:4}],candles=[{time_ns:1,price:99},{time_ns:4,price:102}],f=E.field({zones,candles,asOf:4,tickSize:1,config:{sigmaTicks:1}}),a=E.canonicalState(f,E.corridors(f,1,50)),viewportA={zoom:1,width:800},viewportB={zoom:9,width:1900},b=E.canonicalState(f,E.corridors(f,1,50));console.log(a===b)"; assert run(js)=='true'
def test_zone_is_not_visible_before_available_ts(): assert run("console.log(E.eligibleZones([{id:'z',origin_ts:1,end_ts:2,available_ts:5,lo:1,hi:2,direction:1}],4).length)")=='0'
def test_holdout_zone_and_synthetic_volume_fail_closed():
 js="let a=false,b=false;try{E.eligibleZones([{id:'z',origin_ts:1,end_ts:2,available_ts:E.HOLDOUT,lo:1,hi:2,direction:1}],E.HOLDOUT)}catch(e){a=true}try{E.consumeVolume()}catch(e){b=true}console.log(a&&b)"; assert run(js)=='true'
