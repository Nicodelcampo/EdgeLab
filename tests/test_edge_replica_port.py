import unittest,json,re,hashlib
from pathlib import Path
from datetime import datetime,timedelta,timezone
import importlib.util,sys,base64,gzip
ROOT=Path(__file__).resolve().parents[1]
def load_repo_module(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path)
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module
    spec.loader.exec_module(module);return module
load_repo_module('edge_replica','strategies/edge_replica.py')
load_repo_module('asset_safety','edgelab/data/asset_safety.py')
from edge_replica import Bar,Rule,load_rules,shadow_events
from asset_safety import AssetSafetyError,safe_group_ids,audited_volume_rows,validate_mnq_tick_batch
UTC=timezone.utc

def bars(count=40,start=None,close=1000,session_end=None):
    start=start or datetime(2025,1,6,14,0,tzinfo=UTC)
    end=session_end or start+timedelta(hours=9)
    return [Bar(start+timedelta(minutes=i),close+i,end,'MNQ_03-25','regime-test') for i in range(count)]

class PortTests(unittest.TestCase):
    def test_source_rules_roundtrip(self):
        src=gzip.decompress(base64.b64decode((ROOT/'tests/fixtures/edge_replica/EdgeReplica.cs.gz.b64').read_bytes()))
        o=json.loads((ROOT/'config/edge_replica/rules_v1.json').read_text())
        self.assertEqual(hashlib.sha256(src).hexdigest(),o['source_sha256'])
        parsed=[list(map(int,m)) for m in re.findall(r'new RuleDef\((\d+),\s*(\d+),\s*(\d+),\s*(-?\d+),\s*(\d+),\s*(-?\d+)\)',src.decode('utf-8-sig'))]
        self.assertEqual(parsed,o['rules']);self.assertEqual(len(load_rules(ROOT/'config/edge_replica/rules_v1.json')),60)
    def test_three_phase_latency_and_hold(self):
        result=shadow_events(bars(),[Rule(1,1,800,1,15,0)])
        by={e['event']:e for e in result['events']}
        self.assertEqual(by['SIGNAL']['bar_index'],1)
        self.assertEqual(by['SUBMIT_ENTRY']['bar_index'],2)
        self.assertEqual(by['ASSUMED_ENTRY_FILL']['bar_index'],3)
        self.assertEqual(by['SUBMIT_EXIT']['bar_index'],17)
        self.assertEqual(by['ASSUMED_EXIT_FILL']['bar_index'],18)
        self.assertFalse(result['observed_broker_fills']);self.assertFalse(result['asserts_edge'])
    def test_clock_reference_not_15_rows(self):
        a=bars(25);a=[b for i,b in enumerate(a) if i not in (3,4,5)]
        r=shadow_events(a,[Rule(1,1,820,1,15,1)])
        signals=[e for e in r['events'] if e['event']=='SIGNAL']
        self.assertEqual(signals[0]['reference_bar_index'],3)
    def test_cond_zero_does_not_need_reference(self):
        self.assertTrue(shadow_events(bars(5),[Rule(1,1,800,1,15,0)])['events'])
    def test_cond_requires_reference(self):
        self.assertFalse(shadow_events(bars(5),[Rule(1,1,800,1,15,1)])['events'])
    def test_zero_change_rejects_directional_cond(self):
        a=bars(30);a=[Bar(b.end,1000,b.session_end,b.contract,b.regime_id) for b in a]
        self.assertFalse(shadow_events(a,[Rule(1,1,820,1,15,1)])['events'])
    def test_weekend_skip(self):
        self.assertFalse(shadow_events(bars(start=datetime(2025,1,5,14,0,tzinfo=UTC)),[Rule(1,0,800,1,15,0)])['events'])
    def test_dst_chicago_conversion(self):
        self.assertTrue(shadow_events(bars(start=datetime(2025,3,10,13,0,tzinfo=UTC)),[Rule(1,1,800,1,15,0)])['events'])
    def test_wrong_dow(self):
        self.assertFalse(shadow_events(bars(),[Rule(1,2,800,1,15,0)])['events'])
    def test_session_margin_gate(self):
        a=bars(3,session_end=datetime(2025,1,6,14,16,tzinfo=UTC))
        self.assertTrue(shadow_events(a,[Rule(1,1,800,1,15,0)],session_margin=0)['events'])
        self.assertFalse(shadow_events(a,[Rule(1,1,800,1,15,0)],session_margin=1)['events'])
    def test_reversal_logical_lots(self):
        out=shadow_events(bars(),[Rule(1,1,800,1,60,0),Rule(2,1,810,-1,15,0)])
        self.assertEqual([e['rule_id'] for e in out['events'] if e['event']=='ASSUMED_REVERSAL_CLOSE'],[1])
    def test_terminal_censor_preserved(self):
        out=shadow_events(bars(3),[Rule(1,1,800,1,15,0)])
        self.assertEqual(out['unresolved']['submitted_orders'],[{'kind':'entry','rule_id':1}])
    def test_naive_timestamp_rejected(self):
        a=bars();a[0]=Bar(a[0].end.replace(tzinfo=None),1000,a[0].session_end,a[0].contract,a[0].regime_id)
        self.assertRaises(ValueError,shadow_events,a,[])
    def test_mixed_contract_rejected(self):
        a=bars();a[2]=Bar(a[2].end,1002,a[2].session_end,'MNQ_06-25','other')
        self.assertRaises(ValueError,shadow_events,a,[])
    def test_standard_nq_rejected(self):
        a=[Bar(b.end,b.close_ticks,b.session_end,'NQ_03-25',b.regime_id) for b in bars()]
        self.assertRaises(ValueError,shadow_events,a,[])
    def test_no_virtual_stop_target(self):
        out=shadow_events(bars(),[Rule(1,1,800,1,15,0)])
        self.assertNotIn('pnl',out);self.assertFalse(any('tp' in e or 'sl' in e for e in out['events']))

