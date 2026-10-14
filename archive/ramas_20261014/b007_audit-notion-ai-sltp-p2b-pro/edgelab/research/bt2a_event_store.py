"""Identity checks shared by BT2A Gate-2 runners."""
from __future__ import annotations
import hashlib,json
from pathlib import Path

def canonical_sha256(value):
 return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
def file_sha256(path):
 h=hashlib.sha256()
 with Path(path).open("rb") as handle:
  for block in iter(lambda:handle.read(1<<20),b""): h.update(block)
 return h.hexdigest()
def verify_file_sha256(path,expected):
 actual=file_sha256(path)
 if actual!=str(expected): raise RuntimeError(f"input sha256 mismatch: {Path(path).name}")
 return actual
def validate_event_checkpoint(value,*,contract,session,sample_registry_sha256,input_registry_sha256):
 if not isinstance(value,dict) or value.get("status")!="COMPLETE": raise RuntimeError("event checkpoint is not COMPLETE")
 required={"events","events_sha256","sample_registry_payload_sha256","input_registry_payload_sha256","contract","cme_session"}; missing=sorted(required-set(value))
 if missing: raise RuntimeError(f"event checkpoint missing fields: {missing}")
 if str(value["contract"])!=str(contract) or str(value["cme_session"])!=str(session): raise RuntimeError("event checkpoint partition mismatch")
 if value["sample_registry_payload_sha256"]!=sample_registry_sha256 or value["input_registry_payload_sha256"]!=input_registry_sha256: raise RuntimeError("event checkpoint registry mismatch")
 events=value["events"]
 if not isinstance(events,list) or value["events_sha256"]!=canonical_sha256(events): raise RuntimeError("event checkpoint payload hash mismatch")
 ids=[]; identities=[]; arms=set()
 for event in events:
  if not isinstance(event,dict): raise RuntimeError("event checkpoint contains non-object")
  identity=event.get("identity_sha256"); body={k:v for k,v in event.items() if k!="identity_sha256"}
  if not identity or identity!=canonical_sha256(body): raise RuntimeError("event identity hash mismatch")
  if str(event.get("contract"))!=str(contract) or str(event.get("cme_session"))!=str(session): raise RuntimeError("foreign event partition")
  if int(event.get("direction",0)) not in (-1,1): raise RuntimeError("invalid event direction")
  ids.append(str(event.get("event_id"))); identities.append(str(identity)); arms.add(event.get("arm"))
 if len(ids)!=len(set(ids)) or len(identities)!=len(set(identities)): raise RuntimeError("duplicate event identity")
 if not arms.issubset({"K_ABS","K_BT2"}) or not {"K_ABS","K_BT2"}.issubset(arms): raise RuntimeError("observed arm coverage mismatch")
 return events
