import csv,json
from pathlib import Path
P=Path('/data/analysis/avzvol-expansion');chosen={}
with (P/'signals-private.csv').open() as f:
 for r in csv.DictReader(f):
  if (r['family'],r['origin'],r['mode'],r['endpoint'],r['D'],r['q'])!=('P80_W5_R8_1000_20','real','first_D_qualifying','touch','40','0.5'):continue
  k=(r['session'],int(r['trigger_idx'])//6250);v=(int(r['trigger_idx']),int(r['anchor_idx']),r)
  if k not in chosen or v[:2]<chosen[k][:2]:chosen[k]=v
r=[v[2] for v in chosen.values() if float(v[2]['prior256_corridor_overlap'])<.25];wins=sum(x['status']=='TARGET_FIRST' for x in r);loss=sum(x['status']=='OPPOSITE_FIRST' for x in r);un=len(r)-wins-loss
assert (wins,loss,un,len(r))==(255,212,9,476)
result=dict(independent_stream_filter_count='PASS',signals=len(r),wins=wins,losses=loss,unresolved=un,resolved=wins+loss,target_percent=100*wins/(wins+loss),by_day={d:dict(wins=sum(x['session']==d and x['status']=='TARGET_FIRST' for x in r),losses=sum(x['session']==d and x['status']=='OPPOSITE_FIRST' for x in r)) for d in sorted(set(x['session'] for x in r))})
(P/'headline-check.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
