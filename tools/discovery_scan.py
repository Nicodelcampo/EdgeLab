#!/usr/bin/env python3
"""Barrido de descubrimiento sobre un activo o un grupo de activos pre-fijado. Pasos: tensores -> (calibrar) -> barrer en D0 -> replicar en D1 (D2 sellado) -> registrar.

  # calibrar (no barre)
  python tools/discovery_scan.py --asset config/discovery/assets/GC.json --spec config/discovery/families/f1_momentum.json --out /data/analysis/discovery --calibrate-only
  # grupo fijado de antemano: varios activos separados por coma (se suman por sesión; p. ej. FX = 6E,6J)
  python tools/discovery_scan.py --asset config/discovery/assets/6E.json,config/discovery/assets/6J.json --group-name FX --spec ... --prereg <pre-registro con el hash> ...
El barrido real exige que el pre-registro contenga el hash de la rejilla."""
import argparse,json,os,sys,time
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from edgelab.discovery import load_spec,spec_hash,get_backend
from edgelab.discovery import data as D,pipeline as P,scan as S,calibrate as C,families as Fm

def build_tensors(asset:dict,spec,cache:str|None=None):
    sp=spec.__class__(**{**spec.__dict__,"commission_ticks":asset["commission_usd_rt"]/asset["tick_value_usd"]})
    from edgelab.discovery import cache as CA
    if cache:
        if not CA.cache_ok(asset,sp,cache):CA.build_cache(asset,sp,cache)
        bars,rows,order,segs,elig,_,_=CA.load_cache(asset,cache)
        T=P.build(sp,None,bars,order,segs,elig,rows=rows);T.meta["segments"]=[(order[r],int(a),int(b)) for r,a,b in segs];T.meta["cache"]=True;return T,sp
    order=asset["order"];ticks={};bars={};daily={}
    for c in order:
        path=asset["path_template"].format(contract=c)
        if not os.path.exists(path):raise FileNotFoundError(path)
        ticks[c]=D.load_ticks(path,asset.get("cut_ns"));bars[c]=D.minute_bars(ticks[c]);daily[c]=D.daily_volume(bars[c])
    segs,elig=D.continuous_segments(daily,order,0.5)
    T=P.build(sp,ticks,bars,order,segs,elig);T.meta["segments"]=[(order[r],int(a),int(b)) for r,a,b in segs];return T,sp

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--asset",required=True);ap.add_argument("--group-name",default=None);ap.add_argument("--spec",required=True);ap.add_argument("--out",required=True)
    ap.add_argument("--backend",default="auto");ap.add_argument("--calibrate-only",action="store_true");ap.add_argument("--calib-reps",type=int,default=30)
    ap.add_argument("--prereg",default=None);ap.add_argument("--registry",default=None);ap.add_argument("--ledger",default=None);ap.add_argument("--export-tensors",default=None);ap.add_argument("--parity-report",default=None);ap.add_argument("--cache",default=None);a=ap.parse_args()
    assets=[json.loads(Path(x).read_text()) for x in a.asset.split(",")];name=a.group_name or "+".join(x["root"] for x in assets)
    spec=load_spec(a.spec);h=spec_hash(spec);out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    if not a.calibrate_only:
        if not a.prereg or h not in Path(a.prereg).read_text():raise SystemExit(f"El barrido real exige un pre-registro que contenga el hash de la rejilla ({h}). Use --calibrate-only o escriba el pre-registro antes.")
    t0=time.time();parts=[]
    for asset in assets:
        T,sp=build_tensors(asset,spec,a.cache);M,N=P.cell_matrices(T);parts.append((asset["root"],T,M,N))
    if len(parts)==1:_,T,M,N=parts[0];dates=T.dates
    else:dates,M,N=P.pool_cells([(t.dates,m,n) for _,t,m,n in parts]);T=parts[0][1]
    be=get_backend(a.backend,work_items=int(M.shape[0]*M.shape[1]*spec.n_sims))
    res={"group":name,"assets":[x["root"] for x in assets],"spec":spec.name,"spec_hash":h,"backend":be.name,"sessions":int(len(dates)),"cells_total":int(M.shape[1]),"build_s":round(time.time()-t0,1),"meta":{r:t.meta for r,t,_,_ in parts}}
    if a.calibrate_only:
        t1=time.time();res["false_positive"]=C.false_positive_rate(M,N,spec.min_trades,a.calib_reps,500,spec.seed,spec.alpha,be)
        res["power"]=C.power_curve(M,N,spec.min_trades,[0.1,0.2,0.3,0.5],max(10,a.calib_reps//2),500,spec.seed+1,spec.alpha,be);res["calibration_s"]=round(time.time()-t1,1)
        f=out/f"calibration_{name}_{spec.name}_{h[:10]}.json";f.write_text(json.dumps(res,indent=1,default=float));print(json.dumps({k:v for k,v in res.items() if k!="meta"},indent=1,default=float));return
    if be.name=="gpu":
        pr=json.loads(Path(a.parity_report).read_text()) if a.parity_report else {}
        if pr.get("status")!="PASS" or pr.get("kernel_id")!=S.KERNEL_ID:raise SystemExit("GPU solicitada: se exige un reporte de paridad CPU/GPU con status PASS para este kernel.")
    if a.export_tensors:np.savez(a.export_tensors,M=M,N=N,min_trades=spec.min_trades,n_sims=spec.n_sims,seed=spec.seed,spec_hash=h)
    from edgelab.funnel.splits import make_splits
    split=make_splits(dates);t1=time.time();r=S.staged_scan(M,N,dates,split,spec,be);rep=r["replication"];r.pop("D0_mask")
    z=r["z"];cells=r["cells"];heads=Fm.headlines(z,cells,T.cond_keys,len(T.slots),len(T.holds));tops=[]
    for hd in heads:
        c=int(hd["cell"]);d=P.decode(T,c);s_i,h_i,k_i=hd["slot_idx"],hd["hold_idx"],T.cond_keys.index(d["cond"]);sign=1 if hd["z"]>0 else -1;nets={}
        for root,t,_,_ in parts:
            m=t.masks[:,s_i,k_i]&np.isfinite(t.rt[:,s_i,h_i]);net=(t.nl if sign>0 else t.ns)[m,s_i,h_i];nets[root]={"trades":int(m.sum()),"mean_net_ticks_all_sessions":float(np.nanmean(net)) if m.any() else None}
        hd.update(d);hd.update({"direction":"long" if sign>0 else "short","per_asset":nets});tops.append(hd)
    for x in rep:x.update(P.decode(T,x["cell"]))
    res.update({"scan_s":round(time.time()-t1,1),"partition":{"policy":"chronological_v1","D0_sessions":r["D0_sessions"],"D1_sessions":r["D1_sessions"],"D2":"SEALED","split_hash":r["split_hash"]},
                "n_cells_tested":r["n_cells"],"real_max_abs_z":r["real_max_abs_z"],"null_max_q95":r["null_max_q95"],"p_max":r["p_max"],"n_q_bh_below_0.05":int((r["q_bh"]<0.05).sum()),
                "family_headlines":tops,"replication":rep,"kernel":{"kernel_id":S.KERNEL_ID,"backend":be.name,"precision":"float32","deterministic":"seeded","seed":spec.seed,"n_sims":spec.n_sims}})
    f=out/f"scan_{name}_{spec.name}_{h[:10]}.json";f.write_text(json.dumps(res,indent=1,default=float))
    if a.ledger:
        from edgelab.funnel.ledger import FunnelLedger
        FunnelLedger(a.ledger).append("DISCOVERY_SCAN",f"{spec.name}:{name}:{h[:12]}",{"group":name,"spec_hash":h,"backend":be.name,"p_max":res["p_max"],"n_cells":res["n_cells_tested"],"result_file":str(f),"asserts_edge":False})
    if a.registry:
        from edgelab.funnel.multiplicity import TrialRegistry
        TrialRegistry(a.registry).ensure(f"discovery_{spec.name}_{name}","DISCOVERY_GRID_SIGN_FLIP_MAXNULL",int(r["n_cells"]),"pre-registered grid; hash "+h)
    print(json.dumps({k:v for k,v in res.items() if k not in("meta","family_headlines")},indent=1,default=float));print("titulares por familia (top 6):",json.dumps(tops[:6],default=float))
if __name__=="__main__":main()
