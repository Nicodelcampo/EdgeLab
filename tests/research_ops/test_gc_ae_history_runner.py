import ast
import base64
import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
import zlib
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from tools.research_ops.confluence import gc_ae_history_runner as R
from tools.research_ops.confluence import package_gc_ae_history as K
from tools.research_ops.confluence import phenomena_history_session as S
from tools.research_ops.audits.review_gc_ae_history import review
from tests.research_ops.test_phenomena import tape
ROOT = Path(__file__).resolve().parents[2]


def plan(): return json.loads((ROOT/R.PLAN).read_bytes())
def calibration(): return json.loads((ROOT/R.CAL_PATH).read_bytes())


class RunnerTests(unittest.TestCase):
    def source(self, source, row, p):
        n = 2200
        x = tape(n); x[0] = row["start_ns"] + np.arange(n,dtype=np.int64)*500000000
        yield SimpleNamespace(ticks=SimpleNamespace(**dict(zip(
            ("ts_ns","sequence","price_ticks","volume","bid_ticks","ask_ticks"),x))))

    def run_synthetic(self, source=None):
        with patch.dict(os.environ,{"KAGGLE_KERNEL_RUN_TYPE":"SYNTHETIC"}), \
             patch.object(R,"one_session",source or self.source):
            return R.run("synthetic",plan(),"/tmp/ae-history-synthetic-private",calibration())

    def test_plan_calibration_and_closed_holdout(self):
        R.validate(plan(),calibration())
        for key, value in (("max_total_ticks",True),("holdout",True),("practical_improvement_brier",.00001),
                           ("evaluation_sessions",["2026-10-01"]),("max_submissions",2)):
            p=plan();p[key]=value
            with self.assertRaises(ValueError):R.validate(p,calibration())
        c=calibration();c["outcomes_used"]=True
        with self.assertRaises(ValueError):R.validate(plan(),c)
        with patch.dict(os.environ,{},clear=True):
            with self.assertRaises(ValueError):R.run("never-open",plan(),"/tmp/private",calibration())
        with patch.dict(os.environ,{"KAGGLE_KERNEL_RUN_TYPE":"SYNTHETIC"}):
            with self.assertRaises(ValueError):R.run("never-open",plan(),"/kaggle/working/private",calibration())

    def test_complete_actual_measurements_fit_before_eval_and_auditor(self):
        seen=[];fitted=[];fit=R.fit_models
        def source(*args):
            seen.append(args[1]["trade_date"])
            yield from self.source(*args)
        def fitter(data):
            fitted.append(len(seen));return fit(data)
        with patch.object(R,"fit_models",fitter):result=self.run_synthetic(source)
        self.assertEqual(seen,plan()["research_dates"])
        self.assertEqual(fitted,[6])
        self.assertEqual(result["total_ticks"],16*2200)
        self.assertEqual(len(result["models"]),14)
        self.assertEqual(len(result["evaluation_sessions"]),10)
        for s in result["training_sessions"]+result["evaluation_sessions"]:
            self.assertTrue(s["clock_only_purge_embargo_applied"])
        raw=(json.dumps(result,indent=2)+"\n").encode()
        package={"source_commit":"a"*40,"bundle_sha256":"b"*64,"plan_sha256":R.digest(plan())}
        boot={**package,"status":"DEVELOPMENT_AE_HISTORY_COMPLETE_NOT_EDGE","exit_code":0,
              "stop_reason":None,"outcomes_computed":True,"ae_history_receipt_sha256":hashlib.sha256(raw).hexdigest(),
              "holdout_opened":False,"raw_exported":False,"pnl_computed":False,"new_quality_audit":False,
              "transport_pin_verified":True}
        verified=review(boot,result,plan(),calibration(),package,raw)
        self.assertEqual(verified["evaluation_sessions"],10)
        for key, value in (("holdout_opened",True),("baseline_equal_session_brier",{"HISTORY":-1}),
                           ("model_feature_counts",{"PRIOR":0}),("total_ticks",1)):
            broken=copy.deepcopy(result);broken[key]=value
            with self.assertRaises((ValueError,KeyError)):review(boot,broken,plan(),calibration(),package,raw)
        broken=copy.deepcopy(result);broken["evaluation_sessions"][0]["history_updates"]-=1
        with self.assertRaises(ValueError):review(boot,broken,plan(),calibration(),package,raw)
        broken=copy.deepcopy(result);broken["primary_results"]["A_TO_E"]["all_usable"]["classification"]="WINNER"
        with self.assertRaises(ValueError):review(boot,broken,plan(),calibration(),package,raw)
        for direction in ("A_TO_E","E_TO_A"):
            a=result["primary_results"][direction]["all_usable"]
            self.assertFalse(a["support_minimum_met"])
            self.assertTrue(a["classification"].startswith("INCONCLUSIVE"))

    def test_empty_eval_report_without_replacement_and_training_required(self):
        excluded=plan()["evaluation_sessions"][0]
        def source(*args):
            if args[1]["trade_date"]!=excluded:yield from self.source(*args)
        result=self.run_synthetic(source)
        self.assertEqual(len(result["evaluation_sessions"]),9)
        self.assertEqual(result["unavailable_evaluation_sessions"][0]["trade_date"],excluded)
        self.assertFalse(result["unavailable_evaluation_sessions"][0]["replacement_selected"])
        def empty(*args):yield from ()
        with self.assertRaises(ValueError):self.run_synthetic(empty)

    def test_clock_purge_advances_history_but_never_reads_future_label(self):
        p=plan();r=p["session_ranges"][0];n=2200;x=tape(n)
        x[0]=r["end_ns"]-1100*10**9+np.arange(n,dtype=np.int64)*500000000
        st=SimpleNamespace(ticks=SimpleNamespace(**dict(zip(
            ("ts_ns","sequence","price_ticks","volume","bid_ticks","ask_ticks"),x))))
        label=S.SecondsResponse.label;seen=[]
        def checked(obj,index,*args,**kw):
            self.assertLess(int(x[0][index]),p["scoring_bounds"][r["trade_date"]]["upper_ns"])
            seen.append(index);return label(obj,index,*args,**kw)
        with patch.object(S.SecondsResponse,"label",checked):
            data=S.session_data(st,r["trade_date"],p,calibration(),time.monotonic())
        self.assertGreater(data["summary"]["excluded_counts"]["CLOCK_ONLY_PURGE_EMBARGO"],0)
        self.assertEqual(data["summary"]["observed_anchors"],data["summary"]["history_updates"])
        self.assertGreater(len(seen),100)

    def test_exact_private_package_dependencies_isolated_startup(self):
        request,receipt=K.build_request(ROOT,url="https://storage.googleapis.com/kagglesdsdata/datasets/synthetic/GC/GC_12-26_ticks_ext.parquet",source_commit="a"*40)
        text=request["request"]["text"];compile(text,"boot","exec")
        self.assertTrue(request["request"]["isPrivate"])
        self.assertFalse(request["request"]["enableGpu"])
        self.assertNotIn("'--asset'",text)
        self.assertIn("ae-history-receipt.json",text)
        tree=ast.parse(text);data=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id=="DATA")
        bundle=json.loads(zlib.decompress(base64.b64decode(data)))
        self.assertIn(R.PLAN,bundle);self.assertIn(R.CAL_PATH,bundle)
        self.assertIn("tools/research_ops/confluence/phenomena_history_models.py",bundle)
        self.assertNotIn("datasets",json.dumps(receipt))
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            for name,rec in bundle.items():
                p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(base64.b64decode(rec["data"]))
            for pkg in ("tools","tools/research_ops","tools/research_ops/confluence"):
                (root/pkg/"__init__.py").touch()
            env=dict(os.environ);env.pop("PYTHONPATH",None);env["OPENBLAS_NUM_THREADS"]="1"
            run=subprocess.run([sys.executable,"-m","tools.research_ops.confluence.gc_ae_history_runner","--help"],cwd=root,env=env,capture_output=True,text=True,timeout=30)
            self.assertEqual(run.returncode,0,run.stderr)
            self.assertIn("--receipt",run.stdout)

    def test_missing_subsets_null_and_descriptive_margin_not_winner(self):
        # Aggregate fixture independent of tape; supported but worsening direction.
        p=plan();sessions=[]
        for i in range(6):
            groups={}
            for direction in ("A_TO_E","E_TO_A"):
                g={"anchors":400,"paired_delta_proxy_minus_history":.002,
                   "paired_delta_proxy_minus_capacity":.001}
                groups[direction]={"all_usable":g,"thin_60s":{"anchors":0}}
            sessions.append({"primary_transition_subsets":groups})
        x=R.summarize(sessions,p)
        for direction in ("A_TO_E","E_TO_A"):
            self.assertTrue(x[direction]["all_usable"]["support_minimum_met"])
            self.assertEqual(x[direction]["all_usable"]["classification"],"NO_PRACTICAL_MARGIN_CROSSING")
            self.assertIsNone(x[direction]["thin_60s"]["minus_capacity"])