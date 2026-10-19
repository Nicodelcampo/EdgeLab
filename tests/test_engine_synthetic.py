"""Frozen-engine regression scenarios; invented ticks, never market data."""
import numpy as np
import pytest
from edgelab.engine import run_ledger, run_grid

@pytest.mark.parametrize("direction,sign,outcome", [(1,1,"tp"),(1,-1,"sl"),(-1,-1,"tp"),(-1,1,"sl")])
def test_synthetic_fills_and_pnl(direction, sign, outcome):
    t = np.arange(8, dtype=np.int64)*100
    last = 100.0 + sign*np.arange(8, dtype=np.float64)*0.25
    bid, ask = last-0.125, last+0.125
    out = run_ledger(np.array([0]),np.array([direction]),t,last,bid,ask,2.,2.,tick=0.25,fees=0.5)
    assert len(out)==1
    row=out.iloc[0]
    assert row.entry_i==1
    assert row.entry_px == (ask[1] if direction==1 else bid[1])
    assert row.reason==outcome
    assert row.pnl_ticks==pytest.approx(direction*(row.exit_px-row.entry_px)/0.25-0.5)
    assert (row.pnl_ticks>0) == (outcome=="tp")
    grid=run_grid(np.array([0]),np.array([direction]),t,last,bid,ask,np.array([2.]),np.array([2.]),tick=0.25,fees=0.5)
    assert grid[0,0,0]==pytest.approx(row.pnl_ticks)

def test_signal_at_end_has_no_fill():
    t=np.arange(4,dtype=np.int64); last=np.full(4,100.)
    out=run_ledger(np.array([3]),np.array([1]),t,last,last-0.125,last+0.125,2.,2.)
    assert out.empty
