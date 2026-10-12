"""Serial instrumentation for a future isolated Linux single-process workload.
Not an executor or timeout sandbox. No functions, code, signals or paths are
supplied by a model. A trusted fixed driver owns calls, cap enforcement and
whole-workload coverage. Multi-process workloads are rejected, not underestimated.
"""
import contextlib, os, resource, sys, time
from .store import digest
from .post_run import _sha

STAGES=frozenset(('prepare','jit','detector','trigger','outcome','features',
                  'serialization','primary_analysis','export'))

def _children():
    if sys.platform!='linux':raise ValueError('Linux ru_maxrss semantics required')
    # Inspect every thread's children; a final RUSAGE_CHILDREN check catches
    # waited descendants as well. Not protection against a hostile workload.
    from pathlib import Path
    children=[]
    for p in Path('/proc/self/task').glob('*/children'):
        children.extend(p.read_text().split())
    return children

class StageProfiler:
    def __init__(self,*,identity,code_commit):
        from .mnq_closeout import IDENTITY_FIELDS
        from .post_run import RunObservation
        if type(identity) is not dict or set(identity)!=IDENTITY_FIELDS:
            raise ValueError('closed execution/input/build identity required')
        RunObservation(**identity,state='COMPLETE',receipt_sha256='0'*64,
                       wall_seconds=1,peak_rss_bytes=1,expected_units=1,completed_units=1,stages=()).validate()
        import re
        if not isinstance(code_commit,str) or not re.fullmatch('[0-9a-f]{40}',code_commit):raise ValueError('frozen code commit required')
        if _children() or resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss:
            raise ValueError('fresh no-child process required')
        self.identity=dict(identity);self.code_commit=code_commit
        self.pid=os.getpid();self.started=time.perf_counter();self.stages={}
        self.open=False;self.failed=False;self.closed=False

    @contextlib.contextmanager
    def stage(self,name):
        if name not in STAGES or self.open or self.closed or os.getpid()!=self.pid:
            raise ValueError('closed, serial, same-process fixed stage required')
        if _children():self.failed=True;raise ValueError('child process invalidates RSS scope')
        self.open=True;start=time.perf_counter()
        try:yield
        except BaseException:
            self.failed=True
            raise
        finally:
            self.stages[name]=self.stages.get(name,0)+time.perf_counter()-start
            self.open=False

    def finish(self):
        if self.open or self.closed or self.failed or os.getpid()!=self.pid:
            raise ValueError('complete successful same-process workload required')
        if _children() or resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss:
            self.failed=True;raise ValueError('child process invalidates single-process RSS')
        self.closed=True
        wall=time.perf_counter()-self.started
        peak=int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)*1024
        memory=dict(schema='research_ops_memory_measurement_v1',
                    identity_sha256=digest(self.identity),code_commit=self.code_commit,
                    measurement='LINUX_SINGLE_PROCESS_RUSAGE_SELF_HIGH_WATER_RSS',
                    peak_rss_bytes=peak,children_seen=False,workload_complete=True)
        return dict(schema='research_ops_serial_stage_profile_v1',wall_seconds=wall,
                    stage_seconds=dict(self.stages),unassigned_seconds=wall-sum(self.stages.values()),
                    memory=memory,execution_allowed=False,source_certified=False,
                    qualification='Self RSS high-water includes imports/pre-profiler allocations; isolated fresh process and fixed full-workload driver required. This API does not enforce timeout, source access or coverage.')