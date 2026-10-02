#!/usr/bin/env python3
import argparse,json,hashlib
from pathlib import Path
import numpy as np,pandas as pd,pyarrow.parquet as pq

def ema(x,p):
 a=2/(p+1); y=np.empty(len(x)); y[0]=x[0]
 for i in range(1,len(x)): y[i]=y[i-1]+a*(x[i]-y[i-1])
 return y

def load(root,tick,cut):
 rows=[]; inv=[]
 for p in sorted(Path(root).rglob('*.parquet')):
  pf=pq.ParquetFile(p); cols=set(pf.schema.names)
  raw={'ts_utc_ns','last','bid','ask'}.issubset(cols)
  canonical={'ts_utc_ns','price_ticks','bid_ticks','ask_ticks','contract'}.issubset(cols)
  if not (raw or canonical): continue
  if canonical:
   use=['ts_utc_ns','price_ticks','bid_ticks','ask_ticks','contract']+(['source_file'] if 'source_file' in cols else [])
   x=pd.read_parquet(p,columns=use).rename(columns={'price_ticks':'last','bid_ticks':'bid','ask_ticks':'ask'})
   if 'source_file' in x:
    day=x.source_file.astype(str).str.extract(r'(\d{8})(?=\.Last)',expand=False)
    fallback=pd.to_datetime(x.ts_utc_ns,unit='ns',utc=True).dt.strftime('%Y%m%d')
    x['source_day_nt_local']=pd.to_numeric(day.fillna(fallback),errors='raise').astype('int32')
    x=x.drop(columns=['source_file'])
   else:
    x['source_day_nt_local']=pd.to_datetime(x.ts_utc_ns,unit='ns',utc=True).dt.strftime('%Y%m%d').astype('int32')
   price_encoding='INTEGER_TICKS'
  else:
   use=['ts_utc_ns','last','bid','ask']+(['source_day_nt_local'] if 'source_day_nt_local' in cols else [])
   x=pd.read_parquet(p,columns=use)
   if 'source_day_nt_local' not in x: x['source_day_nt_local']=pd.to_datetime(x.ts_utc_ns,unit='ns',utc=True).dt.strftime('%Y%m%d').astype('int32')
   x['contract']=p.stem.split('_ticks')[0].replace('.parquet','')
   for c in ['last','bid','ask']: x[c]=np.rint(x[c].astype(float)/tick).astype('int64')
   price_encoding='DECIMAL_PRICE_TO_TICKS'
  x=x[x.source_day_nt_local<=cut].copy()
  inv.append({'file':p.name,'rows_total':pf.metadata.num_rows,'rows_discovery':len(x),'price_encoding':price_encoding})
  if len(x): rows.append(x[['ts_utc_ns','last','bid','ask','contract','source_day_nt_local']])
 if not rows: raise ValueError('no eligible parquet')
 x=pd.concat(rows,ignore_index=True)
 x=x[np.isfinite(x[['last','bid','ask']]).all(axis=1)&(x['last']>0)&(x['ask']>=x['bid'])]
 for c in ['last','bid','ask']: x[c]=x[c].astype('int64')
 return x.sort_values(['contract','source_day_nt_local','ts_utc_ns'],kind='stable').reset_index(drop=True),inv

def bars25(x):
 x['bar_no']=x.groupby(['contract','source_day_nt_local'],sort=False).cumcount()//25
 g=x.groupby(['contract','source_day_nt_local','bar_no'],sort=False,observed=True)
 b=g.agg(start_ns=('ts_utc_ns','first'),close_ns=('ts_utc_ns','last'),open=('last','first'),high=('last','max'),low=('last','min'),close=('last','last'),bid_open=('bid','first'),bid_low=('bid','min'),bid_high=('bid','max'),bid_close=('bid','last'),ask_open=('ask','first'),ask_low=('ask','min'),ask_high=('ask','max'),ask_close=('ask','last'),n=('last','size')).reset_index(); b=b[b.n==25].copy()
 for p in [200,500,2000]: b['e'+str(p)]=np.nan
 for _,ix in b.groupby('contract',sort=False).groups.items():
  ii=np.asarray(list(ix)); z=b.loc[ii,'close'].to_numpy(float)
  for p in [200,500,2000]: b.loc[ii,'e'+str(p)]=ema(z,p)
 b['prev200']=b.groupby('contract').e200.shift(); b['prev500']=b.groupby('contract').e500.shift(); b['age']=b.groupby('contract').cumcount()
 up=(b.prev200<=b.prev500)&(b.e200>b.e500)&(b.e200>b.e2000)&(b.e500>b.e2000); dn=(b.prev200>=b.prev500)&(b.e200<b.e500)&(b.e200<b.e2000)&(b.e500<b.e2000)
 b['sig']=np.where(up,1,np.where(dn,-1,0)); b.loc[b.age<6000,'sig']=0
 return b.reset_index(drop=True)

