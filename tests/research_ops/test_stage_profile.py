import unittest, resource, subprocess, sys, json
from unittest.mock import patch
from types import SimpleNamespace
from tools.research_ops.stage_profile import StageProfiler

class StageProfileTests(unittest.TestCase):
    def setUp(self):
        self.child=patch('tools.research_ops.stage_profile._children',return_value=[]);self.child.start()
        self.rss=patch('tools.research_ops.stage_profile.resource.getrusage',side_effect=lambda who:SimpleNamespace(ru_maxrss=0 if who==resource.RUSAGE_CHILDREN else 8192));self.rss.start()
        self.identity=dict(run_id='fixture_run',provider_job_id='fixture_execution',version=1,source_sha256='a'*64,selection_sha256='b'*64,scientific_protocol_sha256='c'*64,engine_build_sha256='d'*64,manifest_sha256='e'*64)
    def tearDown(self):self.child.stop();self.rss.stop()
    def profiler(self):return StageProfiler(identity=self.identity,code_commit='a'*40)
    def test_serial_profile_receipt(self):
        p=self.profiler()
        with p.stage('features'):pass
        with p.stage('serialization'):pass
        r=p.finish();self.assertGreaterEqual(r['unassigned_seconds'],0)
        self.assertEqual(r['memory']['peak_rss_bytes'],8192*1024);self.assertFalse(r['execution_allowed'])
    def test_repeated_substep_aggregates(self):
        p=self.profiler()
        for _ in range(3):
            with p.stage('outcome'):pass
        self.assertEqual(list(p.finish()['stage_seconds']),['outcome'])
    def test_nested_stages_rejected(self):
        p=self.profiler()
        with self.assertRaises(ValueError):
            with p.stage('features'):
                with p.stage('outcome'):pass
        with self.assertRaises(ValueError):p.finish()
    def test_unknown_stage(self):
        p=self.profiler()
        with self.assertRaises(ValueError):
            with p.stage('economic_returns'):pass
    def test_error_not_success_receipt(self):
        p=self.profiler()
        with self.assertRaises(RuntimeError):
            with p.stage('prepare'):raise RuntimeError('failure')
        with self.assertRaises(ValueError):p.finish()
    def test_single_finish(self):
        p=self.profiler();p.finish()
        with self.assertRaises(ValueError):p.finish()
    def test_stage_after_close_rejected(self):
        p=self.profiler();p.finish()
        with self.assertRaises(ValueError):
            with p.stage('features'):pass
    def test_live_child_rejected(self):
        with patch('tools.research_ops.stage_profile._children',return_value=['123']):
            with self.assertRaises(ValueError):self.profiler()
    def test_waited_child_rejected(self):
        p=self.profiler()
        with patch('tools.research_ops.stage_profile.resource.getrusage',return_value=SimpleNamespace(ru_maxrss=10)):
            with self.assertRaises(ValueError):p.finish()
    def test_postfork_pid_rejected(self):
        p=self.profiler();p.pid=-1
        with self.assertRaises(ValueError):p.finish()
    def test_open_stage_not_terminal(self):
        p=self.profiler()
        with p.stage('prepare'):
            with self.assertRaises(ValueError):p.finish()
    def test_identity_unknown_fields(self):
        self.identity['pnl']=1
        with self.assertRaises(ValueError):self.profiler()
    def test_real_fresh_process_instrumentation_synthetic_only(self):
        result=subprocess.run([sys.executable,'-m','tools.research_ops.benchmarks.profile_instrumentation_demo'],capture_output=True,text=True,timeout=15,check=True)
        out=json.loads(result.stdout)
        self.assertEqual(out['status'],'SYNTHETIC_PROFILE_INSTRUMENTATION_PASS_NOT_MNQ_PARITY')
        self.assertEqual(out['expected_units'],out['completed_units'])
        self.assertGreater(out['memory']['peak_rss_bytes'],0)

if __name__=='__main__':unittest.main()