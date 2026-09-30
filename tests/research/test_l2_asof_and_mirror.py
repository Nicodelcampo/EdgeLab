"""Synthetic formulas and causality tests; no economic targets."""
from dataclasses import FrozenInstanceError
from pathlib import Path
import copy
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"tools"))
from l2_asof_features import AsOfFeatures,endpoint_ofi
from mirror_l2_attempts import Geometry,Attempt,AttemptRegistry,geometry_from_confirmed_event


def books():
    return ([[100-i,20.] for i in range(10)],[[101+i,10.] for i in range(10)])


def engine():
    b,a=books();e=AsOfFeatures("GC")
    e.publish(b,a,10,100,11,101)
    return e


def geometry(**kw):
    d=dict(id="fixture",instrument="GC",a_tick=80,b_tick=100,
           a_available_row=1,b_available_row=10,registration_row=11,
           registration_ts_us=101,fraction=.5)
    d.update(kw);return Geometry(**d)


class Features(unittest.TestCase):
    def test_touch_formulas(self):
        v=engine().sample(11,101)["values"]
        self.assertAlmostEqual(v["queue_imbalance_1"],1/3)
        self.assertAlmostEqual(v["weighted_mid_minus_mid_ticks"],1/6)
        self.assertEqual(v["spread_ticks"],1)
        self.assertAlmostEqual(v["weighted_mid_minus_mid_ticks"],
                               .5*v["spread_ticks"]*v["queue_imbalance_1"])

    def test_direction_reflection(self):
        v=engine().sample(11,101,direction=-1)["values"]
        self.assertAlmostEqual(v["directional_queue_imbalance_1"],-1/3)

    def test_book_mirror(self):
        bid,ask=books()
        x=AsOfFeatures("GC");y=AsOfFeatures("GC")
        x.publish(bid,ask,10,100,11,101)
        y.publish([[200-p,q] for p,q in ask],[[200-p,q] for p,q in bid],10,100,11,101)
        vx=x.sample(11,101)["values"];vy=y.sample(11,101)["values"]
        for k in ["queue_imbalance_1","queue_imbalance_3","queue_imbalance_10","weighted_mid_minus_mid_ticks"]:
            self.assertAlmostEqual(vx[k],-vy[k])

    def test_ofi_equal_prices_quantity_change(self):
        b,a=books();old=dict(bid=b,ask=a);new=copy.deepcopy(old)
        new["bid"][0][1]+=5;new["ask"][0][1]-=3
        self.assertEqual(endpoint_ofi(old,new),8)

    def test_ofi_bid_up_and_ask_down(self):
        b,a=books();old=dict(bid=b,ask=a);new=copy.deepcopy(old)
        new["bid"][0]=[101,7];new["ask"][0]=[100,9]
        self.assertEqual(endpoint_ofi(old,new),-2)

    def test_no_published_snapshot_unknown(self):
        p=AsOfFeatures("GC").sample(0,0)
        self.assertIsNone(p["values"]);self.assertEqual(p["gate"],"NO_PUBLISHED_SNAPSHOT")

    def test_future_row_rejected(self):
        with self.assertRaisesRegex(ValueError,"FUTURE"): engine().sample(10,101)

    def test_future_time_rejected(self):
        with self.assertRaisesRegex(ValueError,"FUTURE"): engine().sample(11,100)

    def test_unobserved_next_row_rejected(self):
        b,a=books()
        with self.assertRaisesRegex(ValueError,"NEXT_OBSERVED_ROW"):
            AsOfFeatures("GC").publish(b,a,10,100,10,101)

    def test_same_timestamp_publication_rejected(self):
        b,a=books()
        with self.assertRaisesRegex(ValueError,"NEXT_TIMESTAMP"):
            AsOfFeatures("GC").publish(b,a,10,100,11,100)

    def test_crossed_book_null(self):
        b,a=books();a[0][0]=100;e=AsOfFeatures("GC")
        e.publish(b,a,10,100,11,101)
        self.assertIsNone(e.sample(11,101)["values"])

    def test_incomplete_depth_null(self):
        b,a=books();e=AsOfFeatures("GC");e.publish(b[:-1],a,10,100,11,101)
        self.assertEqual(e.sample(11,101)["gate"],"INCOMPLETE_DEPTH")

    def test_unordered_book_null(self):
        b,a=books();b[2][0]=100;e=AsOfFeatures("GC");e.publish(b,a,10,100,11,101)
        self.assertEqual(e.sample(11,101)["gate"],"UNORDERED_BOOK")

    def test_zero_size_null(self):
        b,a=books();b[0][1]=0;e=AsOfFeatures("GC");e.publish(b,a,10,100,11,101)
        self.assertIsNone(e.sample(11,101)["values"])

    def test_stale_snapshot_null(self):
        p=engine().sample(20,200,max_age_us=5)
        self.assertEqual(p["gate"],"STALE_SNAPSHOT");self.assertIsNone(p["values"])

    def test_target_outside_visible_is_unknown_not_zero(self):
        p=engine().sample(11,101,target_tick=80,target_side="bid")
        self.assertFalse(p["target_observation"]["visible"])
        self.assertIsNone(p["target_observation"]["visible_size"])

    def test_target_visible_size(self):
        p=engine().sample(11,101,target_tick=100,target_side="bid")
        self.assertEqual(p["target_observation"]["visible_size"],20)

    def test_wrong_instrument_rejected(self):
        with self.assertRaisesRegex(ValueError,"CROSS_INSTRUMENT"):engine().sample(11,101,instrument="MNQ")

    def test_history_reset(self):
        b,a=books();e=engine()
        e.publish(b,a,12,102,13,103,gate="BOOTSTRAP_60S")
        e.publish(b,a,14,104,15,105)
        v=e.sample(15,105)["values"]
        self.assertIsNone(v["endpoint_ofi_window"]);self.assertEqual(v["history_span_us"],0)

    def test_prefix_independence(self):
        b,a=books();e=engine();first=e.sample(11,101)
        e.publish(b,a,12,102,13,103)
        self.assertEqual(first,engine().sample(11,101))


