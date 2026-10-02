#!/usr/bin/env python3
import json
from pathlib import Path
import numpy as np
OUT=Path('/data/analysis/mgc/tick_exact')
def main():
 rng=np.random.default_rng(20261002);res={};mapping={'0':'MGC_12-25','1':'MGC_02-26','2':'MGC_04-26','3':'MGC_06-26'}
 for tp in (300,400,450):
  z=np.load(OUT/f'normal_sl200_tp{tp}.npz');p=z['pnl_ticks'];td=z['exit_trade_date'];cid=z['contract_id'];days=np.unique(td);daily=np.array([p[td==d].sum() for d in days]);boot=daily[rng.integers(0,len(days),size=(20000,len(days)))].sum(1);split=int(len(days)*.7)
  res[str(tp)]={'trades':len(p),'net_ticks':float(p.sum()),'bootstrap_session_positive':float((boot>0).mean()),'is_70_net_ticks':float(daily[:split].sum()),'oos_30_net_ticks':float(daily[split:].sum()),'months':{str(int(m)):float(p[td//100==m].sum()) for m in np.unique(td//100)},'contracts':{mapping[str(int(c))]:float(p[cid==c].sum()) for c in np.unique(cid)},'cost_sensitivity_net_ticks':{str(cost):float(p.sum()-(cost-.5)*len(p)) for cost in (.5,2,4,6,8,10)}}
 out={'schema_version':'mgc_tick_exact_stability_v2','bar_artifact_id':json.load(open('/data/analysis/mgc/tick_exact/results.json'))['bar_artifact_id'],'unit':'trade ledger aggregated by exit CME trade date','holdout_opened':False,'contract_id_map':mapping,'results':res};(OUT/'stability.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
if __name__=='__main__':main()
