"""Offline, finite post-run planning and benchmark screening, NOT a supervisor.
No network, code execution, canonical-memory writes, deployment or scientific
adjudication. Input hashes/telemetry are declarations; the trusted host must
verify their provenance, completeness and freshness before using this output.
"""
from dataclasses import dataclass, asdict
from math import isfinite
from statistics import median
from .store import digest, HEX, ID


def _sha(v):
    if not isinstance(v, str) or not HEX.fullmatch(v):
        raise ValueError('lowercase SHA256 required')


def _id(v):
    if not isinstance(v, str) or not ID.fullmatch(v):
        raise ValueError('bounded operational ID required')


def _number(v, positive=False):
    if type(v) not in (int, float) or not isfinite(v) or v < 0 or (positive and v == 0):
        raise ValueError('finite nonnegative numeric telemetry required')


@dataclass(frozen=True)
class RunObservation:
    run_id: str
    provider_job_id: str
    version: int
    state: str
    source_sha256: str
    selection_sha256: str
    scientific_protocol_sha256: str
    engine_build_sha256: str
    manifest_sha256: str
    receipt_sha256: str
    wall_seconds: float
    peak_rss_bytes: int
    expected_units: int
    completed_units: int
    stages: tuple  # Nonoverlapping serial (closed stage ID, seconds) spans only.
    integrity: str = 'UNVERIFIED'
    failure: str = 'NONE'

    def validate(self):
        for v in (self.run_id, self.provider_job_id):
            _id(v)
        for v in (self.source_sha256, self.selection_sha256,
                  self.scientific_protocol_sha256, self.engine_build_sha256,
                  self.manifest_sha256, self.receipt_sha256):
            _sha(v)
        if type(self.version) is not int or self.version < 1:
            raise ValueError('explicit immutable job version required')
        if self.state not in ('COMPLETE', 'FAILED', 'CANCELLED'):
            raise ValueError('terminal run only; RUNNING must not be learned as complete')
        if self.integrity not in ('PASS', 'FAIL', 'UNVERIFIED'):
            raise ValueError('closed integrity state required')
        if self.failure not in ('NONE', 'OOM', 'TIMEOUT', 'INTEGRITY', 'PARITY', 'INFRA', 'CANCELLED', 'UNKNOWN'):
            raise ValueError('closed failure code required')
        if self.state != 'COMPLETE' and self.failure == 'NONE':
            raise ValueError('failed/cancelled run needs a failure code')
        if self.state == 'COMPLETE' and self.failure != 'NONE':
            raise ValueError('conflicting terminal state')
        _number(self.wall_seconds, positive=True)
        if type(self.peak_rss_bytes) is not int or self.peak_rss_bytes <= 0:
            raise ValueError('integer peak RSS required')
        if any(type(v) is not int for v in (self.expected_units, self.completed_units)):
            raise ValueError('integer work-unit census required')
        if not 0 <= self.completed_units <= self.expected_units or self.expected_units < 1:
            raise ValueError('invalid work-unit census')
        if type(self.stages) is not tuple or len(self.stages) > 32:
            raise ValueError('bounded immutable stage telemetry required')
        names = set()
        for stage in self.stages:
            if type(stage) is not tuple or len(stage) != 2:
                raise ValueError('stage pair required')
            name, seconds = stage
            _id(name); _number(seconds)
            if name in names:
                raise ValueError('duplicate stage')
            names.add(name)
        if sum(t for _, t in self.stages) > self.wall_seconds + 1e-6:
            raise ValueError('overlapping stage spans require a separate trace, not this schema')


