"""Finite durable submission-intent primitive. No executor or permission grant.

One shared journal must be adopted by the existing host BEFORE provider access.
After begin_send a crash is ambiguous: no resend, no budget refund. Only an
exact independently reconciled remote job can acknowledge/close that intent.
Hashes detect local corruption, not rollback/latestness or remote truth.
"""
import contextlib,json,os,sqlite3
from pathlib import Path
from .store import canonical,digest
from .post_run import _sha,_id

REQUEST_FIELDS={'account','spec_sha256','source_commit','bundle_sha256','plan_sha256'}
JOB_FIELDS={'account','kernel_id','version','source_commit','bundle_sha256','plan_sha256'}
TERMINAL={'COMPLETE','ERROR','CANCELLED'}

def request_key(x):
    if type(x) is not dict or set(x)!=REQUEST_FIELDS:raise ValueError('closed target-free request identity')
    _id(x['account'])
    for k in ('spec_sha256','bundle_sha256','plan_sha256'):_sha(x[k])
    s=x['source_commit']
    if type(s) is not str or len(s)!=40 or any(c not in '0123456789abcdef' for c in s):raise ValueError('full source commit')
    return digest(x)

def verify_job(job,request):
    if type(job) is not dict or set(job)!=JOB_FIELDS:raise ValueError('exact remote job identity')
    if any(type(job[k]) is not int or job[k]<1 for k in ('kernel_id','version')):raise ValueError('positive remote coordinates')
    if any(job[k]!=request[k] for k in ('account','source_commit','bundle_sha256','plan_sha256')):raise ValueError('job/request binding conflict')

