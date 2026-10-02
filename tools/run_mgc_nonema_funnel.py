#!/usr/bin/env python3
"""Target-free D0/D1 funnel for three fixed non-EMA MGC families. D2 stays sealed."""
import json,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from edgelab.funnel.runner import FunnelRunner
from edgelab.funnel.signals import session_vwap_reclaim,absorption_break,failed_auction_reentry
ROOT=Path('/data/analysis/mgc/artifacts')/Path('/data/analysis/mgc/artifacts/LATEST').read_text().strip();OUT=Path('/data/analysis/mgc/nonema_funnel')
def l(n):return np.load(ROOT/f'{n}.npy',mmap_mode='r')
def configs(family):
 return [{'candidate_id':f'{family.lower()}_sl{sl}_tp{tp}','family_id':family,'direction':'normal','sl_ticks':sl,'tp_ticks':tp} for sl,tp in [(100,200),(150,300),(200,400)]]
def main():
 O,H,L,C,V,TD,BO,AO=[l(n) for n in ('open_ticks','high_ticks','low_ticks','close_ticks','volume','trade_date','bid_open_ticks','ask_open_ticks')]
 families={
  'SESSION_VWAP_RECLAIM':session_vwap_reclaim(C,V,TD,50,20),
  'L1_ABSORPTION_BREAK':absorption_break(O,H,L,C,V,TD,100,2.0,10),
  'OPENING_RANGE_FAILED_AUCTION':failed_auction_reentry(H,L,C,TD,100,2000),
 }
 result={'schema_version':'mgc_nonema_funnel_v1','artifact_id':ROOT.name,'holdout_opened':False,'families':{}}
 for family,(si,sd) in families.items():
  r=FunnelRunner(trade_dates=TD,signal_idx=si,signal_dir=sd,high=H,low=L,bid_open=BO,ask_open=AO,configs=configs(family),out_dir=OUT/family.lower(),backend='auto');summary=r.run_e1_e3(min_trades=30)
  try:r.d2_mask();raise AssertionError('D2 opened')
  except PermissionError:pass
  result['families'][family]={'signals':len(si),'long':int((sd==1).sum()),'short':int((sd==-1).sum()),'tested':summary['tested'],'survivors':summary['survivors'],'headlines':summary['headlines'],'split_hash':summary['split']['split_hash'],'ledger':r.ledger.verify()}
 OUT.mkdir(parents=True,exist_ok=True);(OUT/'summary.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
if __name__=='__main__':main()
