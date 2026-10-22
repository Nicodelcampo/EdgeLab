"""Synthetic loss/recovery tests only; no remote durability or market execution."""
import base64,contextlib,hashlib,io,json,os,shutil,sqlite3,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from tools.research_ops.store import Store,Plan,Policy,canonical
from tools.research_ops.worker import SCRIPT_SHA256,run_one
from tools.research_ops.snapshots import export_queue,inspect_snapshot,restore_queue,MAX_BYTES
from tools.research_ops.cli import main

class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.source=self.root/'source';self.source.mkdir();self.store=Store(self.source/'queue.sqlite');self.store.initialize();self.output=self.root/'snapshot.json'
    def tearDown(self):self.tmp.cleanup()
    def submit(self,name='JOB'):self.store.submit(Plan(name,'synthetic recovery',SCRIPT_SHA256))
    def export(self):
        tip=self.store.verify()['tip'];r=export_queue(self.store,self.output,snapshot_id='SNAPSHOT-1',expected_tip=tip);return r
    def inspect(self,r):return inspect_snapshot(self.output,expected_sha256=r['snapshot_sha256'],expected_tip=r['event_tip'])
    def restore(self,r,dest=None):return restore_queue(self.output,dest or self.root/'restored',expected_sha256=r['snapshot_sha256'],expected_tip=r['event_tip'])
    def rewrite(self,r,change):
        pack=json.loads(self.output.read_bytes());change(pack);raw=(canonical(pack)+'\n').encode();self.output.write_bytes(raw);return {**r,'snapshot_sha256':hashlib.sha256(raw).hexdigest()}
    def test_empty_queue_roundtrip(self):
        r=self.export();out=self.restore(r);self.assertEqual(out['state'],self.store.verify());self.assertFalse(out['auto_resume_allowed'])
    def test_queued_fifo_preserved(self):
        self.submit('B');self.submit('A');r=self.export();self.restore(r);s=Store(self.root/'restored/queue.sqlite');self.assertEqual(s.claim().job_id,'B')
    def test_running_not_replayed_or_refunded(self):
        self.submit();self.store.claim();r=self.export();out=self.restore(r);self.assertEqual(out['state']['attempts_reserved'],1);self.assertEqual(out['running_jobs_require_external_liveness_review'],['JOB']);self.assertIsNone(Store(self.root/'restored/queue.sqlite').claim());self.assertFalse(out['budget_refunded']);self.assertFalse(out['jobs_replayed'])
    def test_success_receipt_roundtrip(self):
        self.submit();run_one(self.store);r=self.export();out=self.restore(r);self.assertEqual(out['state'],self.store.verify());self.assertEqual((self.root/'restored/receipts/JOB.json').read_bytes(),(self.source/'receipts/JOB.json').read_bytes())
    def test_failed_budget_roundtrip(self):
        self.submit();self.store.claim();self.store.finish('JOB','FAILED_TECHNICAL');r=self.export();out=self.restore(r);self.assertEqual(out['state']['attempts_reserved'],1);self.assertEqual(out['state']['states']['JOB'],'FAILED_TECHNICAL')
    def test_interrupted_budget_roundtrip(self):
        self.submit();self.store.claim();self.store.finish('JOB','INTERRUPTED');r=self.export();out=self.restore(r);self.assertEqual(out['state']['states']['JOB'],'INTERRUPTED');self.assertEqual(out['state']['seconds_reserved'],5)
    def test_orphan_receipt_preserved_never_completion(self):
        self.submit();self.store.claim();d=self.source/'receipts';d.mkdir();(d/'JOB.json').write_bytes(b'{"status":"PASS"}\n');r=self.export();out=self.inspect(r);self.assertEqual(out['uncommitted_receipts_require_review'],['JOB']);self.restore(r);self.assertEqual((self.root/'restored/receipts/JOB.json').read_bytes(),b'{"status":"PASS"}\n');self.assertEqual(Store(self.root/'restored/queue.sqlite').verify()['states']['JOB'],'RUNNING')
    def test_snapshot_not_remote_claim(self):
        r=self.export();out=self.inspect(r)
        for item in (r,out):
            for field in ('remote_copy_verified','external_latest_anchor_verified','auto_resume_allowed','market_execution_allowed'):self.assertFalse(item[field])
    def test_source_tip_unchanged(self):
        self.submit();tip=self.store.verify()['tip'];self.export();self.assertEqual(self.store.verify()['tip'],tip)
    def test_no_output_overwrite(self):
        self.output.write_text('existing')
        with self.assertRaises(FileExistsError):self.export()
        self.assertEqual(self.output.read_text(),'existing')
    def test_export_stale_tip_rejected(self):
        tip=self.store.verify()['tip'];self.submit()
        with self.assertRaises(ValueError):export_queue(self.store,self.output,snapshot_id='S',expected_tip=tip)
        self.assertFalse(self.output.exists())
    def test_old_valid_snapshot_rejected_by_latest_tip(self):
        r=self.export();self.submit()
        with self.assertRaises(ValueError):inspect_snapshot(self.output,expected_sha256=r['snapshot_sha256'],expected_tip=self.store.verify()['tip'])
    def test_hash_tamper_rejected(self):
        r=self.export();self.output.write_bytes(self.output.read_bytes()+b' ')
        with self.assertRaises(ValueError):self.inspect(r)
    def test_wrong_external_hash(self):
        r=self.export();r['snapshot_sha256']='0'*64
        with self.assertRaises(ValueError):self.inspect(r)
    def test_expected_hash_mandatory(self):
        self.export()
        with self.assertRaises(ValueError):inspect_snapshot(self.output,expected_sha256=None,expected_tip='0'*64)
    def test_destination_not_created_on_invalid_hash(self):
        r=self.export();r['snapshot_sha256']='0'*64
        with self.assertRaises(ValueError):self.restore(r)
        self.assertFalse((self.root/'restored').exists())
    def test_no_destination_overwrite(self):
        r=self.export();d=self.root/'restored';d.mkdir();(d/'keep').write_text('safe')
        with self.assertRaises(FileExistsError):self.restore(r)
        self.assertEqual((d/'keep').read_text(),'safe')
    def test_destination_symlink_rejected(self):
        r=self.export();d=self.root/'restored';d.symlink_to(self.source,target_is_directory=True)
        with self.assertRaises(FileExistsError):self.restore(r)
    def test_snapshot_symlink_rejected(self):
        r=self.export();link=self.root/'link';link.symlink_to(self.output)
        with self.assertRaises(OSError):inspect_snapshot(link,expected_sha256=r['snapshot_sha256'],expected_tip=r['event_tip'])
    def test_fifo_rejected_without_blocking(self):
        self.export();fifo=self.root/'fifo';os.mkfifo(fifo)
        with self.assertRaises(ValueError):inspect_snapshot(fifo,expected_sha256='0'*64,expected_tip='0'*64)
    def test_oversize_snapshot(self):
        r=self.export()
        with self.output.open('wb') as f:f.truncate(MAX_BYTES+1)
        with self.assertRaises(ValueError):self.inspect(r)
    def test_invalid_snapshot_id(self):
        for name in ('../x','',None):
            with self.assertRaises(ValueError):export_queue(self.store,self.output,snapshot_id=name,expected_tip=self.store.verify()['tip'])
    def test_duplicate_json_keys(self):
        r=self.export();raw=self.output.read_bytes().replace(b'{',b'{"scope":"synthetic",',1);self.output.write_bytes(raw);r['snapshot_sha256']=hashlib.sha256(raw).hexdigest()
        with self.assertRaises(ValueError):self.inspect(r)
    def test_nonfinite_json(self):
        r=self.export();raw=b'{"value":NaN}';self.output.write_bytes(raw);r['snapshot_sha256']=hashlib.sha256(raw).hexdigest()
        with self.assertRaises(ValueError):self.inspect(r)
    def test_unknown_top_field(self):
        r=self.rewrite(self.export(),lambda p:p.update(command='do not execute'))
        with self.assertRaises(ValueError):self.inspect(r)
    def test_market_scope_rejected(self):
        r=self.rewrite(self.export(),lambda p:p.update(scope='market'))
        with self.assertRaises(ValueError):self.inspect(r)
    def test_projection_tamper(self):
        self.submit();r=self.rewrite(self.export(),lambda p:p['jobs'][0].update(status='SUCCEEDED_TECHNICAL'))
        with self.assertRaises(ValueError):self.inspect(r)
    def test_budget_reset_rejected(self):
        self.submit();self.store.claim();r=self.rewrite(self.export(),lambda p:p['policy'][0].update(attempts=0))
        with self.assertRaises(ValueError):self.inspect(r)
    def test_event_chain_tamper(self):
        r=self.rewrite(self.export(),lambda p:p['events'][0].update(hash='0'*64))
        with self.assertRaises(ValueError):self.inspect(r)
    def test_receipt_removed(self):
        self.submit();run_one(self.store);r=self.rewrite(self.export(),lambda p:p.update(receipts={}))
        with self.assertRaises(ValueError):self.inspect(r)
    def test_receipt_tampered(self):
        self.submit();run_one(self.store);r=self.rewrite(self.export(),lambda p:p['receipts'].update(JOB=base64.b64encode(b'changed').decode()))
        with self.assertRaises(ValueError):self.inspect(r)
    def test_receipt_path_traversal(self):
        r=self.rewrite(self.export(),lambda p:p['receipts'].update({'../outside':'eA=='}))
        with self.assertRaises(ValueError):self.inspect(r)
    def test_invalid_base64(self):
        self.submit();run_one(self.store);r=self.rewrite(self.export(),lambda p:p['receipts'].update(JOB='!!'))
        with self.assertRaises(ValueError):self.inspect(r)
    def test_unknown_receipt_on_disk_blocks_export(self):
        d=self.source/'receipts';d.mkdir();(d/'UNKNOWN.json').write_text('{}')
        with self.assertRaises(ValueError):self.export()
        self.assertFalse(self.output.exists())
    def test_unexpected_receipt_file_blocks_export(self):
        d=self.source/'receipts';d.mkdir();(d/'metadata.txt').write_text('x')
        with self.assertRaises(ValueError):self.export()
    def test_receipt_folder_symlink_blocks_export(self):
        d=self.root/'other';d.mkdir();(self.source/'receipts').symlink_to(d,target_is_directory=True)
        with self.assertRaises(ValueError):self.export()
    def test_captured_bytes_immutable(self):
        r=self.export();self.submit();out=self.inspect(r);self.assertEqual(out['state']['jobs'],0)
    def test_cli_inspect_does_not_initialize_queue(self):
        r=self.export();queue=self.root/'unexpected/queue.sqlite'
        with contextlib.redirect_stdout(io.StringIO()):main(['--state',str(queue),'inspect-snapshot',str(self.output),'--expected-sha256',r['snapshot_sha256'],'--expected-tip',r['event_tip']])
        self.assertFalse(queue.parent.exists())
    def test_cli_restore_does_not_initialize_default_queue(self):
        r=self.export();queue=self.root/'unexpected/queue.sqlite'
        with contextlib.redirect_stdout(io.StringIO()):main(['--state',str(queue),'restore-queue',str(self.output),str(self.root/'restored'),'--expected-sha256',r['snapshot_sha256'],'--expected-tip',r['event_tip']])
        self.assertFalse(queue.parent.exists())
    def test_source_invalid_before_export(self):
        with contextlib.closing(sqlite3.connect(self.store.path)) as db, db:db.execute('UPDATE policy SET attempts=1')   # cerrar, no sólo commit
        with self.assertRaises(ValueError):self.export()
    def test_snapshot_file_permissions(self):
        self.export();self.assertEqual(self.output.stat().st_mode&0o777,0o600)
    def test_restored_permissions(self):
        r=self.export();self.restore(r);self.assertEqual((self.root/'restored').stat().st_mode&0o777,0o700);self.assertEqual((self.root/'restored/queue.sqlite').stat().st_mode&0o777,0o600)
    def test_malformed_json(self):
        r=self.export();raw=b'{';self.output.write_bytes(raw);r['snapshot_sha256']=hashlib.sha256(raw).hexdigest()
        with self.assertRaises(ValueError):self.inspect(r)
    def test_event_table_bound(self):
        r=self.rewrite(self.export(),lambda p:p.update(events=p['events']*1025))
        with self.assertRaises(ValueError):self.inspect(r)

    def test_simulated_host_loss_restores_receipts_budget_and_running(self):
        self.submit('DONE');run_one(self.store);self.submit('UNCERTAIN');self.store.claim();before=self.store.verify();r=self.export()
        shutil.rmtree(self.source)  # Only this test's temporary fixture, not workspace data.
        out=self.restore(r);self.assertEqual(out['state'],before);self.assertEqual(out['running_jobs_require_external_liveness_review'],['UNCERTAIN']);self.assertEqual(out['state']['attempts_reserved'],2);self.assertTrue((self.root/'restored/receipts/DONE.json').exists());self.assertIsNone(Store(self.root/'restored/queue.sqlite').claim())
    def test_partial_export_is_not_retried_or_overwritten(self):
        def partial(path,raw):Path(path).write_bytes(raw[:10]);raise OSError('simulated disk failure')
        with patch('tools.research_ops.snapshots._exclusive',side_effect=partial):
            with self.assertRaises(OSError):self.export()
        self.assertEqual(self.output.stat().st_size,10)
        with self.assertRaises(FileExistsError):self.export()
    def test_wrong_snapshot_schema(self):
        r=self.rewrite(self.export(),lambda p:p.update(schema='market_replay_v1'))
        with self.assertRaises(ValueError):self.inspect(r)
    def test_restoration_does_not_run_worker(self):
        self.submit();r=self.export()
        with patch('tools.research_ops.worker.run_one',side_effect=AssertionError('must not dispatch')):self.restore(r)
        self.assertEqual(Store(self.root/'restored/queue.sqlite').verify()['states']['JOB'],'QUEUED')
