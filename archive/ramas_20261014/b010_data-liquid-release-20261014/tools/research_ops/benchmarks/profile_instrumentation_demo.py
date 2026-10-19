"""Fixed synthetic instrumentation self-check; no market/source access.
Run in a fresh interpreter: python -m tools.research_ops.benchmarks.profile_instrumentation_demo
It compares only an instrumented computation with its independent reference,
not a speedup, Kaggle memory measurement or scientific engine parity.
"""
import json
from tools.research_ops.stage_profile import StageProfiler
from tools.research_ops.store import digest

def main():
    identity=dict(run_id='synthetic_profile',provider_job_id='synthetic_profile_execution',version=1,
                  source_sha256=digest('synthetic_sequence'),selection_sha256=digest('4096'),
                  scientific_protocol_sha256=digest('exclude_current_prefix'),
                  engine_build_sha256=digest('fixed_synthetic_driver_v1'),
                  manifest_sha256=digest('not_a_market_manifest'))
    p=StageProfiler(identity=identity,code_commit='0'*40)
    with p.stage('prepare'):values=[(i*17)%257 for i in range(4096)]
    with p.stage('features'):
        features=[sum(values[max(0,i-8):i]) for i in range(len(values))]
    with p.stage('serialization'):output_sha=digest(features)
    # Independent streaming path, outside measured stage; disclosed residual.
    running=0;reference=[]
    for i,value in enumerate(values):
        reference.append(running);running+=value
        if i>=8:running-=values[i-8]
    if features!=reference:raise ValueError('synthetic parity failed')
    out=p.finish()
    out.update(status='SYNTHETIC_PROFILE_INSTRUMENTATION_PASS_NOT_MNQ_PARITY',
               expected_units=4096,completed_units=4096,output_sha256=output_sha,
               input_sha256=digest(values),baseline_adopted=False)
    print(json.dumps(out,allow_nan=False))

if __name__=='__main__':main()