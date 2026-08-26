from __future__ import annotations
import json
import unittest
from datetime import date
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
class Gate1All5ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from edgelab.research.bt2_gate1_all5 import _context
        cls.registry,_,cls.spec=_context(ROOT)
    def test_all_five_contracts_and_234_unique_sessions(self):
        self.assertEqual(self.registry['selection']['contracts'],['GC 12-25','GC 02-26','GC 04-26','GC 06-26','GC 08-26'])
        rows=self.registry['sessions'];self.assertEqual(len(rows),234);self.assertEqual(len({r['cme_session_id'] for r in rows}),234)
        counts={c:sum(r['contract']==c for r in rows) for c in self.registry['selection']['contracts']}
        self.assertEqual(counts,{'GC 12-25':82,'GC 02-26':44,'GC 04-26':42,'GC 06-26':42,'GC 08-26':24})
    def test_only_weekdays_and_no_partial_left_edge(self):
        for row in self.registry['sessions']:
            s=row['cme_session_id'];self.assertLess(date(int(s[:4]),int(s[4:6]),int(s[6:])).weekday(),5)
        self.assertNotIn('20250801',{r['cme_session_id'] for r in self.registry['sessions']})
        self.assertEqual(self.registry['sessions'][0]['cme_session_id'],'20250804')
    def test_every_session_has_strictly_prior_warmup(self):
        for row in self.registry['sessions']:self.assertLess(row['warmup_cme_session_id'],row['cme_session_id'])
    def test_post_outcome_firewall_is_fail_closed(self):
        f=self.spec['firewall'];self.assertTrue(f['CAMPAIGN_OUTCOMES_OPENED']);self.assertFalse(f['EDGE_DECLARED']);self.assertFalse(f['confirmatory_eligible']);self.assertFalse(self.spec['power']['promotion_eligible'])
    def test_interpretation_forbids_net_pnl_claim(self):
        i=self.spec['interpretation_contract'];self.assertTrue(i['not_realized_pnl']);self.assertFalse(i['costs_included']);self.assertIn('net ticks',i['forbidden_claims'])
if __name__=='__main__':unittest.main()
