import unittest
from edgelab.data.time_order_reference import first_quote_fill
class TimeOrderTests(unittest.TestCase):
    def tick(self,t,seq=0):return dict(ts_utc_ns=t,sequence=seq,bid_ticks=100,ask_ticks=102)
    def fill(self,rows,**kw):
        defaults=dict(order_ns=10,information_key=(9,0),direction=1,is_exit=False,max_lateness_ns=5)
        defaults.update(kw);return first_quote_fill(rows,**defaults)
    def test_long_entry_ask(self):self.assertEqual(self.fill([self.tick(10)])['price_ticks'],102)
    def test_long_exit_bid(self):self.assertEqual(self.fill([self.tick(10)],is_exit=True)['price_ticks'],100)
    def test_short_entry_bid(self):self.assertEqual(self.fill([self.tick(10)],direction=-1)['price_ticks'],100)
    def test_short_exit_ask(self):self.assertEqual(self.fill([self.tick(10)],direction=-1,is_exit=True)['price_ticks'],102)
    def test_no_retrospective_last_tick_exit(self):
        self.assertEqual(self.fill([self.tick(9)],is_exit=True)['status'],'DATA_INCOMPLETE')
    def test_lateness_budget_is_enforced(self):
        self.assertEqual(self.fill([self.tick(16)])['status'],'DATA_INCOMPLETE')
        self.assertEqual(self.fill([self.tick(15)])['lateness_ns'],5)
    def test_signal_event_cannot_fill_itself(self):
        x=self.fill([self.tick(10,0),self.tick(10,1)],information_key=(10,0))
        self.assertEqual(x['sequence'],1);self.assertFalse(x['observed_broker_fill'])
    def test_lookahead_order_rejected(self):
        self.assertRaises(ValueError,self.fill,[],information_key=(11,0))
    def test_quote_geometry_rejected(self):
        x=self.tick(10);x['bid_ticks']=103;self.assertRaises(ValueError,self.fill,[x])
