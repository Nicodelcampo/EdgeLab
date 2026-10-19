import unittest
from tools.research_ops.confluence.multiasset_support_probe import finish_counts,run
class SupportProbeTests(unittest.TestCase):
 def test_support_not_success_and_exact_partition(self):
  x=finish_counts(200,{'UNKNOWN':199,'NEITHER':1},{'CLASSIFICATION_UNKNOWN':199},{'CONTINUATION_FIRST':1},1)
  self.assertFalse(x['training_min100_passed']);self.assertEqual(x['common_usable_anchors'],1)
  self.assertTrue(finish_counts(100,{'NEITHER':100},{},{'CONTINUATION_FIRST':100},100)['training_min100_passed'])
 def test_invalid_census_and_market_off_kaggle(self):
  with self.assertRaises(ValueError):finish_counts(200,{'UNKNOWN':199},{'CLASSIFICATION_UNKNOWN':199},{},0)
  with self.assertRaises(ValueError):run('.',{}, {})
