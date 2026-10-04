#!/usr/bin/env python3
"""Script para un kernel PRIVADO de Kaggle con GPU (T4). Sin internet; no lee datos de mercado, solo tensores ya construidos.

Entradas (datasets adjuntos al kernel):
  - código: dataset con la carpeta `edgelab/discovery` (zip del repo en la versión que se declara en el reporte)
  - tensores: `.npz` con M (D x ncell, float32), N (D x ncell, float32), generado por tools/discovery_scan.py --export-tensors
Salida: /kaggle/working/gpu_scan_report.json con (1) paridad CPU/GPU sobre un subconjunto, (2) máximo nulo en GPU, (3) tiempos.
La paridad se exige ANTES de usar el resultado de GPU: si difiere más de 1e-3, el reporte marca FAIL y no se usa."""
import glob,hashlib,json,sys,time
import numpy as np
for p in glob.glob("/kaggle/input/*"):sys.path.insert(0,p)
from edgelab.discovery import scan as S,get_backend
npz=sorted(glob.glob("/kaggle/input/**/*.npz",recursive=True))[0];Z=np.load(npz);M,N=Z["M"],Z["N"]
cpu=get_backend("cpu");gpu=get_backend("gpu");rep={"npz":npz,"npz_sha256":hashlib.sha256(open(npz,"rb").read()).hexdigest(),"shape":list(M.shape)}
z,Sg,use,Ms=S.cell_z(M,N,int(Z["min_trades"]) if "min_trades" in Z else 40);sub=Ms[:,:20000]
a=S.max_null(sub,2048,7,cpu);b=S.max_null(sub,2048,7,gpu);rep["parity_max_abs_diff"]=float(np.abs(a-b).max());rep["parity"]="PASS" if rep["parity_max_abs_diff"]<1e-3 else "FAIL"
t=time.time();nul=S.max_null(Ms,int(Z["n_sims"]) if "n_sims" in Z else 20000,int(Z["seed"]) if "seed" in Z else 1,gpu);rep["gpu_null_seconds"]=round(time.time()-t,2)
real=float(np.abs(z).max());rep.update({"n_cells":int(len(z)),"real_max_abs_z":real,"null_max_q95":float(np.quantile(nul,.95)),"p_max":S.p_value(real,nul)})
json.dump(rep,open("/kaggle/working/gpu_scan_report.json","w"),indent=1);print(json.dumps(rep,indent=1))
