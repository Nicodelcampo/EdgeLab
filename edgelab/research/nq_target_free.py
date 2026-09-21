"""Target-free utilities for contract-month representation episodes."""
from datetime import datetime,timezone
import numpy as np
DISCOVERY_END_NS=1767225600000000000
def month_slices(min_ns:int,max_ns:int,end_exclusive:int=DISCOVERY_END_NS):
 start=datetime.fromtimestamp(min_ns/1e9,tz=timezone.utc).replace(day=1,hour=0,minute=0,second=0,microsecond=0);out=[]
 while int(start.timestamp()*1e9)<min(max_ns+1,end_exclusive):
  nxt=start.replace(year=start.year+1,month=1)if start.month==12 else start.replace(month=start.month+1)
  a=max(min_ns,int(start.timestamp()*1e9));b=min(max_ns+1,end_exclusive,int(nxt.timestamp()*1e9))
  if a<b:out.append((start.strftime('%Y-%m'),a,b))
  start=nxt
 return out
def quantiles(values):
 if not values:return None
 a=np.asarray(values,dtype=float);return {str(float(p)):float(np.quantile(a,p))for p in(0,.1,.25,.5,.75,.9,1)}
