from pathlib import Path
import argparse,json,hashlib,math
import pandas as pd,numpy as np
p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--raw',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();A=a.out;A.mkdir(parents=True,exist_ok=True)
plan=json.loads(Path(__file__).with_name('plan.json').read_text());pins=json.loads((a.repo/'docs/research/avzvol_entry_distance_20261011/analysis-plan.json').read_text())['pins']
cols=['contract','cell','kind','session','clock','t0','te','pos','dir','trend','mom100_h','L','H','h','mx_h','o2','o3a','o3b']
fs=[]
for pin in pins:
 paths=list(a.raw.rglob(pin['basename']));assert len(paths)==1;f=paths[0];assert hashlib.sha256(f.read_bytes()).hexdigest()==pin['sha256'];d=pd.read_parquet(f,columns=cols);assert len(d)==pin['rows'];assert d.notna().all().all();fs.append(d[d.cell.isin(plan['cells'])].copy())
d=pd.concat(fs,ignore_index=True);d['momentum_sign']=np.sign(d.mom100_h).astype(int);d['ticks']=np.rint(d.mx_h*d.h).astype(int);d['fold']=0
for f in plan['folds']:d.loc[d.session.between(f['first'],f['last']),'fold']=f['fold']
t=d[d.fold>0].copy();base=t[t.pos.eq(0)&t.te.ge(0)]
ledger=[]
for (fold,cell,kind),z in t.groupby(['fold','cell','kind']):
 inside=z[z.pos.eq(0)];ex=inside[inside.te.ge(0)];ledger.append({'fold':int(fold),'cell':cell,'kind':kind,'all_records':len(z),'inside_records':len(inside),'no_exit':int(inside.te.lt(0).sum()),'unresolved_o2_exits':int((~ex.o2.isin([0,1])).sum()),'known_o2_exits':int(ex.o2.isin([0,1]).sum()),'retouch_exits':int(ex.o3a.ge(0).sum()),'unresolved_or_ambiguous_o3b':int((ex.o3a.ge(0)&~ex.o3b.isin([0,1])).sum())})
reach=base[base.o2.isin([0,1])].copy();assert np.array_equal(reach.ticks.ge(reach.h),reach.o2.eq(1));assert np.allclose(reach.ticks,reach.mx_h*reach.h,atol=1e-10,rtol=0)
metrics={}
for v in [5,10,20,40]:metrics['reach_'+str(v)+'ticks']=(reach,reach.ticks.ge(v).astype(float))
metrics['reach_1h']=(reach,reach.o2.astype(float))
z=base[base.dir.isin([-1,1])&base.trend.ne(0)].copy();metrics['trend_agreement']=(z,z.dir.eq(z.trend).astype(float))
z=base[base.o3a.ge(0)&base.o3b.isin([0,1])].copy();metrics['post_retouch_exit_side_first']=(z,z.o3b.eq(1).astype(float))
records=[];support=[];bycontract=[];checks=[];keys=['contract','session','clock','trend','momentum_sign']
for metric,(z,y) in metrics.items():
 z=z.copy();z['y']=y
 for fold in [1,2,3]:
  f=z[z.fold.eq(fold)].copy()
  # All six populations share identical context-stratum support and weights.
  grouped=f.groupby(keys+['cell','kind']).y.mean().unstack(['cell','kind'])
  wanted=pd.MultiIndex.from_product([plan['cells'],['real','pseudo']],names=['cell','kind'])
  common=grouped.reindex(columns=wanted).dropna();assert len(common)>0
  idx=pd.MultiIndex.from_frame(f[keys]);mask=idx.isin(common.index)
  for cell in plan['cells']:
   for kind in ['real','pseudo']:
    zz=f[f.cell.eq(cell)&f.kind.eq(kind)];kept=f[mask&f.cell.eq(cell)&f.kind.eq(kind)]
    for mode in ['unadjusted','joint_context']:
     if mode=='unadjusted':daily=zz.groupby(['contract','session']).y.mean()
     else:daily=common[(cell,kind)].groupby(['contract','session']).mean()
     ct=daily.groupby('contract').mean();rate=float(ct.mean());use=zz if mode=='unadjusted' else kept
     records.append({'metric':metric,'fold':fold,'cell':cell,'kind':kind,'mode':mode,'rate':rate,'rows':len(use),'sessions':int(use[['contract','session']].drop_duplicates().shape[0]),'contracts':len(ct)})
     for contract,cr in ct.items():
      cz=use[use.contract.eq(contract)];bycontract.append({'metric':metric,'fold':fold,'cell':cell,'kind':kind,'mode':mode,'contract':contract,'rate':float(cr),'rows':len(cz),'sessions':int(cz.session.nunique())})
    support.append({'metric':metric,'fold':fold,'cell':cell,'kind':kind,'eligible_rows':len(zz),'joint_context_rows':len(kept),'row_coverage':len(kept)/len(zz),'joint_strata':len(common),'joint_sessions':int(common.index.droplevel(['clock','trend','momentum_sign']).unique().shape[0])})
    # independent raw-row accumulation for the primary 20tick headline
    if metric=='reach_20ticks' and mode=='joint_context':
     bins={}
     for row in kept[keys+['y']].itertuples(index=False,name=None):bins.setdefault(tuple(row[:-1]),[]).append(row[-1])
     day={}
     for k,vals in bins.items():day.setdefault(k[:2],[]).append(math.fsum(vals)/len(vals))
     ctr={}
     for k,vals in day.items():ctr.setdefault(k[0],[]).append(math.fsum(vals)/len(vals))
     oracle=math.fsum(math.fsum(v)/len(v) for v in ctr.values())/len(ctr);assert abs(oracle-rate)<1e-12
     checks.append({'fold':fold,'cell':cell,'kind':kind,'metric':metric,'independent_error':abs(oracle-rate)})
