import sys, json, pathlib, time
import numpy as np
from datetime import datetime, timezone
sys.path.insert(0, r"C:\ProyectosQuant\EdgeLab")
from edgelab.bridge.indicators.bigtrap2absorption import run as run_abs, DEFAULTS
from tools.sweep_bigtrap2_tickframes import load_canonical_ticks

BASE  = pathlib.Path(r"C:\Users\nicoc\OneDrive\Documentos\DataNT8")
CACHE = pathlib.Path(r"C:\Users\nicoc\AppData\Local\Temp\claude\C--Users-nicoc-OneDrive-Escritorio-Repositorios---Edges\89905be6-498d-439f-8be3-00dd77a7ceaa\scratchpad\b9cache152")
CACHE.mkdir(exist_ok=True)
# cadena rule-based de ENMIENDA_UNIVERSO_GATE1_2026-08-23.md (4 rolls, 2 confirmaciones)
CHAIN = {"GC 02-26": ("20251126","20260128"), "GC 04-26": ("20260129","20260327"),
         "GC 06-26": ("20260330","20260527"), "GC 08-26": ("20260528","20260630")}
# DST EEUU: termina 2025-11-02 07:00 UTC, arranca 2026-03-08 08:00 UTC
DST_O = int(datetime(2025,11,2,7,0,tzinfo=timezone.utc).timestamp())*10**9
DST_I = int(datetime(2026,3,8,8,0,tzinfo=timezone.utc).timestamp())*10**9
NS_H  = 3_600_000_000_000
def ctl(ts):  return ts + np.where((ts < DST_O) | (ts >= DST_I), -5, -6) * NS_H
def bins(ts): return ((((ctl(ts)//10**9)%86400)//60 - 1020) % 1440)//30
def sesd(ts): return ((ctl(ts) + 7*NS_H)//86_400_000_000_000).astype(np.int64)
def d2s(d):   return datetime.fromtimestamp(int(d)*86400, tz=timezone.utc).strftime("%Y%m%d")
def pct(v,q):
    v = np.asarray(v,dtype=float); v = v[np.isfinite(v)]
    return float(np.percentile(v,q)) if v.size else None

for c,(d0,d1) in CHAIN.items():
    f = CACHE/f"{c.replace(' ','_')}.npz"
    if f.exists(): print(f"[cache] {c}", flush=True); continue
    t0=time.time(); print(f"=== {c} {d0}->{d1} ===", flush=True)
    ticks,_,_,_,_,_ = load_canonical_ticks(BASE/f"{c}.Last.txt", tick_size=0.10, max_ticks=None)
    tl=time.time(); p=dict(DEFAULTS); p["ScoreMode"]="AbsMagnitude"
    res = run_abs(ticks, params=p); tk=time.time()
    # parseo rapido: posicional, sin dict ni strptime
    ev = res.get("events", [])
    TS=[]; THR=[]; NH=[]; RES=[]
    order=None
    for e in ev:
        i = e.find("|ABS_SCORE|")
        if i < 0: continue
        pa = e[i+11:].split(";")
        if order is None:
            order = [x.split("=",1)[0] for x in pa]
            iR,iT,iH,iS = order.index("residual"),order.index("a_thr"),order.index("n_hist"),order.index("t_start")
            print("    campos:", order, flush=True)
        RES.append(pa[iR][9:]); THR.append(pa[iT][6:]); NH.append(pa[iH][7:]); TS.append(pa[iS][8:34])
    ts  = np.array(TS, dtype="datetime64[ns]").astype(np.int64)
    thr = np.array([float(x) if x!="NaN" else np.nan for x in THR])
    nh  = np.array(NH, dtype=np.int32)
    rs  = np.array([x=="True" for x in RES])
    np.savez_compressed(f, ts=ts, thr=thr, nh=nh, res=rs,
                        tick_ts=ticks.ts_ns, spread=(ticks.ask_ticks-ticks.bid_ticks).astype(np.int32))
    print(f"    carga {tl-t0:.0f}s | kernel {tk-tl:.0f}s | parseo {time.time()-tk:.0f}s | {len(ts)} cubetas", flush=True)
    del ticks,res,ev

sess, bthr, btk, bsp = {}, {}, {}, {}
for c,(d0,d1) in CHAIN.items():
    z = np.load(CACHE/f"{c.replace(' ','_')}.npz")
    ts,thr,nh,rs = z["ts"],z["thr"],z["nh"],z["res"]
    ok = (~rs) & (nh>=200) & np.isfinite(thr) & (thr>0)      # no residual + post burn-in
    ts,thr = ts[ok],thr[ok]
    sd,bn = sesd(ts),bins(ts)
    days = np.unique(sd); days = days[[d0 <= d2s(x) <= d1 for x in days]]
    m = np.isin(sd,days)
    for x in np.unique(sd[m]): sess[d2s(x)] = (c, thr[m][sd[m]==x])
    for b in np.unique(bn[m]): bthr.setdefault(int(b),[]).extend(thr[m][bn[m]==b].tolist())
    T,SP = z["tick_ts"], z["spread"]
    sdT = sesd(T); mT = np.isin(sdT,days); bnT = bins(T)[mT]; SP = SP[mT]
    for b in np.unique(bnT):
        sel=bnT==b; bi=int(b)
        btk[bi]=btk.get(bi,0)+int(sel.sum()); bsp.setdefault(bi,[]).extend(SP[sel].tolist())
    print(f"  {c}: {len(days)} sesiones", flush=True)

out={"_meta":{"n_sesiones":len(sess),"universo":"ENMIENDA_UNIVERSO_GATE1_2026-08-23 (152 ses, 4 rolls rule-based)",
     "chain":{k:list(v) for k,v in CHAIN.items()},
     "nota":"a_thr de cubetas no residuales y post burn-in (n_hist>=200). Kernel headline AbsMagnitude, corrida por contrato."},
     "by_session":{},"by_bin":{}}
for s,(c,t) in sorted(sess.items()):
    out["by_session"][s]={"contrato":c,"n":int(t.size),"p10":pct(t,10),"p50":pct(t,50),"p90":pct(t,90),
        "ratio_p90_p10":(pct(t,90)/pct(t,10)) if pct(t,10) else None}
ns=max(len(sess),1)
for b in sorted(set(bthr)|set(btk)):
    t=bthr.get(b,[]); sp=bsp.get(b,[])
    out["by_bin"][str(b)]={"hora_ct":"%02d:%02d"%(((17*60+b*30)//60)%24,(b*30)%60),"n_cubetas":len(t),
        "a_thr_p10":pct(t,10),"a_thr_p50":pct(t,50),"a_thr_p90":pct(t,90),
        "a_thr_ratio_p90_p10":(pct(t,90)/pct(t,10)) if t and pct(t,10) else None,
        "n_ticks":btk.get(b,0),"tick_rate_seg":round(btk.get(b,0)/(ns*1800.0),3),
        "spread_p50":pct(sp,50),"spread_p90":pct(sp,90)}
pathlib.Path(r"C:\ProyectosQuant\EdgeLab\docs\research\B9_CONTEXTO_BT2_ABSORPTION.json").write_text(
    json.dumps(out,indent=2,ensure_ascii=False),encoding="utf-8")
print("\nOK sesiones=%d bins=%d"%(len(out["by_session"]),len(out["by_bin"])))
