"""Invented fixtures only. No market source, review or certification produced."""
from copy import deepcopy
import hashlib
from pathlib import Path
import pytest
import pyarrow as pa
import pyarrow.parquet as pq
from edgelab.data.contract_regime import build_contract_regime, ContractRegimeError
from edgelab.data.research_data_gate import DataEligibilityError, REQUIRED_CHECKS, seal, require_research_eligibility
from edgelab.data.research_session import read_research_session

DAYS = [20260330, 20260331, 20260401]


def regime(volumes=None):
    return build_contract_regime(contracts=[{'root':'MNQ','contract':'MNQ_06-26',
        'expiry_ordinal':202606,'first_trade_date':DAYS[0],'last_trade_date':DAYS[-1]}],
        daily_volumes=[{'root':'MNQ','contract':'MNQ_06-26','trade_date':d,'volume':v,
            'complete_session':True} for d,v in zip(DAYS, volumes if volumes is not None else [2000]*3)],
        calendar_trade_dates=DAYS, source_identity={'dataset':'SYNTHETIC_TEST_ONLY','version':1})


def fixture():
    r=regime()
    c={'status':'SANITIZED_VERIFIED','checks':dict.fromkeys(REQUIRED_CHECKS,'PASS'),
       'source_identity':r['source_identity'], 'holdout_first_trade_date':20260401,
       'allowed_trade_dates':DAYS[:2], 'sessions':{
           'MNQ|MNQ_06-26|20260330':{'status':'PASS','complete_session':True,
                                  'trade_quantity':2000,'spread_p99_ticks':1},
           'MNQ|MNQ_06-26|20260331':{'status':'PASS','complete_session':True}}}
    limits={'root':'MNQ','frozen_before_strategy':True,'min_previous_session_volume':1000,
            'max_previous_session_spread_p99_ticks':2}
    return {'certificate':c,'regime_manifest':r,'root':'MNQ','trade_date':20260331,
            'liquidity_limits':limits}


def pin(f):
    f['expected_certificate_sha256']=seal(f['certificate'])
    r=f['regime_manifest']; r.pop('manifest_sha256',None)
    r['manifest_sha256']=seal(r)
    f['expected_regime_sha256']=r['manifest_sha256']
    f['expected_liquidity_limits_sha256']=seal(f['liquidity_limits'])
    return f


def test_valid_metadata_no_authority():
    out=require_research_eligibility(**pin(fixture()))
    assert out['contract']=='MNQ_06-26'
    assert out['promotion_allowed'] is False and out['authority_authenticated'] is False


@pytest.mark.parametrize('field,value', [('trade_quantity',0),('trade_quantity',True),
    ('trade_quantity',-1),('trade_quantity',10),('trade_quantity',float('inf')),
    ('trade_quantity',float('nan')),('trade_quantity','2000'),('spread_p99_ticks',True),
    ('spread_p99_ticks',-1),('spread_p99_ticks',8),('spread_p99_ticks',float('inf')),
    ('complete_session',False),('status','UNKNOWN')])
def test_prior_measurements_rejected(field,value):
    f=fixture();f['certificate']['sessions']['MNQ|MNQ_06-26|20260330'][field]=value
    with pytest.raises(DataEligibilityError): require_research_eligibility(**pin(f))


@pytest.mark.parametrize('mutation', ['status','checks','identity','target_missing','target_incomplete',
    'limits_unfrozen','wrong_root','same_day','adjustment','unknown_decision','calendar_duplicate',
    'calendar_invalid','allowed_duplicate','allowed_holdout','allowed_bool','assignment_duplicate',
    'backward_contract','selected_volume','unlabeled','signal_bool','schema','bad_date'])
def test_missing_or_inconsistent_metadata(mutation):
    f=fixture();c=f['certificate'];r=f['regime_manifest'];row=r['daily_assignments'][1]
    if mutation=='status':c['status']='REMOTE_LISTED'
    elif mutation=='checks':del c['checks']['schema']
    elif mutation=='identity':c['source_identity']={'dataset':'OTHER'}
    elif mutation=='target_missing':del c['sessions']['MNQ|MNQ_06-26|20260331']
    elif mutation=='target_incomplete':c['sessions']['MNQ|MNQ_06-26|20260331']['complete_session']=False
    elif mutation=='limits_unfrozen':f['liquidity_limits']['frozen_before_strategy']=False
    elif mutation=='wrong_root':f['root']='NQ'
    elif mutation=='same_day':row['signal_trade_date']=20260331
    elif mutation=='adjustment':r['price_adjustment']='BACK_ADJUSTED'
    elif mutation=='unknown_decision':row['decision']='UNDECLARED'
    elif mutation=='calendar_duplicate':r['calendar_trade_dates'].append(20260401)
    elif mutation=='calendar_invalid':r['calendar_trade_dates'][0]=20260230
    elif mutation=='allowed_duplicate':c['allowed_trade_dates'].append(20260331)
    elif mutation=='allowed_holdout':c['allowed_trade_dates'].append(20260401)
    elif mutation=='allowed_bool':c['allowed_trade_dates']=[True]
    elif mutation=='assignment_duplicate':r['daily_assignments'].append(deepcopy(row))
    elif mutation=='backward_contract':row['active_contract']='UNKNOWN'
    elif mutation=='selected_volume':row['current_volume']=2001
    elif mutation=='unlabeled':row['regime_id']=None
    elif mutation=='signal_bool':row['signal_trade_date']=True
    elif mutation=='schema':r['schema_version']='OTHER'
    elif mutation=='bad_date':f['trade_date']=20260230
    with pytest.raises(DataEligibilityError): require_research_eligibility(**pin(f))


