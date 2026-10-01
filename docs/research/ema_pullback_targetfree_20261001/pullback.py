"""Frozen target-free pullback census. NO outcomes, models or economic replay."""
from pathlib import Path,PureWindowsPath
import sys,json,argparse,hashlib,collections
import numpy as np
import pyarrow.parquet as pq
sys.path.insert(0,str(Path(__file__).parent/'repo'))
from edgelab.research.holdout_guard import check_holdout
from edgelab.research.universo_estudio import cargar_dias_de_estudio
import past_price_producer as p
NS=10**9

def detect(b,asset,contract,days,tf):
 """Past-EMA touch/reclaim; one episode must rearm on a new untouched bar."""
 result=[]; raw=[];armed=False;active=False;age=0;episode_side=0;lastday=None;blocked=-1
 c=b.c.to_numpy();h=b.h.to_numpy();l=b.l.to_numpy();e20=b.e20.to_numpy();e50=b.e50.to_numpy();e200=b.e200.to_numpy();u=b.mom_atr_prev.to_numpy()
 buck=b.bucket.to_numpy();dates=b.date.to_numpy();minutes=b.minute.to_numpy();nss=b.close_ns.to_numpy()
 for i in range(600,len(b)):
  day=dates[i];ns=int(nss[i]);minute=int(minutes[i])
  if day!=lastday:armed=active=False;age=0;lastday=day
  if day not in days or minute<600 or minute+tf>885 or buck[i]-buck[i-1]!=1 or not np.isfinite(u[i]) or u[i]<=0:
   armed=active=False;age=0;continue
  # Levels are frozen at the PREVIOUS completed bar, not current-bar EMA.
  side=1 if e20[i-1]>e50[i-1] and c[i-1]>e200[i-1] else -1 if e20[i-1]<e50[i-1] and c[i-1]<e200[i-1] else 0
  if side==0 or (active and side!=episode_side):armed=active=False;age=0
  if side==0:continue
  level=e20[i-1];untouched=(l[i]>level if side==1 else h[i]<level)
  reclaimed=side*(c[i]-level)>0
  if active:
   age+=1
   if age>10:armed=active=False;age=0
  if not active:
   if untouched:armed=True;episode_side=side;continue
   if not armed or side!=episode_side:continue
   active=True;age=1
  if active and reclaimed:
   row={'id':f'{asset}|{contract}|{day}|TF{tf}|{ns}', 'asset':asset,'contract':contract,'day':str(day),'tf':tf,'signal_ns':ns,'direction':side,'U':float(u[i]),'separated':bool(abs(e20[i-1]-e50[i-1])>=.25*u[i]),'episode_bars':age}
   raw.append(row)
   # Base slots are fixed first; separated is a subset with no rescheduling.
   if ns>blocked:result.append(row);blocked=ns+1860*NS
   active=armed=False;age=0
 return raw,result

def summarize(rows,raw,days):
 counts=[sum(s['day']==d for s in rows) for d in days]
 return {'eligible_sessions':len(days),'episodes_unthinned':len(raw),'reserved_intents':len(rows),'separated_subset':sum(s['separated'] for s in rows),'mean_per_session':float(np.mean(counts)),'median_per_session':float(np.median(counts)),'active_sessions':sum(x>0 for x in counts),'zero_sessions':sum(x==0 for x in counts),'q25_q75':list(map(float,np.quantile(counts,[.25,.75]))),'by_month':{m:sum(s['day'][:6]==m for s in rows) for m in sorted({d[:6] for d in days})},'by_contract':dict(collections.Counter(s['contract'] for s in rows)),'frequency_support':len(rows)>=200 and np.median(counts)>=4 and sum(x>0 for x in counts)>=.8*len(days),'not_trades':True,'outcomes_computed':False}

