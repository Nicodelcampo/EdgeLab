from pathlib import Path
import sys, tempfile, unittest
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tools"))
from gc_current_logic_l2_census import publication_for,selected_functions,summarize


class CensusTests(unittest.TestCase):
    def bar(self):
        return dict(bar_i=0,feed_trade_end_row=4,l2=dict(decision_ts_us=100))

    def test_publication_excludes_entire_close_timestamp(self):
        p=publication_for(self.bar(),np.array([1,4,8,11]),np.array([100,100,100,101]))
        self.assertEqual(p["available_row"],11)
        self.assertEqual(p["snapshot_asof_row"],8)
        self.assertEqual(p["bar_close_row"],4)

    def test_no_synthetic_eof_publication(self):
        self.assertIsNone(publication_for(self.bar(),np.array([1,4]),np.array([100,100])))

    def test_invalid_raw_close_fails(self):
        b=self.bar();b["feed_trade_end_row"]=20
        with self.assertRaises(AssertionError):
            publication_for(b,np.array([1,4,11]),np.array([100,100,101]))

    def test_only_requested_original_function_executes(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"source.py"
            p.write_text("raise RuntimeError('grid forbidden')\ndef keep(x): return x+1\ndef run(): raise RuntimeError('outcome forbidden')\n")
            env=selected_functions(p,["keep"],{})
            self.assertEqual(env["keep"](2),3)
            self.assertNotIn("run",env)

    def test_missing_function_abstains(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"source.py";p.write_text("def f(): pass\n")
            with self.assertRaisesRegex(ValueError,"MISSING"):
                selected_functions(p,["detect"],{})

    def test_decorators_not_silently_removed(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"source.py";p.write_text("@decorator\ndef f(): pass\n")
            with self.assertRaisesRegex(ValueError,"DECORATED"):
                selected_functions(p,["f"],{})

    def test_missing_target_is_unknown_not_zero(self):
        q=[dict(l2=dict(gate="PASS",values=dict(full_window_available=True),
                        target_observation=dict(visible=False)))]
        s=summarize(q)
        self.assertEqual(s["total"],1);self.assertEqual(s["gate_PASS"],1)
        self.assertEqual(s["target_unknown"],1);self.assertEqual(s.get("target_visible",0),0)


if __name__=="__main__":unittest.main()