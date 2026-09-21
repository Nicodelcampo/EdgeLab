import json
import subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
MODULE=ROOT/"viewer"/"nt8_bridge"/"crosshair_density_profile.js"
def node_eval(payload):
    script=f'''const d=require({json.dumps(str(MODULE))});process.stdout.write(JSON.stringify(d.build({json.dumps(payload)})));'''
    return json.loads(subprocess.check_output(["node","-e",script],text=True))
def test_profile_peaks_inside_zone_and_is_gaussian_outside():
    r=node_eval({"tickSize":.25,"minPrice":99,"maxPrice":102,"sigmaTicks":1,"ranges":[{"lo":100,"hi":101,"weight":10}]}); at_zone=r["density"][round(100/.25)-r["loTick"]]; below=r["density"][round(99.75/.25)-r["loTick"]]; assert at_zone==10; assert 0<below<at_zone; assert r["contributingRanges"]==1
def test_profile_adds_overlapping_ranges():
    r=node_eval({"tickSize":1,"minPrice":9,"maxPrice":13,"sigmaTicks":0,"ranges":[{"lo":10,"hi":12,"weight":2},{"lo":11,"hi":11,"weight":3}]}); assert r["density"]==[0,2,5,2,0]; assert r["maxDensity"]==5
def test_invalid_or_zero_weight_ranges_are_ignored():
    r=node_eval({"tickSize":.25,"minPrice":100,"maxPrice":101,"ranges":[{"lo":100,"hi":101,"weight":0},{"lo":None,"hi":101,"weight":2}]}); assert r["maxDensity"]==0; assert r["contributingRanges"]==0
def test_domain_guard_prevents_unbounded_allocation():
    script=f'''const d=require({json.dumps(str(MODULE))});try{{d.build({{tickSize:.01,minPrice:0,maxPrice:1000,maxBins:100}});process.exit(2)}}catch(e){{if(!String(e.message).includes("maxBins"))process.exit(3)}}'''; subprocess.run(["node","-e",script],check=True)
