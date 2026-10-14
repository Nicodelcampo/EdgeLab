"""Arithmetic tests only, no market or strategy outcomes."""
import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd
sp=importlib.util.spec_from_file_location('entry_distance',Path(__file__).resolve().parents[1]/'tools/review_avzvol_entry_distance.py')
m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)

def test_integer_threshold_ceil_handles_fractional_band_ticks():
    assert np.array_equal(m.cutoff_ticks(np.array([3,4,5,10]),.25),[1,1,2,3])

def test_integer_threshold_does_not_add_tick_from_float_rounding():
    assert np.array_equal(m.cutoff_ticks(np.array([10,20,30]),.1),[1,2,3])

def test_independent_weights_share_duplicate_cells_and_contracts():
    d=pd.DataFrame({'session':[1]*4,'contract':['A','A','A','B'],'t0':[2,2,3,4]})
    assert np.allclose(m.native_weights(d),[.125,.125,.25,.5])

def test_larger_assumed_entry_offset_never_improves_geometric_bound():
    h=np.array([20,40,20,40]);exc=np.array([8,16,20,40]);rates=[]
    for offset in [0,.1,.25,.5,.75]:rates.append(float(np.mean(exc>=m.cutoff_ticks(h,offset+.25))))
    assert all(a>=b for a,b in zip(rates,rates[1:]))