class AssetTests(unittest.TestCase):
    def tick(self):return {'ts_utc_ns':[1,1,2],'sequence':[0,1,0],'price_ticks':[100,100,101],'bid_ticks':[99,99,100],'ask_ticks':[101,101,102],'volume':[1,1,2]}
    def test_same_timestamp_legitimate_ticks(self):self.assertEqual(validate_mnq_tick_batch(self.tick(),expected_contract='MNQ_03-25'),(2,0))
    def test_duplicate_identity_rejected(self):
        d=self.tick();d['sequence'][1]=0;self.assertRaises(AssetSafetyError,validate_mnq_tick_batch,d,expected_contract='MNQ_03-25')
    def test_crossed_quotes_rejected(self):
        d=self.tick();d['bid_ticks'][1]=500;self.assertRaises(AssetSafetyError,validate_mnq_tick_batch,d,expected_contract='MNQ_03-25')
    def test_no_negative_volume(self):
        d=self.tick();d['volume'][0]=-1;self.assertRaises(AssetSafetyError,validate_mnq_tick_batch,d,expected_contract='MNQ_03-25')
    def test_group_cutoff_strict(self):
        ids,excluded=safe_group_ids([{'min_ts':1,'max_ts':9,'null_count':0},{'min_ts':9,'max_ts':10,'null_count':0},{}],10)
        self.assertEqual(ids,[0]);self.assertEqual(len(excluded),2)
    def session(self):return {'root':'MNQ','contract':'MNQ_03-25','trade_date':20250106,'volume':200,'observed':True,'complete_session':True,'audit_status':'COMPLETE_VERIFIED'}
    def test_unknown_is_not_zero(self):
        s=self.session();s['observed']=False;s['volume']=0;self.assertRaises(AssetSafetyError,audited_volume_rows,[s])
    def test_observed_zero_preserved_not_liquid_certified(self):
        s=self.session();s['volume']=0;self.assertEqual(audited_volume_rows([s])[0]['volume'],0)
    def test_infinite_volume_rejected(self):
        s=self.session();s['volume']=float('inf');self.assertRaises(AssetSafetyError,audited_volume_rows,[s])
    def test_completeness_not_assumed(self):
        s=self.session();s['audit_status']='UNKNOWN';self.assertRaises(AssetSafetyError,audited_volume_rows,[s])
    def test_missing_row_not_invented(self):self.assertEqual(audited_volume_rows([]),[])
    def test_cross_batch_backwards(self):self.assertRaises(AssetSafetyError,validate_mnq_tick_batch,self.tick(),expected_contract='MNQ_03-25',previous_key=(2,1))




class CustodyTests(unittest.TestCase):
    def test_matching_declared_hash(self):
        from asset_safety import verify_file_custody
        import tempfile
        with tempfile.NamedTemporaryFile() as f:
            f.write(b'synthetic');f.flush()
            self.assertEqual(verify_file_custody(f.name,expected_file_sha256=hashlib.sha256(b'synthetic').hexdigest())['bytes'],9)
    def test_mismatched_hash_quarantines(self):
        from asset_safety import verify_file_custody
        import tempfile
        with tempfile.NamedTemporaryFile() as f:
            f.write(b'synthetic');f.flush()
            self.assertRaises(AssetSafetyError,verify_file_custody,f.name,expected_file_sha256='0'*64)
    def test_no_implicit_custody(self):
        from asset_safety import verify_file_custody
        self.assertRaises(AssetSafetyError,verify_file_custody,'not-opened',expected_file_sha256=None)
    def test_reader_rejects_before_pyarrow_or_rows(self):
        from asset_safety import stream_safe_preholdout
        import tempfile
        with tempfile.NamedTemporaryFile() as f:
            f.write(b'synthetic');f.flush()
            gen=stream_safe_preholdout(f.name,cutoff_ns=1,expected_contract='MNQ_03-26',expected_file_sha256='0'*64)
            self.assertRaises(AssetSafetyError,next,gen)

if __name__=='__main__':unittest.main()
