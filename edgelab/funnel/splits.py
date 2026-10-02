from __future__ import annotations
from dataclasses import dataclass,asdict
import hashlib,json
import numpy as np
@dataclass(frozen=True)
class FunnelSplit:
    d0_dates:tuple[int,...]; d1_dates:tuple[int,...]; d2_dates:tuple[int,...]; split_hash:str; d2_opened:bool=False

def make_splits(trade_dates, d0_fraction=.50, d1_fraction=.25)->FunnelSplit:
    days=np.unique(np.asarray(trade_dates,dtype=np.int32)); n=len(days)
    if n<12 or not (0<d0_fraction<1) or not (0<d1_fraction<1) or d0_fraction+d1_fraction>=1: raise ValueError("invalid/insufficient split")
    a=max(1,int(n*d0_fraction)); b=max(a+1,int(n*(d0_fraction+d1_fraction)))
    body={"d0_dates":days[:a].tolist(),"d1_dates":days[a:b].tolist(),"d2_dates":days[b:].tolist(),"policy":"chronological_v1"}
    h=hashlib.sha256(json.dumps(body,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    return FunnelSplit(tuple(body["d0_dates"]),tuple(body["d1_dates"]),tuple(body["d2_dates"]),h,False)
def mask_for(split:FunnelSplit, trade_dates, part:str, *, unlock_token:str|None=None):
    if part not in {"D0","D1","D2"}:raise ValueError(part)
    if part=="D2" and unlock_token!=split.split_hash:raise PermissionError("D2 sealed: exact split hash required")
    vals=getattr(split,part.lower()+"_dates");return np.isin(np.asarray(trade_dates),np.asarray(vals))
def to_dict(split):return asdict(split)
