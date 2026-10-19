"""Prueba: el kernel Python, corta las sesiones igual que el .cs?

No necesita alineacion tick-perfecta. Compara el PATRON de cortes de sesion:
la secuencia de cubetas residuales (posicion y largo) que produce cada lado.

Si la logica de sesion es la misma, las 29 sesiones que no tienen el hueco de
24 ticks deben producir residuales identicas. Si difieren en mas que esa, el
defecto es de kernel, no de datos.
"""
import sys
import pathlib
from datetime import datetime, timezone

import numpy as np

sys.path.insert(0, r"C:\ProyectosQuant\EdgeLab")
from edgelab.bridge.ticks import TickSeries
from edgelab.bridge.indicators.bigtrap2absorption import run as run_abs, DEFAULTS

EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
ART_NS = 3 * 3600 * 1_000_000_000
ANCLA = 92275
E = pathlib.Path(r"C:\Users\nicoc\Documents\NinjaTrader 8\exports"
                 r"\bt2_absorption__AbsMagnitude__GC0226dic__TW25.csv")
T = pathlib.Path(r"C:\Users\nicoc\OneDrive\Documentos\DataNT8\GC 02-26.Last.txt")


def tape_ns(s):
    d = datetime(int(s[0:4]), int(s[4:6]), int(s[6:8]),
                 int(s[9:11]), int(s[11:13]), int(s[13:15]), tzinfo=timezone.utc)
    return int((d - EPOCH).total_seconds()) * 1_000_000_000 + int(s[16:23]) * 100


def iso_art_ns(s):
    d = datetime(int(s[0:4]), int(s[5:7]), int(s[8:10]),
                 int(s[11:13]), int(s[14:16]), int(s[17:19]), tzinfo=timezone.utc)
    return (int((d - EPOCH).total_seconds()) * 1_000_000_000
            + int(s[20:27]) * 100 + ART_NS)


print("[*] oraculo...", flush=True)
o_bars = []
for ln in E.read_text(encoding="utf-8").splitlines():
    q = ln.split("|")
    if len(q) != 4 or q[2] != "BARRA_PROCESADA":
        continue
    d = dict(x.split("=", 1) for x in q[3].split(";") if "=" in x)
    o_bars.append({"bar": int(d["bar"]), "largo": int(d["largo"]),
                   "resid": d["residual"] == "True", "td": d["td"],
                   "ts": iso_art_ns(q[1])})
o_res = [(i, b["largo"], b["td"]) for i, b in enumerate(o_bars) if b["resid"]]
print("    cubetas=%d  residuales=%d" % (len(o_bars), len(o_res)))
fin_ns = o_bars[-1]["ts"]

print("[*] cinta...", flush=True)
ts, px, bid, ask, vol = [], [], [], [], []
with open(T, encoding="utf-8", errors="ignore") as f:
    for ln in f:
        p = ln.rstrip("\n").split(";")
        if len(p) < 5:
            continue
        ts.append(tape_ns(p[0]))
        px.append(round(float(p[1]) * 10))
        bid.append(round(float(p[2]) * 10))
        ask.append(round(float(p[3]) * 10))
        vol.append(int(float(p[4])))
ts = np.array(ts, dtype=np.int64)
hi = int(np.searchsorted(ts, fin_ns + 3_600_000_000_000, side="right"))
sl = slice(ANCLA, hi)
print("    ticks totales=%d   ventana [%d:%d] = %d ticks"
      % (len(ts), ANCLA, hi, hi - ANCLA))

serie = TickSeries(
    ts_ns=ts[sl],
    price_ticks=np.array(px, dtype=np.int64)[sl],
    bid_ticks=np.array(bid, dtype=np.int64)[sl],
    ask_ticks=np.array(ask, dtype=np.int64)[sl],
    volume=np.array(vol, dtype=np.float64)[sl],
    sequence=np.arange(hi - ANCLA, dtype=np.int64),
    tick_size=0.1)

print("[*] kernel...", flush=True)
p = dict(DEFAULTS)
p["ScoreMode"] = "AbsMagnitude"
res = run_abs(serie, params=p)

k_bars = []
for evt in res.get("events", []):
    q = evt.split("|")
    if len(q) != 4 or q[2] != "ABS_SCORE":
        continue
    d = dict(x.split("=", 1) for x in q[3].split(";") if "=" in x)
    k_bars.append({"bar": int(d["bar"]), "largo": int(d.get("n_ticks", 0)),
                   "resid": d.get("residual") == "True"})
k_res = [(i, b["largo"]) for i, b in enumerate(k_bars) if b["resid"]]
print("    cubetas=%d  residuales=%d" % (len(k_bars), len(k_res)))

print("\n" + "=" * 74)
print("COMPARACION DEL PATRON DE CORTES DE SESION")
print("=" * 74)
print("  residuales .cs     : %d" % len(o_res))
print("  residuales Python  : %d" % len(k_res))
print()
print("  %-4s %-10s %14s %14s %10s" % ("#", "td (.cs)", "pos .cs", "pos Python", "largo"))
n = max(len(o_res), len(k_res))
iguales = 0
for i in range(n):
    a = o_res[i] if i < len(o_res) else None
    b = k_res[i] if i < len(k_res) else None
    if a and b:
        dl = "%d / %d %s" % (a[1], b[1], "OK" if a[1] == b[1] else "<<<")
        if a[1] == b[1]:
            iguales += 1
        print("  %-4d %-10s %14d %14d %10s" % (i + 1, a[2], a[0], b[0], dl))
    elif a:
        print("  %-4d %-10s %14d %14s %10s" % (i + 1, a[2], a[0], "-", "solo .cs"))
    else:
        print("  %-4d %-10s %14s %14d %10s" % (i + 1, "?", "-", b[0], "solo Python"))
print()
print("  residuales con largo identico: %d/%d" % (iguales, n))
print("  desplazamiento de posicion    : %s"
      % ("constante" if len({a[0] - b[0] for a, b in zip(o_res, k_res)}) == 1
         else sorted({a[0] - b[0] for a, b in zip(o_res, k_res)})[:8]))
