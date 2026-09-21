"""Fail-closed semantics between existing EdgeLab carriers and trend context."""
from __future__ import annotations
import hashlib, json
from bisect import bisect_right
from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable, Mapping
from edgelab.research.trend_context import EventAlignment, TrendContext, align_event_with_trend

CONTRACT_VERSION="TREND_CARRIER_SEMANTICS_V1"
HFT_CERTIFIED_PARITY="PASS_CERTIFIED_FULL_FIELD_PARITY"
class CarrierSource(str,Enum):
    BIGTRAP2="BigTrap2"; BIGTRAP2_ABSORPTION="BigTrap2Absorption"; HFTZONES2="HFTZones2"; HFTZONES_NQ_V2="HFTZonesNQPureV4"
class CarrierMechanism(str,Enum):
    TRAPPED_AGGRESSOR_FADE="TRAPPED_AGGRESSOR_FADE"; FORMATION_CONTINUATION="FORMATION_CONTINUATION"; ZONE_BOUNCE="ZONE_BOUNCE"; CONFIRMED_ZONE_BREACH="CONFIRMED_ZONE_BREACH"
@dataclass(frozen=True,slots=True)
class TrendCarrier:
    contract_version:str; source:CarrierSource; carrier_id:str; mechanism:CarrierMechanism; available_at_ns:int; session_id:str; lineage_id:str; continuation_direction:int; native_label:str; parent_carrier_id:str|None; digest:str
@dataclass(frozen=True,slots=True)
class CarrierTrendClassification:
    carrier:TrendCarrier; context:TrendContext; alignment:EventAlignment

def _make(source,carrier_id,mechanism,available_at_ns,session_id,lineage_id,direction,native_label,parent_carrier_id=None):
    if not carrier_id or not session_id or not lineage_id: raise ValueError("carrier_id, session_id and lineage_id are required")
    if available_at_ns<0 or direction not in (-1,1): raise ValueError("invalid availability or direction")
    p=dict(contract_version=CONTRACT_VERSION,source=source.value,carrier_id=carrier_id,mechanism=mechanism.value,available_at_ns=int(available_at_ns),session_id=session_id,lineage_id=lineage_id,continuation_direction=direction,native_label=native_label,parent_carrier_id=parent_carrier_id)
    d=hashlib.sha256(json.dumps(p,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    return TrendCarrier(CONTRACT_VERSION,source,carrier_id,mechanism,int(available_at_ns),session_id,lineage_id,direction,native_label,parent_carrier_id,d)
def _check_ms(z,t):
    if "created_ms" not in z: raise ValueError("created_ms is required")
    if int(z["created_ms"])!=int(t)//1_000_000: raise ValueError("available_at_ns does not match detector created_ms")
def adapt_bigtrap2_zone(z,*,available_at_ns,session_id,lineage_id):
    _check_ms(z,available_at_ns); k=str(z.get("kind","")); d={"trapped_buyers":-1,"trapped_sellers":1}.get(k)
    if d is None: raise ValueError("unsupported BigTrap2 kind")
    return _make(CarrierSource.BIGTRAP2,str(z.get("id","")),CarrierMechanism.TRAPPED_AGGRESSOR_FADE,available_at_ns,session_id,lineage_id,d,k)
def adapt_bigtrap2_absorption_zone(z,*,session_id,lineage_id):
    k,l=str(z.get("kind",z.get("side",""))),str(z.get("dir","")); e={"trapped_buyers":"short","trapped_sellers":"long"}
    if k not in e or l!=e[k]: raise ValueError("inconsistent BigTrap2Absorption kind/dir")
    if z.get("sig_ts") is None: raise ValueError("sig_ts is required")
    return _make(CarrierSource.BIGTRAP2_ABSORPTION,str(z.get("id","")),CarrierMechanism.TRAPPED_AGGRESSOR_FADE,int(z["sig_ts"]),session_id,lineage_id,-1 if l=="short" else 1,f"{k}:{l}")
def adapt_hftzones2_zone(z,*,available_at_ns,session_id,lineage_id):
    _check_ms(z,available_at_ns); d,k=int(z.get("dir",0)),str(z.get("kind",""))
    if d not in (-1,1): raise ValueError("HFTZones2 dir must be +1 or -1")
    if not k.lower().startswith("support_" if d==1 else "resistance_"): raise ValueError("inconsistent HFTZones2 kind/dir")
    return _make(CarrierSource.HFTZONES2,str(z.get("id","")),CarrierMechanism.FORMATION_CONTINUATION,available_at_ns,session_id,lineage_id,d,f"{k}:dir={d}")
def adapt_hft_nq_v2_zone(z,*,lineage_id):
    if z.get("source")!=CarrierSource.HFTZONES_NQ_V2.value: raise ValueError("unsupported HFT NQ source")
    if z.get("parity_status")!=HFT_CERTIFIED_PARITY: raise ValueError("HFT NQ zone is not parity certified")
    if z.get("available_ts_source")!="V2_AVAILABLE_NS": raise ValueError("legacy HFT availability is diagnostic only")
    d=int(z.get("direction",0))
    if d not in (-1,1): raise ValueError("HFT NQ direction must be +1 or -1")
    return _make(CarrierSource.HFTZONES_NQ_V2,str(z.get("id","")),CarrierMechanism.FORMATION_CONTINUATION,int(z["available_ts"]),str(z.get("session_id","")),lineage_id,d,f"direction={d}")
def adapt_confirmed_zone_bounce(parent,*,bounce_available_at_ns):
    if parent.mechanism is not CarrierMechanism.FORMATION_CONTINUATION: raise ValueError("bounce requires an HFT formation parent")
    if bounce_available_at_ns<=parent.available_at_ns: raise ValueError("bounce must be available after zone creation")
    return _make(parent.source,f"{parent.carrier_id}:bounce:{bounce_available_at_ns}",CarrierMechanism.ZONE_BOUNCE,bounce_available_at_ns,parent.session_id,parent.lineage_id,parent.continuation_direction,f"bounce_of:{parent.native_label}",parent.carrier_id)
def adapt_confirmed_zone_breach(parent,*,breach_available_at_ns):
    if parent.mechanism not in (CarrierMechanism.FORMATION_CONTINUATION,CarrierMechanism.ZONE_BOUNCE): raise ValueError("breach requires an HFT formation/bounce parent")
    if breach_available_at_ns<=parent.available_at_ns: raise ValueError("breach must be available after its parent event")
    return _make(parent.source,f"{parent.carrier_id}:breach:{breach_available_at_ns}",CarrierMechanism.CONFIRMED_ZONE_BREACH,breach_available_at_ns,parent.session_id,parent.lineage_id,-parent.continuation_direction,f"breach_of:{parent.native_label}",parent.carrier_id)
def latest_available_context(contexts:Iterable[TrendContext],event_available_at_ns:int,*,session_id:str):
    rows=[r for r in contexts if r.session_id==session_id]; ts=[r.available_at_ns for r in rows]
    if any(b<=a for a,b in zip(ts,ts[1:])): raise ValueError("contexts must be strictly increasing by available_at_ns")
    i=bisect_right(ts,int(event_available_at_ns))-1; return None if i<0 else rows[i]
def classify_carrier(carrier,contexts):
    c=latest_available_context(contexts,carrier.available_at_ns,session_id=carrier.session_id)
    if c is None:return None
    return CarrierTrendClassification(carrier,c,align_event_with_trend(carrier.continuation_direction,c,event_available_at_ns=carrier.available_at_ns))
