#!/usr/bin/env python3
"""Portable local/Kaggle entrypoint for E1-E3 (+ optional E4 multiplicity); never opens D2 or the holdout."""
import argparse,json,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from edgelab.funnel.runner import FunnelRunner
def main():
 p=argparse.ArgumentParser();p.add_argument('--arrays',required=True);p.add_argument('--registry',required=True);p.add_argument('--out',required=True);p.add_argument('--backend',choices=['auto','cpu','gpu'],default='auto')
 p.add_argument('--holdout-first-date',type=int,required=True,help='abort if any trade date is >= this value (mandatory)')
 p.add_argument('--e4',action='store_true',help='also run EF3/EF4: max-null under randomized direction, plateau, global trial count')
 p.add_argument('--campaign-id',required=True);p.add_argument('--trial-registry',required=True,help='hash-chained global trial counter (mandatory)');p.add_argument('--seen-ledger',default=None);p.add_argument('--nsims',type=int,default=500);p.add_argument('--seed',type=int,default=20261004);p.add_argument('--min-trades',type=int,default=30)
 a=p.parse_args();root=Path(a.arrays);load=lambda n:np.load(root/f'{n}.npy',mmap_mode='r');reg=json.load(open(a.registry));raw=reg.get('candidates',reg);cfg=[]
 for c in raw:
  cfg.append({'candidate_id':c['candidate_id'],'family_id':c.get('family_id',reg.get('family_id','UNDECLARED_FAMILY')),'direction':c.get('direction','normal'),'sl_ticks':c['sl_ticks'],'tp_ticks':c['tp_ticks']})
 r=FunnelRunner(trade_dates=load('trade_date'),signal_idx=load('signal_bar_idx'),signal_dir=load('signal_dir'),high=load('high_ticks'),low=load('low_ticks'),bid_open=load('bid_open_ticks'),ask_open=load('ask_open_ticks'),configs=cfg,out_dir=a.out,backend=a.backend,holdout_first_date=a.holdout_first_date,campaign_id=a.campaign_id,trial_registry=a.trial_registry,seen_ledger=a.seen_ledger)
 print(json.dumps(r.run_e1_e3(min_trades=a.min_trades),indent=2))
 if a.e4:print(json.dumps(r.run_e4(n_sims=a.nsims,seed=a.seed,min_trades=a.min_trades),indent=2))
if __name__=='__main__':main()
