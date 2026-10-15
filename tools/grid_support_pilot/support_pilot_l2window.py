"""Soporte de etiquetas (primer paso) sobre la ventana L2 de ES usando los trades del L1 local (E:/l2_parquet).
ts_us = reloj de pared ART (UTC-3) leido como UTC: se convierte sumando 3 h. Contrato principal por sesion = el de mas filas L1.
Mide resolucion, no predictibilidad. Solo precio; sin modelo."""
import glob, json, os, re, sys, time
from datetime import datetime
from pathlib import Path
import numpy as np, pyarrow.parquet as pq
sys.path.insert(0, str(Path(__file__).parent))
import support_pilot_kernel as K

ART_TO_UTC_NS = 3 * 3600 * 1_000_000_000
best = {}
for c in glob.glob("E:/l2_parquet/ES_*"):
    for f in glob.glob(c + "/l1_quotes/*.parquet"):
        d = re.search(r"(20\d{6})", os.path.basename(f)).group(1)
        n = pq.ParquetFile(f).metadata.num_rows
        if d not in best or n > best[d][0]:
            best[d] = (n, f)
sessions = []
for d in sorted(best):
    t = pq.read_table(best[d][1], columns=["ts_us", "side", "price_tick"])
    m = t["side"].to_numpy() == 2
    ts = t["ts_us"].to_numpy()[m].astype(np.int64) * 1000 + ART_TO_UTC_NS
    px = t["price_tick"].to_numpy()[m].astype(np.int64)
    if len(ts) < 1000: continue
    if (np.diff(ts) < 0).any():
        o = np.argsort(ts, kind="mergesort"); ts, px = ts[o], px[o]
    off = int(datetime.fromtimestamp(int(ts[len(ts)//2]) / 1e9, K.CHI).utcoffset().total_seconds())
    sessions.append((int(d), ts, px, off))
print("sesiones L2 (trades L1):", len(sessions), sessions[0][0], sessions[-1][0], flush=True)
tmax = max(K.HORIZONS_S) * 1_000_000_000
per = {}
for td, ts, px, off in sessions:
    mins = ((ts // 1_000_000_000 + off) % 86400) // 60
    rth = (mins >= K.RTH_MIN[0]) & (mins <= K.RTH_MIN[1])
    if not rth.any(): continue
    dec = np.arange(int(ts[rth][0]), int(ts[rth][-1]), K.DECISION_STEP_S * 1_000_000_000, dtype=np.int64)
    mm = ((dec // 1_000_000_000 + off) % 86400) // 60
    dec = dec[(mm >= K.RTH_MIN[0]) & (mm <= K.RTH_MIN[1])]
    tu, tdn, ok, cov = K.scan_session(ts, px, dec, K.LEVELS, tmax)
    tu, tdn, cov = tu[ok], tdn[ok], cov[ok]
    for pair in K.PAIRS:
        for T in K.HORIZONS_S:
            per.setdefault((pair, T), []).append(K.classify(tu, tdn, cov, pair[0], pair[1], T * 1_000_000_000).sum(axis=0))
rows = []
for (pair, T), lst in per.items():
    tot = np.array(lst).sum(axis=0); n = tot.sum()
    rows.append(dict(X=pair[0], Y=pair[1], T_s=T, p_R=round(tot[0]/n,4), p_C=round(tot[1]/n,4), p_timeout=round(tot[3]/n,4), p_censurado=round(tot[4]/n,4),
                     sesiones=len(lst), p_eq=round((pair[1]+K.FRICTION_ES)/(pair[0]+pair[1]),4)))
out = Path("docs/research/grid_support_pilot_20261015/GRID_SUPPORT_PILOT_L2WINDOW.json")
out.write_text(json.dumps(dict(ventana=[sessions[0][0], sessions[-1][0]], sesiones=len(sessions), tabla=rows), indent=1), encoding="utf-8")
for r in rows:
    if r["T_s"] in (900, 1800, 3600) and (r["X"], r["Y"]) in ((24,24),(32,32),(48,32),(48,48)):
        print(r)
