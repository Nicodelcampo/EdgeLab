from pathlib import Path,PureWindowsPath
import json,numpy as np
import past_price_producer as p
r=Path(__file__).parent;days=p.DAYS;ss=[s for s in p.CATALOGS['RTY']['sessions'] if s['trade_date'] in days and PureWindowsPath(s['path']).name=='RTY_12-25_ticks_ext.parquet'];f=Path('/data/raw/no_l2_campaign_20260930/RTY_12-25_ticks_ext.parquet');counts={}
for tf in [5,15]:
 p.STEP=tf*60*p.NS;b,prof,lo,hi=p.aggregate_profile(f,ss)
 # Separate scalar implementation of event acceptance. No census.events reused.
 for K in [1.,.5]:
  for H in [120,60,30]:
   blocked=-1;ds={d:0 for d in days};raw=0
   for i in range(600,len(b)):
    z=b.iloc[i];j=i-60//tf
    if z.date not in days or z.minute<600 or z.minute+tf>960-H-15 or z.bucket-b.bucket.iloc[i-1]!=1:continue
    scale=float(z.mom_atr_prev)
    if not np.isfinite(scale) or scale<=0 or z.bucket-b.bucket.iloc[j]!=60//tf:continue
    roc=float(z.c-b.c.iloc[j])
    if roc==0 or abs(roc)<K*scale:continue
    raw+=1;ns=int(z.close_ns)
    if ns>blocked:ds[z.date]+=1;blocked=ns+(H*60+60)*p.NS
   counts[f'RTY|TF{tf}|K{K}|H{H}']={'contract':'RTY 12-25','reserved':sum(ds.values()),'unthinned':raw}
(r/'independent_real_support.json').write_text(json.dumps({'source_sha256':p.sha(f),'scope':'RTY12-25componentonly;independentscalareventacceptance;notallassetscertification','outcomes_computed':False,'checks':counts},indent=2));print('independent RTY12-25support counts',[(k,v['reserved']) for k,v in counts.items()])
