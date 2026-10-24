"""Operational synthetic tests, no economic outcomes and no external data."""
import contextlib,io,json,os,shutil,sqlite3,tempfile,threading,unittest,subprocess
from unittest.mock import patch,MagicMock
from dataclasses import replace
from pathlib import Path
from tools.research_ops.store import Store,Policy,Plan
from tools.research_ops.worker import SCRIPT_SHA256,run_one
from tools.research_ops.observer import observe
from tools.research_ops.cli import main

class OpsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.store=Store(self.root/'queue.sqlite');self.store.initialize()
    def tearDown(self):self.tmp.cleanup()
    def plan(self,name='job',**kw):return Plan(name,'synthetic test',SCRIPT_SHA256,**kw)
    def submit(self,name='job',**kw):self.store.submit(self.plan(name,**kw))
    def mutate(self,sql):
        with contextlib.closing(sqlite3.connect(self.store.path)) as db, db:db.execute(sql)   # `with connect()` sólo hace commit; closing la cierra
    def test_initialization_idempotent(self):
        tip=self.store.verify()['tip'];self.store.initialize();self.assertEqual(self.store.verify()['tip'],tip)
    def test_policy_frozen(self):
        with self.assertRaises(ValueError):self.store.initialize(Policy(4,30))
    def test_explicit_initialization(self):
        with self.assertRaises(ValueError):Store(self.root/'absent').verify()
    def test_invalid_policy_bools(self):
        with self.assertRaises(ValueError):Policy(True,5).validate()
    def test_invalid_policy_range(self):
        with self.assertRaises(ValueError):Policy(101,5).validate()
    def test_id_path_traversal(self):
        with self.assertRaises(ValueError):self.store.submit(self.plan('../escape'))
    def test_market_scope_rejected(self):
        with self.assertRaises(ValueError):self.store.submit(self.plan(scope='market'))
    def test_holdout_scope_rejected(self):
        with self.assertRaises(ValueError):self.store.submit(self.plan(scope='holdout'))
    def test_arbitrary_action_rejected(self):
        with self.assertRaises(ValueError):self.store.submit(self.plan(action='shell'))
    def test_timeout_bounded(self):
        for timeout in [0,31,True]:
            with self.assertRaises(ValueError):self.store.submit(self.plan(timeout_seconds=timeout))
    def test_unknown_json_fields_rejected(self):
        with self.assertRaises(TypeError):Plan(**{**self.plan().__dict__,'command':'rm -rf'})
    def test_duplicate_no_overwrite(self):
        self.submit();tip=self.store.verify()['tip']
        with self.assertRaises(ValueError):self.store.submit(replace(self.plan(),hypothesis='changed'))
        self.assertEqual(self.store.verify()['tip'],tip)
    def test_fifo_and_single_running(self):
        self.submit('one');self.submit('two');self.assertEqual(self.store.claim().job_id,'one');self.assertIsNone(self.store.claim());self.store.finish('one','INTERRUPTED');self.assertEqual(self.store.claim().job_id,'two')
    def test_budget_charged_before_execution(self):
        self.submit(timeout_seconds=5);self.store.claim();s=self.store.verify();self.assertEqual((s['attempts_reserved'],s['seconds_reserved']),(1,5))
    def test_interrupted_no_refund_or_retry(self):
        self.submit();self.store.claim();self.store.finish('job','INTERRUPTED');self.assertIsNone(self.store.claim());self.assertEqual(self.store.verify()['attempts_reserved'],1)
    def test_attempt_budget(self):
        s=Store(self.root/'other.sqlite');s.initialize(Policy(1,30))
        for name in ['a','b']:s.submit(self.plan(name))
        s.claim();s.finish('a','INTERRUPTED')
        with self.assertRaises(ValueError):s.claim()
        self.assertEqual(s.verify()['attempts_reserved'],1)
    def test_wall_budget(self):
        s=Store(self.root/'other.sqlite');s.initialize(Policy(3,5));s.submit(self.plan('a',timeout_seconds=6))
        with self.assertRaises(ValueError):s.claim()
        self.assertEqual(s.verify()['attempts_reserved'],0)
    def test_finite_proposal_count(self):
        s=Store(self.root/'other.sqlite');s.initialize(Policy(1,30))
        for i in range(4):s.submit(self.plan(str(i)))
        with self.assertRaises(ValueError):s.submit(self.plan('fifth'))
    def test_reopen_is_durable(self):
        self.submit();self.store.claim();self.assertEqual(Store(self.store.path).verify()['states']['job'],'RUNNING');self.assertIsNone(Store(self.store.path).claim())
    def test_projection_tampering(self):
        self.submit();self.mutate("UPDATE jobs SET status='SUCCEEDED_TECHNICAL'")
        with self.assertRaises(ValueError):self.store.verify()
    def test_budget_tampering(self):
        self.mutate('UPDATE policy SET attempts=1')
        with self.assertRaises(ValueError):self.store.claim()
    def test_event_tampering(self):
        self.mutate("UPDATE events SET body='{}'")
        with self.assertRaises((ValueError,KeyError)):self.store.verify()
    def test_external_tip_detects_valid_prefix_rollback(self):
        backup=self.root/'prefix.sqlite';shutil.copy2(self.store.path,backup);self.submit();tip=self.store.verify()['tip'];shutil.copy2(backup,self.store.path);self.store.verify()
        with self.assertRaises(ValueError):self.store.verify(tip)
    def test_concurrent_claims(self):
        self.submit('one');self.submit('two');barrier=threading.Barrier(3);results=[];errors=[]
        def claim():
            try:barrier.wait();p=Store(self.store.path).claim();results.append(p.job_id if p else None)
            except Exception as e:errors.append(e)
        threads=[threading.Thread(target=claim) for _ in range(2)]
        for t in threads:t.start()
        barrier.wait()
        for t in threads:t.join()
        self.assertFalse(errors);self.assertEqual(results.count('one'),1);self.assertEqual(results.count(None),1);self.store.verify()
    def test_terminal_transition_blocked(self):
        self.submit()
        with self.assertRaises(ValueError):self.store.finish('job','INTERRUPTED')
    def test_success_without_receipt_rejected(self):
        self.submit();self.store.claim()
        with self.assertRaises(ValueError):self.store.finish('job','SUCCEEDED_TECHNICAL')
    @unittest.skipUnless(os.name=='posix','POSIX worker only')
    def test_real_synthetic_subprocess(self):
        self.submit();r=run_one(self.store);self.assertEqual(r['status'],'SUCCEEDED_TECHNICAL');self.assertFalse(r['market_data_opened']);self.store.verify();self.assertIsNone(run_one(self.store))
    @unittest.skipUnless(os.name=='posix','POSIX worker only')
    def test_unrecognized_protocol_is_failed_and_charged(self):
        self.store.submit(replace(self.plan(),protocol_sha256='f'*64));r=run_one(self.store);self.assertEqual(r['status'],'FAILED_TECHNICAL');self.assertEqual(self.store.verify()['attempts_reserved'],1)
    @unittest.skipUnless(os.name=='posix','POSIX worker only')
    def test_receipt_tampering(self):
        self.submit();run_one(self.store);(self.root/'receipts/job.json').write_text('{}')
        with self.assertRaises(ValueError):self.store.verify()
    @unittest.skipUnless(os.name=='posix','POSIX worker only')
    def test_timeout_kills_group_and_charges_attempt(self):
        self.submit();process=MagicMock();process.pid=23456;process.wait.side_effect=[subprocess.TimeoutExpired('fixed-task',5),None]
        with patch('tools.research_ops.worker.subprocess.Popen',return_value=process),patch('tools.research_ops.worker.os.killpg') as kill:
            r=run_one(self.store)
        kill.assert_called_once();self.assertEqual(r['status'],'FAILED_TECHNICAL');self.assertEqual(self.store.verify()['attempts_reserved'],1)
    @unittest.skipUnless(os.name=='posix','POSIX worker only')
    def test_existing_receipt_never_overwritten(self):
        self.submit();d=self.root/'receipts';d.mkdir();(d/'job.json').write_text('existing')
        with self.assertRaises(FileExistsError):run_one(self.store)
        self.assertEqual((d/'job.json').read_text(),'existing');self.assertEqual(self.store.verify()['states']['job'],'RUNNING');self.assertIsNone(self.store.claim())
    @unittest.skipUnless(os.name=='posix','POSIX worker only')
    def test_missing_receipt_blocks_reuse(self):
        self.submit();run_one(self.store);(self.root/'receipts/job.json').unlink()
        with self.assertRaises(ValueError):self.store.claim()
    def test_symlink_database(self):
        target=self.root/'link';target.symlink_to(self.store.path)
        with self.assertRaises(ValueError):Store(target)
    def test_observer_missing_not_completed(self):
        self.assertEqual(observe(self.root/'missing')['status'],'UNAVAILABLE')
    def test_observer_read_only_and_not_liveness_claim(self):
        p=self.root/'status.json';p.write_text(json.dumps({'status':'RUNNING_RECOVERED_CAMPAIGNS','active_contract':'MNQ_12-25','stage':'longevity'}));old=p.read_bytes();r=observe(p);self.assertEqual(r['status'],'OBSERVED');self.assertFalse(r['completion_inferred']);self.assertFalse(r['controller_or_worker_liveness_verified']);self.assertEqual(old,p.read_bytes())
    def test_observer_rejects_oversize(self):
        p=self.root/'big';p.write_text('x'*65537);self.assertEqual(observe(p)['status'],'REJECTED_OVERSIZE')
    def test_observer_rejects_unknown(self):
        p=self.root/'unknown';p.write_text('{"status":"CONFIRMED_EDGE"}');self.assertEqual(observe(p)['status'],'UNRECOGNIZED')
    def test_observer_symlink(self):
        p=self.root/'link';p.symlink_to(self.store.path);self.assertEqual(observe(p)['status'],'UNAVAILABLE')
    def test_cli_finite_bounds(self):
        with self.assertRaises(ValueError):main(['--state',str(self.store.path),'daemon','--cycles','101','--expected-tip',self.store.verify()['tip']])
    def test_cli_stale_anchor(self):
        tip=self.store.verify()['tip'];self.submit()
        with self.assertRaises(ValueError):main(['--state',str(self.store.path),'daemon','--expected-tip',tip])

class StatusTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
    def tearDown(self):self.tmp.cleanup()
    def test_status_reports_not_initialized_without_raising(self):
        from io import StringIO
        import contextlib,json as _json
        buf=StringIO()
        with contextlib.redirect_stdout(buf):
            main(['--state',str(self.root/'queue.sqlite'),'status','--dispatch-state',str(self.root/'dispatch.sqlite'),'--checkpoint-state',str(self.root/'checkpoints.sqlite')])
        out=_json.loads(buf.getvalue())
        for key in ('queue','dispatch','checkpoint'):
            self.assertEqual(out[key]['status'],'NOT_INITIALIZED_OR_INVALID')
    def test_status_reports_configured_queue(self):
        from io import StringIO
        import contextlib,json as _json
        Store(self.root/'queue.sqlite').initialize()
        buf=StringIO()
        with contextlib.redirect_stdout(buf):
            main(['--state',str(self.root/'queue.sqlite'),'status'])
        out=_json.loads(buf.getvalue())
        self.assertIn('tip',out['queue'])
        self.assertEqual(out['dispatch']['status'],'NOT_CONFIGURED')
        self.assertEqual(out['checkpoint']['status'],'NOT_CONFIGURED')
    def test_status_never_writes_to_disk(self):
        main(['--state',str(self.root/'queue.sqlite'),'status','--dispatch-state',str(self.root/'dispatch.sqlite')])
        self.assertEqual(list(self.root.iterdir()),[])

