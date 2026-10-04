"""Graph wiring test. Gate/calendar approvals are SYNTHETIC MOCKS, not custody evidence."""
import unittest,types,sys
from unittest.mock import patch
from datetime import datetime,timezone
from strategies.edge_replica import run_verified_shadow,Rule
from edgelab.data.edge_replica_inputs import make_shadow_reader,calendar_digest

def ns(s):return int(datetime.fromisoformat(s).replace(tzinfo=timezone.utc).timestamp())*10**9
class ConnectedTests(unittest.TestCase):
    def case(self,blocked=False):
        p=dict(contract='MNQ_03-25',regime_id='synthetic-only',trade_date=20250106)
        cal=[dict(p,open_ns=ns('2025-01-05T23:00:00'),close_ns=ns('2025-01-06T22:00:00'),status='VERIFIED')]
        calls=[];report={}
        def source(permission):
            calls.append(permission)
            for i in range(5):
                yield dict(ts_utc_ns=ns('2025-01-06T14:00:00')+i*60*10**9,sequence=i,
                    price_ticks=100+i,bid_ticks=99+i,ask_ticks=101+i,volume=1,tick_type='trade',instrument='MNQ',contract='MNQ 03-25',
                    source_file='SYNTHETIC.Last.txt',source_row=i)
        reader=make_shadow_reader(source,calendar=cal,expected_calendar_sha256=calendar_digest(cal),
            cutoff_ns=ns('2025-02-01T00:00:00'),report=report)
        def mock_gate(**kwargs):
            if blocked:raise ValueError('SYNTHETIC_BLOCKED_GATE')
            return p
        modules={'edgelab.data.contract_regime':types.SimpleNamespace(validate_contract_regime=lambda m:None),
                 'edgelab.data.research_data_gate':types.SimpleNamespace(require_research_eligibility=mock_gate)}
        args=dict(reader=reader,rules=[Rule(1,1,801,1,15,0)],root='MNQ',trade_dates=[20250106],
            certificate={},regime_manifest={},liquidity_limits={},expected_certificate_sha256='mock',expected_regime_sha256='mock')
        return modules,args,calls,report
    def test_gate_reader_shadow_connected(self):
        modules,args,calls,report=self.case()
        with patch.dict(sys.modules,modules):out=run_verified_shadow(**args)
        self.assertEqual(len(calls),1)
        self.assertTrue(any(e['event']=='SUBMIT_ENTRY' for e in out[0]['events']))
        self.assertFalse(out[0]['observed_broker_fills']);self.assertFalse(out[0]['asserts_edge'])
        self.assertEqual(report['sessions'][0]['bars'],5)
    def test_blocked_gate_never_invokes_reader(self):
        modules,args,calls,report=self.case(True)
        with patch.dict(sys.modules,modules):self.assertRaises(ValueError,run_verified_shadow,**args)
        self.assertFalse(calls)
