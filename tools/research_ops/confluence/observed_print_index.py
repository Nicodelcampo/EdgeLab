"""Private observed-print range index for sparse zone arrival queries.

One immutable session/tape, price -> ordered source-index lists. Queries use
caller-bound causal [left,right) prefixes and CLOSED half-tick bands. No
interpolation, inferred touch, future label, geometry graph or native mutation.
Index construction can see the full tape only as an offline computational
index; every returned count/first index is clipped to explicit observed prefix.
Caller must bind typed availability clocks, after-birth left boundary and
coverage/censor flags. A hit at creation is NOT automatically an arrival.
"""
import numpy as np

class ObservedPrintIndex:
    def __init__(self,price_ticks,*,max_ticks=8000000,max_price_levels_per_query=10000,max_queries=1000000,max_level_queries=100000000):
        for v in (max_ticks,max_price_levels_per_query,max_queries,max_level_queries):
            if type(v) is not int or v<1:raise ValueError('positive print-index budgets')
        px=np.asarray(price_ticks)
        if px.ndim!=1 or not 0<len(px)<=max_ticks or px.dtype.kind not in 'iu':raise ValueError('bounded integer print tape')
        self.n=len(px);order=np.argsort(px,kind='stable');sorted_px=px[order]
        starts=np.r_[0,np.flatnonzero(sorted_px[1:]!=sorted_px[:-1])+1]
        self.levels=sorted_px[starts].copy();self.offsets=np.r_[starts,len(px)]
        self.indices=order.copy();self.max_levels=max_price_levels_per_query
        self.max_queries=max_queries;self.max_level_queries=max_level_queries
        self.queries=self.level_queries=0;self.poisoned=False
    def query(self,lo2,hi2,*,left,right):
        if self.poisoned:raise ValueError('poisoned print index')
        if any(type(v) is not int for v in (lo2,hi2,left,right)) or hi2<lo2 or not 0<=left<=right<=self.n:
            raise ValueError('closed half-tick band and bound observed prefix')
        # ceil(lo2/2), floor(hi2/2), including negative coordinates and odd-point bands.
        low=-((-lo2)//2);high=hi2//2
        a=int(np.searchsorted(self.levels,low,side='left'));z=int(np.searchsorted(self.levels,high,side='right'))
        width=max(0,z-a)
        if self.queries+1>self.max_queries or width>self.max_levels or self.level_queries+width>self.max_level_queries:
            self.poisoned=True;raise ValueError('print query capacity; no truncation')
        self.queries+=1;self.level_queries+=width;count=0;first=last=None
        for k in range(a,z):
            indices=self.indices[self.offsets[k]:self.offsets[k+1]]
            l=int(np.searchsorted(indices,left,side='left'));r=int(np.searchsorted(indices,right,side='left'))
            if r>l:
                count+=r-l;f=int(indices[l]);b=int(indices[r-1])
                first=f if first is None else min(first,f);last=b if last is None else max(last,b)
        return {'observed_print_count':count,'first_observed_index':first,'last_observed_index':last,
                'scope':'OBSERVED_PRINTS_ONLY_NOT_INTERPOLATED_PATH_OR_PHYSICAL_NO_TOUCH'}
