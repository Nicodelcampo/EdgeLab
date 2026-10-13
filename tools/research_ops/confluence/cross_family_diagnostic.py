"""One bounded no-outcome reproduction of the original native-stage failure.

Existing source/warmup/configs and retention limits unchanged. Stop after June16
without fitting, labels, evaluation, market QA or private-log acquisition.
"""
import argparse,json,os,time
from pathlib import Path
from datetime import datetime,timezone
from .cross_family_pilot import PLAN as SCIENCE_PLAN,ROSTER,validate_plan
from .cross_family_scene import CrossFamilyScene
from .cross_family_diagnostics import safe_failure
from .kaggle_session_reader import iter_sessions
from .build_target_free_pilot import digest
PLAN='docs/research/ops/MNQ_CROSS_FAMILY_DIAGNOSTIC_PLAN.json'
PLAN_SHA='1cd333c02fe550c646dcab602bb9c71cc05614df0875ca656abb7f9ff7928f3f'
def validate(p):
 if digest(p)!=PLAN_SHA:raise ValueError('immutable diagnostic plan')
 return p

def run(source,p):
 if not os.environ.get('KAGGLE_KERNEL_RUN_TYPE'):raise ValueError('diagnostic source remains Kaggle-only')
 validate(p);original=json.loads(Path(SCIENCE_PLAN).read_bytes());roster=json.loads(Path(ROSTER).read_bytes());validate_plan(original,roster)
 if digest(original)!=p['source_plan_sha256']:raise ValueError('original frozen scope')
 native={**original,'wall_seconds':p['wall_seconds']};scene=CrossFamilyScene(roster,native);selected=[];date=None;started=time.monotonic()
 result={'schema':'crossfamily_diagnostic_receipt_v1','plan_sha256':digest(p),'source_science_plan_sha256':digest(original),'outcomes_computed':False,'quality_audit':False,'holdout_opened':False,'pnl':False,'raw_exported':False,'canonical_brain_written':False,'retention_policy':p['retention_policy'],'failure_reproduced':False,'scientific_result':False}
 try:
  for st in iter_sessions(source,start_ns=original['warmup_start_ns'],end_ns=original['read_end_ns'],max_session_ticks=original['max_session_ticks'],max_total_ticks=original['max_total_ticks']):
   date=datetime.fromtimestamp(st.session_id*86400,timezone.utc).date().isoformat();events,diag=scene.session(st,date,retain=date in original['training_sessions'])
   if date in original['training_sessions']:selected.append(diag)
   del events,st
   if date==p['stop_trade_date']:result['status']='PREFIX_NATIVE_PASS_NO_SCIENTIFIC_RESULTS';break
  else:raise ValueError('required diagnostic stop session unavailable')
 except Exception as exc:
  result.update(status='NATIVE_FAILURE_REPRODUCED_NO_SCIENTIFIC_RESULTS',failure_reproduced=True,failure_trade_date=date if date in original['training_sessions'] else None,failure=safe_failure(exc,scene.progress))
 result.update(completed_training_native_sessions=selected,total_ticks=scene.ticks,native_stage_seconds=dict(scene.times),wall_seconds=time.monotonic()-started)
 if len(json.dumps(result,indent=2,allow_nan=False).encode())>p['max_aggregate_bytes']:raise ValueError('bounded diagnostic aggregate')
 return result

def main():
 ap=argparse.ArgumentParser();[ap.add_argument('--'+k,required=True) for k in ('source','plan','private-root','receipt')];a=ap.parse_args();root=Path(a.private_root).resolve()
 if root==Path('/kaggle/working') or Path('/kaggle/working') in root.parents:raise ValueError('private diagnostics outside outputs')
 r=run(a.source,json.loads(Path(a.plan).read_bytes()));Path(a.receipt).write_text(json.dumps(r,indent=2,allow_nan=False)+'\n')
if __name__=='__main__':main()
