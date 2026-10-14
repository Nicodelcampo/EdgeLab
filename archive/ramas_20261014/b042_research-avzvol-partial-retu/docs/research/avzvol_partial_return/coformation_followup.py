from pathlib import Path
import json,hashlib, argparse
import numpy as np,pandas as pd
p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--raw',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
pins=json.loads((a.repo/'docs/research/avzvol_entry_distance_20261011/analysis-plan.json').read_text())['pins'];cols=['cell','kind','contract','session','clock','t0','L','H','h','trend','mom100_h','pos','te','o2','o3a','o3b','mx_h'];frames=[]
for pin in pins:
 files=list(a.raw.rglob(pin['basename']));assert len(files)==1 and hashlib.sha256(files[0].read_bytes()).hexdigest()==pin['sha256'];d=pd.read_parquet(files[0],columns=cols);assert len(d)==pin['rows'];assert d.notna().all().all();frames.append(d[d.kind.eq('real')&d.cell.isin(['4_1000_20','4_1000_30','4_1000_45'])])
d=pd.concat(frames,ignore_index=True);n=d[d.cell.eq('4_1000_20')].copy();kk=['contract','session','t0'];assert not n.duplicated(kk).any()
for h in [30,45]:
 wide=d[d.cell.eq('4_1000_'+str(h))][kk+['L','H']];assert not wide.duplicated(kk).any();n=n.merge(wide.rename(columns={'L':'L'+str(h),'H':'H'+str(h)}),on=kk,how='left',validate='one_to_one');n['contains'+str(h)]=n['L'+str(h)].le(n.L)&n['H'+str(h)].ge(n.H)
n['status']=n.contains30.astype(int)+n.contains45.astype(int);n['mom_sign']=np.sign(n.mom100_h).astype(int);n['ticks']=np.rint(n.mx_h*n.h).astype(int)
keys=['contract','session','clock','trend','mom_sign','h'];results=[];contracts=[]
for fold,first,last in [(1,20260112,20260402),(2,20260406,20260625),(3,20260626,20260930)]:
 f=n[n.session.between(first,last)&n.pos.eq(0)&n.te.ge(0)&n.status.isin([0,2])].copy()
 for metric in ['post_retouch_exit_side_first','reach20ticks']:
  z=f[f.o3a.ge(0)&f.o3b.isin([0,1])].copy() if metric=='post_retouch_exit_side_first' else f[f.o2.isin([0,1])].copy();z['y']=z.o3b.eq(1).astype(float) if metric=='post_retouch_exit_side_first' else z.ticks.ge(20).astype(float)
  common=z.groupby(keys+['status']).y.mean().unstack('status').reindex(columns=[0,2]).dropna()
  for status in [0,2]:
   zz=z[z.status.eq(status)];keep=pd.MultiIndex.from_frame(zz[keys]).isin(common.index);matched=zz[keep];daily=common[status].groupby(['contract','session']).mean();ct=daily.groupby('contract').mean()
   results.append({'fold':fold,'metric':metric,'status':status,'eligible_rows':len(zz),'matched_rows':len(matched),'joint_strata':len(common),'matched_sessions':len(daily),'equal_session_rate':None if daily.empty else float(daily.mean()),'equal_contract_rate':None if daily.empty else float(ct.mean())})
   for contract,rate in ct.items():contracts.append({'fold':fold,'metric':metric,'status':status,'contract':contract,'rate':float(rate),'sessions':int(daily.loc[contract].shape[0])})
r=pd.DataFrame(results);r.to_csv(a.out/'coformation-matched-height.csv',index=False);pd.DataFrame(contracts).to_csv(a.out/'coformation-matched-height-by-contract.csv',index=False)
e={'plan':json.loads(Path(__file__).with_name('coformation-plan.json').read_text()),'pins':pins,'results':results,'partial_return_empirical_results':None,'source_tape_prices_or_imbalance_loaded':False,'source_quality_gates_modified':False};(a.out/'coformation-evidence.json').write_text(json.dumps(e,indent=2));print(r.to_string(index=False))
# Support robustness after exact context/height overlap proved very sparse.
# Retain every variant; no best-bin selection and no significance claim.
coarse=[]
for fold,first,last in [(1,20260112,20260402),(2,20260406,20260625),(3,20260626,20260930)]:
 f=n[n.session.between(first,last)&n.pos.eq(0)&n.te.ge(0)&n.status.isin([0,2])&n.o3a.ge(0)&n.o3b.isin([0,1])].copy();f['y']=f.o3b.eq(1).astype(float)
 for name,keys in [('height_day',['contract','session','h']),('height_clock_day',['contract','session','h','clock']),('height_full_context',['contract','session','h','clock','trend','mom_sign'])]:
  common=f.groupby(keys+['status']).y.mean().unstack('status').reindex(columns=[0,2]).dropna()
  for status in [0,2]:
   zz=f[f.status.eq(status)];keep=pd.MultiIndex.from_frame(zz[keys]).isin(common.index);daily=common[status].groupby(['contract','session']).mean()
   coarse.append({'fold':fold,'context':name,'status':status,'matched_rows':int(keep.sum()),'sessions':len(daily),'strata':len(common),'equal_session_rate':None if daily.empty else float(daily.mean()),'equal_contract_rate':None if daily.empty else float(daily.groupby('contract').mean().mean())})
pd.DataFrame(coarse).to_csv(a.out/'coformation-support-sensitivity.csv',index=False);e['coarsening_post_exposure']=coarse;(a.out/'coformation-evidence.json').write_text(json.dumps(e,indent=2));print('SUPPORT SENSITIVITY');print(pd.DataFrame(coarse).to_string(index=False))
