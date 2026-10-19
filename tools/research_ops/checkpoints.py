"""Durable, tamper-evident checkpoint ledger for frozen longevity work-plan units.

Closes the "external durable receipt store" gap work_plan.py already lists under
`required_before_execution`. A Kaggle kernel restart (or any of up to five concurrent
notebooks) can query this ledger to find out which of a frozen plan's units already have
an identity-verified checkpoint, so it spends its wall-clock budget only on units that are
actually still pending — this is how more runs/samples get produced per unit time without
silently re-running completed work or silently skipping anything unrecorded.

This module records identity, never completion, output content or permission to skip:
`skip_allowed` stays False in every status this module returns, exactly like
work_plan.validate_checkpoint_identity does. Recording a checkpoint here does not run
anything and does not read any market data; the actual unit execution and its output stay
entirely external and separately authorized.
"""
from __future__ import annotations
import contextlib, hashlib, json, os, sqlite3
from pathlib import Path
from .store import canonical, ZERO
from .work_plan import validate_checkpoint_identity, validate_work_plan


class CheckpointLedger:
    """One ledger per frozen work plan (bound to its plan_sha256 on init)."""

    def __init__(self, path):
        self.path = Path(path)
        if self.path.is_symlink():
            raise ValueError('symlink database rejected')
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)

    @contextlib.contextmanager
    def _tx(self, create=False):
        if not create and not self.path.is_file():
            raise ValueError('explicit initialization required')
        db = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        db.row_factory = sqlite3.Row
        try:
            db.execute('PRAGMA synchronous=FULL')
            db.execute('BEGIN IMMEDIATE')
            yield db
            db.execute('COMMIT')
        except BaseException:
            if db.in_transaction:
                db.execute('ROLLBACK')
            raise
        finally:
            db.close()

    def initialize(self, plan):
        validate_work_plan(plan)
        with self._tx(create=True) as db:
            db.execute('CREATE TABLE IF NOT EXISTS plan (singleton INTEGER PRIMARY KEY CHECK(singleton=1), plan_sha256 TEXT NOT NULL, definition TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS checkpoints (unit_id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, output_sha256 TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS events (seq INTEGER PRIMARY KEY, body TEXT NOT NULL, previous TEXT NOT NULL, hash TEXT NOT NULL)')
            row = db.execute('SELECT plan_sha256 FROM plan').fetchone()
            if row:
                if row['plan_sha256'] != plan['plan_sha256']:
                    raise ValueError('ledger already bound to a different frozen plan')
                self._verify(db)
            else:
                db.execute('INSERT INTO plan VALUES (1,?,?)', (plan['plan_sha256'], canonical(plan)))
                self._event(db, 'PLAN_BOUND', None, dict(plan_sha256=plan['plan_sha256']))
        os.chmod(self.path, 0o600)

    @staticmethod
    def _event(db, kind, unit_id, payload):
        last = db.execute('SELECT seq, hash FROM events ORDER BY seq DESC LIMIT 1').fetchone()
        seq, previous = (last['seq'] + 1, last['hash']) if last else (1, ZERO)
        body = canonical(dict(seq=seq, kind=kind, unit=unit_id, payload=payload))
        pin = hashlib.sha256((previous + body).encode()).hexdigest()
        db.execute('INSERT INTO events VALUES (?,?,?,?)', (seq, body, previous, pin))
        return pin

    def _verify(self, db):
        previous = ZERO
        plan_sha = None
        plan_def = None
        checkpoints = {}
        for seq, row in enumerate(db.execute('SELECT * FROM events ORDER BY seq'), 1):
            body = json.loads(row['body'])
            if row['seq'] != seq or body['seq'] != seq or row['previous'] != previous or canonical(body) != row['body']:
                raise ValueError('event ordering/chain mismatch')
            previous = hashlib.sha256((previous + row['body']).encode()).hexdigest()
            if previous != row['hash']:
                raise ValueError('event checksum mismatch')
            kind, unit_id, payload = body['kind'], body['unit'], body['payload']
            if kind == 'PLAN_BOUND':
                if seq != 1 or plan_sha is not None:
                    raise ValueError('plan event must be first and unique')
                plan_sha = payload['plan_sha256']
            elif kind == 'CHECKPOINT_RECORDED':
                if plan_sha is None or unit_id in checkpoints:
                    raise ValueError('checkpoint recorded without a bound plan or already recorded')
                checkpoints[unit_id] = payload
            else:
                raise ValueError('unknown checkpoint event')
        row = db.execute('SELECT * FROM plan').fetchone()
        if (plan_sha is None) != (row is None):
            raise ValueError('plan projection mismatch')
        if row is not None:
            if row['plan_sha256'] != plan_sha:
                raise ValueError('plan projection mismatch')
            plan_def = json.loads(row['definition'])
        actual = {r['unit_id']: dict(fingerprint=r['fingerprint'], output_sha256=r['output_sha256'])
                  for r in db.execute('SELECT * FROM checkpoints')}
        if actual != checkpoints:
            raise ValueError('checkpoint projection mismatch')
        return dict(tip=previous, plan_sha256=plan_sha, plan=plan_def, recorded=dict(checkpoints),
                    execution_allowed=False, skip_allowed=False, output_content_verified=False)

    def verify(self):
        with self._tx() as db:
            return self._verify(db)

    def record(self, receipt):
        """Durably record one unit's identity-verified checkpoint. Never overwrites an
        existing one, and never implies that the unit may now be skipped by a caller."""
        with self._tx() as db:
            state = self._verify(db)
            if state['plan'] is None:
                raise ValueError('no plan bound to this ledger yet')
            status = validate_checkpoint_identity(state['plan'], receipt)
            unit_id = receipt['unit_id']
            if unit_id in state['recorded']:
                raise ValueError('checkpoint already recorded for this unit; receipts are not replaced')
            db.execute('INSERT INTO checkpoints VALUES (?,?,?)',
                       (unit_id, receipt['fingerprint'], receipt['output_sha256']))
            self._event(db, 'CHECKPOINT_RECORDED', unit_id,
                        dict(fingerprint=receipt['fingerprint'], output_sha256=receipt['output_sha256']))
            return dict(status, ledger_tip=self._verify(db)['tip'])

    def pending_units(self):
        """Unit ids from the bound plan with no durably recorded checkpoint yet. This is
        what an external, separately authorized supervisor queries before spending any
        more wall-clock budget, so repeated kernel restarts converge instead of looping."""
        state = self.verify()
        if state['plan'] is None:
            raise ValueError('no plan bound to this ledger yet')
        return [u['unit_id'] for u in state['plan']['units'] if u['unit_id'] not in state['recorded']]
