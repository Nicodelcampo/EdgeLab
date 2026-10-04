#!/usr/bin/env python3
"""Mide qué tan buen sustituto es una serie de ticks de otra fuente (p. ej. spot XAU/USD de Dukascopy) para la EMA 200/500/2000 de barras de 25 ticks de MGC.
Solo usa MGC PREVIO AL HOLDOUT (artefactos de /data/analysis/mgc; el holdout desde 2026-04-01 no se abre aquí).
Entrada del sustituto: CSV o parquet con columnas  time (epoch ms, epoch ns o ISO UTC), bid, ask.
  python tools/equivalence_check.py --spot spot_xauusd_ticks.csv --out artifacts/equivalence
  python tools/equivalence_check.py --selftest --out /tmp/eq     # prueba de cañería con un sustituto sintético hecho de los propios ticks de MGC (no mide nada real)"""
import argparse,json,sys
from pathlib import Path
import numpy as np,pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from edgelab.equivalence import tick_bars,match_bar_size,sync_resample,signal_agreement,outcome_agreement,ema_cross_signals
ROOT=Path("/data/analysis/mgc")

def load_spot(path:str)->tuple[np.ndarray,np.ndarray]:
    df=pd.read_parquet(path) if path.endswith(".parquet") else pd.read_csv(path)
    t=df["time"]
    if np.issubdtype(t.dtype,np.number):
        v=t.to_numpy(np.int64);ts=v*1_000_000 if v[0]<10**14 else v           # ms o ns
    else:ts=pd.to_datetime(t,utc=True).astype("int64").to_numpy()
    o=np.argsort(ts,kind="stable");mid=((df["bid"]+df["ask"])/2).to_numpy(np.float64);return ts[o],mid[o]

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--spot");ap.add_argument("--out",required=True);ap.add_argument("--selftest",action="store_true");a=ap.parse_args()
    br=ROOT/"artifacts"/(ROOT/"artifacts/LATEST").read_text().strip();tr=ROOT/"tick_arrays"/(ROOT/"tick_arrays/LATEST").read_text().strip()
    fts=np.load(tr/"ts_utc_ns.npy",mmap_mode="r");fpx=np.load(tr/"price_ticks.npy",mmap_mode="r");fcid=np.load(tr/"contract_id.npy",mmap_mode="r")
    bts=np.load(br/"ts_end_ns.npy");bc=np.load(br/"close_ticks.npy").astype(float);bcid=np.load(br/"contract_id.npy");sig=np.load(br/"signal_bar_idx.npy");sdir=np.load(br/"signal_dir.npy")
    TICK=0.1
    if a.selftest:
        rng=np.random.default_rng(0);k=np.arange(0,len(fts),1);sub=np.asarray(fts[k]);spx=np.asarray(fpx[k])*TICK+rng.standard_normal(len(k))*0.05+1.5
        spot_ts=np.sort(np.concatenate([sub+rng.integers(0,10**9//2,len(sub)) for _ in range(3)]));spot_px=np.interp(spot_ts,sub,spx)
    else:
        if not a.spot:raise SystemExit("falta --spot")
        spot_ts,spot_px=load_spot(a.spot)
    lo=max(int(bts[0]),int(spot_ts[0]));hi=min(int(bts[-1]),int(spot_ts[-1]));out={"overlap_utc":[str(pd.Timestamp(lo,tz="UTC")),str(pd.Timestamp(hi,tz="UTC"))],"selftest":bool(a.selftest)}
    fm=(np.asarray(fts)>=lo)&(np.asarray(fts)<=hi);m=match_bar_size(np.asarray(fts)[fm],spot_ts[(spot_ts>=lo)&(spot_ts<=hi)],25);out["bar_size_matching"]=m
    # A) sincronizado: precio del sustituto en cada cierre de barra de futuros (mide la equivalencia de PRECIO, sin tocar la formación de barras)
    bm=(bts>=lo)&(bts<=hi);sync=sync_resample(bts,spot_ts,spot_px);ok=np.isfinite(sync)
    sa_i,sa_d=ema_cross_signals(np.where(ok,sync,np.nan),200,500,2000,group=bcid) if ok.all() else (np.array([],int),np.array([],np.int8))
    ref=bm[sig];ri,rd=sig[ref],sdir[ref]
    if len(sa_i):
        sm=bm[sa_i];out["A_sincronizado"]={f"tol_{t}s":signal_agreement(bts[ri],rd,bts[sa_i[sm]],sa_d[sm],t) for t in (300,900,3600)}
    else:out["A_sincronizado"]="el sustituto no cubre todo el período de las barras de futuros: se omite (use solo el tramo cubierto)"
    # B) barras con el N elegido sobre el sustituto: mide la equivalencia de FORMACIÓN de barras
    n=m["best"]["n_spot"];sm_ts=spot_ts[(spot_ts>=lo)&(spot_ts<=hi)];sm_px=spot_px[(spot_ts>=lo)&(spot_ts<=hi)];t2,c2,_=tick_bars(sm_ts,sm_px,n);bi,bd=ema_cross_signals(c2,200,500,2000)
    out["B_barras_equivalentes"]={"n_spot":n,"bars_spot":int(len(t2)),"bars_futures_in_overlap":int(bm.sum()),"signals_spot":int(len(bi)),"signals_futures":int(len(ri)),
        "agreement":{f"tol_{t}s":signal_agreement(bts[ri],rd,t2[bi],bd,t) for t in (900,3600,14400)}}
    hold=[900,1800,3600,7200];fpx_ts=bts[bm];fpx_px=bc[bm]*TICK
    out["B_barras_equivalentes"]["outcome_agreement"]=outcome_agreement(bts[ri],rd,fpx_ts,fpx_px,t2[bi],bd,sm_ts,sm_px,hold)
    Path(a.out).mkdir(parents=True,exist_ok=True);f=Path(a.out)/("equivalence_selftest.json" if a.selftest else "equivalence_spot_vs_mgc.json");f.write_text(json.dumps(out,indent=1,default=float));print(json.dumps(out,indent=1,default=float)[:3000])
if __name__=="__main__":main()
