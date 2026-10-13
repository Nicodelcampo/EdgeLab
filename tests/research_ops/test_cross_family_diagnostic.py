import ast,base64,json,os,tempfile,unittest,zlib,subprocess
from pathlib import Path
from unittest.mock import patch
from tools.research_ops.confluence.cross_family_diagnostics import safe_failure,reasons
from tools.research_ops.confluence.cross_family_diagnostic import validate,PLAN,run
from tools.research_ops.confluence.package_crossfamily_diagnostic import build_request
from tools.research_ops.confluence.cross_family_pilot import PLAN as SCIENCE_PLAN
ROOT=Path(__file__).resolve().parents[2]
class DiagnosticTests(unittest.TestCase):
 def test_unknown_exception_never_exports_arbitrary_text(self):
  x=safe_failure(ValueError('SECRET_PRICE_100500_RAW_ROW'),{'substage':'PRIVATE_THING','profile_index':99,'capture_records_by_kind':{'raw_price':123}})
  self.assertNotIn('SECRET',json.dumps(x));self.assertNotIn('PRIVATE_THING',json.dumps(x));self.assertEqual(x['reason_code'],'UNCLASSIFIED_STATIC_REASON');self.assertEqual(x['capture_records_by_kind'],{});self.assertIsNone(x['profile_index'])
 def test_static_capture_error_allowlisted_with_bounded_context(self):
  x=safe_failure(ValueError('nine config capture capacity no truncation'),{'substage':'CAPTURE','profile_index':3,'capture_records_retained':400001,'capture_records_by_kind':{'BIRTH':20,'TOUCH':399981}})
  self.assertEqual(x['reason_code'],reasons()['nine config capture capacity no truncation']);self.assertEqual(x['native_substage'],'CAPTURE');self.assertEqual(x['profile_index'],3)
 def test_exact_plan_no_labels_or_scope_relaxation(self):
  p=json.loads((ROOT/PLAN).read_bytes());validate(p);self.assertFalse(p['outcomes']);self.assertEqual(p['stop_trade_date'],'2026-06-16');self.assertEqual(p['retention_policy'],'ORIGINAL_ALL_CAPTURE_KINDS_TO_REPRODUCE_NOT_PATCHED');p['outcomes']=True
  with self.assertRaises(ValueError):validate(p)
 def test_real_source_requires_kaggle(self):
  with patch.dict(os.environ,{},clear=True):
   with self.assertRaises(ValueError):run('unused',json.loads((ROOT/PLAN).read_bytes()))
 def test_package_false_outcomes_isolated_dependency_closure(self):
  req,receipt=build_request(ROOT,url='https://storage.googleapis.com/kagglesdsdata/datasets/1/2/MNQ/MNQ_09-26_ticks_ext.parquet',source_commit='1'*40);text=req['request']['text'];self.assertFalse(receipt['outcomes_requested']);self.assertIn("'outcomes_requested':False",text);self.assertNotIn("'outcomes_requested':True",text);self.assertIn("state['outcomes_computed']=False",text);self.assertIn('DIAGNOSTIC_EXECUTION_COMPLETE_NOT_SCIENTIFIC_RESULT',text)
  data=next(ast.literal_eval(n.value) for n in ast.parse(text).body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='DATA');files=json.loads(zlib.decompress(base64.b64decode(data)));self.assertIn(SCIENCE_PLAN,files)
  with tempfile.TemporaryDirectory() as td:
   root=Path(td)
   for name,r in files.items():p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(base64.b64decode(r['data']))
   for name in ('tools','tools/research_ops','tools/research_ops/confluence'):(root/name/'__init__.py').touch()
   r=subprocess.run([os.sys.executable,'-m','tools.research_ops.confluence.cross_family_diagnostic','--help'],cwd=root,env={**os.environ,'PYTHONPATH':str(root)},capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stderr)
if __name__=='__main__':unittest.main()
