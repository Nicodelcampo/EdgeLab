import unittest,hashlib,copy
from datetime import datetime,timezone
from edgelab.data.edge_replica_inputs import make_shadow_reader,calendar_digest

def ns(s):return int(datetime.fromisoformat(s).replace(tzinfo=timezone.utc).timestamp())*10**9
class InputTests(unittest.TestCase):
    def setup_reader(self,rows,calendar=None,cutoff=None):
        c=calendar or [{'contract':'MNQ_03-25','regime_id':'synthetic-only','trade_date':20250106,
            'open_ns':ns('2025-01-05T23:00:00'),'close_ns':ns('2025-01-06T22:00:00'),'status':'VERIFIED'}]
        # Fixtures are synthetic approvals, never actual calendar certificates.
        p={k:c[0][k] for k in ('contract','regime_id','trade_date')};calls=[];report={}
        def source(permission):calls.append(permission);return iter(rows)
        reader=make_shadow_reader(source,calendar=c,expected_calendar_sha256=calendar_digest(c),
            cutoff_ns=cutoff or ns('2025-02-01T00:00:00'),report=report)
        return reader,p,calls,report
    def tick(self,t,price=100,seq=0):
        return {'ts_utc_ns':t,'sequence':seq,'price_ticks':price,'bid_ticks':price-1,
            'ask_ticks':price+1,'volume':1,'tick_type':'trade','instrument':'MNQ','contract':'MNQ 03-25'}
    def test_close_belongs_to_session_not_next_day(self):
        end=ns('2025-01-06T22:00:00');r,p,c,a=self.setup_reader([self.tick(end-1)])
        b=list(r([p]))[0][0][0];self.assertEqual(b.end,b.session_end)
        self.assertEqual(list(a['sessions'])[0]['trade_date'],20250106)
    def test_right_open_minute(self):
        t=ns('2025-01-06T14:00:00');r,p,c,a=self.setup_reader([self.tick(t,100),self.tick(t+60*10**9,200)])
        bars=list(r([p]))[0];self.assertEqual([x[0].close_ticks for x in bars],[100,200])
        self.assertEqual(int(bars[0][0].end.timestamp())*10**9,t+60*10**9)
    def test_no_fabricated_gap_bars(self):
        t=ns('2025-01-06T14:00:00');r,p,c,a=self.setup_reader([self.tick(t),self.tick(t+180*10**9,200)])
        self.assertEqual(len(list(r([p]))[0]),2);self.assertEqual(a['empty_bars_fabricated'],0)
        self.assertFalse(a['sessions'][0]['complete_session_certified_by_adapter'])
    def test_all_permissions_checked_before_read(self):
        r,p,c,a=self.setup_reader([]);bad=dict(p,trade_date=20250107)
        self.assertRaises(ValueError,lambda:list(r([p,bad])));self.assertFalse(c)
    def test_closed_tick_rejected_not_shifted(self):
        r,p,c,a=self.setup_reader([self.tick(ns('2025-01-06T22:00:00'))])
        self.assertRaises(ValueError,lambda:list(r([p])))
    def test_unknown_calendar_rejected(self):
        c=[{'contract':'MNQ_03-25','regime_id':'synthetic-only','trade_date':20250106,
            'open_ns':ns('2025-01-05T23:00:00'),'close_ns':ns('2025-01-06T22:00:00'),'status':'UNVERIFIED'}]
        self.assertRaises(ValueError,self.setup_reader,[],c)
    def test_sealed_calendar_rejected_before_read(self):
        self.assertRaises(ValueError,self.setup_reader,[],None,ns('2025-01-06T21:00:00'))
    def test_empty_is_not_zero_activity(self):
        r,p,c,a=self.setup_reader([]);self.assertRaises(ValueError,lambda:list(r([p])))
    def test_identity_order_preserved(self):
        t=ns('2025-01-06T14:00:00');r,p,c,a=self.setup_reader([self.tick(t,100,0),self.tick(t,101,1)])
        self.assertEqual(list(r([p]))[0][0][0].close_ticks,101)
        r,p,c,a=self.setup_reader([self.tick(t,100,0),self.tick(t,101,0)])
        self.assertRaises(ValueError,lambda:list(r([p])))
