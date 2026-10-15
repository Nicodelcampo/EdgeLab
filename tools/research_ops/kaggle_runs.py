"""Durable control of Kaggle kernel runs: reserve -> push -> poll -> collect, fail-closed.

Hito 4 of CLAUDE_HANDOFF.md ("control operacional remoto sobre Kaggle"): job identity,
versions, bounded poll, output download and verification, concurrency and run budget,
all in a hash-chained ledger that survives restarts. Same recipe as CheckpointLedger.

What this module does NOT do: decide what to run, generate code, open market data,
read outputs' content, retry anything, or certify a result. A COLLECTED_VERIFIED run means
"the files named in the reservation exist, are non-empty and their sha256 is recorded" —
a technical fact, never a scientific one. Every network call lives in KaggleCli, behind a
fixed argv (no shell), so tests run without network through a fake client.
"""
from __future__ import annotations
import contextlib, dataclasses, hashlib, json, os, re, sqlite3, subprocess, sys
from pathlib import Path
from .store import canonical, ZERO, ID

REF = re.compile(r'^[a-z0-9][a-z0-9-]{0,48}/[a-z0-9][a-z0-9-]{0,48}$')
NAME = re.compile(r'^[A-Za-z0-9._-]{1,120}$')
STATES = ('RESERVED', 'SUBMITTED', 'RUNNING', 'COMPLETE_TECHNICAL', 'FAILED', 'COLLECTED_VERIFIED', 'COLLECTION_INCOMPLETE')
ACTIVE = {'RESERVED', 'SUBMITTED', 'RUNNING'}
# Kaggle KernelWorkerStatus -> ledger state. Anything not listed fails closed.
KAGGLE_STATUS = {'QUEUED': 'RUNNING', 'RUNNING': 'RUNNING', 'COMPLETE': 'COMPLETE_TECHNICAL',
                 'ERROR': 'FAILED', 'CANCEL_REQUESTED': 'FAILED', 'CANCEL_ACKNOWLEDGED': 'FAILED'}
NEXT = {'RESERVED': {'SUBMITTED', 'FAILED'}, 'SUBMITTED': {'RUNNING', 'COMPLETE_TECHNICAL', 'FAILED'},
        'RUNNING': {'RUNNING', 'COMPLETE_TECHNICAL', 'FAILED'},
        'COMPLETE_TECHNICAL': {'COLLECTED_VERIFIED', 'COLLECTION_INCOMPLETE'}}
MAX_CONCURRENT = 5          # límite operacional de Kaggle (sesiones CPU simultáneas)


@dataclasses.dataclass(frozen=True)
class KagglePolicy:
    owner: str                          # cuenta dueña de los kernels, p. ej. 'nicolasbuttaro'
    allowed_datasets: tuple             # refs owner/slug que un kernel puede montar; holdout queda afuera
    max_runs: int = 20                  # presupuesto durable: no se reinicia ni se devuelve
    max_concurrent: int = 3

    def validate(self):
        if not isinstance(self.owner, str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,48}', self.owner):
            raise ValueError('invalid owner')
        if not self.allowed_datasets or not all(isinstance(d, str) and REF.fullmatch(d) for d in self.allowed_datasets):
            raise ValueError('explicit dataset allowlist required')
        if type(self.max_runs) is not int or not 1 <= self.max_runs <= 500:
            raise ValueError('invalid run budget')
        if type(self.max_concurrent) is not int or not 1 <= self.max_concurrent <= MAX_CONCURRENT:
            raise ValueError('invalid concurrency limit')


def kernel_dir_identity(kernel_dir, policy):
    """sha256 of kernel-metadata.json + its code file, after fail-closed checks on the metadata.
    The pushed payload is exactly what was reserved, or nothing is pushed."""
    kdir = Path(kernel_dir)
    meta_path = kdir / 'kernel-metadata.json'
    if kdir.is_symlink() or meta_path.is_symlink() or not meta_path.is_file() or meta_path.stat().st_size > 65536:
        raise ValueError('bounded regular kernel-metadata.json required')
    meta = json.loads(meta_path.read_bytes())
    ref = meta.get('id', '')
    if not REF.fullmatch(ref) or ref.split('/')[0] != policy.owner:
        raise ValueError('kernel id must belong to the policy owner')
    if meta.get('is_private') is not True or meta.get('enable_internet') is not False:
        raise ValueError('kernel must be private and without internet')
    if meta.get('competition_sources') or meta.get('kernel_sources'):
        raise ValueError('only allowlisted datasets may be mounted')
    extra = set(meta.get('dataset_sources') or ()) - set(policy.allowed_datasets)
    if extra:
        raise ValueError('dataset not allowlisted: %s' % sorted(extra))
    code = kdir / str(meta.get('code_file', ''))
    if not NAME.fullmatch(code.name) or code.parent != kdir or code.is_symlink() or not code.is_file():
        raise ValueError('code file must be a regular file inside the kernel directory')
    h = hashlib.sha256()
    for part in (meta_path.read_bytes(), code.read_bytes()):
        h.update(hashlib.sha256(part).digest())
    return ref, h.hexdigest()