def plan_post_run(observation):
    observation.validate()
    ready = (observation.state == 'COMPLETE' and observation.integrity == 'PASS'
             and observation.completed_units == observation.expected_units)
    ordered = sorted(observation.stages, key=lambda x: (-x[1], x[0]))
    # Idempotency is a key, not durable enforcement or writer authorization.
    key = digest([observation.provider_job_id, observation.version, observation.receipt_sha256])
    out = dict(
        schema='research_ops_post_run_v1', status='READY_FOR_TECHNICAL_REVIEW' if ready else 'REPAIR_OR_VERIFY_FIRST',
        observation=asdict(observation), idempotency_key=key,
        measured_stage_order=[s for s, _ in ordered],
        unassigned_wall_seconds=observation.wall_seconds-sum(t for _, t in observation.stages),
        actions=(['RECALL_CANONICAL_OPERATIONAL_LESSONS_AND_INVALIDATIONS',
                  'REVIEW_MEASURED_STAGES_AND_RESOURCE_BOUNDS',
                  'PROPOSE_AT_MOST_ONE_SEMANTICS_PRESERVING_CHANGE',
                  'PREREGISTER_FINITE_BENCHMARK_AND_PARITY_PLAN'] if ready else
                 ['PRESERVE_FAILURE_OR_INCOMPLETE_RECEIPT', 'VERIFY_OR_REPAIR_BEFORE_PERFORMANCE_CLAIMS']),
        canonical_handoff=dict(kind='TECHNICAL_LESSON_DRAFT' if ready else 'FAILURE_OR_REPAIR_DRAFT',
                              status='PROPOSED', confidence='LOW', evidence_receipt_sha256=observation.receipt_sha256,
                              outcome_values_included=False, writer_attached=False,
                              requires='reviewed operational episode + canonical writer + verified custody'),
        scientific_learning='SEPARATE_CANONICAL_ADJUDICATION_NOT_IMPLEMENTED',
        provenance_attested=False, idempotency_enforced=False,
        execution_allowed=False, activation_allowed=False, holdout_allowed=False,
        ledger_modified=False, network_executed=False)
    out['plan_sha256'] = digest(out)
    return out


@dataclass(frozen=True)
class BenchmarkPolicy:
    strata: tuple = ('cold', 'warm')
    pairs_per_stratum: int = 3
    min_median_speedup: float = 1.05
    max_pair_slowdown: float = 1.05
    peak_rss_cap_bytes: int = 1_073_741_824
    max_total_wall_seconds: float = 3600

    def validate(self):
        if type(self.strata) is not tuple or not 1 <= len(self.strata) <= 8 or len(set(self.strata)) != len(self.strata):
            raise ValueError('unique frozen strata required')
        for s in self.strata: _id(s)
        if type(self.pairs_per_stratum) is not int or not 3 <= self.pairs_per_stratum <= 10:
            raise ValueError('3..10 preregistered pairs per stratum required')
        for v in (self.min_median_speedup, self.max_pair_slowdown, self.max_total_wall_seconds): _number(v, True)
        if self.max_total_wall_seconds > 3600:
            raise ValueError('offline benchmark policy wall cap exceeded')
        if self.min_median_speedup < 1.05 or not 1 <= self.max_pair_slowdown <= 1.05:
            raise ValueError('conservative fixed technical thresholds required')
        if type(self.peak_rss_cap_bytes) is not int or self.peak_rss_cap_bytes <= 0:
            raise ValueError('finite integer memory cap required')


@dataclass(frozen=True)
class BenchmarkPair:
    pair_id: str
    stratum: str
    comparison_identity_sha256: str  # Same source/selection/protocol/environment/workload.
    baseline_build_sha256: str
    candidate_build_sha256: str
    baseline_output_sha256: str
    candidate_output_sha256: str
    baseline_seconds: float
    candidate_seconds: float
    baseline_peak_rss_bytes: int
    candidate_peak_rss_bytes: int
    expected_units: int
    baseline_units: int
    candidate_units: int
    state: str = 'COMPLETE'

    def validate(self):
        _id(self.pair_id); _id(self.stratum)
        for v in (self.comparison_identity_sha256, self.baseline_build_sha256,
                  self.candidate_build_sha256, self.baseline_output_sha256,
                  self.candidate_output_sha256): _sha(v)
        if self.baseline_build_sha256 == self.candidate_build_sha256:
            raise ValueError('distinct pinned baseline/candidate builds required')
        for v in (self.baseline_seconds, self.candidate_seconds): _number(v, True)
        for v in (self.baseline_peak_rss_bytes, self.candidate_peak_rss_bytes):
            if type(v) is not int or v <= 0: raise ValueError('positive measured RSS required')
        for v in (self.expected_units, self.baseline_units, self.candidate_units):
            if type(v) is not int or v < 0: raise ValueError('integer coverage required')
        if self.expected_units < 1 or max(self.baseline_units, self.candidate_units) > self.expected_units:
            raise ValueError('invalid coverage')
        if self.state not in ('COMPLETE', 'FAILED', 'CANCELLED'):
            raise ValueError('closed terminal attempt state required')


