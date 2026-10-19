"""Synthetic fixtures only. Never includes private GC data."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from gc_exact4_prepare import run_census
from gc_exact4_review import audit, export, layer, safe_viewer_copy, sha
from gc_exact4_variants import resolve


class TestGCExact4Review(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.viewer = self.root / "viewer"
        (self.viewer / "bundles").mkdir(parents=True)
        self.bundle_path = self.viewer / "bundles/GC_04-26_202602_25T_HFT.json"
        rows = [dict(high_tick=800, low_tick=799, close_tick=799, time=0, session_id="s")]
        for k in range(8):
            h = 1000 - 10*k
            rows += [dict(high_tick=h, low_tick=h-1, close_tick=h-1,
                          time=2*k+1, session_id="s"),
                     dict(high_tick=h-40, low_tick=h-41, close_tick=h-41,
                          time=2*k+2, session_id="s")]
        cd = [dict(open=b["close_tick"]/10, high=b["high_tick"]/10,
                   low=b["low_tick"]/10, close=b["close_tick"]/10, time=b["time"])
              for b in rows]
        self.bundle = dict(meta=dict(tick_size=.1), bar_series=dict(tick_25=dict(candles=cd)))
        self.bundle_path.write_text(json.dumps(self.bundle))
        self.base = dict(scope="LOCAL_CAPTURED_CURRENT_CONFIG", instrument="GC",
            tick_size=.1, asset="GC_04-26_202602_25T_HFT", bar_series="tick_25",
            bar_type="tick", bar_size=25, family="synthetic",
            source_sha256="a"*64, chart_bundle_sha256=sha(self.bundle_path),
            window=dict(first_bar_time=0,last_bar_time=16,bars=17),
            params=dict(w=1,max_gap=30,max_step=49,min_pull=25,nmin=4,dmax=1000000,
                        total_min=0,step_min=0,conf=8,
                        confirmation_mode="precio",confirm_ticks=28))
        self.baseline_path = self.root / "base.json"
        self.baseline_path.write_text(json.dumps(self.base))
        bars = self.root / "bars.jsonl"
        bars.write_text("\n".join(json.dumps(x) for x in rows))
        self.packet = self.root / "packet"
        run_census(self.baseline_path, bars, self.packet)
        (self.packet / "gc_exact4_baseline_local.json").write_bytes(self.baseline_path.read_bytes())
        self.report, _, self.resolved, self.events = audit(self.packet)

    def tearDown(self):
        self.tmp.cleanup()

    def test_audit_reconciles(self):
        self.assertEqual(len(self.report["profiles"]), 4)
        self.assertFalse(self.report["financial_use_certified"])
        self.assertFalse(self.report["outcomes_computed"])

    def test_four_frozen_members_layer(self):
        d = layer(self.base, self.resolved["profiles"][1],
                  self.events["C1_EXACT4"], self.bundle)
        self.assertTrue(d["zonas"])
        self.assertTrue(all(len(z["picos"]) == 4 and z["det_idx"] == 3 for z in d["zonas"]))

    def test_detection_price_is_close_not_trigger_fill(self):
        e = self.events["C1_EXACT4"][0]
        d = layer(self.base,self.resolved["profiles"][1],[e],self.bundle)["zonas"][0]
        self.assertEqual(d["det_precio"], self.bundle["bar_series"]["tick_25"]["candles"][e["det_i"]]["close"])
        self.assertNotEqual(d["det_precio"], d["trigger_reference_price"])

    def test_fifth_member_rejected(self):
        p = self.packet / "C1_EXACT4_events_private.jsonl"
        a = [json.loads(x) for x in p.read_text().splitlines()]
        a[0]["members"].append(a[0]["det_i"])
        p.write_text("\n".join(json.dumps(x) for x in a))
        with self.assertRaisesRegex(ValueError, "EXACT_FOUR_FAIL"): audit(self.packet)

    def test_missing_publication_not_pass(self):
        self.assertEqual(self.report["publication_verdict"],"ABSTAIN_MISSING_RAW_PUBLICATION_METADATA")
        self.assertTrue(all(r["missing_publication"] == r["zones"] for r in self.report["profiles"]))

    def test_bad_bundle_hash_abstains_before_writing(self):
        self.bundle_path.write_text(self.bundle_path.read_text() + " ")
        with self.assertRaisesRegex(ValueError,"CHART_BUNDLE_BYTES_HASH_FAIL"):
            export(self.packet, self.bundle_path, self.viewer)
        self.assertFalse((self.viewer / "bundles/peaks_det").exists())

    def test_wrong_peak_abstains(self):
        b = copy.deepcopy(self.bundle)
        e = self.events["C1_EXACT4"][0]
        field = "high" if e["kind"] == "H" else "low"
        b["bar_series"]["tick_25"]["candles"][e["members"][-1]][field] += .1
        with self.assertRaisesRegex(ValueError,"EVENT_BUNDLE_PEAK_PARITY_FAIL"):
            layer(self.base,self.resolved["profiles"][1],[e],b)

    def test_wrong_series_abstains(self):
        b = copy.deepcopy(self.bundle)
        b["bar_series"]["tick_150"] = b["bar_series"].pop("tick_25")
        with self.assertRaisesRegex(ValueError,"BUNDLE_SERIES_FAIL"):
            layer(self.base,self.resolved["profiles"][1],self.events["C1_EXACT4"],b)

    def test_wrong_time_abstains(self):
        b = copy.deepcopy(self.bundle)
        e = self.events["C1_EXACT4"][0]
        b["bar_series"]["tick_25"]["candles"][e["det_i"]]["time"] += .5
        with self.assertRaisesRegex(ValueError,"DETECTION_TIME_FAIL"):
            layer(self.base,self.resolved["profiles"][1],[e],b)

    def test_no_overwrite(self):
        (self.viewer / "index.html").write_text("original fixture")
        export(self.packet,self.bundle_path,self.viewer)
        with self.assertRaisesRegex(ValueError,"DO_NOT_OVERWRITE_LAYER"):
            export(self.packet,self.bundle_path,self.viewer)
        self.assertEqual((self.viewer / "index.html").read_text(), "original fixture")

    def test_changed_viewer_hook_abstains(self):
        with self.assertRaisesRegex(ValueError,"VIEWER_HOOK_CHANGED"):
            safe_viewer_copy("<html>unknown version</html>")

    def test_baseline_hash_mismatch_abstains(self):
        p=self.packet / "gc_exact4_baseline_local.json"
        p.write_text(p.read_text()+" ")
        with self.assertRaisesRegex(ValueError,"BASELINE_BYTES_HASH_FAIL"): audit(self.packet)

    def test_equal_timestamps_preserve_indices(self):
        b=copy.deepcopy(self.bundle)
        e=copy.deepcopy(self.events["C1_EXACT4"][0])
        for c in b["bar_series"]["tick_25"]["candles"]: c["time"]=0
        base=copy.deepcopy(self.base); base["window"]["last_bar_time"]=0
        e["logical_available_time"]=0
        d=layer(base,self.resolved["profiles"][1],[e],b)
        self.assertEqual([p[0] for p in d["zonas"][0]["picos"]],e["members"])


if __name__ == "__main__":
    unittest.main()