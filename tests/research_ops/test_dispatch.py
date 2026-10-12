"""Durable research budget ledger tests. No network, no provider, synthetic only."""
import hashlib, json, os, sqlite3, tempfile, unittest
from pathlib import Path
from tools.research_ops.dispatch import DispatchLedger, Reviewer
from tools.research_ops.knowledge import knowledge_context, validate_literature_pack
from tools.research_ops.research_cycle import ResearchBudget, plan_research

QUESTION = 'liquidity context causal control'
COMMIT = '5c10da451b164c54133bdb9a4674de43d6fa2d22'


def literature_pack(question=QUESTION, passage='Inversion: order book liquidity requires causal control.'):
    items = [dict(record_id='PASSAGE-SSRN-0001-01', source_id='SRC-SSRN-0001', doc_id=1, title='SYNTHETIC ARTICLE ONLY',
                  source_file='synthetic.txt', passage=passage, score=3, authority_status='LITERATURE_CLAIM_UNVERIFIED',
                  reason_for_inclusion='Synthetic matched terms')]
    h = hashlib.sha256(json.dumps(items, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    pack = dict(query=question, items=items, char_budget=12000, used_chars=len(passage), context_sha256=h, claims_are_evidence=False)
    return validate_literature_pack(pack, expected_query=question, producer_commit=COMMIT)


def ready_plan(public_query='public evidence question', budget=None):
    brain = dict(query=QUESTION, hits=[{'record_id': 'L-1'}], claims_are_evidence=False, used_chars=10, invalidations={})
    ctx = knowledge_context(QUESTION, brain, literature_pack())
    return plan_research(ctx, gap_kind='NO_PRIOR_EVIDENCE', missing_evidence='need external methodology evidence',
                          episode_id='EP-1', budget=budget, public_query=public_query, public_query_reviewed=True)


class DispatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name)
        self.ledger = DispatchLedger(self.root / 'dispatch.sqlite')
        self.ledger.initialize(Reviewer('reviewer-one'))

    def tearDown(self):
        self.tmp.cleanup()

    def sha(self, text): return hashlib.sha256(text.encode()).hexdigest()

    def test_initialization_idempotent(self):
        tip = self.ledger.verify()['tip']
        self.ledger.initialize(Reviewer('reviewer-one'))
        self.assertEqual(self.ledger.verify()['tip'], tip)

    def test_reviewer_frozen(self):
        with self.assertRaises(ValueError): self.ledger.initialize(Reviewer('someone-else'))

    def test_invalid_reviewer_scope(self):
        with self.assertRaises(ValueError): Reviewer('r', scope='market').validate()

    def test_invalid_reviewer_id(self):
        with self.assertRaises(ValueError): Reviewer('bad id!').validate()

    def test_explicit_initialization_required(self):
        with self.assertRaises(ValueError): DispatchLedger(self.root / 'absent.sqlite').verify()

    def test_bind_plan_requires_ready_status(self):
        plan = ready_plan(public_query=None, budget=ResearchBudget())
        with self.assertRaises(ValueError): self.ledger.bind_plan(plan)

    def test_bind_plan_rejects_tampered_hash(self):
        plan = ready_plan(); plan['plan_sha256'] = '0' * 64
        with self.assertRaises(ValueError): self.ledger.bind_plan(plan)

    def test_bind_plan_once(self):
        self.ledger.bind_plan(ready_plan())
        with self.assertRaises(ValueError): self.ledger.bind_plan(ready_plan())

    def test_reserve_requires_bound_plan(self):
        with self.assertRaises(ValueError): self.ledger.reserve(0, reviewer_id='reviewer-one')

    def test_reserve_and_no_double_grant(self):
        self.ledger.bind_plan(ready_plan())
        state = self.ledger.reserve(0, reviewer_id='reviewer-one')
        self.assertEqual(state['reserved'], [0])
        self.assertFalse(state['network_executed'])
        with self.assertRaises(ValueError): self.ledger.reserve(0, reviewer_id='reviewer-one')

    def test_reserve_wrong_reviewer_rejected(self):
        self.ledger.bind_plan(ready_plan())
        with self.assertRaises(ValueError): self.ledger.reserve(0, reviewer_id='impostor')

    def test_reserve_out_of_budget_index_rejected(self):
        plan = ready_plan()
        self.ledger.bind_plan(plan)
        with self.assertRaises(ValueError): self.ledger.reserve(plan['budget']['max_queries'], reviewer_id='reviewer-one')

    def test_restart_does_not_regrant_budget(self):
        self.ledger.bind_plan(ready_plan())
        self.ledger.reserve(0, reviewer_id='reviewer-one')
        reopened = DispatchLedger(self.root / 'dispatch.sqlite')
        with self.assertRaises(ValueError): reopened.reserve(0, reviewer_id='reviewer-one')
        self.assertEqual(reopened.verify()['reserved'], [0])

    def test_receipt_requires_prior_reservation(self):
        self.ledger.bind_plan(ready_plan())
        with self.assertRaises(ValueError):
            self.ledger.record_receipt(0, evidence_sha256='a' * 64, source_url_sha256='b' * 64, char_count=100, cost=0)

    def test_receipt_recorded_once(self):
        self.ledger.bind_plan(ready_plan())
        self.ledger.reserve(0, reviewer_id='reviewer-one')
        state = self.ledger.record_receipt(0, evidence_sha256='a' * 64, source_url_sha256='b' * 64, char_count=100, cost=0)
        self.assertEqual(state['receipts'][0], 'a' * 64)
        with self.assertRaises(ValueError):
            self.ledger.record_receipt(0, evidence_sha256='a' * 64, source_url_sha256='b' * 64, char_count=100, cost=0)

    def test_receipt_rejects_paid_spend(self):
        self.ledger.bind_plan(ready_plan())
        self.ledger.reserve(0, reviewer_id='reviewer-one')
        with self.assertRaises(ValueError):
            self.ledger.record_receipt(0, evidence_sha256='a' * 64, source_url_sha256='b' * 64, char_count=100, cost=1)

    def test_receipt_rejects_unpinned_evidence(self):
        self.ledger.bind_plan(ready_plan())
        self.ledger.reserve(0, reviewer_id='reviewer-one')
        with self.assertRaises(ValueError):
            self.ledger.record_receipt(0, evidence_sha256='not-a-hash', source_url_sha256='b' * 64, char_count=100, cost=0)

    def test_tampered_event_chain_detected(self):
        self.ledger.bind_plan(ready_plan())
        self.ledger.reserve(0, reviewer_id='reviewer-one')
        db = sqlite3.connect(self.ledger.path)
        try:
            db.execute("UPDATE events SET body=replace(body,'RESERVED','TAMPERED') WHERE seq=3")
            db.commit()
        finally:
            db.close()
        with self.assertRaises(ValueError): self.ledger.verify()

    @unittest.skipUnless(os.name == 'posix', 'symlinks require elevated privileges on Windows')
    def test_symlink_db_rejected(self):
        link = self.root / 'link.sqlite'
        link.symlink_to(self.root / 'dispatch.sqlite')
        with self.assertRaises(ValueError): DispatchLedger(link)

    def test_no_network_module_level(self):
        import tools.research_ops.dispatch as mod
        src = Path(mod.__file__).read_text()
        for forbidden in ('requests', 'urllib', 'socket', 'http.client'):
            self.assertNotIn(forbidden, src)
