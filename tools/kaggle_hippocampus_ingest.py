#!/usr/bin/env python3
"""Verified aggregate evidence -> existing durable Hipocampo. Never a trial/edge."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import types

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()


def modules():
    # Existing production modules, loaded without optional cortex/__init__ deps.
    for name,path in [('edgelab',ROOT/'edgelab'),('edgelab.edge_brain',ROOT/'edgelab/edge_brain')]:
        if name not in sys.modules:
            pkg=types.ModuleType(name);pkg.__path__=[str(path)];sys.modules[name]=pkg
    out=[]
    for name in ['hippocampus','hippocampus_store']:
        full='edgelab.edge_brain.'+name
        if full not in sys.modules:
            spec=importlib.util.spec_from_file_location(full,ROOT/'edgelab/edge_brain'/f'{name}.py')
            mod=importlib.util.module_from_spec(spec);sys.modules[full]=mod;spec.loader.exec_module(mod)
        out.append(sys.modules[full])
    return out


def verify_store(directory):
    d=Path(directory).resolve()
    manifest=json.loads((d/'manifest.json').read_text())
    listed={x['path'] for x in manifest['files']}
    if not {'results.json','attestation.json','plan.json'} <= listed:
        raise ValueError('incomplete evidence')
    for row in manifest['files']:
        p=(d/row['path']).resolve()
        if not p.is_relative_to(d) or sha(p)!=row['sha256']:
            raise ValueError('artifact hash mismatch')
    r=json.loads((d/'results.json').read_text());a=json.loads((d/'attestation.json').read_text());plan=json.loads((d/'plan.json').read_text())
    if r['status']!='PASS_INTEGRITY_NOT_EDGE' or a['scope']!='infrastructure_only':
        raise ValueError('not an integrity-only result')
    for field in ['holdout_touched','future_price_path_accessed','first_touch_accessed','pnl_accessed']:
        if a.get(field) is not False:raise ValueError('unverified firewall')
    if plan['spec']['holdout_first_trade_date']!='2026-10-01':raise ValueError('holdout mismatch')
    if any(x['date']>='2026-10-01' for s in plan['shards'] for x in s['sessions']):
        raise ValueError('holdout session selected')
    if plan['spec']['mode']!='aggregate' or plan['spec']['metrics']!=['input_integrity','bar_conservation']:
        raise ValueError('not a supported aggregate spec')
    for bar in r['bars']:
        if bar['file'] not in listed:raise ValueError('missing bars')
    return plan,r,a,sha(d/'manifest.json')


def ingest(directory,ledger_path,*,recorded_at_utc=None):
    plan,result,attest,artifact_hash=verify_store(directory) # NO records before verification
    h,storemod=modules();ledger=Path(ledger_path);ledger.parent.mkdir(parents=True,exist_ok=True)
    episode='EP-AGGREGATES-'+plan['spec']['run_id']+'-'+artifact_hash[:16]
    now=recorded_at_utc or datetime.now(timezone.utc).isoformat()
    # Atomic copy-on-append; the original is never replaced by a partial episode.
    lock=storemod._exclusive_lock(ledger) # Same OS lock as every durable-store writer, portable to Windows.
    lock.__enter__()
    tmp=None
    try:
        current=storemod.DurableHippocampus(ledger)
        if episode in current.memory.episodes:
            steps=current.memory.steps[episode]
            if not any(s.input_params.get('manifest_sha256')==artifact_hash for s in steps):
                raise ValueError('idempotency collision')
            if not current.memory.successes[episode]:raise ValueError('incomplete existing episode')
            return {'schema':'edgelab_aggregate_hippocampus_receipt_v1','episode_id':episode,'tip':current.verify(),
                    'records':len(storemod.ledger_record_hashes(ledger)),'manifest_sha256':artifact_hash,'idempotent':True}
        fd,name=tempfile.mkstemp(prefix=ledger.name+'.',dir=ledger.parent);os.close(fd);tmp=Path(name)
        if ledger.exists():tmp.write_bytes(ledger.read_bytes())
        store=storemod.DurableHippocampus(tmp,expected_tip_hash=current.tip_hash)
        store.register_episode(h.AnalysisEpisode(episode_id=episode,goal='Materialize approved ES/NQ bars and verify data conservation; no economic hypothesis',
              status='COMPLETED_UNADJUDICATED',created_at_utc=now,updated_at_utc=now,
              recorded_by='tools/kaggle_hippocampus_ingest.py',outcomes_inspected=False))
        store.record_expectation(h.Expectation(expectation_id=episode+'-EXPECT',episode_id=episode,
              statement='Exact planned session coverage, file hashes, and target-free firewall',metric='aggregate_integrity',
              expected_direction='EXACT_MATCH',status='PROPOSED',created_at_utc=now))
        store.record_step(h.StepExecution(step_id=episode+'-VERIFY',episode_id=episode,step_index=0,
              action='verify_aggregate_store',tool_name='kaggle_spec_v2.merge',status='SUCCEEDED_UNADJUDICATED',
              input_params={'manifest_sha256':artifact_hash,'runner_sha256':attest['runner_sha256'],
                            'catalog':plan['spec']['catalog'],'dataset_versions':plan['spec']['dataset_versions']},
              output_summary=f"PASS_INTEGRITY_NOT_EDGE; sessions={plan['selected_sessions']}; files={len(result['bars'])}",executed_at_utc=now))
        store.record_success(h.SuccessEvent(success_id=episode+'-SUCCESS',episode_id=episode,step_id=episode+'-VERIFY',
              description='Verified aggregate store; no trial, promotion, or economic verdict',
              verified_invariants=['HASHES','APPROVED_SESSION_COVERAGE','NO_HOLDOUT','NO_OUTCOMES'],occurred_at_utc=now))
        store.record_lesson(h.LessonCandidate(lesson_id=episode+'-LESSON',episode_id=episode,
              statement='A successful kernel save is not proof of input mounts. Require actual file identity and exact approved-session conservation before ingestion.',
              evidence_record_ids=[episode+'-VERIFY'],confidence='LOW',status='PROPOSED',scope='OPERATIONAL',created_at_utc=now))
        tip=store.verify()
        os.replace(tmp,ledger);tmp=None
        receipt={'schema':'edgelab_aggregate_hippocampus_receipt_v1','episode_id':episode,'tip':tip,
                 'records':len(storemod.ledger_record_hashes(ledger)),'manifest_sha256':artifact_hash,'idempotent':False}
        return receipt
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)
        lock.__exit__(None,None,None)


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--store',required=True);p.add_argument('--ledger',required=True);p.add_argument('--receipt',required=True)
    a=p.parse_args();receipt=ingest(a.store,a.ledger);Path(a.receipt).write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

if __name__=='__main__':main()
