"""Causal landmarks/revisits on frozen zones; no final lifespan conditioning."""
import numpy as np
from numba import njit
@njit(cache=True)
def first_visit(px,ts,bar,marker,stop,low,high,wait=2000,gap=10000000000):
 for i in range(marker,stop):
  if bar[i]-bar[marker]>wait:return -1,2
  if i>marker and ts[i]-ts[i-1]>gap:return -1,3
  if low<=px[i]<=high:return i,0
 return -1,1
@njit(cache=True)
def dedup_masks(birth,session,threshold):
 keep=np.zeros(len(birth),np.bool_);saved=np.empty(len(birth),np.int64);n=0;last=-1
 for i in range(len(birth)):
  d=session[birth[i,0]]
  if d!=last:n=0;last=d
  lo=birth[i,2];hi=birth[i,3];ok=True
  for j in range(n):
   x=saved[j];inter=max(0,min(hi,birth[x,3])-max(lo,birth[x,2])+1);union=max(hi,birth[x,3])-min(lo,birth[x,2])+1
   if inter/union>=threshold:ok=False;break
  if ok:keep[i]=True;saved[n]=i;n+=1
 return keep
@njit(cache=True)
def features(px,ts,vol,flow,bar,st,en,birth_b,birth_i,tr,ex,pk,side,peak,target,low,high):
 # Visits require actual inside prints in CLOSED bars; range crossing alone is insufficient.
 counts=np.zeros(3,np.int64);seen=low<=px[birth_i]<=high;outside=0;last_inside=-1;clock_exit=-1
 for b in range(birth_b+1,bar[tr]):
  inside=False;first=-1;last=-1
  for i in range(st[b],en[b]):
   if low<=px[i]<=high:
    inside=True
    if first<0:first=i
    last=i
  if inside:
   if not seen:seen=True
   else:
    if outside>=1:counts[0]+=1
    if outside>=5:counts[1]+=1
    if clock_exit>=0 and ts[first]-clock_exit>=10000000000:counts[2]+=1
   outside=0;last_inside=last;clock_exit=-1
  else:
   outside+=1
   if clock_exit<0:clock_exit=ts[st[b]]
 total=0.;inside_vol=0.;seconds_inside=0.;gaps=0
 for i in range(birth_i+1,tr+1):
  total+=vol[i]
  if low<=px[i]<=high:inside_vol+=vol[i]
  dt=ts[i]-ts[i-1]
  if dt>10000000000:gaps+=1
  elif low<=px[i-1]<=high:seconds_inside+=dt/1e9
 out_sec=(ts[pk]-ts[ex-1])/1e9;back_sec=(ts[tr]-ts[pk])/1e9;edge=high if side>0 else low;back=peak-side*(px[tr]-edge)
 speed=(back/back_sec)/(peak/out_sec) if back_sec>0 and out_sec>0 else np.nan
 path=0.;v=0.;known=0.;signed=0.
 for i in range(pk+1,tr+1):
  path+=abs(px[i]-px[i-1]);v+=vol[i];known+=vol[i]*(flow[i]!=0);signed+=vol[i]*flow[i]
 return (counts[0],counts[1],counts[2],inside_vol/total if total else np.nan,seconds_inside,(ts[tr]-ts[last_inside])/1e9 if last_inside>=0 else np.nan,gaps,speed,back_sec,(bar[tr]-bar[pk]+1)/back if back else np.nan,back/path if path else np.nan,-side*signed/v if v and known else np.nan,known/v if v else np.nan,abs(px[tr]-target),bar[tr]-birth_b,(ts[tr]-ts[birth_i])/1e9)

@njit(cache=True)
def build_cache(px,ts,vol,flow,bar,st,en,b0,i0,stop,low,high):
 n=stop-i0;nb=bar[stop-1]-b0+1
 total=np.zeros(n);inside=np.zeros(n);secs=np.zeros(n);gaps=np.zeros(n,np.int64);signed=np.zeros(n);known=np.zeros(n);path=np.zeros(n)
 for j in range(1,n):
  i=i0+j;total[j]=total[j-1]+vol[i];inside[j]=inside[j-1]+vol[i]*(low<=px[i]<=high);dt=ts[i]-ts[i-1];secs[j]=secs[j-1]+(dt/1e9 if dt<=10000000000 and low<=px[i-1]<=high else 0);gaps[j]=gaps[j-1]+(dt>10000000000);signed[j]=signed[j-1]+vol[i]*flow[i];known[j]=known[j-1]+vol[i]*(flow[i]!=0);path[j]=path[j-1]+abs(px[i]-px[i-1])
 visits=np.zeros((nb,3),np.int64);lasts=np.full(nb,-1,np.int64);cnt=np.zeros(3,np.int64);seen=low<=px[i0]<=high;outside=0;last=-1;clock_exit=-1
 for b in range(b0+1,b0+nb):
  visits[b-b0]=cnt;lasts[b-b0]=last
  hit=False;first=-1;end=-1
  for i in range(st[b],min(en[b],stop)):
   if low<=px[i]<=high:
    hit=True
    if first<0:first=i
    end=i
  if hit:
   if not seen:seen=True
   else:
    if outside>=1:cnt[0]+=1
    if outside>=5:cnt[1]+=1
    if clock_exit>=0 and ts[first]-clock_exit>=10000000000:cnt[2]+=1
   outside=0;last=end;clock_exit=-1
  else:
   outside+=1
   if clock_exit<0:clock_exit=ts[st[b]]
 return total,inside,secs,gaps,signed,known,path,visits,lasts
@njit(cache=True)
def cached_features(px,ts,bar,b0,i0,tr,ex,pk,side,peak,target,low,high,cache):
 total,inside,secs,gaps,signed,known,path,visits,lasts=cache;j=tr-i0;k=pk-i0;bb=bar[tr]-b0;last=lasts[bb];out_sec=(ts[pk]-ts[ex-1])/1e9;back_sec=(ts[tr]-ts[pk])/1e9;edge=high if side>0 else low;back=peak-side*(px[tr]-edge);speed=(back/back_sec)/(peak/out_sec) if back_sec>0 and out_sec>0 else np.nan;v=total[j]-total[k];kv=known[j]-known[k];sv=signed[j]-signed[k];pa=path[j]-path[k]
 return (visits[bb,0],visits[bb,1],visits[bb,2],inside[j]/total[j] if total[j] else np.nan,secs[j],(ts[tr]-ts[last])/1e9 if last>=0 else np.nan,gaps[j],speed,back_sec,(bar[tr]-bar[pk]+1)/back if back else np.nan,back/pa if pa else np.nan,-side*sv/v if v and kv else np.nan,kv/v if v else np.nan,abs(px[tr]-target),bar[tr]-b0,(ts[tr]-ts[i0])/1e9)
