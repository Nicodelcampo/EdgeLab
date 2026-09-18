import importlib.util
from pathlib import Path
import numpy as np,pytest
from edgelab.bridge.ticks import TickSeries
ROOT=Path(__file__).resolve().parents[2];MODULE=ROOT/'tools'/'build_multiasset_25t_hft_bundles.py';spec=importlib.util.spec_from_file_location('multiasset_hft',MODULE);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def entry(end_ns=1_780_000_001_000_000_000):
 return {'instrument':'NQ','contract':'NQ 06-26','parquet':'unused.parquet','expected_sha256':'a'*64,'sessions':[{'trade_date':20260601,'start_utc_ns':1_780_000_000_000_000_000,'end_utc_ns':end_ns,'prev_session_close_ticks':99}]}
def ticks():
 n=60;start=1_780_000_000_000_000_000
 return TickSeries(start+np.arange(n,dtype=np.int64)*1_000_000,100+np.arange(n,dtype=np.int64),np.ones(n),99+np.arange(n,dtype=np.int64),101+np.arange(n,dtype=np.int64),np.arange(n,dtype=np.int64),0.25,'NQ','NQ 06-26','synthetic')
def test_builds_tick25_and_causal_hft_without_transporting_parity(monkeypatch):
 monkeypatch.setattr(m,'load_canonical_parquet',lambda *a,**k:ticks());bundle,manifest=m.build_entry(entry(),holdout_ns=m.DEFAULT_HOLDOUT_NS,source_sha256='a'*64);assert len(bundle['bar_series']['tick_25']['candles'])==3;assert bundle['meta']['tick_size']==0.25;assert manifest['parity_status']=='PARITY_ABSTAIN';assert manifest['holdout_rows_decoded']==0
 for z in bundle['runs'][0]['zones']:assert z['origin_ts_ns']<=z['end_ts_ns']<=z['available_ns']<m.DEFAULT_HOLDOUT_NS
def test_rejects_holdout_crossing_session():
 with pytest.raises(ValueError,match='holdout'):m.validate_entry(entry(m.DEFAULT_HOLDOUT_NS+1),m.DEFAULT_HOLDOUT_NS)
def test_non_abstain_parity_requires_evidence_hash():
 e=entry();e['parity_status']='PASS_CERTIFIED'
 with pytest.raises(ValueError,match='parity_evidence_sha256'):m.validate_entry(e,m.DEFAULT_HOLDOUT_NS)
def test_non_nq_parameters_are_explicitly_uncalibrated(monkeypatch):
 e=entry();e['instrument']='GC';e['contract']='GC 06-26';tk=ticks();tk.instrument='GC';tk.contract='GC 06-26';tk.tick_size=.1;monkeypatch.setattr(m,'load_canonical_parquet',lambda *a,**k:tk);_,man=m.build_entry(e,holdout_ns=m.DEFAULT_HOLDOUT_NS,source_sha256='a'*64);assert man['engine_status']=='ENGINE_PORTABLE';assert man['parameter_status']=='PARAMETERS_UNCALIBRATED';assert man['parity_status']=='PARITY_ABSTAIN'
