"""Causal first-departure and first-D-qualifying departure; finite formation wait.
Endpoint 0=edge,1=integer center,2=one tick beyond far edge. Outcome starts next
record; skipped excursions only if they never reached D. No hindsight extrema.
"""
import numpy as np
from numba import njit
STATUS={0:'ANCHOR_OUTSIDE',1:'NO_DEPARTURE',2:'NO_TRIGGER_SESSION_END',3:'TOUCH_BEFORE_OBSERVED_TRIGGER',4:'TARGET_FIRST',5:'OPPOSITE_FIRST',6:'UNRESOLVED_HORIZON',7:'UNRESOLVED_GAP',8:'UNRESOLVED_SESSION_END',9:'NO_SIGNAL_GAP',10:'NO_TRIGGER_WAIT_LIMIT'}
@njit(cache=True)
def evaluate(px,ts,bar,anchor,end,low,high,D,q,endpoint,mode,horizon=2000,wait=2000,gap=10000000000):
 # status,exit,peak,trigger,last_observed,side,peakD,target,opposite,skipped
 if not low<=px[anchor]<=high:return 0,-1,-1,-1,anchor,0,0,0,0,0
 ex=-1;pk=-1;peak=0;side=0;edge=0;skipped=0;any_exit=False
 for i in range(anchor+1,end):
  if bar[i]-bar[anchor]>wait:return 10,ex,pk,-1,i-1,side,peak,0,0,skipped
  if ts[i]-ts[i-1]>gap:return 9,ex,pk,-1,i-1,side,peak,0,0,skipped
  if ex<0:
   if low<=px[i]<=high:continue
   ex=i;pk=i;side=1 if px[i]>high else -1;edge=high if side==1 else low;peak=side*(px[i]-edge);any_exit=True;continue
  x=side*(px[i]-edge)
  if x<=0:
   if mode==1 and peak<D:
    skipped+=1;ex=-1;pk=-1;peak=0;side=0
    # If a jump crosses whole zone, next exit must start from an observed inside
    # observation. Current opposite-side tick is not a free new departure.
    if not low<=px[i]<=high:return 3,-1,-1,-1,i,0,0,0,0,skipped
    continue
   return 3,ex,pk,-1,i,side,peak,0,0,skipped
  if x>peak:peak=x;pk=i
  if peak<D or x>peak*(1-q):continue
  target=edge if endpoint==0 else (low+high)//2 if endpoint==1 else low-1 if side==1 else high+1
  dist=side*(px[i]-target);opp=px[i]+side*dist
  assert dist>0
  for j in range(i+1,end):
   if bar[j]-bar[i]>horizon:return 6,ex,pk,i,j-1,side,peak,target,opp,skipped
   if ts[j]-ts[j-1]>gap:return 7,ex,pk,i,j-1,side,peak,target,opp,skipped
   if side*(px[j]-target)<=0:return 4,ex,pk,i,j,side,peak,target,opp,skipped
   if side*(px[j]-opp)>=0:return 5,ex,pk,i,j,side,peak,target,opp,skipped
  return 8,ex,pk,i,end-1,side,peak,target,opp,skipped
 return (2 if any_exit else 1),ex,pk,-1,end-1,side,peak,0,0,skipped

def reference(px,ts,bar,anchor,end,low,high,D,q,endpoint,mode,horizon=2000,wait=2000,gap=10000000000):
 """Unoptimized independent list/state implementation for ordered tapes."""
 if px[anchor]<low or px[anchor]>high:return (0,-1,-1,-1,anchor,0,0,0,0,0)
 exits=[];k=anchor+1;skips=0
 while k<end:
  if bar[k]-bar[anchor]>wait:return (10,-1,-1,-1,k-1,0,0,0,0,skips) if not exits else _waiting(exits[-1],10,k-1,skips)
  if ts[k]-ts[k-1]>gap:return (9,-1,-1,-1,k-1,0,0,0,0,skips) if not exits else _waiting(exits[-1],9,k-1,skips)
  if low<=px[k]<=high:k+=1;continue
  start=k;direction=1 if px[k]>high else -1;boundary=high if direction>0 else low
  points=[(k,direction*(px[k]-boundary))];exits.append([start,k,points[0][1],direction]);k+=1
  rearm=False
  while k<end:
   maximum=max(d for _,d in points);pki=next(idx for idx,d in points if d==maximum);exits[-1]=[start,pki,maximum,direction]
   if bar[k]-bar[anchor]>wait:return _waiting(exits[-1],10,k-1,skips)
   if ts[k]-ts[k-1]>gap:return _waiting(exits[-1],9,k-1,skips)
   displacement=direction*(px[k]-boundary)
   if displacement<=0:
    if mode==1 and maximum<D and low<=px[k]<=high:skips+=1;rearm=True;exits=[];k+=1;break
    if mode==1 and maximum<D:skips+=1;return (3,-1,-1,-1,k,0,0,0,0,skips)
    return _waiting(exits[-1],3,k,skips)
   points.append((k,displacement));maximum=max(d for _,d in points);pki=next(idx for idx,d in points if d==maximum);exits[-1]=[start,pki,maximum,direction]
   if maximum>=D and displacement<=maximum*(1-q):
    tgt=boundary if endpoint==0 else (low+high)//2 if endpoint==1 else low-1 if direction>0 else high+1
    opposite=px[k]+direction*abs(px[k]-tgt)
    base=(start,pki,k,direction,maximum,tgt,opposite,skips)
    for j in range(k+1,end):
     status=6 if bar[j]-bar[k]>horizon else 7 if ts[j]-ts[j-1]>gap else 4 if direction*(px[j]-tgt)<=0 else 5 if direction*(px[j]-opposite)>=0 else None
     if status is not None:return (status,*base[:3],j-1 if status in (6,7) else j,*base[3:])
    return (8,*base[:3],end-1,*base[3:])
   k+=1
  if not rearm:return _waiting(exits[-1],2,end-1,skips)
 return (2 if exits else 1,-1,-1,-1,end-1,0,0,0,0,skips) if not exits else _waiting(exits[-1],2,end-1,skips)
def _waiting(state,status,last,skips):
 a,b,d,s=state;return status,a,b,-1,last,s,d,0,0,skips
