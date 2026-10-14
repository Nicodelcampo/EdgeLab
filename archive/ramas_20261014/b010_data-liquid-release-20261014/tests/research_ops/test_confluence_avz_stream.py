from dataclasses import replace
from unittest.mock import patch
import unittest
import numpy as np
from edgelab.bridge import bars as B
from tools.research_ops.confluence._pinned_total_footprint import build_total_footprint_csr_nt8
from tools.research_ops.confluence.avz_stream import AVZStream,BarFeed
from tools.research_ops.confluence.detector_capture import capture_run,_bar_availability,PINS
from test_confluence_detector_capture import avz_tape


def inputs(t,bar_size=5):
    b=B.build_tick_bars(t,bar_size);f=build_total_footprint_csr_nt8(t,b);ses=B.session_ids(b.end_ns);clocks=_bar_availability(t,b)
    feeds=[];last_members=np.r_[np.flatnonzero(np.diff(b.tick_bar_idx)),len(t)-1]
    for i in range(len(b)):
        cells,vols=f.bar_cells(i);a=clocks[i];last=int(last_members[i])
        feeds.append(BarFeed(i,int(b.end_ns[i]),int(ses[i]),int(b.low_t[i]),int(b.high_t[i]),cells,vols,last,a[1] if a else None))
    return b,f,ses,feeds

