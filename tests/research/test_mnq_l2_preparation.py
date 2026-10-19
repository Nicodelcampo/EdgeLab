import ast
import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2] / "tools"))
from pathlib import Path
from types import SimpleNamespace
import unittest
import tempfile
import json
from unittest.mock import patch
import numpy as np
import pandas as pd
from streaming_escalonadas import PriceConfirmed, PARAMS
from mirror_landmark import Candidate
import mnq_l2_prepare as E
import gc_l2_fixed_price_probe as P0


def oracle():
    """Load exact repo pure-Python functions; no numba or unrelated viewer imports."""
    root=Path(__file__).parent/"source/tools"
    if not root.exists():root=Path(__file__).resolve().parents[2]/"tools"
    ns={"np":np,"TICK":.25,"CONF_TICKS":2}
    tree=ast.parse((root/"peaks_rule.py").read_text())
    functions=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ("backfill","pivots")]
    exec(compile(ast.Module(body=functions,type_ignores=[]),"repo_peaks_pure","exec"),ns)
    ns["R"]=SimpleNamespace(backfill=ns["backfill"],pivots=ns["pivots"])
    tree=ast.parse((root/"escalonadas_det.py").read_text())
    functions=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ("pasa","chains_px","detectar_px")]
    exec(compile(ast.Module(body=functions,type_ignores=[]),"repo_detector_pure","exec"),ns)
    return ns["detectar_px"]


