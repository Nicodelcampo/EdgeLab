from __future__ import annotations
import numpy as np
from numba import njit,prange
from .device import detect_device
@njit(parallel=True,cache=True)
def _cpu(sig,dirs,h,l,bid_open,ask_open,sls,tps,mults,max_hold,fees):
    ns=len(sig);nc=len(sls);out=np.full((ns,nc),np.nan)
    for q in prange(nc):
        sl=sls[q];tp=tps[q]
        for k in range(ns):
            i=sig[k]+1
            if i>=len(h):continue
            d=dirs[k]*mults[q];e=ask_open[i] if d==1 else bid_open[i];stop=e-d*sl;targ=e+d*tp;end=min(len(h),i+max_hold+1);x=np.nan
            for j in range(i,end):
                if d==1:
                    if l[j]<=stop:x=-sl-fees;break
                    if h[j]>=targ+1:x=tp-fees;break
                else:
                    if h[j]>=stop:x=-sl-fees;break
                    if l[j]<=targ-1:x=tp-fees;break
            if np.isnan(x):x=-fees
            out[k,q]=x
    return out
_GPU_SRC=r'''extern "C" __global__ void screen(const long long* sig,const signed char* d,const int* h,const int* l,const int* bo,const int* ao,const int* sl,const int* tp,const signed char* mul,int ns,int nc,int n,int hold,float fee,float* out){int z=blockDim.x*blockIdx.x+threadIdx.x;if(z>=ns*nc)return;int k=z/nc,q=z-k*nc,i=(int)sig[k]+1;if(i>=n){out[z]=__int_as_float(0x7fc00000);return;}int di=d[k]*mul[q],e=di==1?ao[i]:bo[i],st=e-di*sl[q],tg=e+di*tp[q],end=min(n,i+hold+1);float v=-fee;for(int j=i;j<end;j++){if(di==1&&l[j]<=st){v=-sl[q]-fee;break;}if(di==1&&h[j]>=tg+1){v=tp[q]-fee;break;}if(di==-1&&h[j]>=st){v=-sl[q]-fee;break;}if(di==-1&&l[j]<=tg-1){v=tp[q]-fee;break;}}out[z]=v;}'''
def cheap_screen(sig,dirs,high,low,bid_open,ask_open,sls,tps,multipliers=None,max_hold_bars=200,fees=.5,backend="auto"):
    ns,nc=len(sig),len(sls);dev=detect_device(backend,ns*nc)
    mult=np.ones(nc,np.int8) if multipliers is None else np.asarray(multipliers,np.int8)
    if len(mult)!=nc or not np.isin(mult,[-1,1]).all():raise ValueError("multipliers must be +/-1 per config")
    if dev.backend=="cpu":return _cpu(np.asarray(sig,np.int64),np.asarray(dirs,np.int8),np.asarray(high,np.int32),np.asarray(low,np.int32),np.asarray(bid_open,np.int32),np.asarray(ask_open,np.int32),np.asarray(sls,np.int32),np.asarray(tps,np.int32),mult,max_hold_bars,fees),dev
    import cupy as cp
    args=[cp.asarray(x) for x in (np.asarray(sig,np.int64),np.asarray(dirs,np.int8),np.asarray(high,np.int32),np.asarray(low,np.int32),np.asarray(bid_open,np.int32),np.asarray(ask_open,np.int32),np.asarray(sls,np.int32),np.asarray(tps,np.int32),mult)];out=cp.empty(ns*nc,cp.float32);ker=cp.RawKernel(_GPU_SRC,"screen");threads=256;ker(((ns*nc+threads-1)//threads,),(threads,),(*args,ns,nc,len(high),max_hold_bars,np.float32(fees),out));return cp.asnumpy(out.reshape(ns,nc)),dev

def iter_screen_batches(sig,dirs,high,low,bid_open,ask_open,sls,tps,multipliers=None,
                        max_hold_bars=200,fees=.5,backend="auto",
                        max_matrix_bytes=512*1024*1024):
    """Bound memory while screening arbitrarily large candidate registries."""
    ns=max(1,len(sig)); nc=len(sls)
    mult=np.ones(nc,np.int8) if multipliers is None else np.asarray(multipliers,np.int8)
    batch=max(1,int(max_matrix_bytes//(ns*4)))
    for start in range(0,nc,batch):
        end=min(nc,start+batch)
        matrix,device=cheap_screen(sig,dirs,high,low,bid_open,ask_open,
                                   np.asarray(sls)[start:end],np.asarray(tps)[start:end],
                                   mult[start:end],max_hold_bars,fees,backend)
        yield start,end,matrix,device
