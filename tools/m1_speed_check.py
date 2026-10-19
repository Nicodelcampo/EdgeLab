#!/usr/bin/env python3
"""Compara `edgelab_data.load_m1` (rápida) con `_load_m1_slow` (original): tiempo y igualdad exacta. Uso: EDGELAB_DATA_ROOTS=/data/fakeroot python tools/m1_speed_check.py GC 2026-04-01 2026-06-30"""
import os,sys,time
from pathlib import Path
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"docs/data_catalog"))
import edgelab_data as ed
inst,a,b=sys.argv[1:4];os.environ.setdefault("EDGELAB_M1_CACHE","/data/m1cache_test")
t=time.time();slow=ed._load_m1_slow(inst,a,b);ts=time.time()-t
t=time.time();fast=ed.load_m1(inst,a,b);tf=time.time()-t
t=time.time();fast2=ed.load_m1(inst,a,b);tf2=time.time()-t
print(f"lenta {ts:.1f}s | rápida (1ª vez, arma caché) {tf:.1f}s | rápida (con caché) {tf2:.2f}s | filas {len(slow)} {len(fast)}")
pd.testing.assert_frame_equal(slow,fast,check_dtype=True,check_like=False);pd.testing.assert_frame_equal(slow,fast2);print("IGUALES (columnas, tipos y valores)")
