"""Exploratory SEQUENCE_CAUSAL_25_LAST_RECORDS adapter. NOT legacy NT8 subseries.
Every footprint uses the actual records of a CLOSED25-record bar. Prices integer
MNQ ticks. Session-short bars retained for calibration but not event origins.
One first departure from a frozen zone; actual observed retracement trigger.
No price outcomes before trigger, no fills/P&L or reserve. Unknown flow stays unknown.
"""
from types import SimpleNamespace
import numpy as np
from numba import njit
STATUS={0:'ANCHOR_OUTSIDE',1:'NO_DEPARTURE',2:'NO_TRIGGER_SESSION_END',3:'TOUCH_BEFORE_OBSERVED_TRIGGER',4:'TARGET_FIRST',5:'OPPOSITE_FIRST',6:'UNRESOLVED_HORIZON',7:'UNRESOLVED_GAP',8:'UNRESOLVED_SESSION_END',9:'NO_SIGNAL_GAP'}
@njit(cache=True)
def csr(px,vol,starts,ends):
 n=len(px);off=np.empty(len(starts)+1,np.int64);ft=np.empty(n,np.int64);fv=np.empty(n,np.float64);off[0]=0;k=0
 scratch=np.empty(25,np.int64);vs=np.empty(25,np.float64)
 for b in range(len(starts)):
  size=ends[b]-starts[b]
  for j in range(size):scratch[j]=px[starts[b]+j];vs[j]=vol[starts[b]+j]
  for j in range(1,size):
   key=scratch[j];value=vs[j];i=j-1
   while i>=0 and scratch[i]>key:scratch[i+1]=scratch[i];vs[i+1]=vs[i];i-=1
   scratch[i+1]=key;vs[i+1]=value
  for j in range(size):
   if j and scratch[j]==scratch[j-1]:fv[k-1]+=vs[j]
   else:ft[k]=scratch[j];fv[k]=vs[j];k+=1
  off[b+1]=k
 return off,ft[:k],fv[:k]

def build_bars(ts,px,vol,sid):
 ss=np.r_[0,np.flatnonzero(sid[1:]!=sid[:-1])+1];ee=np.r_[ss[1:],len(ts)]
 starts=np.concatenate([np.arange(a,z,25,dtype=np.int64) for a,z in zip(ss,ee)])
 ends=np.minimum(starts+25,np.repeat(ee,[(z-a+24)//25 for a,z in zip(ss,ee)]));idx=np.repeat(np.arange(len(starts)),ends-starts)
 bars=SimpleNamespace(start_ns=ts[starts],end_ns=ts[ends-1],open_t=px[starts],close_t=px[ends-1],high_t=np.maximum.reduceat(px,starts),low_t=np.minimum.reduceat(px,starts),volume=np.add.reduceat(vol.astype(np.float64),starts),tick_bar_idx=idx)
 off,ft,fv=csr(px,vol,starts,ends);fps=SimpleNamespace(offsets=off,ticks=ft,vols=fv)
 assert np.array_equal(np.add.reduceat(fv,off[:-1]),bars.volume)
 assert np.all(sid[starts]==sid[ends-1]);assert np.all((ends-starts>=1)&(ends-starts<=25))
 return bars,fps,starts,ends,ss,ee

@njit(cache=True)
def passage(px,ts,bar,anchor,end,low,high,min_distance,q,endpoint=0,horizon=2000,gap_ns=-1):
 # tuple: status, exit_idx, peak_idx, trigger_idx, outcome_idx, side, R, target, opposite
 if px[anchor]<low or px[anchor]>high:return 0,-1,-1,-1,-1,0,0,0,0
 exit_i=-1
 for i in range(anchor+1,end):
  if gap_ns>=0 and ts[i]-ts[i-1]>gap_ns:return 9,-1,-1,-1,-1,0,0,0,0
  if px[i]>high or px[i]<low:exit_i=i;break
 if exit_i<0:return 1,-1,-1,-1,-1,0,0,0,0
 side=1 if px[exit_i]>high else -1;edge=high if side==1 else low;peak_i=exit_i;peak=side*(px[exit_i]-edge)
 for i in range(exit_i+1,end):
  if gap_ns>=0 and ts[i]-ts[i-1]>gap_ns:return 9,exit_i,peak_i,-1,-1,side,peak,0,0
  x=side*(px[i]-edge)
  if x<=0:return 3,exit_i,peak_i,-1,-1,side,peak,0,0
  if x>peak:peak=x;peak_i=i
  if peak<min_distance or x>peak*(1-q):continue
  target=edge if endpoint==0 else edge-side if endpoint==1 else low-1 if side==1 else high+1
  distance=side*(px[i]-target);opposite=px[i]+side*distance
  for u in range(i+1,end):
   if bar[u]-bar[i]>horizon:return 6,exit_i,peak_i,i,-1,side,peak,target,opposite
   if gap_ns>=0 and ts[u]-ts[u-1]>gap_ns:return 7,exit_i,peak_i,i,-1,side,peak,target,opposite
   if side*(px[u]-target)<=0:return 4,exit_i,peak_i,i,u,side,peak,target,opposite
   if side*(px[u]-opposite)>=0:return 5,exit_i,peak_i,i,u,side,peak,target,opposite
  return 8,exit_i,peak_i,i,-1,side,peak,target,opposite
 return 2,exit_i,peak_i,-1,-1,side,peak,0,0

def fail_closed_events(events,allowed):
 for e in events:
  if (e['contract'],e['session']) not in allowed:raise ValueError('EVENT_OUTSIDE_SELECTED_UNIVERSE')
 return True