def run(root,out):
 here=Path(__file__).parent;out.mkdir(parents=True,exist_ok=True);m=json.load(open(here/'manifest.json'))
 assert p.sha(here/'pullback.py')==m['code_sha256']['pullback.py'];assert p.sha(here/'past_price_producer.py')==m['code_sha256']['past_price_producer.py']
 for rel,hash0 in m['repo_modules'].items():assert p.sha(here/'repo'/rel)==hash0
 files=[];custody=[]
 for asset in m['assets']:
  days=m['days_by_asset'][asset];ss=[s for s in p.CATALOGS[asset]['sessions'] if s['trade_date'] in days];assert len(ss)==len(days)
  check_holdout(days[0][:4]+'-'+days[0][4:6]+'-'+days[0][6:]+'T00:00:00Z',days[-1][:4]+'-'+days[-1][4:6]+'-'+days[-1][6:]+'T23:59:59Z',purpose='development',caller='EMA_PULLBACK_CENSUS',log_path=str(out/'guard.log'))
  adapter={'dias':[{'fecha':s['trade_date'][:4]+'-'+s['trade_date'][4:6]+'-'+s['trade_date'][6:],'archivo':PureWindowsPath(s['path']).name,'n_ticks':s['ticks']} for s in ss]};approved,guard=cargar_dias_de_estudio(adapter,caller='EMA_PULLBACK_CENSUS');assert len(approved)==len(days) and not guard['descartados_holdout']
  for name in sorted({PureWindowsPath(s['path']).name for s in ss}):
   rel=asset+'/'+name;f=root/rel;assert f.exists(),('MISSING_INPUT',rel);h=p.sha(f);assert h==p.EXPECTED[rel],('CUSTODY',rel,h)
   custody.append({'path':rel,'sha256':h,'rows':pq.ParquetFile(f).metadata.num_rows});sub=[s for s in ss if PureWindowsPath(s['path']).name==name];files.append((asset,f,sub))
 p.dump(out/'preflight.json',{'code_sha256':m['code_sha256'],'manifest_sha256':p.sha(here/'manifest.json'),'custody':custody,'outcomes_accessed':False,'holdout_opened':False});p.dump(out/'manifest.json',m)
 allrows={};allraw={};prefix=[];profiles=[]
 for asset,f,ss in files:
  days={s['trade_date'] for s in ss};contract=ss[0]['contract'];assert all(s['contract']==contract for s in ss)
  for tf in m['timeframes_min']:
   p.STEP=tf*60*NS;b,prof,lo,hi=p.aggregate_profile(f,ss);assert hi<1782864000000000000 # UTC 2026-07-01; session ends earlier
   raw,rows=detect(b,asset,contract,days,tf);key=f'{asset}|TF{tf}';allrows.setdefault(key,[]).extend(rows);allraw.setdefault(key,[]).extend(raw);profiles.append({'asset':asset,'file':f.name,'tf':tf,**prof})
   pos=[i for i in range(600,len(b)) if b.date.iloc[i] in days and b.minute.iloc[i]==720]
   for i in pos[:3]:
    small=p.indicators(b.iloc[:i+1][['bucket','o','h','l','c','n']].copy());r2,s2=detect(small,asset,contract,days,tf);cut=int(b.close_ns.iloc[i]);assert s2==[x for x in rows if x['signal_ns']<=cut];assert r2==[x for x in raw if x['signal_ns']<=cut];prefix.append({'asset':asset,'file':f.name,'tf':tf,'cut_ns':cut,'pass':True})
   print('census',asset,f.name,tf,len(rows),flush=True)
 cells={key:summarize(sorted(rows,key=lambda x:x['signal_ns']),allraw[key],m['days_by_asset'][key.split('|')[0]]) for key,rows in allrows.items()}
 selection={a:(5 if cells[f'{a}|TF5']['frequency_support'] else 1 if cells[f'{a}|TF1']['frequency_support'] else None) for a in m['assets']}
 result={'cells':cells,'selection_by_frozen_frequency_rule':selection,'prefix_checks':len(prefix),'prefix_pass':True,'outcomes_computed':False,'entry_quote_support_NOT_measured':True,'models_fitted':0,'holdout_opened':False}
 p.dump(out/'census.json',result);p.dump(out/'profiles.json',profiles);p.dump(out/'prefix_checks.json',prefix)
 with open(out/'episodes_PRIVATE.jsonl','w') as f:
  for key,rows in allrows.items():
   for row in rows:f.write(json.dumps(row)+'\n')
 print('DONE census ONLY',selection,flush=True)
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--root',type=Path,required=True);a.add_argument('--out',type=Path,default=Path('/kaggle/working'));args=a.parse_args();run(args.root,args.out)
