"""Transactional finite queue with operational audit events. Never opens market data."""
from __future__ import annotations
import contextlib, dataclasses, hashlib, json, os, re, sqlite3, time
from pathlib import Path

ZERO = '0' * 64
HEX = re.compile(r'^[0-9a-f]{64}$')
ID = re.compile(r'^[A-Za-z0-9_-]{1,80}$')
TERMINAL = {'SUCCEEDED_TECHNICAL', 'FAILED_TECHNICAL', 'INTERRUPTED'}

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)

def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()

@dataclasses.dataclass(frozen=True)
class Policy:
    max_attempts: int = 3
    max_reserved_seconds: int = 30
    def validate(self):
        if type(self.max_attempts) is not int or not 1 <= self.max_attempts <= 100:
            raise ValueError('invalid attempt budget')
        if type(self.max_reserved_seconds) is not int or not 1 <= self.max_reserved_seconds <= 3600:
            raise ValueError('invalid time budget')

@dataclasses.dataclass(frozen=True)
class Plan:
    job_id: str
    hypothesis: str
    protocol_sha256: str
    timeout_seconds: int = 5
    scope: str = 'synthetic'
    action: str = 'synthetic_selfcheck'
    def validate(self):
        if not isinstance(self.job_id, str) or not ID.fullmatch(self.job_id):
            raise ValueError('invalid job id')
        if not isinstance(self.hypothesis, str) or not 1 <= len(self.hypothesis) <= 1024:
            raise ValueError('invalid hypothesis text')
        if not isinstance(self.protocol_sha256, str) or not HEX.fullmatch(self.protocol_sha256):
            raise ValueError('protocol hash required')
        if type(self.timeout_seconds) is not int or not 1 <= self.timeout_seconds <= 30:
            raise ValueError('invalid timeout')
        if self.scope != 'synthetic' or self.action != 'synthetic_selfcheck':
            raise ValueError('market/holdout/arbitrary actions are disabled')

