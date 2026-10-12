#!/usr/bin/env python3
"""Mapa descriptivo de volatilidad por instrumento × franja horaria (CT) × horizonte, para diseñar el universo de corridas (no prueba ninguna hipótesis; no mira retornos futuros condicionados a nada).
Por cada instrumento (M1 de las sesiones aprobadas 2025-07-01 → 2026-09-30) y cada franja de 30 min: desvío estándar del retorno de `h` minutos (h ∈ {15, 30, 60}) que empieza en la franja,
en ticks y en USD por contrato, y media de |retorno|. Se corre como benchmark (sin alfa)."""
from __future__ import annotations
import json, os, sys, time
from pathlib import Path
import numpy as np
import pandas as pd
KAGGLE = Path("/kaggle/input").exists()
if KAGGLE:
    _roots = [Path("/kaggle/input"), *Path("/kaggle/input").glob("datasets/*")]
    os.environ["EDGELAB_DATA_ROOTS"] = os.pathsep.join(str(r) for r in _roots)
    sys.path.insert(0, str(next(p.parent for r in _roots for p in r.glob("edgelab-data-catalog/**/edgelab_data.py")))); OUT = Path("/kaggle/working")
else:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "docs/data_catalog")); OUT = Path(os.environ.get("UNIV_OUT", "/tmp/univ_out"))
OUT.mkdir(parents=True, exist_ok=True); os.environ.setdefault("EDGELAB_ALLOW_MISSING", "1")
import edgelab_data as ed
INST = ["ES", "NQ", "YM", "GC", "ZB", "6E", "6J"]; CT = "America/Chicago"; HS = (15, 30, 60); TICK_USD = {"ES": 12.5, "NQ": 5.0, "YM": 5.0, "GC": 10.0, "ZB": 31.25, "6E": 6.25, "6J": 6.25}
def main():
    t0 = time.time(); res = {}
    for inst in INST:
        m = ed.load_m1(inst, "2025-07-01", "2026-09-30")
        if m.empty: res[inst] = dict(error="sin datos"); continue
        loc = pd.DatetimeIndex(pd.to_datetime(m.minute.to_numpy(), utc=True)).tz_convert(CT); mod = (loc.hour * 60 + loc.minute).to_numpy(); day = loc.strftime("%Y-%m-%d").to_numpy()
        s = pd.Series(m.open.to_numpy().astype(float), index=pd.MultiIndex.from_arrays([day, mod])); s = s[~s.index.duplicated()]
        out = {}
        for h in HS:
            rows = []
            for slot in range(0, 24 * 60, 30):
                a = s.reindex(pd.MultiIndex.from_arrays([np.unique(day), np.full(len(np.unique(day)), slot)])); b = s.reindex(pd.MultiIndex.from_arrays([np.unique(day), np.full(len(np.unique(day)), slot + h)]))
                d = (b.to_numpy() - a.to_numpy()); d = d[np.isfinite(d)]                       # precio en ticks de precio (open del minuto)
                if len(d) >= 60: rows.append(dict(slot=f"{slot // 60:02d}:{slot % 60:02d}", n=int(len(d)), sd_ticks=float(d.std()), mean_abs_ticks=float(np.abs(d).mean()), sd_usd=float(d.std() * TICK_USD[inst])))
            out[f"h{h}"] = rows
        res[inst] = out; print(inst, f"{time.time() - t0:.0f}s", flush=True)
    (OUT / "UNIVERSE_SIGMA.json").write_text(json.dumps(dict(campaign="universe_sigma", period=["2025-07-01", "2026-09-30"], tick_usd=TICK_USD, res=res, seconds=round(time.time() - t0)), indent=1)); print("listo")
if __name__ == "__main__":
    main()
