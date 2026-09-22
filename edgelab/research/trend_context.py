"""Causal closed-bar EMA/SMA/VWAP context for existing event carriers."""
from __future__ import annotations
import hashlib,json,math
from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Iterable
CONTRACT_VERSION="CAUSAL_TREND_CONTEXT_V1"
class TrendState(str,Enum):NOT_READY="NOT_READY";UP="UP";DOWN="DOWN";NEUTRAL="NEUTRAL"
class EventAlignment(str,Enum):NOT_READY="NOT_READY";WITH_TREND="WITH_TREND";COUNTER_TREND="COUNTER_TREND";NEUTRAL="NEUTRAL"
@dataclass(frozen=True,slots=True)
class TrendParameters:
 ema_fast:int=9;ema_slow:int=21;sma_fast:int=20;sma_slow:int=50;slope_lookback:int=3
 def __post_init__(self):
  if any(v<=0 for v in (self.ema_fast,self.ema_slow,self.sma_fast,self.sma_slow,self.slope_lookback)):raise ValueError("all trend parameters must be positive")
  if self.ema_fast>=self.ema_slow:raise ValueError("ema_fast must be less than ema_slow")
  if self.sma_fast>=self.sma_slow:raise ValueError("sma_fast must be less than sma_slow")
@dataclass(frozen=True,slots=True)
class TrendBar:
 ts_ns:int;session_id:str;close_ticks:float;volume:float;typical_price_ticks:float|None=None
 def __post_init__(self):
  if self.ts_ns<0:raise ValueError("ts_ns must be non-negative")
  if not self.session_id:raise ValueError("session_id is required")
  if not math.isfinite(float(self.close_ticks)):raise ValueError("close_ticks must be finite")
  if not math.isfinite(float(self.volume)) or self.volume<0:raise ValueError("volume must be finite and non-negative")
  if self.typical_price_ticks is not None and not math.isfinite(float(self.typical_price_ticks)):raise ValueError("typical_price_ticks must be finite")
@dataclass(frozen=True,slots=True)
class TrendContext:
 contract_version:str;ts_ns:int;available_at_ns:int;session_id:str;bar_index:int;session_bar_index:int;close_ticks:float;vwap_ticks:float|None;ema_fast_ticks:float;ema_slow_ticks:float;sma_fast_ticks:float|None;sma_slow_ticks:float|None;ema_slope_ticks:float|None;vwap_slope_ticks:float|None;close_minus_vwap_ticks:float|None;close_minus_ema_fast_ticks:float;close_minus_ema_slow_ticks:float;ema_state:TrendState;sma_state:TrendState;vwap_state:TrendState;trend_state:TrendState;digest:str
def compute_trend_contexts(bars:Iterable[TrendBar],*,params=TrendParameters(),availability_lag_ns=1):
 rows=list(bars)
 if availability_lag_ns<=0:raise ValueError("availability_lag_ns must be positive")
 if any(b.ts_ns<=a.ts_ns for a,b in zip(rows,rows[1:])):raise ValueError("bars must be strictly increasing by ts_ns")
 af,as_=2/(params.ema_fast+1),2/(params.ema_slow+1);ef=es=None;fw=deque(maxlen=params.sma_fast);sw=deque(maxlen=params.sma_slow);eh=[];sv=[];sid=None;sidx=-1;cv=cpv=0.;out=[]
 for idx,b in enumerate(rows):
  if b.session_id!=sid:sid=b.session_id;sidx=0;cv=cpv=0.;sv=[]
  else:sidx+=1
  c=float(b.close_ticks);ef=c if ef is None else af*c+(1-af)*ef;es=c if es is None else as_*c+(1-as_)*es;fw.append(c);sw.append(c);sf=None if len(fw)<params.sma_fast else sum(fw)/params.sma_fast;ss=None if len(sw)<params.sma_slow else sum(sw)/params.sma_slow
  if b.volume>0:tp=c if b.typical_price_ticks is None else float(b.typical_price_ticks);cpv+=tp*b.volume;cv+=b.volume
  vw=cpv/cv if cv>0 else None;eh.append(ef);sv.append(vw);e_sl=ef-eh[-1-params.slope_lookback] if len(eh)>params.slope_lookback else None;v_sl=vw-sv[-1-params.slope_lookback] if len(sv)>params.slope_lookback and vw is not None and sv[-1-params.slope_lookback] is not None else None
  ee=TrendState.NOT_READY if e_sl is None else TrendState.UP if ef>es and e_sl>0 else TrendState.DOWN if ef<es and e_sl<0 else TrendState.NEUTRAL;ssx=TrendState.NOT_READY if sf is None or ss is None else TrendState.UP if sf>ss else TrendState.DOWN if sf<ss else TrendState.NEUTRAL;vv=TrendState.NOT_READY if vw is None or v_sl is None else TrendState.UP if c>vw and v_sl>0 else TrendState.DOWN if c<vw and v_sl<0 else TrendState.NEUTRAL
  state=TrendState.NOT_READY if TrendState.NOT_READY in (ee,ssx,vv) else TrendState.UP if ee is ssx is vv is TrendState.UP else TrendState.DOWN if ee is ssx is vv is TrendState.DOWN else TrendState.NEUTRAL
  p=dict(contract_version=CONTRACT_VERSION,ts_ns=b.ts_ns,available_at_ns=b.ts_ns+availability_lag_ns,session_id=b.session_id,bar_index=idx,session_bar_index=sidx,close_ticks=c,vwap_ticks=vw,ema_fast_ticks=ef,ema_slow_ticks=es,sma_fast_ticks=sf,sma_slow_ticks=ss,ema_slope_ticks=e_sl,vwap_slope_ticks=v_sl,close_minus_vwap_ticks=c-vw if vw is not None else None,close_minus_ema_fast_ticks=c-ef,close_minus_ema_slow_ticks=c-es,ema_state=ee.value,sma_state=ssx.value,vwap_state=vv.value,trend_state=state.value);d=hashlib.sha256(json.dumps(p,sort_keys=True,separators=(",",":")).encode()).hexdigest();out.append(TrendContext(CONTRACT_VERSION,b.ts_ns,b.ts_ns+availability_lag_ns,b.session_id,idx,sidx,c,vw,ef,es,sf,ss,e_sl,v_sl,p["close_minus_vwap_ticks"],p["close_minus_ema_fast_ticks"],p["close_minus_ema_slow_ticks"],ee,ssx,vv,state,d))
 return out
def align_event_with_trend(direction,context,*,event_available_at_ns):
 if direction not in(-1,1):raise ValueError("continuation_direction must be +1 or -1")
 if event_available_at_ns<context.available_at_ns:raise ValueError("event precedes trend context availability")
 if context.trend_state is TrendState.NOT_READY:return EventAlignment.NOT_READY
 if context.trend_state is TrendState.NEUTRAL:return EventAlignment.NEUTRAL
 return EventAlignment.WITH_TREND if direction==(1 if context.trend_state is TrendState.UP else -1) else EventAlignment.COUNTER_TREND
