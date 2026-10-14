"""Pinned historical pure functions, invented zones ONLY; no market or outcomes."""
import ast
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/'config/research/avzvol_zone_causal_review_v1.json'

def functions():
    evidence=json.loads(EVIDENCE.read_text())
    raw=(ROOT/evidence['fixture_path']).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==evidence['fixture_sha256']
    tree=ast.parse(raw.decode())
    assert all(isinstance(n,ast.FunctionDef) for n in tree.body)
    assert {n.name for n in tree.body}=={'_racimo','racimos_de'}
    assert not any(isinstance(n,(ast.Import,ast.ImportFrom)) for n in ast.walk(tree))
    scope={};exec(compile(tree,'pinned-pure-legacy-fixture','exec'),scope)
    return scope

def zone(bar,lo,hi,session='SYNTHETIC-A'):
    return dict(bar=bar,low_tick=lo,high_tick=hi,racimo_bar=-1,rac=None,session=session)

P=dict(racimo_min=2,racimo_bars=100,racimo_altura_ticks=10)

def test_formation_is_later_than_first_zone_and_membership_not_backdated():
    f=functions()['_racimo'];zs=[];cs=[];a=zone(10,100,101)
    f(a,zs,cs,10,P);zs.append(a)
    assert a['racimo_bar']==-1 and cs==[]
    b=zone(20,101,102);f(b,zs,cs,20,P)
    assert cs[0]['start0']==10 and cs[0]['bar']==20
    assert a['racimo_bar']==20 and b['racimo_bar']==20
    # At bar 10, the future membership was not yet observable.
    assert a['racimo_bar']>a['bar']

def test_later_zone_expands_mutable_extent_but_not_formation_snapshot():
    f=functions()['_racimo'];zs=[];cs=[]
    for bar,lo,hi in [(10,100,101),(20,101,102)]:
        z=zone(bar,lo,hi);f(z,zs,cs,bar,P);zs.append(z)
    before={k:cs[0][k] for k in ('bar','start0','low0','high0')}
    z=zone(30,102,104);f(z,zs,cs,30,P)
    assert len(cs)==1 and cs[0]['high']==104 and cs[0]['high0']==102
    assert {k:cs[0][k] for k in before}==before

def test_racimos_de_can_combine_distinct_declared_sessions():
    zs=[zone(10,100,101,'SYNTHETIC-A'),zone(20,101,102,'SYNTHETIC-B')]
    cs=functions()['racimos_de'](zs,2,100,10)
    assert len(cs)==1 and cs[0]['start0']==10 and cs[0]['bar']==20
    # Characterizes omission, NOT empirical frequency and NOT a correction.

def test_bar_distance_still_bounds_candidates():
    zs=[zone(10,100,101),zone(111,101,102)]
    assert functions()['racimos_de'](zs,2,100,10)==[]

def test_no_cluster_yet_does_not_mean_no_zones():
    assert functions()['racimos_de']([zone(10,100,101)],2,100,10)==[]
    # Distinct predicates require an approved rule: no zone != no formed racimo.

def test_evidence_never_promotes_characterization_to_market_authority():
    j=json.loads(EVIDENCE.read_text())
    lineage=json.loads((ROOT/'config/research/avzvol_lineage_candidates_20261010.json').read_text())
    assert j['recovered_notebook_sha256']==lineage['notebooks'][0]['source_sha256']
    assert all(x['AST_equal_to_pinned_Git'] for x in j['equivalence'])
    for k in ('method_changed','production_detector_modified','historical_runtime_consumption_verified',
              'historical_bias_adjudicated','observed_market_contamination_measured','source_quality_certified',
              'zone_free_census_verified','research_authorized','outcomes_read',
              'economic_outcomes_computed','original_outputs_modified'):
        assert j[k] is False
    assert j['new_market_trials']==0


def test_causal_decisions_stay_unapproved_and_document_links_exist():
    import re
    s=json.loads((ROOT/'specs/research/avzvol_incremental_design_v1.json').read_text())
    assert s['negative_classification_asof_rule'] is None
    assert s['cross_session_cluster_policy'] is None
    assert s['control_census_selection_rule'] is None
    assert s['research_authorized'] is False and s['pnl_allowed'] is False
    request=s['conditional_non_economic_execution_request']
    assert request['requested'] is True
    assert request['clears_runtime_gates'] is False
    assert request['authorizes_holdout_access'] is False
    assert request['authorizes_economic_outcomes'] is False
    assert (ROOT/s['zone_causal_review_ref']).exists()
    doc=ROOT/'docs/research/AVZVOL_ZONE_CAUSAL_REVIEW_20261010.md'
    for link in re.findall(r'\]\(([^)]+)\)',doc.read_text()):
        if '://' not in link and not link.startswith('#'):
            assert (doc.parent/link.split('#')[0]).exists()
