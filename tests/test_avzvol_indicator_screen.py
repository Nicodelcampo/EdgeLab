"""Small deterministic helpers only; no market input or profitability claims."""
import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd

spec=importlib.util.spec_from_file_location('indicator_screen',Path(__file__).resolve().parents[1]/'tools/review_avzvol_indicator_screen.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def test_anchor_weights_share_duplicates_and_contracts():
    d=pd.DataFrame({'session':[1]*4,'contract':['A','A','A','B'],'t0':[2,2,3,4]})
    assert np.allclose(m.weights(d),[.125,.125,.25,.5])

def test_auc_ties_and_correct_order():
    y=np.array([0.,1.,0.,1.]);w=np.ones(4)
    assert m.auc(y,np.array([.1,.9,.1,.9]),w)==1
    assert m.auc(y,np.ones(4),w)==.5
    assert m.auc(y,1-y,w)==0

def test_training_edges_ignore_test_extremes_and_labels():
    tr=pd.DataFrame({'exit_delay_bars':np.arange(12),'range_over_band':np.arange(12)})
    te=pd.DataFrame({'exit_delay_bars':[1000.,1001.],'range_over_band':[1000.,1001.]})
    y=np.tile([0.,1.],6);w=np.ones(12);base=np.array([.5,.5])
    p,model,_=m.predict(tr,te,'delay_x_range_band',y,w,base,.5)
    assert max(model['training_only_edges']['exit_delay_bars'])<12
    assert max(model['training_only_edges']['range_over_band'])<12
    assert np.isfinite(p).all()

def test_pair_unseen_bucket_falls_back_to_cell_baseline():
    tr=pd.DataFrame({'exit_delay_bars':np.arange(12),'range_over_band':np.arange(12)})
    te=pd.DataFrame({'exit_delay_bars':[0.],'range_over_band':[1000.]})
    p,_,_=m.predict(tr,te,'delay_x_range_band',np.tile([0.,1.],6),np.ones(12),np.array([.4]),.5)
    assert np.allclose(p,[.4])

def test_weighted_quantile_observed_values_not_new_path():
    assert m.weighted_quantile(np.array([1.,3.]),np.ones(2),.5)==2
