import unittest,copy,json,math,tempfile,hashlib
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from tools.research_ops.confluence import phenomena_models as M
from tools.research_ops.confluence import phenomena_model_pilot as P
from tools.research_ops.confluence import package_phenomena_model as K
from tools.research_ops.confluence.phenomena_states import classify,classify_components
from tests.research_ops.test_phenomena_science import row,cal
from tests.research_ops.test_phenomena import tape
ROOT=Path(__file__).resolve().parents[2]
def plan():return json.loads((ROOT/K.PLAN).read_bytes())
def frozen():return json.loads((ROOT/P.CAL_PATH).read_bytes())
class ModelTests(unittest.TestCase):
 def test_old_classifier_unchanged(self):
  rng=np.random.default_rng(32);c=cal()
  for _ in range(500):
   r=row();p=r['windows']['20'];p['current']['buy_volume']=float(rng.integers(0,60));p['prior']['buy_volume']=float(rng.integers(1,60));p['pressure_ratio']=p['current']['buy_volume']/p['prior']['buy_volume'];p['trade_count_ratio']=float(rng.random()*2);p['directed_progress_ticks']=float(rng.integers(-15,16));p['prior_directed_progress_ticks']=float(rng.integers(-10,15));p['current']['range_midpoint_ticks']=float(rng.integers(0,10));p['current']['path_midpoint_ticks']=float(rng.integers(0,20))
   x=classify(r,c);z=p['current'];prior=p['prior'];A=z['buy_volume']>=10 and prior['buy_volume']>=10 and abs(p['directed_progress_ticks'])<=2 and z['range_midpoint_ticks']<=4 and z['path_midpoint_ticks']<=8;E=prior['buy_volume']>=10 and p['prior_directed_progress_ticks']>=4 and p['pressure_ratio']<=.5 and p['trade_count_ratio']<=.5
   self.assertEqual(x['state'],'BOTH' if A and E else 'A_ONLY' if A else 'E_ONLY' if E else 'NEITHER')
   self.assertEqual(x,classify_components(p,c['cells']['OTHER:1']))
 def test_calibration_immutable(self):
  M.verified_calibration(frozen());c=frozen();c['cells']['RTH:1']['stall_abs_progress_max']=1
  with self.assertRaises(ValueError):M.verified_calibration(c)
 def test_future_clock_and_old_clock_separate(self):
  r=row();r['trade_date']=M.EVAL[0];r['timestamp_ns']=plan()['session_ranges'][2]['start_ns']+10**9
  self.assertEqual(M.phase_key(r),'OTHER:1');self.assertNotEqual(M.state(r,frozen())['state'],'UNKNOWN')
  with self.assertRaises(ValueError):classify(r,cal())
  for date in ('2026-10-01','2026-06-20'):
   r['trade_date']=date
   with self.assertRaises(ValueError):M.phase_key(r)
 def test_mislabeled_clock(self):
  r=row();r['trade_date']=M.EVAL[0]
  with self.assertRaises(ValueError):M.phase_key(r)
 def test_plan_mutations(self):
  P.validate_plan(plan())
  for key,val in [('ridge_lambda',.1),('holdout',True),('max_total_ticks',True),('zone_detectors',True),('models',list(M.MODELS)[1:]),('training_sessions',list(M.EVAL[:2]))]:
   p=plan();p[key]=val
   with self.assertRaises(ValueError):P.validate_plan(p)
  p=plan();p['session_ranges'][2]['start_ns']+=1
  with self.assertRaises(ValueError):P.validate_plan(p)
 def test_ridge_reference(self):
  rng=np.random.default_rng(112);x=rng.normal(size=(100,4));y=rng.integers(0,3,100);w=np.ones(100)/100;m=M.fit(x,y,w);z=np.column_stack((np.ones(100),(x-m['mean'])/m['scale']));pen=np.eye(5)*.01;pen[0,0]=0
  ref=np.linalg.inv(z.T@z/100+pen)@(z.T@np.eye(3)[y]/100)
  np.testing.assert_allclose(ref,m['coef'],atol=1e-12);np.testing.assert_allclose(m['mean'],x.mean(axis=0))
 def test_no_eval_refit_and_constant_feature(self):
  x=np.column_stack((np.arange(100),np.ones(100)));y=np.arange(100)%3;m=M.fit(x,y,np.ones(100));old=m['mean'].copy();p=M.predict(m,np.array([[1e10,1.],[-1e10,1.]]));np.testing.assert_equal(old,m['mean']);np.testing.assert_allclose(p.sum(axis=1),1);self.assertTrue(np.isfinite(p).all());self.assertEqual(m['scale'][1],1.)
 def test_brier_reference_and_bounds(self):
  p=np.array([[1,0,0],[0,1,0],[.2,.3,.5]]);y=np.array([0,0,2]);np.testing.assert_allclose(M.brier(p,y),[0,2,.38])
  for q in (np.array([[2,0,-1]]),np.array([[.3,.3,.3]]),np.array([[math.nan,0,1]])):
   with self.assertRaises(ValueError):M.brier(q,np.array([0]))
 def test_equal_session_fit(self):
  rng=np.random.default_rng(52);tr=[]
  for n,label in ((100,0),(400,1)):
   tr.append((rng.normal(size=(n,len(M.FEATURES))),np.zeros((n,2)),np.zeros((n,2)),np.full(n,label)))
  models,prior,ref=P.fit_models(tr);np.testing.assert_allclose(prior,[.5,.5,0]);self.assertEqual(len(models['CONTINUOUS_AE']['mean']),len(models['CONTINUOUS_CC']['mean']));self.assertEqual(len(models['CONTINUOUS']['mean']),len(M.FEATURES))
 def test_fit_invalid(self):
  for x,y,w in [(np.ones((10,2)),np.ones(10)*.5,np.ones(10)),(np.ones((10,2)),np.ones(10,dtype=int)*3,np.ones(10)),(np.ones((10,2))*np.nan,np.ones(10,dtype=int),np.ones(10)),(np.ones((10,2)),np.ones(10,dtype=int),np.zeros(10))]:
   with self.assertRaises(ValueError):M.fit(x,y,w)
 def test_common_scoring_identity(self):
  rng=np.random.default_rng(14);n=200;data=(rng.normal(size=(n,len(M.FEATURES))),rng.normal(size=(n,2)),rng.integers(0,2,(n,2)),rng.integers(0,3,n),np.array(['RTH:1']*n),np.array(['NEITHER']*n),{})
  models,prior,ref=P.fit_models([data[:4],data[:4]]);s=P.score(data,models,prior,ref);self.assertEqual(s['scores']['anchors'],n);self.assertEqual(len(s['scores']['mean_brier']),6);self.assertAlmostEqual(s['paired_delta_AE_minus_CC'],s['scores']['mean_brier']['CONTINUOUS_AE']-s['scores']['mean_brier']['CONTINUOUS_CC'])
 def test_package_compiles_and_private(self):
  url='https://storage.googleapis.com/kagglesdsdata/datasets/synthetic/MNQ/MNQ_09-26_ticks_ext.parquet';request,receipt=K.build_request(ROOT,url=url,source_commit='a'*40);text=request['request']['text'];compile(text,'boot','exec');self.assertIn('confluence.phenomena_model_pilot',text);self.assertIn('model-receipt.json',text);self.assertIn("state['outcomes_computed']=True",text);self.assertEqual(request['request']['sessionTimeoutSeconds'],3600);self.assertTrue(request['request']['isPrivate']);self.assertFalse(receipt['submitted']);self.assertNotIn(url,json.dumps(receipt))
 def test_full_synthetic_shared_pass(self):
  p=plan();seen=[];fit_seen=[];original=P.fit_models
  def fitter(data):
   fit_seen.append(len(seen));return original(data)
  def source(src,r,p):
   seen.append(r['trade_date']);a=tape(2200);a[0]=r['start_ns']+np.arange(2200,dtype=np.int64)*500000000
   yield SimpleNamespace(ticks=SimpleNamespace(**dict(zip(('ts_ns','sequence','price_ticks','volume','bid_ticks','ask_ticks'),a))))
  with patch.dict('os.environ',{'KAGGLE_KERNEL_RUN_TYPE':'SYNTHETIC'}),patch.object(P,'one_session',source),patch.object(P,'fit_models',fitter):result=P.run('synthetic',p,'/tmp/model-private',frozen())
  from tools.research_ops.audits.review_phenomena_models import review
  body=json.dumps(result).encode();package={'source_commit':'a'*40,'bundle_sha256':'b'*64,'plan_sha256':P.digest(p)};boot={**package,'status':'DEVELOPMENT_MODEL_COMPLETE_NOT_EDGE','exit_code':0,'stop_reason':None,'outcomes_computed':True,'model_receipt_sha256':hashlib.sha256(body).hexdigest()}
  verified=review(boot,result,p,package,body);self.assertTrue(verified['status'].startswith('PASS_'))
  for key,value in (('mean_session_brier',{'PRIOR':-1}),('confirmation',True),('calibration_sha256','a'*64)):
   broken=copy.deepcopy(result);broken[key]=value
   with self.assertRaises((ValueError,KeyError)):review(boot,broken,p,package,body)
  broken=copy.deepcopy(result);broken['evaluation_sessions'][0]['scores']['anchors']+=1
  with self.assertRaises(ValueError):review(boot,broken,p,package,body)
  self.assertEqual(seen,list(M.TRAIN+M.EVAL));self.assertEqual(fit_seen,[2]);self.assertEqual(len(result['evaluation_sessions']),12);self.assertEqual(result['total_ticks'],14*2200);self.assertFalse(result['confirmation']);self.assertFalse(result['holdout_opened']);self.assertEqual(result['scored_model_count'],6)
  for session in result['training_sessions']+result['evaluation_sessions']:
   self.assertEqual(session['anchors'],session['common_usable_anchors']+sum(session['excluded_counts'].values()));self.assertEqual(sum(session['common_response_counts'].values()),session['common_usable_anchors'])
 def test_missing_session_failure_and_no_private_output(self):
  with patch.dict('os.environ',{'KAGGLE_KERNEL_RUN_TYPE':'SYNTHETIC'}):
   with self.assertRaises(ValueError):P.run('synthetic',plan(),'/kaggle/working/raw',frozen())
  with patch.dict('os.environ',{'KAGGLE_KERNEL_RUN_TYPE':'SYNTHETIC'}),patch.object(P,'one_session',return_value=iter(())):
   with self.assertRaises(ValueError):P.run('synthetic',plan(),'/tmp/private',frozen())
 def test_source_change_rejected(self):
  p=plan();p['pin']['sha256']='a'*64
  with self.assertRaises(ValueError):P.validate_plan(p)
 def test_kaggle_guard(self):
  with patch.dict('os.environ',{},clear=True):
   with self.assertRaises(ValueError):P.run('fake',plan(),'/tmp/private',frozen())
if __name__=='__main__':unittest.main()
