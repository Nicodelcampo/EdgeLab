import copy, hashlib, json, unittest
import tests.research_ops.test_mnq_closeout as fixtures
from tests.research_ops.test_signed_delivery import roots, sign
from tools.research_ops.authenticated_closeout import receive_authenticated_closeout
from tools.research_ops.store import digest
from tools.research_ops.mnq_closeout import write_mnq_envelope
from tools.research_ops.learning_outbox import LearningOutbox
from tools.research_ops.closeout import ingest_closeout
from tools.research_ops.canonical_delivery import deliver_reviewed
from edgelab.edge_brain.hippocampus_store import DurableHippocampus

class AuthenticatedCloseoutTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.MnqCloseoutTests();self.f.setUp();self.root=self.f.root
        self.private,self.keys=roots('KAGGLE_CUSTODY')
        self.identity=self.f.identity()
        self.memory=dict(schema='research_ops_memory_measurement_v1',identity_sha256=digest(self.identity),code_commit='a'*40,measurement='LINUX_SINGLE_PROCESS_RUSAGE_SELF_HIGH_WATER_RSS',peak_rss_bytes=8192,children_seen=False,workload_complete=True)
        self.payload=dict(schema='research_ops_kaggle_custody_v1',principal='fixture_reviewer',issued_at=100,expires_at=200,provider='kaggle',account='fixture_account',kernel_id=123,version=1,execution_id=self.identity['provider_job_id'],terminal='COMPLETE',contract='MNQ_01-00',scope='focal',scientific_code_commit='a'*40,identity=self.identity,pins=self.f.pins,memory_sha256='0'*64)
        self.save_memory()
    def tearDown(self):self.f.tearDown()
    def save_memory(self):
        raw=json.dumps(self.memory).encode();(self.root/'memory-measurement.json').write_bytes(raw)
        self.payload['memory_sha256']=hashlib.sha256(raw).hexdigest()
    def call(self,**kwargs):
        args=dict(trusted_keys=self.keys,now=150,expected_account='fixture_account',expected_kernel_id=123,expected_version=1,expected_execution_id='synthetic_execution_1',expected_contract='MNQ_01-00',expected_scope='focal',expected_code_commit='a'*40)
        args.update(kwargs)
        return receive_authenticated_closeout(self.root,sign(self.private,self.payload),**args)
    def test_verified_custody_no_scientific_authority(self):
        r=self.call();self.assertTrue(r['custody_signature_verified']);self.assertFalse(r['source_certified']);self.assertFalse(r['execution_allowed'])
        self.assertEqual(r['envelope']['observation']['peak_rss_bytes'],8192)
        raw=json.dumps(r);self.assertNotIn('target_percent',raw);self.assertNotIn('instructions',raw)
    def test_signature_role_rejected(self):
        self.keys['test_key']['role']='TECHNICAL_REVIEW'
        with self.assertRaises(ValueError):self.call()
    def test_no_trust_roots(self):
        with self.assertRaises(ValueError):self.call(trusted_keys={})
    def test_identity_mismatch(self):
        self.payload['identity']=dict(self.identity,provider_job_id='rerun')
        with self.assertRaises(ValueError):self.call()
    def test_other_notebook_version(self):
        for k,v in [('expected_account','other'),('expected_kernel_id',124),('expected_version',2),('expected_execution_id','other'),('expected_contract','OTHER'),('expected_scope','matrix'),('expected_code_commit','b'*40)]:
            with self.subTest(k=k),self.assertRaises(ValueError):self.call(**{k:v})
    def test_memory_not_from_this_run(self):
        self.memory['identity_sha256']='a'*64;self.save_memory()
        with self.assertRaises(ValueError):self.call()
    def test_memory_not_from_this_build(self):
        self.memory['code_commit']='b'*40;self.save_memory()
        with self.assertRaises(ValueError):self.call()
    def test_child_rss_cannot_be_underestimated(self):
        self.memory['children_seen']=True;self.save_memory()
        with self.assertRaises(ValueError):self.call()
    def test_sampled_or_cap_memory_rejected(self):
        for method in ('SAMPLED','MEMORY_CAP','LOCAL_HOST'):
            self.memory['measurement']=method;self.save_memory()
            with self.subTest(method=method),self.assertRaises(ValueError):self.call()
    def test_missing_rss_not_imputed(self):
        for rss in (None,0,True,-1):
            self.memory['peak_rss_bytes']=rss;self.save_memory()
            if rss is None:
                self.assertIsNone(self.call()['envelope'])
            else:
                with self.assertRaises(ValueError):self.call()
    def test_incomplete_memory_rejected(self):
        self.memory['workload_complete']=False;self.save_memory()
        with self.assertRaises(ValueError):self.call()
    def test_memory_tampered_bytes(self):
        (self.root/'memory-measurement.json').write_text('{}')
        with self.assertRaises(ValueError):self.call()
    def test_missing_memory_receipt(self):
        (self.root/'memory-measurement.json').unlink()
        with self.assertRaises(FileNotFoundError):self.call()
    def test_unreviewed_census(self):
        self.f.audit['focal_definitions']=1;self.f.save();self.payload['pins']=self.f.pins
        with self.assertRaises(ValueError):self.call()
    def test_live_or_failed_does_not_become_complete(self):
        for state in ('RUNNING','FAILED','CANCELLED'):
            self.payload['terminal']=state
            with self.subTest(state=state),self.assertRaises(ValueError):self.call()
    def test_closed_fields(self):
        self.payload['instructions']='bad'
        with self.assertRaises(ValueError):self.call()
    def test_expiry(self):
        with self.assertRaises(ValueError):self.call(now=200)
    def test_missing_receipt_pin(self):
        self.payload['pins']=dict(self.f.pins);self.payload['pins'].pop('timing-evidence.json')
        with self.assertRaises(ValueError):self.call()
    def test_memory_symlink(self):
        p=self.root/'memory-measurement.json';target=self.root/'memory-other';p.rename(target);p.symlink_to(target)
        with self.assertRaises(OSError):self.call()
    def test_signed_custody_to_independent_review_and_canonical_ack(self):
        candidate=self.call();path=self.root/'envelope.json'
        written=write_mnq_envelope(candidate,path)
        box=LearningOutbox(self.root/'outbox.sqlite');state=box.initialize()
        item=ingest_closeout(path,box,expected_sha256=written['sha256'],
                            expected_provider='kaggle',expected_job_id='synthetic_execution_1',
                            expected_version=1,expected_tip=state['tip'])
        with box.transaction() as db:
            pin=db.execute('SELECT hash FROM outbox_drafts').fetchone()[0]
        reviewer,review_keys=roots('TECHNICAL_REVIEW')
        review=dict(schema='research_ops_technical_review_v1',principal='fixture_reviewer',
                    proposer='fixture_proposer',review_id='independent_review',issued_at=100,
                    expires_at=200,destination_id='fixture_brain',draft_key=item['key'],
                    draft_sha256=pin,envelope_sha256=written['sha256'],
                    custody_receipt_sha256=candidate['custody_receipt_sha256'],
                    anchor_records=0,anchor_tip='0'*64,decision='APPROVE_TECHNICAL_RECORD_ONLY')
        ledger=self.root/'canonical.jsonl'
        out=deliver_reviewed(box,ledger,sign(reviewer,review),trusted_keys=review_keys,
                             destination_id='fixture_brain',expected_outbox_tip=item['outbox']['tip'],
                             expected_ledger_tip='0'*64,expected_proposer='fixture_proposer',now=150)
        self.assertEqual(out['outbox']['states'][item['key']],'DELIVERED')
        brain=DurableHippocampus(ledger)
        self.assertEqual(len(brain.memory.episodes),1)
        self.assertEqual(len(next(iter(brain.memory.lessons.values()))),1)
        self.assertFalse(out['scientific_outcomes_written'])


    def test_cgroup_accounted_peak_cannot_be_relabeled_rss(self):
        self.memory['measurement']='LINUX_CGROUP_V2_MEMORY_PEAK_ACCOUNTED_BYTES_NOT_RSS'
        self.save_memory()
        with self.assertRaises(ValueError):self.call()
    def test_diagnostic_schema_rejected_even_with_fixture_custody_signature(self):
        self.memory={'schema':'research_ops_cgroup_memory_diagnostic_v1','peak_accounted_memory_bytes':8192,'authenticated_custody':False}
        self.save_memory()
        with self.assertRaises(ValueError):self.call()

if __name__=='__main__':unittest.main()
