#!/usr/bin/env python3
"""Claim: tras el close de la 25-tick con TRAP, la SIGUIENTE va contra la absorcion.
Holdout 17-21 ago. Descriptivo. Ver docs/research/h_gc_bt2x_next_bar.json.
Ajustar ORACULO y TICKS a las rutas locales.
"""
from __future__ import annotations
import collections, datetime as dt, json
import numpy as np
ORACULO = "oracle_events__Tick25.csv"
TICKS = "GC 12-26.Last.txt"
TICK = 0.10
OFF_H = 3

def leer_ticks(path):
    ts, px = [], []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            p = line.rstrip("\n").split(";")
            if len(p) < 5: continue
            a, b, c = p[0].split(" ")
            e = int(dt.datetime(int(a[:4]), int(a[4:6]), int(a[6:8]), int(b[:2]), int(b[2:4]), int(b[4:6]), tzinfo=dt.timezone.utc).timestamp())
            ts.append(e * 1_000_000_000 + int(c) * 100)
            px.append(float(p[1]))
    return np.asarray(ts, np.int64), np.asarray(px)

def leer_oraculo(path):
    barras, traps = {}, []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.startswith("#") or "|" not in line: continue
            p = line.strip().split("|")
            if len(p) < 4: continue
            tipo = p[2].strip()
            kv = dict(x.split("=", 1) for x in p[3].split(";") if "=" in x)
            try:
                raw = dt.datetime.fromisoformat(p[1][:26]).replace(tzinfo=dt.timezone.utc)
            except Exception:
                continue
            ts0 = int(raw.timestamp() * 1e9) + OFF_H * 3600 * 10**9
            if tipo == "BARRA_PROCESADA":
                barras[int(kv["bar"])] = dict(largo=int(kv.get("largo", 25)), tclose=ts0)
            elif tipo == "TRAP":
                traps.append((int(kv["bar"]), kv))
    return barras, traps

def ohlc(pt, i0, i1):
    seg = pt[i0:i1]
    if len(seg) == 0: return None
    return dict(o=int(seg[0]), h=int(seg.max()), l=int(seg.min()), c=int(seg[-1]), n=int(len(seg)))

if __name__ == "__main__":
    print("ver docs/research/HANDOFF_2026-08-21_SANDBOX_AUDITOR.md")
    print("resultado ya medido: docs/research/h_gc_bt2x_next_bar.json")
