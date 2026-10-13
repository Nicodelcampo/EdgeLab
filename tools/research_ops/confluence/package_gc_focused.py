"""Two explicitly authorized finite requests; source URLs stay private."""
import hashlib
from .package_multiasset import build_request as build
from .multiasset_crossfamily import FOCUS_PLAN

def build_request(root,*,url,source_commit,purpose):
 if purpose not in ('SCIENCE','SCHEDULE_BENCHMARK'):raise ValueError('closed focused package purpose')
 req,r=build(root,asset='GC',url=url,source_commit=source_commit,plan_path=FOCUS_PLAN)
 if purpose=='SCHEDULE_BENCHMARK':req['request']['text']=req['request']['text'].replace('confluence.multiasset_crossfamily','confluence.bt2a_schedule_benchmark')
 req['request']['newTitle']='EdgeLab GC Focused Return V1' if purpose=='SCIENCE' else 'EdgeLab GC BT2A Schedule Benchmark V1'
 r.update(purpose=purpose,notebook_text_sha256=hashlib.sha256(req['request']['text'].encode()).hexdigest());compile(req['request']['text'],'private-focused-'+purpose,'exec');return req,r
