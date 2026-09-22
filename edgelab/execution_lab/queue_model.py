"""Conservative fail-closed FIFO passive-fill model over observed L2 events."""
from __future__ import annotations
import hashlib,json
from dataclasses import asdict,dataclass,field
from enum import Enum
from typing import Iterable
CONTRACT_VERSION="QUEUE_FIFO_L2_V1"
class Side(str,Enum):BID="BID";ASK="ASK"
class EventKind(str,Enum):SNAPSHOT="SNAPSHOT";ADD="ADD";CANCEL="CANCEL";EXECUTE="EXECUTE";RESET="RESET"
class AbstainReason(str,Enum):
 NO_ACTIVATION_EVENT="NO_ACTIVATION_EVENT";NO_DEPTH_AT_ACTIVATION="NO_DEPTH_AT_ACTIVATION";SEQUENCE_GAP="SEQUENCE_GAP";BOOK_RESET="BOOK_RESET";ACTIVATION_LEVEL_MISMATCH="ACTIVATION_LEVEL_MISMATCH"
@dataclass(frozen=True,slots=True)
class BookEvent:
 sequence:int;ts_ns:int;kind:EventKind;side:Side;price_ticks:int;quantity:int;level_depth_after:int|None=None
 def __post_init__(self):
  if self.sequence<0 or self.ts_ns<0:raise ValueError("sequence and ts_ns must be non-negative")
  if self.quantity<0:raise ValueError("quantity must be non-negative")
  if self.level_depth_after is not None and self.level_depth_after<0:raise ValueError("level_depth_after must be non-negative")
  if self.kind is EventKind.SNAPSHOT and self.level_depth_after is None:raise ValueError("SNAPSHOT requires level_depth_after")
@dataclass(frozen=True,slots=True)
class PassiveOrder:
 order_id:str;side:Side;price_ticks:int;quantity:int;decision_sequence:int;latency_events:int=0
 def __post_init__(self):
  if not self.order_id:raise ValueError("order_id is required")
  if self.quantity<=0:raise ValueError("quantity must be positive")
  if self.decision_sequence<0 or self.latency_events<0:raise ValueError("decision_sequence and latency_events must be non-negative")
 @property
 def activation_sequence(self):return self.decision_sequence+self.latency_events+1
@dataclass(frozen=True,slots=True)
class Fill:
 sequence:int;ts_ns:int;quantity:int;price_ticks:int
 def __post_init__(self):
  if self.sequence<0 or self.ts_ns<0:raise ValueError("fill sequence and ts_ns must be non-negative")
  if self.quantity<=0:raise ValueError("fill quantity must be positive")
@dataclass(slots=True)
class QueueSimulationResult:
 order_id:str;contract_version:str=CONTRACT_VERSION;activation_sequence:int|None=None;initial_queue_ahead:int|None=None;final_queue_ahead:int|None=None;filled_quantity:int=0;remaining_quantity:int=0;fills:list[Fill]=field(default_factory=list);abstain_reason:AbstainReason|None=None;diagnostics:dict[str,int]=field(default_factory=dict);digest:str=""
 @property
 def complete(self):return self.abstain_reason is None and self.remaining_quantity==0
 def seal(self):
  p=asdict(self);p["abstain_reason"]=self.abstain_reason.value if self.abstain_reason else None;p["digest"]="";self.digest=hashlib.sha256(json.dumps(p,sort_keys=True,separators=(",",":")).encode()).hexdigest();return self
def _ordered(events:Iterable[BookEvent]):
 rows=list(events)
 if any(b.sequence<=a.sequence for a,b in zip(rows,rows[1:])):raise ValueError("events must be strictly increasing by sequence")
 if any(b.ts_ns<a.ts_ns for a,b in zip(rows,rows[1:])):raise ValueError("events must be non-decreasing by ts_ns")
 return rows
def simulate_fifo_passive_fill(order,events,*,require_contiguous_sequences=True):
 rows=_ordered(events);r=QueueSimulationResult(order_id=order.order_id,remaining_quantity=order.quantity,diagnostics={"cancels_ignored":0,"adds_behind":0,"executed_at_level":0});ai=next((i for i,x in enumerate(rows) if x.sequence>=order.activation_sequence),None)
 if ai is None:r.abstain_reason=AbstainReason.NO_ACTIVATION_EVENT;return r.seal()
 a=rows[ai];r.activation_sequence=a.sequence
 if require_contiguous_sequences and a.sequence!=order.activation_sequence:r.abstain_reason=AbstainReason.SEQUENCE_GAP;return r.seal()
 if a.side is not order.side or a.price_ticks!=order.price_ticks:r.abstain_reason=AbstainReason.ACTIVATION_LEVEL_MISMATCH;return r.seal()
 if a.level_depth_after is None:r.abstain_reason=AbstainReason.NO_DEPTH_AT_ACTIVATION;return r.seal()
 ahead=a.level_depth_after;r.initial_queue_ahead=ahead;prev=a.sequence
 for x in rows[ai+1:]:
  if require_contiguous_sequences and x.sequence!=prev+1:r.final_queue_ahead=ahead;r.abstain_reason=AbstainReason.SEQUENCE_GAP;return r.seal()
  prev=x.sequence
  if x.kind is EventKind.RESET:r.final_queue_ahead=ahead;r.abstain_reason=AbstainReason.BOOK_RESET;return r.seal()
  if x.side is not order.side or x.price_ticks!=order.price_ticks:continue
  if x.kind is EventKind.CANCEL:r.diagnostics["cancels_ignored"]+=x.quantity;continue
  if x.kind is EventKind.ADD:r.diagnostics["adds_behind"]+=x.quantity;continue
  if x.kind is not EventKind.EXECUTE or x.quantity==0:continue
  r.diagnostics["executed_at_level"]+=x.quantity;used=min(ahead,x.quantity);ahead-=used;available=x.quantity-used
  if available>0:
   qty=min(r.remaining_quantity,available);r.fills.append(Fill(x.sequence,x.ts_ns,qty,order.price_ticks));r.filled_quantity+=qty;r.remaining_quantity-=qty
   if r.remaining_quantity==0:break
 r.final_queue_ahead=ahead;return r.seal()
