"""Durable read-only research budget ledger. Binds one reviewed plan + one frozen reviewer
identity to persisted, restart-safe consumption of its bounded directives.

This module NEVER performs a network call. Reserving a directive only durably marks budget
as spent, so a crash/restart cannot re-grant it (closes the "not durably enforced" gap left
by research_cycle.plan_research). Recording a receipt requires externally supplied,
hash-pinned evidence from an already-executed, separately authorized fetch; it does not
fetch anything itself. Provider wiring, tool allowlists and paid spend remain future,
separately authorized work: research_cycle.ResearchBudget still pins max_api_spend=0.
"""
from __future__ import annotations
import contextlib, dataclasses, hashlib, json, os, re, sqlite3
from pathlib import Path
from .store import canonical, digest, ZERO, HEX

REVIEWER = re.compile(r'^[A-Za-z0-9_.-]{1,80}$')


@dataclasses.dataclass(frozen=True)
class Reviewer:
    reviewer_id: str
    scope: str = 'public_web_readonly'

    def validate(self):
        if not isinstance(self.reviewer_id, str) or not REVIEWER.fullmatch(self.reviewer_id):
            raise ValueError('invalid reviewer id')
        if self.scope != 'public_web_readonly':
            raise ValueError('only read-only public scope supported')


class DispatchLedger:
    """One ledger per episode. ``plan`` must come from research_cycle.plan_research with
    status READY_READONLY_RESEARCH_DIRECTIVES_NOT_EXECUTED; its directive list and
    plan_sha256 are pinned on first use and frozen afterward, like Store.Policy."""

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

    def initialize(self, reviewer):
        reviewer.validate()
        with self._tx(create=True) as db:
            db.execute('CREATE TABLE IF NOT EXISTS reviewer (singleton INTEGER PRIMARY KEY CHECK(singleton=1), definition TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS plan (singleton INTEGER PRIMARY KEY CHECK(singleton=1), plan_sha256 TEXT NOT NULL, max_queries INTEGER NOT NULL, directives TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS events (seq INTEGER PRIMARY KEY, body TEXT NOT NULL, previous TEXT NOT NULL, hash TEXT NOT NULL)')
            row = db.execute('SELECT definition FROM reviewer').fetchone()
            definition = canonical(dataclasses.asdict(reviewer))
            if row:
                if row['definition'] != definition:
                    raise ValueError('reviewer identity frozen; use a new reviewed ledger per reviewer')
                self._verify(db)
            else:
                db.execute('INSERT INTO reviewer VALUES (1,?)', (definition,))
                self._event(db, 'REVIEWER_BOUND', None, dataclasses.asdict(reviewer))
        os.chmod(self.path, 0o600)

    @staticmethod
    def _event(db, kind, directive_idx, payload):
        last = db.execute('SELECT seq, hash FROM events ORDER BY seq DESC LIMIT 1').fetchone()
        seq, previous = (last['seq'] + 1, last['hash']) if last else (1, ZERO)
        body = canonical(dict(seq=seq, kind=kind, directive=directive_idx, payload=payload))
        pin = hashlib.sha256((previous + body).encode()).hexdigest()
        db.execute('INSERT INTO events VALUES (?,?,?,?)', (seq, body, previous, pin))
        return pin

    def _verify(self, db):
        previous = ZERO
        reviewer_payload = None
        plan_bound = None
        reserved = set()
        receipts = {}
        for seq, row in enumerate(db.execute('SELECT * FROM events ORDER BY seq'), 1):
            body = json.loads(row['body'])
            if row['seq'] != seq or body['seq'] != seq or row['previous'] != previous or canonical(body) != row['body']:
                raise ValueError('event ordering/chain mismatch')
            previous = hashlib.sha256((previous + row['body']).encode()).hexdigest()
            if previous != row['hash']:
                raise ValueError('event checksum mismatch')
            kind, idx, payload = body['kind'], body['directive'], body['payload']
            if kind == 'REVIEWER_BOUND':
                if seq != 1 or reviewer_payload is not None:
                    raise ValueError('reviewer event must be first and unique')
                Reviewer(**payload).validate()
                reviewer_payload = payload
            elif kind == 'PLAN_BOUND':
                if plan_bound is not None:
                    raise ValueError('plan event must be unique')
                plan_bound = payload
            elif kind == 'RESERVED':
                if plan_bound is None or idx in reserved:
                    raise ValueError('directive reserved without a bound plan or already reserved')
                if not isinstance(idx, int) or not 0 <= idx < plan_bound['max_queries']:
                    raise ValueError('directive index outside plan budget')
                reserved.add(idx)
            elif kind == 'RECEIPT_RECORDED':
                if idx not in reserved or idx in receipts:
                    raise ValueError('receipt without matching unique reservation')
                receipts[idx] = payload['evidence_sha256']
            else:
                raise ValueError('unknown dispatch event')
        row = db.execute('SELECT * FROM reviewer').fetchone()
        if reviewer_payload is None or not row or row['definition'] != canonical(reviewer_payload):
            raise ValueError('reviewer projection mismatch')
        prow = db.execute('SELECT * FROM plan').fetchone()
        if (plan_bound is None) != (prow is None):
            raise ValueError('plan projection mismatch')
        if plan_bound is not None and (prow['plan_sha256'], prow['max_queries']) != (plan_bound['plan_sha256'], plan_bound['max_queries']):
            raise ValueError('plan projection mismatch')
        return dict(tip=previous, plan_sha256=plan_bound['plan_sha256'] if plan_bound else None,
                    reserved=sorted(reserved), receipts=dict(receipts), network_executed=False,
                    durable_budget_enforced=True)

    def verify(self):
        with self._tx() as db:
            return self._verify(db)

    def bind_plan(self, plan):
        """Pin a READY plan's directive budget once per ledger; cannot be rebound or widened."""
        if plan.get('status') != 'READY_READONLY_RESEARCH_DIRECTIVES_NOT_EXECUTED' or plan.get('blockers'):
            raise ValueError('only an unblocked, reviewed READY plan may be bound')
        directives = plan.get('read_only_directives') or []
        max_queries = plan['budget']['max_queries']
        if not directives or len(directives) > max_queries:
            raise ValueError('plan directives inconsistent with its own budget')
        unsigned = {k: v for k, v in plan.items() if k != 'plan_sha256'}
        if digest(unsigned) != plan.get('plan_sha256'):
            raise ValueError('plan integrity mismatch')
        with self._tx() as db:
            self._verify(db)
            if db.execute('SELECT 1 FROM plan').fetchone():
                raise ValueError('ledger already bound to a plan; use a new episode ledger')
            db.execute('INSERT INTO plan VALUES (1,?,?,?)', (plan['plan_sha256'], max_queries, canonical(directives)))
            self._event(db, 'PLAN_BOUND', None, dict(plan_sha256=plan['plan_sha256'], max_queries=max_queries))

    def reserve(self, directive_index, *, reviewer_id):
        """Durably consume one directive's budget. No network call happens here or ever
        in this module; this only prevents a crash/restart from re-granting spent budget."""
        with self._tx() as db:
            state = self._verify(db)
            row = db.execute('SELECT definition FROM reviewer').fetchone()
            if reviewer_id != json.loads(row['definition'])['reviewer_id']:
                raise ValueError('reservation must come from the bound reviewer')
            if state['plan_sha256'] is None:
                raise ValueError('no plan bound to this ledger yet')
            if directive_index in state['reserved']:
                raise ValueError('directive already reserved; budget cannot be re-granted')
            self._event(db, 'RESERVED', directive_index, {})
            return self._verify(db)

    def record_receipt(self, directive_index, *, evidence_sha256, source_url_sha256, char_count, cost):
        """Attach externally pinned, already-reviewed evidence to a reserved directive.
        Still no fetch happens here: caller must supply hashes of content it already has."""
        if not HEX.fullmatch(evidence_sha256) or not HEX.fullmatch(source_url_sha256):
            raise ValueError('evidence/source must be pinned by external SHA256')
        if type(char_count) is not int or not 0 <= char_count <= 24000:
            raise ValueError('bounded char count required')
        if cost != 0:
            raise ValueError('paid research spend not enabled; see ResearchBudget.max_api_spend')
        with self._tx() as db:
            state = self._verify(db)
            if directive_index not in state['reserved']:
                raise ValueError('cannot record a receipt without a prior reservation')
            if directive_index in state['receipts']:
                raise ValueError('receipt already recorded for this directive')
            payload = dict(evidence_sha256=evidence_sha256, source_url_sha256=source_url_sha256,
                            char_count=char_count, cost=cost)
            self._event(db, 'RECEIPT_RECORDED', directive_index, payload)
            return self._verify(db)
