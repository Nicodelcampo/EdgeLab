"""Exact legacy racimo replay optimized with sliding interval support.
Pure causal replay, identical candidate order/ties/bindings/geometry. Birth tuple:
(bar,start0,low0,high0). Allocation min/max only, never a signal feature.
"""
import numpy as np
from numba import njit
@njit(cache=True)
def replay(bars,lo,hi,min_zones,window,height):
 n=len(bars)
 if n==0:return np.empty((0,4),np.int64)
 origin=int(lo.min())-height-2;width=int(hi.max())-origin+height+3
 support=np.zeros(width,np.int64);low_count=np.zeros(width,np.int64);latest=np.full(width,-1,np.int64);membership=np.full(n,-1,np.int64)
 cllo=np.empty(n,np.int64);clhi=np.empty(n,np.int64);clstart=np.empty(n,np.int64);births=np.empty((n,4),np.int64);nb=0;first=0;inside=np.empty(n,np.int64)
 for i in range(n):
  while first<i and bars[i]-bars[first]>window:
   if hi[first]-lo[first]+1<=height:
    for base in range(hi[first]-height+1,lo[first]+1):support[base-origin]-=1
   low_count[lo[first]-origin]-=1;first+=1
  previous_latest=latest[lo[i]-origin] if low_count[lo[i]-origin]>0 else -1
  if hi[i]-lo[i]+1<=height:
   for base in range(hi[i]-height+1,lo[i]+1):support[base-origin]+=1
  low_count[lo[i]-origin]+=1;latest[lo[i]-origin]=i
  best_count=-1;best_rank=-2;best_base=0
  for base in range(hi[i]-height+1,lo[i]+1):
   if low_count[base-origin]==0:continue
   rank=previous_latest if base==lo[i] else latest[base-origin];count=support[base-origin]
   if count>best_count or (count==best_count and rank>best_rank):best_count=count;best_rank=rank;best_base=base
  if best_count<min_zones:continue
  k=0;bottom=2147483647;top=-2147483647;start=bars[i]
  for j in range(i-1,first-1,-1):
   if lo[j]>=best_base and hi[j]<=best_base+height-1:
    inside[k]=j;k+=1;bottom=min(bottom,lo[j]);top=max(top,hi[j]);start=min(start,bars[j])
  inside[k]=i;k+=1;bottom=min(bottom,lo[i]);top=max(top,hi[i]);start=min(start,bars[i])
  assert k==best_count
  chosen=-1
  for pos in range(k):
   m=membership[inside[pos]]
   if m>=0 and max(top,clhi[m])-min(bottom,cllo[m])+1<=height:chosen=m;break
  if chosen<0:
   chosen=nb;cllo[nb]=bottom;clhi[nb]=top;clstart[nb]=start;births[nb,0]=bars[i];births[nb,1]=start;births[nb,2]=bottom;births[nb,3]=top;nb+=1
  else:cllo[chosen]=min(cllo[chosen],bottom);clhi[chosen]=max(clhi[chosen],top);clstart[chosen]=min(clstart[chosen],start)
  for pos in range(k):
   j=inside[pos]
   if membership[j]<0:membership[j]=chosen
 return births[:nb]
