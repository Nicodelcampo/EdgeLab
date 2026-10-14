import copy,hashlib,json
from pathlib import Path
import unittest
from tools.research_ops.confluence.verify_synthetic_receipts import verify
from tools.research_ops.confluence.build_target_free_pilot import digest
R=Path(__file__).resolve().parents[2]
class ReceiptTests(unittest.TestCase):
    def setUp(self):
        self.pilot=json.loads((R/'docs/research/ops/MNQ_CONFLUENCE_SYNTHETIC_PILOT_LOCAL_RECEIPT.json').read_bytes());self.roster=json.loads((R/'docs/research/ops/MNQ_CONFLUENCE_TARGET_FREE_PILOT_ROSTER.json').read_bytes());self.package={'source_commit':'a'*40,'bundle_sha256':'b'*64}
    def args(self,pilot=None):
        p=copy.deepcopy(pilot if pilot is not None else self.pilot);p['receipt_sha256']=digest({k:v for k,v in p.items() if k!='receipt_sha256'});raw=json.dumps(p).encode()
        boot={'schema':'confluence_synthetic_kaggle_boot_v1','status':'SYNTHETIC_COMPLETE_NOT_MNQ_RESULTS','source_commit':'a'*40,'bundle_sha256':'b'*64,'pilot_receipt_sha256':hashlib.sha256(raw).hexdigest(),'exit_code':0,'stop_reason':None,'hard_address_space_limit_applied':True,'input_mounts_used':False,'internet_required':False,'wall_seconds':1.,'sampled_child_peak_rss_bytes':1,'limits_scope':'SYNTHETIC_TEST_FIXTURE',**{k:False for k in ('market_data_read','holdout_opened','outcomes_computed','pnl_computed')}}
        return json.dumps(boot).encode(),raw
    def test_good_receipt_is_not_market_approval(self):
        r=verify(*self.args(),package=self.package,roster=self.roster,local_reference=self.pilot);self.assertTrue(r['local_kaggle_exact_outputs_match']);self.assertFalse(r['market_launch_authorized'])
    def test_missing_native_reference_rejected(self):
        p=copy.deepcopy(self.pilot);p['configs'][0]['exact_native_output_verified']=False
        with self.assertRaises(ValueError):verify(*self.args(p),package=self.package,roster=self.roster)
    def test_wrong_output_bytes_rejected(self):
        b,p=self.args()
        with self.assertRaises(ValueError):verify(b,p+b' ',package=self.package,roster=self.roster)
    def test_duplicate_triad_rejected(self):
        p=copy.deepcopy(self.pilot);p['triads'][0]=p['triads'][1]
        with self.assertRaises(ValueError):verify(*self.args(p),package=self.package,roster=self.roster)
    def test_local_output_mismatch_rejected(self):
        p=copy.deepcopy(self.pilot);p['configs'][0]['capture_sha256']='f'*64
        with self.assertRaises(ValueError):verify(*self.args(p),package=self.package,roster=self.roster,local_reference=self.pilot)
if __name__=='__main__':unittest.main()
