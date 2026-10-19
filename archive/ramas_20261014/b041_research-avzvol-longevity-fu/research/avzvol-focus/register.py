"""Freeze a development-only focal search before any new gated outcomes are computed."""
import json,itertools,hashlib
from pathlib import Path
P=Path('/data/analysis/avzvol-focus');gates={
 'speed':['all','return_ge_outgoing','return_lt_outgoing'],
 'efficiency':['all','ge_0.50','ge_0.75'],
 'flow':['all','toward_positive_cov80','toward_ge_0.25_cov80','away_negative_cov80','away_le_neg0.25_cov80'],
 'revisits':['all','ge_5','ge_10','ge_20','ge_50'],
 'volume':['all','inside_fraction_ge_0.25','inside_fraction_ge_0.50'],
 'density':['all','le_0.5','le_1','gt_1'],
 'gaps':['observed','gap_free']}
conditions=[dict(condition_id=i,**dict(zip(gates,vals))) for i,vals in enumerate(itertools.product(*gates.values()))];assert len(conditions)==5400
families=[f'P{pct}_W{w}_R{r}_{look}_20' for pct,w in [(80,5),(90,5),(80,10)] for r,look in itertools.product([8,18],[1000,2000,3000])];ages=[1000,2000,3000];rules=[dict(D=d,q=q,endpoint=0) for d,q in itertools.product([20,40,80],[.25,.5,.75])]+[dict(D=40,q=.5,endpoint=1),dict(D=40,q=.5,endpoint=2)]
manifest=dict(status='FROZEN_FOCAL_EXPLORATORY_SEARCH',registry_version=2,registration_v1_replaced_before_any_new_outcome_evaluation=True,gate_definitions=gates,previous_pilot_inspected=True,source_campaign='corrected longevity campaign version2 / verified lossless repair',source_raw_unchanged=True,baseline_campaign_unchanged=True,contracts=['MNQ_12-26','MNQ_09-25','MNQ_12-25','MNQ_03-26','MNQ_06-26','MNQ_09-26'],families=families,age_landmarks=ages,rules=rules,condition_count=5400,base_cohorts=18*3*11,nominal_event_condition_pairs_per_contract=18*3*11*5400,real_and_control_evaluations_per_contract=2*18*3*11*5400,not_independent_strategies_or_samples=True,deduplication='first chronological signal per family/origin/age/rule/selected-session/6250-record bin BEFORE frozen birth dedup75 and all feature gates; identical paired masks collapsed within cohort',visit_definition='actual prior visits separated by one fully outside closed25-Last-record bar; not OHLC intersections',feature_clock='causal at trigger; no later excursions, final lifetimes or outcome-based threshold fitting',control='same filters on real and translated-geometry250 control; common session/hour3/span40/rem-distance10 strata with min count weights; not randomized',support=dict(real_resolved=100,control_resolved=100,active_fraction=.8,minimum_matched_weight=50,matched_active_fraction=.5),uncertainty='all eligible unique-mask hypotheses jointly: whole-session paired influence scores and max-absolute Rademacher multiplier statistic; exploratory simultaneous approximate bands, dependent on independent-session/symmetry/linearization assumptions; not exact finite-sample or causal significance',multipliers=4096,multiplier_seed=17411,selection='rank for review by support, then simultaneous lower-band difference; never describe rank as validated edge; require other-contract stability, neighborhood robustness and later fresh validation',geometry_height_20_only_in_this_feature_search=True,original_1536_by_1260_matrix_preserved=True,not_tested_here='new distances/retracement levels, new dense age landmarks, other heights or cross-session carry require new tick replay; this pass reuses measured signals only',holdout_opened=False,source_certified=False,pnl_computed=False)
for n,data in [('conditions.json',conditions),('manifest.json',manifest)]:
 path=P/n
 if path.exists():assert json.load(open(path))==data,'FOCAL_MANIFEST_CHANGED'
 else:path.write_text(json.dumps(data,indent=2)+'\n')
print('REGISTERED',manifest['nominal_event_condition_pairs_per_contract'],manifest['real_and_control_evaluations_per_contract'])
