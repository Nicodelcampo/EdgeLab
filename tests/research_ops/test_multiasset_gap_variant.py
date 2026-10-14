import unittest,json
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
import numpy as np
from tools.research_ops.confluence.multiasset_crossfamily import PLAN,GAP10_PLAN,validate_plan
from tools.research_ops.confluence.phenomena_model_pilot import session_data
class GapVariantTests(unittest.TestCase):
 def test_frozen_variants_no_silent_gap_mutation(self):
  a=json.loads(Path(PLAN).read_bytes());b=json.loads(Path(GAP10_PLAN).read_bytes())
  for z in ('GC','6E','ZB'):validate_plan(b,z)
  with self.assertRaises(ValueError):validate_plan({**a,'max_gap_ns':10000000000},'GC')
  self.assertEqual(a['training_sessions'],b['training_sessions']);self.assertEqual(a['evaluation_sessions'],b['evaluation_sessions']);self.assertEqual(a['calibration_date'],b['calibration_date']);self.assertEqual(b['max_gap_ns'],10000000000)
 def test_features_and_labels_receive_same_explicit_gap_defaults_unchanged(self):
  st=SimpleNamespace(ticks=SimpleNamespace(**{k:np.array([1],dtype=np.int64) for k in ('ts_ns','sequence','price_ticks','volume','bid_ticks','ask_ticks')}));p={'max_session_ticks':100,'max_anchors':100,'wall_seconds':600,'max_scan_elements_per_session':1000}
  for g in (None,2000000000,10000000000):
   pp=p if g is None else {**p,'max_gap_ns':g}
   with patch('tools.research_ops.confluence.phenomena_model_pilot.ClockMeasurements') as m,patch('tools.research_ops.confluence.phenomena_model_pilot.SecondsResponse') as r:
    m.return_value.measure.return_value=[]
    with self.assertRaisesRegex(ValueError,'session common usable support'):session_data(st,'2026-08-03',pp,{},0)
    self.assertEqual(m.call_args.kwargs['max_gap_ns'],g or 2000000000);self.assertEqual(r.call_args.kwargs['max_gap_ns'],g or 2000000000)
