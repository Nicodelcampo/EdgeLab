import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import gc_l2_historical_controls as C


def episode(i, ts, row, stratum=(0, 0, 3, 2, 1), status="pending"):
    return {"id": i, "ts": ts, "row": row, "stratum": stratum, "status": status}


class TestHistoricalMatching(unittest.TestCase):
    def test_previous_most_recent_and_no_replacement(self):
        m = C.HistoricalMatcher()
        m.add_control(episode(0, 100, 1))
        m.add_control(episode(1, 200, 2))
        self.assertEqual(m.match(episode(2, 300, 3))["control"], 1)
        self.assertEqual(m.match(episode(3, 400, 4))["control"], 0)
        self.assertIsNone(m.match(episode(4, 500, 5)))

    def test_no_future_or_same_group_control(self):
        m = C.HistoricalMatcher()
        m.add_control(episode(0, 300, 3))
        self.assertIsNone(m.match(episode(1, 200, 2)))
        self.assertIsNone(m.match(episode(1, 300, 3)))

    def test_exact_strata_only(self):
        m = C.HistoricalMatcher()
        m.add_control(episode(0, 100, 1, (0, 0, 3, 2, 1)))
        self.assertIsNone(m.match(episode(1, 200, 2, (0, 1, 3, 2, 1))))

    def test_expiry_fixed_not_relaxed(self):
        m = C.HistoricalMatcher()
        m.add_control(episode(0, 0, 1))
        self.assertIsNone(m.match(episode(1, C.MATCH_WINDOW_US+1, 2)))

    def test_outcome_blind_including_unfinished_control(self):
        results = []
        for status in ("pending", "recovery", "disappearance_or_reset"):
            m = C.HistoricalMatcher()
            m.add_control(episode(0, 100, 1, status=status))
            results.append(m.match(episode(1, 200, 2)))
        self.assertEqual(results[0], results[1])
        self.assertEqual(results[1], results[2])

    def test_append_future_does_not_change_fixed_pair(self):
        m = C.HistoricalMatcher()
        m.add_control(episode(0, 100, 1))
        m.match(episode(1, 200, 2))
        saved = [dict(p) for p in m.pairs]
        m.add_control(episode(2, 300, 3))
        m.match(episode(3, 400, 4))
        self.assertEqual(m.pairs[:1], saved)

    def test_bins_fixed_boundaries(self):
        self.assertEqual([C.depth_bin(d) for d in (1,2,3,4,6,7,10)],
                         [0,1,1,2,2,3,3])
        self.assertEqual([C.activity_bin(n) for n in (0,1,3,4,15,16,63,64)],
                         [0,1,1,2,2,3,3,4])
        self.assertEqual([C.power_bin(n) for n in (1,2,3,4)], [0,1,1,2])


class TestAllEpisodeTracking(unittest.TestCase):
    def setUp(self):
        self.key = (0, 20000)
        self.c = C.ControlCycles()
        self.c.prior_depths[self.key] = 1

    def test_no_print_control_can_recover(self):
        self.c.change(self.key,10,5,100,1,drop_row=1)
        self.assertEqual(self.c.episodes[0]["label"],"no_raw_prints")
        self.c.change(self.key,5,8,200,2)
        self.assertEqual(self.c.episodes[0]["status"],"recovery")
        self.assertFalse(self.c.events)

    def test_used_print_not_negative_control(self):
        self.c.trade(20000,100,1,2)
        self.c.change(self.key,10,5,200,2,drop_row=2)
        self.c.change(self.key,5,8,300,3)
        self.c.change(self.key,10,5,400,4,drop_row=4)
        self.assertEqual(self.c.episodes[1]["label"],"prints_without_credit")

    def test_delete_closes_and_add_not_refill(self):
        self.c.change(self.key,10,5,100,1,drop_row=1)
        self.c.change(self.key,5,None,200,2,reset=True)
        self.c.change(self.key,None,10,300,3)
        self.assertEqual(self.c.episodes[0]["status"],"disappearance_or_reset")

    def test_later_print_not_in_features(self):
        self.c.trade(20000,100,5,2)
        self.c.change(self.key,10,5,100,6,drop_row=4)
        e = self.c.episodes[0]
        self.assertEqual(e["raw_compatible_prints"],0)
        self.assertEqual(e["activity"],0)

    def test_invalid_group_closes_all_episodes(self):
        self.c.change(self.key,10,5,100,1,drop_row=1)
        self.c.finish_episode(self.key,"invalid_group")
        self.assertFalse(self.c.all_pending)
        self.assertEqual(self.c.episodes[0]["status"],"invalid_group")


if __name__ == "__main__":
    unittest.main(verbosity=2)