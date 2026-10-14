import json
from pathlib import Path
import unittest
from tools.research_ops.confluence.build_target_free_pilot import build_roster,digest
R=Path(__file__).resolve().parents[2]
class PilotTests(unittest.TestCase):
    def setUp(self):self.s=json.loads((R/'docs/research/ops/MNQ_DENSE_CONFLUENCE_DESIGN.json').read_bytes())
    def test_roster_deterministic_and_outcome_free(self):
        a=build_roster(self.s);b=build_roster(self.s);self.assertEqual(a,b);self.assertEqual(a['n_configs'],96);self.assertFalse(a['launch_ready']);self.assertIsNone(a['source_manifest'])
    def test_complete_marginal_level_coverage_not_cartesian_claim(self):
        a=build_roster(self.s);self.assertTrue(all(not x['not_covered'] for f in a['coverage'].values() for x in f.values()))
    def test_full_config_hash_and_no_silent_alias_duplicates(self):
        a=build_roster(self.s);self.assertEqual(len(set(c['config_sha256'] for c in a['configs'])),96)
        for c in a['configs']:self.assertEqual(c['config_sha256'],digest({k:c[k] for k in ('indicator','bar_spec','params')}))
    def test_no_renderer_or_warmup_reduction(self):
        a=build_roster(self.s)
        for c in a['configs']:
            p=c['params'];self.assertNotIn('AutoScale',p);self.assertNotIn('TopPercentFilter',p)
            if c['indicator']=='bigtrap2absorption':self.assertEqual(p['MinHistoryBuckets'],200);self.assertEqual(p['AbsorptionLookback'],500)
            elif c['indicator']=='avolzonepoi2':self.assertEqual(p['lookback_sessions'],20);self.assertEqual(p['min_samples'],20)
if __name__=='__main__':unittest.main()
