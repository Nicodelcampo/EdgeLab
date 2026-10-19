import json,hashlib,tempfile,unittest
from pathlib import Path
from tools.research_ops.audits.review_cgroup_capability import review,PROGRAMS
class CapabilityReviewTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.path=Path(self.temp.name)/'probe.json';self.programs={p:'c'*64 for p in PROGRAMS};self.p={'schema':'research_ops_cgroup_capability_probe_v1','linux':True,'cgroup2_mount_verified':True,'memory_peak_readable':True,'memory_controller_available':True,'mount_readonly':True,'directory_write_access_hint':False,'self_scope_sha256':'a'*64,'delegated_job_leaf_proven':False,'whole_workload_coverage_attested':False,'rss_measurement':False,'execution_allowed':False,'mutations_performed':False,'source_checkpoint':'b'*40,'program_sha256':self.programs,'wall_seconds':.05}
 def call(self):
  b=json.dumps(self.p).encode();self.path.write_bytes(b);return review(self.path,expected_sha256=hashlib.sha256(b).hexdigest(),expected_source_commit='b'*40,expected_program_sha256=self.programs)
 def test_readable_readonly_does_not_authorize(self):
  r=self.call();self.assertTrue(r['counter_interface_available']);self.assertFalse(r['approved_job_scope_bound']);self.assertFalse(r['production_receiver_compatible'])
 def test_write_hint_not_permission(self):
  self.p['mount_readonly']=False;self.p['directory_write_access_hint']=True;self.assertFalse(self.call()['execution_allowed'])
 def test_missing_interface(self):
  self.p.update(linux=False,cgroup2_mount_verified=False,memory_peak_readable=False,memory_controller_available=False,mount_readonly=None,self_scope_sha256=None,probe_incomplete=True);self.assertFalse(self.call()['counter_interface_available'])
 def test_autoapproval_rejected(self):
  self.p['execution_allowed']=True
  with self.assertRaises(ValueError):self.call()
 def test_wrong_source(self):
  self.p['source_checkpoint']='d'*40
  with self.assertRaises(ValueError):self.call()
 def test_unknown_field(self):
  self.p['peak_rss_bytes']=999
  with self.assertRaises(ValueError):self.call()
 def test_boolean_alias(self):
  self.p['rss_measurement']=0
  with self.assertRaises(ValueError):self.call()
 def test_malformed_time(self):
  self.p['wall_seconds']=31
  with self.assertRaises(ValueError):self.call()
