"""Invented metadata mutations; no markets, outcomes, network or admission."""
import copy
import json
from pathlib import Path
import unittest
from tools.research_ops.designs.check_mnq_dense_confluence import check_metadata

ROOT=Path(__file__).resolve().parents[2]
class DesignMetadataTest(unittest.TestCase):
    def setUp(self):self.spec=json.loads((ROOT/'docs/research/ops/MNQ_DENSE_CONFLUENCE_DESIGN.json').read_text())
    def test_current_is_design_only(self):
        r=check_metadata(self.spec);self.assertFalse(r['launch_authorized']);self.assertEqual(r['detector_definitions_total'],21888)
    def test_rejects_every_authority_claim(self):
        for k in self.spec['authorization']:
            with self.subTest(k=k):
                s=copy.deepcopy(self.spec);s['authorization'][k]=True
                with self.assertRaises(ValueError):check_metadata(s)
    def test_rejects_integer_false(self):
        self.spec['authorization']['launch_authorized']=0
        with self.assertRaises(ValueError):check_metadata(self.spec)
    def test_rejects_holdout_change(self):
        self.spec['data_policy']['holdout_start_trade_date']='2026-11-01'
        with self.assertRaises(ValueError):check_metadata(self.spec)
    def test_rejects_sources_in_design(self):
        self.spec['data_policy']['approved_source_manifest']={'status':'PASS'}
        with self.assertRaises(ValueError):check_metadata(self.spec)
    def test_rejects_duplicate_level(self):
        self.spec['catalog']['axes']['racimo']['racimo_min'].append(3)
        with self.assertRaises(ValueError):check_metadata(self.spec)
    def test_rejects_wrong_count(self):
        self.spec['catalog']['nominal_counts']['bigtrap2']=1
        with self.assertRaises(ValueError):check_metadata(self.spec)
    def test_rejects_duplicate_scenario(self):
        self.spec['scenario_catalog'][1]['id']='S01'
        with self.assertRaises(ValueError):check_metadata(self.spec)
    def test_rejects_fastmath(self):
        self.spec['execution_contract']['fastmath_allowed']=True
        with self.assertRaises(ValueError):check_metadata(self.spec)
    def test_rejects_measured_speedup(self):
        self.spec['execution_contract']['hardware_walltime_ram_estimate']={'speedup':100}
        with self.assertRaises(ValueError):check_metadata(self.spec)
    def test_rejects_self_edge(self):
        self.spec['asserts_edge']=True
        with self.assertRaises(ValueError):check_metadata(self.spec)
    def test_rejects_preregistered_label(self):
        self.spec['status']='PREREGISTERED'
        with self.assertRaises(ValueError):check_metadata(self.spec)
if __name__=='__main__':unittest.main()
