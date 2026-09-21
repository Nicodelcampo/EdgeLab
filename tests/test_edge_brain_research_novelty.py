import unittest
from edgelab.edge_brain.research_novelty import *
class NoveltyGateTests(unittest.TestCase):
 def history(self):
  common=("price_ticks","bid_ticks","ask_ticks","volume");counts=[7128,2304,1296,10368,3456,2304];mechanisms=["GENERIC_RETEST","CORRIDOR_TRAVERSAL","WALL_RETEST","MOMENTUM_CORRIDOR","WALL_REJECTION","WALL_BREACH"];return [CampaignEvidence(f"C{i}","YM_BT2A_DENSITY",("YM_DISCOVERY_PRE2026",),common,m,"NEXT_OBSERVED_MARKET_TICK",n,0)for i,(n,m)in enumerate(zip(counts,mechanisms))]
 def proposal(self,**kw):
  d=dict(campaign_id="P",lineage_id="YM_BT2A_DENSITY",dataset_ids=("YM_DISCOVERY_PRE2026",),observable_fields=("price_ticks","bid_ticks","ask_ticks","volume"),mechanism_family="NEW_STORY",execution_contract="NEXT_OBSERVED_MARKET_TICK");d.update(kw);return CampaignProposal(**d)
 def test_saturation_count_is_explicit(self):
  x=evaluate_research_novelty(self.proposal(),self.history());self.assertEqual(x.cumulative_policy_count,26856);self.assertEqual(x.zero_survivor_campaigns,6);self.assertTrue(x.saturated);self.assertEqual(x.verdict,ABSTAIN_RESEARCH_SATURATED)
 def test_new_l2_observable_opens_novel_episode(self):
  x=evaluate_research_novelty(self.proposal(observable_fields=("price_ticks","bid_ticks","ask_ticks","volume","l2_cancel_volume")),self.history());self.assertTrue(x.may_open);self.assertIn("NEW_OBSERVABLE",x.novel_dimensions)
 def test_new_instrument_opens_target_free_episode(self):
  x=evaluate_research_novelty(self.proposal(dataset_ids=("NQ_DISCOVERY_PRE2026",)),self.history());self.assertTrue(x.may_open);self.assertIn("NEW_DATASET",x.novel_dimensions)
 def test_queue_aware_execution_is_hard_novelty(self):
  x=evaluate_research_novelty(self.proposal(execution_contract="OBSERVED_QUEUE_AWARE_PASSIVE_FILL"),self.history());self.assertTrue(x.may_open);self.assertIn("NEW_EXECUTION_CONTRACT",x.novel_dimensions)
 def test_validation_requires_lock(self):
  x=evaluate_research_novelty(self.proposal(dataset_ids=("NQ_DISCOVERY_PRE2026",),requests_validation=True),self.history());self.assertEqual(x.verdict,ABSTAIN_HOLDOUT_GOVERNANCE)
 def test_holdout_requires_lock_and_human_authorization(self):
  x=evaluate_research_novelty(self.proposal(dataset_ids=("NQ_DISCOVERY_PRE2026",),requests_holdout=True,candidate_lock_present=True),self.history());self.assertEqual(x.verdict,ABSTAIN_HOLDOUT_GOVERNANCE)
if __name__=='__main__':unittest.main()
