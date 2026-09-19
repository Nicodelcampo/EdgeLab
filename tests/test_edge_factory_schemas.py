import unittest
import jsonschema
from edgelab.edge_factory.schema_validator import (
    validate_zone_event,
    validate_zone_event_exploratory,
    validate_corridor_event,
    validate_hypothesis,
    validate_experiment,
    validate_negative_result,
    validate_analysis_dependencies,
)

class TestEdgeFactorySchemas(unittest.TestCase):

    def setUp(self):
        self.valid_causal_zone = {
            "instrument": "ES",
            "contract": "ES 12-25",
            "session_id": "ES_20251117_RTH",
            "indicator": "HFTZonesUniversal",
            "indicator_version": "V2_UNIVERSAL",
            "config_id": "cfg_hft_literal_v2",
            "zone_id": "ES:ES 12-25:20251117:1",
            "origin_ts": 1763388000000000000,
            "signal_available_ts": 1763388002000000000,
            "executable_fill_ts": 1763388002500000000,
            "bar_key": "tick_25",
            "side": "BULL",
            "bottom": 6010.25,
            "top": 6011.50,
            "state": "ACTIVE",
            "termination_reason": "MAX_PAUSE",
            "availability_quality": "EXPLICIT_EXACT",
            "source_sha256": "a" * 64,
            "engine_version": "1.0.0",
            "height_ticks": 5.0,
            "total_vol": 250.0,
            "vol_rate": 12.5,
            "pasos": 25
        }

    def test_valid_causal_zone_passes(self):
        validate_zone_event(self.valid_causal_zone)

    def test_causal_zone_rejects_origin_fallback(self):
        bad_zone = dict(self.valid_causal_zone)
        bad_zone["availability_quality"] = "ORIGIN_FALLBACK_UNVERIFIED"
        with self.assertRaises(ValueError):
            validate_zone_event(bad_zone)

    def test_causal_zone_missing_required_field_fails(self):
        bad_zone = dict(self.valid_causal_zone)
        del bad_zone["executable_fill_ts"]
        with self.assertRaises(jsonschema.ValidationError):
            validate_zone_event(bad_zone)

    def test_exploratory_zone_accepts_fallback(self):
        exp_zone = {
            "instrument": "ES",
            "contract": "ES 12-25",
            "session_id": "ES_20251117_RTH",
            "indicator": "HFTZonesUniversal",
            "indicator_version": "V2_UNIVERSAL",
            "config_id": "cfg_hft_literal_v2",
            "zone_id": "ES:ES 12-25:20251117:exp1",
            "origin_ts": 1763388000000000000,
            "signal_available_ts": None,
            "executable_fill_ts": None,
            "bar_key": "tick_25",
            "side": "BULL",
            "bottom": 6010.25,
            "top": 6011.50,
            "availability_quality": "ORIGIN_FALLBACK_UNVERIFIED",
            "source_sha256": "b" * 64,
            "engine_version": "1.0.0"
        }
        validate_zone_event_exploratory(exp_zone)

    def test_corridor_event_schema(self):
        corr = {
            "instrument": "NQ",
            "contract": "NQ 12-25",
            "session_id": "NQ_20251117_RTH",
            "corridor_id": "corr_1234",
            "active_ts": 1763388100000000000,
            "bar_key": "tick_25",
            "floor_price": 20500.0,
            "ceiling_price": 20550.0,
            "height_ticks": 200.0,
            "density_score": 0.45,
            "contributing_zones_count": 4,
            "status": "OPEN",
            "source_sha256": "c" * 64
        }
        validate_corridor_event(corr)

    def test_hypothesis_schema(self):
        hyp = {
            "hypothesis_id": "HP-BT2A-CORR-01",
            "title": "Low Density Corridor Fast Traversal",
            "mechanism": "Price moves with higher velocity through corridors lacking recent absorption walls.",
            "novelty": "First causal combination of absorption density profiles and tick25 corridor traversal.",
            "required_indicators": ["HFTZonesUniversal"],
            "required_features": ["corridor_density_score", "corridor_height_ticks"],
            "eligible_assets": ["ES", "NQ", "6E"],
            "unit_of_analysis": "corridor_entry_event",
            "causal_entry_definition": "Next tick after price crosses floor/ceiling into low density corridor",
            "suggested_controls": ["matched_time_without_corridor"],
            "suggested_placebos": ["random_timestamp_in_corridor", "reversed_direction"],
            "parameter_families": ["density_threshold", "min_corridor_ticks"],
            "friction_requirements": {
                "min_roundturn_cost_ticks": 1.5,
                "slippage_model": "one_tick_adverse"
            },
            "multiplicity_family": "corridor_traversal_v1",
            "validation_plan": "LOCO across all 55 verified contracts",
            "falsification_plan": "Friction stress 2x and 3x, leave-one-contract-out, permutation test",
            "estimated_compute_cost": "LOW",
            "expected_information_gain": "HIGH",
            "dependencies": ["corridor_events", "zone_events"],
            "research_stage": "PROPOSED_TARGET_FREE",
            "status": "PROPOSED_TARGET_FREE"
        }
        validate_hypothesis(hyp)

    def test_experiment_schema(self):
        exp = {
            "experiment_id": "EXP-20260919-001",
            "hypothesis_id": "HP-BT2A-CORR-01",
            "research_stage": "TARGET_FREE_CENSUS",
            "code_commit": "2658a16",
            "input_hashes": {"bundles_manifest_sha": "d" * 64},
            "indicator_configs": [{"indicator": "HFTZonesUniversal", "bar_key": "tick_25"}],
            "corridor_config": {"hmin_ticks": 16, "density_sigma": 2},
            "assets": ["ES", "NQ"],
            "contracts": ["ES 12-25", "NQ 12-25"],
            "sessions": ["20251117"],
            "control_definition": {"type": "matched_volatility"},
            "outcome_definition": None,
            "friction_model": {"cost_ticks": 1.5},
            "multiplicity_family": "corridor_traversal_v1",
            "result": "CENSUS_COMPLETED",
            "uncertainty": "NONE_TARGET_FREE",
            "failure_reason": None,
            "artifact_hashes": {"census_sha": "e" * 64}
        }
        validate_experiment(exp)

    def test_negative_result_schema(self):
        neg = {
            "falsification_id": "FALS-20260919-001",
            "hypothesis_id": "HP-BT2A-CORR-01",
            "experiment_id": "EXP-20260919-001",
            "stage_at_failure": "VALIDATION",
            "failure_mode": "FRICTION_COLLAPSE",
            "null_distribution_summary": {"p_value_fdr": 0.35, "mean_null_pnl": 0.0},
            "friction_break_even_multiple": 0.45,
            "loocv_survival_rate": 0.20,
            "falsification_commit": "2658a16",
            "timestamp_utc": "2026-09-19T06:00:00Z"
        }
        validate_negative_result(neg)

    def test_analysis_dependencies_schema(self):
        dep = {
            "target_artifact": "artifacts/edge_factory/TARGET_FREE_CENSUS.json",
            "upstream_dependencies": ["artifacts/edge_factory/zone_events/"],
            "required_gates": ["PASS_CAUSAL_AVAILABLE_TS", "HOLDOUT_FIREWALL_PASS"],
            "recompute_policy": "ON_SOURCE_CHANGE",
            "estimated_duration_sec": 45.0
        }
        validate_analysis_dependencies(dep)

if __name__ == "__main__":
    unittest.main()
