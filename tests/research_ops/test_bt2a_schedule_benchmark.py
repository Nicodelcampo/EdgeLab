import json,unittest
from pathlib import Path
from tools.research_ops.confluence.bt2a_schedule_benchmark import measure
import test_cross_family_streaming as streaming_tests
from tools.research_ops.confluence.cross_family_pilot import ROSTER
class ScheduleTests(unittest.TestCase):
 def test_exact_native_capture_history_and_residual_same_tape(self):
  h=streaming_tests.StreamingTests();h.setUp();st=h.tapes(days=2)[1];configs=[c for c in h.roster['configs'] if c['indicator']=='bigtrap2absorption']
  a=measure(st,configs,.25,schedule='PROFILE_SEQUENTIAL');b=measure(st,configs,.25,schedule='CHUNK_INTERLEAVED');self.assertEqual(a['profiles'],b['profiles']);self.assertFalse(b['cache']['native_history_shared'])
  with self.assertRaises(ValueError):measure(st,configs,.25,schedule='UNKNOWN')
