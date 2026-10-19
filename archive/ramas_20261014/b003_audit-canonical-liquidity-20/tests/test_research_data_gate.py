import importlib.util
from pathlib import Path
import unittest
p=Path(__file__).resolve().parents[1]/'edgelab/data/research_data_gate.py'
spec=importlib.util.spec_from_file_location('research_data_gate',p)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
DataEligibilityError=m.DataEligibilityError
REQUIRED_CHECKS=m.REQUIRED_CHECKS
seal=m.seal
require_research_eligibility=m.require_research_eligibility

class GateTests(unittest.TestCase):
    def setUp(self):
        self.c={'status':'SANITIZED_VERIFIED','checks':dict.fromkeys(REQUIRED_CHECKS,'PASS'),
            'source_identity':{'dataset':'SYNTHETIC_TEST_ONLY','version':1},
            'holdout_first_trade_date':20260401,'allowed_trade_dates':[20260330,20260331],
            'sessions':{'MNQ|MNQ_06-26|20260330':{'status':'PASS','complete_session':True,'trade_quantity':2000,'spread_p99_ticks':1},
                        'MNQ|MNQ_06-26|20260331':{'status':'PASS'}}}
        self.r={'policy_id':'previous_complete_session_volume_leader_monotonic_v1',
            'signal_lag_sessions':1,'price_adjustment':'NONE_ACTUAL_TRADED_PRICES','state_boundary':'RESET_AT_CONTRACT_ROLL',
            'source_identity':self.c['source_identity'],'calendar_trade_dates':[20260330,20260331],
            'daily_assignments':[{'root':'MNQ','trade_date':20260331,'signal_trade_date':20260330,
                'active_contract':'MNQ_06-26','eligible':True,'regime_id':'test','decision':'HOLD','current_volume':2000}]}
        self.l={'root':'MNQ','frozen_before_strategy':True,'min_previous_session_volume':1000,'max_previous_session_spread_p99_ticks':2}
    def run_gate(self, day=20260331, tamper_certificate=False, tamper_regime=False):
        rh=seal(self.r);self.r['manifest_sha256']=rh
        return require_research_eligibility(certificate=self.c,regime_manifest=self.r,root='MNQ',trade_date=day,
            liquidity_limits=self.l,expected_certificate_sha256=('a'*64 if tamper_certificate else seal(self.c)),
            expected_regime_sha256=('b'*64 if tamper_regime else rh))
    def test_valid(self):self.assertEqual(self.run_gate()['contract'],'MNQ_06-26')
    def test_not_certified(self):
        self.c['status']='REMOTE_LISTED';self.assertRaises(DataEligibilityError,self.run_gate)
    def test_zero_volume(self):
        self.c['sessions']['MNQ|MNQ_06-26|20260330']['trade_quantity']=0;self.assertRaises(DataEligibilityError,self.run_gate)
    def test_infinite_volume(self):
        self.c['sessions']['MNQ|MNQ_06-26|20260330']['trade_quantity']=float('inf');self.assertRaises(DataEligibilityError,self.run_gate)
    def test_nan_volume(self):
        self.c['sessions']['MNQ|MNQ_06-26|20260330']['trade_quantity']=float('nan');self.assertRaises(DataEligibilityError,self.run_gate)
    def test_below_volume_floor(self):
        self.c['sessions']['MNQ|MNQ_06-26|20260330']['trade_quantity']=10;self.assertRaises(DataEligibilityError,self.run_gate)
    def test_spread_too_wide(self):
        self.c['sessions']['MNQ|MNQ_06-26|20260330']['spread_p99_ticks']=8;self.assertRaises(DataEligibilityError,self.run_gate)
    def test_incomplete_prior(self):
        self.c['sessions']['MNQ|MNQ_06-26|20260330']['complete_session']=False;self.assertRaises(DataEligibilityError,self.run_gate)
    def test_missing_current_quality(self):
        del self.c['sessions']['MNQ|MNQ_06-26|20260331'];self.assertRaises(DataEligibilityError,self.run_gate)
    def test_missing_schema_proof(self):
        del self.c['checks']['schema'];self.assertRaises(DataEligibilityError,self.run_gate)
    def test_certificate_hash_mismatch(self):self.assertRaises(DataEligibilityError,self.run_gate,tamper_certificate=True)
    def test_regime_hash_mismatch(self):self.assertRaises(DataEligibilityError,self.run_gate,tamper_regime=True)
    def test_holdout_closed(self):self.assertRaises(DataEligibilityError,self.run_gate,day=20260401)
    def test_same_day_volume_disallowed(self):
        self.r['daily_assignments'][0]['signal_trade_date']=20260331;self.assertRaises(DataEligibilityError,self.run_gate)
    def test_limits_not_frozen(self):
        self.l['frozen_before_strategy']=False;self.assertRaises(DataEligibilityError,self.run_gate)
    def test_adjusted_price_disallowed(self):
        self.r['price_adjustment']='ADDITIVE';self.assertRaises(DataEligibilityError,self.run_gate)

if __name__=='__main__':unittest.main()
