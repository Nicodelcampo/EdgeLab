"""Invented pre-anchor covariates only; no source data, outcomes or acceptance."""
from copy import deepcopy
import importlib.util
import math
from pathlib import Path
import pytest
from edgelab.kaggle.avzvol_design import AVZVOLDesignError, FEATURES
from edgelab.kaggle.avzvol_diagnostics import describe_control_census

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('synthetic_smoke',ROOT/'tools/avzvol_design_smoke.py')
smoke=importlib.util.module_from_spec(spec);spec.loader.exec_module(smoke)


def fixture():return smoke.synthetic_fixture()

def run(r,c,p):return describe_control_census(r,c,policy=p,holdout_start='2026-10-01')

def test_population_accounting_and_no_permission():
    r,c,p=fixture();d=run(r,c,p)
    assert d['real_event_count']==2 and d['matched_real_event_count']==1
    assert d['unsupported_real_event_count']==1 and d['selected_unique_control_count']==2
    assert math.isclose(sum(d['control_analysis_weights'].values()),1)
    for flag in ('balance_accepted','support_accepted','zone_absence_verified','census_completeness_verified',
        'source_quality_certified','research_authorized','own_census_outcome_benchmark_implemented',
        'inference_implemented','outcomes_read','pnl_computed','economic_outcomes_computed','bias_adjudicated',
        'ecdf_metric_is_hypothesis_test','scale_metric_is_standardized_mean_difference',
        'weight_concentration_is_independent_sample_size'):
        assert d[flag] is False


def test_shuffle_invariant_and_inputs_unmodified():
    r,c,p=fixture();before=deepcopy((r,c,p));a=run(r,c,p);assert (r,c,p)==before
    assert a==run(list(reversed(r)),list(reversed(c)),p)


def test_pair_gaps_do_not_cancel_opposing_controls():
    r,c,p=fixture();r=r[:1];c[0]['features']={f:.8 for f in FEATURES};c[1]['features']={f:1.2 for f in FEATURES}
    gaps=run(r,c,p)['pair_gaps_in_external_scale_units']['occ']
    assert gaps['mean_signed_gap']==pytest.approx(0)
    assert gaps['mean_absolute_gap']==pytest.approx(.2)
    assert gaps['maximum_absolute_gap']==pytest.approx(.2)


def test_reused_control_mass_and_own_census_reference_preserved():
    r,c,p=fixture();r[1]['features']={f:1.1 for f in FEATURES};p['max_controls']=1
    d=run(r,c,p);assert d['selected_unique_control_count']==1
    assert d['control_reuse_counts']=={'SYNTHETIC-C1':2}
    assert d['maximum_control_analysis_weight']==1
    assert d['control_weight_concentration_sum_squares']==1
    x=d['per_stratum'][0]['comparisons']['selected_unique_controls_vs_declared_census']['features']['occ']
    assert x['left_mean']==pytest.approx(1.1) and x['right_mean']==pytest.approx(1.15)
    assert x['maximum_weighted_ecdf_gap']==pytest.approx(.5)


def test_equal_real_weights_not_pair_count_weights():
    r,c,p=fixture();r[1]['features']={f:1.65 for f in FEATURES};p['calipers']={f:.5 for f in FEATURES}
    d=run(r,c,p)
    assert d['matched_real_event_count']==2
    assert d['control_analysis_weights']=={'SYNTHETIC-C1':.25,'SYNTHETIC-C2':.75}
    assert d['control_weight_concentration_sum_squares']==pytest.approx(.625)
    comparisons=d['per_stratum'][0]['comparisons']
    assert comparisons['selected_unique_controls_vs_declared_census']['features']['occ']['left_mean']==pytest.approx(1.15)
    assert comparisons['analysis_controls_vs_declared_census']['features']['occ']['left_mean']==pytest.approx(1.175)


def test_no_support_still_retains_full_reference_census():
    r,c,p=fixture();p['minimum_separation_seconds']=10000;d=run(r,c,p)
    assert d['control_analysis_weights']=={} and d['maximum_control_analysis_weight'] is None
    assert d['selected_unique_control_count']==0 and d['declared_candidate_census_count']==2
    assert all(x is None for x in d['pair_gaps_in_external_scale_units'].values())
    for x in d['per_stratum'][0]['comparisons'].values():
        assert x['status']=='NOT_COMPUTABLE_EMPTY_POPULATION'


def test_census_is_not_restricted_to_caliper_eligible_candidates():
    r,c,p=fixture();extra=deepcopy(c[0]);extra['event_id']='SYNTHETIC-FAR';extra['anchor_utc']='2026-01-05T15:20:00Z';extra['feature_asof_utc']=extra['anchor_utc'];extra['features']={f:50 for f in FEATURES};c.append(extra)
    d=run(r,c,p);s=d['per_stratum'][0]
    assert s['declared_candidate_census_events']==3 and s['unselected_candidate_events']==1
    assert s['comparisons']['selected_unique_controls_vs_declared_census']['right_unique_events']==3


