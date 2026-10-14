import ast,base64,copy,hashlib,json,os,subprocess,sys,tempfile,unittest,zlib
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from tools.research_ops.confluence import gc_pressure_progress as R
from tools.research_ops.confluence import package_gc_pressure_progress as K
from tools.research_ops.confluence import gc_a_support_diagnostic as OLD
from tools.research_ops.audits.review_gc_pressure_progress import review,check_census
from tests.research_ops import test_gc_a_support as fixtures
cal=fixtures.cal
from tests.research_ops.test_phenomena_science import row
ROOT=Path(__file__).resolve().parents[2]
def plan():return json.loads((ROOT/R.PLAN).read_bytes())
class AtlasTests(unittest.TestCase):
 def execute(self):
  with patch.dict(os.environ,{'KAGGLE_KERNEL_RUN_TYPE':'SYNTHETIC'}),patch.object(R,'read_session',fixtures.SupportTests().source):return R.run('synthetic',plan(),'/tmp/private-atlas',cal())
 def test_full_run_no_outcomes_and_unchanged_population(self):
  from tools.research_ops.confluence.phenomena_response import SecondsResponse
  from tools.research_ops.confluence import phenomena_models as models
  with patch.object(SecondsResponse,'__init__',side_effect=AssertionError('no labels')),patch.object(models,'fit',side_effect=AssertionError('no fit')):r=self.execute()
  previous=fixtures.SupportTests().execute();raw=(json.dumps(r,indent=2)+'\n').encode();pkg={'source_commit':'a'*40,'bundle_sha256':'b'*64,'plan_sha256':R.PLAN_SHA}
  boot={**pkg,'status':r['status'],'exit_code':0,'stop_reason':None,'pressure_progress_receipt_sha256':hashlib.sha256(raw).hexdigest(),'transport_pin_verified':True,**{k:False for k in ('outcomes_requested','outcomes_computed','raw_exported','holdout_opened','pnl_computed','new_quality_audit')}}
  z=review(boot,r,plan(),cal(),pkg,raw,previous);self.assertTrue(z['previous_prelabel_census_exact']);self.assertFalse(z['evaluation_authorized'])
  for k,v in [('outcomes_computed',True),('evaluation_read',True),('total_ticks',1)]:
   x=copy.deepcopy(r);x[k]=v
   with self.assertRaises(ValueError):review(boot,x,plan(),cal(),pkg,raw,previous)
  x=copy.deepcopy(r);next(iter(x['total_training']['cells'].values()))['continuous_metrics']['pressure_normalized']['mean']+=1
  with self.assertRaises(ValueError):review(boot,x,plan(),cal(),pkg,raw,previous)
  x=copy.deepcopy(r);next(iter(x['total_training']['cells'].values()))['pressure_progress_counts'][0][0]+=1
  with self.assertRaises(ValueError):check_census(x['total_training'])
 def test_fixed_grid_all_cells_and_nonoverlap_selection(self):
  p=plan();c=cal();a=R.Atlas(p);start=p['session_ranges'][0]['start_ns'];rows=[]
  for i in range(20):
   x=row();x['trade_date']=p['training_sessions'][0];x['timestamp_ns']=start+(i+1)*40*10**9
   pair=x['windows']['20'];pressure=[.25,.75,1.5,3.][i//5];progress=[-5.,-3.,0.,3.,5.][i%5]
   pair['current']['buy_volume']=pressure*c['cells']['OTHER:1']['current_pressure_q80'];pair['directed_progress_ticks']=progress;pair['prior_directed_progress_ticks']=progress;pair['pressure_ratio']=pair['current']['buy_volume']/pair['prior']['buy_volume'];rows.append(x);a.add(x,c)
  z=a.finish();check_census(z);self.assertEqual(z['nonoverlap_windows'],20);self.assertEqual(z['cells']['OTHER:1']['pressure_progress_counts'],[[1]*5]*4)
  self.assertEqual([R.progress_bucket(x,p) for x in [-4.,-2.,2.,4.]],[1,2,3,4])
  # Re-run dense anchors at 5sec spacing; select by date, not separately by cell.
  b=R.Atlas(p)
  for i,x in enumerate(rows):x=copy.deepcopy(x);x['timestamp_ns']=start+(i+1)*5*10**9;b.add(x,c)
  self.assertEqual(b.finish()['nonoverlap_windows'],3)
 def test_plan_changes_and_bad_scale_rejected(self):
  for k,v in [('nonoverlap_seconds',20),('outcomes_requested',True),('training_sessions',['2026-10-01']),('pressure_bin_edges',[1,2,3])]:
   p=plan();p[k]=v
   with self.assertRaises(ValueError):R.validate(p,cal())
  c=cal();c['cells']['OTHER:1']['current_pressure_q80']=0
  with self.assertRaises(ValueError):R.validate(plan(),c)
 def test_unknown_excluded_and_order_guard(self):
  a=R.Atlas(plan());x=row();x['trade_date']=plan()['training_sessions'][0];x['timestamp_ns']=plan()['session_ranges'][0]['start_ns']+10**9;x['windows']['20']['status']='UNKNOWN_PAIR';a.add(x,cal())
  z=a.finish();self.assertEqual(z['state_counts']['UNKNOWN'],1);self.assertEqual(z['eligible_anchors'],0);check_census(z)
  with self.assertRaises(ValueError):a.add(x,cal())
 def test_bundle_isolated_startup_and_private_cpu(self):
  req,pkg=K.build_request(ROOT,url='https://storage.googleapis.com/kagglesdsdata/datasets/synthetic/GC/GC_12-26_ticks_ext.parquet',source_commit='a'*40)
  s=req['request']['text'];compile(s,'atlas','exec');self.assertIn('confluence.gc_pressure_progress',s);self.assertIn("state['outcomes_computed']=False",s);self.assertTrue(req['request']['isPrivate']);self.assertFalse(pkg['outcomes_requested'])
  tree=ast.parse(s);data=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='DATA');bundle=json.loads(zlib.decompress(base64.b64decode(data)))
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)
   for name,v in bundle.items():p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(base64.b64decode(v['data']))
   env=dict(os.environ);env.pop('PYTHONPATH',None);env['OPENBLAS_NUM_THREADS']='1'
   z=subprocess.run([sys.executable,'-m','tools.research_ops.confluence.gc_pressure_progress','--help'],cwd=root,env=env,capture_output=True,text=True,timeout=30);self.assertEqual(z.returncode,0,z.stderr)
 def test_kaggle_only_outputs_and_nonfinite(self):
  with patch.dict(os.environ,{},clear=True):
   with self.assertRaises(ValueError):R.run('never',plan(),'/tmp/private',cal())
  with patch.dict(os.environ,{'KAGGLE_KERNEL_RUN_TYPE':'SYNTHETIC'}):
   with self.assertRaises(ValueError):R.run('never',plan(),'/kaggle/working/private',cal())
  a=R.Atlas(plan());x=row();x['trade_date']=plan()['training_sessions'][0];x['timestamp_ns']=plan()['session_ranges'][0]['start_ns']+10**9;x['windows']['20']['pressure_ratio']=float('nan')
  with self.assertRaises(ValueError):a.add(x,cal())
if __name__=='__main__':unittest.main()
