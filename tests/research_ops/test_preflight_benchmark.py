"""Invented metadata/bars only. No real authority, review or market data produced."""
import hashlib,json,os,random,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from edgelab.data.contract_regime import build_contract_regime
from edgelab.data.research_data_gate import REQUIRED_CHECKS,seal,require_research_eligibility
from tests.synthetic_selection_evidence import add_selection_review
from tools.research_ops.preflight import check_bundle,MAX_BYTES
from tools.research_ops.benchmark import reference_ranges,deque_ranges,run_benchmark
from tools.research_ops.cli import main

def synthetic_bundle():
    days=[20260330,20260331,20260401]
    r=build_contract_regime(contracts=[dict(root='MNQ',contract='MNQ_06-26',expiry_ordinal=202606,first_trade_date=days[0],last_trade_date=days[-1])],daily_volumes=[dict(root='MNQ',contract='MNQ_06-26',trade_date=d,volume=2000,complete_session=True) for d in days],calendar_trade_dates=days,source_identity={'dataset':'SYNTHETIC_TEST_ONLY','version':1})
    c=dict(status='SANITIZED_VERIFIED',checks=dict.fromkeys(REQUIRED_CHECKS,'PASS'),source_identity=r['source_identity'],holdout_first_trade_date=20260401,allowed_trade_dates=days[:2],sessions={'MNQ|MNQ_06-26|20260330':dict(status='PASS',complete_session=True,trade_quantity=2000,spread_p99_ticks=1),'MNQ|MNQ_06-26|20260331':dict(status='PASS',complete_session=True)})
    add_selection_review(c,r,'MNQ')
    limits=dict(root='MNQ',frozen_before_strategy=True,min_previous_session_volume=1000,max_previous_session_spread_p99_ticks=2)
    return dict(schema_version='research_gate_request_v1',request=dict(certificate=c,regime_manifest=r,root='MNQ',trade_date=20260331,liquidity_limits=limits,expected_certificate_sha256=seal(c),expected_regime_sha256=r['manifest_sha256'],expected_liquidity_limits_sha256=seal(limits)))

class PreflightTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'metadata.json';self.bundle=synthetic_bundle()
    def tearDown(self): self.tmp.cleanup()
    def write(self,bundle=None,raw=None):
        self.path.write_bytes(raw if raw is not None else json.dumps(bundle if bundle is not None else self.bundle).encode())
        return hashlib.sha256(self.path.read_bytes()).hexdigest()
    def test_canonical_pass_never_executes(self):
        out=check_bundle(self.path,self.write());self.assertEqual(out['decision']['contract'],'MNQ_06-26')
        for key in ('market_data_read','authority_authenticated','execution_allowed','holdout_opened','promotion_allowed'): self.assertIs(out[key],False)
    def test_canonical_gate_called(self):
        sha=self.write()
        with patch('tools.research_ops.preflight.require_research_eligibility',wraps=require_research_eligibility) as gate:
            check_bundle(self.path,sha);gate.assert_called_once_with(**self.bundle['request'])
    def test_digest_mismatch(self):
        self.write()
        with self.assertRaises(ValueError): check_bundle(self.path,'0'*64)
    def test_no_derived_pin_fallback(self):
        with self.assertRaises(ValueError): check_bundle(self.path,'')
    def test_certificate_pin_mismatch(self):
        self.bundle['request']['expected_certificate_sha256']='f'*64
        with self.assertRaises(ValueError): check_bundle(self.path,self.write())
    def test_holdout_rejected(self):
        self.bundle['request']['trade_date']=20260401
        with self.assertRaises(ValueError): check_bundle(self.path,self.write())
    def test_same_day_selection_rejected(self):
        r=self.bundle['request']['regime_manifest'];r['daily_assignments'][1]['signal_trade_date']=20260331;r.pop('manifest_sha256');r['manifest_sha256']=seal(r);self.bundle['request']['expected_regime_sha256']=r['manifest_sha256']
        with self.assertRaises(ValueError): check_bundle(self.path,self.write())
    def test_sanitation_not_invented(self):
        c=self.bundle['request']['certificate'];c['status']='EXPLORATORY_ONLY';self.bundle['request']['expected_certificate_sha256']=seal(c)
        with self.assertRaises(ValueError): check_bundle(self.path,self.write())
    def test_exploratory_not_coerced(self):
        sha=self.write(dict(schema='avzvol_exploratory_authorization_v1',source_quality_certified=False))
        with self.assertRaises(ValueError): check_bundle(self.path,sha)
    def test_extra_request_field(self):
        self.bundle['request']['command']='shell'
        with self.assertRaises(ValueError): check_bundle(self.path,self.write())
    def test_extra_top_level_field(self):
        self.bundle['command']='shell'
        with self.assertRaises(ValueError): check_bundle(self.path,self.write())
    def test_missing_field(self):
        del self.bundle['request']['liquidity_limits']
        with self.assertRaises(ValueError): check_bundle(self.path,self.write())
    def test_duplicates(self):
        sha=self.write(raw=b'{"request":{},"request":{}}')
        with self.assertRaises(ValueError): check_bundle(self.path,sha)
    def test_nonfinite(self):
        sha=self.write(raw=b'{"number":NaN}')
        with self.assertRaises(ValueError): check_bundle(self.path,sha)
    def test_oversize(self):
        sha=self.write(raw=b' '*(MAX_BYTES+1))
        with self.assertRaises(ValueError): check_bundle(self.path,sha)
    def test_symlink(self):
        sha=self.write();link=self.path.with_name('link');link.symlink_to(self.path)
        with self.assertRaises(OSError): check_bundle(link,sha)
    def test_fifo_nonblocking(self):
        fifo=self.path.with_name('fifo');os.mkfifo(fifo)
        with self.assertRaises(ValueError): check_bundle(fifo,'0'*64)
    def test_readonly(self):
        sha=self.write();check_bundle(self.path,sha);self.assertEqual(hashlib.sha256(self.path.read_bytes()).hexdigest(),sha)
    def test_cli_does_not_initialize_queue(self):
        import io,contextlib
        sha=self.write();queue=self.path.with_name('absent.sqlite')
        with contextlib.redirect_stdout(io.StringIO()): main(['--state',str(queue),'preflight-metadata',str(self.path),'--expected-sha256',sha])
        self.assertFalse(queue.exists())

