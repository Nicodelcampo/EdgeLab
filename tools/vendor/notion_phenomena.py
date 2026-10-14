# COPIA SIN CAMBIOS de tools/research_ops/confluence/phenomena.py (rama feat/research-ops-supervisor-mvp del agente de Notion).
# SHA-256 del original: 05c39573bd8fbd35b4bf975042fc2143681cb5bf742fef2b25aba115f7f9a2b0
# Se copia para reutilizar EXACTAMENTE su motor de medicion de ventanas; no editar. Los tests comparan este SHA.
"""Bounded target-free clock-window measurements, not a phenomenon classifier.

Market arrays/private feature rows remain inside Kaggle. Synthetic fixtures may
exercise this module elsewhere. No outcome, thresholds fitted, A/E state claim,
indicator mutation or canonical writer. Midquotes use half-tick integers.
"""
from datetime import date
import time
import numpy as np

HOLDOUT_NS = 1790805600000000000
WINDOWS = (5, 20, 60)

class BlockedRangeIndex:
    """Exact blocked min/max; no per-query full-window scan or all-tick Python loop."""
    def __init__(self, values, block=512):
        self.x=np.asarray(values); self.block=block
        self.lo=np.array([self.x[i:i+block].min() for i in range(0,len(self.x),block)])
        self.hi=np.array([self.x[i:i+block].max() for i in range(0,len(self.x),block)])
    def query(self, left, right):
        if not 0<=left<right<=len(self.x): raise ValueError('nonempty bounded range')
        a=(left+self.block-1)//self.block; b=right//self.block
        if a>=b:
            x=self.x[left:right];return x.min().item(),x.max().item()
        low=self.lo[a:b].min().item(); high=self.hi[a:b].max().item()
        for x in (self.x[left:a*self.block], self.x[b*self.block:right]):
            if len(x): low=min(low,x.min().item()); high=max(high,x.max().item())
        return low,high

class DirectRangeIndex:
    """Reference NumPy range reductions; lower setup cost for the measured fixture."""
    def __init__(self, values): self.x=np.asarray(values)
    def query(self, left, right):
        if not 0<=left<right<=len(self.x): raise ValueError('nonempty bounded range')
        return self.x[left:right].min().item(),self.x[left:right].max().item()

# Synthetic comparison did not support adopting blocked indexing for P0.
RangeIndex = DirectRangeIndex

