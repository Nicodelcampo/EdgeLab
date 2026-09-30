import importlib.util
import tempfile
import unittest
from pathlib import Path
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location("support",ROOT/"tools/es_ipc_tick_support.py")
M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)

class SupportTests(unittest.TestCase):
    def run_data(self, bids, asks, ts=None):
        n=len(bids)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"x.parquet"
            pq.write_table(pa.table(dict(ts_utc_ns=ts if ts is not None else np.arange(n)+M.START,
                price_ticks=np.arange(n)+100,bid_ticks=bids,ask_ticks=asks)),p)
            return M.stream_month(p,True)

    def test_partial_counted(self):
        daily,bars,_=self.run_data([100]*53,[101]*53)
        q=daily["2026-02-01"]
        self.assertEqual((q["complete_bars"],q["partial_records"]),(2,3))
        self.assertEqual(bars["2026-02-01"]["h"].tolist(),[124,149])

    def test_quote_partition(self):
        daily,_,_=self.run_data([100,100,100,0],[101,100,99,101])
        q=daily["2026-02-01"]
        self.assertEqual([q[k] for k in ("valid_spread","locked","crossed","invalid_quote")],[1,1,1,1])

    def test_daily_anchor_reset(self):
        ts=np.r_[np.arange(26)+M.START,np.arange(26)+M.START+M.DAY]
        daily,bars,_=self.run_data([100]*52,[101]*52,ts)
        self.assertEqual(len(bars),2)
        self.assertTrue(all(q["partial_records"]==1 for q in daily.values()))

    def test_month_exclusive_end(self):
        daily,_,_=self.run_data([100]*2,[101]*2,[M.START,M.END])
        self.assertEqual(sum(q["records"] for q in daily.values()),1)

    def test_order_abstains(self):
        with self.assertRaisesRegex(AssertionError,"ORDER"):
            self.run_data([100]*2,[101]*2,[M.START+1,M.START])

    def test_frozen_es_params(self):
        self.assertEqual(M.FAMILIES["PLANAS"]["nmin"],3)
        self.assertEqual(M.FAMILIES["EMPINADAS"]["total_min"],5)
        self.assertEqual(M.FAMILIES["EMPINADAS"]["step_min"],3)

if __name__=="__main__": unittest.main()