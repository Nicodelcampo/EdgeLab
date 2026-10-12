"""CLI: explicit synthetic proposals, finite daemon, read-only observation."""
import argparse,json,time
from pathlib import Path
from .store import Store,Policy,Plan
from .worker import run_one,SCRIPT_SHA256
from .observer import observe
from .design import Draft,audit_draft
from .dispatch import DispatchLedger,Reviewer

def _bounded_json(path):
    if path.is_symlink() or path.stat().st_size>65536:raise ValueError('bounded regular file required')
    with path.open('rb') as f:raw=f.read(65537)
    if len(raw)>65536:raise ValueError('file grew beyond limit')
    return json.loads(raw)

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--state',type=Path,default=Path('artifacts/research_ops/queue.sqlite'))
    s=p.add_subparsers(dest='command',required=True)
    a=s.add_parser('init');a.add_argument('--attempts',type=int,default=3);a.add_argument('--seconds',type=int,default=30)
    a=s.add_parser('submit-synthetic');a.add_argument('job_id');a.add_argument('--hypothesis',default='operational synthetic selfcheck');a.add_argument('--timeout',type=int,default=5)
    a=s.add_parser('verify');a.add_argument('--expected-tip')
    s.add_parser('run-one')
    a=s.add_parser('quarantine');a.add_argument('job_id')
    a=s.add_parser('audit-draft');a.add_argument('proposal',type=Path)
    a=s.add_parser('observe');a.add_argument('campaign_state',type=Path)
    a=s.add_parser('preflight-metadata');a.add_argument('bundle',type=Path);a.add_argument('--expected-sha256',required=True)
    s.add_parser('benchmark-synthetic')
    s.add_parser('benchmark-context-synthetic')
    a=s.add_parser('recall-brain');a.add_argument('ledger',type=Path);a.add_argument('query');a.add_argument('--expected-sha256',required=True);a.add_argument('--expected-tip',required=True)
    a=s.add_parser('recall-articles');a.add_argument('pack',type=Path);a.add_argument('query');a.add_argument('--expected-sha256',required=True);a.add_argument('--producer-commit',required=True)
    a=s.add_parser('snapshot-queue');a.add_argument('output',type=Path);a.add_argument('--snapshot-id',required=True);a.add_argument('--expected-tip',required=True)
    for name in ('inspect-snapshot','restore-queue'):
        a=s.add_parser(name);a.add_argument('snapshot',type=Path);a.add_argument('--expected-sha256',required=True);a.add_argument('--expected-tip',required=True)
        if name=='restore-queue':a.add_argument('destination',type=Path)
    a=s.add_parser('daemon');a.add_argument('--cycles',type=int,default=1);a.add_argument('--interval',type=float,default=5);a.add_argument('--expected-tip',required=True)
    a=s.add_parser('dispatch-init');a.add_argument('--dispatch-state',type=Path,required=True);a.add_argument('--reviewer-id',required=True)
    a=s.add_parser('dispatch-bind-plan');a.add_argument('--dispatch-state',type=Path,required=True);a.add_argument('plan',type=Path)
    a=s.add_parser('dispatch-reserve');a.add_argument('--dispatch-state',type=Path,required=True);a.add_argument('--reviewer-id',required=True);a.add_argument('directive_index',type=int)
    a=s.add_parser('dispatch-receipt');a.add_argument('--dispatch-state',type=Path,required=True);a.add_argument('directive_index',type=int);a.add_argument('--evidence-sha256',required=True);a.add_argument('--source-sha256',required=True);a.add_argument('--chars',type=int,required=True);a.add_argument('--cost',type=int,default=0)
    a=s.add_parser('dispatch-verify');a.add_argument('--dispatch-state',type=Path,required=True)
    args=p.parse_args(argv)
    if args.command=='snapshot-queue':
        from .snapshots import export_queue
        result=export_queue(Store(args.state),args.output,snapshot_id=args.snapshot_id,expected_tip=args.expected_tip)
    elif args.command=='inspect-snapshot':
        from .snapshots import inspect_snapshot
        result=inspect_snapshot(args.snapshot,expected_sha256=args.expected_sha256,expected_tip=args.expected_tip)
    elif args.command=='restore-queue':
        from .snapshots import restore_queue
        result=restore_queue(args.snapshot,args.destination,expected_sha256=args.expected_sha256,expected_tip=args.expected_tip)
    elif args.command=='recall-brain':
        from .knowledge import recall_brain
        result=recall_brain(args.ledger,expected_file_sha256=args.expected_sha256,expected_tip=args.expected_tip,query=args.query)
    elif args.command=='recall-articles':
        from .knowledge import recall_literature
        result=recall_literature(args.pack,expected_file_sha256=args.expected_sha256,producer_commit=args.producer_commit,query=args.query)
    elif args.command=='preflight-metadata':
        from .preflight import check_bundle
        result=check_bundle(args.bundle,args.expected_sha256)
    elif args.command=='benchmark-context-synthetic':
        from .context_benchmark import run_context_benchmark
        result=run_context_benchmark()
    elif args.command=='benchmark-synthetic':
        from .benchmark import run_benchmark
        result=run_benchmark()
    elif args.command=='audit-draft':
        result=audit_draft(Draft(**_bounded_json(args.proposal)))
    elif args.command=='observe': result=observe(args.campaign_state)
    elif args.command=='dispatch-init':
        ledger=DispatchLedger(args.dispatch_state);ledger.initialize(Reviewer(args.reviewer_id));result=ledger.verify()
    elif args.command=='dispatch-bind-plan':
        ledger=DispatchLedger(args.dispatch_state);ledger.bind_plan(_bounded_json(args.plan));result=ledger.verify()
    elif args.command=='dispatch-reserve':
        ledger=DispatchLedger(args.dispatch_state);result=ledger.reserve(args.directive_index,reviewer_id=args.reviewer_id)
    elif args.command=='dispatch-receipt':
        ledger=DispatchLedger(args.dispatch_state)
        result=ledger.record_receipt(args.directive_index,evidence_sha256=args.evidence_sha256,source_url_sha256=args.source_sha256,char_count=args.chars,cost=args.cost)
    elif args.command=='dispatch-verify':
        result=DispatchLedger(args.dispatch_state).verify()
    else:
        store=Store(args.state)
        if args.command=='init':store.initialize(Policy(args.attempts,args.seconds));result=store.verify()
        elif args.command=='submit-synthetic':store.submit(Plan(args.job_id,args.hypothesis,SCRIPT_SHA256,args.timeout));result=store.verify()
        elif args.command=='verify':result=store.verify(args.expected_tip)
        elif args.command=='quarantine':store.finish(args.job_id,'INTERRUPTED');result=store.verify()
        elif args.command=='run-one':result=run_one(store)
        else:
            if not 1<=args.cycles<=100 or not 0<=args.interval<=300:raise ValueError('finite daemon bounds required')
            store.verify(args.expected_tip)
            result=[]
            for cycle in range(args.cycles):
                receipt=run_one(store)
                result.append({'cycle':cycle,'receipt':receipt,'queue':store.verify()})
                if receipt is None or receipt['status']!='SUCCEEDED_TECHNICAL':break
                if cycle+1<args.cycles:time.sleep(args.interval)
    print(json.dumps(result,sort_keys=True,allow_nan=False))
    return 0

if __name__=='__main__':raise SystemExit(main())