def test_strata_without_reals_or_without_controls_retained_not_pooled():
    r,c,p=fixture();r[1]['cell']='REAL_ONLY';extra=deepcopy(c[0]);extra['cell']='CONTROL_ONLY';extra['event_id']='OTHER-C';c.append(extra)
    strata={s['stratum']['cell']:s for s in run(r,c,p)['per_stratum']}
    assert len(strata)==3
    assert strata['CONTROL_ONLY']['support_fraction'] is None
    assert strata['REAL_ONLY']['support_fraction']==0
    assert strata['CONTROL_ONLY']['comparisons']['analysis_controls_vs_declared_census']['status']=='NOT_COMPUTABLE_EMPTY_POPULATION'


def test_same_value_ecdf_advances_ties_together():
    r,c,p=fixture()
    for row in r+c:row['features']={f:1 for f in FEATURES}
    d=run(r,c,p)
    for comparison in d['per_stratum'][0]['comparisons'].values():
        assert all(x['maximum_weighted_ecdf_gap']==0 for x in comparison['features'].values())
    assert not d['balance_accepted']


@pytest.mark.parametrize('field',['O5','pnl','future_return'])
def test_outcome_fields_rejected(field):
    r,c,p=fixture();c[0][field]=1
    with pytest.raises(AVZVOLDesignError):run(r,c,p)


def test_known_real_anchor_alias_rejected_not_dropped_from_reference():
    r,c,p=fixture();c[0]['anchor_utc']=r[0]['anchor_utc'];c[0]['feature_asof_utc']=r[0]['anchor_utc']
    with pytest.raises(AVZVOLDesignError,match='alias'):run(r,c,p)


@pytest.mark.parametrize('mutation',['future','holdout','duplicate','missing_feature','missing_policy','incomplete','zero_scale','nan','boolean'])
def test_existing_design_guards_apply(mutation):
    r,c,p=fixture()
    if mutation=='future':c[0]['feature_asof_utc']='2026-01-05T16:00:00Z'
    elif mutation=='holdout':r[0]['session']='2026-10-01'
    elif mutation=='duplicate':c.append(deepcopy(c[0]))
    elif mutation=='missing_feature':del c[0]['features']['occ']
    elif mutation=='missing_policy':del p['calipers']['occ']
    elif mutation=='incomplete':c[0]['prewindow_complete']=False
    elif mutation=='zero_scale':p['scales']['occ']=0
    elif mutation=='nan':c[0]['features']['occ']=float('nan')
    elif mutation=='boolean':c[0]['features']['occ']=True
    with pytest.raises(AVZVOLDesignError):run(r,c,p)


def test_extreme_diagnostic_overflow_stops_without_clipping():
    r,c,p=fixture();r=r[:1]
    for row in r:row['features']={f:1e308 for f in FEATURES}
    c[0]['features']={f:1e308 for f in FEATURES}
    c[1]['features']={f:-1e308 for f in FEATURES}
    p['scales']={f:.01 for f in FEATURES}
    with pytest.raises(AVZVOLDesignError,match='overflow'):run(r,c,p)


def test_research_cli_stops_before_fixture_for_census_report(capsys):
    from unittest.mock import patch
    with patch.object(smoke,'synthetic_fixture',side_effect=AssertionError('must not construct inputs')):
        assert smoke.main(['--purpose','research','--report','control-census'])==2
    import json
    assert json.loads(capsys.readouterr().out)['inputs_opened'] is False


def test_synthetic_census_cli_report(capsys):
    assert smoke.main(['--report','control-census'])==0
    import json
    out=json.loads(capsys.readouterr().out)
    assert out['schema']=='edgelab_avzvol_control_census_diagnostic_v1'
    assert out['fixture']=='SYNTHETIC_ONLY_NOT_MARKET_THRESHOLDS'
    assert not out['research_authorized'] and not out['economic_outcomes_computed']


def test_documents_preserve_scientific_blockers_and_four_proposals():
    import json
    import re
    doc=ROOT/'docs/research/AVZVOL_CONTROL_CENSUS_DIAGNOSTICS_20261010.md'
    for link in re.findall(r'\]\(([^)]+)\)',doc.read_text()):
        if '://' not in link and not link.startswith('#'):
            assert (doc.parent/link.split('#')[0]).exists()
    s=json.loads((ROOT/'specs/research/avzvol_incremental_design_v1.json').read_text())
    assert s['research_authorized'] is False
    assert s['descriptive_diagnostics_grant_acceptance'] is False
    assert s['own_census_outcome_benchmark_implemented'] is False
    assert (ROOT/s['descriptive_control_census_diagnostics_ref']).exists()
    for key in ('match_policy','support_acceptance_threshold','balance_acceptance_thresholds',
                'formal_family_and_budget','reviewed_input_pins','source_quality_review_refs',
                'control_census_selection_rule'):
        assert s[key] is None
    tracker=json.loads((ROOT/'config/research/avzvol_followup_proposals_v1.json').read_text())
    assert [x['id'] for x in tracker['proposals']]==['P1','P2','P3','P4']
    assert tracker['new_market_trials']==0 and tracker['original_evidence_rewritten'] is False
    assert tracker['economic_execution_authorized'] is False
    assert tracker['proposals'][3]['status']=='DOCUMENTED_ONLY_USER_FORBIDS_ECONOMIC_OUTCOMES'
    assert all(x['market_execution_done'] is False and x['new_inference_done'] is False
               for x in tracker['proposals'])
