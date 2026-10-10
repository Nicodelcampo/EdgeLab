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
def _integer_vector(name, values, dtype):
    a = np.asarray(values)
    if a.ndim != 1 or a.dtype.kind not in "iuf":
        raise ValueError(f"{name} must be a numeric 1D vector")
    bounds = np.iinfo(dtype)
    if not np.isfinite(a).all() or np.any(a < bounds.min) or np.any(a > bounds.max):
        raise ValueError(f"{name} must be finite and fit {np.dtype(dtype)}")
    converted = a.astype(dtype, copy=False)
    if not np.equal(a, converted).all():
        raise ValueError(f"{name} must contain integral values")
    return converted


def _screen_inputs(sig, dirs, high, low, bid_open, ask_open, sls, tps,
                   multipliers, max_hold_bars, fees):
    if isinstance(max_hold_bars, (bool, np.bool_)) or not isinstance(max_hold_bars, (int, np.integer)) or max_hold_bars < 0 or max_hold_bars >= np.iinfo(np.int32).max:
        raise ValueError("max_hold_bars must be a nonnegative integer")
    if not np.isscalar(fees) or not np.isfinite(fees) or fees < 0 or fees > np.finfo(np.float32).max:
        raise ValueError("fees must be finite and nonnegative")
    sig = _integer_vector("signals", sig, np.int64)
    dirs = _integer_vector("directions", dirs, np.int8)
    h, l, bo, ao, sl, tp = [_integer_vector(name, value, np.int32) for name, value in zip(
        ("high", "low", "bid", "ask", "SL", "TP"),
        (high, low, bid_open, ask_open, sls, tps))]
    nc = len(sl)
    mult = np.ones(nc, np.int8) if multipliers is None else _integer_vector("multipliers", multipliers, np.int8)
    if len(sig) != len(dirs) or len(sl) != len(tp) or len(mult) != nc:
        raise ValueError("signal/configuration lengths disagree")
    if any(len(a) != len(h) for a in (l, bo, ao)):
        raise ValueError("bar lengths disagree")
    if not np.isin(dirs, [-1, 1]).all() or not np.isin(mult, [-1, 1]).all():
        raise ValueError("directions and multipliers must be +/-1")
    if np.any(sl <= 0) or np.any(tp <= 0):
        raise ValueError("SL/TP must be positive integral tick distances")
    if np.any(sig < -1) or np.any(sig >= len(h)):
        raise ValueError("signals must be inside stage bars, or -1 for entry at stage start")
    if np.any(h < l) or np.any(ao < bo):
        raise ValueError("invalid high/low or crossed quotes")
    # CPU/GPU both consume int32 ticks. Prevent CUDA integer arithmetic overflow.
    if len(h) and nc:
        margin = max(int(sl.max()), int(tp.max())) + 1
        floor = min(int(bo.min()), int(ao.min())) - margin
        ceiling = max(int(bo.max()), int(ao.max())) + margin
        if floor < np.iinfo(np.int32).min or ceiling > np.iinfo(np.int32).max:
            raise ValueError("entry/SL/TP arithmetic exceeds int32 domain")
    return sig, dirs, h, l, bo, ao, sl, tp, mult


def cheap_screen(sig, dirs, high, low, bid_open, ask_open, sls, tps,
                 multipliers=None, max_hold_bars=200, fees=.5, backend="auto"):
    arrays = _screen_inputs(sig, dirs, high, low, bid_open, ask_open, sls, tps,
                            multipliers, max_hold_bars, fees)
    return _validated_screen(arrays, max_hold_bars, fees, backend)


def _validated_screen(arrays, max_hold_bars, fees, backend):
    sig, dirs, h, l, bo, ao, sl, tp, mult = arrays
    ns, nc = len(sig), len(sl)
    dev = detect_device(backend, ns * nc)
    if dev.backend == "gpu" and (ns*nc > np.iinfo(np.int32).max or len(h)+max_hold_bars >= np.iinfo(np.int32).max):
        raise ValueError("GPU launch/index arithmetic exceeds int32 domain")
    if not ns or not nc:
        return np.empty((ns, nc), np.float64 if dev.backend == "cpu" else np.float32), dev
    if dev.backend == "cpu":
        return _cpu(sig, dirs, h, l, bo, ao, sl, tp, mult, max_hold_bars, fees), dev
    import cupy as cp
    args = [cp.asarray(x) for x in arrays]
    out = cp.empty(ns * nc, cp.float32)
    kernel = cp.RawKernel(_GPU_SRC, "screen")
    kernel(((ns * nc + 255) // 256,), (256,),
           (*args, ns, nc, len(h), max_hold_bars, np.float32(fees), out))
    return cp.asnumpy(out.reshape(ns, nc)), dev


def iter_screen_batches(sig, dirs, high, low, bid_open, ask_open, sls, tps,
                        multipliers=None, max_hold_bars=200, fees=.5,
                        backend="auto", max_matrix_bytes=512*1024*1024):
    """Cap one returned matrix at worst-case float64; NOT total RAM/VRAM.

    A budget too small for one signal-by-one-configuration column fails.
    Signal chunking changes aggregation and must be implemented explicitly.
    """
    if isinstance(max_matrix_bytes, (bool, np.bool_)) or not isinstance(max_matrix_bytes, (int, np.integer)) or max_matrix_bytes <= 0:
        raise ValueError("matrix budget must be a positive integer")
    arrays = _screen_inputs(sig, dirs, high, low, bid_open, ask_open, sls, tps,
                            multipliers, max_hold_bars, fees)
    sig, dirs, h, l, bo, ao, sl, tp, mult = arrays
    ns, nc = len(sig), len(sl)
    if not ns or not nc:
        return
    one_column = ns * np.dtype(np.float64).itemsize
    if one_column > max_matrix_bytes:
        raise ValueError("matrix budget cannot fit one float64 column; chunk signals explicitly")
    width = max_matrix_bytes // one_column
    for first in range(0, nc, width):
        last = min(nc, first + width)
        matrix, dev = _validated_screen((sig, dirs, h, l, bo, ao, sl[first:last],
                                         tp[first:last], mult[first:last]),
                                        max_hold_bars, fees, backend)
        if matrix.nbytes > max_matrix_bytes:
            raise RuntimeError("screen backend exceeded matrix budget")
        yield first, last, matrix, dev
