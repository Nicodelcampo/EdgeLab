import unittest,json,gzip,base64,copy
from pathlib import Path
from tools.research_ops.confluence.multiasset_crossfamily import PLAN
from tools.research_ops.confluence.build_target_free_pilot import digest
from tools.research_ops.audits.review_multiasset_crossfamily import review
class ReviewTests(unittest.TestCase):
 def fixture(self):
  root=Path(__file__).resolve().parents[2];p=json.loads((root/PLAN).read_bytes());archive=json.loads((root/'docs/research/ops/MNQ_CROSS_FAMILY_V3_MODEL_RECEIPT_PACKED.json').read_bytes());r=json.loads(gzip.decompress(base64.b64decode(archive['data'])));r.update(schema='multiasset_crossfamily_receipt_v1',asset='ES',tick_size=.25,plan_sha256=digest(p),approximate_parity_exploration_accepted=True,near100_percent_NT8_parity_measured=False,detector_history_or_active_state_shared=False,bt2a_bucket_preprocessing_shared=True,arrival_context_summaries=[{} for _ in range(18)])
  # Deliberately synthetic aggregate coordinate rewrite for bookkeeping test,
  # never a claim that MNQ rows are real ES observations.
  r['training_sessions']=[{**copy.deepcopy(r['training_sessions'][j%2]),'trade_date':d} for j,d in enumerate(p['training_sessions'])]
  for s,d in zip(r['evaluation_sessions'],p['evaluation_sessions']):s['trade_date']=d
  r['unavailable_evaluation_sessions']=[{'trade_date':d,'status':'SOURCE_EMPTY_NO_REPLACEMENT','replacement_selected':False} for d in p['evaluation_sessions'][len(r['evaluation_sessions']):]]
  for s in r['training_sessions']+r['evaluation_sessions']:s['native_scene']['whole_session_event_store']=False
  c=json.loads((root/'docs/research/ops/MNQ_PHENOMENA_MODEL_FROZEN_CALIBRATION.json').read_bytes());c['training_trade_date']=p['calibration_date'];c['sha256']=digest({k:v for k,v in c.items() if k!='sha256'});r['calibration']=c;r['calibration_sha256']=c['sha256'];return r,p
 def test_aggregate_bookkeeping_not_crossasset_parity(self):
  r,p=self.fixture();s=review(r,p,'ES');self.assertEqual(s['primary_pairs_checked'],18);self.assertFalse(s['crossasset_or_prior_MNQ_same_population_claimed'])
 def test_mismatch_and_expanded_claims_fail(self):
  for field,val in [('tick_size',.1),('holdout_opened',True),('detector_history_or_active_state_shared',True)]:
   r,p=self.fixture();r[field]=val
   with self.assertRaises(ValueError):review(r,p,'ES')
 def test_future_calibration_fails(self):
  r,p=self.fixture();r['calibration']['training_trade_date']='2026-08-11'
  with self.assertRaises(ValueError):review(r,p,'ES')
