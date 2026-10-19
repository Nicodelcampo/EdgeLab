from pathlib import Path
import sys
import tempfile
import unittest
import pandas as pd
repo_tools=Path(__file__).resolve().parents[2]/"tools"
if repo_tools.exists():sys.path.insert(0,str(repo_tools))
import mnq_l2_prepare_v2 as E
import gc_l2_fixed_price_probe as P0


class TestPublicationAndPeakSnapshot(unittest.TestCase):
    def module(self):
        p=Path(__file__).resolve().parent/"source/edgelab/research/l2_phase0.py"
        if not p.exists():p=Path(__file__).resolve().parents[2]/"edgelab/research/l2_phase0.py"
        return P0.load_book_module(p)

    def fixture(self,closing_row=True,incomplete=False):
        depth=[]
        for side in (0,1):
            for level in range(10):
                depth.append(dict(source_row=len(depth),ts_us=0,side=side,operation=0,
                    level=level,price_tick=20001+level if side==0 else 20000-level,size=10))
        depth.append(dict(source_row=20,ts_us=60_000_000,side=0,operation=1,
                         level=0,price_tick=20001,size=10))
        depth.append(dict(source_row=171,ts_us=60_000_001,side=1 if incomplete else 0,
            operation=2 if incomplete else 1,level=9 if incomplete else 0,
            price_tick=19991 if incomplete else 20001,size=0 if incomplete else 99))
        tape=[dict(source_row=i,ts_us=60_000_001,side=2,price_tick=20001,size=1)
              for i in range(21,171)]
        if closing_row:
            tape.append(dict(source_row=172,ts_us=60_000_002,side=1,price_tick=20000,size=10))
        return [{"file":"fixture","frames":{"l1_quotes":pd.DataFrame(tape),"l2_depth":pd.DataFrame(depth)}}]

    def run_fixture(self,**kwargs):
        with tempfile.TemporaryDirectory() as out:
            return E.process(self.fixture(**kwargs),self.module(),out,"fixture")

    def test_publication_waits_for_observed_closing_row(self):
        _,bars,_=self.run_fixture()
        b=bars[0]
        self.assertEqual(b["bar_close_row"],170)
        self.assertEqual(b["snapshot_asof_row"],171)
        self.assertEqual(b["available_row"],172)
        self.assertEqual(b["available_ts_us"],60_000_002)
        self.assertEqual(b["publication_mode"],"OBSERVED_NEXT_TIMESTAMP_ROW")

    def test_no_tradable_publication_at_eof(self):
        _,bars,_=self.run_fixture(closing_row=False)
        self.assertIsNone(bars[0]["available_row"])
        self.assertIsNone(bars[0]["available_ts_us"])
        self.assertFalse(bars[0]["book_valid"])
        self.assertEqual(bars[0]["publication_mode"],"EOF_DIAGNOSTIC_ONLY")

    def test_pre_extreme_does_not_use_later_same_group_quantity(self):
        _,bars,_=self.run_fixture()
        peak=bars[0]["_high"]
        pre,post=peak["pre_observation"],peak["observation"]
        self.assertEqual(pre["level_size"],10)
        self.assertEqual(post["level_size"],99)
        self.assertLessEqual(pre["available_row"],peak["source_row"])
        self.assertGreater(post["available_row"],peak["source_row"])

    def test_no_closed_group_future_changes_pre_observation(self):
        _,short,_=self.run_fixture(closing_row=False)
        _,full,_=self.run_fixture(closing_row=True)
        self.assertEqual(short[0]["_high"]["pre_observation"],
                         full[0]["_high"]["pre_observation"])

    def test_gate_reason_not_assumed_corrupt_or_false_defense(self):
        _,bars,_=self.run_fixture(incomplete=True)
        self.assertEqual(bars[0]["book_gate_reason"],"INCOMPLETE_DEPTH")
        self.assertFalse(bars[0]["book_valid"])
        self.assertIsNone(bars[0]["defense_mask"])


if __name__=="__main__":unittest.main(verbosity=2)