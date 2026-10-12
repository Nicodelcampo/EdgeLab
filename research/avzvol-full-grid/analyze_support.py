"""Descriptive census of ALL full-grid cells; volume-based priority, never winner selection."""
import os,json,csv,gzip,math
from pathlib import Path
from collections import Counter
import numpy as np,pandas as pd
P=Path('/data/analysis/avzvol-matrix-run');C=os.environ.get('MATRIX_CONTRACT','MNQ_12-26');R=P/C;manifest=json.load(open(R/'manifest.json'));verified=json.load(open(R/'coverage-verification.json'));assert verified['config_rule_pairs']==1935360
configs=pd.read_csv('/data/raw/avzvol-matrix/detector-configurations.csv').set_index('config_id');rules=pd.read_csv('/data/raw/avzvol-matrix/partial-return-rules.csv');nd=len(manifest['event_dates']);tiers=Counter();frequency=[];top=[];total=0;check=[];signals_total=0;resolved_total=0
head=['config_id','rule_id','births','raw_signals','thinned_signals','thinned_resolved','target_first','opposite_first','unresolved','active_signal_dates','active_resolved_dates','days_target_gt_opposite','target_percent','largest_day_resolved_share','raw_over_thinned_signals']
with gzip.open(R/'cell-support-private.csv.gz','wt',newline='',compresslevel=1) as out:
 writer=csv.writer(out);writer.writerow(head)
 for ci in range(1536):
  a=np.load(R/f'config-{ci:04d}.npz');raw=a['counts'];thin=a['thinned_daily'];assert thin.shape==(1260,nd,10);w=thin[:,:,4].sum(axis=1);l=thin[:,:,5].sum(axis=1);n=w+l;sig=thin[:,:,4:9].sum(axis=(1,2));rawsig=raw[:,4:9].sum(axis=1);active=(thin[:,:,4:9].sum(axis=2)>0).sum(axis=1);resolved_days=thin[:,:,4]+thin[:,:,5];nactive=(resolved_days>0).sum(axis=1);positive=(thin[:,:,4]>thin[:,:,5]).sum(axis=1);shares=np.divide(resolved_days.max(axis=1),n,out=np.full(1260,np.nan),where=n>0);rates=np.divide(100*w,n,out=np.full(1260,np.nan),where=n>0);overlap=np.divide(rawsig,sig,out=np.full(1260,np.nan),where=sig>0);b=int(a['births'])
  tier=np.select([sig==0,n==0,n<30,n<100,n<300],['no_signal','signals_none_resolved','1-29_resolved','30-99_resolved','100-299_resolved'],default='300+_resolved');tiers.update(tier.tolist());total+=1260;signals_total+=int(sig.sum());resolved_total+=int(n.sum())
  f=dict(config_id=ci,births=b,**configs.loc[ci].to_dict(),median_thinned_resolved=float(np.median(n)),max_thinned_resolved=int(n.max()),rules_with_100_resolved=int((n>=100).sum()),rules_with_100_resolved_80pct_dates=int(((n>=100)&(nactive>=math.ceil(.8*nd))).sum()));frequency.append(f)
  for ri in range(1260):writer.writerow([ci,ri,b,int(rawsig[ri]),int(sig[ri]),int(n[ri]),int(w[ri]),int(l[ri]),int(sig[ri]-n[ri]),int(active[ri]),int(nactive[ri]),int(positive[ri]),rates[ri] if n[ri] else '',shares[ri] if n[ri] else '',overlap[ri] if sig[ri] else ''])
  # Priority only by support, not outcome percentage. Keep all ties deterministic.
  ix=np.lexsort((np.arange(1260),-nactive,-n))[:10]
  top.extend(dict(config_id=ci,rule_id=int(ri),resolved=int(n[ri]),active_resolved_dates=int(nactive[ri]),target_first=int(w[ri]),opposite_first=int(l[ri])) for ri in ix if n[ri]>0)
  if ci in [0,97,511,1023,1535]:
   for ri in [0,419,1259]:
    # Distinct Python event-status traversal versus NumPy reductions.
    wins=sum(int(thin[ri,j,4]) for j in range(nd));losses=sum(int(thin[ri,j,5]) for j in range(nd));signals=sum(sum(int(thin[ri,j,k]) for k in [4,5,6,7,8]) for j in range(nd));assert wins==w[ri] and losses==l[ri] and signals==sig[ri];check.append([ci,ri])
assert total==1935360 and sum(tiers.values())==total
f=pd.DataFrame(frequency);f.to_csv(R/'configuration-support.csv',index=False);tops=sorted(top,key=lambda r:(-r['resolved'],-r['active_resolved_dates'],r['config_id'],r['rule_id']))[:100];pd.DataFrame(tops).to_csv(R/'volume-priority-cells.csv',index=False)
rows=[]
for (pct,win),g in f.groupby(['percentile','window_bars']):rows.append(dict(percentile=float(pct),window_bars=int(win),configurations=len(g),configurations_with_births=int(g.births.gt(0).sum()),median_births=float(g.births.median()),median_max_resolved=float(g.max_thinned_resolved.median()),configurations_with_any_rule_100_resolved=int(g.rules_with_100_resolved.gt(0).sum())))
pd.DataFrame(rows).to_csv(R/'percentile-window-support.csv',index=False)
out=dict(status='ALL_CELLS_DESCRIPTIVE_SUPPORT_COMPLETE',contract=C,selected_sessions=nd,config_rule_pairs=total,support_tiers=dict(tiers),configuration_with_any_100_resolved=int(f.rules_with_100_resolved.gt(0).sum()),configuration_with_any_100_resolved_80pct_dates=int(f.rules_with_100_resolved_80pct_dates.gt(0).sum()),percentile_window_support=rows,priority_rule='resolved count descending, then active resolved dates, then config/rule ID; never target rate',independent_reductions_checked=check,all_cell_signal_assignments_not_independent=signals_total,all_cell_resolved_assignments_not_independent=resolved_total,births_reused_across_configs=True,signals_reused_across_rules=True,thinning_does_not_prove_independence=True,multiplicity_corrected=False,virgin_holdout=False,pnl_computed=False,comparison_plan=[dict(grain='rule/configuration pair',population='all 1935360 cells in the selected contract sessions',unit='cell count',finding='support census retains empty and unresolved cells; no outcome-based winner promotion',disposition='prose',reason='progress/census, not inferential comparison')]);(R/'support-evidence.json').write_text(json.dumps(out,indent=2)+'\n');print('SUPPORT_COMPLETE',C,total,dict(tiers),flush=True)
