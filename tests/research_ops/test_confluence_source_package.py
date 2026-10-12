import hashlib,json
from pathlib import Path
import unittest
import tempfile,subprocess,sys
try:
    import pyarrow as pa
    import pyarrow.parquet as pq
except ImportError:
    pa=pq=None
from tools.research_ops.confluence.package_source_probe import build_request
R=Path(__file__).resolve().parents[2]
class SourcePackageTests(unittest.TestCase):
    def pin(self):return {'contract':'SYN','file':'SYN.parquet','dataset':'synthetic/fixture','version':1,'sha256':'a'*64,'bytes':10,'rows':1,'max_ns':100}
    def test_private_metadata_only_request_no_public_signed_url(self):
        req,r=build_request(R,pin=self.pin(),url='https://storage.googleapis.com/kagglesdsdata/datasets/1/2/MNQ/SYN.parquet?test=synthetic',source_commit='a'*40)
        self.assertTrue(req['request']['isPrivate']);self.assertTrue(req['request']['enableInternet']);self.assertFalse(r['raw_input_included']);self.assertNotIn('http',json.dumps(r));self.assertEqual(r['private_request_source_sha256'],hashlib.sha256(req['request']['text'].encode()).hexdigest())
    @unittest.skipUnless(pa is not None,"requires optional bridge/Arrow dependency")
    def test_actual_bootstrap_fixture_hashes_without_deserializing_price_rows(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);file=root/'SYN.parquet';pq.write_table(pa.table({'ts_utc_ns':[100,101],'price_ticks':[10,11],'volume':[1.,2.],'bid_ticks':[9,10],'ask_ticks':[10,11],'sequence':[0,1]}),file)
            pin={**self.pin(),'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'bytes':file.stat().st_size,'rows':2,'max_ns':101}
            req,_=build_request(R,pin=pin,url='https://storage.googleapis.com/kagglesdsdata/datasets/1/2/MNQ/SYN.parquet?test=synthetic',source_commit='a'*40)
            script=req['request']['text'].replace("URL='https://storage.googleapis.com/kagglesdsdata/datasets/1/2/MNQ/SYN.parquet?test=synthetic'",'URL='+repr(file.as_uri())).replace("'/kaggle/working/confluence-source-preflight'",repr(str(root/'output')))
            (root/'probe.py').write_text(script);p=subprocess.run([sys.executable,str(root/'probe.py')],capture_output=True,text=True,timeout=30)
            self.assertEqual(p.returncode,0,p.stderr);boot=json.loads((root/'output'/'boot-receipt.json').read_bytes());self.assertEqual(boot['status'],'PASS_PINNED_FOOTER_ONLY_NOT_MARKET_APPROVAL');self.assertFalse(boot['price_payload_deserialized']);self.assertFalse(boot['raw_file_exported'])
    def test_url_host_and_file_bound(self):
        for url in ('https://evil.example/MNQ/SYN.parquet','https://storage.googleapis.com/kagglesdsdata/datasets/1/2/MNQ/OTHER.parquet'):
            with self.assertRaises(ValueError):build_request(R,pin=self.pin(),url=url,source_commit='a'*40)
    def test_holdout_pin_cannot_package(self):
        pin=self.pin();pin['max_ns']=1800000000000000000
        with self.assertRaises(ValueError):build_request(R,pin=pin,url='https://storage.googleapis.com/kagglesdsdata/datasets/1/2/MNQ/SYN.parquet',source_commit='a'*40)
if __name__=='__main__':unittest.main()
