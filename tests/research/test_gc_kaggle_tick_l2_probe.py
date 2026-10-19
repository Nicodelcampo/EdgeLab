import unittest
import pandas as pd
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
if (ROOT/"tools").is_dir():
    sys.path.insert(0, str(ROOT/"tools"))
from gc_kaggle_tick_l2_probe import exact_tape, OFFSET_US


class IdentityTests(unittest.TestCase):
    def fixtures(self):
        l1 = pd.DataFrame(dict(side=[2, 2, 2], source_row=[2, 5, 9],
                               ts_us=[100, 100, 200],
                               price_tick=[20, 20, 21], size=[1, 1, 2]))
        ticks = pd.DataFrame(dict(ts_utc_ns=[(100+OFFSET_US)*1000]*2+
                                  [(200+OFFSET_US)*1000],
                                  price_ticks=[20, 20, 21], volume=[1, 1, 2]))
        return l1, ticks

    def test_entire_ordered_tape_with_repeated_prints(self):
        l1,ticks = self.fixtures()
        q,tr = exact_tape(ticks,l1)
        self.assertEqual(len(q),3)

    def test_time_mismatch_abstains(self):
        l1,ticks = self.fixtures()
        ticks.loc[0,"ts_utc_ns"] += 1
        with self.assertRaisesRegex(ValueError,"IDENTITY_FAIL"):
            exact_tape(ticks,l1)

    def test_same_multiset_but_different_order_abstains(self):
        l1,ticks = self.fixtures()
        l1.loc[0,"size"],l1.loc[1,"size"] = 3,4
        ticks.loc[0,"volume"],ticks.loc[1,"volume"] = 4,3
        with self.assertRaisesRegex(ValueError,"IDENTITY_FAIL"):
            exact_tape(ticks,l1)

    def test_missing_trade_abstains(self):
        l1,ticks = self.fixtures()
        with self.assertRaisesRegex(ValueError,"IDENTITY_FAIL"):
            exact_tape(ticks.iloc[1:],l1)


if __name__ == "__main__":
    unittest.main()