"""Selección de backend numérico: CuPy si hay GPU y el trabajo es grande; NumPy si no."""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np

@dataclass(frozen=True)
class Backend:
    name:str
    xp:object
    reason:str
    def to_host(self,a):
        return a.get() if self.name=="gpu" else np.asarray(a)

def get_backend(prefer:str="auto",work_items:int=0,gpu_threshold:int=50_000_000)->Backend:
    if prefer not in {"auto","cpu","gpu"}:raise ValueError("prefer must be auto/cpu/gpu")
    cp=None;n=0
    try:
        import cupy as cp  # type: ignore
        n=int(cp.cuda.runtime.getDeviceCount())
    except Exception:
        n=0
    if prefer=="gpu" and n==0:raise RuntimeError("GPU solicitada pero CuPy/CUDA no está disponible")
    use=n>0 and (prefer=="gpu" or (prefer=="auto" and work_items>=gpu_threshold))
    if use:return Backend("gpu",cp,"GPU amortiza este lote")
    return Backend("cpu",np,"CPU: GPU no disponible o lote pequeño")
