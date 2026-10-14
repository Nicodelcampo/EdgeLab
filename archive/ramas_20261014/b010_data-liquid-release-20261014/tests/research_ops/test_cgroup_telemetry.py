import copy,unittest,os
from unittest.mock import patch
from tools.research_ops.cgroup_telemetry import CgroupAccountingSession,_integer,_pairs,_open_leaf,capability_probe
class CgroupTests(unittest.TestCase):
 def setUp(self):
  self.s={'device':1,'inode':5,'memory_current_bytes':0,'memory_peak_bytes':0,'memory_max_bytes':4096,'pids_current':0,'pids_max':8,'populated':0,'frozen':0,'direct_members':0,'memory_events':{'low':0,'high':0,'max':0,'oom':0,'oom_kill':0}}
  self.a=patch('tools.research_ops.cgroup_telemetry._open_leaf',return_value=99);self.a.start();self.b=patch('tools.research_ops.cgroup_telemetry._snapshot',side_effect=lambda fd:copy.deepcopy(self.s));self.b.start();self.c=patch('tools.research_ops.cgroup_telemetry.os.close');self.close=self.c.start();self.addCleanup(self.a.stop);self.addCleanup(self.b.stop);self.addCleanup(self.c.stop)
 def session(self,**kw):return CgroupAccountingSession('/sys/fs/cgroup/approved',identity_sha256='a'*64,code_commit='b'*40,max_memory_bytes=4096,max_tasks=8,**kw)
 def test_kernel_peak_includes_between_poll_spike(self):
  p=self.session();self.s.update(memory_current_bytes=0,memory_peak_bytes=3072);r=p.finish();self.assertEqual(r['peak_accounted_memory_bytes'],3072);self.assertTrue(r['kernel_counter_not_sampling_peak']);self.assertNotIn('peak_rss_bytes',r);self.assertFalse(r['whole_workload_coverage_attested']);self.assertFalse(r['execution_allowed'])
 def test_multiple_live_members_then_empty(self):
  p=self.session();self.s.update(populated=1,pids_current=4,direct_members=3,memory_current_bytes=2048,memory_peak_bytes=3072);p.poll();self.s.update(populated=0,pids_current=0,direct_members=0,memory_current_bytes=512);self.assertTrue(p.finish()['empty_end_observed'])
 def test_old_peak_not_fresh(self):
  self.s['memory_peak_bytes']=1
  with self.assertRaises(ValueError):self.session()
  self.close.assert_called_once_with(99)
 def test_nonzero_events_not_fresh(self):
  self.s['memory_events']['max']=1
  with self.assertRaises(ValueError):self.session()
 def test_live_begin_not_fresh(self):
  self.s['populated']=1
  with self.assertRaises(ValueError):self.session()
 def test_wrong_cap(self):
  self.s['memory_max_bytes']=8192
  with self.assertRaises(ValueError):self.session()
 def test_unlimited_cap(self):
  self.s['memory_max_bytes']=None
  with self.assertRaises(ValueError):self.session()
 def test_changed_cap_poisoned(self):
  p=self.session();self.s['pids_max']=9
  with self.assertRaises(ValueError):p.poll()
  self.s['pids_max']=8
  with self.assertRaises(ValueError):p.finish()
 def test_changed_inode(self):
  p=self.session();self.s['inode']=6
  with self.assertRaises(ValueError):p.poll()
  p.close()
 def test_reset_peak(self):
  p=self.session();self.s['memory_peak_bytes']=2048;p.poll();self.s['memory_peak_bytes']=1024
  with self.assertRaises(ValueError):p.finish()
 def test_reset_events(self):
  p=self.session();self.s['memory_events']['max']=1;p.poll();self.s['memory_events']['max']=0
  with self.assertRaises(ValueError):p.finish()
 def test_frozen(self):
  p=self.session();self.s['frozen']=1
  with self.assertRaises(ValueError):p.finish()
 def test_oom_is_failure_not_success(self):
  p=self.session();self.s['memory_events']['oom_kill']=1;r=p.finish();self.assertEqual(r['status'],'KERNEL_LIMIT_EVENT_DIAGNOSTIC_NOT_SUCCESS');self.assertFalse(r['workload_success_proven'])
 def test_live_end_rejected(self):
  p=self.session();self.s.update(populated=1,pids_current=1,direct_members=1)
  with self.assertRaises(ValueError):p.finish()
  self.assertTrue(p.closed)
 def test_missing_tasks_at_end(self):
  p=self.session();self.s['pids_current']=1
  with self.assertRaises(ValueError):p.finish()
 def test_cap_exceeded(self):
  p=self.session();self.s['memory_peak_bytes']=4097
  r=p.finish();self.assertEqual(r['peak_accounted_memory_bytes'],4097);self.assertEqual(r['status'],'KERNEL_LIMIT_EVENT_DIAGNOSTIC_NOT_SUCCESS')
 def test_duplicate_finish(self):
  p=self.session();p.finish()
  with self.assertRaises(ValueError):p.finish()
 def test_different_observer_process(self):
  p=self.session();p.owner=-1
  with self.assertRaises(ValueError):p.finish()
 def test_context_exit_no_receipt(self):
  with self.session() as p:pass
  self.assertTrue(p.closed)
 def test_invalid_counter(self):
  for v in ['-1','+1','1.0','01','nan','9223372036854775808']:
   with self.subTest(v=v),self.assertRaises(ValueError):_integer(v)
 def test_max_not_peak(self):
  self.assertIsNone(_integer('max',allow_max=True))
  with self.assertRaises(ValueError):_integer('max')
 def test_duplicate_events(self):
  with self.assertRaises(ValueError):_pairs('oom 0\noom 1')
 def test_real_probe_never_proves_delegation(self):
  r=capability_probe();self.assertFalse(r['mutations_performed']);self.assertFalse(r['delegated_job_leaf_proven']);self.assertFalse(r['rss_measurement'])

 def test_poll_return_cannot_mutate_internal_counter_history(self):
  p=self.session();self.s['memory_events']['max']=1;v=p.poll();v['memory_events']['max']=0;self.s['memory_events']['max']=0
  with self.assertRaises(ValueError):p.finish()
 def test_root_never_used_as_job_leaf(self):
  with self.assertRaises(ValueError):_open_leaf('/sys/fs/cgroup')
 def test_traversal_and_relative_paths(self):
  for path in ['leaf','/sys/fs/cgroup/../other','/tmp/leaf']:
   with self.subTest(path=path),self.assertRaises(ValueError):_open_leaf(path)