def assess_benchmark(policy, pairs, *, expected_policy_sha256):
    """Screen ALL declared attempts. Never promotes/deploys, including on PASS.
    The caller must supply a policy pin recorded BEFORE measurement; matching a
    hash alone cannot prove this ordering or that failed attempts were disclosed.
    """
    policy.validate(); _sha(expected_policy_sha256)
    if digest(asdict(policy)) != expected_policy_sha256:
        raise ValueError('policy pin mismatch')
    if type(pairs) is not tuple or not 1 <= len(pairs) <= 80:
        raise ValueError('bounded immutable attempts required')
    ids=set(); groups={s: [] for s in policy.strata}; blockers=[]; pins=set()
    for pair in pairs:
        pair.validate()
        if pair.pair_id in ids or pair.stratum not in groups:
            raise ValueError('duplicate attempt or unregistered stratum')
        ids.add(pair.pair_id); groups[pair.stratum].append(pair)
        pins.add((pair.comparison_identity_sha256, pair.baseline_build_sha256, pair.candidate_build_sha256, pair.expected_units))
        if pair.state != 'COMPLETE': blockers.append('FAILED_OR_CANCELLED_ATTEMPT')
        if pair.baseline_output_sha256 != pair.candidate_output_sha256: blockers.append('OUTPUT_PARITY_MISMATCH')
        if pair.baseline_units != pair.expected_units or pair.candidate_units != pair.expected_units: blockers.append('COVERAGE_MISMATCH')
        if pair.candidate_peak_rss_bytes > policy.peak_rss_cap_bytes or pair.candidate_peak_rss_bytes > pair.baseline_peak_rss_bytes: blockers.append('MEMORY_REGRESSION_OR_CAP')
        if pair.candidate_seconds / pair.baseline_seconds > policy.max_pair_slowdown: blockers.append('PAIR_TIME_REGRESSION')
    # One homogeneous benchmark context. Additional contexts need separate plans.
    if len(pins) != 1: blockers.append('COMPARISON_IDENTITY_OR_BUILD_MISMATCH')
    if sum(p.baseline_seconds + p.candidate_seconds for p in pairs) > policy.max_total_wall_seconds:
        blockers.append('DECLARED_WALL_BUDGET_EXCEEDED')
    metrics={}
    for name, group in groups.items():
        if len(group) != policy.pairs_per_stratum: blockers.append('INCOMPLETE_OR_EXTRA_REGISTERED_ATTEMPTS')
        if group:
            speed=median(p.baseline_seconds/p.candidate_seconds for p in group)
            metrics[name]=dict(pairs=len(group),median_paired_speedup=speed)
            if speed < policy.min_median_speedup: blockers.append('INSUFFICIENT_STRATUM_SPEEDUP')
    out=dict(schema='research_ops_benchmark_screen_v1',
             status='REJECT_OR_INCOMPLETE' if blockers else 'TECHNICAL_REVIEW_CANDIDATE_NOT_APPROVED',
             policy_sha256=expected_policy_sha256, attempts_sha256=digest([asdict(p) for p in pairs]),
             blockers=sorted(set(blockers)), strata=metrics, all_declared_attempts_included=True,
             attempt_completeness_attested=False, provenance_attested=False,
             independent_parity_attested=False, budget_durably_enforced=False,
             execution_allowed=False, activation_allowed=False, ledger_modified=False,
             scientific_advantage_claimed=False)
    out['assessment_sha256']=digest(out)
    return out
