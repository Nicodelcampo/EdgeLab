"""Descripcion target-free de los impulsos marcados (nada posterior a la marca). Uso: describir_impulsos.py <bundle> <impulsos.json>..."""
import json, sys
import numpy as np, pandas as pd

B = json.load(open(sys.argv[1], encoding="utf-8")); Z = {z["id"]: z for z in B["runs"][0]["zones"]}
for f in sys.argv[2:]:
    I = json.load(open(f, encoding="utf-8")); d = pd.DataFrame(I["impulsos"])
    ny = pd.to_datetime(d.tc, unit="s", utc=True).dt.tz_convert("America/New_York"); h = ny.dt.hour + ny.dt.minute / 60
    fog, fop, edad, alto = [], [], [], []
    for _, g in d.iterrows():
        zs = [Z[i] for i in g.zona_ids]
        fog.append(np.mean(["OG" in z["kind"] for z in zs])); fop.append(np.mean([("BULL" in z["kind"]) != (g.dir == "up") for z in zs]))
        edad += [(g.tc - 60 - z["available_ts"]) / 60 for z in zs]; alto += [z["height_ticks"] for z in zs]
    q = lambda x: "/".join(f"{v:g}" for v in np.percentile(x, [10, 50, 90]).round(2))
    gap = np.diff(np.sort(d.tc.values)) / 60
    print(f"== {f}  vida={I['params']['vida_velas']}")
    print(f"N={len(d)} dias={ny.dt.date.nunique()} max/dia={ny.dt.date.value_counts().max()} <30min={int((gap < 30).sum())} sube/baja={int((d.dir == 'up').sum())}/{int((d.dir == 'down').sum())}")
    print(f"apertura 9:30-11={int(((h >= 9.5) & (h < 11)).sum())} 3-8h={int(((h >= 3) & (h < 8)).sum())} 17-24h={int((h >= 17).sum())}")
    print(f"umbral zonas={I['umbrales']['zonas_min_rango']}")
    for k in ("rango", "velas", "velas_m1", "vel", "zonas"): print(f"  {k} p10/50/90 = {q(d[k])}")
    print(f"  fracOG={q(fog)} fracOpuestas={q(fop)} edad_min={q(edad)} alto_ticks={q(alto)}")