class KaggleRunLedger:
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

    def initialize(self, policy):
        policy.validate()
        pol = dict(dataclasses.asdict(policy), allowed_datasets=sorted(policy.allowed_datasets))
        with self._tx(create=True) as db:
            db.execute('CREATE TABLE IF NOT EXISTS policy (singleton INTEGER PRIMARY KEY CHECK(singleton=1), body TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS runs (run_id TEXT PRIMARY KEY, body TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS events (seq INTEGER PRIMARY KEY, body TEXT NOT NULL, previous TEXT NOT NULL, hash TEXT NOT NULL)')
            row = db.execute('SELECT body FROM policy').fetchone()
            if row:
                if json.loads(row['body']) != pol:
                    raise ValueError('ledger already bound to a different policy')
                self._verify(db)
            else:
                db.execute('INSERT INTO policy VALUES (1,?)', (canonical(pol),))
                self._event(db, 'POLICY_BOUND', None, pol)
        os.chmod(self.path, 0o600)

    @staticmethod
    def _event(db, kind, run_id, payload):
        last = db.execute('SELECT seq, hash FROM events ORDER BY seq DESC LIMIT 1').fetchone()
        seq, previous = (last['seq'] + 1, last['hash']) if last else (1, ZERO)
        body = canonical(dict(seq=seq, kind=kind, run=run_id, payload=payload))
        pin = hashlib.sha256((previous + body).encode()).hexdigest()
        db.execute('INSERT INTO events VALUES (?,?,?,?)', (seq, body, previous, pin))
        return pin

    def _verify(self, db):
        """Replay the chain into the runs projection; any mismatch fails closed."""
        previous, policy, runs = ZERO, None, {}
        for seq, row in enumerate(db.execute('SELECT * FROM events ORDER BY seq'), 1):
            body = json.loads(row['body'])
            if row['seq'] != seq or body['seq'] != seq or row['previous'] != previous or canonical(body) != row['body']:
                raise ValueError('event ordering/chain mismatch')
            previous = hashlib.sha256((previous + row['body']).encode()).hexdigest()
            if previous != row['hash']:
                raise ValueError('event checksum mismatch')
            kind, rid, p = body['kind'], body['run'], body['payload']
            if kind == 'POLICY_BOUND':
                if seq != 1:
                    raise ValueError('policy event must be first and unique')
                policy = p
            elif kind == 'RESERVED':
                if policy is None or rid in runs:
                    raise ValueError('reservation without policy or duplicated')
                runs[rid] = dict(p, state='RESERVED', version=None, outputs=None, history=['RESERVED'])
            elif kind == 'STATE':
                r = runs.get(rid)
                if r is None or p['state'] not in NEXT.get(r['state'], ()):
                    raise ValueError('illegal state transition')
                r.update({k: v for k, v in p.items() if k != 'state'})
                r['state'] = p['state']
                r['history'].append(p['state'])
            else:
                raise ValueError('unknown kaggle event')
        prow = db.execute('SELECT body FROM policy').fetchone()
        if (prow is None) != (policy is None) or (prow and json.loads(prow['body']) != policy):
            raise ValueError('policy projection mismatch')
        actual = {r['run_id']: json.loads(r['body']) for r in db.execute('SELECT * FROM runs')}
        if actual != runs:
            raise ValueError('run projection mismatch')
        active = sorted(k for k, v in runs.items() if v['state'] in ACTIVE)
        return dict(tip=previous, policy=policy, runs=runs, active=active, used_runs=len(runs),
                    remaining_runs=(policy['max_runs'] - len(runs)) if policy else 0,
                    results_certified=False, retries_allowed=False)

    def verify(self, expected_tip=None):
        with self._tx() as db:
            state = self._verify(db)
        if expected_tip is not None and state['tip'] != expected_tip:
            raise ValueError('ledger tip differs from the externally kept tip')
        return state

    def _put(self, db, rid, run):
        db.execute('INSERT OR REPLACE INTO runs VALUES (?,?)', (rid, canonical(run)))

    def reserve(self, run_id, kernel_ref, payload_sha256, expected_outputs):
        """Charge the budget BEFORE anything leaves the machine. Never refunded."""
        if not isinstance(run_id, str) or not ID.fullmatch(run_id):
            raise ValueError('invalid run id')
        names = list(expected_outputs)
        if not names or len(names) > 50 or not all(isinstance(n, str) and NAME.fullmatch(n) for n in names) or len(set(names)) != len(names):
            raise ValueError('explicit, bounded list of expected output names required')
        with self._tx() as db:
            st = self._verify(db)
            if run_id in st['runs']:
                raise ValueError('run id already used; a replacement needs a new id')
            if st['remaining_runs'] <= 0:
                raise ValueError('run budget exhausted')
            if len(st['active']) >= st['policy']['max_concurrent']:
                raise ValueError('concurrency limit reached')
            if any(v['kernel_ref'] == kernel_ref and v['state'] in ACTIVE for v in st['runs'].values()):
                raise ValueError('kernel already has an active run; never push over a live version')
            p = dict(kernel_ref=kernel_ref, payload_sha256=payload_sha256, expected_outputs=sorted(names))
            self._event(db, 'RESERVED', run_id, p)
            self._put(db, run_id, dict(p, state='RESERVED', version=None, outputs=None, history=['RESERVED']))
            return self._verify(db)['runs'][run_id]

    def transition(self, run_id, state, **extra):
        with self._tx() as db:
            st = self._verify(db)
            run = st['runs'].get(run_id)
            if run is None:
                raise ValueError('unknown run')
            if state not in NEXT.get(run['state'], ()):
                raise ValueError('illegal state transition %s -> %s' % (run['state'], state))
            if state == 'RUNNING' and run['state'] == 'RUNNING':
                return run                              # poll sin cambio: no se registra evento
            p = dict(extra, state=state)
            self._event(db, 'STATE', run_id, p)
            run = dict(run, state=state, history=run['history'] + [state], **extra)
            self._put(db, run_id, run)
            self._verify(db)
            return run


