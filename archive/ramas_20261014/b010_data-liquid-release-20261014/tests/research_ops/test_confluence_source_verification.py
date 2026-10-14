import json
from pathlib import Path
import unittest
from tools.research_ops.confluence.verify_source_probe import verify
R=Path(__file__).resolve().parents[2]/'docs/research/ops'
class SourceReceiptTests(unittest.TestCase):
    def args(self):
        return ((R/'MNQ_CONFLUENCE_SOURCE_PROBE_BOOT_RECEIPT.json').read_bytes(),(R/'MNQ_CONFLUENCE_SOURCE_FOOTER_RECEIPT.json').read_bytes())
    def kw(self):return {'pin':json.loads((R/'MNQ_CONFLUENCE_SOURCE_PROBE_PLAN.json').read_bytes())['pin'],'package':json.loads((R/'MNQ_CONFLUENCE_SOURCE_PROBE_PACKAGE_RECEIPT.json').read_bytes())}
    def test_bound_real_metadata_does_not_grant_market_permission(self):
        r=verify(*self.args(),**self.kw());self.assertTrue(r['required_schema_columns_present']);self.assertFalse(r['execution_allowed']);self.assertFalse(r['source_quality_certified'])
    def test_changed_bytes_rejected(self):
        a,b=self.args()
        with self.assertRaises(ValueError):verify(a,b+b' ',**self.kw())
    def test_wrong_source_pin_rejected(self):
        kw=self.kw();kw['pin']['sha256']='a'*64
        with self.assertRaises(ValueError):verify(*self.args(),**kw)
    def test_payload_scope_mismatch_rejected(self):
        a,b=self.args();d=json.loads(a);d['price_payload_deserialized']=True
        with self.assertRaises(ValueError):verify(json.dumps(d).encode(),b,**self.kw())
if __name__=='__main__':unittest.main()
