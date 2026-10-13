"""Bounded immutable memo of native BT2A bucket footprint, not detector state.

Exact native loop order retained. Content-addressing prevents same clock/sequence
with different tape from reusing a footprint. LRU eviction recomputes, never
omits a bucket/event. Histories, thresholds, rows and active zones stay private
per config. No market file reads, execution permission or NT8 certificate.
"""
from collections import OrderedDict
from types import MappingProxyType
import hashlib
import numpy as np

class BucketFootprintCache:
    def __init__(self,*,max_entries=2048,max_cells=200000):
        if any(type(x) is not int or x<1 for x in (max_entries,max_cells)):raise ValueError('finite shared footprint limits')
        self.max_entries=max_entries;self.max_cells=max_cells;self.data=OrderedDict();self.cells=0;self.hits=0;self.misses=0;self.evictions=0;self.peak_cells=0
    def prepare(self,px,vol,bid,ask):
        arrays=[np.asarray(x) for x in (px,vol,bid,ask)];n=len(arrays[0])
        if not 0<n<=1000 or any(a.ndim!=1 or len(a)!=n or a.dtype.kind not in 'iuf' or not np.isfinite(a).all() for a in arrays):raise ValueError('aligned bounded shared footprint')
        h=hashlib.sha256()
        for a in arrays:h.update(a.dtype.str.encode());h.update(str(a.shape).encode());h.update(a.tobytes())
        key=h.digest()
        if key in self.data:self.hits+=1;self.data.move_to_end(key);return self.data[key]
        self.misses+=1;a={};b={};flow=0.;nq=nr=0
        # Copied unchanged from pinned native flush_block; ordered float sums.
        for k in range(n):
            p=px[k];v=vol[k];aq=ask[k];bq=bid[k];side=0;quoted=False
            if aq>0 and bq>0 and aq>=bq:
                if p>=aq:side=1;quoted=True
                elif p<=bq:side=-1;quoted=True
            if side==0:
                if k>0:
                    if p>px[k-1]:side=1
                    elif p<px[k-1]:side=-1
                    else:side=1
                else:side=1
            if quoted:nq+=1
            else:nr+=1
            m=a if side>0 else b;m[p]=m.get(p,0.)+v;flow+=(v if side>0 else -v)
        result=(MappingProxyType(a),MappingProxyType(b),flow,nq,nr);cells=len(a)+len(b)
        # An oversized memo item is computed/used but not retained.
        if cells<=self.max_cells:
            while self.data and (len(self.data)>=self.max_entries or self.cells+cells>self.max_cells):
                _,old=self.data.popitem(last=False);self.cells-=len(old[0])+len(old[1]);self.evictions+=1
            self.data[key]=result;self.cells+=cells;self.peak_cells=max(self.peak_cells,self.cells)
        return result
    def receipt(self):return dict(hits=self.hits,misses=self.misses,evictions=self.evictions,retained_entries=len(self.data),retained_cells=self.cells,peak_cells=self.peak_cells,max_entries=self.max_entries,max_cells=self.max_cells,native_history_shared=False)
