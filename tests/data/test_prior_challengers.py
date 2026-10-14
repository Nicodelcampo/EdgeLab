"""Synthetic evidence adversarial tests. NO market data, price outcomes or review."""
from copy import deepcopy
from pathlib import Path
import pytest
from tests.data.test_research_data_gate import fixture, pin, DAYS, shard_fixture
from tests.synthetic_selection_evidence import add_selection_review
from edgelab.data.contract_regime import build_contract_regime
from edgelab.data.research_data_gate import require_research_eligibility, DataEligibilityError
from edgelab.data.research_session import read_research_session


def two_contracts(v0=(2000, 3000), v1=(2000, 3000)):
    f=fixture()
    meta=[{'root':'MNQ','contract':c,'expiry_ordinal':e,'first_trade_date':DAYS[0],
           'last_trade_date':DAYS[-1]} for c,e in [('MNQ_06-26',202606),('MNQ_09-26',202609)]]
    qty={(c,d):v for i,c in enumerate(['MNQ_06-26','MNQ_09-26'])
         for d,v in zip(DAYS,[v0[i],v1[i],v1[i]])}
    r=build_contract_regime(contracts=meta,daily_volumes=[{'root':'MNQ','contract':c,
        'trade_date':d,'volume':v,'complete_session':True} for (c,d),v in qty.items()],
        calendar_trade_dates=DAYS,source_identity=f['certificate']['source_identity'])
    f['regime_manifest']=r
    selected=r['daily_assignments'][1]['active_contract']
    f['certificate']['sessions'][f'MNQ|{selected}|{DAYS[1]}']={'status':'PASS','complete_session':True}
    add_selection_review(f['certificate'],r,'MNQ',qty)
    for s in f['certificate']['sessions'].values():s.setdefault('spread_p99_ticks',1)
    return f


def test_forward_challenger_selected_and_review_reference_returned():
    f=two_contracts();out=require_research_eligibility(**pin(f))
    assert out['contract']=='MNQ_09-26' and out['selection_review_evidence_sha256']=='c'*64
    assert not out['authority_authenticated'] and not out['promotion_allowed']


@pytest.mark.parametrize('case',['missing_review','schema','root','universe_sha','calendar_sha',
    'universe_unreviewed','calendar_unreviewed','asof_unreviewed','metadata_changed',
    'missing_decision','missing_proof_sha','cutoff_unreviewed','wrong_target','wrong_prior',
    'naive_cutoff','cutoff_after_open','cutoff_before_close','duplicate_candidate',
    'missing_candidate','extra_candidate','missing_measure','incomplete_measure',
    'unknown_measure','missing_measure_sha','future_measure','preclose_measure','missing_availability',
    'missing_volume','boolean_volume','negative_volume','same_day_volume','bad_tie_rule',
    'future_universe','missing_universe_time','numeric_policy_flag'])
def test_rejects_incomplete_inconsistent_or_future_challengers(case):
    f=two_contracts();c=f['certificate'];review=c['selection_review'];proof=review['decisions'][f'MNQ|{DAYS[1]}']
    measure=c['sessions'][f'MNQ|MNQ_06-26|{DAYS[0]}']
    if case=='missing_review':del c['selection_review']
    elif case=='schema':review['schema']='UNKNOWN'
    elif case=='root':review['root']='NQ'
    elif case=='universe_sha':review['universe_evidence_sha256']=None
    elif case=='calendar_sha':review['calendar_evidence_sha256']='bad'
    elif case=='universe_unreviewed':review['universe_review']='UNKNOWN'
    elif case=='calendar_unreviewed':review['calendar_review']='UNKNOWN'
    elif case=='asof_unreviewed':review['asof_review']='UNKNOWN'
    elif case=='metadata_changed':f['regime_manifest']['contracts'][0]['first_trade_date']=20260329
    elif case=='missing_decision':del review['decisions'][f'MNQ|{DAYS[1]}']
    elif case=='missing_proof_sha':proof['evidence_sha256']=None
    elif case=='cutoff_unreviewed':proof['cutoff_review']='UNKNOWN'
    elif case=='wrong_target':proof['trade_date']=DAYS[2]
    elif case=='wrong_prior':proof['signal_trade_date']=DAYS[1]
    elif case=='naive_cutoff':proof['decision_cutoff_utc']='2026-03-31T00:00:00'
    elif case=='cutoff_after_open':proof['decision_cutoff_utc']='2026-03-31T00:00:01Z'
    elif case=='cutoff_before_close':proof['decision_cutoff_utc']='2026-03-30T15:00:00Z'
    elif case=='duplicate_candidate':proof['candidate_contracts'].append('MNQ_06-26')
    elif case=='missing_candidate':proof['candidate_contracts'].remove('MNQ_06-26')
    elif case=='extra_candidate':proof['candidate_contracts'].append('MNQ_UNKNOWN')
    elif case=='missing_measure':del c['sessions'][f'MNQ|MNQ_06-26|{DAYS[0]}']
    elif case=='incomplete_measure':measure['complete_session']=False
    elif case=='unknown_measure':measure['status']='UNKNOWN'
    elif case=='missing_measure_sha':measure['evidence_sha256']=None
    elif case=='future_measure':measure['available_at_utc']='2026-03-31T01:00:00Z'
    elif case=='preclose_measure':measure['available_at_utc']='2026-03-30T15:00:00Z'
    elif case=='missing_availability':del measure['available_at_utc']
    elif case=='missing_volume':del measure['trade_quantity']
    elif case=='boolean_volume':measure['trade_quantity']=True
    elif case=='negative_volume':measure['trade_quantity']=-1
    elif case=='same_day_volume':del c['sessions'][f'MNQ|MNQ_06-26|{DAYS[0]}'];c['sessions'][f'MNQ|MNQ_06-26|{DAYS[1]}']=measure
    elif case=='bad_tie_rule':f['regime_manifest']['tie_rule']='CHOOSE_LATER'
    elif case=='future_universe':proof['contract_metadata_available_at_utc']='2026-03-31T01:00:00Z'
    elif case=='missing_universe_time':del proof['contract_metadata_available_at_utc']
    elif case=='numeric_policy_flag':f['regime_manifest']['strict_crossover']=1
    with pytest.raises(DataEligibilityError):require_research_eligibility(**pin(f))


