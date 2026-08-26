from __future__ import annotations

import unittest
import numpy as np
import pandas as pd

from edgelab.context.l2_gate import (
    L2Book, attach_context_at_t0, extract_minute_features,
    fit_regime4_model, label_regime4,
)


class L2GateTests(unittest.TestCase):
    def test_interleaving_market_data_types_and_flow(self):
        base = 1_800_000_000_000_000
        l2 = pd.DataFrame({"side": [0, 1, 1, 1], "operation": [0, 0, 1, 2],
            "level": [0, 0, 0, 0], "price_tick": [101, 99, 99, 99],
            "size": [10, 10, 15, 0], "source_row": [0, 1, 7, 9],
            "ts_us": [base, base, base + 5, base + 7]})
        l1 = pd.DataFrame({"side": [0, 1, 2, 3, 4, 5, 6, 7, 8, 2],
            "price_tick": [101, 99, 101, 100, 102, 0, 98, 100, 0, 99],
            "size": [10, 10, 3, 0, 0, 100, 0, 0, 50, 2],
            "source_row": [2, 3, 4, 5, 6, 8, 10, 11, 12, 13],
            "ts_us": [base + i for i in range(2, 12)]})
        features, report = extract_minute_features(l2, l1, session="20260609", min_ready_levels=1)
        self.assertEqual(report["l1_side_counts"], {str(i): 1 if i != 2 else 2 for i in range(9)})
        self.assertEqual(int(features.iloc[0]["aggressive_buy_volume"]), 3)
        self.assertEqual(int(features.iloc[0]["aggressive_sell_volume"]), 2)
        self.assertEqual(int(features.iloc[0]["l1_non_signal_stat_count"]), 6)
        self.assertLessEqual(features.iloc[0]["data_window_end_us"], features.iloc[0]["feature_available_at_us"])

    def test_book_add_update_remove_and_fail_closed(self):
        book = L2Book(min_ready_levels=1, strict=False)
        book.apply(0, 0, 0, 101, 10); book.apply(1, 0, 0, 99, 10)
        self.assertTrue(book.ready)
        change = book.apply(1, 0, 1, 98, 5); self.assertEqual(change["added_size"], 5)
        change = book.apply(1, 1, 1, 98, 8); self.assertEqual(change["replenished_size"], 3)
        book.apply(1, 2, 1, 98, 0); self.assertEqual(len(book.bids.levels), 1)
        bad = book.apply(1, 1, 7, 90, 1)
        self.assertFalse(bad["valid"]); self.assertFalse(book.ready)

    @staticmethod
    def feature_fixture():
        rows = []; rng = np.random.default_rng(7)
        for s in range(6):
            session = f"202606{9 + s:02d}"
            for minute in range(80):
                state = (minute // 20 + s) % 3
                rows.append({"instrument": "GC", "contract": "GC 06-26",
                    "cme_session": session, "minute_id": s * 1000 + minute,
                    "feature_available_at_us": (s * 1000 + minute + 1) * 60_000_000,
                    "available_source_row": s * 100000 + minute * 100,
                    "feature_eligible": True,
                    "rv_ticks_15m": .5 + state * 1.5 + rng.normal(0, .03),
                    "event_rate_per_second": 2 + state * 3 + rng.normal(0, .1),
                    "spread_ticks_close": 1 + state,
                    "abs_ofi_normalized": .1 + state * .25 + rng.normal(0, .01),
                    "efficiency_ratio_10m": .2 + state * .2 + rng.normal(0, .01),
                    "log_depth_top5": 5 - state * .4 + rng.normal(0, .02),
                    "abs_tape_imbalance": .15 + state * .2,
                    "l2_remove_rate": .1 + state * .15,
                    "depth_depletion_ratio": .2 + state * .2})
        return pd.DataFrame(rows)

    def test_model_identity_prefix_invariance_and_four_states(self):
        features = self.feature_fixture(); train = [f"202606{d:02d}" for d in range(9, 13)]
        model = fit_regime4_model(features, train_sessions=train, code_identity="a" * 40)
        evaluation = ["20260613", "20260614"]
        labels_long = label_regime4(features, model, evaluation_sessions=evaluation)
        prefix = features[~((features.cme_session == "20260614") & (features.minute_id % 1000 >= 40))]
        labels_short = label_regime4(prefix, model, evaluation_sessions=evaluation)
        key = ["cme_session", "minute_id"]
        merged = labels_short[key + ["context_state"]].merge(
            labels_long[key + ["context_state"]], on=key, suffixes=("_short", "_long"))
        self.assertTrue((merged.context_state_short == merged.context_state_long).all())
        self.assertTrue(set(labels_long.context_state.dropna()) <= {"calm", "normal", "volatile", "toxic"})
        self.assertTrue(str(model["toxicity_overlay"]["name"]).endswith("not_vpin"))

    def test_source_row_asof_is_strict(self):
        contexts = pd.DataFrame({"instrument": ["GC"], "contract": ["GC 06-26"],
            "cme_session": ["20260619"], "context_state": ["normal"],
            "context_group": ["G-operable"], "context_model_id": ["model"],
            "context_as_of_ok": [True], "feature_available_at_us": [100],
            "available_source_row": [10], "p_calm": [.1], "p_normal": [.8],
            "p_volatile": [.1], "flow_toxicity_score": [.2]})
        events = pd.DataFrame({"event_id": ["same", "after"], "instrument": ["GC", "GC"],
            "contract": ["GC 06-26", "GC 06-26"],
            "cme_session": ["20260619", "20260619"], "source_row": [10, 11]})
        joined, report = attach_context_at_t0(events, contexts)
        self.assertFalse(bool(joined.iloc[0].context_as_of_ok))
        self.assertTrue(bool(joined.iloc[1].context_as_of_ok))
        self.assertEqual(report["n_as_of_ok"], 1)


if __name__ == "__main__": unittest.main()
