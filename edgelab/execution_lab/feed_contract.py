"""Normalized fail-closed L2/MBO observability contract."""
from __future__ import annotations
import hashlib,json
from dataclasses import asdict,dataclass,field
from enum import Enum
from typing import Iterable
CONTRACT_VERSION="L2_MBO_OBSERVABILITY_V1"
class FeedSchema(str,Enum):MBP_AGGREGATED="MBP_AGGREGATED";MBO_ORDER_LEVEL="MBO_ORDER_LEVEL"
class BookAction(str,Enum):SNAPSHOT="SNAPSHOT";ADD="ADD";MODIFY="MODIFY";CANCEL="CANCEL";EXECUTE="EXECUTE";CLEAR="CLEAR"
class BookSide(str,Enum):BID="BID";ASK="ASK"
class CertificationStatus(str,Enum):CERTIFIED_EXACT_QUEUE="CERTIFIED_EXACT_QUEUE";CERTIFIED_AGGREGATED_ONLY="CERTIFIED_AGGREGATED_ONLY";ABSTAIN="ABSTAIN"
class CertificationReason(str,Enum):
 PASS="PASS";AGGREGATED_MBP_NOT_EXACT_QUEUE="AGGREGATED_MBP_NOT_EXACT_QUEUE";EMPTY_SEGMENT="EMPTY_SEGMENT";MIXED_DATASET="MIXED_DATASET";MIXED_CHANNEL="MIXED_CHANNEL";INVALID_EVENT_ORDER="INVALID_EVENT_ORDER";PACKET_GAP="PACKET_GAP";PACKET_DUPLICATE="PACKET_DUPLICATE";PACKET_EVIDENCE_MISSING="PACKET_EVIDENCE_MISSING";ORDER_ID_MISSING="ORDER_ID_MISSING";PRIORITY_MISSING="PRIORITY_MISSING";SOURCE_HASH_MISSING="SOURCE_HASH_MISSING";TIMESTAMP_INVERSION="TIMESTAMP_INVERSION";PACKET_TIMESTAMP_INVERSION="PACKET_TIMESTAMP_INVERSION";EVENT_PACKET_UNOBSERVED="EVENT_PACKET_UNOBSERVED";INVALID_INSTRUMENT_ORDER="INVALID_INSTRUMENT_ORDER"
@dataclass(frozen=True,slots=True)
class SourceProvenance:
 dataset_id:str;source_name:str;venue:str;schema:FeedSchema;raw_sha256:str;decoder_id:str;decoder_sha256:str
 def __post_init__(self):
  if any(not getattr(self,n) for n in("dataset_id","source_name","venue","decoder_id")):raise ValueError("provenance identity fields are required")
  for n in("raw_sha256","decoder_sha256"):
   v=getattr(self,n)
   if v and(len(v)!=64 or any(c not in"0123456789abcdef" for c in v.lower())):raise ValueError(f"{n} must be an empty value or a SHA-256 hex digest")
@dataclass(frozen=True,slots=True)
class NormalizedBookEvent:
 dataset_id:str;channel_id:str;instrument_id:str;packet_sequence:int;event_index:int;instrument_sequence:int;exchange_ts_ns:int;receive_ts_ns:int|None;action:BookAction;side:BookSide|None;price_ticks:int|None;quantity:int;order_id:str|None=None;priority:int|None=None;recovered:bool=False
 def __post_init__(self):
  if not self.dataset_id or not self.channel_id or not self.instrument_id:raise ValueError("dataset_id, channel_id and instrument_id are required")
  if any(getattr(self,n)<0 for n in("packet_sequence","event_index","instrument_sequence","exchange_ts_ns","quantity")):raise ValueError("numeric fields must be non-negative")
  if self.receive_ts_ns is not None and self.receive_ts_ns<0:raise ValueError("receive_ts_ns must be non-negative")
  if self.action not in(BookAction.CLEAR,BookAction.SNAPSHOT) and(self.side is None or self.price_ticks is None):raise ValueError("book mutations require side and price_ticks")
  if self.action is BookAction.ADD and self.quantity<=0:raise ValueError("ADD quantity must be positive")
@dataclass(frozen=True,slots=True)
class PacketObservation:
 dataset_id:str;channel_id:str;packet_sequence:int;receive_ts_ns:int|None;recovered:bool=False
 def __post_init__(self):
  if not self.dataset_id or not self.channel_id:raise ValueError("dataset_id and channel_id are required")
  if self.packet_sequence<0 or(self.receive_ts_ns is not None and self.receive_ts_ns<0):raise ValueError("packet fields must be non-negative")