class KernelInterfaceFixtureTests(unittest.TestCase):
 def setUp(self):
  import tempfile
  from pathlib import Path
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.addCleanup(self.temp.cleanup)
  self.values={'memory.events':'low 0\nhigh 0\nmax 0\noom 0\noom_kill 0\n','cgroup.events':'populated 0\nfrozen 0\n','cgroup.procs':'','memory.current':'0','memory.peak':'0','memory.max':'4096','pids.current':'0','pids.max':'8'}
  for name,value in self.values.items():(self.root/name).write_text(value)
 def snap(self):
  from tools.research_ops.cgroup_telemetry import _snapshot
  fd=os.open(self.root,os.O_RDONLY|os.O_DIRECTORY)
  try:return _snapshot(fd)
  finally:os.close(fd)
 def test_real_fd_reads_fixture_not_kernel_proof(self):self.assertEqual(self.snap()['memory_max_bytes'],4096)
 def test_subgroups_rejected(self):
  (self.root/'child').mkdir()
  with self.assertRaises(ValueError):self.snap()
 def test_symlink_interface(self):
  p=self.root/'memory.peak';p.unlink();p.symlink_to(self.root/'memory.current')
  with self.assertRaises(OSError):self.snap()
 def test_incomplete_event_scope(self):
  (self.root/'memory.events').write_text('low 0')
  with self.assertRaises(ValueError):self.snap()
 def test_inconsistent_current_peak(self):
  (self.root/'memory.current').write_text('2048');(self.root/'memory.peak').write_text('1024')
  with self.assertRaises(ValueError):self.snap()
 def test_invalid_members(self):
  (self.root/'cgroup.procs').write_text('7\n7');(self.root/'pids.current').write_text('2')
  with self.assertRaises(ValueError):self.snap()
 def test_short_interface_read_bounded(self):
  (self.root/'memory.events').write_text('x'*20000)
  with self.assertRaises(ValueError):self.snap()
 def test_pids_current_includes_threads(self):
  (self.root/'cgroup.procs').write_text('7');(self.root/'pids.current').write_text('3');(self.root/'cgroup.events').write_text('populated 1\nfrozen 0');self.assertEqual(self.snap()['pids_current'],3)