@pytest.mark.parametrize('name', ['certificate','regime','liquidity_limits'])
def test_pin_mismatch(name):
    f=pin(fixture());f['expected_'+name+'_sha256']='a'*64
    with pytest.raises(DataEligibilityError):require_research_eligibility(**f)


@pytest.mark.parametrize('day', [20260401,20260402,True,'20260331',20260331.0])
def test_reserved_or_unapproved_or_bad_typed_day(day):
    f=pin(fixture());f['trade_date']=day
    with pytest.raises(DataEligibilityError):require_research_eligibility(**f)


@pytest.mark.parametrize('key', ['certificate','regime_manifest','liquidity_limits'])
def test_malformed_top_level(key):
    f=pin(fixture());f[key]=[]
    with pytest.raises(DataEligibilityError):require_research_eligibility(**f)


@pytest.mark.parametrize('value',[float('inf'),float('-inf'),float('nan'),True,'bad'])
def test_regime_rejects_bad_volume(value):
    with pytest.raises(ContractRegimeError):regime([value,2000,2000])


def test_zero_volume_excludes_next_session_not_fabricated_missing():
    r=regime([0,2000,0]);a=r['daily_assignments']
    assert not a[1]['eligible'] and a[1]['decision']=='NO_POSITIVE_SELECTED_VOLUME'
    assert a[1]['regime_id'] is None
    assert a[2]['eligible'] and a[2]['signal_trade_date']==20260331


def test_monotonic_chain_does_not_return_to_backward_liquid_contract():
    r=build_contract_regime(contracts=[{'root':'MNQ','contract':c,'expiry_ordinal':expiry,
        'first_trade_date':DAYS[0],'last_trade_date':DAYS[-1]}
        for c,expiry in [('MNQ_03-26',202603),('MNQ_06-26',202606)]],
        daily_volumes=[{'root':'MNQ','contract':c,'trade_date':d,'volume':v,'complete_session':True}
           for c,values in [('MNQ_03-26',[10,2000,2000]),('MNQ_06-26',[2000,0,0])]
           for d,v in zip(DAYS,values)],calendar_trade_dates=DAYS,
        source_identity={'dataset':'SYNTHETIC_TEST_ONLY'})
    assert r['daily_assignments'][1]['active_contract']=='MNQ_06-26'
    assert r['daily_assignments'][2]['eligible'] is False
    assert r['daily_assignments'][2]['active_contract']=='MNQ_06-26'


def shard_fixture(tmp_path, *, dates=(20260331,20260331), roots=None, contracts=None, stats=True):
    path=tmp_path/'synthetic-session.parquet'
    table=pa.table({'root':roots or ['MNQ']*len(dates),
        'contract':contracts or ['MNQ_06-26']*len(dates),
        'trade_date':pa.array(dates,type=pa.int64()),'last':[100]*len(dates)})
    pq.write_table(table,path,write_statistics=stats,row_group_size=1)
    f=fixture();f['certificate']['sessions']['MNQ|MNQ_06-26|20260331']['shard']={
        'basename':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'size_bytes':path.stat().st_size,'rows':len(table)}
    return path,pin(f)


def spy_reads(monkeypatch):
    real=pq.ParquetFile;calls=[]
    class Spy:
        def __init__(self,*a,**k):self.p=real(*a,**k)
        def __getattr__(self,k):return getattr(self.p,k)
        def read(self,*a,**k):calls.append('read');return self.p.read(*a,**k)
    monkeypatch.setattr(pq,'ParquetFile',Spy)
    return calls


def test_reader_actual_parquet_and_evidence(tmp_path,monkeypatch):
    path,f=shard_fixture(tmp_path);calls=spy_reads(monkeypatch)
    table,e=read_research_session(path=path,**f)
    assert len(table)==2 and calls==['read']
    assert e['source_sha256']==f['certificate']['sessions']['MNQ|MNQ_06-26|20260331']['shard']['sha256']
    assert e['reader_contract']=='single_session_shard_v1'
    assert e['promotion_allowed'] is False and e['existing_consumers_rewired'] is False


