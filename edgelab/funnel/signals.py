"""Causal, target-free L1 signal families for the discovery funnel."""
from __future__ import annotations
import numpy as np
from numba import njit
@njit(cache=True)
def session_vwap_reclaim(close,volume,trade_date,min_bars=50,band_ticks=20):
 idx=np.empty(len(close),np.int64);dirs=np.empty(len(close),np.int8);n=0;pv=0.0;vv=0.0;bars=0;prev_c=0.0;prev_vwap=0.0
 for i in range(len(close)):
  if i==0 or trade_date[i]!=trade_date[i-1]:pv=0.0;vv=0.0;bars=0;prev_c=close[i];prev_vwap=close[i]
  pv+=close[i]*volume[i];vv+=volume[i];bars+=1;vwap=pv/max(vv,1.0)
  if bars>min_bars:
   if prev_c<prev_vwap-band_ticks and close[i]>=vwap:idx[n]=i;dirs[n]=1;n+=1
   elif prev_c>prev_vwap+band_ticks and close[i]<=vwap:idx[n]=i;dirs[n]=-1;n+=1
  prev_c=close[i];prev_vwap=vwap
 return idx[:n],dirs[:n]
@njit(cache=True)
def absorption_break(open_,high,low,close,volume,trade_date,lookback=100,volume_multiple=2.0,max_range_ticks=10):
 idx=np.empty(len(close),np.int64);dirs=np.empty(len(close),np.int8);n=0;buf=np.zeros(lookback,np.float64);pos=0;cnt=0;total=0.0;prev_abs=False;ph=0;pl=0
 for i in range(len(close)):
  if i==0 or trade_date[i]!=trade_date[i-1]:buf[:]=0;pos=0;cnt=0;total=0.0;prev_abs=False
  if prev_abs:
   if close[i]>ph:idx[n]=i;dirs[n]=1;n+=1
   elif close[i]<pl:idx[n]=i;dirs[n]=-1;n+=1
  mean=total/cnt if cnt else 0.0;is_abs=cnt>=lookback and volume[i]>=mean*volume_multiple and high[i]-low[i]<=max_range_ticks
  prev_abs=is_abs;ph=high[i];pl=low[i]
  if cnt<lookback:buf[pos]=volume[i];total+=volume[i];cnt+=1
  else:total-=buf[pos];buf[pos]=volume[i];total+=volume[i]
  pos=(pos+1)%lookback
 return idx[:n],dirs[:n]
@njit(cache=True)
def failed_auction_reentry(high,low,close,trade_date,opening_bars=100,max_session_bars=2000):
 idx=np.empty(len(close),np.int64);dirs=np.empty(len(close),np.int8);n=0;bars=0;rh=0;rl=0;was_above=False;was_below=False
 for i in range(len(close)):
  if i==0 or trade_date[i]!=trade_date[i-1]:bars=0;rh=high[i];rl=low[i];was_above=False;was_below=False
  bars+=1
  if bars<=opening_bars:
   if high[i]>rh:rh=high[i]
   if low[i]<rl:rl=low[i]
   continue
  if bars>max_session_bars:continue
  above=close[i]>rh;below=close[i]<rl
  if was_above and close[i]<=rh:idx[n]=i;dirs[n]=-1;n+=1
  elif was_below and close[i]>=rl:idx[n]=i;dirs[n]=1;n+=1
  was_above=above;was_below=below
 return idx[:n],dirs[:n]