class Mirrors(unittest.TestCase):
    def test_crossing_is_prospective_after_observed_prefix(self):
        a=Attempt(geometry());self.assertIsNone(a.observe(95,11,101))
        p=a.observe(90,12,102,engine())
        self.assertTrue(p["prospective_event_eligible"]);self.assertEqual(p["direction"],-1)

    def test_first_seen_past_landmark_not_backdated(self):
        p=Attempt(geometry()).observe(89,15,105)
        self.assertFalse(p["prospective_event_eligible"])

    def test_target_already_reached_not_forecast(self):
        p=Attempt(geometry()).observe(80,11,101)
        self.assertFalse(p["prospective_event_eligible"]);self.assertTrue(p["target_already_reached"])

    def test_invalid_before_landmark_retained(self):
        a=Attempt(geometry());a.observe(101,11,101)
        self.assertEqual(a.receipt()["status"],"INVALID_BEFORE_LANDMARK")

    def test_pending_attempt_retained(self):
        r=AttemptRegistry("GC");a=r.register(geometry());a.observe(99,11,101)
        self.assertEqual(len(r.receipts()),1);self.assertFalse(r.receipts()[0]["landmark_emitted"])

    def test_duplicate_id_rejected(self):
        r=AttemptRegistry("GC");r.register(geometry())
        with self.assertRaisesRegex(ValueError,"ALREADY_REGISTERED"):r.register(geometry())

    def test_geometry_immutable(self):
        g=geometry()
        with self.assertRaises(FrozenInstanceError):g.a_tick=81

    def test_geometry_reassignment_rejected(self):
        a=Attempt(geometry());a.geometry=geometry(a_tick=81)
        with self.assertRaisesRegex(ValueError,"GEOMETRY_CHANGED"):a.observe(95,11,101)

    def test_unknown_B_at_registration_rejected(self):
        with self.assertRaisesRegex(ValueError,"NOT_KNOWN"):geometry(b_available_row=12)

    def test_before_registration_rejected(self):
        with self.assertRaisesRegex(ValueError,"BEFORE_CAUSAL"):Attempt(geometry()).observe(95,10,100)

    def test_duplicate_observation_rejected(self):
        a=Attempt(geometry());a.observe(95,11,101)
        with self.assertRaisesRegex(ValueError,"ORDER_OR_DUPLICATE"):a.observe(94,11,101)

    def test_no_second_emission(self):
        a=Attempt(geometry());a.observe(95,11,101);a.observe(90,12,102)
        self.assertIsNone(a.observe(89,13,103))

    def test_mirror_direction(self):
        a=Attempt(geometry(a_tick=120,b_tick=100))
        a.observe(105,11,101);p=a.observe(110,12,102)
        self.assertEqual(p["direction"],1);self.assertTrue(p["prospective_event_eligible"])

    def test_receipts_include_all_terminal_and_pending(self):
        r=AttemptRegistry("GC")
        r.register(geometry(id="pending")).observe(99,11,101)
        r.register(geometry(id="invalid")).observe(101,11,101)
        r.register(geometry(id="late")).observe(89,11,101)
        self.assertEqual(len(r.receipts()),3)
        self.assertTrue(all(x["outcomes_computed"] is False for x in r.receipts()))


class MirrorAdapter(unittest.TestCase):
    def packet(self):
        return (dict(kind="IMP_CONFIRMED",bar=8,A=80,B=100),
                dict(bar_i=8,instrument="GC",file_id="synthetic",
                     bar_close_row=10,snapshot_asof_row=11,snapshot_ts_us=100,
                     available_row=12,available_ts_us=101,
                     publication_mode="OBSERVED_NEXT_TIMESTAMP_ROW"))

    def test_registration_at_publication_not_peak(self):
        event,ledger=self.packet()
        g=geometry_from_confirmed_event(event,ledger,"GC","synthetic")
        self.assertEqual(g.b_available_row,12)
        self.assertEqual(g.a_available_row,12)

    def test_completed_only_population_rejected(self):
        event,ledger=self.packet();event["kind"]="MIRROR_COMPLETED"
        with self.assertRaisesRegex(ValueError,"ONLY_CAUSAL"):
            geometry_from_confirmed_event(event,ledger,"GC","synthetic")

    def test_terminal_record_fields_rejected(self):
        event,ledger=self.packet();event["estado_final"]="MIRROR_COMPLETED"
        with self.assertRaisesRegex(ValueError,"OUTCOME_FIELDS"):
            geometry_from_confirmed_event(event,ledger,"GC","synthetic")

    def test_missing_publication_rejected(self):
        event,ledger=self.packet();ledger["available_row"]=None
        with self.assertRaisesRegex(ValueError,"INTEGER_REQUIRED"):
            geometry_from_confirmed_event(event,ledger,"GC","synthetic")

    def test_wrong_file_rejected(self):
        event,ledger=self.packet()
        with self.assertRaisesRegex(ValueError,"CROSS_FILE"):
            geometry_from_confirmed_event(event,ledger,"GC","other")


if __name__=="__main__":
    unittest.main()