"""Observed post-fill markouts with causal as-of quote anchoring.

MARKOUT_OBSERVED_QUOTES_V2 retires V1's future-anchor flaw.
"""
from __future__ import annotations
import hashlib,json
from dataclasses import asdict,dataclass,field
from enum import Enum
from typing import Iterable
from .queue_model import Fill,Side
CONTRACT_VERSION="MARKOUT_OBSERVED_QUOTES_V2"
class MarkoutAbstain(str,Enum):
 NO_FILLS="NO_FILLS";NO_ANCHOR_QUOTE="NO_ANCHOR_QUOTE";STALE_ANCHOR_QUOTE="STALE_ANCHOR_QUOTE";NO_HORIZON_QUOTE="NO_HORIZON_QUOTE";STALE_HORIZON_QUOTE="STALE_HORIZON_QUOTE";SEQUENCE_GAP="SEQUENCE_GAP";BOOK_RESET="BOOK_RESET"
@dataclass(frozen=True,slots=True)
class QuoteObservation:
 sequence:int;ts_ns:int;bid_ticks:int;ask_ticks:int;reset:bool=False
 def __post_init__(self):
  if self.sequence<0 or self.ts_ns<0:raise ValueError("sequence and ts_ns must be non-negative")
  if self.ask_ticks<self.bid_ticks:raise ValueError("crossed quotes are invalid")
 @property
 def mid_ticks(self):return(self.bid_ticks+self.ask_ticks)/2
@dataclass(frozen=True,slots=True)
class FillMarkout:
 fill_sequence:int;fill_ts_ns:int;horizon_ns:int;quantity:int;fill_price_ticks:int;anchor_mid_ticks:float;future_mid_ticks:float;spread_capture_ticks:float;signed_markout_ticks:float;anchor_staleness_ns:int;horizon_staleness_ns:int
@dataclass(slots=True)
class MarkoutResult:
 lineage_id:str;contract_version:str=CONTRACT_VERSION;side:Side=Side.BID;horizons_ns:tuple[int,...]=();observations:list[FillMarkout]=field(default_factory=list);weighted_markout_ticks:dict[int,float]=field(default_factory=dict);abstain_reason:MarkoutAbstain|None=None;digest:str=""
 def seal(self):
  p=asdict(self);p["side"]=self.side.value;p["abstain_reason"]=self.abstain_reason.value if self.abstain_reason else None;p["digest"]="";self.digest=hashlib.sha256(json.dumps(p,sort_keys=True,separators=(",",":")).encode()).hexdigest();return self
def _ordered(quotes:Iterable[QuoteObservation]):
 q=list(quotes)
 if any(b.sequence<=a.sequence for a,b in zip(q,q[1:])):raise ValueError("quotes must be strictly increasing by sequence")
 if any(b.ts_ns<a.ts_ns for a,b in zip(q,q[1:])):raise ValueError("quotes must be non-decreasing by ts_ns")
 return q
def measure_fill_markouts(side:Side,fills:Iterable[Fill],quotes:Iterable[QuoteObservation],*,lineage_id:str,horizons_ns=(1_000_000_000,5_000_000_000),max_anchor_staleness_ns=100_000_000,max_horizon_staleness_ns=100_000_000,require_contiguous_sequences=True):
 if not lineage_id:raise ValueError("lineage_id is required")
 fs,qs=list(fills),_ordered(quotes);hs=tuple(sorted(set(horizons_ns)));r=MarkoutResult(lineage_id=lineage_id,side=side,horizons_ns=hs)
 if not fs:r.abstain_reason=MarkoutAbstain.NO_FILLS;return r.seal()
 if not hs or any(h<=0 for h in hs) or max_anchor_staleness_ns<0 or max_horizon_staleness_ns<0:raise ValueError("horizons must be positive and staleness bounds non-negative")
 for f in fs:
  ai=next((i for i in range(len(qs)-1,-1,-1) if qs[i].ts_ns<=f.ts_ns),None)
  if ai is None:r.abstain_reason=MarkoutAbstain.NO_ANCHOR_QUOTE;return r.seal()
  a=qs[ai];astale=f.ts_ns-a.ts_ns
  if astale>max_anchor_staleness_ns:r.abstain_reason=MarkoutAbstain.STALE_ANCHOR_QUOTE;return r.seal()
  if a.reset:r.abstain_reason=MarkoutAbstain.BOOK_RESET;return r.seal()
  for h in hs:
   target=f.ts_ns+h;hi=next((i for i in range(ai,len(qs)) if qs[i].ts_ns>=target),None)
   if hi is None:r.abstain_reason=MarkoutAbstain.NO_HORIZON_QUOTE;return r.seal()
   seg=qs[ai:hi+1]
   if any(x.reset for x in seg):r.abstain_reason=MarkoutAbstain.BOOK_RESET;return r.seal()
   if require_contiguous_sequences and any(b.sequence!=x.sequence+1 for x,b in zip(seg,seg[1:])):r.abstain_reason=MarkoutAbstain.SEQUENCE_GAP;return r.seal()
   future=qs[hi];hstale=future.ts_ns-target
   if hstale>max_horizon_staleness_ns:r.abstain_reason=MarkoutAbstain.STALE_HORIZON_QUOTE;return r.seal()
   sign=1 if side is Side.BID else -1;r.observations.append(FillMarkout(f.sequence,f.ts_ns,h,f.quantity,f.price_ticks,a.mid_ticks,future.mid_ticks,sign*(a.mid_ticks-f.price_ticks),sign*(future.mid_ticks-f.price_ticks),astale,hstale))
 for h in hs:
  rows=[x for x in r.observations if x.horizon_ns==h];qty=sum(x.quantity for x in rows);r.weighted_markout_ticks[h]=sum(x.signed_markout_ticks*x.quantity for x in rows)/qty
 return r.seal()
