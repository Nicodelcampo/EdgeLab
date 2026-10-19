from pathlib import Path, PureWindowsPath
import argparse,base64,zlib,json,hashlib,platform
from statistics import NormalDist
import numpy as np
import pandas as pd
import pyarrow.dataset as ds
import pyarrow.parquet as pq
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
def dump(p,x):p.write_text(json.dumps(x,indent=2,ensure_ascii=False,allow_nan=False))
def scan(file,cols,lo,hi):
 return ds.dataset(file,format='parquet').scanner(columns=cols,filter=(ds.field('ts_utc_ns')>=lo)&(ds.field('ts_utc_ns')<hi),batch_size=250000,use_threads=False).to_batches()
def rma(x,n):
 a=np.asarray(x,float);o=np.full(len(a),np.nan);good=np.where(np.isfinite(a))[0]
 if len(good)<n:return o
 first=good[0];seed=first+n-1
 assert np.isfinite(a[first:]).all()
 o[seed]=a[first:seed+1].mean()
 for i in range(seed+1,len(a)):o[i]=o[i-1]+(a[i]-o[i-1])/n
 return o
def indicators(b):
 b=b.copy();c=b.c.astype(float)
 for n in [20,50,200]:b[f'e{n}']=c.ewm(span=n,adjust=False).mean()
 prev=c.shift().to_numpy();tr=np.maximum(b.h-b.l,np.maximum(abs(b.h-prev),abs(b.l-prev))).to_numpy(float)
 atr=rma(tr,14);up=b.h.diff().fillna(0).to_numpy();dn=(-b.l.diff()).fillna(0).to_numpy()
 plus=np.where((up>dn)&(up>0),up,0.);minus=np.where((dn>up)&(dn>0),dn,0.)
 plus[0]=minus[0]=np.nan
 with np.errstate(invalid='ignore',divide='ignore'):
  pdi=np.where(atr>0,100*rma(plus,14)/atr,np.where(np.isfinite(atr),0,np.nan));mdi=np.where(atr>0,100*rma(minus,14)/atr,np.where(np.isfinite(atr),0,np.nan))
  den=pdi+mdi;dx=np.where(den>0,100*abs(pdi-mdi)/den,np.where(np.isfinite(den),0,np.nan))
 b['mom_atr_prev']=pd.Series(tr).rolling(20,min_periods=20).mean().shift().to_numpy(); consecutive=b.bucket.diff().eq(1).rolling(20,min_periods=20).sum().eq(20);b.loc[~consecutive,'mom_atr_prev']=np.nan; b['adx']=rma(dx,14);b['atr_prev']=pd.Series(atr).shift().to_numpy();b['close_ns']=(b.bucket+1)*STEP
 et=pd.to_datetime(b.bucket*STEP,utc=True).dt.tz_convert('America/New_York');b['date']=et.dt.strftime('%Y%m%d');b['minute']=et.dt.hour*60+et.dt.minute
 return b
def aggregate_profile(file,ss):
 lo=min(s['start'] for s in ss)-7*86400*NS;hi=max(s['end'] for s in ss)
 bars={};counts={s['trade_date']:0 for s in ss};prof=dict(rows=0,nulls=0,invalid_quotes=0,time_ties=0,nonpositive_price_volume=0)
 last=None
 for batch in scan(file,['ts_utc_ns','price_ticks','volume','bid_ticks','ask_ticks'],lo,hi):
  t=batch.to_pandas()
  if t.empty:continue
  ts=t.ts_utc_ns.to_numpy()
  assert np.all(ts[1:]>=ts[:-1]) and (last is None or ts[0]>=last)
  prof['time_ties']+=int((ts[1:]==ts[:-1]).sum())+int(last is not None and ts[0]==last);last=int(ts[-1])
  prof['rows']+=len(t);prof['nulls']+=int(t.isna().sum().sum())
  prof['invalid_quotes']+=int((~((t.bid_ticks>0)&(t.ask_ticks>t.bid_ticks))).sum())
  prof['nonpositive_price_volume']+=int(((t.price_ticks<=0)|(t.volume<=0)).sum())
  assert not t[['ts_utc_ns','price_ticks','volume']].isna().any().any()
  assert (t.price_ticks>0).all() and (t.volume>0).all() and np.equal(t.price_ticks,np.floor(t.price_ticks)).all()
  for s in ss:counts[s['trade_date']]+=int(np.searchsorted(ts,s['end'],side='left')-np.searchsorted(ts,s['start'],side='left'))
  q=t.assign(bucket=t.ts_utc_ns//STEP).groupby('bucket',sort=True).agg(o=('price_ticks','first'),h=('price_ticks','max'),l=('price_ticks','min'),c=('price_ticks','last'),n=('price_ticks','size'))
  for bucket,row in q.iterrows():
   k=int(bucket);v=[float(row.o),float(row.h),float(row.l),float(row.c),int(row.n)]
   if k in bars:
    z=bars[k];bars[k]=[z[0],max(z[1],v[1]),min(z[2],v[2]),v[3],z[4]+v[4]]
   else:bars[k]=v
 for s in ss:assert counts[s['trade_date']]==s['ticks'],('CATALOG_ROWS',s['trade_date'],counts[s['trade_date']],s['ticks'])
 b=pd.DataFrame([(k,*v) for k,v in sorted(bars.items())],columns=['bucket','o','h','l','c','n'])
 prof.update(catalog_rows_reconciled=True,bars=len(b),warmup_lo_ns=lo,analysis_hi_ns=hi,timestamp_ties='distinct prints preserved, not deduplicated',null_quotes='invalid for execution; price/volume nulls fail closed')
 return indicators(b),prof,lo,hi
NS=10**9;STEP=300*NS
# CATALOGS/EXPECTED/DAYS supplied by private frozen dataset adapter; not market data here.
