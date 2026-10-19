from pathlib import Path
import json,sys,numpy as np
from pullback import detect,NS
import past_price_producer as p
h=Path(__file__).parent;f=Path('/data/raw/no_l2_campaign_20260930/RTY_12-25_ticks_ext.parquet');assert p.sha(f)==p.EXPECTED['RTY/RTY_12-25_ticks_ext.parquet'];ss=[s for s in p.CATALOGS['RTY']['sessions'] if s['trade_date']=='20251007'];assert len(ss)==1
res=[]
for tf in [1,5]:
 p.STEP=tf*60*NS;b,prof,lo,hi=p.aggregate_profile(f,ss);raw,rows=detect(b,'RTY',ss[0]['contract'],{'20251007'},tf)
 # Independent scalar recursion checks all EMA values in this source sample.
 for period in [20,50,200]:
  alpha=2/(period+1);prev=float(b.c.iloc[0]);manual=[prev]
  for close in b.c.iloc[1:]:prev=alpha*float(close)+(1-alpha)*prev;manual.append(prev)
  assert np.allclose(manual,b[f'e{period}'],rtol=1e-12,atol=1e-9)
 for row in rows:
  i=int(np.where(b.close_ns.to_numpy()==row['signal_ns'])[0][0]);prev=b.iloc[i-1];current=b.iloc[i];side=row['direction'];tr=[]
  for j in range(i-20,i):
   rr=b.iloc[j];pc=b.c.iloc[j-1];tr.append(max(rr.h-rr.l,abs(rr.h-pc),abs(rr.l-pc)))
  assert abs(np.mean(tr)-row['U'])<1e-9
  assert side*(current.c-prev.e20)>0 and side*(prev.e20-prev.e50)>0 and side*(prev.c-prev.e200)>0
 cuts=[i for i in range(600,len(b)) if b.date.iloc[i]=='20251007' and b.minute.iloc[i] in [660,720,780]]
 for i in cuts:
  small=p.indicators(b.iloc[:i+1][['bucket','o','h','l','c','n']].copy());_,part=detect(small,'RTY',ss[0]['contract'],{'20251007'},tf);assert part==[s for s in rows if s['signal_ns']<=int(b.close_ns.iloc[i])]
 res.append({'asset':'RTY','day':'20251007','tf':tf,'source_sha256':p.sha(f),'warmup_bars':len(b),'unthinned_episodes':len(raw),'reserved_intents':len(rows),'prefix_checks':len(cuts),'scalar_EMA_and_U_and_signal_conditions_PASS':True,'outcomes_computed':False,'sample_only_NOT_full_census':True})
p.dump(h/'local_probe.json',{'probes':res,'scope':'One RTY date two TF independent scalar EMA/U; not independent detector/full raw replay','outcomes_computed':False});print(json.dumps(res,indent=2))
