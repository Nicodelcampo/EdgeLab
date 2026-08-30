from __future__ import annotations
import importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
from tools.bt2a_nq_gate1_contracts import (CONFIG_ID,INFORMAL_CLASS,load_json,payload_valid,power_missing,validate_macro_policy,validate_runner_contract,validate_selection_provenance)

def test_amendment_is_honest_payload_bound_and_not_retroactive():
 a=load_json(ROOT/'specs/bt2a_nq_informal_all5_provenance_amendment_v1.draft.json')
 assert payload_valid(a); assert a['decision']['selected_config_id']==CONFIG_ID
 assert a['selection_provenance']['formal_score_computed'] is False
 assert a['fixed_config_coordinate_completion']['amendment_is_not_retroactive_authorization'] is True
 assert a['gate1_interpretation']['classification']==INFORMAL_CLASS
 assert a['gate1_interpretation']['confirmatory_eligible'] is False

def test_informal_event_store_amendment_is_frozen_and_still_non_confirmatory():
 # The amendment froze at commit 38e318b (status FROZEN_PROVENANCE_AMENDMENT);
 # this test used to assert the pre-freeze state (require_frozen=True raising
 # "not frozen"), which stopped matching reality once that commit landed and
 # nobody updated the test. Fixed 2026-08-30.
 s=load_json(ROOT/'specs/bt2a_nq_creation_event_store_informal_v1.draft.json')
 p=validate_selection_provenance(s,ROOT,require_frozen=True)
 assert p['confirmatory_eligible'] is False and p['promotion_eligible'] is False
 p=validate_selection_provenance(s,ROOT,require_frozen=False)
 assert p['confirmatory_eligible'] is False and p['promotion_eligible'] is False

def test_formal_event_store_path_remains_supported():
 s=load_json(ROOT/'specs/bt2a_nq_creation_event_store_v1.draft.json')
 p=validate_selection_provenance(s,ROOT,require_frozen=False)
 assert p['mode']=='FORMAL_PREREGISTERED_SELECTION'

def test_macro_policy_is_explicit_null_not_empty_unknown_calendar():
 m=load_json(ROOT/'specs/bt2a_nq_gate1_macro_policy_v1.draft.json')
 assert validate_macro_policy(m,False)==[]
 assert validate_macro_policy(m,True)==['macro_policy.freeze']

def test_power_contract_closes_defensible_inputs_but_remains_fail_closed():
 # K_BT2 density closed 2026-08-30 (tick_25_IMB30_VOL10: 516971/234, commit
 # 95e5866) -- this assertion updated from "in missing" to "not in missing"
 # to match; power.icc renamed to power.icc_retired in the same commit.
 p=load_json(ROOT/'specs/bt2a_nq_gate1_power_design_v1.draft.json')
 missing=power_missing(p,True)
 assert 'power.mde_ticks' not in missing and 'power.paired_session_sd_ticks' not in missing
 assert 'power.icc_retired' not in missing and 'power.arm_density.K_ABS' not in missing
 assert 'power.arm_density.K_BT2' not in missing
 assert 'power.arm_density.N_RAND_capacity_ok' in missing
 assert 'power.freeze' in missing

def test_runner_contract_resolves_choices_but_still_blocks_capability():
 r=load_json(ROOT/'specs/bt2a_nq_gate1_runner_contract_v1.draft.json')
 assert validate_runner_contract(r)==[]
 assert r['implementation_authorized'] is False and r['execution_authorized'] is False
 assert r['contrast_roles']['secondary_contrasts_may_trigger_supported_label'] is False
 assert r['paired_session_variance']['pseudoreplication_forbidden'] is True

def test_event_store_builder_imports_informal_guard():
 src=(ROOT/'tools/build_bt2a_nq_creation_event_store.py').read_text()
 assert 'validate_selection_provenance(spec, ROOT, require_frozen=True)' in src
 assert 'EXPLORATORY_NON_CONFIRMATORY_NON_PROMOTABLE' in src
