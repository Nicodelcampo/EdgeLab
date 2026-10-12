"""P0 single-session PRIVATE measurement runner, no execution authority.

Called only by a bounded Kaggle host with an already bound source and plan.
Never puts private feature rows in /kaggle/working. Aggregate receipt contains
counts/timings/hashes only. No source quality audit, labels or fitted states.
"""
import argparse,hashlib,json,os,resource,time
from datetime import datetime,timezone
from pathlib import Path
from .kaggle_session_reader import iter_sessions
from .phenomena import ClockMeasurements


def run(source,plan,private_root):
    p=Path(private_root).resolve()
    if not os.environ.get('KAGGLE_KERNEL_RUN_TYPE'):raise ValueError('Kaggle host only for market inputs')
    if p==Path('/kaggle/working') or Path('/kaggle/working') in p.parents:raise ValueError('private features cannot be notebook outputs')
    if plan['schema']!='mnq_phenomena_p0_plan_v1' or plan['outcomes'] or plan['classify_states'] or plan['holdout'] or plan['pnl']:
        raise ValueError('fixed measurement-only P0')
    start=time.monotonic();p.mkdir(parents=True,exist_ok=False);out=p/'features-private.jsonl';h=hashlib.sha256();size=0;found=0;summary=None
    with out.open('xb') as f:
        for st in iter_sessions(source,start_ns=plan['start_ns'],end_ns=plan['end_ns'],max_session_ticks=plan['max_session_ticks'],max_total_ticks=plan['max_session_ticks']):
            found+=1
            if found!=1:raise ValueError('single natural session only')
            actual=datetime.fromtimestamp(st.session_id*86400,timezone.utc).date().isoformat()
            if actual!=plan['target_session']:raise ValueError('session identity differs from fixed plan')
            t=st.ticks;m=ClockMeasurements(max_gap_ns=plan['max_gap_ns'],minimum_quote_volume_coverage=plan['minimum_quote_volume_coverage'],
                                         max_ticks=plan['max_session_ticks'],max_anchors=plan['max_anchors'],wall_seconds=plan['wall_seconds'])
            for r in m.measure(t.ts_ns,t.sequence,t.price_ticks,t.volume,t.bid_ticks,t.ask_ticks,trade_date=actual):
                if time.monotonic()-start>plan['wall_seconds']:raise TimeoutError('whole runner wall budget')
                data=(json.dumps(r,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode();size+=len(data)
                if size>plan['max_private_bytes']:raise ValueError('private byte capacity; no truncation')
                f.write(data);h.update(data)
            summary=m.summary
        f.flush();os.fsync(f.fileno())
    if found!=1:raise ValueError('selected session not observed')
    return {'schema':'mnq_phenomena_p0_receipt_v1','status':'MEASUREMENT_COMPLETE_NOT_PHENOMENON_OR_EDGE_VALIDATION',
            'target_session':plan['target_session'],'measurement':summary,'private_feature_bytes':size,'private_feature_sha256':h.hexdigest(),
            'wall_seconds':time.monotonic()-start,'measured_runner_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            'rss_scope':'THIS_LINUX_RUNNER_PROCESS_NOT_DESCENDANTS_OR_CGROUP','source_quality_audit':False,'state_classification':False,
            'outcomes':False,'inference':False,'raw_exported':False,'canonical_brain_written':False,'holdout_opened':False,'pnl':False}


def main():
    a=argparse.ArgumentParser();a.add_argument('--source',required=True);a.add_argument('--plan',required=True);a.add_argument('--private-root',required=True);a.add_argument('--receipt',required=True)
    x=a.parse_args();plan=json.loads(Path(x.plan).read_bytes());receipt=run(x.source,plan,x.private_root)
    Path(x.receipt).write_text(json.dumps(receipt,indent=2,allow_nan=False)+'\n')
if __name__=='__main__':main()
