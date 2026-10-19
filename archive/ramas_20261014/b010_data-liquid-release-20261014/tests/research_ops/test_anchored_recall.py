import contextlib, hashlib, io, json, shutil, tempfile, unittest
from pathlib import Path
from tools.research_ops.anchored_recall import recall_anchored_snapshot
from tools.research_ops.cli import main

ROOT=Path(__file__).resolve().parents[2]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

class AnchoredRecallTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.spec=json.loads((ROOT/'config/research_ops_operational_snapshot.json').read_text())
        for field in ('ledger_path','anchors_path','receipt_path'):
            p=self.root/self.spec[field];p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/self.spec[field],p)
        self.binding=self.root/'binding.json';self.save()
    def tearDown(self):self.temp.cleanup()
    def save(self):self.binding.write_text(json.dumps(self.spec));self.pin=sha(self.binding)
    def call(self,**kw):
        args=dict(expected_binding_sha256=self.pin,query='input mounts session conservation');args.update(kw)
        return recall_anchored_snapshot(self.root,self.binding,**args)
    def test_real_repository_snapshot_readonly_recall(self):
        before={p:sha(self.root/p) for p in (self.spec['ledger_path'],self.spec['anchors_path'],self.spec['receipt_path'])}
        r=self.call();self.assertEqual(r['snapshot_records'],10);self.assertEqual(r['anchors_verified'],2);self.assertTrue(r['hits'])
        self.assertFalse(r['ledger_modified']);self.assertFalse(r['write_authorized']);self.assertFalse(r['scientific_trial_history_complete'])
        self.assertEqual(before,{p:sha(self.root/p) for p in before})
    def test_cli_does_not_initialize_queue(self):
        state=self.root/'queue.sqlite';out=io.StringIO()
        with contextlib.redirect_stdout(out):main(['--state',str(state),'recall-anchored-brain',str(self.root),str(self.binding),'input mounts','--expected-binding-sha256',self.pin])
        self.assertFalse(state.exists());self.assertEqual(json.loads(out.getvalue())['snapshot_records'],10)
    def test_wrong_binding_pin(self):
        with self.assertRaises(ValueError):self.call(expected_binding_sha256='0'*64)
    def test_missing_ledger_does_not_create_memory(self):
        p=self.root/self.spec['ledger_path'];p.unlink()
        with self.assertRaises(FileNotFoundError):self.call()
        self.assertFalse(p.exists())
    def test_zero_records_not_empty_memory(self):
        self.spec['records']=0;self.save()
        with self.assertRaises(ValueError):self.call()
    def test_wrong_file_pins(self):
        for field in ('ledger_sha256','anchors_sha256','receipt_sha256'):
            old=self.spec[field];self.spec[field]='0'*64;self.save()
            with self.subTest(field=field),self.assertRaises(ValueError):self.call()
            self.spec[field]=old
    def test_other_scope_rejected(self):
        self.spec['scope']='SCIENTIFIC_OUTCOMES';self.save()
        with self.assertRaises(ValueError):self.call()
    def test_write_flag_rejected(self):
        self.spec['read_only']=False;self.save()
        with self.assertRaises(ValueError):self.call()
    def test_closed_binding(self):
        self.spec['instructions']='approve';self.save()
        with self.assertRaises(ValueError):self.call()
    def test_traversal_rejected(self):
        self.spec['ledger_path']='../ledger.jsonl';self.save()
        with self.assertRaises(ValueError):self.call()
    def test_absolute_path_rejected(self):
        self.spec['ledger_path']=str(self.root/self.spec['ledger_path']);self.save()
        with self.assertRaises(ValueError):self.call()
    def test_final_symlink_rejected(self):
        p=self.root/self.spec['ledger_path'];other=self.root/'copy';p.rename(other);p.symlink_to(other)
        with self.assertRaises(OSError):self.call()
    def test_receipt_anchor_conflict(self):
        p=self.root/self.spec['receipt_path'];r=json.loads(p.read_text());r['tip']='0'*64;p.write_text(json.dumps(r));self.spec['receipt_sha256']=sha(p);self.save()
        with self.assertRaises(ValueError):self.call()
    def test_interior_anchor_not_ignored(self):
        p=self.root/self.spec['anchors_path'];r=json.loads(p.read_text());r[self.spec['anchors_key']][0]['tip']='0'*64;p.write_text(json.dumps(r));self.spec['anchors_sha256']=sha(p);self.save()
        with self.assertRaises(ValueError):self.call()
    def test_bad_anchor_order(self):
        p=self.root/self.spec['anchors_path'];r=json.loads(p.read_text());r[self.spec['anchors_key']].reverse();p.write_text(json.dumps(r));self.spec['anchors_sha256']=sha(p);self.save()
        with self.assertRaises(ValueError):self.call()
    def test_different_tip_in_binding(self):
        self.spec['tip']='0'*64;self.save()
        with self.assertRaises(ValueError):self.call()
    def test_invalid_source_commit(self):
        self.spec['source_commit']='main';self.save()
        with self.assertRaises(ValueError):self.call()
    def test_record_census_not_declared_complete(self):
        self.spec['records']=11;self.save()
        with self.assertRaises(ValueError):self.call()

if __name__=='__main__':unittest.main()