"""Paridad aVolZonePOI2 NT8 <-> Python: bloques (score, nivel, franja), zonas y clasificación orderblock."""
import sys, dataclasses, numpy as np, pandas as pd
sys.path.insert(0, r"E:\EdgeLab-gex")
from edgelab.bridge import ticks as T, bars as B
from edgelab.bridge.indicators.avolzonepoi2 import run
O = sys.argv[1] if len(sys.argv) > 1 else r"E:\EdgeLab\data\nt8_oracles\avolzonepoi_MNQ1226_200t_20260715_20260930.csv"
rows = [l.rstrip("\n").split(",") for l in open(O, encoding="utf-8") if not l.startswith("#")]
Bn = pd.DataFrame([r for r in rows if r[0] == "B"], columns=["k", "bar", "time", "levels", "best", "bucket", "sess"])
Zn = pd.DataFrame([r for r in rows if r[0] == "Z"], columns=["k", "bar", "time", "low", "high", "levels", "score", "thr", "samples"])
On = pd.DataFrame([r for r in rows if r[0] == "O"], columns=["k", "bar", "time", "zbar", "low", "seen", "inpct", "state"])
Rn = pd.DataFrame([r for r in rows if r[0] == "R"], columns=["k", "bar", "time", "zbar", "low", "n"])
Cn = pd.DataFrame([r for r in rows if r[0] == "C"], columns=["k", "bar", "time", "start", "low", "high", "idx"])
for d in (Bn, Zn, On, Rn, Cn):
    for c in d.columns[1:]:
        if c != "time":
            d[c] = pd.to_numeric(d[c])
print("NT8: bloques", len(Bn), "zonas", len(Zn), "OB", len(On), "| primero", Bn.time.iloc[0], "último", Bn.time.iloc[-1])
last = pd.Timestamp(Bn.time.iloc[-1], tz="America/Argentina/Buenos_Aires")
import os
os.environ["AVCL_INST"] = "MNQ"; os.environ.setdefault("AVCL_OUT", r"C:/tmp_x")
sys.path.insert(0, r"E:/EdgeLab-gex/tools")
import vtd_bracket_stage1 as V
# El chart fusiona contratos (Merge back adjusted): 09-26 hasta el roll, 12-26 después. Los scores sólo dependen del
# volumen, así que el ajuste de precio no los cambia; las zonas se comparan restando el offset de precio del roll.
ROLL = pd.Timestamp(os.environ.get("ZP_ROLL", "2026-09-13 17:00"), tz="America/Chicago").value
sess = V.ed.sessions("MNQ", "2026-07-01", "2026-09-30")
def part(c, a_, b_):
    ds, fl, _a, _b, _d = V.contract_rows(c, sess)
    print("fuente", c, ds, fl)
    return V.load_ticks(V.ed._path(ds, fl), a_, b_, c)
t1 = part("MNQ_09-26", 1784066400000000000, ROLL)
t2 = part("MNQ_12-26", ROLL, (last + pd.Timedelta(minutes=30)).value)
# memoria (PC de 16 GB): sólo se concatenan ts, precio y volumen; bid/ask/sequence no se usan y se descartan
import gc
cols = {f: np.concatenate([getattr(t1, f), getattr(t2, f)]) for f in ("ts_ns", "price_ticks", "volume")}
nT = len(cols["ts_ns"])
del t1; gc.collect()
z0 = np.zeros(nT, dtype=np.int64)
tk = dataclasses.replace(t2, bid_ticks=z0, ask_ticks=z0, sequence=np.arange(nT, dtype=np.int64), **cols)
del t2, cols; gc.collect()
SPEC = int(os.environ.get("ZP_SPEC", 200))
PARAMS = __import__("json").loads(os.environ.get("ZP_PARAMS", "{}"))
bars = B.build_tick_bars(tk, SPEC)
fp = B.build_total_footprint_csr_nt8(tk, bars)
sys.path.insert(0, r"E:\EdgeLab-gex\tools")
from vtd_bracket_stage1 import session_end_vec
sid = session_end_vec(np.asarray(bars.end_ns, dtype=np.int64))
r = run(bars, fp, sid, PARAMS)
ts = lambda b: pd.to_datetime(np.asarray(bars.end_ns)[b], utc=True).tz_convert("America/Argentina/Buenos_Aires").strftime("%Y-%m-%d %H:%M:%S.%f").str[:23]
Bp = pd.DataFrame(r["blocks"], columns=["bar", "levels", "best", "bucket", "sess"]); Bp["time"] = ts(Bp.bar)
Bp = Bp[Bp.bar <= Bn.bar.max()]
tk_ = 0.25
Zp = pd.DataFrame(r["zones"]); Zp = Zp[Zp.bar <= Bn.bar.max()]
Zp["time"] = ts(Zp.bar); Zp["low"] = Zp.low_tick * tk_; Zp["high"] = Zp.high_tick * tk_
m = Bn.merge(Bp, on="bar", how="outer", indicator=True, suffixes=("_n", "_p"))
print("bloques:", m._merge.value_counts().to_dict())
b = m[m._merge == "both"]
for c in ("time", "levels", "bucket", "sess"):
    print(" ", c, "igual", round((b[c + "_n"] == b[c + "_p"]).mean(), 6))
