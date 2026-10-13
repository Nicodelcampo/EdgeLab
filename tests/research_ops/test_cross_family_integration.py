"""Integration orchestration on invented tapes; never physical market evidence."""
import copy,json,unittest,tempfile,ast,base64,zlib,subprocess,os
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
import numpy as np
from edgelab.bridge.ticks import TickSeries
from edgelab.bridge import bars as B
from tools.research_ops.confluence.asof_intersections import Clock,ZoneKey
from tools.research_ops.confluence.detector_capture import Capture
from tools.research_ops.confluence.session_primitives import SessionTape
from tools.research_ops.confluence.cross_family_collector import CrossFamilyCollector
from tools.research_ops.confluence.cross_family_pilot import run,PLAN,ROSTER,CAL_PATH
from tools.research_ops.confluence.phenomena_models import TRAIN,EVAL,FEATURES
from tools.research_ops.confluence.package_crossfamily import build_request
ROOT=Path(__file__).resolve().parents[2]
class IntegrationTests(unittest.TestCase):
 def setUp(self):self.plan=json.loads((ROOT/PLAN).read_bytes());self.roster=json.loads((ROOT/ROSTER).read_bytes());self.cal=json.loads((ROOT/CAL_PATH).read_bytes())
 def fixture(self,date):
  n=701;base=int(np.datetime64(date+'T00:00:00','ns').astype(np.int64));i=np.arange(n,dtype=np.int64);px=np.resize(np.array([99,100,101,102,103,104,103,102,101,100]),n);return TickSeries(base+i*10**9,px,np.ones(n)*10,px-1,px,i,.25,instrument='SYN',contract='SYN')
 def test_complete_orchestration_fit_before_eval_shared_census(self):
  dates=list(TRAIN)+list(EVAL[:6]);whole=[];first=0
  for j,d in enumerate(dates):
   t=self.fixture(d);t.sequence+=first;following=Clock(int(self.fixture(dates[j+1]).ts_ns[0]),first+len(t)) if j+1<len(dates) else None;whole.append(SessionTape(t,first,following,int(B.session_ids(t.ts_ns)[0])));first+=len(t)
  def measured(st,date,plan,cal,started,feature_callback):
   t=st.ticks;rng=np.random.default_rng(58);n=120;rows=[]
   for i in range(100,100+n):
    row={'trade_date':date,'timestamp_ns':int(t.ts_ns[i]),'sequence':int(t.sequence[i]),'windows':{'20':{'pressure_ratio':1.2,'trade_count_ratio':.8,'directed_progress_ticks':1.,'direction_from_prior':1}}};feature_callback(row,i,4)
   return (rng.normal(size=(n,len(FEATURES))),np.zeros((n,2)),np.zeros((n,2)),np.arange(n)%3,np.full(n,'OTHER:1'),np.full(n,'NEITHER'),{'trade_date':date,'ticks':len(t),'common_usable_anchors':n,'response_scanned_elements':0})
  with patch.dict(os.environ,{'KAGGLE_KERNEL_RUN_TYPE':'SYNTHETIC_TEST_ONLY'}),patch('tools.research_ops.confluence.cross_family_pilot.iter_sessions',return_value=iter(whole)),patch('tools.research_ops.confluence.cross_family_pilot.session_data',side_effect=measured):
   result=run('unused-invented-source',self.plan,'/tmp/crossfamily-invented-private',self.cal)
  self.assertEqual(len(result['pairs']),18);self.assertEqual(result['models_including_shared_baselines'],146);self.assertEqual(result['available_evaluation_session_count'],6);self.assertEqual(len(result['unavailable_evaluation_sessions']),6);self.assertFalse(result['confirmation']);self.assertFalse(result['raw_exported']);self.assertFalse(result['canonical_brain_written'])
  for s in result['evaluation_sessions']:
   self.assertTrue(all(p['scores']['anchors']==120 for p in s['pairs']));self.assertEqual(s['crossfamily_context']['common_anchors'],120)
  self.assertLess(len(json.dumps(result,indent=2).encode()),self.plan['max_aggregate_bytes'])
  from tools.research_ops.audits.review_crossfamily_models import review
  review(result,self.plan,self.roster)
  bad=copy.deepcopy(result);bad['evaluation_sessions'][0]['pairs'][0]['paired_deltas']['GEOMETRY_MINUS_GEOMETRY_CC']+=.1
  with self.assertRaises(ValueError):review(bad,self.plan,self.roster)
  bad=copy.deepcopy(result);bad['raw_exported']=True
  with self.assertRaises(ValueError):review(bad,self.plan,self.roster)
 def test_future_event_deferred_without_scanning_labels(self):
  t=self.fixture(TRAIN[0]);c=self.roster['configs'][0];record=Capture('BIRTH',ZoneKey('AVZP2',c['config_sha256'],'b'*64,'a'),Clock(int(t.ts_ns[102]),102),101,0,198,202,1,());groups=[[] for _ in range(9)];groups[0]=[(record.clock,[(record,True)])];collector=CrossFamilyCollector(SimpleNamespace(ticks=t),TRAIN[0],groups,self.roster,{**self.plan,'max_common_anchors_per_session':3})
  def row(i):return {'timestamp_ns':int(t.ts_ns[i]),'sequence':i,'windows':{'20':{'pressure_ratio':1.,'trade_count_ratio':1.,'directed_progress_ticks':1.,'direction_from_prior':1}}}
  collector(row(100),100,4);self.assertFalse(collector.indexes[0][0].active);collector(row(103),103,4);self.assertTrue(collector.indexes[0][0].active);self.assertEqual(collector.cursor[0],1)
 def test_foreign_clock_and_common_row_limit_fail_no_prefix_claim(self):
  t=self.fixture(TRAIN[0]);collector=CrossFamilyCollector(SimpleNamespace(ticks=t),TRAIN[0],[[] for _ in range(9)],self.roster,{**self.plan,'max_common_anchors_per_session':1});row={'timestamp_ns':int(t.ts_ns[100]),'sequence':100,'windows':{'20':{'pressure_ratio':1.,'trade_count_ratio':1.,'directed_progress_ticks':1.,'direction_from_prior':1}}};collector(row,100,4)
  with self.assertRaises(ValueError):collector(row,100,4)
  with self.assertRaises(ValueError):collector.finish(2)
 def test_package_contains_isolated_runner_dependency_closure(self):
  req,receipt=build_request(ROOT,url='https://storage.googleapis.com/kagglesdsdata/datasets/1/2/MNQ/MNQ_09-26_ticks_ext.parquet',source_commit='1'*40);text=req['request']['text'];tree=ast.parse(text);data=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='DATA');files=json.loads(zlib.decompress(base64.b64decode(data)))
  self.assertTrue(req['request']['isPrivate']);self.assertFalse(req['request']['enableGpu']);self.assertFalse(receipt['submitted']);self.assertIn('crossfamily-receipt.json',text);self.assertIn('crossfamily_receipt_sha256',text);self.assertNotIn('zone-receipt.json',text)
  with tempfile.TemporaryDirectory() as td:
   root=Path(td)
   for name,r in files.items():p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(base64.b64decode(r['data']))
   for name in ('tools','tools/research_ops','tools/research_ops/confluence'):(root/name/'__init__.py').touch()
   r=subprocess.run([os.sys.executable,'-m','tools.research_ops.confluence.cross_family_pilot','--help'],cwd=root,env={**os.environ,'PYTHONPATH':str(root)},capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stderr)
 def test_package_rejects_unapproved_source_or_commit(self):
  with self.assertRaises(ValueError):build_request(ROOT,url='https://example.com/ticks',source_commit='1'*40)
  with self.assertRaises(ValueError):build_request(ROOT,url='https://storage.googleapis.com/kagglesdsdata/datasets/1/2/MNQ/MNQ_09-26_ticks_ext.parquet',source_commit='short')
if __name__=='__main__':unittest.main()
