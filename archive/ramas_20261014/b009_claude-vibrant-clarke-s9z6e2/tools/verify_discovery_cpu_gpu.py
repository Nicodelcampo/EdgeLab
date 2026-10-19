#!/usr/bin/env python3
"""Paridad sintética del motor de descubrimiento: CPU sin bloqueo == CPU por bloques == GPU. No lee datos de mercado.
Falla si se pide GPU y no hay CUDA; `--cpu-only` emite CPU_ONLY_PASS_GPU_PENDING y NUNCA cuenta como paridad GPU (regla del embudo)."""
import argparse,hashlib,json,platform,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from edgelab.discovery import scan as S,get_backend
SRC=["edgelab/discovery/scan.py","edgelab/discovery/backend.py"]
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--out",required=True);ap.add_argument("--cpu-only",action="store_true");a=ap.parse_args()
    root=Path(__file__).resolve().parents[1];rep={"schema_version":"discovery_parity_v1","kernel_id":S.KERNEL_ID,"market_data_read":False,"holdout_opened":False,"asserts_edge":False,"gpu_tested":False,
        "python":platform.python_version(),"numpy":np.__version__,"source_sha256":{f:hashlib.sha256((root/f).read_bytes()).hexdigest() for f in SRC},"cases":[]}
    rng=np.random.default_rng(20261011);cpu=get_backend("cpu");ok=True
    for name,(D,nc,sims) in {"pequeno":(80,300,1024),"medio":(225,20000,512),"ancho":(60,100000,256)}.items():
        A=(rng.standard_normal((D,nc))/np.sqrt(D)).astype(np.float32);ref=S.max_null(A,sims,5,cpu,max_matrix_bytes=2**31)
        blk=S.max_null(A,sims,5,cpu,max_matrix_bytes=2**20);d=float(np.abs(ref-blk).max());case={"name":name,"shape":[D,nc],"sims":sims,"cpu_blocked_vs_unblocked_max_abs_diff":d,"cpu_blocked_ok":d<1e-4};ok&=case["cpu_blocked_ok"]
        if not a.cpu_only:
            try:g=get_backend("gpu")
            except RuntimeError as e:rep.update(status="FAIL_NO_CUDA",error=str(e));Path(a.out).write_text(json.dumps(rep,indent=1));print(json.dumps(rep,indent=1));sys.exit(2)
            dg=float(np.abs(ref-S.max_null(A,sims,5,g,max_matrix_bytes=2**28)).max());case.update(gpu_vs_cpu_max_abs_diff=dg,gpu_ok=dg<1e-3);ok&=case["gpu_ok"];rep["gpu_tested"]=True
        rep["cases"].append(case)
    rep["status"]=("PASS" if rep["gpu_tested"] else "CPU_ONLY_PASS_GPU_PENDING") if ok else "FAIL"
    Path(a.out).write_text(json.dumps(rep,indent=1));print(json.dumps(rep,indent=1));sys.exit(0 if ok else 1)
if __name__=="__main__":main()
