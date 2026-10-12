"""Bounded operational delivery outbox, not a second scientific memory.
Persists reviewed-next drafts only; no writer, dispatch, acceptance, promotion or
code execution. Requires a trusted private directory. Local hashes detect
corruption, not hostile administrators or rollback without an external anchor.
"""
import contextlib
import hashlib
import json
import os
import sqlite3
import time
from dataclasses import asdict
from pathlib import Path
from .post_run import RunObservation, plan_post_run, _id, _sha
from .store import canonical, digest, ZERO
from .snapshots import _pairs, _nonfinite, _read, _exclusive, _fsync_dir

TABLES = {'outbox_meta', 'outbox_drafts', 'outbox_events'}
MAX_SNAPSHOT_BYTES = 4 * 1024 * 1024


def _json(raw):
    return json.loads(raw, object_pairs_hook=_pairs, parse_constant=_nonfinite)


def _observation(value):
    if type(value) is not dict:
        raise ValueError('closed observation object required')
    data = dict(value)
    if type(data.get('stages')) not in (list, tuple):
        raise ValueError('stage array required')
    data['stages'] = tuple(tuple(v) if type(v) in (list, tuple) else v for v in data['stages'])
    try:
        out = RunObservation(**data)
    except TypeError as exc:
        raise ValueError('unknown or missing observation fields') from exc
    out.validate()
    return out


def _draft(provider, observation, envelope_sha256):
    if provider not in ('synthetic', 'kaggle'):
        raise ValueError('registered provider required')
    observation.validate(); _sha(envelope_sha256)
    key = digest([provider, observation.provider_job_id, observation.version])
    value = dict(schema='research_ops_delivery_draft_v1', provider=provider,
                 envelope_sha256=envelope_sha256, observation=asdict(observation),
                 plan=plan_post_run(observation), canonical_writer_attached=False,
                 provenance_attested=False, scientific_results_included=False,
                 execution_allowed=False, activation_allowed=False)
    raw = canonical(value)
    if len(raw.encode()) > 65536:
        raise ValueError('bounded operational draft required')
    return key, raw, digest(value)


