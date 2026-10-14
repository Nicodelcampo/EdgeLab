import hashlib,tempfile
from pathlib import Path
import unittest
try:
    import pyarrow as pa
    import pyarrow.parquet as pq
except ImportError:
    pa=pq=None
from tools.research_ops.confluence.source_footer import inspect_footer,validate_pin,HOLDOUT_OPEN_NS
@unittest.skipUnless(pa is not None,"requires optional bridge/Arrow dependency")
class FooterTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.p=Path(self.tmp.name)/'SYN.parquet'
    def fixture(self,missing=False,holdout=False):
        ts=[100,101,102,103] if not holdout else [HOLDOUT_OPEN_NS]*4
        data={'ts_utc_ns':ts,'price_ticks':[100]*4,'volume':[1.]*4,'bid_ticks':[99]*4,'ask_ticks':[100]*4,'sequence':[0,1,2,3]}
        if missing:del data['ask_ticks']
        pq.write_table(pa.table(data),self.p,row_group_size=2)
        return {'contract':'SYN','file':self.p.name,'dataset':'synthetic/fixture','version':1,'sha256':hashlib.sha256(self.p.read_bytes()).hexdigest(),'bytes':self.p.stat().st_size,'rows':4,'max_ns':max(ts)}
    def test_metadata_only_does_not_grant_quality_or_authority(self):
        pin=self.fixture();r=inspect_footer(self.p,pin);self.assertEqual(r['status'],'PASS_PINNED_FOOTER_ONLY_NOT_MARKET_APPROVAL');self.assertFalse(r['price_payload_deserialized']);self.assertFalse(r['execution_allowed']);self.assertFalse(r['source_quality_certified'])
    def test_required_quotes_not_invented(self):
        r=inspect_footer(self.p,self.fixture(missing=True));self.assertEqual(r['status'],'BLOCKED_FOOTER_REQUIREMENTS');self.assertIn('ask_ticks',r['required_columns_missing'])
    def test_wrong_bytes_rejected(self):
        pin=self.fixture();pin['sha256']='a'*64
        with self.assertRaises(ValueError):inspect_footer(self.p,pin)
    def test_holdout_pin_rejected_before_file_access(self):
        pin=self.fixture(holdout=True)
        with self.assertRaises(ValueError):validate_pin(pin)
    def test_path_mismatch_rejected(self):
        pin=self.fixture();pin['file']='other.parquet'
        with self.assertRaises(ValueError):inspect_footer(self.p,pin)
    def test_metadata_row_mismatch_rejected(self):
        pin=self.fixture();pin['rows']=5
        with self.assertRaises(ValueError):inspect_footer(self.p,pin)
if __name__=='__main__':unittest.main()
