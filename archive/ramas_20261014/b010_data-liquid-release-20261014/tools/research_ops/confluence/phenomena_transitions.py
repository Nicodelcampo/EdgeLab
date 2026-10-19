"""Engineering prototype: causal proxy-state paths, no outcomes/source loader."""
from datetime import date as Date
from .asof_intersections import Clock
from .phenomena_states import STATES
class StatePath:
 def __init__(self,*,max_gap_ns=10000000000,cap_seconds=120):
  if type(max_gap_ns) is not int or max_gap_ns<1 or type(cap_seconds) is not int or cap_seconds<1:raise ValueError('finite transition clock bounds')
  self.gap=max_gap_ns;self.cap=cap_seconds;self.clock=None;self.date=None;self.state=None;self.started=None;self.events={};self.count=0;self.direction=None
 def push(self,clock,trade_date,state,*,direction=None):
  if not isinstance(clock,Clock) or state not in STATES:raise ValueError('observed clock and declared proxy state')
  if direction is not None and (type(direction) is not int or direction not in (-1,1)):raise ValueError('observed signed orientation')
  if Date.fromisoformat(trade_date).isoformat()!=trade_date:raise ValueError('canonical natural trade date')
  if self.clock is not None and clock<=self.clock:raise ValueError('strict transition prefix no future or rewind')
  broken=self.clock is None or trade_date!=self.date or clock.ns-self.clock.ns>self.gap or self.state=='UNKNOWN' or state=='UNKNOWN' or direction!=self.direction
  if broken:self.events={};self.started=clock.ns;previous=None
  else:previous=self.state
  if state!=self.state:self.started=clock.ns
  transition='A_TO_E' if previous=='A_ONLY' and state=='E_ONLY' else 'E_TO_A' if previous=='E_ONLY' and state=='A_ONLY' else None
  if transition:self.events[transition]=clock.ns
  self.clock=clock;self.date=trade_date;self.state=state;self.direction=direction;self.count+=1
  out={'known':state!='UNKNOWN','state':state,'duration_seconds':min(self.cap,(clock.ns-self.started)/1e9) if state!='UNKNOWN' else None,'continuity_broken':broken,'transition_observed_now':transition}
  for name in ('A_TO_E','E_TO_A'):
   elapsed=(clock.ns-self.events[name])/1e9 if name in self.events else None
   out[name+'_observed_within_cap']=elapsed is not None and elapsed<=self.cap
   out[name+'_elapsed_seconds']=elapsed if elapsed is not None and elapsed<=self.cap else None
  return out