class ClockMeasurements:
    def __init__(self, *, windows=WINDOWS, grid_seconds=5, max_gap_ns=2_000_000_000,
                 minimum_quote_volume_coverage=.8, max_ticks=5_000_000,
                 max_anchors=250_000, wall_seconds=900):
        if windows!=WINDOWS or grid_seconds!=5: raise ValueError('P0 measurement roster fixed')
        for v in (max_gap_ns,max_ticks,max_anchors,wall_seconds):
            if type(v) is not int or v<1: raise ValueError('positive finite budgets')
        if type(minimum_quote_volume_coverage) not in (int,float) or not 0<minimum_quote_volume_coverage<=1:
            raise ValueError('explicit quote-volume coverage')
        self.windows=windows;self.grid=grid_seconds*10**9;self.gap=max_gap_ns
        self.coverage=minimum_quote_volume_coverage;self.max_ticks=max_ticks
        self.max_anchors=max_anchors;self.wall=wall_seconds

    def measure(self, ts, sequence, price, volume, bid, ask, *, trade_date):
        """Yield private records in source order. Same-ns later sequences excluded."""
        if str(date.fromisoformat(trade_date))!=trade_date or trade_date>='2026-10-01':
            raise ValueError('canonical preholdout trade date')
        started=time.monotonic()
        ns,seq,px,bq,aq=[np.asarray(x) for x in (ts,sequence,price,bid,ask)]
        v=np.asarray(volume,dtype=np.float64);n=len(ns)
        if not 0<n<=self.max_ticks or any(x.ndim!=1 or len(x)!=n for x in (ns,seq,px,bq,aq,v)):
            raise ValueError('bounded equal-length session arrays')
        for x in (ns,seq,px,bq,aq):
            if x.dtype.kind not in 'iu' or (x.dtype.kind=='u' and x.max()>np.iinfo(np.int64).max):
                raise ValueError('integer coordinates in int64 range')
        ns,seq,px,bq,aq=[x.astype(np.int64,copy=False) for x in (ns,seq,px,bq,aq)]
        if ns[0]<=0 or ns[-1]>=HOLDOUT_NS or np.any(ns[1:]<ns[:-1]) or np.any(seq[1:]<=seq[:-1]):
            raise ValueError('ordered preholdout source; no sort or truncation')
        if not np.isfinite(v).all() or np.any(v<0) or np.any(v!=np.floor(v)) or v.max()>2**53//n:
            raise ValueError('bounded exact nonnegative integer volume')
        if np.any(bq>np.iinfo(np.int64).max//2) or np.any(aq>np.iinfo(np.int64).max//2) or np.any(bq<0) or np.any(aq<0):
            raise ValueError('quote coordinate bounds')
        valid=(bq>0)&(aq>bq)
        side=np.where(valid & (px>=aq),1,np.where(valid & (px<=bq),-1,0)).astype(np.int8)
        # Interior prints remain UNKNOWN; no tick-rule fallback or default BUY.
        mid2=bq+aq; spread=aq-bq
        def prefix(x): return np.r_[0.,np.cumsum(x,dtype=np.float64)]
        sums={k:prefix(x) for k,x in {'volume':v,'buy':v*(side>0),'sell':v*(side<0),
              'unknown':v*(side==0),'quote_volume':v*valid}.items()}
        good_mid_lo=np.where(valid,mid2,np.iinfo(np.int64).max)
        good_mid_hi=np.where(valid,mid2,np.iinfo(np.int64).min)
        lows=RangeIndex(good_mid_lo);highs=RangeIndex(good_mid_hi)
        gaps=RangeIndex(np.r_[0,np.diff(ns)])
        path=prefix(np.r_[0.,np.where(valid[1:]&valid[:-1],np.abs(np.diff(mid2))*.5,0.)])
        anchor=np.r_[0,np.flatnonzero(np.diff(ns//self.grid))+1]
        if len(anchor)>self.max_anchors: raise ValueError('anchor capacity; no silent partial census')
        self.summary={'ticks':n,'anchors':len(anchor),'empty_clock_cells':int((ns[-1]//self.grid)-(ns[0]//self.grid)+1-len(anchor)),
                      'windows':{str(w):{} for w in self.windows},'classifier_states_enabled':False,
                      'outcomes_enabled':False,'range_method':RangeIndex.__name__}
        for i in anchor:
            if time.monotonic()-started>self.wall: raise TimeoutError('measurement wall budget')
            i=int(i);t=int(ns[i]);r={'trade_date':trade_date,'timestamp_ns':t,'sequence':int(seq[i]),'windows':{}}
            for w in self.windows:
                width=w*10**9;cut=t-width;old=t-2*width
                l=int(np.searchsorted(ns,cut,side='right'));pl=int(np.searchsorted(ns,old,side='right'))
                # Current end is anchor sequence, not every later trade at its ns.
                cur=self._window(ns,valid,mid2,spread,sums,path,l,i+1,cut,t,lows,highs,gaps)
                prev=self._window(ns,valid,mid2,spread,sums,path,pl,l,old,cut,lows,highs,gaps)
                direction=int(np.sign(prev['signed_volume_proxy'])) if prev['status']=='OBSERVABLE' else 0
                status='MEASURABLE_PAIR' if cur['status']==prev['status']=='OBSERVABLE' and direction else 'UNKNOWN_PAIR'
                changes={}
                if status=='MEASURABLE_PAIR':
                    prior_side=prev['buy_volume' if direction>0 else 'sell_volume']
                    now_side=cur['buy_volume' if direction>0 else 'sell_volume']
                    changes={'pressure_ratio':now_side/prior_side if prior_side else None,
                             'trade_count_ratio':cur['count']/prev['count'] if prev['count'] else None,
                             'total_volume_ratio':cur['volume']/prev['volume'] if prev['volume'] else None,
                             'directed_progress_ticks':direction*cur['net_midpoint_ticks'],
                             'prior_directed_progress_ticks':direction*prev['net_midpoint_ticks']}
                r['windows'][str(w)]={'status':status,'direction_from_prior':direction,'current':cur,'prior':prev,**changes}
                counts=self.summary['windows'][str(w)];counts[status]=counts.get(status,0)+1
            yield r
        self.summary['seconds']=time.monotonic()-started

    def _window(self,ns,valid,mid,spread,sums,path,l,z,cut,end,lows,highs,gaps):
        count=z-l
        out={'count':count,**{k:float(x[z]-x[l]) for k,x in sums.items()}}
        out['buy_volume']=out.pop('buy');out['sell_volume']=out.pop('sell')
        out['unknown_volume']=out.pop('unknown');out['signed_volume_proxy']=out['buy_volume']-out['sell_volume']
        out['quote_volume_coverage']=out['quote_volume']/out['volume'] if out['volume'] else None
        out['signed_volume_coverage']=1-out['unknown_volume']/out['volume'] if out['volume'] else None
        out['net_midpoint_ticks']=out['range_midpoint_ticks']=out['path_midpoint_ticks']=None
        out['mean_trade_size']=out['volume']/count if count else None
        status='OBSERVABLE'
        if cut<int(ns[0]):status='INCOMPLETE_HISTORY'
        elif not count:status='NO_OBSERVED_TRADES'
        elif l==0 or cut-int(ns[l-1])>self.gap or end-int(ns[z-1])>self.gap or gaps.query(l,z)[1]>self.gap:status='GAP_UNKNOWN'
        elif not out['volume']:status='ZERO_VOLUME'
        elif not valid[l] or not valid[z-1] or out['quote_volume_coverage']<self.coverage:status='QUOTE_UNKNOWN'
        out['status']=status
        if status=='OBSERVABLE':
            lo=lows.query(l,z)[0];hi=highs.query(l,z)[1]
            out.update(net_midpoint_ticks=float(mid[z-1]-mid[l])*.5,range_midpoint_ticks=float(hi-lo)*.5,
                       path_midpoint_ticks=float(path[z]-path[l+1]),spread_at_end_ticks=int(spread[z-1]))
        return out