class Store:
    def __init__(self, path):
        self.path = Path(path)
        if self.path.is_symlink():
            raise ValueError('symlink database rejected')
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)

    @contextlib.contextmanager
    def transaction(self, create=False):
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

    def initialize(self, policy=Policy()):
        policy.validate()
        with self.transaction(create=True) as db:
            db.execute('CREATE TABLE IF NOT EXISTS policy (singleton INTEGER PRIMARY KEY CHECK(singleton=1), definition TEXT NOT NULL, attempts INTEGER NOT NULL, seconds INTEGER NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, definition TEXT NOT NULL, pin TEXT NOT NULL, status TEXT NOT NULL, result_sha TEXT)')
            db.execute('CREATE TABLE IF NOT EXISTS events (seq INTEGER PRIMARY KEY, body TEXT NOT NULL, previous TEXT NOT NULL, hash TEXT NOT NULL)')
            row = db.execute('SELECT definition FROM policy').fetchone()
            definition = canonical(dataclasses.asdict(policy))
            if row:
                if row['definition'] != definition:
                    raise ValueError('policy frozen; use a new reviewed queue')
                self._verify(db)
            else:
                db.execute('INSERT INTO policy VALUES (1,?,0,0)', (definition,))
                self._event(db, 'POLICY', None, dataclasses.asdict(policy))
        os.chmod(self.path, 0o600)

    @staticmethod
    def _event(db, kind, job, payload):
        last = db.execute('SELECT seq, hash FROM events ORDER BY seq DESC LIMIT 1').fetchone()
        seq, previous = (last['seq'] + 1, last['hash']) if last else (1, ZERO)
        body = canonical(dict(seq=seq, kind=kind, job=job, payload=payload, at_ns=time.time_ns()))
        pin = hashlib.sha256((previous + body).encode()).hexdigest()
        db.execute('INSERT INTO events VALUES (?,?,?,?)', (seq, body, previous, pin))
        return pin

    def _verify(self, db, expected_tip=None):
        previous = ZERO
        jobs = {}
        policy = None
        attempts = seconds = 0
        for seq, row in enumerate(db.execute('SELECT * FROM events ORDER BY seq'), 1):
            body = json.loads(row['body'])
            if row['seq'] != seq or body['seq'] != seq or row['previous'] != previous:
                raise ValueError('event ordering/chain mismatch')
            if canonical(body) != row['body']:
                raise ValueError('noncanonical event')
            previous = hashlib.sha256((previous + row['body']).encode()).hexdigest()
            if previous != row['hash']:
                raise ValueError('event checksum mismatch')
            kind, job, payload = body['kind'], body['job'], body['payload']
            if kind == 'POLICY':
                if seq != 1 or policy is not None:
                    raise ValueError('policy event invalid')
                policy = Policy(**payload)
                policy.validate()
            elif kind == 'SUBMITTED':
                plan = Plan(**payload)
                plan.validate()
                if plan.job_id != job or job in jobs:
                    raise ValueError('duplicate or invalid proposal')
                jobs[job] = [canonical(payload), digest(payload), 'QUEUED', None]
            elif kind == 'CLAIMED':
                if job not in jobs or jobs[job][2] != 'QUEUED':
                    raise ValueError('invalid claim transition')
                timeout = json.loads(jobs[job][0])['timeout_seconds']
                if payload != {'reserved_seconds': timeout} or any(j[2] == 'RUNNING' for j in jobs.values()):
                    raise ValueError('invalid reservation/concurrency')
                jobs[job][2] = 'RUNNING'
                attempts += 1
                seconds += timeout
            elif kind in TERMINAL:
                if job not in jobs or jobs[job][2] != 'RUNNING' or set(payload) != {'result_sha256'}:
                    raise ValueError('invalid terminal transition')
                pin = payload['result_sha256']
                if pin is not None and (not isinstance(pin, str) or not HEX.fullmatch(pin)):
                    raise ValueError('invalid receipt digest')
                jobs[job][2:] = [kind, pin]
            else:
                raise ValueError('unknown audit event')
        row = db.execute('SELECT * FROM policy').fetchone()
        if policy is None or not row or row['definition'] != canonical(dataclasses.asdict(policy)):
            raise ValueError('policy projection mismatch')
        if (row['attempts'], row['seconds']) != (attempts, seconds):
            raise ValueError('budget projection mismatch')
        if attempts > policy.max_attempts or seconds > policy.max_reserved_seconds:
            raise ValueError('budget exceeded')
        actual = {r['id']: [r['definition'], r['pin'], r['status'], r['result_sha']] for r in db.execute('SELECT * FROM jobs')}
        if actual != jobs:
            raise ValueError('job projection mismatch')
        for job, record in jobs.items():
            if record[3] is not None:
                receipt = self.path.parent / 'receipts' / (job + '.json')
                if receipt.is_symlink() or not receipt.is_file() or receipt.stat().st_size > 65536:
                    raise ValueError('receipt unavailable or unbounded')
                if hashlib.sha256(receipt.read_bytes()).hexdigest() != record[3]:
                    raise ValueError('receipt checksum mismatch')
        if expected_tip is not None and previous != expected_tip:
            raise ValueError('external tip mismatch; possible rollback')
        return dict(tip=previous, jobs=len(jobs), attempts_reserved=attempts, seconds_reserved=seconds,
                    states={job: j[2] for job, j in jobs.items()}, operational_integrity_only=True)

    def verify(self, expected_tip=None):
        with self.transaction() as db:
            return self._verify(db, expected_tip)

    def submit(self, plan):
        plan.validate()
        data = dataclasses.asdict(plan)
        with self.transaction() as db:
            self._verify(db)
            budget = db.execute('SELECT definition FROM policy').fetchone()
            cap = 4 * json.loads(budget['definition'])['max_attempts']
            if db.execute('SELECT count(*) FROM jobs').fetchone()[0] >= cap:
                raise ValueError('finite proposal capacity exhausted')
            if db.execute('SELECT 1 FROM jobs WHERE id=?', (plan.job_id,)).fetchone():
                raise ValueError('job id already registered; no silent overwrite')
            db.execute('INSERT INTO jobs VALUES (?,?,?,?,NULL)', (plan.job_id, canonical(data), digest(data), 'QUEUED'))
            self._event(db, 'SUBMITTED', plan.job_id, data)

    def claim(self):
        with self.transaction() as db:
            self._verify(db)
            if db.execute("SELECT 1 FROM jobs WHERE status='RUNNING'").fetchone():
                return None
            row = db.execute("SELECT * FROM jobs WHERE status='QUEUED' ORDER BY rowid LIMIT 1").fetchone()
            if not row:
                return None
            plan = Plan(**json.loads(row['definition']))
            budget = db.execute('SELECT * FROM policy').fetchone()
            policy = Policy(**json.loads(budget['definition']))
            if budget['attempts'] + 1 > policy.max_attempts or budget['seconds'] + plan.timeout_seconds > policy.max_reserved_seconds:
                raise ValueError('budget exhausted; review required')
            db.execute('UPDATE policy SET attempts=attempts+1, seconds=seconds+? WHERE singleton=1', (plan.timeout_seconds,))
            db.execute("UPDATE jobs SET status='RUNNING' WHERE id=?", (plan.job_id,))
            self._event(db, 'CLAIMED', plan.job_id, {'reserved_seconds': plan.timeout_seconds})
            return plan

    def finish(self, job_id, status, result_sha=None):
        if status not in TERMINAL or (result_sha is not None and (not isinstance(result_sha,str) or not HEX.fullmatch(result_sha))) or (status == 'SUCCEEDED_TECHNICAL' and result_sha is None):
            raise ValueError('invalid finish')
        with self.transaction() as db:
            self._verify(db)
            row = db.execute('SELECT status FROM jobs WHERE id=?', (job_id,)).fetchone()
            if not row or row['status'] != 'RUNNING':
                raise ValueError('only running jobs can finish')
            db.execute('UPDATE jobs SET status=?, result_sha=? WHERE id=?', (status, result_sha, job_id))
            self._event(db, status, job_id, {'result_sha256': result_sha})
            self._verify(db)