class DispatchIntent:
    def __init__(self,path):self.path=Path(path)
    @contextlib.contextmanager
    def transaction(self,create=False):
        if self.path.is_symlink() or (not create and not self.path.is_file()):raise ValueError('explicit non-symlink initialization')
        self.path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
        db=sqlite3.connect(self.path,isolation_level=None,timeout=10)
        try:
            db.execute('PRAGMA synchronous=FULL');db.execute('BEGIN IMMEDIATE')
            tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if tables-{'dispatch_policy','dispatch_events'}:raise ValueError('foreign state rejected')
            yield db;db.execute('COMMIT')
        except BaseException:
            if db.in_transaction:db.execute('ROLLBACK')
            raise
        finally:db.close()
    def initialize(self,*,account,max_pending=1,max_intents=8):
        _id(account)
        if type(max_pending) is not int or not 1<=max_pending<=2 or type(max_intents) is not int or not max_pending<=max_intents<=32:raise ValueError('finite conservative policy')
        p={'account':account,'max_pending':max_pending,'max_intents':max_intents}
        with self.transaction(True) as db:
            db.execute('CREATE TABLE IF NOT EXISTS dispatch_policy(id INTEGER PRIMARY KEY CHECK(id=1), body TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS dispatch_events(seq INTEGER PRIMARY KEY,body TEXT NOT NULL,previous TEXT NOT NULL,hash TEXT NOT NULL)')
            old=db.execute('SELECT body FROM dispatch_policy').fetchone()
            if old:
                if old[0]!=canonical(p):raise ValueError('policy cannot change on recovery')
                self._load(db)
            else:
                if db.execute('SELECT COUNT(*) FROM dispatch_events').fetchone()[0]:raise ValueError('missing policy')
                db.execute('INSERT INTO dispatch_policy VALUES(1,?)',(canonical(p),))
        os.chmod(self.path,0o600);return self.snapshot()
    @staticmethod
    def apply(state,event,policy):
        op,key,x=event['op'],event['key'],event['payload']
        if op=='PREPARE':
            if request_key(x)!=key or key in state or x['account']!=policy['account']:raise ValueError('duplicate or mismatched request')
            if len(state)>=policy['max_intents']:raise ValueError('lifetime intent budget; no recovery reset')
            pending=sum(a['status'] not in TERMINAL|{'ABANDONED_PRE_SEND'} for a in state.values())
            if pending>=policy['max_pending']:raise ValueError('shared pending capacity')
            state[key]={'request':x,'status':'PREPARED','job':None}
        elif op=='BEGIN_SEND':
            a=state[key]
            if x!={} or a['status']!='PREPARED':raise ValueError('send only once; ambiguous attempts cannot retry')
            a['status']='SEND_UNCERTAIN'
        elif op=='ACK':
            a=state[key];verify_job(x,a['request'])
            if a['status']!='SEND_UNCERTAIN':raise ValueError('reconcile only previously begun send')
            if any(v['job'] and (v['job']['account'],v['job']['kernel_id'],v['job']['version'])==(x['account'],x['kernel_id'],x['version']) for v in state.values()):raise ValueError('remote job already bound')
            a['job']=x;a['status']='ACKNOWLEDGED'
        elif op=='TERMINAL':
            a=state[key]
            if set(x)!={'job','status'} or x['status'] not in TERMINAL or a['status']!='ACKNOWLEDGED' or x['job']!=a['job']:raise ValueError('exact acknowledged terminal identity required')
            a['status']=x['status']
        elif op=='ABANDON':
            a=state[key]
            if x!={} or a['status']!='PREPARED':raise ValueError('ambiguous send cannot be abandoned or refunded')
            a['status']='ABANDONED_PRE_SEND'
        else:raise ValueError('unknown transition')
    def _load(self,db,expected_tip=None):
        p=json.loads(db.execute('SELECT body FROM dispatch_policy').fetchone()[0]);state={};tip=digest(p);n=0
        for n,(seq,body,prev,h) in enumerate(db.execute('SELECT seq,body,previous,hash FROM dispatch_events ORDER BY seq'),1):
            e=json.loads(body)
            if len(body)>4096 or set(e)!={'op','key','payload'} or canonical(e)!=body or seq!=n or prev!=tip or h!=digest([tip,e]):raise ValueError('journal corruption')
            self.apply(state,e,p);tip=h
        if expected_tip is not None and expected_tip!=tip:raise ValueError('stale tip; no mutation')
        return p,state,tip,n
    def _mutate(self,op,key,payload,expected_tip):
        _sha(expected_tip)
        with self.transaction() as db:
            p,state,tip,n=self._load(db,expected_tip);e={'op':op,'key':key,'payload':payload};self.apply(state,e,p)
            db.execute('INSERT INTO dispatch_events VALUES(?,?,?,?)',(n+1,canonical(e),tip,digest([tip,e])))
        return self.snapshot()
    def prepare(self,request,*,expected_tip):
        key=request_key(request)
        with self.transaction() as db:
            p,state,tip,n=self._load(db,expected_tip)
            if key in state:return self._summary(p,state,tip,n,key)
        s=self._mutate('PREPARE',key,request,expected_tip);s['intent_key']=key;return s
    def begin_send(self,key,*,expected_tip):return self._mutate('BEGIN_SEND',key,{},expected_tip)
    def acknowledge(self,key,job,*,expected_tip):
        with self.transaction() as db:
            p,state,tip,n=self._load(db,expected_tip);a=state[key]
            if a['job']==job and a['status'] in TERMINAL|{'ACKNOWLEDGED'}:return self._summary(p,state,tip,n,key)
        return self._mutate('ACK',key,job,expected_tip)
    def terminal(self,key,job,status,*,expected_tip):
        with self.transaction() as db:
            p,state,tip,n=self._load(db,expected_tip);a=state[key]
            if a['job']==job and a['status']==status and status in TERMINAL:return self._summary(p,state,tip,n,key)
        return self._mutate('TERMINAL',key,{'job':job,'status':status},expected_tip)
    def abandon_before_send(self,key,*,expected_tip):return self._mutate('ABANDON',key,{},expected_tip)
    @staticmethod
    def _summary(policy,state,tip,n,key=None):
        return {'schema':'dispatch_intent_v1','policy':policy,'intents':state,'tip_sha256':tip,'events':n,'intent_key':key,
                'execution_authorized':False,'network_attached':False,'remote_identity_attested':False,
                'global_account_budget_attested':False,'external_latest_witness_bound':False,
                'automatic_resend_allowed':False,'canonical_brain_written':False}
    def snapshot(self):
        with self.transaction() as db:return self._summary(*self._load(db))
