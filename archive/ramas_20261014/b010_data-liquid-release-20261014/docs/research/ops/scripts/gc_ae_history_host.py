import argparse,json,hashlib,datetime
from pathlib import Path
from tools.research_ops.dispatch_intent import DispatchIntent
from tools.research_ops.remote_watch import RemoteWatch,identity
from tools.research_ops.store import digest
B=Path('/data/operational-state'); S='gc-ae-history-3abcfe6990fa'; D=Path('docs/research/ops'); P=Path('/data/source-review')
def dump(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
def load(p):return json.loads(p.read_bytes())
def journals():return DispatchIntent(B/(S+'-dispatch.sqlite')),RemoteWatch(B/(S+'-watch.sqlite'))
a=argparse.ArgumentParser();a.add_argument('action');a.add_argument('--asset');a.add_argument('--info');a.add_argument('--status');args=a.parse_args();d,w=journals();asset=args.asset
if args.action=='prepare':
 req=load(P/f'ae-{asset}-private-request.json')['request'];pkg=load(D/'GC_AE_HISTORY_PACKAGE.json')[asset]
 request={k:pkg[k] for k in ('source_commit','bundle_sha256','plan_sha256')};request.update(account='nicolasbuttaro',spec_sha256=digest(req))
 snap=d.prepare(request,expected_tip=d.snapshot()['tip_sha256']);d.begin_send(snap['intent_key'],expected_tip=snap['tip_sha256']);dump(B/f'{S}-{asset}-send-ticket.json',{'intent_key':snap['intent_key'],'request':request});print(asset,'SEND_STARTED')
elif args.action=='ack':
 x=load(Path(args.info));x=json.loads(x['content'][0]['text']);m=x['metadata'];req=load(P/f'ae-{asset}-private-request.json')['request'];pkg=load(D/'GC_AE_HISTORY_PACKAGE.json')[asset]
 assert x['blob']['source']==req['text'];assert hashlib.sha256(req['text'].encode()).hexdigest()==pkg['notebook_text_sha256']
 assert m['is_private'] and not m['enable_gpu'] and not m['enable_tpu'] and m['enable_internet'] and m['docker_image']==req['dockerImage']; assert m['current_version_number']==1
 t=load(B/f'{S}-{asset}-send-ticket.json');assert digest(req)==t['request']['spec_sha256']
 job={k:t['request'][k] for k in ('account','source_commit','bundle_sha256','plan_sha256')};job.update(kernel_id=m['id'],version=m['current_version_number'])
 dump(B/f'{S}-{asset}-job.json',job);d.acknowledge(t['intent_key'],job,expected_tip=d.snapshot()['tip_sha256']);w.register(job,expected_tip=w.snapshot()['tip_sha256'])
 evidence={'asset':asset,'job':job,'slug':m['slug'],'source_exact':True,'private_cpu_verified':True,'docker_exact':True,'notebook_text_sha256':pkg['notebook_text_sha256']};dump(B/f'{S}-{asset}-ack.json',evidence);print(json.dumps(evidence))
elif args.action=='reserve':
 job=load(B/f'{S}-{asset}-job.json'); snap=w.snapshot();assert snap['state']['attempts'][identity(job)]['polls_reserved']<6
 s=w.reserve(job,expected_tip=snap['tip_sha256']);dump(B/f'{S}-{asset}-poll-ticket.json',{'job':job,'ticket':s['ticket'],'reserved_tip':s['tip_sha256']});print(asset,'reserved poll',s['ticket'])
elif args.action=='record':
 t=load(B/f'{S}-{asset}-poll-ticket.json');s=w.record(t['job'],ticket=t['ticket'],status=args.status,response_sha256=digest({'status':args.status}),expected_tip=w.snapshot()['tip_sha256'])
 if args.status in ('COMPLETE','ERROR','CANCELLED'):
  st=load(B/f'{S}-{asset}-send-ticket.json');d.terminal(st['intent_key'],t['job'],args.status,expected_tip=d.snapshot()['tip_sha256'])
 print(asset,args.status,'poll',t['ticket'])
elif args.action=='checkpoint':
 launch={};
 for z in ('AE',):
  f=B/f'{S}-{z}-ack.json';launch[z]=load(f) if f.exists() else {'asset':z,'dispatched':False,'status':'SEND_STARTED_NOT_YET_ACKNOWLEDGED' if (B/f'{S}-{z}-send-ticket.json').exists() else 'PACKAGED_NOT_SENT'}
 for v in launch.values():
  if 'job' in v:v.update(dispatched=True,watch=w.snapshot()['state']['attempts'][identity(v['job'])])
 dump(D/'GC_AE_HISTORY_LAUNCH.json',{'schema':'multiasset_launch_v1','assets':launch,'dispatch':d.snapshot(),'watch':w.snapshot(),'canonical_brain_written':False,'holdout_accessed':False,'near_100_percent_NT8_parity_measured':False})
 print({k:v.get('watch',{}).get('status',v.get('status')) for k,v in launch.items()})