r=pd.DataFrame(records);r.to_csv(A/'rates-by-fold.csv',index=False);pd.DataFrame(support).to_csv(A/'context-support.csv',index=False);pd.DataFrame(bycontract).to_csv(A/'rates-by-contract.csv',index=False);pd.DataFrame(ledger).to_csv(A/'population-ledger.csv',index=False)
s=r.groupby(['metric','cell','kind','mode']).agg(mean_rate=('rate','mean'),min_fold_rate=('rate','min'),max_fold_rate=('rate','max'),rows=('rows','sum')).reset_index();s.to_csv(A/'summary.csv',index=False)
e={'plan':plan,'pins':pins,'selected_export_rows':len(d),'test_rows':len(t),'summary':s.to_dict('records'),'ledger':ledger,'context_support':support,'independent_checks':checks,'claims':{'new_price_outcomes':False,'profitability':False,'causal_zone_effect':False,'full_corridor_memory_measured':False},'comparison_plan':[{'grain':'cell x cohort','population':'joint context supported knownO2 exits, equal3folds','unit':'reach percent','metric':'reach20ticks','disposition':'chart','reason':'height effect vs legacy controls within same pre-anchor context strata'},{'grain':'fold x cell','population':'same eligible cohorts','unit':'percent and pp','disposition':'table','reason':'preserve changes and reversals across periods'},{'grain':'cell','population':'different explicitly named populations','unit':'percent','disposition':'table','reason':'fixed ticks, oneheight and postretouch are distinct outcomes'}]}
(A/'evidence.json').write_text(json.dumps(e,indent=2));print(s[s.metric.isin(['reach_20ticks','reach_1h','trend_agreement','post_retouch_exit_side_first'])].to_string(index=False));print('\nPRIMARY BY FOLD');print(r[(r.metric=='reach_20ticks')&(r['mode']=='joint_context')].to_string(index=False));print('\nMATCH COVERAGE');print(pd.DataFrame(support).query("metric=='reach_20ticks'")[['fold','cell','kind','eligible_rows','joint_context_rows','row_coverage','joint_strata','joint_sessions']].to_string(index=False))

# Explicit post-exposure sensitivity extension: not a winning-rule search.
sens=[]
z=base[base.o3a.ge(0)&base.o3b.isin([0,1])].copy();z['y']=z.o3b.eq(1).astype(float)
for fold in [1,2,3]:
 f=z[z.fold.eq(fold)]
 for context,kk in [('clock',['contract','session','clock']),('clock_trend',['contract','session','clock','trend']),('clock_trend_momentum',keys)]:
  g=f.groupby(kk+['cell','kind']).y.mean().unstack(['cell','kind'])
  for policy in ['joint_six','within_cell_pair']:
   for cell in plan['cells']:
    required=wanted if policy=='joint_six' else pd.MultiIndex.from_product([[cell],['real','pseudo']],names=['cell','kind'])
    common=g.reindex(columns=required).dropna()
    for kind in ['real','pseudo']:
     vv=common[(cell,kind)];daily=vv.groupby(['contract','session']).mean()
     ff=f[f.cell.eq(cell)&f.kind.eq(kind)];keep=pd.MultiIndex.from_frame(ff[kk]).isin(common.index);kept=ff[keep]
     vals={'equal_contract_session':float(daily.groupby('contract').mean().mean()),'equal_session':float(daily.mean()),'pooled_supported_rows':float(kept.y.mean())}
     for weight,rate in vals.items():sens.append({'fold':fold,'cell':cell,'kind':kind,'context':context,'policy':policy,'weight':weight,'rate':rate,'rows':len(kept),'sessions':len(daily)})
