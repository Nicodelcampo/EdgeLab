"""Observed-midpoint first passage in seconds. Private market labels, no fills.

Vector windows share next-invalid/gap indexes. A5s clock gives <=13 overlapping
60s windows per tick; not a Cartesian product of indicators or definitions.
Features/classification are separate from this explicitly future-looking step.
"""
import time
import numpy as np
from .phenomena import HOLDOUT_NS

class SecondsResponse:
    def __init__(self,ns,sequence,bid,ask,*,max_gap_ns=2000000000,max_ticks=5000000,max_anchors=250000,max_scan_elements=100000000,wall_seconds=900):
        for v in (max_gap_ns,max_ticks,max_anchors,max_scan_elements,wall_seconds):
            if type(v) is not int or v<1:raise ValueError('finite positive response budgets')
        xs=[np.asarray(v) for v in (ns,sequence,bid,ask)];n=len(xs[0])
        if not 0<n<=max_ticks or any(x.ndim!=1 or len(x)!=n or x.dtype.kind not in 'iu' for x in xs):raise ValueError('bounded integer response tape')
        if any(x.dtype.kind=='u' and x.max()>np.iinfo(np.int64).max for x in xs):raise ValueError('int64 response bounds')
        self.ns,self.seq,b,a=[x.astype(np.int64,copy=False) for x in xs]
        if self.ns[0]<=0 or self.ns[-1]>=HOLDOUT_NS or np.any(np.diff(self.ns)<0) or np.any(self.seq[1:]<=self.seq[:-1]):raise ValueError('ordered preholdout response tape')
        if np.any(b<0) or np.any(a<0) or np.any(b>np.iinfo(np.int64).max//2) or np.any(a>np.iinfo(np.int64).max//2):raise ValueError('midpoint bounds')
        self.valid=(b>0)&(a>b);self.mid2=b+a
        ids=np.arange(n,dtype=np.int64)
        self.bad=np.minimum.accumulate(np.where(~self.valid,ids,n)[::-1])[::-1]
        self.gaps=np.minimum.accumulate(np.where(np.r_[False,np.diff(self.ns)>max_gap_ns],ids,n)[::-1])[::-1]
        self.n=n;self.max_anchors=max_anchors;self.max_scan=max_scan_elements;self.wall=wall_seconds
        self.scanned=0;self.anchors=0;self.started=time.monotonic();self.poisoned=False
    def label(self,index,*,direction,distance_ticks,horizon_ns=60000000000):
        if self.poisoned:raise ValueError('poisoned response engine')
        if type(index) is not int or not 0<=index<self.n or type(direction) is not int or direction not in (-1,1):raise ValueError('observed anchor and prior direction')
        if type(distance_ticks) is not int or not 0<distance_ticks<=np.iinfo(np.int64).max//2 or horizon_ns!=60000000000 or type(horizon_ns) is not int:raise ValueError('fixed60s positive whole-tick barrier')
        if self.anchors>=self.max_anchors or time.monotonic()-self.started>self.wall:
            self.poisoned=True;raise ValueError('response capacity/deadline; no truncation')
        self.anchors+=1
        if not self.valid[index]:return {'status':'ORIGIN_QUOTE_UNKNOWN','usable':False}
        deadline=int(self.ns[index])+horizon_ns
        right=int(np.searchsorted(self.ns,deadline,side='right'))
        # All same-ns observations at deadline are eligible, in sequence order.
        coverage=right-1 if right>index+1 and int(self.ns[right-1])==deadline else right
        j=index+1;censor=min(int(self.bad[j]),int(self.gaps[j])) if j<self.n else self.n
        end=min(right,censor);size=max(0,end-j)
        if self.scanned+size>self.max_scan:
            self.poisoned=True;raise ValueError('response scan budget; no truncation')
        self.scanned+=size
        delta=direction*(self.mid2[j:end]-int(self.mid2[index]));cross=(delta>=2*distance_ticks)|(delta<=-2*distance_ticks)
        if cross.any():
            k=int(cross.argmax());return {'status':'CONTINUATION_FIRST' if delta[k]>0 else 'REVERSAL_FIRST','usable':True}
        # Gap/invalid quote before or at the confirming point wins over no-pass.
        if censor<self.n and censor<=coverage:
            return {'status':'GAP_CENSORED' if int(self.gaps[j])<=int(self.bad[j]) else 'QUOTE_CENSORED','usable':False}
        if coverage>=self.n:return {'status':'EOF_CENSORED','usable':False}
        return {'status':'HORIZON_NO_OBSERVED_PASSAGE','usable':True}
