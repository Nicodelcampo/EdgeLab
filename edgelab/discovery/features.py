"""Biblioteca de características causales calculadas con datos anteriores a la barra de señal.

Para la franja con hora `slot` (CT), la barra de señal b1 es la que CIERRA en slot+1 min; todo se calcula con barras con sello <= b1.
Tipos (ventana W en minutos, sufijo `_W`):
  mom      cierre(b1) - cierre(b1-W), en ticks
  rng      máximo - mínimo de las barras de la ventana, en ticks
  vwapdev  cierre(b1) - VWAP de la ventana, en ticks
  imb      (volumen comprador - vendedor)/(total) por agresor, en [-1,1]
  absorb   volumen de la ventana / max(rng, 1): esfuerzo por tick de recorrido
  effort   volumen de la ventana / (|mom| + 1): esfuerzo frente a resultado neto
  spread   spread medio de la ventana, en ticks
"""
from __future__ import annotations
import numpy as np
from .data import MIN

def _window_idx(t:np.ndarray,b1:np.ndarray,W:int):
    iend=np.searchsorted(t,b1,"right");ist=np.searchsorted(t,b1-W*MIN,"right");return ist,iend

def _range_reduce(arr:np.ndarray,ist:np.ndarray,iend:np.ndarray,fn):
    ok=iend>ist;out=np.full(len(ist),np.nan)
    if ok.any():
        idx=np.empty(2*int(ok.sum()),np.int64);idx[0::2]=ist[ok];idx[1::2]=np.minimum(iend[ok],len(arr))
        r=fn.reduceat(arr,np.minimum(idx,len(arr)-1))[0::2];out[ok]=r
    return out

def compute(bars:dict,b1:np.ndarray,names:set[str])->tuple[dict[str,np.ndarray],np.ndarray]:
    """b1: sellos de las barras de señal (ns). Devuelve ({nombre: valor crudo}, máscara 'existe la barra b1')."""
    t=bars["t"];i1=np.searchsorted(t,b1);has=(i1<len(t))&(t[np.minimum(i1,len(t)-1)]==b1)
    cum={k:np.r_[0.,np.cumsum(bars[k])] for k in("vol","buy","sell","pv","spread","n")};out={}
    for nm in names:
        kind,W=nm.split("_");W=int(W);ist,iend=_window_idx(t,b1,W);v=np.full(len(b1),np.nan)
        win=lambda k:cum[k][iend]-cum[k][ist]
        ref=np.searchsorted(t,b1-W*MIN,"right")-1;cb=np.where(iend>0,bars["c"][np.maximum(iend-1,0)],0)
        mom=np.where(ref>=0,cb-bars["c"][np.maximum(ref,0)],np.nan)
        if kind=="mom":v=mom.astype(float)
        elif kind in("rng","absorb"):
            hi=_range_reduce(bars["h"].astype(float),ist,iend,np.maximum);lo=_range_reduce(bars["l"].astype(float),ist,iend,np.minimum);rng=hi-lo
            v=rng if kind=="rng" else win("vol")/np.maximum(rng,1.)
        elif kind=="vwapdev":
            with np.errstate(invalid="ignore",divide="ignore"):vw=win("pv")/win("vol")
            v=cb-vw
        elif kind=="imb":
            with np.errstate(invalid="ignore",divide="ignore"):v=(win("buy")-win("sell"))/(win("buy")+win("sell"))
        elif kind=="effort":v=win("vol")/(np.abs(mom)+1.)
        elif kind=="spread":
            with np.errstate(invalid="ignore",divide="ignore"):v=win("spread")/np.maximum(iend-ist,1)
        else:raise ValueError(nm)
        out[nm]=np.where(has&(iend>ist),v,np.nan)
    return out,has

def causal_z(values:np.ndarray,lookback:int,min_hist:int)->np.ndarray:
    """z-score causal por franja: media y desvío de las `lookback` sesiones PREVIAS (excluye la actual). values: (D, S) con NaN."""
    D,S=values.shape;z=np.full((D,S),np.nan)
    for d in range(D):
        lo=max(0,d-lookback);h=values[lo:d]
        if h.shape[0]==0:continue
        cnt=np.sum(~np.isnan(h),0)
        with np.errstate(invalid="ignore"):
            mu=np.nanmean(h,0);sd=np.nanstd(h,0)
        ok=(cnt>=min_hist)&(sd>0);z[d]=np.where(ok,(values[d]-mu)/np.where(sd>0,sd,1),np.nan)
    return z
