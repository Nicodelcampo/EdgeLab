"""Finite durable remote-attempt watch journal, not an executor or authority.
Host reserves BEFORE calling a provider and verifies immutable identity itself.
No network, raw data, canonical writing, automatic retry or scientific learning.
Hashes detect local corruption; rollback needs an external latest witness.
"""
import contextlib,json,os,sqlite3
from pathlib import Path
from .store import canonical,digest,ZERO
from .post_run import _sha,_id
from .learning_outbox import _json

TABLES={'watch_policy','watch_events'}
STATES={'QUEUED','RUNNING','COMPLETE','ERROR','CANCELLED'}
TERMINAL={'COMPLETE','ERROR','CANCELLED'}
FIELDS={'account','kernel_id','version','source_commit','bundle_sha256','plan_sha256'}

def identity(value):
    if type(value) is not dict or set(value)!=FIELDS:raise ValueError('closed immutable attempt identity')
    _id(value['account'])
    for k in ('kernel_id','version'):
        if type(value[k]) is not int or value[k]<1:raise ValueError('positive identity integer')
    s=value['source_commit']
    if type(s) is not str or len(s)!=40 or any(c not in '0123456789abcdef' for c in s):raise ValueError('full commit required')
    for k in ('bundle_sha256','plan_sha256'):_sha(value[k])
    return digest([value['account'],value['kernel_id'],value['version']])

def apply(state,event,policy):
    op,key,payload=event['op'],event['key'],event['payload']
    if op=='REGISTER':
        if identity(payload)!=key or key in state['attempts']:raise ValueError('duplicate or malformed registration')
        if len(state['attempts'])>=policy['max_attempts']:raise ValueError('attempt budget')
        state['attempts'][key]={'identity':payload,'status':None,'polls_reserved':0,'pending':{},'terminal_observed':False}
    elif op=='RESERVE':
        a=state['attempts'][key]
        if a['terminal_observed'] or a['pending']:raise ValueError('terminal or outstanding poll')
        if state['calls_reserved']>=policy['max_calls']:raise ValueError('durable call budget exhausted')
        if payload!={'ticket':a['polls_reserved']+1}:raise ValueError('ticket order')
        a['polls_reserved']+=1;state['calls_reserved']+=1;a['pending'][str(payload['ticket'])]=True
    elif op=='RESULT':
        a=state['attempts'][key]
        if set(payload)!={'ticket','status','response_sha256'}:raise ValueError('closed status result')
        _sha(payload['response_sha256']);s=payload['status']
        if s not in STATES|{'UNAVAILABLE'} or str(payload['ticket']) not in a['pending']:raise ValueError('unknown state or ticket')
        if a['status']=='RUNNING' and s=='QUEUED':raise ValueError('status regression')
        del a['pending'][str(payload['ticket'])]
        if s!='UNAVAILABLE':a['status']=s;a['terminal_observed']=s in TERMINAL
    else:raise ValueError('unknown watch event')

