import tempfile,unittest,sqlite3
from pathlib import Path
from tools.research_ops.remote_watch import RemoteWatch,identity

class WatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.p=Path(self.tmp.name)/'watch.sqlite';self.w=RemoteWatch(self.p);self.s=self.w.initialize(max_attempts=2,max_calls=3)
        self.i=dict(account='nicolasbuttaro',kernel_id=123,version=1,source_commit='a'*40,bundle_sha256='b'*64,plan_sha256='c'*64)
        self.s=self.w.register(self.i,expected_tip=self.s['tip_sha256'])
    def tearDown(self):self.tmp.cleanup()
    def reserve(self):
        self.s=self.w.reserve(self.i,expected_tip=self.s['tip_sha256']);return self.s['ticket']
    def record(self,status):
        t=self.reserve();self.s=self.w.record(self.i,ticket=t,status=status,response_sha256='d'*64,expected_tip=self.s['tip_sha256'])
    def test_restart_and_terminal_no_retry(self):
        self.record('RUNNING');self.w=RemoteWatch(self.p);self.s=self.w.snapshot();self.record('ERROR')
        with self.assertRaises(ValueError):self.reserve()
        self.assertFalse(self.s['automatic_retry_allowed']);self.assertEqual(self.s['state']['calls_reserved'],2)
    def test_complete_not_success(self):
        self.record('COMPLETE');self.assertFalse(self.s['complete_means_verified_success']);self.assertFalse(self.s['canonical_brain_written'])
    def test_outstanding_does_not_refund_after_crash(self):
        self.reserve();self.w=RemoteWatch(self.p);self.s=self.w.snapshot()
        with self.assertRaises(ValueError):self.reserve()
        self.assertEqual(self.s['state']['calls_reserved'],1)
    def test_unavailable_consumes_budget(self):
        for _ in range(3):self.record('UNAVAILABLE')
        with self.assertRaises(ValueError):self.reserve()
    def test_frozen_policy(self):
        with self.assertRaises(ValueError):self.w.initialize(max_attempts=2,max_calls=4)
    def test_stale_tip(self):
        old=self.s['tip_sha256'];self.reserve()
        with self.assertRaises(ValueError):self.w.snapshot(expected_tip=old)
    def test_registration_idempotent(self):
        r=self.w.register(self.i,expected_tip=self.s['tip_sha256']);self.assertEqual(r['tip_sha256'],self.s['tip_sha256'])
    def test_identity_conflict(self):
        for k in ('source_commit','bundle_sha256','plan_sha256'):
            v=dict(self.i);v[k]='e'*len(v[k])
            with self.assertRaises(ValueError):self.w.register(v,expected_tip=self.s['tip_sha256'])
    def test_new_version_separate(self):
        v=dict(self.i,version=2);r=self.w.register(v,expected_tip=self.s['tip_sha256']);self.assertEqual(len(r['state']['attempts']),2)
        with self.assertRaises(ValueError):self.w.register(dict(self.i,version=3),expected_tip=r['tip_sha256'])
    def test_regression(self):
        self.record('RUNNING');t=self.reserve()
        with self.assertRaises(ValueError):self.w.record(self.i,ticket=t,status='QUEUED',response_sha256='d'*64,expected_tip=self.s['tip_sha256'])
    def test_no_arbitrary_narrative(self):
        with self.assertRaises(ValueError):identity(dict(self.i,url='https://example.test/private'))
        t=self.reserve()
        with self.assertRaises(ValueError):self.w.record(self.i,ticket=t,status='raw text',response_sha256='d'*64,expected_tip=self.s['tip_sha256'])
    def test_tamper(self):
        db=sqlite3.connect(self.p);db.execute("update watch_events set hash=?",('f'*64,));db.commit();db.close()
        with self.assertRaises(ValueError):self.w.snapshot()
    def test_foreign_and_symlink(self):
        p=Path(self.tmp.name)/'other';db=sqlite3.connect(p);db.execute('create table private_data(x)');db.close()
        with self.assertRaises(ValueError):RemoteWatch(p).initialize()
        q=Path(self.tmp.name)/'link';q.symlink_to(self.p)
        with self.assertRaises(ValueError):RemoteWatch(q)
    def test_boolean_identity_ticket_rejected(self):
        with self.assertRaises(ValueError):identity(dict(self.i,version=True))
        self.reserve()
        with self.assertRaises(ValueError):self.w.record(self.i,ticket=True,status='ERROR',response_sha256='d'*64,expected_tip=self.s['tip_sha256'])

if __name__=='__main__':unittest.main()
