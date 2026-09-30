import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from gc_l2_fixed_price_probe import Cycles

K=(0,20000)

class TestCycles(unittest.TestCase):
    def test_observed_drop_then_refill(self):
        c=Cycles();c.trade(20000,100,1,3)
        c.change(K,10,5,200,2,drop_row=2);c.change(K,5,8,300,3)
        self.assertEqual(len(c.events),1)
        self.assertEqual(c.events[0]["available_row"],3)
        self.assertEqual(c.events[0]["print_volume"],3)
    def test_no_trade_no_attribution(self):
        c=Cycles();c.change(K,10,5,200,2,drop_row=2);c.change(K,5,10,300,3)
        self.assertFalse(c.events)
    def test_future_time_print_not_used(self):
        c=Cycles();c.trade(20000,400,1,3)
        c.change(K,10,5,200,2,drop_row=2);c.change(K,5,10,300,3)
        self.assertFalse(c.events)
    def test_later_source_row_same_timestamp_not_used(self):
        c=Cycles();c.trade(20000,100,5,3)
        c.change(K,10,5,100,6,drop_row=4);c.change(K,5,10,300,7)
        self.assertFalse(c.events)
    def test_delete_reappearance_not_refill(self):
        c=Cycles();c.trade(20000,100,1,3)
        c.change(K,10,5,200,2,drop_row=2);c.change(K,5,None,250,3,reset=True)
        c.change(K,None,10,300,4)
        self.assertFalse(c.events)
    def test_no_reuse_of_print(self):
        c=Cycles();c.trade(20000,100,1,3)
        c.change(K,10,5,200,2,drop_row=2);c.change(K,5,10,300,3)
        c.change(K,10,5,400,4,drop_row=4);c.change(K,5,10,500,5)
        self.assertEqual(len(c.events),1)
    def test_timeout(self):
        c=Cycles();c.trade(20000,100,1,3)
        c.change(K,10,5,200,2,drop_row=2);c.change(K,5,10,5_000_201,3)
        self.assertFalse(c.events)
    def test_old_print_expired(self):
        c=Cycles();c.trade(20000,100,1,3)
        c.change(K,10,5,2_000_101,2,drop_row=2);c.change(K,5,10,2_000_102,3)
        self.assertFalse(c.events)
    def test_change_of_price_not_same_episode(self):
        c=Cycles();c.trade(20000,100,1,3)
        c.change(K,10,5,200,2,drop_row=2);c.change(K,5,None,250,3,reset=True)
        c.change((0,20001),5,10,300,4)
        self.assertFalse(c.events)
    def test_prefix_event_immutability(self):
        c=Cycles();c.trade(20000,100,1,3)
        c.change(K,10,5,200,2,drop_row=2);c.change(K,5,10,300,3)
        saved=[dict(e) for e in c.events]
        c.trade(20000,400,4,2)
        c.change(K,10,5,500,5,drop_row=5);c.change(K,5,10,600,6)
        self.assertEqual(c.events[:1],saved)
    def test_price_not_depth_key(self):
        c=Cycles();c.trade(20000,100,1,3)
        c.change(K,10,5,200,2,drop_row=2);c.change((0,20001),5,10,300,3)
        self.assertFalse(c.events)
    def test_no_eof_flushed_recovery(self):
        c=Cycles();c.trade(20000,100,1,3);c.change(K,10,5,200,2,drop_row=2)
        self.assertFalse(c.events);self.assertEqual(len(c.pending),1)

if __name__=="__main__":unittest.main(verbosity=2)