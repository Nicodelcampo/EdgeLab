import copy,json
from pathlib import Path
import unittest
from tools.research_ops.confluence.build_crossfamily_roster import build
from tools.research_ops.confluence.build_target_free_pilot import digest
from tools.research_ops.confluence.detector_capture import _module
ROOT=Path(__file__).resolve().parents[2]
class CrossFamilyTests(unittest.TestCase):
 def source(self):return json.loads((ROOT/'docs/research/ops/MNQ_CONFLUENCE_TARGET_FREE_PILOT_ROSTER.json').read_bytes())
 def test_deterministic_nine_profiles_eighteen_only_distinct_family_pairs(self):
  a=build(self.source());b=build(self.source());self.assertEqual(a,b);self.assertEqual(a['config_count'],9);self.assertEqual(a['primary_pair_count'],18)
  self.assertEqual(len({p['pair_sha256'] for p in a['pairs']}),18)
  self.assertTrue(all(p['left_indicator']=='avolzonepoi2' and p['right_indicator'] in ('bigtrap2','bigtrap2absorption') for p in a['pairs']))
  sha=a.pop('roster_sha256');self.assertEqual(sha,digest(a))
 def test_all_profile_params_match_native_defaults_and_digest(self):
  for c in build(self.source())['configs']:
   family={'avolzonepoi2':'AVZP2','bigtrap2':'BT2','bigtrap2absorption':'BT2A'}[c['indicator']]
   self.assertEqual(set(c['params']),set(_module(family).DEFAULTS))
   self.assertEqual(c['config_sha256'],digest({k:c[k] for k in ('indicator','bar_spec','params')}))
 def test_corrupt_profile_or_incomplete_roster_rejected(self):
  s=self.source();s['configs'][2]['params']['detection_percentile']=99
  with self.assertRaises(ValueError):build(s)
  s=self.source();s['configs'].pop()
  with self.assertRaises(ValueError):build(s)
 def test_no_launch_no_outcome_gate_and_no_native_pruning(self):
  p=build(self.source());self.assertFalse(p['market_data_read']);self.assertFalse(p['launched']);self.assertFalse(p['new_results']);self.assertTrue(p['exposure_horizon_is_measurement_scope_not_detector_pruning']);self.assertIn('NOT_COMPLETE_RUNTIME_PLAN',p['status'])
if __name__=='__main__':unittest.main()
