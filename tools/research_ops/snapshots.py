"""Portable synthetic queue snapshots. No provider, remote storage or auto-resume.
External latest snapshot SHA/tip must be retained by a different trusted system.
These controls detect corruption; they are not signatures or host authentication.
"""
import base64,contextlib,hashlib,json,os,sqlite3,stat,tempfile,time
from pathlib import Path
from .store import Store,HEX,ID,canonical

MAX_BYTES=16*1024*1024
FIELDS={'schema','snapshot_id','created_ns','event_tip','policy','jobs','events','receipts','scope'}
TABLE_FIELDS={'policy':['singleton','definition','attempts','seconds'],'jobs':['id','definition','pin','status','result_sha'],'events':['seq','body','previous','hash']}

def _pin(value):
    if not isinstance(value,str) or not HEX.fullmatch(value):raise ValueError('external SHA256/tip required')

def _pairs(items):
    d={}
    for k,v in items:
        if k in d:raise ValueError('duplicate snapshot key')
        d[k]=v
    return d

def _nonfinite(value):raise ValueError('nonfinite snapshot JSON')

def _read(path,limit):
    if os.name!='posix' or not hasattr(os,'O_NOFOLLOW'):raise ValueError('POSIX no-follow snapshot reader required')
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(fd,'rb') as f:
        before=os.fstat(f.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size>limit:raise ValueError('bounded regular snapshot file required')
        raw=f.read(limit+1);after=os.fstat(f.fileno())
    if len(raw)>limit or (before.st_size,before.st_mtime_ns,before.st_ctime_ns)!=(after.st_size,after.st_mtime_ns,after.st_ctime_ns):raise ValueError('snapshot changed or exceeded limit')
    return raw

def _fsync_dir(path):
    fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)

def _exclusive(path,raw):
    if os.name!='posix':raise ValueError('POSIX snapshot writer required')
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
    _fsync_dir(Path(path).parent)

def _shape(pack):
    if type(pack) is not dict or set(pack)!=FIELDS or pack['schema']!='research_ops_synthetic_queue_snapshot_v1' or pack['scope']!='synthetic':raise ValueError('closed synthetic snapshot schema required')
    if not isinstance(pack['snapshot_id'],str) or not ID.fullmatch(pack['snapshot_id']):raise ValueError('bounded snapshot id required')
    if type(pack['created_ns']) is not int or pack['created_ns']<=0:raise ValueError('snapshot timestamp required')
    _pin(pack['event_tip'])
    for table,limit in [('policy',1),('jobs',400),('events',1024)]:
        rows=pack[table]
        if type(rows) is not list or len(rows)>limit or (table=='policy' and len(rows)!=1):raise ValueError('finite snapshot table required')
        for row in rows:
            if type(row) is not dict or set(row)!=set(TABLE_FIELDS[table]):raise ValueError('closed snapshot row required')
    if type(pack['receipts']) is not dict or len(pack['receipts'])>100:raise ValueError('bounded receipt map required')
    expected={row['id'] for row in pack['jobs'] if row['result_sha'] is not None}
    registered={row['id'] for row in pack['jobs']}
    if not expected<=set(pack['receipts']) or not set(pack['receipts'])<=registered:raise ValueError('referenced receipts required; unknown receipts rejected')
    if any(row['status']=='SUCCEEDED_TECHNICAL' and row['result_sha'] is None for row in pack['jobs']):raise ValueError('technical success requires receipt')
    decoded={}
    for job,text in pack['receipts'].items():
        if not isinstance(job,str) or not ID.fullmatch(job) or not isinstance(text,str) or len(text)>90000:raise ValueError('bounded safe receipt required')
        try:raw=base64.b64decode(text,validate=True)
        except (ValueError,TypeError) as exc:raise ValueError('invalid receipt encoding') from exc
        if len(raw)>65536:raise ValueError('receipt exceeds bound')
        decoded[job]=raw
    return decoded

def _materialize(pack,root,decoded):
    root=Path(root);receipts=root/'receipts';receipts.mkdir(mode=0o700)
    for job,raw in decoded.items():_exclusive(receipts/(job+'.json'),raw)
    path=root/'queue.sqlite'
    # Temporary/new exclusive root only. Rebuild exact rows, never replay jobs.
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);os.close(fd)
    with contextlib.closing(sqlite3.connect(path)) as db:
        db.execute('PRAGMA synchronous=FULL')
        db.execute('CREATE TABLE policy (singleton INTEGER PRIMARY KEY CHECK(singleton=1), definition TEXT NOT NULL, attempts INTEGER NOT NULL, seconds INTEGER NOT NULL)')
        db.execute('CREATE TABLE jobs (id TEXT PRIMARY KEY, definition TEXT NOT NULL, pin TEXT NOT NULL, status TEXT NOT NULL, result_sha TEXT)')
        db.execute('CREATE TABLE events (seq INTEGER PRIMARY KEY, body TEXT NOT NULL, previous TEXT NOT NULL, hash TEXT NOT NULL)')
        for table,cols in TABLE_FIELDS.items():
            for row in pack[table]:db.execute('INSERT INTO '+table+' VALUES ('+','.join('?' for _ in cols)+')',[row[c] for c in cols])
        db.commit()
    with path.open('rb') as f:os.fsync(f.fileno())
    _fsync_dir(root)
    return Store(path).verify(pack['event_tip'])

