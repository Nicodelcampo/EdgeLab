"""Caché por activo: barras de 1 min + filas de ejecución por libro (independientes de la familia) + auditoría de cada contrato.
Se arma UNA vez leyendo los ticks (un contrato a la vez: memoria acotada) y después cada familia solo calcula máscaras sobre las barras.
La clave del caché incluye franjas, holdings, guarda de retraso, comisión, corte y tamaño de cada archivo de ticks: si algo cambia, se rearma."""
from __future__ import annotations
import hashlib,json,os,time
from pathlib import Path
import numpy as np
from . import data as D,pipeline as P,audit as A
from .spec import GridSpec

BAR_KEYS=("t","o","h","l","c","vol","buy","sell","pv","spread","n")
ROW_KEYS=("td","sl","b1","has","entry_fail","exit_fail","rt","nl","ns")

def fills_key(spec:GridSpec,asset:dict)->tuple[str,dict]:
    sizes={c:(os.path.getsize(asset["path_template"].format(contract=c)) if os.path.exists(asset["path_template"].format(contract=c)) else None) for c in asset["order"]}
    d={"slots":list(spec.slots_hhmm),"holds":list(spec.holds),"max_entry_delay_s":spec.max_entry_delay_s,"max_exit_delay_s":spec.max_exit_delay_s,
       "commission_ticks":spec.commission_ticks,"cut_ns":asset.get("cut_ns"),"order":asset["order"],"file_sizes":sizes,"code":"cache.v1"}
    return hashlib.sha256(json.dumps(d,sort_keys=True).encode()).hexdigest(),d

def _paths(root:Path,c:str):return root/f"{c}.bars.npz",root/f"{c}.rows.npz",root/f"{c}.audit.json"

def build_cache(asset:dict,spec:GridSpec,cache_dir:str|Path,log=print)->dict:
    """Lee los ticks contrato por contrato y guarda barras, filas y auditoría. Devuelve el meta."""
    root=Path(cache_dir)/asset["root"];root.mkdir(parents=True,exist_ok=True);key,kd=fills_key(spec,asset);t0=time.time();meta={"key":key,"key_detail":kd,"contracts":{}}
    for c in asset["order"]:
        path=asset["path_template"].format(contract=c)
        if not os.path.exists(path):raise FileNotFoundError(path)
        acc={};t1=time.time();tk=D.load_ticks(path,asset.get("cut_ns"),audit=acc);bars=D.minute_bars(tk);rows=P.contract_rows(spec,tk,bars)
        tl=A.tick_level(tk,acc);sl=A.session_level(bars);aud={"contract":c,"tick_level":tl,"session_level":sl}
        pb,pr,pa=_paths(root,c);np.savez_compressed(pb,**{k:bars[k] for k in BAR_KEYS});np.savez_compressed(pr,**{k:rows[k] for k in ROW_KEYS});pa.write_text(json.dumps(aud,default=float))
        meta["contracts"][c]={"trades":int(len(tk["ts_utc_ns"])),"bars":int(len(bars["t"])),"rows":int(len(rows["td"])),"seconds":round(time.time()-t1,1)};log(f"  {c}: {meta['contracts'][c]}")
        del tk,bars,rows
    meta["seconds"]=round(time.time()-t0,1);(root/"meta.json").write_text(json.dumps(meta,indent=1));return meta

def cache_ok(asset:dict,spec:GridSpec,cache_dir:str|Path)->bool:
    root=Path(cache_dir)/asset["root"];m=root/"meta.json"
    if not m.exists():return False
    try:key,_=fills_key(spec,asset);return json.loads(m.read_text()).get("key")==key and all(all(p.exists() for p in _paths(root,c)) for c in asset["order"])
    except Exception:return False

def load_cache(asset:dict,cache_dir:str|Path):
    """Devuelve (bars, rows, order, segs, elig, audit_por_contrato)."""
    root=Path(cache_dir)/asset["root"];bars={};rows={};aud={};daily={};order=list(asset["order"])
    for c in order:
        pb,pr,pa=_paths(root,c);bars[c]={k:v for k,v in np.load(pb).items()};rows[c]={k:v for k,v in np.load(pr).items()};aud[c]=json.loads(pa.read_text());daily[c]=D.daily_volume(bars[c])
    segs,elig=D.continuous_segments(daily,order,0.5);return bars,rows,order,segs,elig,aud,daily

def asset_audit(asset:dict,cache_dir:str|Path)->dict:
    """Auditoría del activo. Además de los controles por contrato, separa lo que importa para el barrido: sesiones realmente usadas (serie continua elegible)
    y el costo de libro (entrada + salida) de las operaciones que entran en las matrices."""
    bars,rows,order,segs,elig,aud,daily=load_cache(asset,cache_dir);dates=np.array(sorted(elig));ct=asset["commission_usd_rt"]/asset["tick_value_usd"];used_sp=[]
    for ci,c in enumerate(order):
        sl=dict(aud[c]["session_level"]);sl.pop("per_session",None)
        for f in sl["flagged"]:f["used_in_scan"]=bool(elig.get(f["td"])==ci)
        sl["n_flagged_used_in_scan"]=sum(1 for f in sl["flagged"] if f["used_in_scan"]);sl["used_sessions"]=sum(1 for d,r in elig.items() if r==ci);aud[c]["session_level"]=sl
        R=rows[c];m,_=P._mine(R,elig,ci,dates);ok=m[:,None]&np.isfinite(R["nl"])&np.isfinite(R["ns"])&R["has"][:,None];used_sp.append((-(R["nl"]+R["ns"])-2*ct)[ok])
    sp=np.concatenate(used_sp) if used_sp else np.array([0.])
    fills={"n_fills":int(len(sp)),"entry_plus_exit_spread_ticks":{"p50":float(np.percentile(sp,50)),"p99":float(np.percentile(sp,99)),"p99.9":float(np.percentile(sp,99.9)),"max":float(sp.max())}}
    return {"asset":asset["root"],"contracts":aud,"fills_used":fills,"asset_level":A.asset_level(daily,bars,order,segs,elig)}