def test_resealed_nonleader_not_accepted_even_with_selected_volume():
    f=two_contracts()
    for row in f['regime_manifest']['daily_assignments'][1:]:
        row['active_contract']='MNQ_06-26';row['current_volume']=2000
    with pytest.raises(DataEligibilityError,match='disagrees'):
        require_research_eligibility(**pin(f))


def test_real_zero_challenger_is_preserved_not_missing():
    f=two_contracts(v0=(2000,0),v1=(2000,0))
    assert require_research_eligibility(**pin(f))['contract']=='MNQ_06-26'
    del f['certificate']['sessions'][f'MNQ|MNQ_09-26|{DAYS[0]}']
    with pytest.raises(DataEligibilityError):require_research_eligibility(**pin(f))


def test_tie_keeps_current_and_no_backward_roll():
    f=two_contracts(v0=(2000,1000),v1=(3000,3000));f['trade_date']=DAYS[2]
    f['certificate']['holdout_first_trade_date']=20260402
    f['certificate']['allowed_trade_dates']=DAYS
    f['certificate']['sessions'][f'MNQ|MNQ_06-26|{DAYS[2]}']={'status':'PASS','complete_session':True}
    assert require_research_eligibility(**pin(f))['contract']=='MNQ_06-26'
    f=two_contracts(v0=(1000,2000),v1=(9000,2000));f['trade_date']=DAYS[2]
    f['certificate']['holdout_first_trade_date']=20260402;f['certificate']['allowed_trade_dates']=DAYS
    f['certificate']['sessions'][f'MNQ|MNQ_09-26|{DAYS[2]}']={'status':'PASS','complete_session':True}
    assert require_research_eligibility(**pin(f))['contract']=='MNQ_09-26'


def test_missing_challenger_review_fails_before_any_source_open(tmp_path,monkeypatch):
    path,f=shard_fixture(tmp_path);del f['certificate']['selection_review'];pin(f)
    def fail(*a,**k):raise AssertionError('source opened before challenger gate')
    monkeypatch.setattr(Path,'open',fail)
    with pytest.raises(DataEligibilityError):read_research_session(path=path,**f)


def test_selection_check_does_not_mutate_evidence():
    f=pin(two_contracts());before=deepcopy(f);require_research_eligibility(**f);assert f==before


def test_avzvol_readiness_is_not_source_or_economic_approval():
    import json
    root=Path(__file__).resolve().parents[2]
    evidence=json.loads((root/'config/research/avzvol_selection_readiness_review_v1.json').read_text())
    assert evidence['status']=='BLOCKED_PENDING_EXTERNAL_SELECTION_EVIDENCE'
    for field in ('research_authorized','promotion_allowed','price_payload_read','economic_outcomes_computed',
                  'raw_source_quality_certified','historical_bias_adjudicated','historical_consumption_verified',
                  'warmup_liquidity_certified','original_outputs_or_data_modified'):
        assert evidence[field] is False
    assert evidence['new_market_trials']==0 and evidence['four_original_proposals_preserved']
    assert evidence['economic_scope_requires_new_explicit_user_authorization']
    spec=json.loads((root/'specs/research/avzvol_incremental_design_v1.json').read_text())
    assert root/spec['candidate_selection_readiness_evidence_ref'] == root/'config/research/avzvol_selection_readiness_review_v1.json'
    assert spec['reviewed_input_pins'] is None and not spec['candidate_selection_readiness_is_certification']