class RemoteWatch:
    def __init__(self,path):
        self.path=Path(path)
        if self.path.is_symlink():raise ValueError('symlink rejected')
    @contextlib.contextmanager
    def transaction(self,create=False):
        if self.path.is_symlink() or (not create and not self.path.is_file()):raise ValueError('explicit initialization')
        self.path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
        db=sqlite3.connect(self.path,isolation_level=None,timeout=10)
        try:
            db.execute('PRAGMA synchronous=FULL');db.execute('BEGIN IMMEDIATE')
            tables={r[0] for r in db.execute("select name from sqlite_master where type='table'")}
            if tables-TABLES:raise ValueError('foreign database rejected')
            yield db;db.execute('COMMIT')
        except BaseException:
            if db.in_transaction:db.execute('ROLLBACK')
            raise
        finally:db.close()
    def initialize(self,*,max_attempts=8,max_calls=64):
        if type(max_attempts) is not int or not 1<=max_attempts<=32 or type(max_calls) is not int or not 1<=max_calls<=256:raise ValueError('finite policy')
        p={'max_attempts':max_attempts,'max_calls':max_calls}
        with self.transaction(create=True) as db:
            db.execute('create table if not exists watch_policy (id integer primary key check(id=1), body text not null)')
            db.execute('create table if not exists watch_events (seq integer primary key, body text not null, previous text not null, hash text not null)')
            row=db.execute('select body from watch_policy').fetchone()
            if row:
                if row[0]!=canonical(p):raise ValueError('policy frozen')
                self._load(db)
            else:
                if db.execute('select count(*) from watch_events').fetchone()[0]:raise ValueError('missing policy')
                db.execute('insert into watch_policy values(1,?)',(canonical(p),))
        os.chmod(self.path,0o600)
        return self.snapshot()
    def _load(self,db,expected_tip=None):
        row=db.execute('select body from watch_policy').fetchone()
        if row is None:raise ValueError('missing policy')
        policy=_json(row[0]);state={'attempts':{},'calls_reserved':0};tip=digest(policy);n=0
        for n,(seq,body,prev,h) in enumerate(db.execute('select seq,body,previous,hash from watch_events order by seq'),1):
            e=_json(body)
            if len(body)>4096 or seq!=n or set(e)!={'op','key','payload'} or canonical(e)!=body or prev!=tip or h!=digest([tip,e]):raise ValueError('watch journal corruption')
            apply(state,e,policy);tip=h
        if expected_tip is not None:
            _sha(expected_tip)
            if tip!=expected_tip:raise ValueError('stale external tip')
        return policy,state,tip,n
    def _mutate(self,op,key,payload,expected_tip):
        with self.transaction() as db:
            policy,state,tip,n=self._load(db,expected_tip);e={'op':op,'key':key,'payload':payload};apply(state,e,policy)
            new=digest([tip,e]);db.execute('insert into watch_events values(?,?,?,?)',(n+1,canonical(e),tip,new))
        return self.snapshot()
    def register(self,value,*,expected_tip):
        key=identity(value)
        with self.transaction() as db:
            _,state,_,_=self._load(db,expected_tip)
            if key in state['attempts']:
                if state['attempts'][key]['identity']!=value:raise ValueError('attempt identity conflict')
                return self._summary(*self._load(db))
        return self._mutate('REGISTER',key,value,expected_tip)
    def reserve(self,value,*,expected_tip):
        key=identity(value)
        with self.transaction() as db:
            _,state,_,_=self._load(db,expected_tip);a=state['attempts'][key]
            if a['identity']!=value:raise ValueError('attempt identity conflict')
            ticket=a['polls_reserved']+1
        result=self._mutate('RESERVE',key,{'ticket':ticket},expected_tip);result['ticket']=ticket;return result
    def record(self,value,*,ticket,status,response_sha256,expected_tip):
        key=identity(value)
        if type(ticket) is not int or ticket<1:raise ValueError('integer ticket')
        with self.transaction() as db:
            _,state,_,_=self._load(db,expected_tip)
            if state['attempts'][key]['identity']!=value:raise ValueError('attempt identity conflict')
        return self._mutate('RESULT',key,{'ticket':ticket,'status':status,'response_sha256':response_sha256},expected_tip)
    @staticmethod
    def _summary(policy,state,tip,n):
        return {'schema':'research_ops_remote_watch_v1','policy':policy,'state':state,'tip_sha256':tip,'events':n,'network_attached':False,'remote_identity_attested':False,'complete_means_verified_success':False,'sampled_rss_is_measured_peak':False,'canonical_brain_written':False,'execution_allowed':False,'automatic_retry_allowed':False,'service_24x7_deployed':False}
    def snapshot(self,*,expected_tip=None):
        with self.transaction() as db:return self._summary(*self._load(db,expected_tip))