class StreamTests(unittest.TestCase):
    def compare(self,params,bar_size=5):
        t=avz_tape();b,f,ses,feeds=inputs(t,bar_size);native,receipt=capture_run('AVZP2',t,bars=b,footprints=f,sessions=ses,params=params)
        stream=AVZStream(params=params,bar_spec=f'tick:{bar_size}');records=[];blocks=[];unavailable=0
        for feed in feeds:
            delta=stream.push(feed);records.extend(delta.records);blocks.extend(delta.blocks);unavailable+=delta.unavailable_events
        self.assertEqual(tuple(records),receipt.records);self.assertEqual(blocks,native['blocks']);self.assertEqual(unavailable,receipt.unavailable_time_events)
        stream.close();return records
    def test_native_events_blocks_exact_both_score_modes_and_ob(self):
        for mode in ('Suma','Densidad'):
            for ob in (0,2,100):
                rs=self.compare({'racimo_min':0,'window_bars':1,'min_samples':2,'lookback_sessions':3,'score_mode':mode,'ob_bars':ob})
                self.assertTrue(rs)
    def test_partial_W_block_survives_feeds_and_resets_at_session(self):
        self.compare({'racimo_min':0,'window_bars':3,'min_samples':2,'lookback_sessions':3,'ob_bars':2},bar_size=3)
    def test_all_32_pilot_avz_configs_match_native_on_fixed_invented_fixture(self):
        import json
        from pathlib import Path
        from tools.research_ops.confluence.pilot_runtime import synthetic_fixture
        from tools.research_ops.confluence._pinned_avzp2 import run
        root=Path(__file__).resolve().parents[2];roster=json.loads((root/'docs/research/ops/MNQ_CONFLUENCE_TARGET_FREE_PILOT_ROSTER.json').read_bytes());t,_=synthetic_fixture();cache={}
        for c in (c for c in roster['configs'] if c['indicator']=='avolzonepoi2'):
            spec=c['bar_spec'];kind,size=spec.split(':');size=int(size)
            if spec not in cache:
                b=B.build_tick_bars(t,size) if kind=='tick' else B.build_time_bars(t,size);f=build_total_footprint_csr_nt8(t,b);ses=B.session_ids(b.end_ns);clocks=_bar_availability(t,b);lasts=np.r_[np.flatnonzero(np.diff(b.tick_bar_idx)),len(t)-1];fs=[]
                for i in range(len(b)):
                    levels,vs=f.bar_cells(i);fs.append(BarFeed(i,int(b.end_ns[i]),int(ses[i]),int(b.low_t[i]),int(b.high_t[i]),levels,vs,int(lasts[i]),clocks[i][1] if clocks[i] else None))
                cache[spec]=(b,f,ses,fs)
            b,f,ses,fs=cache[spec];native,receipt=capture_run('AVZP2',t,bars=b,footprints=f,sessions=ses,params=c['params']);stream=AVZStream(params=c['params'],bar_spec=spec);records=[];blocks=[];unavailable=0
            for feed in fs:
                d=stream.push(feed);records.extend(d.records);blocks.extend(d.blocks);unavailable+=d.unavailable_events
            self.assertEqual(tuple(records),receipt.records,c['config_sha256']);self.assertEqual(blocks,native['blocks'],c['config_sha256']);self.assertEqual(unavailable,receipt.unavailable_time_events);stream.close()
    def test_unknown_eof_availability_is_not_backfilled_by_later_feed(self):
        t=avz_tape();_,_,_,fs=inputs(t);s=AVZStream(params={'racimo_min':0},bar_spec='tick:5');s.push(replace(fs[0],available=None));self.assertTrue(s.closed)
        with self.assertRaises(ValueError):s.push(fs[1])
    def test_caller_buffer_mutation_does_not_change_pending_block(self):
        t=avz_tape();_,_,_,fs=inputs(t);params={'racimo_min':0,'window_bars':2,'min_samples':2,'lookback_sessions':3,'ob_bars':2}
        a=AVZStream(params=params,bar_spec='tick:5');b=AVZStream(params=params,bar_spec='tick:5')
        first=replace(fs[0],levels=fs[0].levels.copy(),volumes=fs[0].volumes.copy());self.assertEqual(a.push(first),b.push(fs[0]));first.volumes[:]=99999
        for feed in fs[1:]:self.assertEqual(a.push(feed),b.push(feed))
    def test_closed_or_poisoned_stream_not_reusable(self):
        t=avz_tape();_,_,_,fs=inputs(t);s=AVZStream(params={'racimo_min':0,'window_bars':1},bar_spec='tick:5',max_history_values=1)
        s.push(fs[0])
        with self.assertRaises(ValueError):s.push(fs[1])
        self.assertTrue(s.poisoned)
        with self.assertRaises(ValueError):s.push(fs[2])
    def test_duplicate_or_retrograde_bar_rejected(self):
        t=avz_tape();_,_,_,fs=inputs(t);s=AVZStream(params={'racimo_min':0},bar_spec='tick:5');s.push(fs[0])
        with self.assertRaises(ValueError):s.push(fs[0])
    def test_native_racimo_not_silently_redefined(self):
        with self.assertRaises(ValueError):AVZStream(params={'racimo_min':5},bar_spec='tick:5')
    def test_parameter_identity_cannot_be_mutated_midstream(self):
        s=AVZStream(params={'racimo_min':0},bar_spec='tick:5')
        with self.assertRaises(TypeError):s.params['bucket_min']=1
    def test_integer_clock_bucket_matches_pandas_at_dst_and_minute_edges(self):
        import pandas as pd
        from datetime import datetime,timezone
        from zoneinfo import ZoneInfo
        base=[int(pd.Timestamp(x).value) for x in ('2026-03-08T07:59:59Z','2026-03-08T08:00:00Z','2026-11-01T07:00:00Z','2026-09-01T14:15:00Z')]
        for ns in [n+d for n in base for d in (-1,0,1)]:
            a=pd.to_datetime(ns,unit='ns',utc=True).tz_convert('America/Chicago');b=datetime.fromtimestamp(ns//1000000000,timezone.utc).astimezone(ZoneInfo('America/Chicago'))
            self.assertEqual((a.hour*60+a.minute)//15,(b.hour*60+b.minute)//15)
    def test_source_drift_rejected(self):
        with patch.dict(PINS,{'AVZP2':'0'*64}):
            with self.assertRaises(ValueError):AVZStream(params={'racimo_min':0},bar_spec='tick:5')
    def test_bad_cells_and_future_availability_rejected(self):
        t=avz_tape();_,_,_,fs=inputs(t);s=AVZStream(params={'racimo_min':0},bar_spec='tick:5')
        with self.assertRaises(ValueError):s.push(replace(fs[0],levels=np.array([101,100])))
        with self.assertRaises(ValueError):s.push(replace(fs[0],available=replace(fs[0].available,ns=fs[0].end_ns-1)))
if __name__=='__main__':unittest.main()
