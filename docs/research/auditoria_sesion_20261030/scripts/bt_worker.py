"""Una pasada mecánica, sin LLM: trae kernels terminados y lanza la cola respetando 5 en simultáneo. Nunca usa el holdout."""
import json,os,subprocess,sys,time
from pathlib import Path
R=Path("C:/Users/Gonza-PC/PruebaDeAgente");W="C:/Users/Gonza-PC/AppData/Local/Temp/edgelab-bt"
os.chdir(W);sys.path.insert(0,W)
os.environ.update(KAGGLE_AUTH_HEADER_FILE=str(Path.home()/".kaggle_auth_header"),EDGELAB_KAGGLE_CUENTAS="nicolasbutta,nicolasbuttaro,nicobuttaro",EDGELAB_KAGGLE_API="https://www.kaggle.com/api/v1",PYTHONIOENCODING="utf-8")
from edgelab.research import embudo_runners as ER
k=ER.KaggleRunner("nicolasbutta",raiz=Path("tmp_bt"))
C=["CVGAP-NQ","CVGAP-CFD-NQ","U1-YM-GRILLA","U1-ES-GRILLA","U1-ORO-GRILLA","U1-RACIMOS-GRILLA-ES","U1-RACIMOS-GRILLA-NQ","U1-ZONAS-AVCL-NQ","U1-ZONAS-BT2-ES","U1-ZONAS-BT2-NQ","U1-ZONAS-ES","U1-ZONAS-NQ"]
log=lambda s:(R/"bt_worker.log").open("a",encoding="utf-8").write(time.strftime("%F %T ")+s+"\n")
corr=sum(k.estado(f"nicolasbutta/almacen-zonas-{x.split(chr(95))[0].lower()}-{x.split(chr(95))[1].lower()}")=="running" for x in json.loads((R/"alm_handles_todos.json").read_text()));pend=[];LF=R/"flt_lanzados.json";lanz=json.loads(LF.read_text()) if LF.exists() else []
for pre,dir_,lz in (("btt","btt_res","lanzar_tope.py"),("pt","pt_res","lanzar_pert.py"),("flt","flt_res","lanzar_flt.py")):
    (R/dir_).mkdir(exist_ok=True)
    for c in C:
        f=R/dir_/f"{c}.json"
        if f.exists(): continue
        h=f"nicolasbutta/embudo-{pre}-{c.lower()}-rep-20250805";e=k.estado(h)
        if e=="complete": f.write_text(json.dumps(k.traer(h),default=float));log(f"bajado {pre} {c}")
        elif e in("running","queued"): corr+=1
        elif pre=="flt" and c not in lanz: pend.append((lz,c))   # nunca lanzado: Kaggle da 403/404
        elif e=="error": log(f"ERROR {pre} {c}: no se relanza solo")
        else: corr+=1   # recién lanzado, todavía 404
for lz,c in pend[:max(0,5-corr)]:
    r=subprocess.run([sys.executable,"-X","utf8",str(R/lz),c],capture_output=True,text=True,timeout=600);lanz.append(c);LF.write_text(json.dumps(lanz));log(f"lanzado {lz} {c}: {(r.stdout+r.stderr)[-120:].strip()}");corr+=1
log(f"corriendo={corr} pendientes={len(pend)}")
# Almacén de zonas HFT: baja parquet y json de los kernels terminados
Z=R/"zonas_hft";Z.mkdir(exist_ok=True)
for s in json.loads((R/"alm_handles_todos.json").read_text()):
    ind,inst=s.split("_");p=Z/f"ZONAS_{ind}_{inst}.parquet"
    if p.exists(): continue
    sl=f"nicolasbutta/almacen-zonas-{ind.lower()}-{inst.lower()}";e=k.estado(sl)
    if e=="complete":
        for fn,out in ((p.name,p),(f"ALMACEN_ZONAS_{ind}.json",Z/f"{ind}_{inst}.json")):
            subprocess.run([sys.executable,"tools/kaggle_kernel.py","output","--slug",sl,"--file",fn,"--out",str(out)],capture_output=True,text=True,timeout=600,env=k._env("nicolasbutta"))
        log(f"bajado almacén {s} ({p.stat().st_size if p.exists() else 'SIN ARCHIVO'})")
    elif e=="error": log(f"ERROR almacén {s}")
