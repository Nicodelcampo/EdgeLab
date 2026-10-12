"""Synthetic operational fixtures only. No market, cloud or canonical writes."""
import contextlib
import io
import hashlib
import json
import sqlite3
import tempfile
import multiprocessing
import os
import unittest
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, replace
from pathlib import Path
from tools.research_ops.post_run import RunObservation
from tools.research_ops.learning_outbox import LearningOutbox, export_outbox, restore_outbox
from tools.research_ops.closeout import ingest_closeout
from tools.research_ops.store import Store
from tools.research_ops.cli import main


def _crash_uncommitted(path):
    db=sqlite3.connect(path,isolation_level=None)
    db.execute('PRAGMA synchronous=FULL')
    db.execute('BEGIN IMMEDIATE')
    db.execute('UPDATE outbox_meta SET max_items=7')
    os._exit(19)


class LearningOutboxTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.box=LearningOutbox(self.root/'outbox.sqlite');self.box.initialize(8)
    def tearDown(self):self.temp.cleanup()
    def obs(self):
        return RunObservation('run_1','job_1',1,'COMPLETE','a'*64,'b'*64,'c'*64,'d'*64,'e'*64,'f'*64,100,512,10,10,(('prepare',20),('scan',60)),'PASS')
    def enqueue(self,obs=None,sha='1'*64):
        return self.box.enqueue('synthetic',obs or self.obs(),envelope_sha256=sha,expected_tip=self.box.verify()['tip'])
    def pack(self,obs=None):return {'schema':'research_ops_technical_closeout_v1','provider':'synthetic','observation':asdict(obs or self.obs())}
    def envelope(self,pack=None):
        raw=json.dumps(pack or self.pack()).encode();p=self.root/'envelope.json';p.write_bytes(raw);return p,hashlib.sha256(raw).hexdigest()
    def ingest(self,path,sha,**overrides):
        kw=dict(expected_sha256=sha,expected_provider='synthetic',expected_job_id='job_1',expected_version=1,expected_tip=self.box.verify()['tip']);kw.update(overrides)
        return ingest_closeout(path,self.box,**kw)
    def snapshot(self):
        p=self.root/'snapshot.json';s=self.box.verify();out=export_outbox(self.box,p,expected_tip=s['tip']);return p,out
    def test_empty_initialized(self):self.assertEqual(self.box.verify()['items'],0)
    def test_registration_and_reopen(self):
        x=self.enqueue();b=LearningOutbox(self.box.path);s=b.verify();self.assertEqual(s['items'],1);self.assertEqual(s['states'][x['key']],'REVIEW_PENDING')
    def test_duplicate_is_noop_after_restart(self):
        x=self.enqueue();tip=x['outbox']['tip'];self.box=LearningOutbox(self.box.path);y=self.enqueue();self.assertTrue(y['duplicate']);self.assertEqual(y['outbox']['tip'],tip)
    def test_receipt_conflict_not_overwritten(self):
        self.enqueue()
        with self.assertRaises(ValueError):self.enqueue(replace(self.obs(),receipt_sha256='9'*64))
        self.assertEqual(self.box.verify()['items'],1)
    def test_envelope_pin_conflict_not_overwritten(self):
        self.enqueue()
        with self.assertRaises(ValueError):self.enqueue(sha='2'*64)
    def test_same_job_other_version_distinct(self):
        self.enqueue();self.enqueue(replace(self.obs(),version=2));self.assertEqual(self.box.verify()['items'],2)
    def test_other_provider_distinct(self):
        self.enqueue();self.box.enqueue('kaggle',self.obs(),envelope_sha256='1'*64,expected_tip=self.box.verify()['tip']);self.assertEqual(self.box.verify()['items'],2)
    def test_capacity_preserved(self):
        for i in range(8):self.enqueue(replace(self.obs(),provider_job_id='job_'+str(i)))
        with self.assertRaises(ValueError):self.enqueue(replace(self.obs(),provider_job_id='extra'))
        self.assertEqual(self.box.verify()['items'],8)
    def test_capacity_frozen(self):
        with self.assertRaises(ValueError):self.box.initialize(9)
    def test_bounds(self):
        for x in (0,129,True):
            with self.subTest(x=x),self.assertRaises(ValueError):LearningOutbox(self.root/'new.sqlite').initialize(x)
    def test_stale_anchor_blocks_mutation(self):
        old=self.box.verify()['tip'];self.enqueue()
        with self.assertRaises(ValueError):self.box.enqueue('synthetic',replace(self.obs(),version=2),envelope_sha256='2'*64,expected_tip=old)
    def test_local_projection_tamper(self):
        self.enqueue()
        with sqlite3.connect(self.box.path) as db:db.execute("UPDATE outbox_drafts SET status='DELIVERED'")
        with self.assertRaises(ValueError):self.box.verify()
    def test_event_tamper(self):
        self.enqueue()
        with sqlite3.connect(self.box.path) as db:db.execute("UPDATE outbox_events SET hash=? WHERE seq=2",('a'*64,))
        with self.assertRaises(ValueError):self.box.verify()
    def test_missing_metadata_not_reset(self):
        self.enqueue()
        with sqlite3.connect(self.box.path) as db:db.execute('DELETE FROM outbox_meta')
        with self.assertRaises(ValueError):self.box.initialize(8)
    def test_no_implicit_init(self):
        with self.assertRaises(ValueError):LearningOutbox(self.root/'absent.sqlite').verify()
    def test_reject_other_queue(self):
        p=self.root/'queue.sqlite';s=Store(p);s.initialize();before=s.verify()
        with self.assertRaises(ValueError):LearningOutbox(p).initialize()
        self.assertEqual(s.verify(),before)
    def test_symlink_db(self):
        p=self.root/'link.sqlite';p.symlink_to(self.box.path)
        with self.assertRaises(ValueError):LearningOutbox(p)
    def test_invalidate_and_no_reuse(self):
        x=self.enqueue();s=self.box.invalidate(x['key'],reason='MEASUREMENT_ERROR',review_id='review_1',expected_tip=x['outbox']['tip'])
        self.assertEqual(s['states'][x['key']],'INVALIDATED');self.assertEqual(self.box.pending(expected_tip=s['tip']),[])
        with self.assertRaises(ValueError):self.enqueue()
    def test_invalid_reason_rejected(self):
        x=self.enqueue()
        with self.assertRaises(ValueError):self.box.invalidate(x['key'],reason='ADOPTED',review_id='review',expected_tip=x['outbox']['tip'])
    def test_failed_run_preserved(self):
        x=self.enqueue(replace(self.obs(),state='FAILED',failure='OOM',completed_units=2))
        draft=self.box.pending(expected_tip=x['outbox']['tip'])[0];self.assertEqual(draft['plan']['status'],'REPAIR_OR_VERIFY_FIRST')
    def test_pending_not_authority_or_memory_write(self):
        x=self.enqueue();d=self.box.pending(expected_tip=x['outbox']['tip'])[0]
        for k in ('canonical_writer_attached','provenance_attested','scientific_results_included','execution_allowed','activation_allowed'):self.assertIs(d[k],False)
    def test_concurrent_clients_no_duplicate(self):
        # External CAS serializes mutations; stale contender must retry after reading.
        tip=self.box.verify()['tip']
        def run(_):
            try:return LearningOutbox(self.box.path).enqueue('synthetic',self.obs(),envelope_sha256='1'*64,expected_tip=tip)
            except ValueError:return None
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(run,range(2)))
        self.assertEqual(sum(x is not None for x in results),1);self.assertEqual(self.box.verify()['items'],1);self.assertTrue(self.enqueue()['duplicate'])
    def test_snapshot_restore_exact_and_no_delivery(self):
        x=self.enqueue();p,s=self.snapshot();r=restore_outbox(p,self.root/'restore',expected_sha256=s['sha256'],expected_tip=s['tip'])
        self.assertEqual(r['outbox'],self.box.verify());self.assertIs(r['auto_delivery_allowed'],False)
        b=LearningOutbox(self.root/'restore/outbox.sqlite');d=b.enqueue('synthetic',self.obs(),envelope_sha256='1'*64,expected_tip=s['tip']);self.assertTrue(d['duplicate'])
    def test_invalidated_snapshot_preserved(self):
        x=self.enqueue();self.box.invalidate(x['key'],reason='SOURCE_INVALIDATED',review_id='r',expected_tip=x['outbox']['tip']);p,s=self.snapshot()
        r=restore_outbox(p,self.root/'restore',expected_sha256=s['sha256'],expected_tip=s['tip']);self.assertEqual(r['outbox']['states'][x['key']],'INVALIDATED')
    def test_snapshot_hash_mismatch(self):
        self.enqueue();p,s=self.snapshot()
        with self.assertRaises(ValueError):restore_outbox(p,self.root/'restore',expected_sha256='a'*64,expected_tip=s['tip'])
        self.assertFalse((self.root/'restore').exists())
    def test_snapshot_wrong_tip(self):
        p,s=self.snapshot()
        with self.assertRaises(ValueError):restore_outbox(p,self.root/'restore',expected_sha256=s['sha256'],expected_tip='b'*64)
    def test_export_never_overwrites(self):
        p,s=self.snapshot()
        with self.assertRaises(FileExistsError):export_outbox(self.box,p,expected_tip=s['tip'])
    def test_restore_never_overwrites(self):
        p,s=self.snapshot();dest=self.root/'restore';dest.mkdir()
        with self.assertRaises(FileExistsError):restore_outbox(p,dest,expected_sha256=s['sha256'],expected_tip=s['tip'])
    def test_snapshot_closed_schema(self):
        p,s=self.snapshot();pack=json.loads(p.read_text());pack['activation_allowed']=True;raw=json.dumps(pack).encode();p.write_bytes(raw)
        with self.assertRaises(ValueError):restore_outbox(p,self.root/'restore',expected_sha256=hashlib.sha256(raw).hexdigest(),expected_tip=s['tip'])
    def test_import_enqueues_once(self):
        p,s=self.envelope();x=self.ingest(p,s);y=self.ingest(p,s);self.assertFalse(x['duplicate']);self.assertTrue(y['duplicate']);self.assertIs(x['remote_provenance_attested'],False)
    def test_import_pin_mismatch(self):
        p,s=self.envelope()
        with self.assertRaises(ValueError):self.ingest(p,'a'*64)
        self.assertEqual(self.box.verify()['items'],0)
    def test_import_wrong_job(self):
        p,s=self.envelope()
        with self.assertRaises(ValueError):self.ingest(p,s,expected_job_id='other')
    def test_import_wrong_version(self):
        p,s=self.envelope()
        with self.assertRaises(ValueError):self.ingest(p,s,expected_version=2)
    def test_import_wrong_provider(self):
        p,s=self.envelope()
        with self.assertRaises(ValueError):self.ingest(p,s,expected_provider='kaggle')
    def test_running_import_rejected(self):
        p,s=self.envelope(self.pack(replace(self.obs(),state='RUNNING')))
        with self.assertRaises(ValueError):self.ingest(p,s)
    def test_outcomes_and_free_text_rejected(self):
        for key in ('pnl','hypothesis','winner','instructions'):
            pack=self.pack();pack[key]='run command';p,s=self.envelope(pack)
            with self.subTest(key=key),self.assertRaises(ValueError):self.ingest(p,s)
    def test_unknown_observation_field(self):
        pack=self.pack();pack['observation']['target_percent']=60;p,s=self.envelope(pack)
        with self.assertRaises(ValueError):self.ingest(p,s)
    def test_duplicate_json_keys_rejected(self):
        p,s=self.envelope();raw=b'{"schema":"x","schema":"research_ops_technical_closeout_v1"}';p.write_bytes(raw)
        with self.assertRaises(ValueError):self.ingest(p,hashlib.sha256(raw).hexdigest())
    def test_nonfinite_import_rejected(self):
        pack=self.pack();pack['observation']['wall_seconds']=float('nan');p,s=self.envelope(pack)
        with self.assertRaises(ValueError):self.ingest(p,s)
    def test_unmeasured_rss_rejected(self):
        pack=self.pack();pack['observation']['peak_rss_bytes']=None;p,s=self.envelope(pack)
        with self.assertRaises(ValueError):self.ingest(p,s)
    def test_envelope_symlink_rejected(self):
        p,s=self.envelope();link=self.root/'link.json';link.symlink_to(p)
        with self.assertRaises(OSError):self.ingest(link,s)
    def test_envelope_size_bound(self):
        p=self.root/'big.json';raw=b' '*65537;p.write_bytes(raw)
        with self.assertRaises(ValueError):self.ingest(p,hashlib.sha256(raw).hexdigest())
    def test_cli_import_and_verify(self):
        p,s=self.envelope();tip=self.box.verify()['tip'];buf=io.StringIO()
        with contextlib.redirect_stdout(buf):rc=main(['ingest-closeout',str(p),'--outbox',str(self.box.path),'--expected-sha256',s,'--expected-tip',tip,'--provider','synthetic','--job-id','job_1','--version','1'])
        self.assertEqual(rc,0);self.assertEqual(json.loads(buf.getvalue())['outbox']['items'],1)

    def test_registration_failure_rolls_back_atomically(self):
        before=self.box.verify()
        def fail(*args):raise RuntimeError('synthetic interruption before event')
        old=self.box._event;self.box._event=fail
        try:
            with self.assertRaises(RuntimeError):self.enqueue()
        finally:self.box._event=old
        self.assertEqual(self.box.verify(),before)
    def test_process_crash_recovers_uncommitted_transaction(self):
        before=self.box.verify();ctx=multiprocessing.get_context('fork')
        proc=ctx.Process(target=_crash_uncommitted,args=(str(self.box.path),))
        proc.start();proc.join(5)
        if proc.is_alive():proc.kill();proc.join();self.fail('synthetic crash fixture timed out')
        self.assertEqual(proc.exitcode,19);self.assertEqual(LearningOutbox(self.box.path).verify(),before)
    def test_rehashed_snapshot_bad_projection_rejected_before_restore(self):
        self.enqueue();p,s=self.snapshot();pack=json.loads(p.read_text())
        pack['tables']['outbox_drafts'][0]['status']='DELIVERED'
        raw=json.dumps(pack).encode();p.write_bytes(raw)
        with self.assertRaises(ValueError):restore_outbox(p,self.root/'restore',expected_sha256=hashlib.sha256(raw).hexdigest(),expected_tip=s['tip'])
        self.assertFalse((self.root/'restore').exists())

if __name__=='__main__':unittest.main()
