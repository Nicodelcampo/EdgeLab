from __future__ import annotations
import importlib.util, json, tempfile, unittest
from pathlib import Path
HERE=Path(__file__).resolve(); MOD=HERE.parents[2]/'tools/derive_bt2a_nq_gate1_planning_inputs.py'
spec=importlib.util.spec_from_file_location('planner',MOD); planner=importlib.util.module_from_spec(spec); spec.loader.exec_module(planner)
class TestPlanning(unittest.TestCase):
 def manifest(self,d:Path,firewall=None):
  p=d/'manifest.json'; p.write_text(json.dumps({'status':'READY_CREATION_EVENT_STORE','rows':152695,'sessions_with_events':234,'firewall':firewall or {'holdout':False,'outcomes':False}})); return p
 def test_known_inputs_and_fail_closed_external_blockers(self):
  with tempfile.TemporaryDirectory() as td:
   out=planner.derive(self.manifest(Path(td)),None,None,None,None,1.0,.20,30)
   self.assertEqual(out['event_store']['rows'],152695); self.assertEqual(out['design']['effective_sessions_required_conservative'],51897)
   self.assertEqual(out['status'],'NOT_READY'); self.assertFalse(out['attestation']['OUTCOMES_ACCESSED'])
 def test_complete_inputs_still_block_if_conservative_power_insufficient(self):
  with tempfile.TemporaryDirectory() as td:
   out=planner.derive(self.manifest(Path(td)),None,1000,234,True,1.0,.20,30)
   self.assertEqual(out['K_BT2']['sessions'],234); self.assertIn('effective sessions below conservative finite-support requirement',out['missing_or_blocking'])
 def test_rejects_open_firewall(self):
  with tempfile.TemporaryDirectory() as td:
   with self.assertRaisesRegex(RuntimeError,'firewall'):
    planner.derive(self.manifest(Path(td),{'outcomes':True}),None,None,None,None,1.0,.2,30)
if __name__=='__main__': unittest.main()
