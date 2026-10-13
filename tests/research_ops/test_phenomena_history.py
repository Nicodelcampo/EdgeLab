import copy
import json
import time
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from tools.research_ops.confluence import phenomena_history as H
from tools.research_ops.confluence import phenomena_history_session as S
from tools.research_ops.confluence import phenomena_models as M
from tools.research_ops.confluence import phenomena_history_models as HM
from tools.research_ops.confluence.asof_intersections import Clock
from tests.research_ops.test_phenomena import tape

DATE = "2026-09-17"
START = int(datetime.fromisoformat(DATE + "T22:00:00+00:00").timestamp()) * 10**9 - 86400 * 10**9


class HistoryTests(unittest.TestCase):
    def history(self, **kw):
        return H.CausalHistory(research_dates=(DATE, "2026-09-18"), **kw)

    def push(self, h, seconds, state="A_ONLY", direction=1, value=1., sequence=None):
        return h.push(Clock(START + int(seconds * 10**9), int(seconds) if sequence is None else sequence),
                      DATE, state, direction=direction,
                      continuous=None if state == "UNKNOWN" else np.full(len(M.FEATURES), value))

    def test_prefix_exact_and_input_aliases_detached(self):
        def run(stop):
            h = self.history()
            return [self.push(h, i * 5, "A_ONLY" if i < 7 else "E_ONLY", value=i) for i in range(stop)]
        a, b = run(40), run(15)
        for original, prefix in zip(a, b):
            self.assertEqual(original["path"], prefix["path"])
            for field in ("base", "capacity", "extras"):
                np.testing.assert_array_equal(original[field], prefix[field])
        h = self.history()
        x = np.ones(len(M.FEATURES))
        h.push(Clock(START, 0), DATE, "A_ONLY", direction=1, continuous=x)
        x[:] = 999.
        for seconds in (5, 10, 15, 20):
            z = self.push(h, seconds)
        np.testing.assert_array_equal(z["base"][len(M.FEATURES):2*len(M.FEATURES)], np.ones(len(M.FEATURES)))

    def test_asof_lags_never_nearest_future_and_missing_masks(self):
        h = self.history()
        for seconds in (0, 5, 10, 15, 21, 25):
            result = self.push(h, seconds, value=seconds)
        first = len(M.FEATURES)
        np.testing.assert_array_equal(result["base"][first:first+first], np.full(first, 5.))
        self.assertEqual(result["base"][2*first], 1.)
        # No observation at target40s in this prefix; explicit missing mask.
        self.assertEqual(result["base"][first + (first+2) + first], 0.)
        np.testing.assert_array_equal(result["base"][first+(first+2):first+(first+2)+first], np.zeros(first))

    def test_unknown_is_history_update_not_negative_or_skipped(self):
        h = self.history()
        self.push(h, 0)
        z = self.push(h, 5, "UNKNOWN", direction=None)
        self.assertIsNone(z["base"])
        z = self.push(h, 10, "E_ONLY")
        self.assertFalse(z["path"]["A_TO_E_observed_within_cap"])
        for t in (15, 20, 25):
            z = self.push(h, t, "E_ONLY")
        # lag20s lands on UNKNOWN at5s, not previous known at0s.
        self.assertEqual(z["base"][2*len(M.FEATURES)], 0.)
        self.assertEqual(h.count, 6)

    def test_direction_flip_gap_and_session_do_not_invent_transition(self):
        for direction, seconds in ((-1, 5), (1, 11)):
            h = self.history(); self.push(h, 0)
            z = self.push(h, seconds, "E_ONLY", direction=direction)
            self.assertTrue(z["path"]["continuity_broken"])
            self.assertFalse(z["path"]["A_TO_E_observed_within_cap"])
        h = self.history(); self.push(h, 0)
        z = h.push(Clock(START + 86400*10**9, 1), "2026-09-18", "E_ONLY",
                   direction=1, continuous=np.ones(len(M.FEATURES)))
        self.assertFalse(z["path"]["A_TO_E_observed_within_cap"])
        self.assertEqual(z["base"][2*len(M.FEATURES)], 0.)

    def test_same_ns_strict_sequence_and_single_transition_event(self):
        h = self.history()
        self.push(h, 0, sequence=0)
        z = self.push(h, 0, "E_ONLY", sequence=1)
        self.assertEqual(z["path"]["transition_observed_now"], "A_TO_E")
        z = self.push(h, 0, "E_ONLY", sequence=2)
        self.assertIsNone(z["path"]["transition_observed_now"])
        self.assertTrue(z["path"]["A_TO_E_observed_within_cap"])
        with self.assertRaises(ValueError):
            self.push(h, 0, "E_ONLY", sequence=2)
        with self.assertRaises(ValueError):
            self.push(h, 5, "E_ONLY")

    def test_bounded_history_and_anchor_cap_fail_closed(self):
        h = self.history()
        for i in range(5000):
            self.push(h, i*5)
        self.assertLessEqual(len(h.rows), 27)
        h = self.history(max_anchors=1); self.push(h, 0)
        with self.assertRaises(ValueError):
            self.push(h, 5)
        with self.assertRaises(ValueError):
            self.push(h, 10)

    def test_invalid_vector_date_holdout_and_poisoning(self):
        with self.assertRaises(ValueError):
            H.CausalHistory(research_dates=("2026-10-01",))
        for clock, day, x in ((Clock(START-1, 0), DATE, np.ones(len(M.FEATURES))),
                              (Clock(START, 0), "2026-09-19", np.ones(len(M.FEATURES))),
                              (Clock(START, 0), DATE, np.ones(3)),
                              (Clock(START, 0), DATE, np.full(len(M.FEATURES), np.nan))):
            h = self.history()
            with self.assertRaises(ValueError):
                h.push(clock, day, "A_ONLY", direction=1, continuous=x)
            self.assertTrue(h.poisoned)

    def test_thinning_before_future_filter_and_fixed_purge_embargo(self):
        h = self.history()
        selected = [i for i in range(25) if self.push(h, i*5,
                    "UNKNOWN" if i in (0,12) else "A_ONLY",
                    direction=None if i in (0,12) else 1)["retained_for_60s_sensitivity"]]
        self.assertEqual(selected, [0, 12, 24])
        split = START + 200*10**9
        self.assertTrue(H.split_eligible(Clock(split-120*10**9, 0), split_ns=split, partition="TRAIN"))
        self.assertFalse(H.split_eligible(Clock(split-120*10**9+1, 0), split_ns=split, partition="TRAIN"))
        self.assertTrue(H.split_eligible(Clock(split+60*10**9, 0), split_ns=split, partition="EVAL"))
        self.assertFalse(H.split_eligible(Clock(split+60*10**9-1, 0), split_ns=split, partition="EVAL"))

    def test_capacity_matched_ablations_common_base_and_no_tuning(self):
        h = self.history()
        results = [self.push(h, i*5, "A_ONLY" if i<5 else "E_ONLY", value=i) for i in range(30)]
        base, cc, extra = [np.stack([z[k] for z in results]) for k in ("base", "capacity", "extras")]
        for family, ix in H.MODEL_SLICES.items():
            a = H.design(base, cc, extra, "PROXY:"+family)
            b = H.design(base, cc, extra, "CAPACITY:"+family)
            self.assertEqual(a.shape, b.shape)
            self.assertEqual(a.shape[1], len(H.HISTORY_NAMES)+len(ix))
            np.testing.assert_array_equal(a[:, :len(H.HISTORY_NAMES)], b[:, :len(H.HISTORY_NAMES)])
        for name in ("PROXY:WINNER", "TUNED:ALL"):
            with self.assertRaises(ValueError):
                H.design(base, cc, extra, name)

    def test_session_history_is_pushed_before_all_future_labels(self):
        # Real integration module; synthetic rows and controlled future eligibility.
        rows = [{"timestamp_ns":START+i*5*10**9, "sequence":i, "trade_date":DATE,
                 "windows":{"20":{"direction_from_prior":1},
                            "60":{"current":{"status":"OBSERVABLE","range_midpoint_ticks":8.}}}}
                for i in range(30)]
        arrays = SimpleNamespace(ts_ns=np.array([r["timestamp_ns"] for r in rows]),
                                 sequence=np.arange(30), price_ticks=np.ones(30),
                                 volume=np.ones(30), bid_ticks=np.ones(30), ask_ticks=np.ones(30)*2)
        plan = {"research_dates":[DATE], "max_session_ticks":100, "max_anchors":100,
                "wall_seconds":100, "max_gap_ns":10**10, "max_scan_elements_per_session":10000}
        seen = []
        original = H.CausalHistory.push
        def observe(obj, *args, **kw):
            z = original(obj, *args, **kw); seen.append(args[0].sequence); return z
        class Measurement:
            summary = {}
            def __init__(self, **kwargs): pass
            def measure(self, *args, **kwargs): return iter(copy.deepcopy(rows))
        def execute(exclude):
            seen.clear()
            class Response:
                scanned = 0
                def __init__(self, *args, **kwargs): pass
                def label(self, index, **kwargs):
                    if seen[-1] != index: raise AssertionError("future read before observed history")
                    return {"usable":index not in exclude,
                            "status":"CENSORED" if index in exclude else "REVERSAL_FIRST"}
            with patch.object(S, "ClockMeasurements", Measurement), patch.object(S,"SecondsResponse",Response), \
                 patch.object(S,"state",side_effect=lambda r,*a,**k:{"state":"A_ONLY" if r["sequence"]<3 else "E_ONLY"}), \
                 patch.object(S,"features",side_effect=lambda r,*a,**k:(np.full(len(M.FEATURES),r["sequence"]),np.zeros(2))), \
                 patch.object(H.CausalHistory,"push",observe):
                return S.session_data(SimpleNamespace(ticks=arrays), DATE, plan, {}, time.monotonic())
        full = execute(set()); censored = execute({2,3,12})
        self.assertEqual(censored["summary"]["history_updates"], 30)
        self.assertEqual(censored["summary"]["observed_transition_counts_before_labels"]["A_TO_E"], 1)
        for i, clock in enumerate(censored["clocks"]):
            np.testing.assert_array_equal(censored["base"][i], full["base"][clock.sequence])
            np.testing.assert_array_equal(censored["extras"][i], full["extras"][clock.sequence])
        # Excluding selected12 must not substitute13 in thin60s.
        self.assertEqual([c.sequence for c,t in zip(censored["clocks"],censored["thin_60s"]) if t],[0,24])

    def test_real_measurement_synthetic_session_same_prefix(self):
        n = 2200
        a = tape(n); a[0] = START + np.arange(n, dtype=np.int64)*500000000
        st = SimpleNamespace(ticks=SimpleNamespace(**dict(zip(
            ("ts_ns","sequence","price_ticks","volume","bid_ticks","ask_ticks"), a))))
        plan = {"research_dates":[DATE], "max_session_ticks":5000, "max_anchors":1000,
                "wall_seconds":100, "max_gap_ns":10**10, "max_scan_elements_per_session":10000000}
        root = Path(__file__).resolve().parents[2]
        cal = json.loads((root/"docs/research/ops/MNQ_PHENOMENA_MODEL_FROZEN_CALIBRATION.json").read_bytes())
        result = S.session_data(st, DATE, plan, cal, time.monotonic())
        summary = result["summary"]
        self.assertGreater(summary["common_usable_anchors"], 100)
        self.assertEqual(summary["history_updates"], summary["observed_anchors"])
        self.assertEqual(summary["observed_anchors"], summary["common_usable_anchors"]+sum(summary["excluded_counts"].values()))
        self.assertEqual(result["base"].shape[1], len(H.HISTORY_NAMES))
        self.assertFalse(summary["raw_exported"])

    def test_equal_session_training_all_models_scored_no_eval_refit(self):
        rng = np.random.default_rng(743)
        def fixture(date, n, label=None):
            return {
                "base": rng.normal(size=(n, len(H.HISTORY_NAMES))),
                "capacity": rng.normal(size=(n, 6)),
                "extras": rng.integers(0, 2, (n, 6)).astype(float),
                "y": rng.integers(0,3,n) if label is None else np.full(n,label),
                "thin_60s": np.arange(n)%12==0,
                "summary":{"trade_date":date},
            }
        tr = [fixture("2026-09-15",100,0),fixture("2026-09-16",400,1)]
        models = HM.fit_models(tr)
        np.testing.assert_allclose(models["prior"], [.5,.5,0])
        before = copy.deepcopy(models)
        data = fixture(DATE,120)
        data["extras"][:,5] = 0  # zero support must be explicit, not good performance.
        score = HM.score(data, models)
        self.assertEqual(len(score["whole_population"]["mean_brier"]),14)
        for family in H.MODEL_SLICES:
            self.assertEqual(models["feature_counts"]["PROXY:"+family],
                             models["feature_counts"]["CAPACITY:"+family])
        self.assertIsNone(score["primary_transition_subsets"]["E_TO_A"]["all_usable"]["paired_delta_proxy_minus_capacity"])
        for name in models["models"]:
            np.testing.assert_array_equal(models["models"][name]["coef"],before["models"][name]["coef"])
        for date in ("2026-09-16","2026-10-01"):
            data["summary"]["trade_date"] = date
            with self.assertRaises(ValueError): HM.score(data, models)
        for broken in ([tr[1],tr[0]], [tr[0],tr[0]], [fixture(DATE,99)]):
            with self.assertRaises(ValueError): HM.fit_models(broken)