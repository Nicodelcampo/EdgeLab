import pandas as pd, numpy as np, json, hashlib, itertools, argparse
from pathlib import Path
parser=argparse.ArgumentParser(description='Frequency-only screen of the six already-exposed pinned cluster exports; no price outcomes.')
parser.add_argument('--raw-root',type=Path,required=True)
parser.add_argument('--out',type=Path,required=True)
parser.add_argument('--repo-root',type=Path,default=Path(__file__).resolve().parents[3])
a=parser.parse_args()
out=a.out;out.mkdir(parents=True,exist_ok=True)
plan_path=Path(__file__).with_name('plan.json')
plan=json.loads(plan_path.read_text())
pins=json.loads((a.repo_root/'docs/research/avzvol_entry_distance_20261011/analysis-plan.json').read_text())['pins']
files=sorted(a.raw_root.glob('k*/*.parquet'))
assert len(files)==6 and {p.name for p in files}=={x['basename'] for x in pins}, 'Expected exactly six pinned exports'
cols=['cell','contract','kind','session','t0','L','H','h','pos','te','o2']
frames=[]
for p in files:
 pin=next(x for x in pins if x['basename']==p.name)
 assert hashlib.sha256(p.read_bytes()).hexdigest()==pin['sha256']
 d=pd.read_parquet(p,columns=cols);assert len(d)==pin['rows'];frames.append(d)
d=pd.concat(frames,ignore_index=True)
universe=pd.MultiIndex.from_frame(d[['contract','session']].drop_duplicates())
r=d[d.kind=='real'].copy()
assert len(d)==544531 and len(r)==96755
cells=['_'.join(map(str,x)) for x in itertools.product([4,5,6,8],[250,500,1000],[20,30,45])]
rows=[]; contract_rows=[]
contracts=sorted(r.contract.unique())
for cell in cells:
 g=r[r.cell==cell];m,w,a=map(int,cell.split('_'))
 daily=g.groupby(['contract','session']).size().reindex(universe,fill_value=0)
 anchors=g.drop_duplicates(['contract','session','t0'])
 identity=g.drop_duplicates(['contract','session','t0','L','H'])
 by=g.groupby('contract').size().reindex(contracts,fill_value=0)
 row={'cell':cell,'min_zones':m,'lookback':w,'height_max':a,'formation_records':len(g),'distinct_anchors':len(anchors),'distinct_exact_records':len(identity),'duplicate_exact_records':len(g)-len(identity),'represented_contract_sessions':len(universe),'active_contract_sessions':int((daily>0).sum()),'coverage_pct':float(100*(daily>0).mean()),'records_per_represented_contract_session':float(daily.mean()),'daily_median':float(daily.median()),'daily_p10':float(daily.quantile(.1)),'daily_p90':float(daily.quantile(.9)),'min_contract_records':int(by.min()),'height_median':float(g.h.median()) if len(g) else None,'inside_records':int((g.pos==0).sum())}
 rows.append(row)
 for contract,n in by.items():
  u=[s for c,s in universe if c==contract];z=g[g.contract==contract]
  contract_rows.append({'cell':cell,'contract':contract,'records':int(n),'represented_sessions':len(u),'active_sessions':int(z.session.nunique()),'records_per_represented_session':float(n/len(u))})
s=pd.DataFrame(rows).sort_values(['formation_records','cell'],ascending=[False,True]);s.to_csv(out/'frequency.csv',index=False)
cs=pd.DataFrame(contract_rows);cs.to_csv(out/'frequency-by-contract.csv',index=False)
# independent direct raw filter check for overall leader
leader=s.iloc[0];direct=sum(int(((f.kind=='real')&(f.cell==leader.cell)).sum()) for f in frames)
assert direct==int(leader.formation_records);assert s.formation_records.sum()==len(r)
assert set(r.cell).issubset(set(cells))
assert len(rows)==36 and len(contract_rows)==216
assert all(x['duplicate_exact_records']==0 for x in rows)
# Fixed one-parameter comparisons, no outcome selection.
comparisons=[]
for m in [4,5,6,8]:
 for a in [20,30,45]:
  z=s[(s.min_zones==m)&(s.height_max==a)].sort_values('lookback')
  comparisons.append({'m':m,'a':a,'records_by_lookback':z[['lookback','formation_records']].to_dict('records'),'nondecreasing':bool(np.all(np.diff(z.formation_records)>=0))})
for w in [250,500,1000]:
 for a in [20,30,45]:
  z=s[(s.lookback==w)&(s.height_max==a)].sort_values('min_zones')
  comparisons.append({'w':w,'a':a,'records_by_min':z[['min_zones','formation_records']].to_dict('records'),'nonincreasing':bool(np.all(np.diff(z.formation_records)<=0))})
# Complete median frequency profile by maxheight, not additive across overlapping configs.
ev={'plan':plan,'source_pins':pins,'raw_rows':len(d),'real_rows':len(r),'represented_contract_sessions':len(universe),'counts':s.to_dict('records'),'by_contract':contract_rows,'one_parameter_comparisons':comparisons,'independent_check':{'leader_cell':leader.cell,'direct_records':direct,'passed':True},'visual_plan':[{'grain':'configuration','population':'all exported real formations','unit':'records','finding':'frequency shortlist includes high-count tight-height comparator','disposition':'chart','reason':'compare support without outcome-based selection'},{'grain':'configuration x contract','population':'represented export sessions','unit':'records/session','disposition':'table','reason':'retain temporal/contract variation'}]}
(out/'evidence.json').write_text(json.dumps(ev,indent=2))
print(s.head(8).to_string(index=False))
print('\nTIGHT HEIGHT:');print(s[s.height_max==20].head(4).to_string(index=False))
print('\nMIN=4,HEIGHT=20 LOOKBACK:');print(s[(s.min_zones==4)&(s.height_max==20)][['cell','formation_records','coverage_pct','records_per_represented_contract_session']].to_string(index=False))
print('\nLEADER BY CONTRACT:');print(cs[cs.cell==leader.cell].to_string(index=False))
print('monotonic lookback:',sum(x.get('nondecreasing',False) for x in comparisons),'of12; min:',sum(x.get('nonincreasing',False) for x in comparisons),'of9')