def sim(b,direction,pb,sl,tp,be,cost=2.4):
 trades=[]; free=-1; sgn=1 if direction=='NORMAL' else -1
 for i in np.flatnonzero(b.sig.to_numpy()!=0):
  if i<=free: continue
  side=int(b.sig.iloc[i])*sgn; day=b.source_day_nt_local.iloc[i]; con=b.contract.iloc[i]; end=min(len(b)-1,i+20); j=i+1
  if j>=len(b) or b.source_day_nt_local.iloc[j]!=day or b.contract.iloc[j]!=con: continue
  if pb:
   th=b.close.iloc[i]-side*pb; found=-1
   for q in range(j,end+1):
    if b.source_day_nt_local.iloc[q]!=day or b.contract.iloc[q]!=con: break
    if (side>0 and b.low.iloc[q]<=th) or (side<0 and b.high.iloc[q]>=th): found=q; break
   if found<0: continue
   j=found; entry=(th+max(1,b.ask_open.iloc[j]-b.bid_open.iloc[j])+1) if side>0 else (th-max(1,b.ask_open.iloc[j]-b.bid_open.iloc[j])-1)
  else: entry=(b.ask_open.iloc[j]+1) if side>0 else (b.bid_open.iloc[j]-1)
  stop=entry-side*sl; target=entry+side*tp; beon=False; k=j
  while k+1<len(b):
   k+=1
   if b.source_day_nt_local.iloc[k]!=day or b.contract.iloc[k]!=con:
    k-=1; px=(b.bid_close.iloc[k]-1) if side>0 else (b.ask_close.iloc[k]+1); reason='SESSION_END'; break
   stophit=(b.low.iloc[k]<=stop) if side>0 else (b.high.iloc[k]>=stop); tphit=(b.bid_high.iloc[k]>=target) if side>0 else (b.ask_low.iloc[k]<=target)
   if stophit: px=(stop-1) if side>0 else (stop+1); reason='BE' if beon else 'SL'; break
   if tphit: px=target; reason='TP'; break
   if be is not None and not beon and ((side>0 and b.high.iloc[k]>=entry+be) or (side<0 and b.low.iloc[k]<=entry-be)): beon=True; stop=entry
  else: continue
  net=side*(px-entry)-cost; trades.append({'signal_bar':int(i),'entry_bar':int(j),'exit_bar':int(k),'contract':con,'day':int(day),'side':side,'entry':float(entry),'exit':float(px),'reason':reason,'net_ticks':float(net)}); free=k
 return trades

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--input',required=True); ap.add_argument('--output',required=True); ap.add_argument('--asset',required=True); ap.add_argument('--tick-size',type=float,required=True); ap.add_argument('--cutoff',type=int,default=20260331); a=ap.parse_args(); o=Path(a.output);o.mkdir(parents=True,exist_ok=True)
 x,inv=load(a.input,a.tick_size,a.cutoff); b=bars25(x); del x; grid=[]; alltr=[]
 for d in ['NORMAL','INVERTED']:
  for pb in [0,25,50]:
   for sl in [90,200,300]:
    for tp in [30,150,300,450]:
     for be in [None,90]:
      if be is not None and be>=tp: continue
      cid=f'{d}_PB{pb}_SL{sl}_TP{tp}_BE{be or "OFF"}'; tr=sim(b,d,pb,sl,tp,be); v=np.array([z['net_ticks'] for z in tr]); days=np.array([z['day'] for z in tr]); daily=pd.Series(v).groupby(days).sum() if len(v) else pd.Series(dtype=float); rng=np.random.default_rng(20261002); boots=np.array([rng.choice(daily.to_numpy(),len(daily),replace=True).sum() for _ in range(500)]) if len(daily) else np.array([])
      grid.append({'cell_id':cid,'direction':d,'pullback':pb,'sl':sl,'tp':tp,'be':be,'trades':len(v),'sum_net_ticks':float(v.sum()) if len(v) else 0.0,'mean_net_ticks':float(v.mean()) if len(v) else None,'win_rate':float((v>0).mean()) if len(v) else None,'bootstrap_p_positive':float((boots>0).mean()) if len(boots) else None}); alltr += [dict(z,cell_id=cid) for z in tr]
 pd.DataFrame(grid).sort_values('sum_net_ticks',ascending=False).to_csv(o/'cell_summary.csv',index=False); pd.DataFrame(alltr).to_parquet(o/'trades.parquet',index=False); b.to_parquet(o/'bars25t.parquet',index=False)
 audit={'status':'PASS','asset':a.asset,'method':'25-trade bars; closed-bar EMA signals; next-bar/pullback entry; conservative bar replay; stop-first','execution_fidelity':'BAR_LEVEL_CONSERVATIVE_NOT_TICK_EXACT','holdout_opened':False,'cutoff':a.cutoff,'raw_discovery_rows':sum(z['rows_discovery'] for z in inv),'bars':len(b),'signals':int((b.sig!=0).sum()),'grid_cells':len(grid),'inventory':inv}; (o/'audit.json').write_text(json.dumps(audit,indent=2)); print(json.dumps(audit,indent=2))
if __name__=='__main__': main()
