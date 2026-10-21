"""Durable checkpoint ledger tests. No execution, no output content, synthetic only."""
import json, sqlite3, tempfile, unittest
from pathlib import Path
from tools.research_ops.work_plan import CampaignIdentity, build_work_plan
from tools.research_ops.checkpoints import CheckpointLedger
from tools.research_ops.cli import main


class CheckpointTests(unittest.TestCase):
    def identity(self): return CampaignIdentity('MNQ_12-25', *['a' * 64, 'b' * 64, 'c' * 64, 'd' * 64, 'e' * 64, 'f' * 64])
    def plan(self): return build_work_plan(self.identity(), max_attempts=18, seconds_per_attempt=600, memory_bytes_per_worker=4 * 1024 ** 3)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name)
        self.ledger = CheckpointLedger(self.root / 'checkpoints.sqlite')
        self.plan_doc = self.plan()
        self.ledger.initialize(self.plan_doc)

    def tearDown(self):
        self.tmp.cleanup()

    def receipt(self, index=0, output='0' * 64):
        unit = self.plan_doc['units'][index]
        return dict(unit_id=unit['unit_id'], fingerprint=unit['fingerprint'], output_sha256=output)

    def test_initialization_idempotent(self):
        tip = self.ledger.verify()['tip']
        self.ledger.initialize(self.plan_doc)
        self.assertEqual(self.ledger.verify()['tip'], tip)

    def test_plan_frozen(self):
        other = build_work_plan(self.identity(), max_attempts=20, seconds_per_attempt=600, memory_bytes_per_worker=4 * 1024 ** 3)
        with self.assertRaises(ValueError): self.ledger.initialize(other)

    def test_explicit_initialization_required(self):
        with self.assertRaises(ValueError): CheckpointLedger(self.root / 'absent.sqlite').verify()

    def test_record_requires_bound_plan(self):
        bare = CheckpointLedger(self.root / 'bare.sqlite')
        with self.assertRaises(ValueError): bare.record(self.receipt())

    def test_record_and_pending_shrinks(self):
        self.assertEqual(len(self.ledger.pending_units()), 18)
        status = self.ledger.record(self.receipt(0))
        self.assertFalse(status['skip_allowed']); self.assertFalse(status['execution_allowed'])
        self.assertEqual(len(self.ledger.pending_units()), 17)
        self.assertNotIn(self.plan_doc['units'][0]['unit_id'], self.ledger.pending_units())

    def test_no_duplicate_checkpoint(self):
        self.ledger.record(self.receipt(0))
        with self.assertRaises(ValueError): self.ledger.record(self.receipt(0, output='1' * 64))

    def test_wrong_fingerprint_rejected(self):
        bad = self.receipt(0); bad['fingerprint'] = '9' * 64
        with self.assertRaises(ValueError): self.ledger.record(bad)

    def test_unknown_unit_rejected(self):
        bad = self.receipt(0); bad['unit_id'] = 'MNQ_12-25-UNKNOWN'
        with self.assertRaises(ValueError): self.ledger.record(bad)

    def test_restart_does_not_lose_or_regrant_checkpoints(self):
        self.ledger.record(self.receipt(0))
        reopened = CheckpointLedger(self.root / 'checkpoints.sqlite')
        self.assertEqual(len(reopened.pending_units()), 17)
        with self.assertRaises(ValueError): reopened.record(self.receipt(0))

    def test_all_units_can_be_recorded(self):
        for i in range(18):
            self.ledger.record(self.receipt(i, output=f'{i:064x}'[-64:]))
        self.assertEqual(self.ledger.pending_units(), [])

    def test_tampered_event_chain_detected(self):
        self.ledger.record(self.receipt(0))
        db = sqlite3.connect(self.ledger.path)
        try:
            db.execute("UPDATE events SET body=replace(body,'CHECKPOINT_RECORDED','TAMPERED') WHERE seq=2")
            db.commit()
        finally:
            db.close()
        with self.assertRaises(ValueError): self.ledger.verify()

    def test_tampered_checkpoint_row_detected(self):
        self.ledger.record(self.receipt(0))
        db = sqlite3.connect(self.ledger.path)
        try:
            db.execute("UPDATE checkpoints SET output_sha256='9'*64")
            db.commit()
        finally:
            db.close()
        with self.assertRaises(ValueError): self.ledger.verify()

    def test_symlink_db_rejected(self):
        import os
        if os.name != 'posix':
            self.skipTest('symlinks require elevated privileges on Windows')
        link = self.root / 'link.sqlite'
        link.symlink_to(self.root / 'checkpoints.sqlite')
        with self.assertRaises(ValueError): CheckpointLedger(link)


class CheckpointCliTests(unittest.TestCase):
    def identity(self): return CampaignIdentity('MNQ_12-25', *['a' * 64, 'b' * 64, 'c' * 64, 'd' * 64, 'e' * 64, 'f' * 64])

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name)
        self.state = self.root / 'checkpoints.sqlite'
        self.plan_doc = build_work_plan(self.identity(), max_attempts=18, seconds_per_attempt=600, memory_bytes_per_worker=4 * 1024 ** 3)
        self.plan_path = self.root / 'plan.json'; self.plan_path.write_text(json.dumps(self.plan_doc))

    def tearDown(self):
        self.tmp.cleanup()

    def test_cli_full_cycle(self):
        main(['checkpoint-init', '--checkpoint-state', str(self.state), str(self.plan_path)])
        unit = self.plan_doc['units'][0]
        receipt_path = self.root / 'receipt.json'
        receipt_path.write_text(json.dumps(dict(unit_id=unit['unit_id'], fingerprint=unit['fingerprint'], output_sha256='0' * 64)))
        main(['checkpoint-record', '--checkpoint-state', str(self.state), str(receipt_path)])
        ledger = CheckpointLedger(self.state)
        self.assertEqual(len(ledger.pending_units()), 17)

    def test_cli_pending_without_init_fails_closed(self):
        with self.assertRaises(ValueError):
            main(['checkpoint-pending', '--checkpoint-state', str(self.state)])

    def test_cli_rejects_oversize_plan_file(self):
        self.plan_path.write_bytes(b' ' * 65537)
        with self.assertRaises(ValueError):
            main(['checkpoint-init', '--checkpoint-state', str(self.state), str(self.plan_path)])
