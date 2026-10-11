"""Invented labels/outcomes only; no market prices, fills or profit claims."""
from pathlib import Path
from importlib.util import spec_from_file_location,module_from_spec
import subprocess,sys
import pandas as pd
import numpy as np
import pytest
spec=spec_from_file_location('entry',Path(__file__).resolve().parents[1]/'tools/review_avzvol_entry_hypotheses.py');m=module_from_spec(spec);spec.loader.exec_module(m)
def frame():
 rows=[]
 for c in m.core.CONTRACTS:
  for kind,codes in [('real',[1,0,-2]),('pseudo',[1,0,-1])]:
   for rb in codes:rows.append(dict(contract=c,session=1,cell='4_250_20',clock=0,trend=1,kind=kind,t0=0,te=10,dir=1,pos=0,mom100_h=1.,o2=0,o3a=1,o3b=rb))
 d=pd.DataFrame(rows);d['bounce']=d.o3b.where(d.o3b.isin([0,1]),np.nan);d['retest']=d.o3a.astype(float)
 return d

def test_exit_known_categories_and_no_future_as_anchor_predictor():
 d=pd.DataFrame({'trend':[1,-1,1,0,1],'mom100_h':[1.,-1.,-1.,1.,1.],'dir':[1,1,1,1,0],'te':[1,1,1,1,-1]})
 assert list(m.exit_context(d))==['BOTH_ALIGNED','BOTH_OPPOSED','MIXED','NEUTRAL_OR_ZERO','NO_EXIT']
 assert 'unavailable at original anchor' in m.plan()['exit_known_cut']

def test_ambiguous_and_unresolved_not_scored_as_binary_failures():
 d=frame();r,g,c=m.core.summarize(d,'bounce');assert r['headline']['real_rate_percent']==50 and r['headline']['pseudo_rate_percent']==50
 b=m.bounce_bounds(d,g,c);assert b['lower_gap_pp']==pytest.approx(-100/3) and b['upper_gap_pp']==pytest.approx(100/3)

def test_no_retest_not_in_bounce_denominator():
 d=frame();extra=d.iloc[[0]].copy();extra['o3a']=0;extra['o3b']=-1;extra['bounce']=np.nan;extra['retest']=0
 d=pd.concat([d,extra]);r,g,c=m.core.summarize(d,'bounce');assert r['headline']['real_rate_percent']==50
 assert m.bounce_bounds(d,g,c)['upper_gap_pp']==pytest.approx(100/3)

def test_all_cells_and_no_backtest_promotion():
 r=m.summarize_scope(frame());assert len(r['bounce_given_resolved_retest']['cells'])==36
 assert m.plan()['no_entry_or_exit_fills'] and m.plan()['no_economic_outcomes'] and m.plan()['no_parameter_optimization']

@pytest.mark.parametrize('optin',[False,True])
def test_optin_and_code_pin_stop_before_payload(tmp_path,optin):
 source=tmp_path/'source';source.write_text('invented')
 cmd=[sys.executable,'-O',m.__file__,'--inventory',str(tmp_path/'missing'),'--historical-stage-source',str(source),'--out-dir',str(tmp_path/'out')]
 if optin:cmd.append('--allow-exposed-entry-hypothesis-review')
 r=subprocess.run(cmd,capture_output=True,text=True);assert r.returncode==2 and not (tmp_path/'out').exists()


def test_exit_delay_quantiles_independent_and_empty():
 assert m.exit_delay_summary(np.array([1,2,3,10]))=={'median_exit_delay_25_trade_bars':2.5,'q90_exit_delay_25_trade_bars':pytest.approx(7.9)}
 assert m.exit_delay_summary(np.array([]))['median_exit_delay_25_trade_bars'] is None
 with pytest.raises(ValueError):m.exit_delay_summary(np.array([0]))