def _validated(pack,expected_tip):
    _pin(expected_tip)
    if type(pack) is not dict or pack.get('event_tip')!=expected_tip:raise ValueError('snapshot external tip mismatch')
    decoded=_shape(pack)
    with tempfile.TemporaryDirectory(prefix='edgelab-snapshot-verify-') as temp:
        try:state=_materialize(pack,temp,decoded)
        except (sqlite3.Error,KeyError,TypeError) as exc:raise ValueError('invalid snapshot table or projection') from exc
    return state,decoded

def export_queue(store,output,*,snapshot_id,expected_tip):
    if not isinstance(snapshot_id,str) or not ID.fullmatch(snapshot_id):raise ValueError('bounded snapshot id required')
    _pin(expected_tip)
    # Lock queue writers while capturing tables and referenced receipts.
    with store.transaction() as db:
        store._verify(db,expected_tip)
        tables={table:[dict(row) for row in db.execute('SELECT * FROM '+table+' ORDER BY '+('rowid' if table=='jobs' else 'singleton' if table=='policy' else 'seq'))] for table in TABLE_FIELDS}
        receipts={};directory=store.path.parent/'receipts'
        if directory.is_symlink():raise ValueError('symlink receipt directory rejected')
        if directory.exists():
            for receipt in directory.iterdir():
                if receipt.suffix!='.json' or not ID.fullmatch(receipt.stem):raise ValueError('unexpected receipt entry; quarantine before snapshot')
                raw=_read(receipt,65536);receipts[receipt.stem]=base64.b64encode(raw).decode('ascii')
        for job in tables['jobs']:
            if job['result_sha'] is not None:
                raw=base64.b64decode(receipts.get(job['id'],''))
                if hashlib.sha256(raw).hexdigest()!=job['result_sha']:raise ValueError('receipt changed during snapshot')
        pack=dict(schema='research_ops_synthetic_queue_snapshot_v1',snapshot_id=snapshot_id,created_ns=time.time_ns(),event_tip=expected_tip,scope='synthetic',receipts=receipts,**tables)
        raw=(canonical(pack)+'\n').encode()
        if len(raw)>MAX_BYTES:raise ValueError('snapshot exceeds bound')
        _validated(pack,expected_tip)
        # Never overwrites. If interrupted, partial files remain invalid/quarantined.
        _exclusive(output,raw)
    return dict(status='LOCAL_SNAPSHOT_EXPORTED_NOT_REMOTE_DURABILITY',snapshot_id=snapshot_id,snapshot_sha256=hashlib.sha256(raw).hexdigest(),event_tip=expected_tip,bytes=len(raw),remote_copy_verified=False,external_latest_anchor_verified=False,auto_resume_allowed=False,market_execution_allowed=False)

def _load(path,expected_sha256,expected_tip):
    _pin(expected_sha256);_pin(expected_tip);raw=_read(path,MAX_BYTES)
    if hashlib.sha256(raw).hexdigest()!=expected_sha256:raise ValueError('snapshot external hash mismatch')
    try:pack=json.loads(raw,object_pairs_hook=_pairs,parse_constant=_nonfinite)
    except (json.JSONDecodeError,UnicodeError) as exc:raise ValueError('invalid snapshot JSON') from exc
    state,decoded=_validated(pack,expected_tip)
    return pack,state,decoded

def inspect_snapshot(path,*,expected_sha256,expected_tip):
    pack,state,_=_load(path,expected_sha256,expected_tip)
    orphan=[j for j in pack['receipts'] if next(row for row in pack['jobs'] if row['id']==j)['result_sha'] is None]
    return dict(status='VERIFIED_SYNTHETIC_SNAPSHOT_NOT_REMOTE_ATTESTATION',uncommitted_receipts_require_review=orphan,snapshot_id=pack['snapshot_id'],snapshot_sha256=expected_sha256,state=state,running_jobs_require_external_liveness_review=[j for j,s in state['states'].items() if s=='RUNNING'],remote_copy_verified=False,external_latest_anchor_verified=False,auto_resume_allowed=False,market_execution_allowed=False)

def restore_queue(path,destination,*,expected_sha256,expected_tip):
    pack,state,decoded=_load(path,expected_sha256,expected_tip)
    dest=Path(destination)
    # Exclusive fresh directory: never replaces another queue or drops attempts.
    dest.mkdir(mode=0o700,parents=False,exist_ok=False)
    _fsync_dir(dest.parent)
    actual=_materialize(pack,dest,decoded)
    if actual!=state:raise ValueError('restored state mismatch; quarantine directory')
    return dict(status='RESTORED_SYNTHETIC_STATE_NOT_RESUMED',snapshot_id=pack['snapshot_id'],state=actual,running_jobs_require_external_liveness_review=[j for j,s in state['states'].items() if s=='RUNNING'],budget_refunded=False,jobs_replayed=False,auto_resume_allowed=False,market_execution_allowed=False,remote_copy_verified=False,external_latest_anchor_verified=False)