class LearningOutbox:
    def __init__(self, path):
        self.path = Path(path)
        if self.path.is_symlink():
            raise ValueError('symlink outbox rejected')
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)

    @contextlib.contextmanager
    def transaction(self, create=False):
        if self.path.is_symlink() or (not create and not self.path.is_file()):
            raise ValueError('explicit regular outbox initialization required')
        db = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        db.row_factory = sqlite3.Row
        try:
            db.execute('PRAGMA synchronous=FULL')
            db.execute('BEGIN IMMEDIATE')
            actual = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if actual - TABLES:
                raise ValueError('not an outbox database; never modify another queue')
            yield db
            db.execute('COMMIT')
        except BaseException:
            if db.in_transaction: db.execute('ROLLBACK')
            raise
        finally:
            db.close()

    @staticmethod
    def _event(db, kind, key, payload):
        last = db.execute('SELECT seq,hash FROM outbox_events ORDER BY seq DESC LIMIT 1').fetchone()
        seq, previous = (last['seq']+1,last['hash']) if last else (1,ZERO)
        body = canonical(dict(seq=seq,kind=kind,key=key,payload=payload,at_ns=time.time_ns()))
        tip = hashlib.sha256((previous+body).encode()).hexdigest()
        db.execute('INSERT INTO outbox_events VALUES (?,?,?,?)',(seq,body,previous,tip))
        return tip

    def initialize(self, max_items=32):
        if type(max_items) is not int or not 1 <= max_items <= 128:
            raise ValueError('finite outbox capacity 1..128 required')
        with self.transaction(create=True) as db:
            db.execute('CREATE TABLE IF NOT EXISTS outbox_meta (singleton INTEGER PRIMARY KEY CHECK(singleton=1), max_items INTEGER NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS outbox_drafts (key TEXT PRIMARY KEY, body TEXT NOT NULL, hash TEXT NOT NULL, status TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS outbox_events (seq INTEGER PRIMARY KEY, body TEXT NOT NULL, previous TEXT NOT NULL, hash TEXT NOT NULL)')
            meta = db.execute('SELECT max_items FROM outbox_meta').fetchone()
            if meta:
                if meta[0] != max_items: raise ValueError('outbox capacity frozen')
                self._verify(db)
            else:
                if db.execute('SELECT count(*) FROM outbox_events').fetchone()[0] or db.execute('SELECT count(*) FROM outbox_drafts').fetchone()[0]:
                    raise ValueError('missing metadata on nonempty outbox; no reset')
                db.execute('INSERT INTO outbox_meta VALUES (1,?)',(max_items,))
                self._event(db,'POLICY',None,{'max_items':max_items})
        os.chmod(self.path,0o600)
        _fsync_dir(self.path.parent)
        return self.verify()

    def _verify(self, db, expected_tip=None):
        if expected_tip is not None: _sha(expected_tip)
        previous=ZERO; expected={}; capacity=None; count=0
        for count,row in enumerate(db.execute('SELECT * FROM outbox_events ORDER BY seq'),1):
            if len(row['body'].encode()) > 70000: raise ValueError('unbounded event')
            body=_json(row['body'])
            if type(body) is not dict or set(body)!={'seq','kind','key','payload','at_ns'}:
                raise ValueError('closed event required')
            if row['seq']!=count or body['seq']!=count or row['previous']!=previous or canonical(body)!=row['body']:
                raise ValueError('outbox chain order/canonical mismatch')
            if type(body['at_ns']) is not int or body['at_ns'] <= 0: raise ValueError('event clock required')
            previous=hashlib.sha256((previous+row['body']).encode()).hexdigest()
            if previous!=row['hash']: raise ValueError('outbox event hash mismatch')
            kind,key,payload=body['kind'],body['key'],body['payload']
            if kind=='POLICY':
                if count!=1 or key is not None or type(payload) is not dict or set(payload)!={'max_items'}:
                    raise ValueError('initial policy required')
                capacity=payload['max_items']
                if type(capacity) is not int or not 1<=capacity<=128: raise ValueError('bounded policy required')
            elif kind=='REGISTERED':
                if capacity is None or key in expected or type(payload) is not dict:
                    raise ValueError('invalid draft registration')
                if set(payload)!={'schema','provider','envelope_sha256','observation','plan','canonical_writer_attached','provenance_attested','scientific_results_included','execution_allowed','activation_allowed'}:
                    raise ValueError('closed operational draft required')
                k,raw,pin=_draft(payload['provider'],_observation(payload['observation']),payload['envelope_sha256'])
                if key!=k or raw!=canonical(payload): raise ValueError('draft reconstruction mismatch')
                expected[key]=[raw,pin,'REVIEW_PENDING']
            elif kind=='INVALIDATED':
                if key not in expected or expected[key][2]!='REVIEW_PENDING' or type(payload) is not dict or set(payload)!={'reason','review_id'}:
                    raise ValueError('invalid invalidation transition')
                if payload['reason'] not in ('SOURCE_INVALIDATED','MEASUREMENT_ERROR','SUPERSEDED_REQUIRES_REVIEW'):
                    raise ValueError('closed invalidation reason required')
                _id(payload['review_id']); expected[key][2]='INVALIDATED'
            elif kind=='DELIVERED':
                if key not in expected or expected[key][2]!='REVIEW_PENDING' or type(payload) is not dict:
                    raise ValueError('invalid delivery transition')
                if set(payload)!={'destination_id','episode_id','lesson_id','draft_sha256','review_sha256','ledger_tip'}:
                    raise ValueError('closed canonical ack required')
                for name in ('destination_id','episode_id','lesson_id'): _id(payload[name])
                for name in ('draft_sha256','review_sha256','ledger_tip'): _sha(payload[name])
                if payload['draft_sha256']!=expected[key][1]: raise ValueError('ack/draft mismatch')
                expected[key][2]='DELIVERED'
            else:
                raise ValueError('unknown outbox event')
            if capacity is None or len(expected)>capacity or count>1+2*capacity:
                raise ValueError('outbox policy exceeded')
        meta=db.execute('SELECT * FROM outbox_meta').fetchall()
        if len(meta)!=1 or meta[0]['singleton']!=1 or meta[0]['max_items']!=capacity:
            raise ValueError('outbox policy projection mismatch')
        actual={r['key']:[r['body'],r['hash'],r['status']] for r in db.execute('SELECT * FROM outbox_drafts')}
        if actual!=expected: raise ValueError('outbox draft projection mismatch')
        if expected_tip is not None and previous!=expected_tip: raise ValueError('external outbox tip mismatch')
        return dict(status='VERIFIED_LOCAL_OPERATIONAL_OUTBOX_NOT_AUTHORITY',tip=previous,
                    items=len(expected),max_items=capacity,events=count,
                    states={k:v[2] for k,v in expected.items()},
                    canonical_writer_attached=False,remote_durability_attested=False,
                    activation_allowed=False,execution_allowed=False)

    def verify(self, expected_tip=None):
        with self.transaction() as db: return self._verify(db,expected_tip)

    def enqueue(self, provider, observation, *, envelope_sha256, expected_tip):
        key,raw,pin=_draft(provider,observation,envelope_sha256)
        with self.transaction() as db:
            state=self._verify(db,expected_tip)
            old=db.execute('SELECT * FROM outbox_drafts WHERE key=?',(key,)).fetchone()
            if old:
                if old['body']!=raw: raise ValueError('different closeout for same provider/job/version; review conflict')
                if old['status'] not in ('REVIEW_PENDING','DELIVERED'): raise ValueError('invalidated draft cannot be silently reused')
                return dict(key=key,duplicate=True,outbox=state)
            if state['items']>=state['max_items']: raise ValueError('outbox capacity exhausted')
            db.execute('INSERT INTO outbox_drafts VALUES (?,?,?,?)',(key,raw,pin,'REVIEW_PENDING'))
            self._event(db,'REGISTERED',key,_json(raw))
            return dict(key=key,duplicate=False,outbox=self._verify(db))

    def invalidate(self, key, *, reason, review_id, expected_tip):
        _sha(key);_sha(expected_tip);_id(review_id)
        if reason not in ('SOURCE_INVALIDATED','MEASUREMENT_ERROR','SUPERSEDED_REQUIRES_REVIEW'):
            raise ValueError('closed reason required')
        with self.transaction() as db:
            self._verify(db,expected_tip)
            row=db.execute('SELECT status FROM outbox_drafts WHERE key=?',(key,)).fetchone()
            if not row or row[0]!='REVIEW_PENDING': raise ValueError('pending draft required')
            db.execute("UPDATE outbox_drafts SET status='INVALIDATED' WHERE key=?",(key,))
            self._event(db,'INVALIDATED',key,dict(reason=reason,review_id=review_id))
            return self._verify(db)

    def pending(self, *, expected_tip):
        with self.transaction() as db:
            self._verify(db,expected_tip)
            return [_json(r[0]) for r in db.execute("SELECT body FROM outbox_drafts WHERE status='REVIEW_PENDING' ORDER BY rowid")]


