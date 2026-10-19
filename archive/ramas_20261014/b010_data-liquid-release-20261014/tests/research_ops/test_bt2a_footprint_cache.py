import unittest,json,time
from pathlib import Path
from dataclasses import replace
import numpy as np
from tools.research_ops.confluence.bt2a_footprint_cache import BucketFootprintCache
from tools.research_ops.confluence.bt2a_stream import BT2AStream
from test_confluence_bt2a_stream import chunk,PERMISSIVE
from test_confluence_detector_capture import trap_tape
class CacheTests(unittest.TestCase):
 def test_exact_capture_history_diagnostic_across_ticksizes_and_boundaries(self):
  for size in (.25,.1,.00005,.03125):
   t=trap_tape(607);t.ts_ns[204:]+=86400000000000;t.ts_ns[401:]+=86400000000000;cache=BucketFootprintCache(max_entries=32,max_cells=1000)
   for params in (PERMISSIVE,{**PERMISSIVE,'TapeWindowTicks':25,'AbsorptionPct':50.,'MinHistoryBuckets':10,'AbsorptionLookback':50,'ScoreMode':'AbsMagnitude'},{**PERMISSIVE,'TapeWindowTicks':50,'ScoreMode':'AbsDirectional'}):
    streams=[BT2AStream(params=params,tick_size=size,collect_diagnostics=True,footprint_cache=c) for c in (None,cache)];rs=[[],[]];u=[0,0]
    for begin in range(0,len(t),17):
     for j,s in enumerate(streams):d=s.push(chunk(t,begin,min(begin+17,len(t))));rs[j].extend(d.records);u[j]+=d.unavailable_events
    for j,s in enumerate(streams):d=s.finish();rs[j].extend(d.records);u[j]+=d.unavailable_events
    self.assertEqual(rs[0],rs[1]);self.assertEqual(u[0],u[1]);self.assertEqual(streams[0].state_sizes(),streams[1].state_sizes());self.assertEqual(streams[0].log_hash.hexdigest(),streams[1].log_hash.hexdigest())
 def test_content_binding_mutation_and_readonly_results(self):
  c=BucketFootprintCache();p=np.array([100,100,101]);v=np.array([1.,2.,3.]);b=p-1;a=p
  r=c.prepare(p,v,b,a);self.assertEqual(c.prepare(p,v,b,a),r);self.assertEqual(c.hits,1)
  with self.assertRaises(TypeError):r[0][100]=999
  v[0]=5.;z=c.prepare(p,v,b,a);self.assertNotEqual(dict(r[0]),dict(z[0]));self.assertEqual(c.misses,2)
 def test_bounded_eviction_recomputes_not_truncates(self):
  c=BucketFootprintCache(max_entries=1,max_cells=1);p=np.array([100]);v=np.array([1.]);r=c.prepare(p,v,p-1,p);c.prepare(p+1,v,p,p+1);self.assertEqual(c.prepare(p,v,p-1,p),r);self.assertGreater(c.evictions,0);self.assertLessEqual(c.cells,1)
 def test_bad_inputs_and_foreign_cache_rejected(self):
  with self.assertRaises(ValueError):BucketFootprintCache(max_entries=0)
  with self.assertRaises(ValueError):BucketFootprintCache().prepare(np.array([1]),np.array([float('nan')]),np.array([1]),np.array([2]))
  with self.assertRaises(ValueError):BT2AStream(params={},tick_size=.25,footprint_cache={})
