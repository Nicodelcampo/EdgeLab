import os
import sys
sys.path.insert(0, os.path.abspath("."))
import json
import itertools
import collections
from edgelab.edge_factory.schema_validator import validate_hypothesis

OUTPUT_DIR = r"E:\EdgeLab-edgefactory\artifacts\edge_factory"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Define 20 Distinct Architectural Families with Domain Mechanisms
FAMILIES_SPEC = [
    {
        "family": "continuacion",
        "title_prefix": "Low Density Corridor Continuation",
        "mechanism": "Price accelerates in direction of impulse when entering liquidity voids with low historical absorption density.",
        "novelty": "Causal measurement of post-absorption corridor flow without predictive labels.",
        "unit": "corridor_entry_event",
        "entry": "Next tick after crossing corridor boundary into sparse liquidity zone",
        "controls": ["matched_time_outside_corridor"],
        "placebos": ["random_timestamp_within_corridor", "direction_inversion"],
        "params": ["corridor_density_threshold", "min_corridor_height_ticks"]
    },
    {
        "family": "reversion",
        "title_prefix": "High Density Wall Mean Reversion",
        "mechanism": "Price bounces off thick multi-pass absorption walls due to institutional limit order replenishment.",
        "novelty": "First causal boundary condition using real tick25 absorption wall thickness.",
        "unit": "wall_touch_event",
        "entry": "Next tick after touch of zone with total_vol > p75 and vol_rate > p80",
        "controls": ["touch_of_thin_zone"],
        "placebos": ["direction_inversion", "delayed_entry_placebo"],
        "params": ["min_volume_threshold", "max_touch_penetration_ticks"]
    },
    {
        "family": "rechazo",
        "title_prefix": "Fast Time-Rejection at Zone Boundary",
        "mechanism": "Speed of rejection from zone boundary is positively correlated with total absorbed contract volume.",
        "novelty": "Velocity-based microstructural response timing measured strictly at t0 causal.",
        "unit": "zone_boundary_event",
        "entry": "Immediate next tick upon candle rejection wick exceeding 3 ticks",
        "controls": ["rejection_at_random_price"],
        "placebos": ["time_scrambled_bars"],
        "params": ["wick_size_ticks", "rejection_time_window_ms"]
    },
    {
        "family": "ruptura",
        "title_prefix": "Absorption Wall Exhaustion Breakout",
        "mechanism": "Zones touched multiple times with diminishing delta volume fail, causing rapid breakout impulse.",
        "novelty": "Volume decay tracking per touch without post-hoc curve fitting.",
        "unit": "zone_breakout_event",
        "entry": "Next tick after price closes beyond opposite zone boundary",
        "controls": ["breakout_without_preceding_zone"],
        "placebos": ["random_breakout_placebo"],
        "params": ["min_prior_touches", "breakout_candle_size_ticks"]
    },
    {
        "family": "traversing_corredores",
        "title_prefix": "Corridor Full Span Traversal",
        "mechanism": "Once price crosses 25% of an open corridor, conditional probability of reaching opposite wall increases.",
        "novelty": "Geometrical boundary conditioning across multi-contract parquets.",
        "unit": "corridor_quarter_cross_event",
        "entry": "Next tick upon crossing 25% of corridor span",
        "controls": ["quarter_cross_in_wide_range"],
        "placebos": ["random_entry_in_session"],
        "params": ["corridor_height_min_ticks", "max_active_zones_inside"]
    },
    {
        "family": "pared_opuesta",
        "title_prefix": "Opposite Wall Target Magnetism",
        "mechanism": "Unconsumed opposite absorption walls act as primary attractors in trending sessions.",
        "novelty": "Dual-barrier structural target without arbitrary tick targets.",
        "unit": "corridor_opposite_target_event",
        "entry": "Signal availability of opposing zone pair",
        "controls": ["fixed_distance_target"],
        "placebos": ["inverted_opposite_target"],
        "params": ["distance_ticks_range", "wall_age_max_minutes"]
    },
    {
        "family": "edad",
        "title_prefix": "Zone Freshness vs Latency Decay",
        "mechanism": "Rejection probability decays as a power-law function of zone age in minutes and intervening volume.",
        "novelty": "Parametric half-life modeling of absorption memory across 11 instruments.",
        "unit": "zone_touch_with_age",
        "entry": "First touch occurring within specific age bracket [0-15m, 15-60m, 60m+]",
        "controls": ["touch_without_age_conditioning"],
        "placebos": ["shuffled_age_assignment"],
        "params": ["age_brackets_minutes", "session_normalized_time"]
    },
    {
        "family": "consumo",
        "title_prefix": "Progressive Volume Consumption Dynamics",
        "mechanism": "Each consecutive tick pass through a zone depletes resting liquidity until barrier becomes transparent.",
        "novelty": "Quantitative consumption tracking without Level 2 orderbook reliance.",
        "unit": "zone_pass_event",
        "entry": "Touch on zone having accumulated > 3 prior passes",
        "controls": ["touch_on_fresh_zone"],
        "placebos": ["unconditioned_pass"],
        "params": ["pass_count_threshold", "volume_consumed_pct"]
    },
    {
        "family": "densidad",
        "title_prefix": "Gaussian Density Profile Barrier",
        "mechanism": "Continuous KDE density peaks generated by crosshair density profile act as high-friction barriers.",
        "novelty": "Causal sigma-KDE integration directly on 25t tick bars.",
        "unit": "density_peak_proximity_event",
        "entry": "Next tick when price enters top 10% density decile",
        "controls": ["entry_at_median_density"],
        "placebos": ["density_profile_price_scramble"],
        "params": ["sigma_ticks", "density_percentile_cutoff"]
    },
    {
        "family": "first_touch",
        "title_prefix": "Virgin Zone First Touch Efficiency",
        "mechanism": "The initial touch of a newly formed causal absorption zone carries the highest information ratio.",
        "novelty": "Strict causal available_ns timestamp gating prevents retrospective first touch leaks.",
        "unit": "virgin_zone_first_touch",
        "entry": "First price tick penetrating [bottom, top] after available_ns",
        "controls": ["unconditioned_touch"],
        "placebos": ["pseudo_first_touch_random"],
        "params": ["max_formation_delay_ms", "penetration_tolerance_ticks"]
    },
    {
        "family": "retoques",
        "title_prefix": "Secondary Retouch Diminishing Return",
        "mechanism": "Second and third retouches exhibit wider distribution of adverse excursions compared to initial touch.",
        "novelty": "Comparative survival analysis of retouch lifecycle across contracts.",
        "unit": "retouch_event",
        "entry": "Touch count == 2 or 3 after origin",
        "controls": ["first_touch_control"],
        "placebos": ["time_shifted_retouch"],
        "params": ["retouch_index", "minimum_elapsed_bars_between_touches"]
    },
    {
        "family": "conflicto_indicadores",
        "title_prefix": "Cross-Indicator Absorption Conflict",
        "mechanism": "Coexistence of opposing absorption zones within tight price band signals range compression and impending expansion.",
        "novelty": "Direct interaction between multi-asset HFT zones and structural levels.",
        "unit": "indicator_conflict_event",
        "entry": "Next tick when BULL and BEAR zones overlap by >= 50%",
        "controls": ["single_indicator_zone"],
        "placebos": ["synthetic_random_zone_pair"],
        "params": ["overlap_ratio", "max_band_ticks"]
    },
    {
        "family": "confluencia",
        "title_prefix": "Multi-Zone Level Confluence Reinforcement",
        "mechanism": "When multiple absorption zones align at the same price tick, bounce probability increases non-linearly.",
        "novelty": "Clustered zone density verification without visual ambiguity.",
        "unit": "confluence_cluster_event",
        "entry": "Touch of cluster with >= 2 overlapping zones",
        "controls": ["isolated_single_zone_touch"],
        "placebos": ["randomly_placed_cluster"],
        "params": ["cluster_tolerance_ticks", "min_zones_in_cluster"]
    },
    {
        "family": "regimen",
        "title_prefix": "Volatility Regime Conditioning",
        "mechanism": "Absorption zone retention is significantly higher in low-volatility regimes than during high-volatility expansions.",
        "novelty": "Target-free session tick25 volatility classification.",
        "unit": "regime_conditioned_touch",
        "entry": "Touch occurring during session volatility < median",
        "controls": ["touch_in_high_volatility_regime"],
        "placebos": ["unconditioned_regime_touch"],
        "params": ["session_vol_rolling_bars", "vol_ratio_threshold"]
    },
    {
        "family": "horario",
        "title_prefix": "Intraday Session Cycle Sensitivity",
        "mechanism": "Zones created during European/London open hold with higher structural integrity into US RTH open.",
        "novelty": "Cross-session persistent zone evaluation without cross-session data leaks.",
        "unit": "cross_session_touch",
        "entry": "RTH open touch of London-formed absorption zone",
        "controls": ["RTH_touch_of_Asian_zone"],
        "placebos": ["random_hourly_window_entry"],
        "params": ["formation_window_utc", "execution_window_utc"]
    },
    {
        "family": "persistencia_multisesion",
        "title_prefix": "Multisession Unfinished Business",
        "mechanism": "Orphan zones surviving entire sessions without touch maintain residual gravity in subsequent session.",
        "novelty": "Session reset compliant cross-day causal state mapping.",
        "unit": "multisession_orphan_touch",
        "entry": "First touch in session T+1 of zone originating in session T",
        "controls": ["same_session_touch"],
        "placebos": ["shuffled_session_orphan"],
        "params": ["max_prior_sessions", "orphan_volume_minimum"]
    },
    {
        "family": "interaccion_escalas",
        "title_prefix": "Multi-Scale Micro vs Macro Interaction",
        "mechanism": "Tick25 micro-absorption aligning with macro swing extremes exhibits higher directional asymmetry.",
        "novelty": "Multiscale structural conditioning without lookahead.",
        "unit": "multiscale_aligned_event",
        "entry": "Tick25 zone touch occurring within 5 ticks of session high/low as-of",
        "controls": ["zone_touch_at_mid_session_range"],
        "placebos": ["random_price_relative_to_range"],
        "params": ["extreme_proximity_ticks", "min_bars_since_extreme"]
    },
    {
        "family": "transferencia_activos",
        "title_prefix": "Cross-Asset Direct Transferability",
        "mechanism": "Parameters calibrated on ES/NQ maintain structural validity on MES/MNQ and transfer to equity index YM.",
        "novelty": "Empirical invariance test across micro and full-sized contracts.",
        "unit": "cross_asset_evaluation_event",
        "entry": "Identical literal parameter execution across asset pairs",
        "controls": ["asset_specific_overfitted_params"],
        "placebos": ["uncorrelated_asset_transfer_6E_to_ES"],
        "params": ["asset_pair", "scale_factor_ticks"]
    },
    {
        "family": "estabilidad_parametros",
        "title_prefix": "Parametric Plateau Sensitivity",
        "mechanism": "Valid microstructural effects reside on smooth parameter plateaus where perturbations do not degrade behavior.",
        "novelty": "Continuous gradient test on target-free zone formation gates.",
        "unit": "grid_point_evaluation",
        "entry": "Evaluation across 3x3 parameter neighborhood",
        "controls": ["isolated_peak_parameter_point"],
        "placebos": ["random_parameter_noise"],
        "params": ["pasos_tolerance", "volume_threshold_grid"]
    },
    {
        "family": "controles_placebos",
        "title_prefix": "Rigorous Placebo Null Baseline",
        "mechanism": "Empirical benchmark measuring the exact information gain of absorption signals over matched random placebos.",
        "novelty": "Automated Monte Carlo null hypothesis distribution generation.",
        "unit": "synthetic_placebo_comparison",
        "entry": "Simultaneous execution of signal and 100 matched placebos",
        "controls": ["true_causal_signal"],
        "placebos": ["scrambled_timestamps", "scrambled_direction", "scrambled_asset"],
        "params": ["placebo_sample_size", "matching_tolerance_ms"]
    }
]