class KaggleCli:
    """The only place with network. Fixed argv, no shell, bounded output."""
    def __init__(self, python=sys.executable, timeout=600):
        self.base = [python, '-m', 'kaggle']
        self.timeout = timeout

    def _run(self, *args):
        p = subprocess.run(self.base + list(args), capture_output=True, text=True, timeout=self.timeout, shell=False)
        out = (p.stdout + p.stderr)[-4000:]
        if p.returncode != 0:
            raise RuntimeError('kaggle cli failed: %s' % out.strip()[-500:])
        return out

    def push(self, kernel_dir):
        m = re.search(r'Kernel version (\d+) successfully pushed', self._run('kernels', 'push', '-p', str(kernel_dir)))
        if not m:
            raise RuntimeError('push not confirmed by kaggle')
        return int(m.group(1))

    def status(self, kernel_ref):
        m = re.search(r'KernelWorkerStatus\.([A-Z_]+)', self._run('kernels', 'status', kernel_ref))
        return m.group(1) if m else 'UNKNOWN'

    def output(self, kernel_ref, dest):
        self._run('kernels', 'output', kernel_ref, '-p', str(dest))


class KaggleRunController:
    def __init__(self, ledger, client):
        self.ledger, self.client = ledger, client

    def submit(self, run_id, kernel_dir, expected_outputs):
        st = self.ledger.verify()
        policy = KagglePolicy(st['policy']['owner'], tuple(st['policy']['allowed_datasets']),
                              st['policy']['max_runs'], st['policy']['max_concurrent'])
        ref, sha = kernel_dir_identity(kernel_dir, policy)
        self.ledger.reserve(run_id, ref, sha, expected_outputs)
        try:
            again = kernel_dir_identity(kernel_dir, policy)[1]
            if again != sha:
                raise ValueError('kernel directory changed between reservation and push')
            version = self.client.push(kernel_dir)
        except Exception as exc:
            self.ledger.transition(run_id, 'FAILED', reason=type(exc).__name__)   # presupuesto no se devuelve
            raise
        return self.ledger.transition(run_id, 'SUBMITTED', version=version)

    def poll(self):
        """One bounded pass over active runs. Unknown statuses do not move the ledger."""
        out = {}
        for rid in self.ledger.verify()['active']:
            run = self.ledger.verify()['runs'][rid]
            if run['state'] == 'RESERVED':
                out[rid] = 'RESERVED_NOT_PUSHED'            # caída entre reserva y push: revisión humana
                continue
            raw = self.client.status(run['kernel_ref'])
            state = KAGGLE_STATUS.get(raw)
            out[rid] = self.ledger.transition(rid, state)['state'] if state else 'UNKNOWN_STATUS_%s' % raw
        return out

    def collect(self, run_id, dest_root):
        run = self.ledger.verify()['runs'].get(run_id)
        if run is None or run['state'] != 'COMPLETE_TECHNICAL':
            raise ValueError('only COMPLETE_TECHNICAL runs can be collected')
        dest = Path(dest_root) / run_id
        if dest.exists():
            raise ValueError('destination exists; outputs are never overwritten')
        dest.mkdir(parents=True)
        self.client.output(run['kernel_ref'], dest)
        files = {}
        for name in run['expected_outputs']:
            hits = [p for p in dest.rglob(name) if p.is_file() and not p.is_symlink()]
            if len(hits) == 1 and hits[0].stat().st_size > 0:
                files[name] = dict(sha256=hashlib.sha256(hits[0].read_bytes()).hexdigest(), size=hits[0].stat().st_size)
        state = 'COLLECTED_VERIFIED' if len(files) == len(run['expected_outputs']) else 'COLLECTION_INCOMPLETE'
        return self.ledger.transition(run_id, state, outputs=files)
