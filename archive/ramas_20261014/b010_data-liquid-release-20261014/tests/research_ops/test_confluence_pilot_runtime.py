import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import numpy as np
from tools.research_ops.confluence.pilot_runtime import Prepared,synthetic_fixture,validate_roster,fingerprint,run_synthetic_pilot
from tools.research_ops.confluence._pinned_total_footprint import build_total_footprint_csr_nt8
from edgelab.bridge import bars as B
R=Path(__file__).resolve().parents[2]
class RuntimeTests(unittest.TestCase):
    def test_roster_unchanged_and_hash_bound(self):
        r=json.loads((R/'docs/research/ops/MNQ_CONFLUENCE_TARGET_FREE_PILOT_ROSTER.json').read_bytes());self.assertEqual(len(validate_roster(r)),96)
        bad=copy.deepcopy(r);bad['configs'][0]['params']['min_samples']=1
        with self.assertRaises(ValueError):validate_roster(bad)
    def test_cached_bars_exact_and_two_footprint_semantics_not_aliased(self):
        t,_=synthetic_fixture(sessions=2,ticks_per_session=65);p=Prepared(t)
        bt=p.get('BT2','tick:25');av=p.get('AVZP2','tick:25');again=p.get('BT2','tick:25')
        self.assertIs(bt['bars'],av['bars']);self.assertIs(bt['footprints'],again['footprints']);self.assertIsNot(bt['footprints'],av['footprints'])
        ref=B.build_tick_bars(t,25)
        for key in ('start_ns','end_ns','high_t','low_t','tick_bar_idx'):np.testing.assert_array_equal(getattr(ref,key),getattr(bt['bars'],key))
        fresh=build_total_footprint_csr_nt8(t,ref)
        for key in ('offsets','ticks','vols'):np.testing.assert_array_equal(getattr(fresh,key),getattr(av['footprints'],key))
        self.assertEqual(p.counts['bar_builds'],1);self.assertEqual(p.counts['bar_cache_hits'],2)
    def test_fixture_is_deterministic_invented_only(self):
        a,ad=synthetic_fixture(sessions=2,ticks_per_session=50);b,bd=synthetic_fixture(sessions=2,ticks_per_session=50)
        self.assertEqual(fingerprint(a.price_ticks),fingerprint(b.price_ticks));self.assertEqual(ad,bd);self.assertEqual(a.source,'INVENTED_IN_MEMORY');self.assertEqual(a.instrument,'SYN')
    def test_input_budget_before_preparation(self):
        t,_=synthetic_fixture(sessions=1,ticks_per_session=50)
        with self.assertRaises(ValueError):Prepared(t,max_tick_count=49)
    def test_bad_or_unsupported_bar_spec(self):
        t,_=synthetic_fixture(sessions=1,ticks_per_session=50);p=Prepared(t)
        for spec in ('tick:0','weird:25','time:10001'):
            with self.assertRaises(ValueError):p.get('BT2',spec)
        with self.assertRaises(ValueError):p.get('BT2A','tick:25')
    def test_complete_small_pilot_has_exact_native_outputs_and_no_outcomes(self):
        r=json.loads((R/'docs/research/ops/MNQ_CONFLUENCE_TARGET_FREE_PILOT_ROSTER.json').read_bytes())
        out=run_synthetic_pilot(r,sessions=2,ticks_per_session=65,deadline_seconds=30)
        self.assertEqual(len(out['configs']),96);self.assertEqual(len(out['triads']),32)
        self.assertTrue(all(x['exact_native_output_verified'] for x in out['configs']))
        self.assertFalse(out['market_data_read']);self.assertFalse(out['outcomes_computed'])
    def test_deadline_stops_not_partial_success(self):
        r=json.loads((R/'docs/research/ops/MNQ_CONFLUENCE_TARGET_FREE_PILOT_ROSTER.json').read_bytes())
        with patch('tools.research_ops.confluence.pilot_runtime.time.perf_counter',side_effect=[0.,5.]):
            with self.assertRaises(TimeoutError):run_synthetic_pilot(r,sessions=1,ticks_per_session=10,deadline_seconds=1)
    def test_native_hash_is_typed_and_mutation_sensitive(self):
        self.assertNotEqual(fingerprint([1]),fingerprint((1,)));self.assertNotEqual(fingerprint(1),fingerprint(1.))
        self.assertEqual(fingerprint({'b':1,'a':2}),fingerprint({'a':2,'b':1}))
        a=np.arange(5);old=fingerprint(a);a[2]=100;self.assertNotEqual(old,fingerprint(a))
if __name__=='__main__':unittest.main()
