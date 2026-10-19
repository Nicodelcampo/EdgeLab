"""All three stateful detectors -> identical racimos/episodes/arrivals, invented only."""
from dataclasses import replace
import unittest
import numpy as np
from edgelab.bridge import bars as B
from tools.research_ops.confluence.bt2a_stream import BT2AStream
from tools.research_ops.confluence.bt2_stream import BT2Stream
from tools.research_ops.confluence.avz_stream import AVZStream
from tools.research_ops.confluence.replay import replay_declared
from test_confluence_bt2a_stream import chunk
from test_confluence_bt2_stream import inputs as bt_inputs
from test_confluence_avz_stream import inputs as av_inputs
from test_confluence_detector_pipeline import fixture,H

BT={'use_wick_filter':False,'imbalance_ratio':1,'min_trap_volume':1}
BA={'TapeWindowTicks':5,'AbsorptionPct':0,'UseWickFilter':False,'ImbalanceRatio':1,'MinStackedRows':1,'MinTrapFrac':0,'RequireFlowSideMatch':False}
AV={'window_bars':1,'min_samples':2,'lookback_sessions':3,'racimo_min':0,'ob_bars':2}

class StreamPipelineTests(unittest.TestCase):
    def stream_receipts(self,t,refs,chunk_size):
        bt=BT2Stream(params=BT,bar_spec='tick:5',tick_size=.25);ba=BT2AStream(params=BA,tick_size=.25);av=AVZStream(params=AV,bar_spec='tick:5');receipts=[]
        _,_,bfs=bt_inputs(t,'tick',5);_,_,_,afs=av_inputs(t,5)
        for stream,feeds,ref in ((bt,bfs,refs[0]),(av,afs,refs[2])):
            rs=[];u=0
            for feed in feeds:
                d=stream.push(feed);rs.extend(d.records);u+=d.unavailable_events
            receipts.append(replace(ref,records=tuple(rs),unavailable_time_events=u))
        rs=[];u=0
        for pos in range(0,len(t),chunk_size):
            d=ba.push(chunk(t,pos,min(len(t),pos+chunk_size)));rs.extend(d.records);u+=d.unavailable_events
        d=ba.finish();rs.extend(d.records);u+=d.unavailable_events;receipts.insert(1,replace(refs[1],records=tuple(rs),unavailable_time_events=u));av.close()
        self.assertEqual(tuple(receipts),refs);self.assertEqual(bt.log_count+ba.log_count,0)
        return receipts
    def test_three_families_generate_identical_racimos_triples_and_arrivals(self):
        t,refs,dates=fixture();kw=dict(contract='SYN',tape_sha256=H,trade_dates=dates,racimo_params=[{'racimo_min':3,'racimo_bars':10,'racimo_altura_ticks':10}],window_ticks=3)
        expected=list(replay_declared(t,refs,**kw));self.assertTrue(any(len(e.episode.components)==3 for f in expected for e in f.episode_events))
        self.assertTrue(any(f.arrivals for f in expected))
        for cut in (1,7,21,80):
            got=self.stream_receipts(t,refs,cut);self.assertEqual(list(replay_declared(t,got,**kw)),expected)
    def test_no_chunk_boundary_creates_a_new_detector_identity(self):
        t,refs,_=fixture();a=self.stream_receipts(t,refs,3);b=self.stream_receipts(t,refs,80)
        self.assertEqual(a,b);self.assertEqual({r.parameter_sha256 for r in a},{r.parameter_sha256 for r in refs})
if __name__=='__main__':unittest.main()
