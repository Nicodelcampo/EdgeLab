"""Causal order-flow confirmation at a previously formed density wall."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Sequence
import numpy as np
@dataclass(frozen=True)
class FlowConfirmation:
 trigger_idx:int;confirmation_idx:int;fill_idx:int;aligned_imbalance:float;wall_prints:int;rejection_ticks:float
def aggressor_sign(price,bid,ask):
 price=np.asarray(price);bid=np.asarray(bid);ask=np.asarray(ask);valid=(bid>0)&(ask>=bid);out=np.zeros(len(price),dtype=np.int8);out[valid&(price>=ask)]=1;out[valid&(price<=bid)]=-1;return out
def confirm_rejection(*,trigger_idx:int,lo:float,hi:float,direction:str,price:Sequence[float],bid:Sequence[float],ask:Sequence[float],volume:Sequence[float],sessions:Sequence[int],observation_ticks:int,rejection_min:float,imbalance_min:float,wall_prints_min:int):
 if direction not in {'long','short'}:raise ValueError('bad direction')
 p=np.asarray(price);b=np.asarray(bid);a=np.asarray(ask);v=np.asarray(volume,dtype=float);s=np.asarray(sessions);end=min(len(p),trigger_idx+observation_ticks)
 if trigger_idx>=len(p)-1:return None
 cut=np.flatnonzero(s[trigger_idx:end]!=s[trigger_idx])
 if cut.size:end=trigger_idx+int(cut[0])
 signs=aggressor_sign(p[trigger_idx:end],b[trigger_idx:end],a[trigger_idx:end]);buy=sell=0.;prints=0;anchor=float(p[trigger_idx]);d=1. if direction=='long' else-1.
 for off,j in enumerate(range(trigger_idx,end)):
  if lo<=p[j]<=hi:prints+=1
  if signs[off]>0:buy+=float(v[j])
  elif signs[off]<0:sell+=float(v[j])
  total=buy+sell;aligned=d*(buy-sell)/total if total>0 else 0.;rejection=d*(float(p[j])-anchor)
  if rejection>=rejection_min and aligned>=imbalance_min and prints>=wall_prints_min:
   fill=j+1
   if fill>=len(p)or s[fill]!=s[trigger_idx]:return None
   return FlowConfirmation(trigger_idx,j,fill,aligned,prints,rejection)
 return None
def wall_contact_policy_grid_v1():
 out=[]
 for sigma in(1.,4.):
  for density in(.7,.9):
   for conf in(2,3):
    for dep in(4,8):
     for depth in(0.,.5):
      for wait in(250,1000):
       for obs in(5,25):
        for reject in(1,2,4):
         for imbalance in(0.,.15,.30):
          for prints in(1,3,5):
           pid=f"OF_S{int(sigma)}_D{int(density*100)}_C{conf}_X{dep}_Z{int(depth*100)}_W{wait}_O{obs}_R{reject}_I{int(imbalance*100)}_P{prints}";out.append((pid,sigma,density,conf,dep,depth,wait,obs,reject,imbalance,prints))
 assert len(out)==3456;return out
