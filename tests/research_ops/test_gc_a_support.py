import ast,base64,copy,json,hashlib,os,subprocess,sys,tempfile,unittest,zlib
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from tools.research_ops.confluence import gc_a_support_diagnostic as R
from tools.research_ops.confluence import package_gc_a_support as K
from tools.research_ops.confluence import phenomena_models as M
from tools.research_ops.audits.review_gc_a_support import review
from tests.research_ops.test_phenomena import tape
from tests.research_ops.test_phenomena_science import row
ROOT=Path(__file__).resolve().parents[2]
def plan():return json.loads((ROOT/R.PLAN).read_bytes())
def cal():return json.loads((ROOT/R.CAL_PATH).read_bytes())
class SupportTests(unittest.TestCase):
 def source(self,source,r,p):
  a=tape(2200);a[0]=r["start_ns"]+np.arange(2200,dtype=np.int64)*500000000
  yield SimpleNamespace(ticks=SimpleNamespace(**dict(zip(("ts_ns","sequence","price_ticks","volume","bid_ticks","ask_ticks"),a))))
 def execute(self):
  with patch.dict(os.environ,{"KAGGLE_KERNEL_RUN_TYPE":"SYNTHETIC"}),patch.object(R,"read_session",self.source),patch.object(M,"fit",side_effect=AssertionError("no models")):
   return R.run("synthetic",plan(),"/tmp/private-support",cal())
 def test_no_outcomes_complete_training_and_recount(self):
  from tools.research_ops.confluence.phenomena_response import SecondsResponse
  with patch.object(SecondsResponse,"label",side_effect=AssertionError("no outcomes")),patch.object(SecondsResponse,"__init__",side_effect=AssertionError("no response construction")):
   r=self.execute()
  self.assertEqual(r["total_ticks"],6*2200);self.assertEqual(len(r["sessions"]),6);self.assertFalse(r["evaluation_read"]);self.assertFalse(r["outcomes_computed"])
  raw=(json.dumps(r,indent=2)+"\n").encode();pkg={"source_commit":"a"*40,"bundle_sha256":"b"*64,"plan_sha256":R.digest(plan())}
  boot={**pkg,"status":"TARGET_FREE_TRAINING_SUPPORT_COMPLETE_NOT_EDGE","exit_code":0,"stop_reason":None,"a_support_receipt_sha256":hashlib.sha256(raw).hexdigest(),"transport_pin_verified":True,**{k:False for k in ("outcomes_requested","outcomes_computed","raw_exported","holdout_opened","pnl_computed","new_quality_audit")}}
  self.assertTrue(review(boot,r,plan(),cal(),pkg,raw)["status"].startswith("PASS_"))
  for k,v in (("thresholds_changed",True),("total_ticks",1),("evaluation_read",True)):
   x=copy.deepcopy(r);x[k]=v
   with self.assertRaises(ValueError):review(boot,x,plan(),cal(),pkg,raw)
  x=copy.deepcopy(r);cell=next(iter(x["total_training"]["cells"].values()));cell["joint_condition_mask_counts"][0]+=1
  with self.assertRaises(ValueError):review(boot,x,plan(),cal(),pkg,raw)
 def test_plan_hash_holdout_and_threshold_changes_rejected(self):
  R.validate(plan(),cal())
  for k,v in (("evaluation_read",True),("outcomes_requested",True),("training_sessions",["2026-10-01"]),("new_calibration",True),("wall_seconds",1200)):
   p=plan();p[k]=v
   with self.assertRaises(ValueError):R.validate(p,cal())
  c=cal();c["cells"]["OTHER:1"]["stall_range_max"]+=1
  with self.assertRaises(ValueError):R.validate(plan(),c)
 def test_conjunct_bruteforce_masks(self):
  c=cal();threshold=c["cells"]["OTHER:1"];census=R.Census();start=plan()["session_ranges"][0]["start_ns"]
  for mask in range(32):
   x=row();x["trade_date"]=plan()["training_sessions"][0];x["timestamp_ns"]=start+(mask+1)*5*10**9
   pair=x["windows"]["20"];current=pair["current"];prior=pair["prior"]
   current["buy_volume"]=threshold["current_pressure_q80"]+(1 if mask&1 else -1)
   prior["buy_volume"]=threshold["prior_pressure_q80"]+(1 if mask&2 else -1)
   pair["directed_progress_ticks"]=threshold["stall_abs_progress_max"]+(0 if mask&4 else 1)
   current["range_midpoint_ticks"]=threshold["stall_range_max"]+(0 if mask&8 else 1)
   current["path_midpoint_ticks"]=threshold["stall_path_max"]+(0 if mask&16 else 1)
   census.add(x,c,plan()["training_sessions"])
  result=census.finish()["cells"]["OTHER:1"]
  self.assertEqual(result["joint_condition_mask_counts"],[1]*32)
  self.assertEqual(set(result["condition_counts"].values()),{16})
  self.assertEqual(set(result["passes_all_other_conditions"].values()),{2})
  self.assertEqual(result["absorption_conjunction_anchors"],1)
 def test_package_boot_no_outcomes_and_isolated_startup(self):
  req,pkg=K.build_request(ROOT,url="https://storage.googleapis.com/kagglesdsdata/datasets/synthetic/GC/GC_12-26_ticks_ext.parquet",source_commit="a"*40)
  s=req["request"]["text"];compile(s,"supportboot","exec");self.assertIn("'outcomes_requested':False",s);self.assertIn("state['outcomes_computed']=False",s);self.assertFalse(pkg["outcomes_requested"]);self.assertTrue(req["request"]["isPrivate"])
  tree=ast.parse(s);data=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id=="DATA")
  bundle=json.loads(zlib.decompress(base64.b64decode(data)))
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)
   for name,v in bundle.items():
    p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(base64.b64decode(v["data"]))
   for pkg in ("tools","tools/research_ops","tools/research_ops/confluence"):(root/pkg/"__init__.py").touch()
   env=dict(os.environ);env.pop("PYTHONPATH",None);env["OPENBLAS_NUM_THREADS"]="1"
   q=subprocess.run([sys.executable,"-m","tools.research_ops.confluence.gc_a_support_diagnostic","--help"],cwd=root,env=env,text=True,capture_output=True,timeout=30)
   self.assertEqual(q.returncode,0,q.stderr)
 def test_kaggle_only_and_output_root(self):
  with patch.dict(os.environ,{},clear=True):
   with self.assertRaises(ValueError):R.run("neverread",plan(),"/tmp/private",cal())
  with patch.dict(os.environ,{"KAGGLE_KERNEL_RUN_TYPE":"SYNTHETIC"}):
   with self.assertRaises(ValueError):R.run("neverread",plan(),"/kaggle/working/private",cal())