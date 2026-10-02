from datetime import datetime,timezone
from pathlib import Path
from edgelab.edge_brain.registry import append_record,verify_registry
class FunnelLedger:
    def __init__(self,path):self.path=Path(path)
    def append(self,record_type,record_id,payload):return append_record(self.path,record_type=record_type,record_id=record_id,payload=payload,recorded_at_utc=datetime.now(timezone.utc).isoformat())
    def verify(self):return verify_registry(self.path)
