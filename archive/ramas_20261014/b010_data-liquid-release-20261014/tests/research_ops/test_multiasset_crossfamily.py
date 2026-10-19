import unittest,json
from pathlib import Path
from datetime import datetime
import numpy as np
from tools.research_ops.confluence.multiasset_crossfamily import PLAN,validate_plan,AssetCalibration
from tools.research_ops.confluence.phenomena_models import phase_key,FEATURES
from tools.research_ops.confluence.cross_family_streaming import StreamingScene
from tools.research_ops.confluence.cross_family_collector import CrossFamilyCollector
from tools.research_ops.confluence.cross_family_pilot import fit_models
class MultiassetTests(unittest.TestCase):
 def setUp(self):self.p=json.loads((Path(__file__).resolve().parents[2]/PLAN).read_bytes())
 def test_frozen_asset_tick_identity_calendar_and_no_mnq_substitution(self):
  for a,size in [('ES',.25),('GC',.1),('6E',.00005),('ZB',.03125)]:self.assertEqual(validate_plan(self.p,a)[0]['tick_size'],size)
  with self.assertRaises(ValueError):validate_plan(self.p,'MNQ')
  with self.assertRaises(ValueError):validate_plan({**self.p,'confirmation':True},'ES')
 def test_phase_preholdout_clock_only_and_calibration_no_eval(self):
  d='2026-07-31';row={'trade_date':d,'timestamp_ns':int(datetime.fromisoformat(d+'T15:00:00+00:00').timestamp())*10**9,'windows':{'20':{'direction_from_prior':1}}};self.assertEqual(phase_key(row,research_dates=(d,)),'RTH:1')
  with self.assertRaises(ValueError):phase_key(row)
  with self.assertRaises(ValueError):AssetCalibration(d).add({**row,'trade_date':'2026-08-11'})
  r=AssetCalibration(d).freeze();self.assertEqual(r['training_trade_date'],d);self.assertFalse(r['outcomes_used'])
 def test_all18features_and146fits_exact_shared_footprint_with_history(self):
  # Import helper class, not its tests into discovery namespace.
  import test_cross_family_streaming as fixtures
  f=fixtures.StreamingTests();f.setUp();outputs=[];diags=[]
  for shared in (False,True):
   scene=StreamingScene(f.roster,{**f.plan,'shared_bt2a_footprints':shared});out=[];cnt=[]
   for j,st in enumerate(f.tapes()):
    d=np.datetime64(st.session_id*86400,'s').astype(str)[:10];keep=j>=22;e,diag=scene.session(st,d,retain=keep)
    if keep:
     c=CrossFamilyCollector(st,d,e,f.roster,f.plan);f.measured(c,st.ticks);e.finish();z,_=c.finish(c.n);out.append(z.copy());cnt.append(diag['config_counts'])
   scene.finish();outputs.append(out);diags.append(cnt)
   if shared:self.assertGreater(scene.footprint_cache.hits,0)
  self.assertEqual(diags[0],diags[1])
  for a,b in zip(*outputs):np.testing.assert_array_equal(a,b)
  rng=np.random.default_rng(989);train=[(rng.normal(size=(len(z),len(FEATURES))),z,rng.integers(0,3,len(z))) for z in outputs[0]];a=fit_models(train);b=fit_models([(x,z,y) for (x,_,y),z in zip(train,outputs[1])]);np.testing.assert_array_equal(a[0]['coef'],b[0]['coef'])
  for aa,bb in zip(a[1],b[1]):
   for n in aa:np.testing.assert_array_equal(aa[n]['coef'],bb[n]['coef'])
