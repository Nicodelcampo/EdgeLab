"""Target-free synthetic contract tests; no cloud, market data or live writer."""
import unittest
from dataclasses import asdict, replace
from tools.research_ops.store import digest
from tools.research_ops.post_run import RunObservation, BenchmarkPolicy, BenchmarkPair, plan_post_run, assess_benchmark


class PostRunTests(unittest.TestCase):
    def run_fixture(self):
        return RunObservation('run_1','job_1',1,'COMPLETE','a'*64,'b'*64,'c'*64,'d'*64,'e'*64,'f'*64,
                              100,512,10,10,(('prepare',20),('scan',60),('export',10)),'PASS')
    def pairs(self):
        return tuple(BenchmarkPair(f'{s}_{i}',s,'a'*64,'b'*64,'c'*64,'d'*64,'d'*64,
                                   10,8,1024,900,10,10,10)
                     for s in ('cold','warm') for i in range(3))
    def assess(self, pairs=None, policy=None):
        p=policy or BenchmarkPolicy()
        return assess_benchmark(p,self.pairs() if pairs is None else pairs,expected_policy_sha256=digest(asdict(p)))
    def test_success_is_proposal_only(self):
        x=plan_post_run(self.run_fixture()); self.assertEqual(x['status'],'READY_FOR_TECHNICAL_REVIEW')
        for f in ('execution_allowed','activation_allowed','holdout_allowed','ledger_modified','provenance_attested'):
            self.assertIs(x[f],False)
        self.assertEqual(x['canonical_handoff']['confidence'],'LOW')
    def test_deterministic_and_idempotency_key(self):
        a=plan_post_run(self.run_fixture()); b=plan_post_run(self.run_fixture());self.assertEqual(a,b)
    def test_new_receipt_new_key(self):
        a=plan_post_run(self.run_fixture());b=plan_post_run(replace(self.run_fixture(),receipt_sha256='1'*64))
        self.assertNotEqual(a['idempotency_key'],b['idempotency_key'])
    def test_new_version_new_key(self):
        self.assertNotEqual(plan_post_run(self.run_fixture())['idempotency_key'],plan_post_run(replace(self.run_fixture(),version=2))['idempotency_key'])
    def test_rank_telemetry_and_unassigned_time(self):
        p=plan_post_run(self.run_fixture());self.assertEqual(p['measured_stage_order'],['scan','prepare','export']);self.assertEqual(p['unassigned_wall_seconds'],10)
    def test_failed_retained_not_performance_ready(self):
        p=plan_post_run(replace(self.run_fixture(),state='FAILED',failure='OOM',completed_units=2))
        self.assertEqual(p['status'],'REPAIR_OR_VERIFY_FIRST');self.assertEqual(p['canonical_handoff']['kind'],'FAILURE_OR_REPAIR_DRAFT')
    def test_cancelled_retained(self):
        self.assertEqual(plan_post_run(replace(self.run_fixture(),state='CANCELLED',failure='CANCELLED'))['status'],'REPAIR_OR_VERIFY_FIRST')
    def test_incomplete_blocks(self):
        self.assertEqual(plan_post_run(replace(self.run_fixture(),completed_units=9))['status'],'REPAIR_OR_VERIFY_FIRST')
    def test_unverified_blocks(self):
        self.assertEqual(plan_post_run(replace(self.run_fixture(),integrity='UNVERIFIED'))['status'],'REPAIR_OR_VERIFY_FIRST')
    def test_failed_integrity_blocks(self):
        self.assertEqual(plan_post_run(replace(self.run_fixture(),integrity='FAIL'))['status'],'REPAIR_OR_VERIFY_FIRST')
    def test_running_rejected(self):
        with self.assertRaises(ValueError):plan_post_run(replace(self.run_fixture(),state='RUNNING'))
    def test_unknown_failure_rejected(self):
        with self.assertRaises(ValueError):plan_post_run(replace(self.run_fixture(),failure='execute_shell'))
    def test_conflicting_terminal_state(self):
        with self.assertRaises(ValueError):plan_post_run(replace(self.run_fixture(),state='FAILED'))
    def test_nonfinite_and_bool_rejected(self):
        for v in (float('nan'),float('inf'),True,-1,0):
            with self.subTest(v=v),self.assertRaises(ValueError):plan_post_run(replace(self.run_fixture(),wall_seconds=v))
    def test_overlapping_stage_times_rejected(self):
        with self.assertRaises(ValueError):plan_post_run(replace(self.run_fixture(),stages=(('scan',101),)))
    def test_duplicate_stages_rejected(self):
        with self.assertRaises(ValueError):plan_post_run(replace(self.run_fixture(),stages=(('scan',1),('scan',1))))
    def test_invalid_identity_rejected(self):
        with self.assertRaises(ValueError):plan_post_run(replace(self.run_fixture(),source_sha256='bad'))
    def test_positive_screen_never_approves(self):
        x=self.assess();self.assertEqual(x['status'],'TECHNICAL_REVIEW_CANDIDATE_NOT_APPROVED')
        for k in ('execution_allowed','activation_allowed','ledger_modified','independent_parity_attested','attempt_completeness_attested','scientific_advantage_claimed'):
            self.assertIs(x[k],False)
    def test_warm_only_blocks(self):
        self.assertIn('INCOMPLETE_OR_EXTRA_REGISTERED_ATTEMPTS',self.assess(self.pairs()[3:])['blockers'])
    def test_parity_mismatch(self):
        a=self.pairs();a=(replace(a[0],candidate_output_sha256='e'*64),)+a[1:]
        self.assertIn('OUTPUT_PARITY_MISMATCH',self.assess(a)['blockers'])
    def test_missing_coverage(self):
        a=self.pairs();a=(replace(a[0],candidate_units=9),)+a[1:]
        self.assertIn('COVERAGE_MISMATCH',self.assess(a)['blockers'])
    def test_failed_attempt_cannot_disappear(self):
        a=self.pairs();a=(replace(a[0],state='FAILED'),)+a[1:]
        self.assertIn('FAILED_OR_CANCELLED_ATTEMPT',self.assess(a)['blockers'])
    def test_one_regression_cannot_hide_in_median(self):
        a=self.pairs();a=(replace(a[0],candidate_seconds=12),)+a[1:]
        self.assertIn('PAIR_TIME_REGRESSION',self.assess(a)['blockers'])
    def test_memory_regression(self):
        a=self.pairs();a=(replace(a[0],candidate_peak_rss_bytes=1025),)+a[1:]
        self.assertIn('MEMORY_REGRESSION_OR_CAP',self.assess(a)['blockers'])
    def test_memory_cap(self):
        self.assertIn('MEMORY_REGRESSION_OR_CAP',self.assess(policy=replace(BenchmarkPolicy(),peak_rss_cap_bytes=899))['blockers'])
    def test_insufficient_speedup(self):
        self.assertIn('INSUFFICIENT_STRATUM_SPEEDUP',self.assess(tuple(replace(p,candidate_seconds=10) for p in self.pairs()))['blockers'])
    def test_different_environment_blocks(self):
        a=self.pairs();a=(replace(a[0],comparison_identity_sha256='e'*64),)+a[1:]
        self.assertIn('COMPARISON_IDENTITY_OR_BUILD_MISMATCH',self.assess(a)['blockers'])
    def test_build_switch_blocks(self):
        a=self.pairs();a=(replace(a[0],candidate_build_sha256='e'*64),)+a[1:]
        self.assertIn('COMPARISON_IDENTITY_OR_BUILD_MISMATCH',self.assess(a)['blockers'])
    def test_duplicate_attempt_rejected(self):
        with self.assertRaises(ValueError):self.assess(self.pairs()+(self.pairs()[0],))
    def test_extra_attempt_not_selectively_accepted(self):
        self.assertIn('INCOMPLETE_OR_EXTRA_REGISTERED_ATTEMPTS',self.assess(self.pairs()+(replace(self.pairs()[0],pair_id='extra'),))['blockers'])
    def test_unregistered_stratum(self):
        with self.assertRaises(ValueError):self.assess((replace(self.pairs()[0],stratum='new'),))
    def test_budget_screen(self):
        self.assertIn('DECLARED_WALL_BUDGET_EXCEEDED',self.assess(policy=replace(BenchmarkPolicy(),max_total_wall_seconds=100))['blockers'])
    def test_policy_tamper(self):
        with self.assertRaises(ValueError):assess_benchmark(BenchmarkPolicy(),self.pairs(),expected_policy_sha256='f'*64)
    def test_threshold_cannot_be_relaxed(self):
        with self.assertRaises(ValueError):self.assess(policy=replace(BenchmarkPolicy(),min_median_speedup=1))
    def test_bad_attempt_numeric_rejected(self):
        with self.assertRaises(ValueError):self.assess((replace(self.pairs()[0],candidate_seconds=float('nan')),))
    def test_bool_counts_rejected(self):
        with self.assertRaises(ValueError):self.assess((replace(self.pairs()[0],candidate_units=True),))

    def test_zero_rss_is_not_a_measurement(self):
        with self.assertRaises(ValueError):self.assess((replace(self.pairs()[0],candidate_peak_rss_bytes=0),))
        with self.assertRaises(ValueError):plan_post_run(replace(self.run_fixture(),peak_rss_bytes=0))
    def test_excessive_budget_rejected(self):
        with self.assertRaises(ValueError):self.assess(policy=replace(BenchmarkPolicy(),max_total_wall_seconds=3601))
    def test_different_work_census_blocks(self):
        a=self.pairs();a=(replace(a[0],expected_units=11,baseline_units=11,candidate_units=11),)+a[1:]
        self.assertIn('COMPARISON_IDENTITY_OR_BUILD_MISMATCH',self.assess(a)['blockers'])

if __name__=='__main__':unittest.main()
