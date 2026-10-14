from __future__ import annotations
import hashlib,json
from pathlib import Path
import numpy as np
from numba import njit,prange
@njit(cache=True)
def _ema(x,reset,span):
    y=np.empty(x.size,np.float64);a=2.0/(span+1.0);y[0]=x[0]
    for i in range(1,x.size):y[i]=x[i] if reset[i] else a*x[i]+(1-a)*y[i-1]
    return y
@njit(parallel=True,cache=True)
def ema_bank_cpu(x,reset,spans):
    out=np.empty((len(spans),len(x)),np.float64)
    for k in prange(len(spans)):out[k]=_ema(x,reset,int(spans[k]))
    return out
class FeatureStore:
    def __init__(self,root):self.root=Path(root);self.root.mkdir(parents=True,exist_ok=True)
    def put(self,name,array,provenance):
        a=np.asarray(array);p=self.root/f"{name}.npy";np.save(p,a,allow_pickle=False);h=hashlib.sha256(p.read_bytes()).hexdigest();meta={"name":name,"file":p.name,"shape":list(a.shape),"dtype":str(a.dtype),"sha256":h,"provenance":provenance};(self.root/f"{name}.json").write_text(json.dumps(meta,indent=2));return meta
    def get(self,name,mmap=True):return np.load(self.root/f"{name}.npy",mmap_mode="r" if mmap else None)