print("  best igual (|d|<1e-6)", round(((b.best_n - b.best_p).abs() < 1e-6).mean(), 6))
bad = b[(b.best_n - b.best_p).abs() >= 1e-6]
if len(bad): print(bad[["bar", "time_n", "time_p", "levels_n", "levels_p", "best_n", "best_p"]].head(5).to_string())
# offset del back-adjust: diferencia de precio entre NT8 y Python en las zonas anteriores al roll (misma barra)
roll_bar = int(np.searchsorted(np.asarray(bars.end_ns), ROLL))
pre = Zn[Zn.bar < roll_bar].merge(Zp[Zp.bar < roll_bar], on=["bar", "score"], suffixes=("_n", "_p"))
OFF = float((pre.low_n - pre.low_p).mode().iloc[0]) if len(pre) else 0.0
print("roll en barra", roll_bar, "offset back-adjust", OFF, "puntos (zonas pre-roll con ese offset:", round(((pre.low_n - pre.low_p) == OFF).mean(), 6), ")")
for c in ("low", "high"):
    Zp[c] = np.where(Zp.bar < roll_bar, Zp[c] + OFF, Zp[c])
Zn["low"] = Zn.low.round(2); Zn["high"] = Zn.high.round(2); Zp["low"] = Zp.low.round(2); Zp["high"] = Zp.high.round(2)
key = ["bar", "low", "high"]
mz = Zn.merge(Zp, on=key, how="outer", indicator=True, suffixes=("_n", "_p"))
print("zonas:", mz._merge.value_counts().to_dict())
bz = mz[mz._merge == "both"]
print("  score igual", round(((bz.score_n - bz.score_p).abs() < 1e-6).mean(), 6), "thr igual", round(((bz.thr - bz.thresh).abs() < 1e-6).mean(), 6))
print(mz[mz._merge != "both"][["bar", "low", "high", "score_n", "score_p", "thr", "thresh", "_merge"]].head(8).to_string())
Zd = Zp[Zp.decided_bar.notna()].copy()  # ya con offset
Zd["zbar"] = Zd.bar; Zd["low"] = Zd.low.round(2)
On["low"] = On.low.round(2)
mo = On.merge(Zd, on=["zbar", "low"], how="outer", indicator=True, suffixes=("_n", "_p"))
print("clasificación OB:", mo._merge.value_counts().to_dict())
bo = mo[mo._merge == "both"]
import json
res = dict(bloques=int(len(b)), bloques_iguales=bool(((b.best_n - b.best_p).abs() < 1e-6).all()), zonas_nt8=int(len(Zn)), zonas_match=int(len(bz)), offset=OFF, ob_nt8=int(len(On)), ob_match=int(len(bo)), estado_igual=float((bo.state_n == bo.state_p).mean()), decision_igual=float((bo.bar_n == bo.decided_bar).mean()))
open(r"E:/EdgeLab-gex/docs/parity/paridad_avolzonepoi2_MNQ1226_%dt.json" % SPEC, "w").write(json.dumps(res, indent=1))
print("  estado igual", round((bo.state_n == bo.state_p).mean(), 6), "barra de decisión igual", round((bo.bar_n == bo.decided_bar).mean(), 6),
      "| OB NT8", int((On.state == 2).sum()), "py", int((Zd.state == 2).sum()))

# racimos: barra en que cada zona entra a un racimo
if len(Rn):
    Rn["low"] = Rn.low.round(2)
    Zr = Zp[Zp.racimo_bar >= 0][["bar", "low", "racimo_bar"]].rename(columns={"bar": "zbar"})
    Zr["low"] = Zr.low.round(2)
    mr = Rn.merge(Zr, on=["zbar", "low"], how="outer", indicator=True)
    print("racimo (zona, barra de entrada):", mr._merge.value_counts().to_dict(),
          "barra igual", round((mr[mr._merge == "both"].bar == mr[mr._merge == "both"].racimo_bar).mean(), 6))
    Cl = pd.DataFrame(r["clusters"])
    if len(Cn) and len(Cl):
        last_c = Cn.groupby("idx").last().reset_index()
        Cl["idx"] = range(len(Cl))
        Cl["low_p"] = np.where(Cl.start < roll_bar, Cl.low + OFF / tk_, Cl.low) * tk_
        Cl["high_p"] = np.where(Cl.start < roll_bar, Cl.high + OFF / tk_, Cl.high) * tk_
        mc = last_c.merge(Cl, on="idx")
        print("racimos NT8", len(last_c), "py", len(Cl), "| inicio igual", round((mc.start_x == mc.start_y).mean(), 6),
              "piso igual", round(((mc.low_x - mc.low_p).abs() < 1e-6).mean(), 6), "techo igual", round(((mc.high - mc.high_p).abs() < 1e-6).mean(), 6))
