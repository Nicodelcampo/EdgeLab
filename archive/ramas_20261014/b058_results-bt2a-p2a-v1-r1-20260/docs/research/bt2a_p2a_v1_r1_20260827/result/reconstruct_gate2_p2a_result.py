#!/usr/bin/env python3
import hashlib,json
from pathlib import Path
p=Path(__file__).resolve().parent
h=json.loads((p/'result_header.json').read_text())
expected=h.pop('source_result_payload_sha256')
def load(prefix,key):
 out=[]
 for b in (5,9,18,30): out.extend(json.loads((p/f'{prefix}_B{b}.json').read_text())[key])
 return out
h['primary_family']=load('primary','primary_family')
h['secondary_clock_family']=load('secondary','secondary_clock_family')
actual=hashlib.sha256(json.dumps(h,sort_keys=True,separators=(',',':')).encode()).hexdigest()
assert actual==expected,(actual,expected)
h['payload_sha256']=expected
print(json.dumps(h,indent=2))