class RangeTests(unittest.TestCase):
    def parity(self,h,l,s,w): self.assertEqual(deque_ranges(h,l,s,w),reference_ranges(h,l,s,w))
    def test_empty(self): self.parity([],[],[],256)
    def test_current_bar_excluded(self): self.assertEqual(deque_ranges([2,9999],[1,-9999],[1,1],256),[None,1])
    def test_session_reset(self): self.assertEqual(deque_ranges([2,99,4,6],[1,-99,3,5],[1,1,2,2],256),[None,1,None,1])
    def test_randomized_parity(self):
        rng=random.Random(42)
        for n in (1,2,255,256,257,513):
            lo=[rng.randrange(-10000,10000) for _ in range(n)];hi=[v+rng.randrange(50) for v in lo];s=[i//79 for i in range(n)]
            for w in (1,2,32,256,3000): self.parity(hi,lo,s,w)
    def test_full_window_expiration_randomized(self):
        rng=random.Random(712);lo=[rng.randrange(-500,500) for _ in range(1536)];hi=[v+rng.randrange(80) for v in lo]
        for w in (1,2,256,500,3000): self.parity(hi,lo,[1]*len(lo),w)
    def test_extreme_expires_exactly(self):
        self.assertEqual(deque_ranges([999,2,3,4],[0,1,2,3],[1]*4,2),[None,999,999,2])
    def test_input_count_bounded(self):
        with self.assertRaises(ValueError): deque_ranges([1]*16385,[0]*16385,[1]*16385,256)
    def test_plateaus_and_negative(self):
        self.parity([0]*600,[-1]*600,[1]*600,256);self.parity(list(range(-600,0)),list(range(-601,-1)),[1]*600,256)
    def test_alignment(self):
        with self.assertRaises(ValueError): deque_ranges([1],[],[1],256)
    def test_noninteger(self):
        with self.assertRaises(ValueError): deque_ranges([True],[0],[1],256)
    def test_backwards_session(self):
        with self.assertRaises(ValueError): deque_ranges([1,2],[0,1],[2,1],256)
    def test_reversed_range(self):
        with self.assertRaises(ValueError): deque_ranges([0],[1],[1],256)
    def test_bounds(self):
        for w in (0,3001,True):
            with self.assertRaises(ValueError): deque_ranges([],[],[],w)
    def test_benchmark_scope(self):
        out=run_benchmark()
        for key in ('market_data_read','active_runner_changed','campaign_speedup_established'): self.assertIs(out[key],False)
        self.assertEqual(len(out['output_sha256']),64)

if __name__=='__main__': unittest.main()
