"""Synthetic signing roots and temporary ledgers only. Never production authority."""
import base64, copy, json, tempfile, unittest, multiprocessing, os
from pathlib import Path
from dataclasses import asdict, replace
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from tools.research_ops.store import canonical, digest, ZERO
from tools.research_ops.learning_outbox import LearningOutbox, export_outbox, restore_outbox
from tools.research_ops.post_run import RunObservation
from tools.research_ops.canonical_delivery import deliver_reviewed
from tools.research_ops.signed_authority import verify_signed
from edgelab.edge_brain.hippocampus_store import DurableHippocampus
from edgelab.edge_brain.hippocampus import AnalysisEpisode, StepExecution

def roots(role='TECHNICAL_REVIEW'):
    private=Ed25519PrivateKey.generate()
    return private,{'test_key':{'public_key':base64.b64encode(private.public_key().public_bytes_raw()).decode(),'principal':'fixture_reviewer','role':role}}

def sign(private,payload):
    return {'payload':payload,'key_id':'test_key','signature':base64.b64encode(private.sign(canonical(payload).encode())).decode()}

def _crash_delivery(box_path,ledger,pack,keys,tip):
    deliver_reviewed(LearningOutbox(box_path),ledger,pack,trusted_keys=keys,
                     destination_id='fixture_brain',expected_outbox_tip=tip,
                     expected_ledger_tip=ZERO,expected_proposer='fixture_proposer',
                     now=150,after_destination=lambda:os._exit(19))

class SignedDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.box=LearningOutbox(self.root/'box.sqlite');self.box.initialize()
        self.obs=RunObservation('run_1','execution_1',1,'COMPLETE','a'*64,'b'*64,'c'*64,'d'*64,'e'*64,'f'*64,100,512,10,10,(('scan',80),),'PASS')
        self.item=self.box.enqueue('synthetic',self.obs,envelope_sha256='1'*64,expected_tip=self.box.verify()['tip'])
        self.private,self.keys=roots(); self.ledger=self.root/'canonical.jsonl'
        with self.box.transaction() as db:self.pin=db.execute('SELECT hash FROM outbox_drafts').fetchone()[0]
        self.payload=dict(schema='research_ops_technical_review_v1',principal='fixture_reviewer',proposer='fixture_proposer',review_id='review_1',issued_at=100,expires_at=200,destination_id='fixture_brain',draft_key=self.item['key'],draft_sha256=self.pin,envelope_sha256='1'*64,custody_receipt_sha256='2'*64,anchor_records=0,anchor_tip=ZERO,decision='APPROVE_TECHNICAL_RECORD_ONLY')
    def tearDown(self):self.temp.cleanup()
    def call(self,**kw):
        args=dict(trusted_keys=self.keys,destination_id='fixture_brain',expected_outbox_tip=self.box.verify()['tip'],expected_ledger_tip=DurableHippocampus(self.ledger).tip_hash,expected_proposer='fixture_proposer',now=150)
        args.update(kw)
        return deliver_reviewed(self.box,self.ledger,sign(self.private,self.payload),**args)
    def test_delivery_preserves_authority_ceiling(self):
        out=self.call(); b=DurableHippocampus(self.ledger)
        self.assertEqual(out['outbox']['states'][self.item['key']],'DELIVERED')
        self.assertEqual(len(b.memory.episodes),1)
        lesson=next(iter(b.memory.lessons.values()))[0]
        self.assertEqual((lesson.status,lesson.confidence),('PROPOSED','LOW'))
        self.assertFalse(next(iter(b.memory.episodes.values())).outcomes_inspected)
        self.assertFalse(out['activation_allowed'])
    def test_restart_delivery_no_duplicate(self):
        self.call(); raw=self.ledger.read_bytes(); self.box=LearningOutbox(self.box.path)
        self.call();self.assertEqual(raw,self.ledger.read_bytes())
    def test_destination_write_then_crash_before_ack_recovers(self):
        def crash():raise RuntimeError('fixture crash')
        with self.assertRaises(RuntimeError):self.call(after_destination=crash)
        self.assertEqual(self.box.verify()['states'][self.item['key']],'REVIEW_PENDING')
        raw=self.ledger.read_bytes();self.call();self.assertEqual(raw,self.ledger.read_bytes())
    def test_partial_episode_prefix_recovers(self):
        key=self.item['key']; b=DurableHippocampus(self.ledger)
        b.register_episode(AnalysisEpisode('ROE_'+key,'Reviewed target-free technical closeout',status='COMPLETED_UNADJUDICATED',recorded_by='research_ops_signed_delivery'))
        self.call();self.assertEqual(len(DurableHippocampus(self.ledger).memory.steps['ROE_'+key]),1)
    def test_snapshot_restore_delivered_keeps_state(self):
        self.call();p=self.root/'snapshot.json';snap=export_outbox(self.box,p,expected_tip=self.box.verify()['tip'])
        out=restore_outbox(p,self.root/'restored',expected_sha256=snap['sha256'],expected_tip=snap['tip'])
        self.assertEqual(out['outbox']['states'][self.item['key']],'DELIVERED')
    def test_unsigned_or_tampered_receipt_rejected(self):
        pack=sign(self.private,self.payload);pack['payload']['decision']='ADOPT'
        with self.assertRaises(ValueError):deliver_reviewed(self.box,self.ledger,pack,trusted_keys=self.keys,destination_id='fixture_brain',expected_outbox_tip=self.box.verify()['tip'],expected_ledger_tip=ZERO,expected_proposer='fixture_proposer',now=150)
        self.assertFalse(self.ledger.exists())
    def test_unknown_key(self):
        with self.assertRaises(ValueError):self.call(trusted_keys={})
    def test_wrong_role(self):
        self.keys['test_key']['role']='KAGGLE_CUSTODY'
        with self.assertRaises(ValueError):self.call()
    def test_wrong_public_key(self):
        _,self.keys=roots()
        with self.assertRaises(ValueError):self.call()
    def test_key_principal_binding(self):
        self.payload['principal']='pretend_human'
        with self.assertRaises(ValueError):self.call()
    def test_no_self_approval(self):
        self.payload['proposer']='fixture_reviewer'
        with self.assertRaises(ValueError):self.call()
    def test_proposer_bound_to_host_not_receipt_label(self):
        with self.assertRaises(ValueError):self.call(expected_proposer='other')
    def test_process_exit_after_destination_without_ack(self):
        ctx=multiprocessing.get_context('spawn')
        proc=ctx.Process(target=_crash_delivery,args=(str(self.box.path),str(self.ledger),sign(self.private,self.payload),self.keys,self.box.verify()['tip']))
        proc.start();proc.join(15)
        if proc.is_alive():proc.terminate();proc.join();self.fail('bounded crash fixture timed out')
        self.assertEqual(proc.exitcode,19)
        self.assertEqual(self.box.verify()['states'][self.item['key']],'REVIEW_PENDING')
        raw=self.ledger.read_bytes();self.call();self.assertEqual(self.ledger.read_bytes(),raw)
    def test_source_invalidation_cascades_and_blocks_retry(self):
        self.call();b=DurableHippocampus(self.ledger)
        b.invalidate_with_cascade(self.obs.receipt_sha256)
        self.assertIn('ROL_'+self.item['key'],b.invalidations)
        raw=self.ledger.read_bytes()
        with self.assertRaises(ValueError):self.call()
        self.assertEqual(self.ledger.read_bytes(),raw)
    def test_closeout_replayed_after_delivery_is_noop(self):
        self.call();tip=self.box.verify()['tip']
        out=self.box.enqueue('synthetic',self.obs,envelope_sha256='1'*64,expected_tip=tip)
        self.assertTrue(out['duplicate']);self.assertEqual(tip,out['outbox']['tip'])
    def test_acked_destination_rollback_not_recreated(self):
        self.call();self.ledger.write_bytes(b'')
        with self.assertRaises(ValueError):self.call()
        self.assertEqual(self.ledger.read_bytes(),b'')
    def test_unexpected_destination_record_blocks_retry(self):
        self.call();b=DurableHippocampus(self.ledger)
        b.record_step(StepExecution('other_step','ROE_'+self.item['key'],1,'OTHER','fixture'))
        raw=self.ledger.read_bytes()
        with self.assertRaises(ValueError):self.call()
        self.assertEqual(self.ledger.read_bytes(),raw)
    def test_expiry(self):
        for now in (99,200,True):
            with self.subTest(now=now),self.assertRaises(ValueError):self.call(now=now)
    def test_overlong_review(self):
        self.payload['expires_at']=1000000
        with self.assertRaises(ValueError):self.call()
    def test_source_text_or_outcomes_not_accepted(self):
        for k in ('instructions','pnl','target_percent'):
            p=dict(self.payload);self.payload[k]=99
            with self.assertRaises(ValueError):self.call()
            self.payload=p
    def test_exact_draft_binding(self):
        self.payload['draft_sha256']='9'*64
        with self.assertRaises(ValueError):self.call()
    def test_exact_envelope_binding(self):
        self.payload['envelope_sha256']='9'*64
        with self.assertRaises(ValueError):self.call()
    def test_destination_binding(self):
        with self.assertRaises(ValueError):self.call(destination_id='other')
    def test_anchor_mismatch(self):
        self.payload['anchor_tip']='9'*64
        with self.assertRaises(ValueError):self.call()
    def test_anchor_ahead(self):
        self.payload['anchor_records']=1
        with self.assertRaises(ValueError):self.call()
    def test_latest_witness_mismatch(self):
        self.call()
        with self.assertRaises(ValueError):self.call(expected_ledger_tip=ZERO)
    def test_outbox_stale_tip(self):
        old=self.box.verify()['tip'];self.call()
        with self.assertRaises(ValueError):self.call(expected_outbox_tip=old)
    def test_invalidated_pending_blocks(self):
        self.box.invalidate(self.item['key'],reason='MEASUREMENT_ERROR',review_id='revocation',expected_tip=self.box.verify()['tip'])
        with self.assertRaises(ValueError):self.call()
        self.assertFalse(self.ledger.exists())
    def test_existing_episode_conflict(self):
        DurableHippocampus(self.ledger).register_episode(AnalysisEpisode('ROE_'+self.item['key'],'wrong'))
        raw=self.ledger.read_bytes()
        with self.assertRaises(ValueError):self.call()
        self.assertEqual(self.ledger.read_bytes(),raw)
    def test_changed_review_not_ack_rewrite(self):
        self.call();self.payload['review_id']='different'
        with self.assertRaises(ValueError):self.call()
    def test_ledger_symlink_rejected(self):
        other=self.root/'other';other.write_text('');self.ledger.symlink_to(other)
        with self.assertRaises(ValueError):self.call()
    def test_torn_ledger_quarantined(self):
        self.ledger.write_bytes(b'{')
        with self.assertRaises(ValueError):self.call()
        self.assertEqual(self.ledger.read_bytes(),b'{')
    def test_failure_record_not_hidden(self):
        # Failure uses same canonical proposed ceiling, not fake optimization success.
        box=LearningOutbox(self.root/'failed.sqlite');box.initialize()
        obs=replace(self.obs,state='FAILED',failure='OOM',completed_units=3,integrity='FAIL')
        item=box.enqueue('synthetic',obs,envelope_sha256='1'*64,expected_tip=box.verify()['tip']);self.box=box
        self.payload['draft_key']=item['key']
        with box.transaction() as db:self.payload['draft_sha256']=db.execute('SELECT hash FROM outbox_drafts').fetchone()[0]
        self.call()
        b=DurableHippocampus(self.ledger);s=next(iter(b.memory.steps.values()))[0]
        self.assertEqual(s.input_params['failure'],'OOM')

if __name__=='__main__':unittest.main()