@dataclass(slots=True)
class FeedCertification:
 contract_version:str=CONTRACT_VERSION;status:CertificationStatus=CertificationStatus.ABSTAIN;reasons:list[CertificationReason]=field(default_factory=list);event_count:int=0;packet_count:int=0;recovered_packet_count:int=0;first_packet_sequence:int|None=None;last_packet_sequence:int|None=None;exact_queue_eligible:bool=False;digest:str=""
 def seal(self):
  p=asdict(self);p["status"]=self.status.value;p["reasons"]=[x.value for x in self.reasons];p["digest"]="";self.digest=hashlib.sha256(json.dumps(p,sort_keys=True,separators=(",",":")).encode()).hexdigest();return self
def certify_feed_segment(provenance,events:Iterable[NormalizedBookEvent],packets:Iterable[PacketObservation]|None,*,require_priority=True):
 rows=list(events);ps=list(packets) if packets is not None else[];r=FeedCertification(event_count=len(rows),packet_count=len(ps));re=[]
 def add(x):
  if x not in re:re.append(x)
 if not provenance.raw_sha256 or not provenance.decoder_sha256:add(CertificationReason.SOURCE_HASH_MISSING)
 if not rows:add(CertificationReason.EMPTY_SEGMENT)
 if any(x.dataset_id!=provenance.dataset_id for x in rows+ps):add(CertificationReason.MIXED_DATASET)
 ec={x.channel_id for x in rows};pc={x.channel_id for x in ps}
 if len(ec)>1 or len(pc)>1 or(ec and pc and ec!=pc):add(CertificationReason.MIXED_CHANNEL)
 keys=[(x.packet_sequence,x.event_index) for x in rows]
 if any(b<=a for a,b in zip(keys,keys[1:])):add(CertificationReason.INVALID_EVENT_ORDER)
 if any(b.exchange_ts_ns<a.exchange_ts_ns for a,b in zip(rows,rows[1:])):add(CertificationReason.TIMESTAMP_INVERSION)
 last={}
 for x in rows:
  if x.instrument_id in last and x.instrument_sequence<=last[x.instrument_id]:add(CertificationReason.INVALID_INSTRUMENT_ORDER)
  last[x.instrument_id]=x.instrument_sequence
 if not ps:add(CertificationReason.PACKET_EVIDENCE_MISSING)
 else:
  seq=[x.packet_sequence for x in ps];r.first_packet_sequence=seq[0];r.last_packet_sequence=seq[-1];r.recovered_packet_count=sum(x.recovered for x in ps)
  for a,b in zip(seq,seq[1:]):add(CertificationReason.PACKET_DUPLICATE if b==a else CertificationReason.PACKET_GAP) if b!=a+1 else None
  if any(x.packet_sequence not in set(seq) for x in rows):add(CertificationReason.EVENT_PACKET_UNOBSERVED)
  rt=[x.receive_ts_ns for x in ps if x.receive_ts_ns is not None]
  if any(b<a for a,b in zip(rt,rt[1:])):add(CertificationReason.PACKET_TIMESTAMP_INVERSION)
 if provenance.schema is FeedSchema.MBO_ORDER_LEVEL:
  life={BookAction.ADD,BookAction.MODIFY,BookAction.CANCEL,BookAction.EXECUTE}
  if any(x.action in life and not x.order_id for x in rows):add(CertificationReason.ORDER_ID_MISSING)
  if require_priority and any(x.action in(BookAction.ADD,BookAction.MODIFY) and x.priority is None for x in rows):add(CertificationReason.PRIORITY_MISSING)
 else:add(CertificationReason.AGGREGATED_MBP_NOT_EXACT_QUEUE)
 hard=set(CertificationReason)-{CertificationReason.PASS,CertificationReason.AGGREGATED_MBP_NOT_EXACT_QUEUE}
 if hard.intersection(re):r.status=CertificationStatus.ABSTAIN
 elif provenance.schema is FeedSchema.MBP_AGGREGATED:r.status=CertificationStatus.CERTIFIED_AGGREGATED_ONLY
 else:r.status=CertificationStatus.CERTIFIED_EXACT_QUEUE;r.exact_queue_eligible=True;re=[CertificationReason.PASS]
 r.reasons=re;return r.seal()
