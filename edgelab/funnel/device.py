from __future__ import annotations
from dataclasses import dataclass
import os
@dataclass(frozen=True)
class DeviceProfile:
    cpu_count:int; cupy:bool; cuda_devices:int; backend:str; reason:str

def detect_device(prefer:str="auto", work_items:int=0, gpu_threshold:int=2_000_000)->DeviceProfile:
    cp=None; n=0
    try:
        import cupy as cp  # type: ignore
        n=int(cp.cuda.runtime.getDeviceCount())
    except Exception: n=0
    available=n>0
    if prefer not in {"auto","cpu","gpu"}: raise ValueError("prefer must be auto/cpu/gpu")
    if prefer=="gpu" and not available: raise RuntimeError("GPU requested but CuPy/CUDA is unavailable")
    use=available and (prefer=="gpu" or (prefer=="auto" and work_items>=gpu_threshold))
    return DeviceProfile(os.cpu_count() or 1,available,n,"gpu" if use else "cpu",("GPU amortizes this batch" if use else "CPU reference or GPU unavailable/batch too small"))
