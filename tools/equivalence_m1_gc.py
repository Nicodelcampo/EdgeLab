#!/usr/bin/env python3
"""Equivalencia de M1 spot (Dukascopy) con GC para horas fijas. Umbrales en docs/research/equivalence_20261004/PREREGISTRO_EQUIVALENCIA_M1.md."""
import json,sys
from pathlib import Path
import numpy as np,pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from edgelab.discovery import cache as CA,data as D,pipeline as P
MIN=60_000_000_000
def main():
    asset=json.loads(Path("config/discovery/assets/GC.json").read_text());bars,rows,order,segs,elig,_,_=CA.load_cache(asset,"/data/cache/discovery")
    T=[];C=[]
    for ci,c in enumerate(order):
        b=bars[c];td=D.tdate_ordinal(b["t"]);m=np.array([elig.get(int(x))==ci for x in td]);T.append(b["t"][m]);C.append(b["c"][m]*0.1)
    t=np.concatenate(T);c=np.concatenate(C);o=np.argsort(t,kind="stable");t,c=t[o],c[o]
    s=pd.read_parquet("/data/spot/XAUUSD_m1.parquet");st=s["time_utc_ns"].to_numpy()+MIN;sp=((s["bid_close"]+s["ask_close"])/2).to_numpy();ok=(s["bid_vol"]+s["ask_vol"]).to_numpy()>=0
    common,ig,isp=np.intersect1d(t,st,return_indices=True);tg,cg,cs=common,c[ig],sp[isp];out={"minutes_common":int(len(common)),"first":str(pd.Timestamp(int(tg[0]),tz="UTC")),"last":str(pd.Timestamp(int(tg[-1]),tz="UTC"))}
    # 1) retornos de 1 min
    k=np.diff(tg)==MIN;rg=np.diff(cg)[k];rs=np.diff(cs)[k];nz=(rg!=0)&(rs!=0)
    out["M1a_corr_1min_returns"]=float(np.corrcoef(rg,rs)[0,1]);out["sign_agreement_nonzero_1min"]=float((np.sign(rg[nz])==np.sign(rs[nz])).mean());out["n_1min_returns"]=int(k.sum())
    # 2) y 3) horas fijas: 96 franjas por sesión
    slots=tuple(h*100+m for h in range(24) for m in (0,15,30,45));dates=np.array(sorted(elig));G=P.slot_grid(dates-0,slots)  # UTC ns de cada franja (D,S) por fecha de calendario
    idx={int(x):i for i,x in enumerate(tg)};mom_g=[];mom_s=[];rh_g=[];rh_s=[]
    lut_g=dict(zip(tg.tolist(),cg));lut_s=dict(zip(tg.tolist(),cs))
    for row in G:
        for b0 in row:
            if b0<=0:continue
            b1=int(b0)+MIN;a=b1-15*MIN;e=int(b0)+2*MIN+MIN;x=e+15*MIN      # señal: barra que cierra en franja+1 min; entrada: cierre de la barra de franja+2 min
            if b1 in lut_g and a in lut_g:mom_g.append(lut_g[b1]-lut_g[a]);mom_s.append(lut_s[b1]-lut_s[a])
            if e in lut_g and x in lut_g:rh_g.append(lut_g[x]-lut_g[e]);rh_s.append(lut_s[x]-lut_s[e])
    mg,ms,hg,hs=map(np.array,(mom_g,mom_s,rh_g,rh_s));nzm=(mg!=0)&(ms!=0)
    out["M1b_sign_agreement_mom15"]=float((np.sign(mg[nzm])==np.sign(ms[nzm])).mean());out["n_mom15"]=int(len(mg))
    out["M1c_corr_hold15_returns"]=float(np.corrcoef(hg,hs)[0,1]);out["M1d_mean_abs_diff_over_std_gc"]=float(np.abs(hg-hs).mean()/hg.std());out["n_hold15"]=int(len(hg));out["std_hold15_gc"]=float(hg.std())
    th={"M1a_corr_1min_returns":(">=",0.90),"M1b_sign_agreement_mom15":(">=",0.90),"M1c_corr_hold15_returns":(">=",0.90),"M1d_mean_abs_diff_over_std_gc":("<=",0.25)}
    res={k:(out[k]>=v if op==">=" else out[k]<=v) for k,(op,v) in th.items()};out["pasa"]=res;n=sum(res.values());out["veredicto"]="M1_UTILIZABLE" if n==4 else ("M1_PARCIAL" if n>0 else "M1_NO_UTILIZABLE")
    Path("docs/research/equivalence_20261004/equivalence_m1_spot_vs_gc.json").write_text(json.dumps(out,indent=1));print(json.dumps(out,indent=1))
if __name__=="__main__":main()
