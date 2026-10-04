#!/usr/bin/env python3
"""Barrido de descubrimiento sobre un activo. Pasos: construir tensores -> (calibrar) -> barrer -> replicar -> registrar pruebas.

  python tools/discovery_scan.py --asset config/discovery/assets/GC.json --spec config/discovery/spec_d1.json \
      --out /data/analysis/discovery --calibrate-only
  python tools/discovery_scan.py ... --prereg docs/research/<campaña>/PREREGISTRO.md   # el barrido real exige el hash de la rejilla en el pre-registro
"""
import argparse,json,os,sys,time
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from edgelab.discovery import load_spec,spec_hash,get_backend
from edgelab.discovery import data as D,pipeline as P,scan as S,calibrate as C

def build_tensors(asset:dict,spec):
    order=asset["order"];ticks={};bars={};daily={}
    for c in order:
        path=asset["path_template"].format(contract=c)
        if not os.path.exists(path):raise FileNotFoundError(path)
        ticks[c]=D.load_ticks(path,asset.get("cut_ns"));bars[c]=D.minute_bars(ticks[c]);daily[c]=D.daily_volume(bars[c])
    segs,elig=D.continuous_segments(daily,order,0.5)
    sp=spec.__class__(**{**spec.__dict__,"commission_ticks":asset["commission_usd_rt"]/asset["tick_value_usd"]})
    T=P.build(sp,ticks,bars,order,segs,elig);T.meta["segments"]=[(order[r],int(a),int(b)) for r,a,b in segs];return T,sp

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--asset",required=True);ap.add_argument("--spec",required=True);ap.add_argument("--out",required=True)
    ap.add_argument("--backend",default="auto");ap.add_argument("--calibrate-only",action="store_true");ap.add_argument("--calib-reps",type=int,default=30)
    ap.add_argument("--prereg",default=None);ap.add_argument("--registry",default=None);a=ap.parse_args()
    asset=json.loads(Path(a.asset).read_text());spec=load_spec(a.spec);h=spec_hash(spec);out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    if not a.calibrate_only:
        if not a.prereg or h not in Path(a.prereg).read_text():raise SystemExit(f"El barrido real exige un pre-registro que contenga el hash de la rejilla ({h}). Use --calibrate-only o escriba el pre-registro antes.")
    t0=time.time();T,sp=build_tensors(asset,spec);M,N=P.cell_matrices(T);be=get_backend(a.backend,work_items=int(M.shape[0]*M.shape[1]*spec.n_sims))
    res={"asset":asset["root"],"spec":spec.name,"spec_hash":h,"backend":be.name,"sessions":int(len(T.dates)),"cells_total":int(M.shape[1]),"build_s":round(time.time()-t0,1),"meta":T.meta}
    if a.calibrate_only:
        t1=time.time();res["false_positive"]=C.false_positive_rate(M,N,spec.min_trades,a.calib_reps,500,spec.seed,spec.alpha,be)
        res["power"]=C.power_curve(M,N,spec.min_trades,[0.1,0.2,0.3,0.5],max(10,a.calib_reps//2),500,spec.seed+1,spec.alpha,be);res["calibration_s"]=round(time.time()-t1,1)
        f=out/f"calibration_{asset['root']}_{h[:10]}.json";f.write_text(json.dumps(res,indent=1,default=float));print(json.dumps({k:v for k,v in res.items() if k!="meta"},indent=1,default=float));return
    t1=time.time();r=S.scan(M,N,spec.min_trades,spec.n_sims,spec.seed,be);cut=int(len(T.dates)*spec.split)
    rep=S.replicate(M,N,cut,spec.min_trades,spec.top_k_replication,20000,spec.seed+1,be)
    z=r["z"];cells=r["cells"];top=np.argsort(-np.abs(z))[:25];tops=[]
    Dn,Sn,Hn=T.rt.shape;K=len(T.cond_keys)
    for t in top:
        c=int(cells[t]);d=P.decode(T,c);s_i=T.slots.index(d["slot"]);h_i=T.holds.index(d["hold"]);k_i=T.cond_keys.index(d["cond"]);m=T.masks[:,s_i,k_i]&np.isfinite(T.rt[:,s_i,h_i])
        sign=1 if r["S"][t]>0 else -1;net=(T.nl if sign>0 else T.ns)[m,s_i,h_i]
        tops.append({**d,"z":float(z[t]),"q_bh":float(r["q_bh"][t]),"direction":"long" if sign>0 else "short","trades":int(m.sum()),"mean_net_ticks":float(np.nanmean(net)) if m.any() else None})
    for x in rep:x.update(P.decode(T,x["cell"]))
    res.update({"scan_s":round(time.time()-t1,1),"n_cells_tested":r["n_cells"],"real_max_abs_z":r["real_max_abs_z"],"null_max_q95":r["null_max_q95"],"p_max":r["p_max"],
                "n_q_bh_below_0.05":int((r["q_bh"]<0.05).sum()),"top_cells":tops,"replication":rep,"split_session_index":cut})
    f=out/f"scan_{asset['root']}_{h[:10]}.json";f.write_text(json.dumps(res,indent=1,default=float))
    if a.registry:
        from edgelab.funnel.multiplicity import TrialRegistry
        TrialRegistry(a.registry).ensure(f"discovery_{spec.name}_{asset['root']}","DISCOVERY_GRID_SIGN_FLIP_MAXNULL",int(r["n_cells"]),"pre-registered grid; hash "+h)
    print(json.dumps({k:v for k,v in res.items() if k not in("meta","top_cells")},indent=1,default=float));print("top 5:",json.dumps(tops[:5],default=float))
if __name__=="__main__":main()
