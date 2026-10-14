#!/usr/bin/env python3
"""Calibra el detector de zonas EMA-estables contra las capturas del usuario (1 píxel ≈ 1 barra de 25 ticks; escala ajustada con la propia EMA dibujada).
No lee datos de mercado de edgelab (las zonas son posteriores al holdout). Entrada: docs/research/ema_trend/templates.json. Salida: docs/research/ema_trend/calibration.json"""
import itertools, json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from edgelab.research import ema_zones as Z

T = json.load(open("docs/research/ema_trend/templates.json")); Z.EXPANDING = True
DIR = {"down_A": -1, "up_B": 1, "down_C": -1, "down_D": -1}


def series(t):
    hi, lo, em = Z._fill(t["hi"]), Z._fill(t["lo"]), Z._fill(t["ema"]); close = -(hi + lo) / 2; high, low = -hi, -lo
    return close, high, low, -em


def prep():
    out = {}
    for k, t in T.items():
        c, h, l, e = series(t); b = t["blue"]; out[k] = (Z.precompute(c, h, l, atr_n=50, e=e), (b["x0"], b["x1"], DIR[k]), len(c))
    return out


def evaluate(D, **kw):
    rec, fp, det = [], [], []
    for k, (P, (a, b, d), n) in D.items():
        st = Z.state(P, **kw); seg = st[a:b + 1] == d; rec.append(seg.mean()); det.append(np.argmax(seg) / len(seg) if seg.any() else 1.0)
        out = np.ones(n, bool); out[a:b + 1] = False; fp.append((st[out] != 0).mean())
    return float(np.mean(rec)), float(np.max(rec) if False else np.min(rec)), float(np.mean(fp)), float(np.mean(det)), rec


if __name__ == "__main__":
    D = prep(); rows = []
    grid = dict(M=[40, 60, 80, 120, 160], K=[50, 100, 150], f=[0.7, 0.8, 0.9, 0.95], er=[0.0, 0.3, 0.5, 0.7], dmin=[0.0, 0.5, 1.0], cv=[0.0, 0.5, 1.0], hold=[0, 10, 30], drift_atr=[0.0, 0.5])
    keys = list(grid)
    for vals in itertools.product(*[grid[k] for k in keys]):
        kw = dict(zip(keys, vals)); r, rmin, fp, det, rec = evaluate(D, **kw); rows.append((kw, r, rmin, fp, det, rec))
    rows.sort(key=lambda x: -(x[1] - 1.5 * x[3]))                       # objetivo: recall medio menos 1,5 × falsos positivos (barras marcadas fuera de las zonas del usuario)
    print("ref. detector original (W=300,ER .85,side .97): ", end="")
    base = evaluate(D, M=300, K=300, f=0.97, er=0.85, dmin=0.5, cv=0.45, drift_atr=1.2); print([round(x, 2) for x in base[:4]], "recall por captura", [round(x, 2) for x in base[4]])
    for kw, r, rmin, fp, det, rec in rows[:8]: print(kw, "recall", round(r, 2), "min", round(rmin, 2), "fp", round(fp, 2), "detecta a", round(det, 2), [round(x, 2) for x in rec])
    Path("docs/research/ema_trend/calibration.json").write_text(json.dumps([dict(params=kw, recall=r, recall_min=rmin, fp_outside=fp, detect_frac=det, recall_each=[float(x) for x in rec]) for kw, r, rmin, fp, det, rec in rows[:50]], indent=1))