def export_outbox(outbox, output, *, expected_tip):
    with outbox.transaction() as db:
        state=outbox._verify(db,expected_tip)
        pack=dict(schema='research_ops_delivery_outbox_snapshot_v1',tip=state['tip'],
                  tables={t:[dict(r) for r in db.execute('SELECT * FROM '+t+' ORDER BY rowid')] for t in sorted(TABLES)})
        raw=(canonical(pack)+'\n').encode()
        if len(raw)>MAX_SNAPSHOT_BYTES: raise ValueError('outbox snapshot exceeds bound')
        _exclusive(output,raw)
    return dict(status='EXPORTED_LOCAL_OUTBOX_NOT_REMOTE_DURABILITY',sha256=hashlib.sha256(raw).hexdigest(),tip=state['tip'],bytes=len(raw),auto_delivery_allowed=False)


def restore_outbox(snapshot, destination, *, expected_sha256, expected_tip):
    _sha(expected_sha256);_sha(expected_tip)
    raw=_read(snapshot,MAX_SNAPSHOT_BYTES)
    if hashlib.sha256(raw).hexdigest()!=expected_sha256: raise ValueError('snapshot hash mismatch')
    pack=_json(raw)
    if type(pack) is not dict or set(pack)!={'schema','tip','tables'} or pack['schema']!='research_ops_delivery_outbox_snapshot_v1' or pack['tip']!=expected_tip:
        raise ValueError('closed externally pinned outbox snapshot required')
    if type(pack['tables']) is not dict or set(pack['tables'])!=TABLES: raise ValueError('closed snapshot tables required')
    columns={'outbox_meta':('singleton','max_items'),'outbox_drafts':('key','body','hash','status'),'outbox_events':('seq','body','previous','hash')}
    for t,cols in columns.items():
        rows=pack['tables'][t]
        if type(rows) is not list or len(rows)>{'outbox_meta':1,'outbox_drafts':128,'outbox_events':257}[t]: raise ValueError('bounded snapshot table required')
        for r in rows:
            if type(r) is not dict or set(r)!=set(cols): raise ValueError('closed snapshot row required')
    import tempfile
    def materialize(root):
        box=LearningOutbox(root/'outbox.sqlite'); box.initialize()
        with box.transaction() as db:
            for t,cols in columns.items():
                db.execute('DELETE FROM '+t)
                for r in pack['tables'][t]:
                    db.execute('INSERT INTO '+t+' VALUES ('+','.join('?' for _ in cols)+')',tuple(r[c] for c in cols))
            state=box._verify(db,expected_tip)
        return box,state
    with tempfile.TemporaryDirectory(prefix='research-ops-outbox-verify-') as temp:
        _,expected=materialize(Path(temp))
    dest=Path(destination);dest.mkdir(mode=0o700,exist_ok=False);_fsync_dir(dest.parent)
    box,state=materialize(dest)
    if state!=expected: raise ValueError('restored outbox mismatch; quarantine directory')
    return dict(status='RESTORED_OUTBOX_REVIEW_PENDING_NOT_DELIVERED',outbox=state,
                auto_delivery_allowed=False,canonical_ledger_modified=False)
