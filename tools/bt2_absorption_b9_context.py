import sys, json, pathlib, time
import numpy as np
from datetime import datetime, timezone
sys.path.insert(0, r"C:\ProyectosQuant\EdgeLab")
from edgelab.bridge.indicators.bigtrap2absorption import run as run_abs, DEFAULTS
from tools.sweep_bigtrap2_tickframes import load_canonical_ticks
BASE = pathlib.Path(r"C:\Users\nicoc\OneDrive\Documentos\DataNT8")
CACHE = pathlib.Path(r"C:\Users\nicoc\AppData\Local\Temp\claude\C--Users-nicoc-OneDrive-Escritorio-Repositorios---Edges\89905be6-498d-439f-8be3-00dd77a7ceaa\scratchpad\b9cache")
CACHE.mkdir(exist_ok=True)
CHAIN = {"GC 04-26": ("20260120","20260326"), "GC 06-26": ("20260327","20260526"), "GC 08-26": ("20260527","20260630")}
DST = int(datetime(2026,3,8,8,0,tzinfo=timezone.utc).timestamp())*1_000_000_000
NS_H = 3_600_000_000_000
ctl  = lambda ts: ts + np.where(ts >= DST, -5, -6) * NS_H
bins = lambda ts: ((((ctl(ts)//1_000_000_000)%86400)//60 - 1020) % 1440)//30
sesd = lambda ts: ((ctl(ts) + 7*NS_H)//86_400_000_000_000).astype(np.int64)
d2s  = lambda d: datetime.fromtimestamp(int(d)*86400, tz=timezone.utc).strftime("%Y%m%d")
def pct(v,q):
    v = np.asarray(v,dtype=float); v = v[np.isfinite(v)]
    return float(np.percentile(v,q)) if v.size else None

for c,(d0,d1) in CHAIN.items():
    f = CACHE/f"{c.replace(' ','_')}.npz"
    if f.exists(): print(f"[cache] {c}", flush=True); continue
    t0=time.time(); print(f"=== {c} ===", flush=True)
    ticks,_,_,_,_,_ = load_canonical_ticks(BASE/f"{c}.Last.txt", tick_size=0.10, max_ticks=None)
    p=dict(DEFAULTS); p["ScoreMode"]="AbsMagnitude"
    res=run_abs(ticks, params=p)
    ts_l,thr_l,nh_l,sc_l,ap_l = [],[],[],[],[]
    for ev in res.get("events",[]):
        q=ev.split("|")
        if len(q)<4 or q[2]!="ABS_SCORE": continue
        d=dict(i.split("=",1) for i in q[3].split(";") if "=" in i)
        if d.get("residual")=="True": continue
        ts_l.append(int(datetime.strptime(d["t_start"][:26],"%Y-%m-%dT%H:%M:%S.%f").replace(tzinfo=timezone.utc).timestamp()*1e9))
        thr_l.append(float(d.get("a_thr","nan")))
        nh_l.append(int(d.get("n_hist",0)))
        sc_l.append(float(d.get("a_score","nan")))
        ap_l.append(1 if d.get("a_pass")=="True" else 0)
    np.savez_compressed(f, ts=np.array(ts_l,dtype=np.int64), thr=np.array(thr_l),
        nh=np.array(nh_l,dtype=np.int32), sc=np.array(sc_l), ap=np.array(ap_l,dtype=np.int8),
        tick_ts=ticks.ts_ns, spread=(ticks.ask_ticks-ticks.bid_ticks).astype(np.int32))
    print(f"    cacheado {time.time()-t0:.0f}s  cubetas={len(ts_l)}", flush=True)
    del ticks,res

sess_thr, bin_thr, bin_tk, bin_sp = {}, {}, {}, {}
for c,(d0,d1) in CHAIN.items():
    z = np.load(CACHE/f"{c.replace(' ','_')}.npz")
    ts,thr,nh = z["ts"],z["thr"],z["nh"]
    ok = (nh >= 200) & np.isfinite(thr) & (thr > 0)          # <-- burn-in fuera
    ts,thr = ts[ok],thr[ok]
    sd,bn = sesd(ts),bins(ts)
    days = np.unique(sd); days = days[[d0 <= d2s(x) <= d1 for x in days]]
    m = np.isin(sd,days)
    for x in np.unique(sd[m]): sess_thr[d2s(x)] = (c, thr[m][sd[m]==x])
    for b in np.unique(bn[m]): bin_thr.setdefault(int(b),[]).extend(thr[m][bn[m]==b].tolist())
    T,SP = z["tick_ts"], z["spread"]
    sdT = sesd(T); mT = np.isin(sdT,days); bnT = bins(T)[mT]; SP = SP[mT]
    for b in np.unique(bnT):
        sel = bnT==b; bi=int(b)
        bin_tk[bi]=bin_tk.get(bi,0)+int(sel.sum()); bin_sp.setdefault(bi,[]).extend(SP[sel].tolist())

out={"_meta":{"n_sesiones":len(sess_thr),"chain":{k:list(v) for k,v in CHAIN.items()},
     "nota":"a_thr de cubetas no residuales y post burn-in (n_hist>=200). Kernel headline AbsMagnitude, corrida por contrato."},
     "by_session":{},"by_bin":{}}
for s,(c,t) in sorted(sess_thr.items()):
    out["by_session"][s]={"contrato":c,"n":int(t.size),"p10":pct(t,10),"p50":pct(t,50),"p90":pct(t,90),
        "ratio_p90_p10":(pct(t,90)/pct(t,10)) if pct(t,10) else None}
ns=max(len(sess_thr),1)
for b in sorted(set(bin_thr)|set(bin_tk)):
    t=bin_thr.get(b,[]); sp=bin_sp.get(b,[])
    out["by_bin"][str(b)]={"hora_ct":"%02d:%02d"%(((17*60+b*30)//60)%24,(b*30)%60),"n_cubetas":len(t),
        "a_thr_p10":pct(t,10),"a_thr_p50":pct(t,50),"a_thr_p90":pct(t,90),
        "a_thr_ratio_p90_p10":(pct(t,90)/pct(t,10)) if t and pct(t,10) else None,
        "n_ticks":bin_tk.get(b,0),"tick_rate_seg":round(bin_tk.get(b,0)/(ns*1800.0),3),
        "spread_p50":pct(sp,50),"spread_p90":pct(sp,90)}
pathlib.Path(r"C:\ProyectosQuant\EdgeLab\docs\research\B9_CONTEXTO_BT2_ABSORPTION.json").write_text(
    json.dumps(out,indent=2,ensure_ascii=False),encoding="utf-8")
print("OK sesiones=%d bins=%d"%(len(out["by_session"]),len(out["by_bin"])))
