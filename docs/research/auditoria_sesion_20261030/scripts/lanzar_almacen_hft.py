"""Almacén de zonas HFT, un kernel por indicador×activo. Corre desde el worktree el-prh."""
import re,sys,os,subprocess,json
from pathlib import Path
ROOT=Path.cwd();sys.path.insert(0,str(ROOT/"tools/kaggle_grilla"));sys.path.insert(0,str(ROOT))
from construir_kernel import construir
from edgelab.research import embudo_runners as ER
def deps(ini):
    v=set();c=list(ini)
    while c:
        m=c.pop()
        if m in v or not Path(m).exists(): continue
        v.add(m);s=Path(m).read_text(encoding="utf-8")
        for a,b in re.findall(r"^\s*from (edgelab[\w.]*) import ([\w ,]+)",s,re.M):
            base=a.replace(".","/");c.append(base+".py")
            c+= [f"{base}/{x.split(' as ')[0].strip()}.py" for x in b.split(",")]
        for pts,a,bb in re.findall(r"^\s*from (\.+)([\w.]*) import \(?([\w ,\n]+)",s,re.M):
            base="/".join(Path(m).parts[:-len(pts)]+tuple(a.split(".") if a else ()));c.append(base+".py");c+=[f"{base}/{x.split(' as ')[0].strip()}.py" for x in bb.split(",")]
        for a in re.findall(r"^\s*import (edgelab[\w.]*)",s,re.M): c.append(a.replace(".","/")+".py")
    return sorted(x for x in v if not x.endswith("__init__.py"))
M=deps(["tools/kaggle_grilla/almacen_zonas_main.py","edgelab/research/prerange_hft.py","edgelab/research/oro_0530.py","edgelab/research/fuentes_ticks.py"])
M=[m for m in M if m!="tools/kaggle_grilla/almacen_zonas_main.py"];print(len(M),"módulos")
k=ER.KaggleRunner("nicolasbutta",raiz=Path("tmp_bt"));env=k._env("nicolasbutta");h={}
Path("tmp_bt").mkdir(exist_ok=True)
for ind,inst in [x.split(":") for x in sys.argv[1:]]:
    out=f"tmp_bt/alm_{ind}_{inst}.py";construir("tools/kaggle_grilla/almacen_zonas_main.py",out,M)
    t=Path(out).read_text(encoding="utf-8");Path(out).write_text(f'import os\nos.environ.update(INDICADOR="{ind}",INSTS="{inst}")\n'+t,encoding="utf-8")
    slug=f"nicolasbutta/almacen-zonas-{ind.lower()}-{inst.lower()}"
    r=subprocess.run([sys.executable,"-X","utf8","tools/kaggle_launch.py","--slug",slug,"--script",out,"--need",f"{inst}:2025-07-01:2026-09-30"],capture_output=True,text=True,env=env,timeout=600)
    print(slug,r.returncode,(r.stdout+r.stderr)[-200:].replace("\n"," "));h[f"{ind}_{inst}"]=slug
Path("C:/Users/Gonza-PC/PruebaDeAgente/alm_handles.json").write_text(json.dumps(h,indent=1))
