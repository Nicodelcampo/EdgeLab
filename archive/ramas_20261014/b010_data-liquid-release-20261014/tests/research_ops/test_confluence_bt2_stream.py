import hashlib,json
from pathlib import Path
from dataclasses import replace
from unittest.mock import patch
import unittest
import numpy as np
from edgelab.bridge import bars as B
from tools.research_ops.confluence.bt2_stream import BT2Stream,AggressiveBar
from tools.research_ops.confluence.detector_capture import capture_run,_bar_availability,PINS
from test_confluence_detector_capture import trap_tape

def inputs(t,kind,size):
    b=B.build_tick_bars(t,size) if kind=='tick' else B.build_time_bars(t,size);fp=B.build_footprints(t,b);clocks=_bar_availability(t,b);lasts=np.r_[np.flatnonzero(np.diff(b.tick_bar_idx)),len(t)-1]
    return b,fp,[AggressiveBar(i,int(b.end_ns[i]),int(b.low_t[i]),int(b.high_t[i]),int(b.close_t[i]),float(b.volume[i]),fp.ask[i],fp.bid[i],int(fp.n_quote[i]),int(fp.n_rule[i]),int(lasts[i]),clocks[i][1] if clocks[i] else None) for i in range(len(b))]

class BT2StreamTests(unittest.TestCase):
    def compare(self,t,params,kind='tick',size=10):
        b,f,fs=inputs(t,kind,size);native,r=capture_run('BT2',t,bars=b,footprints=f,params=params);s=BT2Stream(params=params,bar_spec=f'{kind}:{size}',tick_size=t.tick_size,collect_diagnostics=True);records=[];unavailable=0
        for feed in fs:d=s.push(feed);records.extend(d.records);unavailable+=d.unavailable_events
        self.assertEqual(tuple(records),r.records);self.assertEqual(unavailable,r.unavailable_time_events)
        h=hashlib.sha256()
        for line in native['csv_lines']:
            _,_,kind,payload=line.split('|',3);h.update(f'{kind}|{payload}\n'.encode())
        self.assertEqual(s.log_hash.hexdigest(),h.hexdigest());self.assertEqual(s.log_count,len(native['csv_lines']))
        return s,records
    def test_native_events_and_diagnostics_exact(self):
        for mode in ('CloseThrough','FirstTouch','None'):
            s,rs=self.compare(trap_tape(121),{'use_wick_filter':False,'imbalance_ratio':1.,'min_trap_volume':1.,'invalidation_mode':mode,'max_age_bars':1})
            self.assertTrue(rs)
    def test_session_partial_and_unknown_eof(self):
        t=trap_tape(57);t.ts_ns[21:]+=86400000000000
        s,rs=self.compare(t,{'use_wick_filter':False,'imbalance_ratio':1.,'min_trap_volume':1.})
        self.assertTrue(s.closed);self.assertTrue(any(r.clock.sequence>r.consumed_tick_index for r in rs))
    def test_timebars_available_after_close(self):
        t=trap_tape(181);t.ts_ns=t.ts_ns[0]+np.arange(len(t),dtype=np.int64)*1000000000
        self.compare(t,{'use_wick_filter':False,'imbalance_ratio':1.,'min_trap_volume':1.},'time',1)
    def test_all_32_roster_configs(self):
        from tools.research_ops.confluence.pilot_runtime import synthetic_fixture
        t,_=synthetic_fixture();roster=json.loads((Path(__file__).resolve().parents[2]/'docs/research/ops/MNQ_CONFLUENCE_TARGET_FREE_PILOT_ROSTER.json').read_bytes())
        for c in (x for x in roster['configs'] if x['indicator']=='bigtrap2'):
            kind,size=c['bar_spec'].split(':')
            with self.subTest(config=c['config_sha256']):
                s,_=self.compare(t,c['params'],kind,int(size));self.assertEqual(s.config,c['config_sha256'])
    def test_first_bar_skipped_same_as_native(self):
        s,rs=self.compare(trap_tape(10),{'use_wick_filter':False,'imbalance_ratio':1.,'min_trap_volume':1.});self.assertFalse(rs);self.assertEqual(s.log_count,0)
    def test_invalid_and_duplicate_feed_before_state_change(self):
        _,_,fs=inputs(trap_tape(30),'tick',10);s=BT2Stream(params={},bar_spec='tick:10',tick_size=.25);s.push(fs[0])
        with self.assertRaises(ValueError):s.push(fs[0])
        with self.assertRaises(ValueError):s.push(replace(fs[1],volume=-1.))
        self.assertFalse(s.poisoned);s.push(fs[1])
    def test_capacity_failure_poisoned(self):
        _,_,fs=inputs(trap_tape(41),'tick',10);s=BT2Stream(params={'use_wick_filter':False,'imbalance_ratio':1.,'min_trap_volume':1.,'invalidation_mode':'None','max_age_bars':0},bar_spec='tick:10',tick_size=.25,max_active=1)
        s.push(fs[0]);s.push(fs[1])
        with self.assertRaises(ValueError):s.push(fs[2])
        self.assertTrue(s.poisoned)
    def test_no_csv_fast_path_preserves_receipts(self):
        t=trap_tape(57);t.ts_ns[21:]+=86400000000000;p={'use_wick_filter':False,'imbalance_ratio':1.,'min_trap_volume':1.}
        b,f,fs=inputs(t,'tick',10);_,ref=capture_run('BT2',t,bars=b,footprints=f,params=p);s=BT2Stream(params=p,bar_spec='tick:10',tick_size=.25);rs=[];u=0
        for feed in fs:d=s.push(feed);rs.extend(d.records);u+=d.unavailable_events
        self.assertEqual(tuple(rs),ref.records);self.assertEqual(u,ref.unavailable_time_events);self.assertEqual(s.log_count,0)
    def test_source_drift_and_renderer_rejected(self):
        with patch.dict(PINS,{'BT2':'0'*64}):
            with self.assertRaises(ValueError):BT2Stream(params={},bar_spec='tick:10',tick_size=.25)
        with self.assertRaises(ValueError):BT2Stream(params={'AutoScale':True},bar_spec='tick:10',tick_size=.25)
if __name__=='__main__':unittest.main()
