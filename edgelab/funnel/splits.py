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


def validate_split(split, trade_dates):
    """Check frozen labels/hash/exact day coverage; grants no data permission."""
    if split.d2_opened is not False:
        raise PermissionError("Outcome runner requires an unopened D2 split")
    all_dates = []
    for name in ("d0_dates", "d1_dates", "d2_dates"):
        values = tuple(getattr(split, name))
        if not values or any(isinstance(x, (bool, np.bool_)) or not isinstance(x, (int, np.integer)) for x in values):
            raise ValueError("split partitions need nonempty integer labels")
        if any(a >= b for a, b in zip(values, values[1:])):
            raise ValueError("split partition labels must be strictly increasing")
        all_dates.extend(int(x) for x in values)
    if any(a >= b for a, b in zip(all_dates, all_dates[1:])):
        raise ValueError("split partitions overlap or are out of order")
    td = np.asarray(trade_dates)
    if td.ndim != 1 or td.dtype.kind not in "iu" or not len(td) or np.any(td[1:] < td[:-1]):
        raise ValueError("trade_dates must be chronological integer labels")
    if list(np.unique(td)) != all_dates:
        raise ValueError("array day coverage differs from frozen split; do not resplit")
    body = {"d0_dates": [int(x) for x in split.d0_dates], "d1_dates": [int(x) for x in split.d1_dates],
            "d2_dates": [int(x) for x in split.d2_dates], "policy": "chronological_v1"}
    expected = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    if split.split_hash != expected:
        raise ValueError("frozen split hash mismatch")
    return FunnelSplit(tuple(body["d0_dates"]), tuple(body["d1_dates"]),
                       tuple(body["d2_dates"]), split.split_hash, False)


def load_frozen_split(path):
    """Read split metadata only. Hash identity is NOT an approval credential."""
    from pathlib import Path
    data = json.loads(Path(path).read_text())
    required = {"d0_dates", "d1_dates", "d2_dates", "split_hash"}
    allowed = required | {"d2_opened", "policy"}
    if not isinstance(data, dict) or required - data.keys() or data.keys() - allowed:
        raise ValueError("unsupported frozen split metadata shape")
    if data.get("policy", "chronological_v1") != "chronological_v1":
        raise ValueError("unsupported frozen split policy")
    return FunnelSplit(tuple(data["d0_dates"]), tuple(data["d1_dates"]),
                       tuple(data["d2_dates"]), data["split_hash"],
                       data.get("d2_opened", False))
