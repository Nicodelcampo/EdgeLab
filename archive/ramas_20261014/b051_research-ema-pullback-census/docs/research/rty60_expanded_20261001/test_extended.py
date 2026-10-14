from pathlib import Path
import json,sys,math
sys.path.insert(0,str(Path(__file__).parent/'repo'))
import pytest
import past_price_producer as p
from edgelab.research.holdout_guard import check_holdout,HoldoutViolation
from edgelab.stats import cluster_estimand as ce
from economic import costs

def test_catalog175_scope():
 m=json.load(open('manifest.json'));ss=[s for s in p.CATALOGS['RTY']['sessions'] if s['trade_date']<'20260701'];assert sorted(s['trade_date'] for s in ss)==m['days'];assert len(ss)==175 and max(s['trade_date'] for s in ss)=='20260630'
def test_partition_crossfoot():
 m=json.load(open('manifest.json'));assert len(set(m['days'])-set(m['original54']))==121 and len(m['original54'])==54
 assert sum(m['partitions']['quarter_descriptives'].values())==175

def test_unchanged_producer_replay_detector():
 m=json.load(open('manifest.json'));assert p.sha('economic.py')=='4f46ecbe6426fb027d6db8bdfc5f635f28a5f362c19cff6f56a0456e02f9cbb8';assert p.sha('census.py')=='ccd2b9ba7f902cb5981936cd740e05bb25cfccbd8702ccb22d358c14aa142d7b';assert p.sha('past_price_producer.py')=='0ecfb04cb9cf60a02704d35e08aa0277e12e8e41c8147cd8aba7e14960a36783'
def test_holdout_boundary(tmp_path):
 check_holdout('2025-10-01','2026-06-30T23:59:59Z',purpose='development',caller='TEST',log_path=str(tmp_path/'guard.log'))
 with pytest.raises(HoldoutViolation):check_holdout('2026-06-30','2026-07-01',purpose='development',caller='TEST',log_path=str(tmp_path/'guard.log'))
def test_costs_still_same_RTY():
 m=json.load(open('manifest.json'));assert abs(costs(m,'RTY',1)-2.9)<1e-9 and abs(costs(m,'RTY',2)-4.9)<1e-9

def test_native_studentized_component_not_overallG2():
 days=['S%03d'%i for i in range(175)];cl=ce.aggregate_sessions(days,{d:[1+math.sin(i)*.2] for i,d in enumerate(days)});r=ce.studentized_stationary_interval(cl,n_replicates=200,seed=2);assert r.lower>0 and r.method=='stationary_bootstrap_t'
 with pytest.raises(ce.ClusterEstimandError):ce.studentized_stationary_interval(cl[:54],n_replicates=200,seed=2)
