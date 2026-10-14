import json,sqlite3,tempfile,unittest
from pathlib import Path
from tools.research_ops.dispatch_intent import DispatchIntent,request_key
REQ={'account':'nicolasbuttaro','spec_sha256':'a'*64,'source_commit':'b'*40,'bundle_sha256':'c'*64,'plan_sha256':'d'*64}
JOB={k:REQ[k] for k in ('account','source_commit','bundle_sha256','plan_sha256')};JOB.update(kernel_id=10,version=1)
class IntentTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'intents.sqlite';self.w=DispatchIntent(self.path);self.s=self.w.initialize(account=REQ['account']);self.key=request_key(REQ)
 def tearDown(self):self.tmp.cleanup()
 def prepare(self):self.s=self.w.prepare(REQ,expected_tip=self.s['tip_sha256'])
 def send(self):self.prepare();self.s=self.w.begin_send(self.key,expected_tip=self.s['tip_sha256'])
 def test_prepare_idempotent(self):
  self.prepare();old=self.s['tip_sha256'];self.prepare();self.assertEqual(old,self.s['tip_sha256']);self.assertEqual(len(self.s['intents']),1)
 def test_crash_unknown_cannot_resend(self):
  self.send();w=DispatchIntent(self.path);s=w.snapshot()
  with self.assertRaises(ValueError):w.begin_send(self.key,expected_tip=s['tip_sha256'])
  with self.assertRaises(ValueError):w.abandon_before_send(self.key,expected_tip=s['tip_sha256'])
 def test_reconcile_then_terminal(self):
  self.send();self.s=self.w.acknowledge(self.key,JOB,expected_tip=self.s['tip_sha256']);old=self.s['tip_sha256']
  self.s=self.w.acknowledge(self.key,JOB,expected_tip=old);self.assertEqual(old,self.s['tip_sha256'])
  self.s=self.w.terminal(self.key,JOB,'COMPLETE',expected_tip=self.s['tip_sha256']);old=self.s['tip_sha256']
  self.assertEqual(old,self.w.terminal(self.key,JOB,'COMPLETE',expected_tip=old)['tip_sha256'])
  self.prepare();self.assertEqual(self.s['intents'][self.key]['status'],'COMPLETE')
 def test_stale_writer(self):
  old=self.s['tip_sha256'];self.prepare()
  with self.assertRaises(ValueError):self.w.begin_send(self.key,expected_tip=old)
 def test_pending_capacity(self):
  self.send();other={**REQ,'spec_sha256':'f'*64}
  with self.assertRaises(ValueError):self.w.prepare(other,expected_tip=self.s['tip_sha256'])
 def test_job_conflict(self):
  self.send()
  with self.assertRaises(ValueError):self.w.acknowledge(self.key,{**JOB,'bundle_sha256':'e'*64},expected_tip=self.s['tip_sha256'])
 def test_terminal_before_ack_rejected(self):
  self.send()
  with self.assertRaises(ValueError):self.w.terminal(self.key,JOB,'ERROR',expected_tip=self.s['tip_sha256'])
 def test_pre_send_abandon_not_refund(self):
  self.w=DispatchIntent(Path(self.tmp.name)/'small.sqlite');self.s=self.w.initialize(account=REQ['account'],max_intents=1);self.prepare()
  self.s=self.w.abandon_before_send(self.key,expected_tip=self.s['tip_sha256'])
  with self.assertRaises(ValueError):self.w.prepare({**REQ,'spec_sha256':'e'*64},expected_tip=self.s['tip_sha256'])
 def test_policy_not_reset(self):
  self.send()
  with self.assertRaises(ValueError):self.w.initialize(account=REQ['account'],max_intents=16)
 def test_corrupt_journal(self):
  self.prepare()
  with sqlite3.connect(self.path) as db:db.execute("UPDATE dispatch_events SET hash=?",('f'*64,))
  with self.assertRaises(ValueError):self.w.snapshot()
 def test_closed_fields_no_url_or_secret(self):
  with self.assertRaises(ValueError):self.w.prepare({**REQ,'signed_url':'PRIVATE'},expected_tip=self.s['tip_sha256'])
 def test_no_authority_claim(self):
  self.send()
  for k in ('execution_authorized','network_attached','global_account_budget_attested','external_latest_witness_bound'):self.assertFalse(self.s[k])
if __name__=='__main__':unittest.main()
