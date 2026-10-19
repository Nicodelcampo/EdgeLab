import numpy as np
import pandas as pd
from edgelab.research.ema3_25t import GridCell, build_25t_bars, frozen_grid, simulate_cell

def ticks(prices,day="20260301"):
 p=np.asarray(prices,int); n=len(p)
 return pd.DataFrame({"ts_ns":np.arange(n,dtype=np.int64)+10**18,"price_ticks":p,"bid_ticks":p-1,"ask_ticks":p+1,"contract":["MGC 04-26"]*n,"trade_date":[day]*n,"_row":np.arange(n)})

def event():
 return [{"event_id":"e","contract":"MGC 04-26","trade_date":"20260301","bar_index":0,"bar_no":0,"signal_ns":10**18+2,"signal_close_ticks":102.0,"normal_side":1}]

def test_frozen_grid_contains_user_parity_cell():
 g=frozen_grid(); assert len(g)==108; assert len({x.cell_id for x in g})==108
 assert any(x.stop_ticks==200 and x.target_ticks==300 and x.breakeven_ticks is None for x in g)

def test_25t_never_crosses_trade_date_and_tail_is_incomplete():
 a=ticks([100]*26,"20260301"); b=ticks([101]*25,"20260302"); b.ts_ns+=100
 bars=build_25t_bars(pd.concat([a,b],ignore_index=True)); assert list(bars.trade_count)==[25,1,25]; assert list(bars.complete)==[True,False,True]

def test_25t_prefix_invariance():
 x=ticks(100+(np.arange(100)%7)); a=build_25t_bars(x.iloc[:75]); b=build_25t_bars(x)
 pd.testing.assert_frame_equal(a[["open","high","low","close","start_ns","close_ns"]].reset_index(drop=True),b.iloc[:3][["open","high","low","close","start_ns","close_ns"]].reset_index(drop=True))

def test_immediate_entry_is_after_signal_and_tp_uses_executable_quote():
 x=ticks([100,101,102,103,104,105,106,107,108]); bars=build_25t_bars(x,3)
 d=simulate_cell(x,bars,event(),GridCell("NORMAL",0,20,20,2,None,0),0)
 assert d.iloc[0].entry_ns>event()[0]["signal_ns"]; assert d.iloc[0].reason=="TP"

def test_pullback_touch_then_next_quote():
 x=ticks([100,101,102,101,99,100,101,102,103,104,105]); bars=build_25t_bars(x,3)
 d=simulate_cell(x,bars,event(),GridCell("NORMAL",3,20,20,3,None,0),0)
 assert d.iloc[0].entry_ns==10**18+5; assert d.iloc[0].entry_ticks==101

def test_breakeven_moves_stop_only_after_trigger():
 x=ticks([100,101,102,103,106,105,104,103,102,101]); bars=build_25t_bars(x,3)
 d=simulate_cell(x,bars,event(),GridCell("NORMAL",0,20,10,20,2,0),0)
 assert d.iloc[0].reason=="BE"; assert bool(d.iloc[0].be_active)
