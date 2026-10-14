"""Explicit feature serialization; no positional CSV-header slicing."""
import math
FEATURE_NAMES=('visits1','visits5','visits_clock10s','volume_inside_fraction','inside_seconds_observed','recency_seconds','prior_gap_count','speed_ratio','return_seconds','return_bars_per_tick','return_efficiency','return_imbalance_proxy_toward','proxy_coverage','remaining_ticks','age_bars','age_seconds')
def attach_features(row, values):
 assert len(values)==len(FEATURE_NAMES)
 assert not set(FEATURE_NAMES)&set(row), 'FEATURE_METADATA_COLLISION'
 row.update(zip(FEATURE_NAMES, values))
 validate(row)
 return row
def validate(r):
 def number(k):return float(r[k])
 assert number('hour').is_integer() and 0<=number('hour')<=23
 for k in ['visits1','visits5','visits_clock10s','prior_gap_count','remaining_ticks','age_bars']:
  v=number(k);assert math.isfinite(v) and v>=0 and v.is_integer(),(k,v)
 assert number('visits5')<=number('visits1')
 for k in ['volume_inside_fraction','proxy_coverage','return_efficiency']:
  v=number(k);assert math.isnan(v) or 0<=v<=1+1e-9,(k,v)
 v=number('return_imbalance_proxy_toward');assert math.isnan(v) or -1-1e-9<=v<=1+1e-9
 for k in ['inside_seconds_observed','recency_seconds','speed_ratio','return_seconds','return_bars_per_tick','age_seconds']:
  v=number(k);assert math.isnan(v) or v>=0,(k,v)