class DraftTests(unittest.TestCase):
    def draft(self):
        from tools.research_ops.design import Draft
        return Draft('HYP-SYNTHETIC',*["review required" for _ in range(11)])
    def test_structural_not_authority(self):
        from tools.research_ops.design import audit_draft
        r=audit_draft(self.draft());self.assertFalse(r['execution_enabled']);self.assertFalse(r['authorization_verified'])
    def test_self_approval_rejected(self):
        from tools.research_ops.design import audit_draft
        with self.assertRaises(ValueError):audit_draft(replace(self.draft(),status='APPROVED'))
    def test_missing_control_rejected(self):
        from tools.research_ops.design import audit_draft
        with self.assertRaises(ValueError):audit_draft(replace(self.draft(),control_definition=''))
    def test_unknown_execution_field(self):
        from tools.research_ops.design import Draft
        with self.assertRaises(TypeError):Draft(**{**self.draft().__dict__,'execute':True})
    def test_cli_audit_draft(self):
        tmp=tempfile.TemporaryDirectory();path=Path(tmp.name)/'draft.json'
        path.write_text(json.dumps(self.draft().__dict__))
        try:main(['audit-draft',str(path)])
        finally:tmp.cleanup()
    def test_cli_audit_draft_rejects_oversize(self):
        tmp=tempfile.TemporaryDirectory();path=Path(tmp.name)/'draft.json'
        path.write_bytes(b' '*65537)
        try:
            with self.assertRaises(ValueError):main(['audit-draft',str(path)])
        finally:tmp.cleanup()

if __name__=='__main__':unittest.main()