@pytest.mark.parametrize('reason',['holdout','uncertified','pin','missing_shard','shard_basename'])
def test_gate_rejects_before_any_source_open(tmp_path,monkeypatch,reason):
    path,f=shard_fixture(tmp_path)
    if reason=='holdout':f['trade_date']=20260401
    elif reason=='uncertified':f['certificate']['status']='RAW';pin(f)
    elif reason=='pin':f['expected_certificate_sha256']='a'*64
    elif reason=='missing_shard':del f['certificate']['sessions']['MNQ|MNQ_06-26|20260331']['shard'];pin(f)
    elif reason=='shard_basename':path=tmp_path/'wrong-name.parquet'
    def fail(*a,**k):raise AssertionError('source opened before rejection')
    monkeypatch.setattr(Path,'open',fail)
    with pytest.raises(DataEligibilityError):read_research_session(path=path,**f)


@pytest.mark.parametrize('variant',['mixed_date','null_date','wrong_root','wrong_contract','no_stats',
    'wrong_hash','wrong_size','wrong_rows','no_identity'])
def test_shard_rejects_before_payload(tmp_path,monkeypatch,variant):
    kw={}
    if variant=='mixed_date':kw['dates']=(20260331,20260401)
    elif variant=='null_date':kw['dates']=(20260331,None)
    elif variant=='wrong_root':kw['roots']=['MNQ','NQ']
    elif variant=='wrong_contract':kw['contracts']=['MNQ_06-26','MNQ_09-26']
    elif variant=='no_stats':kw['stats']=False
    path,f=shard_fixture(tmp_path,**kw)
    s=f['certificate']['sessions']['MNQ|MNQ_06-26|20260331']['shard']
    if variant=='wrong_hash':s['sha256']='a'*64
    elif variant=='wrong_size':s['size_bytes']+=1
    elif variant=='wrong_rows':s['rows']+=1
    elif variant=='no_identity':
        pq.write_table(pa.table({'trade_date':[20260331,20260331]}),path)
        s.update(size_bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    pin(f);calls=spy_reads(monkeypatch)
    with pytest.raises(DataEligibilityError):read_research_session(path=path,**f)
    assert calls==[]


def test_forward_roll_gate_selects_leader_volume():
    f=fixture()
    days=[20260327,20260330,20260331]
    r=build_contract_regime(contracts=[{'root':'MNQ','contract':c,'expiry_ordinal':e,
        'first_trade_date':days[0],'last_trade_date':days[-1]}
        for c,e in [('MNQ_03-26',202603),('MNQ_06-26',202606)]],
        daily_volumes=[{'root':'MNQ','contract':c,'trade_date':d,'volume':v,'complete_session':True}
          for c,vs in [('MNQ_03-26',[3000,10,10]),('MNQ_06-26',[10,2000,2000])]
          for d,v in zip(days,vs)],calendar_trade_dates=days,
        source_identity=f['certificate']['source_identity'])
    f['regime_manifest']=r
    assert r['daily_assignments'][-1]['decision']=='ROLL_FORWARD'
    assert require_research_eligibility(**pin(f))['contract']=='MNQ_06-26'


@pytest.mark.parametrize('field,value',[('signal_lag_sessions',True),('daily_assignments',None)])
def test_bad_regime_shapes(field,value):
    f=fixture();f['regime_manifest'][field]=value
    with pytest.raises(DataEligibilityError):require_research_eligibility(**pin(f))


def test_metadata_cli_pass_and_fail_without_source_reads(tmp_path):
    import subprocess,sys,json
    tool=Path(__file__).resolve().parents[2]/'tools/check_research_data_gate.py'
    f=pin(fixture());bundle=tmp_path/'bundle.json'
    bundle.write_text(json.dumps({'schema_version':'research_gate_request_v1','request':f}))
    out=subprocess.run([sys.executable,str(tool),'--bundle',str(bundle)],capture_output=True,text=True)
    assert out.returncode==0 and json.loads(out.stdout)['status']=='PASS_METADATA_ONLY'
    f['trade_date']=20260401
    bundle.write_text(json.dumps({'schema_version':'research_gate_request_v1','request':f}))
    out=subprocess.run([sys.executable,str(tool),'--bundle',str(bundle)],capture_output=True,text=True)
    assert out.returncode==2 and json.loads(out.stdout)['status']=='BLOCKED_METADATA'


def test_metadata_cli_rejects_missing_pins(tmp_path):
    import subprocess,sys,json
    tool=Path(__file__).resolve().parents[2]/'tools/check_research_data_gate.py'
    bundle=tmp_path/'bundle.json'
    bundle.write_text(json.dumps({'schema_version':'research_gate_request_v1','request':fixture()}))
    out=subprocess.run([sys.executable,str(tool),'--bundle',str(bundle)],capture_output=True,text=True)
    assert out.returncode==2
    assert json.loads(out.stdout)['market_data_read'] is False
