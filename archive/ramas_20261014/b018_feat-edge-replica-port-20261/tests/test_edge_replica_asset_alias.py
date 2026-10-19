import unittest,importlib.util,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('asset_alias_guard',ROOT/'edgelab/data/asset_safety.py')
m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
class AssetAliasTests(unittest.TestCase):
    def test_explicit_nt8_contract_spelling(self):
        d={'ts_utc_ns':[1,2],'sequence':[0,1],'price_ticks':[100,101],'bid_ticks':[99,100],'ask_ticks':[101,102],'volume':[1,2],'instrument':['MNQ','MNQ'],'contract':['MNQ 03-25','MNQ_03-25']}
        self.assertEqual(m.validate_mnq_tick_batch(d,expected_contract='MNQ_03-25'),(2,1))
        d['contract'][1]='NQ 03-25'
        self.assertRaises(m.AssetSafetyError,m.validate_mnq_tick_batch,d,expected_contract='MNQ_03-25')
