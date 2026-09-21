import pytest
from edgelab.research.trend_ablation import *
from edgelab.research.trend_context import TrendParameters
def test_default_budget_and_placebo():
 m=build_manifest(); assert m.policy_count==len(DEFAULT_HYPOTHESES)*len(ContextCell)==48; assert len({c.cell_id for c in m.cells})==48; assert sum(c.placebo for c in m.cells)==8
def test_deterministic_and_sealed():
 a,b=build_manifest(),build_manifest(); assert a==b and len(a.digest)==64; assert a.outcome_access=="FORBIDDEN_UNTIL_EXPLICIT_AUTHORIZATION" and a.holdout_access=="SEALED"
def test_neighbourhood_is_charged():
 ps=(TrendParameters(),TrendParameters(ema_fast=8,ema_slow=21,sma_fast=20,sma_slow=50,slope_lookback=3)); assert build_manifest(parameter_sets=ps).policy_count==96
def test_duplicates_and_shuffle_fail():
 with pytest.raises(ValueError,match="duplicate"): build_manifest(hypotheses=(DEFAULT_HYPOTHESES[0],)*2)
 with pytest.raises(ValueError,match="duplicate"): build_manifest(parameter_sets=(TrendParameters(),TrendParameters()))
 with pytest.raises(ValueError,match="shuffle"): build_manifest(shuffle_replicates=0)
def test_no_outcomes_in_schema():
 f={"pnl","return","sharpe","win_rate","expectancy"}; m=build_manifest(); assert not f.intersection(m.__dataclass_fields__); assert all(not f.intersection(c.__dataclass_fields__) for c in m.cells)