pd.DataFrame(sens).to_csv(A/'retouch-sensitivity.csv',index=False)
# Simultaneous formation agreement is observable at the anchor in this export,
# unlike requiring eventual joint support in a whole clock/session stratum.
real=d[d.kind.eq('real')].copy();n=real[real.cell.eq('4_1000_20')].copy();kk=['contract','session','t0'];assert not n.duplicated(kk).any()
for h in [30,45]:
 w=real[real.cell.eq('4_1000_'+str(h))][kk+['L','H']];assert not w.duplicated(kk).any()
 n=n.merge(w.rename(columns={'L':'L'+str(h),'H':'H'+str(h)}),on=kk,how='left',validate='one_to_one')
 n['contains'+str(h)]=n['L'+str(h)].le(n.L)&n['H'+str(h)].ge(n.H)
n['coformation']=n.contains30.astype(int)+n.contains45.astype(int);co=[]
for fold in [1,2,3]:
 f=n[n.fold.eq(fold)]
 for status in [0,1,2]:
  allf=f[f.coformation.eq(status)];b=allf[allf.pos.eq(0)&allf.te.ge(0)]
  for metric in ['reach_20ticks','post_retouch_exit_side_first']:
   z=b[b.o2.isin([0,1])] if metric=='reach_20ticks' else b[b.o3a.ge(0)&b.o3b.isin([0,1])]
   y=z.ticks.ge(20).astype(float) if metric=='reach_20ticks' else z.o3b.eq(1).astype(float)
   daily=z.assign(y=y).groupby(['contract','session']).y.mean()
   co.append({'fold':fold,'status':status,'metric':metric,'formation_rows':len(allf),'eligible_rows':len(z),'sessions':len(daily),'equal_contract_rate':None if daily.empty else float(daily.groupby('contract').mean().mean()),'equal_session_rate':None if daily.empty else float(daily.mean()),'pooled_rate':None if z.empty else float(y.mean())})
pd.DataFrame(co).to_csv(A/'simultaneous-coformation.csv',index=False)
# All recorded retouches, not only resolved O3b, with adversarial bounds.
b=base[base.o3a.ge(0)].copy();b['lo']=b.o3b.eq(1).astype(float);b['hi']=(b.o3b.eq(1)|~b.o3b.isin([0,1])).astype(float);bounds=[]
for fold in [1,2,3]:
 f=b[b.fold.eq(fold)];g=f.groupby(keys+['cell','kind'])[['lo','hi']].mean().unstack(['cell','kind'])
 good=g.dropna()
 for cell in plan['cells']:
  for kind in ['real','pseudo']:
   lo=good[('lo',cell,kind)].groupby(['contract','session']).mean();hi=good[('hi',cell,kind)].groupby(['contract','session']).mean()
   bounds.append({'fold':fold,'cell':cell,'kind':kind,'lower_equal_session':float(lo.mean()),'upper_equal_session':float(hi.mean()),'lower_equal_contract':float(lo.groupby('contract').mean().mean()),'upper_equal_contract':float(hi.groupby('contract').mean().mean()),'joint_strata':len(good)})
pd.DataFrame(bounds).to_csv(A/'retouch-identification-bounds.csv',index=False)
e['post_exposure_extension_plan']=json.loads(Path(__file__).with_name('extension-plan.json').read_text());e['retouch_sensitivity']=sens;e['simultaneous_coformation']=co;e['retouch_bounds']=bounds
(A/'evidence.json').write_text(json.dumps(e,indent=2,allow_nan=False))
print('\nNARROW RETURN SENSITIVITY, MEAN3FOLDS');print(pd.DataFrame(sens).query("cell=='4_1000_20'").groupby(['context','policy','weight','kind']).rate.mean().to_string())
print('\nSIMULTANEOUS CONTAINED FORMATIONS');print(pd.DataFrame(co).to_string(index=False))
