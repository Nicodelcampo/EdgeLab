"""Dependency-light regression tests; no CUDA or market data."""
import importlib.util
from pathlib import Path
import sys, types, unittest
from unittest.mock import patch
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('funnel_isolation_under_test',ROOT/'edgelab/funnel/isolation.py')
iso=importlib.util.module_from_spec(spec);sys.modules[spec.name]=iso;spec.loader.exec_module(iso)
parity_spec=importlib.util.spec_from_file_location('parity_oracle',ROOT/'tools/verify_funnel_cpu_gpu.py')
parity=importlib.util.module_from_spec(parity_spec);parity_spec.loader.exec_module(parity)

class IsolationTests(unittest.TestCase):
    def test_horizon_not_crossing_partition(self):
        w=iso.stage_window(np.repeat([1,2,3],5),np.arange(15),[1,2],2)
        self.assertEqual(w.signal_positions.tolist(),list(range(7)))
        self.assertEqual(w.excluded_boundary_signals,2)
        self.assertTrue(np.all(w.local_signals(np.arange(15))+1+2<w.bar_stop))
    def test_stage_local_reindex(self):
        w=iso.stage_window(np.repeat([1,2,3],5),np.arange(15),[2],1)
        self.assertEqual(w.signal_positions.tolist(),[4,5,6,7])
        self.assertEqual(w.local_signals(np.arange(15)).tolist(),[-1,0,1,2])
    def test_unsorted_dates_rejected(self):
        with self.assertRaises(ValueError): iso.stage_window([2,1],[0],[1],1)
    def test_invalid_signal_rejected(self):
        for sig in ([-1],[3],[.5]):
            with self.assertRaises(ValueError): iso.stage_window([1,1,1],sig,[1],1)
    def test_noncontiguous_partition_rejected(self):
        with self.assertRaises(ValueError): iso.stage_window([1,2,3],[0],[1,3],1)
    def test_empty_signals(self):
        w=iso.stage_window([1,1],np.array([],np.int64),[1],2)
        self.assertEqual(len(w.signal_positions),0)
    def test_oracle_known_paths(self):
        for name,raw in parity.cases():
            if name=='known_paths': np.testing.assert_equal(parity.oracle(*raw),[[9.5],[9.5],[np.nan]])
            if name=='stop_first_tie': np.testing.assert_equal(parity.oracle(*raw),[[-10.5]])
            if name=='target_touch_not_fill': np.testing.assert_equal(parity.oracle(*raw),[[-.5]])
    def test_float64_budget_and_minimum_column(self):
        # Resolve the lazy relative import without importing Numba/CUDA.
        fake=types.ModuleType('fake_funnel.screen')
        def batches(*args,**kw):
            ns=len(args[0]);nc=len(args[6]);b=max(1,kw['max_matrix_bytes']//(ns*4))
            for start in range(0,nc,b):
                end=min(nc,start+b);yield start,end,np.zeros((ns,end-start),np.float64),None
        fake.iter_screen_batches=batches
        with patch.object(iso,'__package__','fake_funnel'),patch.dict(sys.modules,{'fake_funnel.screen':fake}):
            args=(np.array([0,1]),np.array([1,-1]),*[np.ones(4,np.int32)]*4,np.array([1,2,3]),np.array([1,2,3]))
            out=list(iso.bounded_batches(*args,max_matrix_bytes=16))
            self.assertEqual([(a,b) for a,b,_,_ in out],[(0,1),(1,2),(2,3)])
            self.assertTrue(all(x.nbytes<=16 for _,_,x,_ in out))
            with self.assertRaises(ValueError): list(iso.bounded_batches(*args,max_matrix_bytes=8))
    def test_mutating_d2_cannot_change_stage_oracle(self):
        td=np.repeat([1,2,3],8);sig=np.arange(24);w=iso.stage_window(td,sig,[2],2)
        h=np.full(24,105);l=np.full(24,95);bo=np.full(24,99);ao=np.full(24,101)
        def outcome():
            s=slice(w.bar_start,w.bar_stop)
            return parity.oracle(w.local_signals(sig),np.ones(len(w.signal_positions)),h[s],l[s],bo[s],ao[s],[3],[4],[1],2,.5)
        before=outcome();h[16:]=999999;l[16:]=-999999;bo[16:]=-12345;ao[16:]=12345
        np.testing.assert_equal(before,outcome())

if __name__=='__main__': unittest.main()

class RunnerRouteTests(unittest.TestCase):
    def test_runner_never_routes_d2_prices(self):
        import tempfile
        fake=types.ModuleType('fake_runner');fake.__path__=[]
        iso_mod=types.ModuleType('fake_runner.isolation');seen=[]
        def batches(sig,d,h,l,bo,ao,sl,tp,m,**kw):
            seen.append((h.copy(),l.copy()))
            matrix=parity.oracle(sig,d,h,l,bo,ao,sl,tp,m,kw['max_hold_bars'],.5)
            yield 0,len(sl),matrix,types.SimpleNamespace(backend='cpu')
        iso_mod.bounded_batches=batches;iso_mod.stage_window=iso.stage_window
        splits=types.ModuleType('fake_runner.splits')
        splits.make_splits=lambda td:types.SimpleNamespace(d0_dates=(1,),d1_dates=(2,),d2_dates=(3,),split_hash='synthetic')
        splits.mask_for=lambda *a,**kw:None
        splits.to_dict=lambda s:dict(d0_dates=[1],d1_dates=[2],d2_dates=[3],split_hash=s.split_hash)
        artifacts=[]
        surv=types.ModuleType('fake_runner.survivors')
        def write(rows,path,metadata): artifacts.append(rows);return {'rows':len(rows)}
        surv.write_survivors=write
        ledger=types.ModuleType('fake_runner.ledger')
        class Ledger:
            def __init__(self,path):pass
            def append(self,*a):pass
        ledger.FunnelLedger=Ledger
        pbo=types.ModuleType('validation.pbo');pbo.pbo_cscv=lambda *a,**kw:None
        def load_pure(name):
            sp=importlib.util.spec_from_file_location('fake_runner.'+name,ROOT/f'edgelab/funnel/{name}.py');m=importlib.util.module_from_spec(sp);sys.modules[sp.name]=m;sp.loader.exec_module(m);return m
        screen_stub=types.ModuleType('fake_runner.screen');screen_stub.kernel_manifest=lambda backend:{'kernel_id':'stub'}
        modules={'fake_runner.custody':load_pure('custody'),'fake_runner.multiplicity':load_pure('multiplicity'),'fake_runner.screen':screen_stub,'fake_runner':fake,'fake_runner.isolation':iso_mod,'fake_runner.splits':splits,'fake_runner.survivors':surv,'fake_runner.ledger':ledger,'validation':types.ModuleType('validation'),'validation.pbo':pbo}
        with patch.dict(sys.modules,modules),tempfile.TemporaryDirectory() as out:
            spec=importlib.util.spec_from_file_location('fake_runner.runner',ROOT/'edgelab/funnel/runner.py')
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            h=np.full(24,105);l=np.full(24,95);h[16:]=999999;l[16:]=-999999
            runner=module.FunnelRunner(trade_dates=np.repeat([1,2,3],8),signal_idx=np.arange(24),signal_dir=np.ones(24),high=h,low=l,bid_open=np.full(24,99),ask_open=np.full(24,101),configs=[{'candidate_id':'one','family_id':'f','sl_ticks':3,'tp_ticks':4}],out_dir=out,backend='cpu',holdout_first_date=99)
            result=runner.run_e1_e3(min_trades=1,max_hold_bars=2)
            self.assertEqual(len(seen),2)
            self.assertTrue(all(len(h)==8 and np.max(h)==105 and np.min(l)==95 for h,l in seen))
            self.assertFalse(result['holdout_opened'])
            self.assertFalse(result['promotion_allowed'])
            self.assertFalse(result['isolation']['d2_prices_passed_to_kernel'])
