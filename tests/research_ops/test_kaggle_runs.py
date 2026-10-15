"""Kaggle run control tests. Fake client only: no network, no market data."""
import json, sqlite3, tempfile, unittest
from pathlib import Path
from tools.research_ops.kaggle_runs import KagglePolicy, KaggleRunLedger, KaggleRunController, kernel_dir_identity
from tools.research_ops.cli import main

OWNER, DS = 'nicolasbuttaro', ('nicolasbuttaro/edgelab-data-catalog', 'nicolasbuttaro/edgelab-code-zones')


class FakeClient:
    def __init__(self):
        self.pushed, self.status_map, self.files, self.fail_push = [], {}, {}, False
    def push(self, kernel_dir):
        if self.fail_push:
            raise RuntimeError('network down')
        self.pushed.append(str(kernel_dir)); return len(self.pushed)
    def status(self, ref):
        return self.status_map.get(ref, 'RUNNING')
    def output(self, ref, dest):
        for name, data in self.files.get(ref, {}).items():
            (Path(dest) / name).write_bytes(data)


class KaggleRunTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name)
        self.ledger = KaggleRunLedger(self.root / 'kaggle.sqlite')
        self.ledger.initialize(KagglePolicy(OWNER, DS, max_runs=3, max_concurrent=2))
        self.client = FakeClient(); self.ctl = KaggleRunController(self.ledger, self.client)

    def tearDown(self):
        self.tmp.cleanup()

    def kernel(self, slug='edgelab-k1', **meta):
        d = self.root / slug; d.mkdir(exist_ok=True)
        m = dict(id='%s/%s' % (OWNER, slug), code_file='z.py', is_private=True, enable_internet=False,
                 dataset_sources=[DS[0]], competition_sources=[], kernel_sources=[]); m.update(meta)
        (d / 'kernel-metadata.json').write_text(json.dumps(m)); (d / 'z.py').write_text('print(1)\n')
        return d

    def test_happy_path_reserve_push_poll_collect(self):
        run = self.ctl.submit('R1', self.kernel(), ['out.parquet'])
        self.assertEqual((run['state'], run['version']), ('SUBMITTED', 1))
        self.assertEqual(self.ctl.poll(), {'R1': 'RUNNING'})
        self.client.status_map['nicolasbuttaro/edgelab-k1'] = 'COMPLETE'
        self.assertEqual(self.ctl.poll(), {'R1': 'COMPLETE_TECHNICAL'})
        self.client.files['nicolasbuttaro/edgelab-k1'] = {'out.parquet': b'x' * 10, 'k.log': b'log'}
        run = self.ctl.collect('R1', self.root / 'out')
        self.assertEqual(run['state'], 'COLLECTED_VERIFIED'); self.assertEqual(run['outputs']['out.parquet']['size'], 10)
        st = self.ledger.verify()
        self.assertFalse(st['results_certified']); self.assertFalse(st['retries_allowed']); self.assertEqual(st['active'], [])

    def test_missing_or_empty_output_is_incomplete_never_verified(self):
        self.ctl.submit('R1', self.kernel(), ['a.parquet', 'b.parquet'])
        self.client.status_map['nicolasbuttaro/edgelab-k1'] = 'COMPLETE'; self.ctl.poll()
        self.client.files['nicolasbuttaro/edgelab-k1'] = {'a.parquet': b'x', 'b.parquet': b''}
        self.assertEqual(self.ctl.collect('R1', self.root / 'out')['state'], 'COLLECTION_INCOMPLETE')
        with self.assertRaises(ValueError):
            self.ctl.collect('R1', self.root / 'out2')        # no se re-recolecta ni se sobrescribe

    def test_error_status_fails_without_retry_and_keeps_budget_charged(self):
        self.ctl.submit('R1', self.kernel(), ['o'])
        self.client.status_map['nicolasbuttaro/edgelab-k1'] = 'ERROR'
        self.assertEqual(self.ctl.poll(), {'R1': 'FAILED'})
        self.assertEqual(self.ledger.verify()['remaining_runs'], 2)
        with self.assertRaises(ValueError):
            self.ctl.submit('R1', self.kernel(), ['o'])        # mismo id: nunca se reintenta

    def test_unknown_status_does_not_move_the_ledger(self):
        self.ctl.submit('R1', self.kernel(), ['o'])
        self.client.status_map['nicolasbuttaro/edgelab-k1'] = 'WEIRD'
        tip = self.ledger.verify()['tip']
        self.assertEqual(self.ctl.poll(), {'R1': 'UNKNOWN_STATUS_WEIRD'})
        self.assertEqual(self.ledger.verify()['tip'], tip)

    def test_push_failure_marks_failed_and_charges_budget(self):
        self.client.fail_push = True
        with self.assertRaises(RuntimeError):
            self.ctl.submit('R1', self.kernel(), ['o'])
        st = self.ledger.verify()
        self.assertEqual(st['runs']['R1']['state'], 'FAILED'); self.assertEqual(st['remaining_runs'], 2)

    def test_concurrency_budget_and_live_kernel_limits(self):
        self.ctl.submit('R1', self.kernel('edgelab-k1'), ['o'])
        with self.assertRaises(ValueError):
            self.ctl.submit('R2', self.kernel('edgelab-k1'), ['o'])     # no se pushea sobre una versión viva
        self.ctl.submit('R3', self.kernel('edgelab-k2'), ['o'])
        with self.assertRaises(ValueError):
            self.ctl.submit('R4', self.kernel('edgelab-k3'), ['o'])     # concurrencia 2
        self.assertEqual(self.client.pushed.__len__(), 2)

    def test_budget_exhausted(self):
        for i in range(3):
            self.client.status_map['nicolasbuttaro/edgelab-k%d' % i] = 'ERROR'
            self.ctl.submit('R%d' % i, self.kernel('edgelab-k%d' % i), ['o']); self.ctl.poll()
        with self.assertRaises(ValueError):
            self.ctl.submit('R9', self.kernel('edgelab-k9'), ['o'])

    def test_metadata_fail_closed(self):
        bad = [dict(is_private=False), dict(enable_internet=True), dict(dataset_sources=['nicolasbuttaro/edgelab-holdout']),
               dict(kernel_sources=['x/y']), dict(id='otro/edgelab-k1'), dict(code_file='../z.py')]
        for i, meta in enumerate(bad):
            with self.subTest(meta=meta), self.assertRaises(ValueError):
                self.ctl.submit('B%d' % i, self.kernel('edgelab-b%d' % i, **meta), ['o'])
        self.assertEqual(self.ledger.verify()['used_runs'], 0)     # lo rechazado no gasta presupuesto
        self.assertEqual(self.client.pushed, [])

    def test_identity_changes_with_code(self):
        d = self.kernel(); pol = KagglePolicy(OWNER, DS)
        a = kernel_dir_identity(d, pol)[1]; (d / 'z.py').write_text('print(2)\n')
        self.assertNotEqual(a, kernel_dir_identity(d, pol)[1])

    def test_tamper_detected(self):
        self.ctl.submit('R1', self.kernel(), ['o'])
        db = sqlite3.connect(self.root / 'kaggle.sqlite')
        db.execute("UPDATE runs SET body=replace(body,'SUBMITTED','COMPLETE_TECHNICAL')"); db.commit(); db.close()
        with self.assertRaises(ValueError):
            self.ledger.verify()

    def test_policy_rebind_rejected_and_expected_tip(self):
        with self.assertRaises(ValueError):
            self.ledger.initialize(KagglePolicy(OWNER, DS, max_runs=99))
        with self.assertRaises(ValueError):
            self.ledger.verify(expected_tip='0' * 64)

    def test_cli_status_includes_kaggle_ledger_read_only(self):
        missing = self.root / 'nope.sqlite'
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            main(['--state', str(self.root / 'q.sqlite'), 'status', '--kaggle-state', str(missing)])
        out = json.loads(buf.getvalue())
        self.assertEqual(out['kaggle']['status'], 'NOT_INITIALIZED_OR_INVALID'); self.assertFalse(missing.exists())


if __name__ == '__main__':
    unittest.main()