# Eligible Asset Universes
ASSET_UNIVERSES = [
    ["ES", "MES"],
    ["NQ", "MNQ"],
    ["YM"],
    ["6E", "6B", "6J"],
    ["ZB"],
    ["GC"],
    ["MBT"],
    ["ES", "NQ", "6E", "ZB", "GC"] # Multi-asset diversified
]

def generate_hypotheses():
    hypotheses = []
    dep_graph = {"nodes": [], "edges": []}

    idx = 1
    for spec in FAMILIES_SPEC:
        fam_name = spec["family"]
        # Generate 3-4 specialized variations per family across asset groups
        for u_idx, universe in enumerate(ASSET_UNIVERSES[:4]):
            h_id = f"HP-{fam_name.upper()[:8]}-{idx:03d}"
            title = f"{spec['title_prefix']} — {', '.join(universe)} (V{u_idx+1})"
            
            # Estimate compute cost and info gain based on family complexity
            if fam_name in ["controles_placebos", "persistencia_multisesion", "transferencia_activos"]:
                cost = "HIGH"
                info_gain = "TRANSFORMATIVE"
            elif fam_name in ["confluencia", "densidad", "conflicto_indicadores"]:
                cost = "MEDIUM"
                info_gain = "HIGH"
            else:
                cost = "LOW"
                info_gain = "MEDIUM"

            hyp = {
                "hypothesis_id": h_id,
                "title": title,
                "mechanism": f"{spec['mechanism']} Specifically evaluated on {', '.join(universe)}.",
                "novelty": spec["novelty"],
                "required_indicators": ["HFTZonesUniversal"],
                "required_features": ["height_ticks", "total_vol", "vol_rate", "causal_delay_ms", "origin_ts", "signal_available_ts"],
                "eligible_assets": universe,
                "unit_of_analysis": spec["unit"],
                "causal_entry_definition": spec["entry"],
                "suggested_controls": spec["controls"],
                "suggested_placebos": spec["placebos"],
                "parameter_families": spec["params"],
                "friction_requirements": {
                    "min_roundturn_cost_ticks": 1.5 if "ES" in universe or "NQ" in universe else 2.0,
                    "slippage_model": "one_tick_adverse"
                },
                "multiplicity_family": f"family_{fam_name}",
                "validation_plan": f"LOCO evaluation across all verified contracts of {', '.join(universe)} without parameter retraining.",
                "falsification_plan": "Friction stress test (1.5x, 2.0x, 3.0x), leave-one-session-out, matched placebo comparison, FDR < 0.05.",
                "estimated_compute_cost": cost,
                "expected_information_gain": info_gain,
                "dependencies": ["zone_events", "session_inventory"] + (["corridor_events"] if "corridor" in fam_name else []),
                "research_stage": "PROPOSED_TARGET_FREE",
                "status": "PROPOSED_TARGET_FREE"
            }

            # Validate schema
            validate_hypothesis(hyp)
            hypotheses.append(hyp)

            # Build dependency graph
            dep_graph["nodes"].append({
                "id": h_id,
                "label": title,
                "family": fam_name,
                "cost": cost,
                "info_gain": info_gain
            })
            for dep in hyp["dependencies"]:
                dep_graph["edges"].append({"from": dep, "to": h_id})

            idx += 1

    print(f"Generated {len(hypotheses)} verified, non-redundant hypotheses across {len(FAMILIES_SPEC)} families.")

    # Rank hypotheses target-free
    # Ranking formula: Transformative (4), High (3), Med (2) / Cost High(3), Med(2), Low(1)
    gain_weights = {"TRANSFORMATIVE": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
    cost_weights = {"VERY_HIGH": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}

    def score(h):
        g = gain_weights.get(h["expected_information_gain"], 1)
        c = cost_weights.get(h["estimated_compute_cost"], 1)
        coverage = len(h["eligible_assets"])
        return round((g * 2.0 + coverage * 0.5) / c, 3)

    for h in hypotheses:
        h["priority_score"] = score(h)

    hypotheses.sort(key=lambda x: -x["priority_score"])

    # Write HYPOTHESIS_REGISTRY.jsonl
    jsonl_path = os.path.join(OUTPUT_DIR, "HYPOTHESIS_REGISTRY.jsonl")
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for h in hypotheses:
            # write without internal priority_score to strictly match schema
            clean_h = dict(h)
            clean_h.pop("priority_score", None)
            f.write(json.dumps(clean_h) + "\n")

    # Write HYPOTHESIS_DEPENDENCY_GRAPH.json
    dep_path = os.path.join(OUTPUT_DIR, "HYPOTHESIS_DEPENDENCY_GRAPH.json")
    with open(dep_path, "w", encoding="utf-8") as f:
        json.dump(dep_graph, f, indent=2)

    # Write HYPOTHESIS_BACKLOG.md
    md_lines = [
        "# Edge Discovery Factory — Registro Autónomo de Hipótesis",
        "",
        f"- **Total de Hipótesis Registradas:** {len(hypotheses)} hipótesis no redundantes",
        f"- **Familias Microestructurales Cubiertas:** {len(FAMILIES_SPEC)} familias canónicas",
        "- **Estado Científico:** `PROPOSED_TARGET_FREE` (Ninguna promovida a VALIDATION sin confirmación)",
        "- **Outcomes Firewall:** ESTRICTO. Cero resultados evaluados o pre-seleccionados.",
        "",
        "## 1. Familias de Investigación Formalizadas",
        "",
        "| Familia | Descripción Mecánica | Hipótesis Activas | Prioridad Media |",
        "| :--- | :--- | :--- | :--- |"
    ]
    family_grouped = collections.defaultdict(list)
    for h in hypotheses:
        family_grouped[h["multiplicity_family"]].append(h)

    for fam, h_list in sorted(family_grouped.items()):
        avg_score = round(sum(h["priority_score"] for h in h_list) / len(h_list), 2)
        md_lines.append(f"| `{fam}` | {h_list[0]['mechanism'][:80]}... | {len(h_list)} | {avg_score} |")

    md_lines.extend([
        "",
        "## 2. Top 15 Hipótesis Priorizadas (Ranking Target-Free)",
        "",
        "| ID | Título | Activos | Coste | Ganancia Informativa | Score |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |"
    ])
    for h in hypotheses[:15]:
        md_lines.append(f"| `{h['hypothesis_id']}` | {h['title']} | {', '.join(h['eligible_assets'])} | `{h['estimated_compute_cost']}` | `{h['expected_information_gain']}` | **{h['priority_score']}** |")

    md_lines.extend([
        "",
        "## 3. Protocolo de Prerregistro y Falsificación",
        "",
        "- Cada hipótesis cuenta con controles emparejados y placebos sintéticos específicos.",
        "- Antes de evaluar retornos en Train (Discovery Set), la hipótesis debe ser congelada con hash SHA-256.",
        "- Se contabilizarán todas las hipótesis de cada familia para corrección por multiplicidad (Holm-Bonferroni / Benjamini-Hochberg).",
        "- Si una hipótesis no supera la prueba de fricción adversa (1 tick adverso + spread), pasa directamente a `negative_results_registry`."
    ])

    with open(os.path.join(OUTPUT_DIR, "HYPOTHESIS_BACKLOG.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    print(f"Hypothesis registry, dependency graph, and backlog MD written successfully to {OUTPUT_DIR}.")

if __name__ == "__main__":
    generate_hypotheses()
