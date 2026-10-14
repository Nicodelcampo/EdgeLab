"""Independent scalar gates and dictionary-matched contrasts, extracted from audited review."""
import math
from collections import defaultdict
def scalar_gate(r,c):
 def finite(k):return r[k] is not None and math.isfinite(float(r[k]))
 if r['dedup75']!=1:return False
 s=c['speed']
 if s!='all' and (not finite('speed_ratio') or not (r['speed_ratio']>=1 if s=='return_ge_outgoing' else r['speed_ratio']<1)):return False
 s=c['efficiency']
 if s!='all' and (not finite('return_efficiency') or r['return_efficiency']<(.5 if s=='ge_0.50' else .75)):return False
 s=c['flow']
 if s!='all':
  if not finite('return_imbalance_proxy_toward') or not finite('proxy_coverage') or r['proxy_coverage']<.8:return False
  v=r['return_imbalance_proxy_toward'];ok=v>0 if s=='toward_positive_cov80' else v>=.25 if s=='toward_ge_0.25_cov80' else v<0 if s=='away_negative_cov80' else v<=-.25
  if not ok:return False
 s=c['revisits']
 if s!='all' and (not finite('visits1') or r['visits1']<int(s[3:])):return False
 s=c['volume']
 if s!='all' and (not finite('volume_inside_fraction') or r['volume_inside_fraction']<(.25 if s.endswith('0.25') else .5)):return False
 s=c['density']
 if s!='all':
  if not finite('return_bars_per_tick'):return False
  v=r['return_bars_per_tick'];ok=v<=.5 if s=='le_0.5' else v<=1 if s=='le_1' else v>1
  if not ok:return False
 if c['gaps']=='gap_free' and r['prior_gap_count']!=0:return False
 return True
def independent_from_records(a,condition,dateid,nd):
 g=defaultdict(lambda:[[],[]]);rd=set();cd=set();rn=cn=0;triggers=set()
 for r in a:
  if not scalar_gate(r,condition) or r['status'] not in ['TARGET_FIRST','OPPOSITE_FIRST']:continue
  day=dateid[r['session']];o=0 if r['origin']=='real' else 1;win=int(r['status']=='TARGET_FIRST');span=min((r['volatility256_ticks'] if r['volatility256_ticks'] is not None else -40)//40,4);k=(day,int(r['hour'])//3,span,min(r['remaining_ticks']//10,8));g[k][o].append(win)
  if o==0:rn+=1;rd.add(day);triggers.add(int(r['trigger_idx']))
  else:cn+=1;cd.add(day)
 num=[0.]*nd;weights=[0.]*nd;common=0
 for k,(rr,cc) in g.items():
  if rr and cc:
   w=min(len(rr),len(cc));num[k[0]]+=w*(sum(rr)/len(rr)-sum(cc)/len(cc));weights[k[0]]+=w;common+=1
 total=sum(weights);effect=sum(num)/total if total else math.nan;score=[(n-effect*w)/total for n,w in zip(num,weights)] if total else [math.nan]*nd;se=math.sqrt(nd/(nd-1)*sum(s*s for s in score)) if total else math.nan;ok=rn>=100 and cn>=100 and min(len(rd),len(cd))>=math.ceil(.8*nd) and total>=50 and sum(w>0 for w in weights)>=math.ceil(.5*nd) and math.isfinite(se) and se>1e-12
 return dict(real_resolved=rn,control_resolved=cn,matched_weight=total,common_strata=common,effect=effect,se=se,eligible=ok,num=num,weights=weights,triggers=triggers)
