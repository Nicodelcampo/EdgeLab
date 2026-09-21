"""Causal density-field and liquidity-corridor primitives for YM/BT2A.

Only attributes known at zone formation are admitted. Lifecycle fields such as
future touches, final state, invalidation and end time are intentionally absent.
"""
from __future__ import annotations
from dataclasses import dataclass
from math import exp, sqrt
from typing import Iterable, Sequence
import numpy as np
MAX_ZONE_AGE_NS=48*60*60*1_000_000_000
@dataclass(frozen=True)
class CausalZone:
 zone_id:str;available_idx:int;available_ns:int;lo_ticks:float;hi_ticks:float;direction:str;volume:float;rows:int;trap_fraction:float;score:float;threshold:float
 @property
 def strength_ratio(self):return self.score/self.threshold if self.threshold>0 else 0.0
@dataclass(frozen=True)
class CorridorPolicy:
 policy_id:str;field_mode:str;sigma_ticks:float;void_max:float;wall_min:float;backstop_min:float;width_lo:int;width_hi:int;momentum_lookback:int;momentum_min:int;strength_min:float
@dataclass(frozen=True)
class CorridorObservation:
 wall_distance:int|None;interior_mean:float|None;backstop_max:float;momentum_ticks:float;strength_ratio:float
def causal_zone_from_bt2(zone,ts_ns):
 idx=int(zone['sig_idx']);direction=str(zone['dir'])
 if direction not in {'long','short'}:raise ValueError('unknown direction')
 lo,hi=sorted((float(zone['lo']),float(zone['hi'])))
 return CausalZone(str(zone['id']),idx,int(ts_ns[idx]),lo,hi,direction,float(zone.get('vol',0)),int(zone.get('nrows',0)),float(zone.get('frac',0)),float(zone.get('a_score',0)),float(zone.get('a_thr',0)))
def zone_weight(zone):
 volume=min(3,max(.25,sqrt(max(zone.volume,1)/10)));rows=min(2,max(.5,sqrt(max(zone.rows,1)/2)));score=min(2,max(.5,zone.strength_ratio));fraction=min(1.5,max(.5,zone.trap_fraction/.2 if zone.trap_fraction else .5));return volume*rows*score*fraction
def density_profile(zones:Iterable[CausalZone],*,asof_idx,asof_ns,origin_price_ticks,trade_direction,offsets:Sequence[int],sigma_ticks,scope):
 if trade_direction not in {'long','short'}:raise ValueError('bad direction')
 if scope not in {'total','opposition','support'}:raise ValueError('bad scope')
 if sigma_ticks<=0:raise ValueError('sigma must be positive')
 sign=1 if trade_direction=='long' else-1;prices=origin_price_ticks+sign*np.asarray(offsets,dtype=float);field=np.zeros(len(prices));denom=2*sigma_ticks*sigma_ticks;cutoff=4*sigma_ticks
 for z in zones:
  if z.available_idx>asof_idx or z.available_ns>asof_ns:continue
  if asof_ns-z.available_ns>MAX_ZONE_AGE_NS:continue
  if scope=='opposition' and z.direction==trade_direction:continue
  if scope=='support' and z.direction!=trade_direction:continue
  dist=np.where(prices<z.lo_ticks,z.lo_ticks-prices,np.where(prices>z.hi_ticks,prices-z.hi_ticks,0.0));mask=dist<=cutoff
  if np.any(mask):field[mask]+=zone_weight(z)*np.exp(-(dist[mask]**2)/denom)
 return 1-np.exp(-field)
def observe_corridor(*,total,opposition,support_back,wall_min,field_mode,momentum_ticks,strength_ratio):
 if len(total)!=len(opposition):raise ValueError('profile length mismatch')
 if field_mode not in {'TOTAL','DIRECTIONAL'}:raise ValueError('bad field mode')
 w=np.flatnonzero(opposition[4:]>=wall_min)
 if not w.size:return CorridorObservation(None,None,float(np.max(support_back)),momentum_ticks,strength_ratio)
 wall=4+int(w[0]);interior=total if field_mode=='TOTAL' else opposition;mean=float(np.mean(interior[1:wall])) if wall>1 else float(interior[0]);return CorridorObservation(wall,mean,float(np.max(support_back)),momentum_ticks,strength_ratio)
def policy_matches(policy,obs):
 return bool(obs.wall_distance is not None and obs.interior_mean is not None and policy.width_lo<=obs.wall_distance<=policy.width_hi and obs.interior_mean<=policy.void_max and obs.backstop_max>=policy.backstop_min and obs.momentum_ticks>=policy.momentum_min and obs.strength_ratio>=policy.strength_min)
def corridor_policy_grid_v1():
 out=[];widths=((4,7),(8,14),(15,30),(4,30))
 for mode in('TOTAL','DIRECTIONAL'):
  for sigma in(1.,2.,4.):
   for void in(.15,.30):
    for wall in(.50,.70):
     for back in(.30,.50):
      for lo,hi in widths:
       for lookback in(5,25):
        for momentum in(0,2,4):
         for strength in(1.,1.25):
          pid=f"C_{mode[0]}_S{int(sigma)}_V{int(void*100)}_W{int(wall*100)}_B{int(back*100)}_R{lo}-{hi}_L{lookback}_M{momentum}_Q{int(strength*100)}";out.append(CorridorPolicy(pid,mode,sigma,void,wall,back,lo,hi,lookback,momentum,strength))
 assert len(out)==2304;return out