class TestIncrementalGeometry(unittest.TestCase):
    def compare_prefix(self,h,l,c,t):
        detector=PriceConfirmed()
        original=oracle()
        f={k:v for k,v in PARAMS.items() if k!="confirm_ticks"}
        observed=[]
        for j in range(len(h)):
            fresh=detector.append(h[j],l[j],c[j],t[j])
            if j<2*PARAMS["w"]:continue
            cd={"h":np.asarray(h[:j+1],float)*.25,
                "l":np.asarray(l[:j+1],float)*.25,
                "c":np.asarray(c[:j+1],float)*.25,
                "t":np.asarray(t[:j+1],float)}
            ref=original(cd,f,X=PARAMS["confirm_ticks"])
            expected=sorted((z["kind"],z["det_i"],int(round(z["det_nivel"]/.25)),
                             tuple(q[0] for q in z["picos"][:z["det_idx"]+1]))
                            for z in ref if z["det_i"]==j)
            # Drawing geometry may extend after detection; known picos are the
            # actual prefix now, compare event level/detection timestamp separately.
            expected_simple=sorted((a,b,c) for a,b,c,_ in expected)
            actual=sorted((z["kind"],z["det_i"],z["det_nivel_tick"]) for z in fresh)
            self.assertEqual(actual,expected_simple, f"prefix {j}")
            observed.extend(fresh)
        return observed

    def test_crafted_three_peaks(self):
        h=[970,980,1000,950,940,990,940,930,980,920]
        l=[900,910,940,900,890,930,890,880,920,870]
        ev=self.compare_prefix(h,l,[(a+b)//2 for a,b in zip(h,l)],list(range(len(h))))
        self.assertTrue(any(z["kind"]=="H" and z["det_i"]==9 for z in ev))

    def test_random_every_prefix_parity(self):
        for seed in range(4):
            rng=np.random.default_rng(seed);n=140
            center=10000+np.cumsum(rng.integers(-12,13,n))
            h=(center+rng.integers(15,65,n)).tolist()
            l=(center-rng.integers(15,65,n)).tolist()
            self.compare_prefix(h,l,center.tolist(),list(range(n)))

    def test_future_does_not_rewrite_event(self):
        h=[970,980,1000,950,940,990,940,930,980,920];l=[900,910,940,900,890,930,890,880,920,870]
        d=PriceConfirmed()
        for j in range(len(h)):d.append(h[j],l[j],(h[j]+l[j])//2,j)
        saved=[dict(x) for x in d.events]
        d.append(1100,1000,1050,11)
        self.assertEqual(d.events[:len(saved)],saved)

    def test_tick_scale_constants(self):
        self.assertEqual(PARAMS["confirm_ticks"],round(2*12.42))
        self.assertEqual(PARAMS["min_pull"],round(5*12.42))
        self.assertEqual(PARAMS["max_step"],round(2*12.42))

    def test_clock_inversion_stops(self):
        d=PriceConfirmed();d.append(10,5,7,10)
        with self.assertRaises(ValueError):d.append(10,5,7,9)

    def test_gap_resets_chain(self):
        d=PriceConfirmed()
        h=[970,980,1000,950,940,990,940,930,980,920];l=[900,910,940,900,890,930,890,880,920,870]
        for j in range(len(h)):d.append(h[j],l[j],(h[j]+l[j])//2,j if j<6 else j+2000)
        self.assertFalse(d.events)


class TestMirrorLandmark(unittest.TestCase):
    def test_up_first_leg_down_second(self):
        d=Candidate("x",100,200,1,10)
        self.assertIsNone(d.observe(175,11))
        self.assertEqual(d.observe(150,12)["available_row"],12)

    def test_down_first_leg_up_second(self):
        d=Candidate("x",200,100,1,10)
        self.assertIsNone(d.observe(125,11))
        self.assertEqual(d.observe(150,12)["available_row"],12)

    def test_cannot_backdate_before_b_confirmation(self):
        d=Candidate("x",100,200,1,10)
        self.assertIsNone(d.observe(140,5))
        event=d.observe(140,10)
        self.assertEqual(event["available_row"],10)
        self.assertEqual(event["landmark_timing"],"ALREADY_REACHED_AT_B_CONFIRMATION")

    def test_failed_attempt_no_landmark_but_retained(self):
        d=Candidate("x",100,200,1,10)
        self.assertIsNone(d.observe(210,11));self.assertTrue(d.invalidated)
        self.assertIsNone(d.observe(150,12))

    def test_one_landmark_only(self):
        d=Candidate("x",100,200,1,10)
        saved=d.observe(150,11)
        self.assertIsNone(d.observe(100,12));self.assertEqual(saved["available_row"],11)

    def test_zero_and_future_a_rejected(self):
        with self.assertRaises(ValueError):Candidate("x",100,100,1,10)
        with self.assertRaises(ValueError):Candidate("x",100,200,11,10)

    def test_geometry_cannot_be_rewritten_and_failed_state_persists(self):
        d=Candidate("x",100,200,1,10)
        d.observe(210,11)
        self.assertEqual(d.snapshot()["status"],"INVALID_BEFORE_LANDMARK")
        d.b_tick=220
        with self.assertRaisesRegex(ValueError,"GEOMETRY_CHANGED"):d.observe(150,12)


class TestExportAvailability(unittest.TestCase):
    def book(self):
        path=Path(__file__).parent/"source/edgelab/research/l2_phase0.py"
        if not path.exists():path=Path(__file__).resolve().parents[2]/"edgelab/research/l2_phase0.py"
        return P0.load_book_module(path)

    def fixture(self):
        rows=[]
        for side in (0,1):
            for level in range(10):
                rows.append(dict(source_row=len(rows),ts_us=0,side=side,operation=0,
                                 level=level,price_tick=20001+level if side==0 else 20000-level,size=10))
        rows.append(dict(source_row=170,ts_us=60_000_000,side=0,operation=1,
                         level=0,price_tick=20001,size=99))
        a=pd.DataFrame([dict(source_row=i,ts_us=60_000_000,side=2,price_tick=20000,size=1)
                        for i in range(20,170)])
        return [{"file":"synthetic","frames":{"l1_quotes":a,"l2_depth":pd.DataFrame(rows)}}]

    def test_wait_for_end_timestamp_group(self):
        with tempfile.TemporaryDirectory() as tmp:
            q,bars,_=E.process(self.fixture(),self.book(),tmp,"fixture")
        self.assertEqual(q["bars"],1)
        self.assertEqual(bars[0]["bar_close_row"],169)
        self.assertEqual(bars[0]["available_row"],170)
        self.assertEqual(bars[0]["ask3_size"],119)

    def test_partial_bar_no_fabricated_signal(self):
        f=self.fixture();f[0]["frames"]["l1_quotes"]=f[0]["frames"]["l1_quotes"].iloc[:149]
        with tempfile.TemporaryDirectory() as tmp:
            q,bars,signals=E.process(f,self.book(),tmp,"fixture")
        self.assertEqual(q["partial_prints_at_end"],149)
        self.assertFalse(bars);self.assertFalse(signals)

    def test_invalid_book_features_not_zero_or_pass(self):
        f=E.features([[],[]],False,20000,0,10)
        self.assertIsNone(f["defense_mask"])
        self.assertIsNone(f["spread_ticks"])

    def test_zero_quantity_not_defense(self):
        asks=[[20001+i,0] for i in range(10)];bids=[[20000-i,10] for i in range(10)]
        self.assertFalse(E.features([asks,bids],True,20001,0,2)["defense_mask"])
        self.assertIsNone(E.features([asks,bids],True,30000,0,2)["defense_mask"])


class TestNativeInput(unittest.TestCase):
    def test_price_removed_schema_and_hash_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp)/"MNQ_09-26"
            for k in ("l1_quotes","l2_depth","manifests"):(base/k).mkdir(parents=True)
            fixture=TestExportAvailability().fixture()[0]["frames"]
            outputs={}
            for kind,df in fixture.items():
                p=base/kind/"20260701.parquet";df.to_parquet(p,index=False)
                outputs[kind]={"bytes":p.stat().st_size,"rows":len(df),"sha256":E.sha(p)}
            (base/"manifests/20260701.manifest.json").write_text(json.dumps({
                "conversion":{"tick_size":.25,"subsecond_unit":"100ns_ticks"},"outputs":outputs}))
            frames,_=E.checked_file(tmp,"MNQ_09-26","20260701",.25)
            self.assertNotIn("price",frames["l2_depth"])
            p=base/"l1_quotes/20260701.parquet"
            with p.open("ab") as f:f.write(b"changed")
            with self.assertRaisesRegex(ValueError,"HASH_OR_SIZE_FAIL"):
                E.checked_file(tmp,"MNQ_09-26","20260701",.25)

    def test_overlap_joint_cut_retains_new_snapshot(self):
        first=TestExportAvailability().fixture()[0]["frames"]
        second={k:v.copy() for k,v in first.items()}
        for v in second.values():v["ts_us"]+=30_000_000
        with patch.object(E,"checked_file",side_effect=[(first,{}),(second,{})]):
            parts,q=E.session_input("unused",{"contract":"MNQ_09-26","files":["a","b"]})
        self.assertTrue(all((v["ts_us"]<30_000_000).all() for v in parts[0]["frames"].values()))
        self.assertEqual(len(parts[1]["frames"]["l2_depth"]),len(second["l2_depth"]))
        self.assertTrue((parts[1]["frames"]["l2_depth"]["source_row"]>=10**12).all())


if __name__=="__main__":unittest.main(verbosity=2)