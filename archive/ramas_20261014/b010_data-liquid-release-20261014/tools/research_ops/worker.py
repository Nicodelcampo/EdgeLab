"""Fixed synthetic action only. Resource limits are NOT an untrusted-code sandbox."""
from __future__ import annotations
import hashlib, json, math, os, signal, subprocess, sys, tempfile, time
from pathlib import Path
from .store import canonical, digest

SCRIPT = "import json\nassert sum(i*i for i in range(64)) == 85344\nprint(json.dumps({'status':'PASS','scope':'synthetic','market_data_opened':False}))\n"
SCRIPT_SHA256 = hashlib.sha256(SCRIPT.encode()).hexdigest()

def limits(timeout):
    import resource
    resource.setrlimit(resource.RLIMIT_AS, (256 << 20, 256 << 20))
    resource.setrlimit(resource.RLIMIT_CPU, (math.ceil(timeout), math.ceil(timeout) + 1))
    resource.setrlimit(resource.RLIMIT_FSIZE, (65536, 65536))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def run_one(store):
    if os.name != 'posix':
        raise RuntimeError('bounded worker requires POSIX; fail closed')
    plan = store.claim()
    if plan is None:
        return None
    start = time.monotonic()
    result = dict(job_id=plan.job_id, plan_sha256=digest(plan.__dict__), script_sha256=SCRIPT_SHA256,
                  scope='synthetic', status='FAILED_TECHNICAL', market_data_opened=False,
                  holdout_opened=False, pnl_computed=False, edge_claim=False)
    try:
        if plan.protocol_sha256 != SCRIPT_SHA256:
            raise ValueError('unrecognized protocol; claim remains charged')
        with tempfile.TemporaryDirectory(prefix='edgelab-synthetic-') as tmp:
            root = Path(tmp)
            script = root / 'task.py'
            script.write_text(SCRIPT)
            with (root/'stdout').open('wb') as out, (root/'stderr').open('wb') as err:
                process = subprocess.Popen([sys.executable, '-I', '-S', str(script)], cwd=root,
                    env={'PATH': '/usr/bin:/bin', 'OPENBLAS_NUM_THREADS': '1'}, stdout=out, stderr=err,
                    start_new_session=True, preexec_fn=lambda: limits(plan.timeout_seconds))
                try:
                    process.wait(timeout=plan.timeout_seconds)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
                    raise TimeoutError('synthetic worker timeout')
            if process.returncode != 0:
                raise RuntimeError('synthetic worker nonzero exit')
            output = json.loads((root/'stdout').read_text())
            if output != {'status':'PASS','scope':'synthetic','market_data_opened':False}:
                raise ValueError('unexpected synthetic output')
            result['status'] = 'SUCCEEDED_TECHNICAL'
    except Exception as exc:
        result['error'] = type(exc).__name__ + ': ' + str(exc)
    result['wall_seconds'] = time.monotonic() - start
    directory = store.path.parent / 'receipts'
    directory.mkdir(exist_ok=True, mode=0o700)
    output = directory / (plan.job_id + '.json')
    data = (canonical(result) + '\n').encode()
    fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as f:
        f.write(data); f.flush(); os.fsync(f.fileno())
    store.finish(plan.job_id, result['status'], hashlib.sha256(data).hexdigest())
    return result
