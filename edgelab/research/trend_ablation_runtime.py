"""Target-free runtime for real and placebo trend ablation cells."""
from __future__ import annotations
import hashlib,random
from collections import Counter
from dataclasses import dataclass
from edgelab.research.trend_ablation import ContextCell
from edgelab.research.trend_carriers import TrendCarrier
from edgelab.research.trend_context import EventAlignment,TrendContext,TrendState
@dataclass(frozen=True,slots=True)
class AblationObservation:
 context_cell:ContextCell; state:TrendState|None; alignment:EventAlignment|None; execution_eligible:bool; placebo:bool
def shuffle_states_within_session(contexts,*,seed:int,replicate:int):
 if seed<0 or replicate<0: raise ValueError("seed and replicate must be non-negative")
 rows=list(contexts); out={}
 for session in sorted({r.session_id for r in rows}):
  group=[r for r in rows if r.session_id==session]
  if len({r.digest for r in group})!=len(group): raise ValueError("context digests must be unique")
  states=[r.trend_state for r in group]; material=f"{seed}:{replicate}:{session}:"+":".join(r.digest for r in group); rng=random.Random(int(hashlib.sha256(material.encode()).hexdigest(),16)); rng.shuffle(states); out.update({r.digest:s for r,s in zip(group,states)})
  if Counter(states)!=Counter(r.trend_state for r in group): raise AssertionError("shuffle changed state counts")
 return out
def _align(direction,state):
 if state is TrendState.NOT_READY:return EventAlignment.NOT_READY
 if state is TrendState.NEUTRAL:return EventAlignment.NEUTRAL
 return EventAlignment.WITH_TREND if direction==(1 if state is TrendState.UP else -1) else EventAlignment.COUNTER_TREND
def evaluate_cell(carrier:TrendCarrier,context:TrendContext,cell:ContextCell,*,shuffled_states=None):
 if carrier.session_id!=context.session_id: raise ValueError("carrier/context session mismatch")
 if carrier.available_at_ns<context.available_at_ns: raise ValueError("context is not causally available")
 if cell is ContextCell.CARRIER_ONLY:return AblationObservation(cell,None,None,True,False)
 if cell is ContextCell.EMA_ONLY:state=context.ema_state
 elif cell is ContextCell.SMA_ONLY:state=context.sma_state
 elif cell is ContextCell.VWAP_ONLY:state=context.vwap_state
 elif cell is ContextCell.ALL_COMPONENTS:state=context.trend_state
 else:
  if shuffled_states is None or context.digest not in shuffled_states: raise ValueError("shuffled state is required")
  state=shuffled_states[context.digest]; return AblationObservation(cell,state,_align(carrier.continuation_direction,state),False,True)
 return AblationObservation(cell,state,_align(carrier.continuation_direction,state),True,False)
