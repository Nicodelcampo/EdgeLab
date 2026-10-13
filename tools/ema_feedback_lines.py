#!/usr/bin/env python3
"""Mide las líneas azules de las capturas del usuario (22-31): extensión, pendiente, desplazamiento en ATR, toques, distancia media y máxima al precio. Sirve para calibrar qué líneas el usuario considera buenas o malas."""
import json, sys
import numpy as np
from PIL import Image
sys.path.insert(0, ".")
from edgelab.research import ema_zones as Z

D = "/tmp/claude-0/-home-user-EdgeLab/c1d99ed7-90f8-5ca5-8a93-7e5ff1aefe21/images/"
BLUE = (102, 151, 237)


def load(n):
    a = np.array(Image.open(D + f"{n}.png").convert("RGB")).astype(int); H, W, _ = a.shape
    y0, y1 = (48, 940) if H > 1000 else (48, 935); x0, x1 = 8, W - 75
    near = lambda c, t: np.abs(a - np.array(c)).sum(-1) <= t
    cand = near((255, 4, 4), 90) | near((53, 206, 53), 90); blue = near(BLUE, 60)
    for m in (cand, blue): m[:y0] = False; m[y1:] = False; m[:, :x0] = False; m[:, x1:] = False
    hi = np.full(W, np.nan); lo = hi.copy()
    for x in range(W):
        ys = np.flatnonzero(cand[:, x])
        if len(ys): hi[x], lo[x] = ys.min(), ys.max()
    return hi, lo, blue


def lines(blue, k=2, seed=0):
    ys, xs = np.nonzero(blue); pts = np.c_[xs, ys].astype(float); rng = np.random.default_rng(seed); out = []
    for _ in range(k):
        if len(pts) < 40: break
        best = None
        for _ in range(600):
            i, j = rng.integers(0, len(pts), 2); p, q = pts[i], pts[j]
            if abs(p[0] - q[0]) < 30: continue
            m = (q[1] - p[1]) / (q[0] - p[0]); d = np.abs(pts[:, 1] - (p[1] + m * (pts[:, 0] - p[0]))) / np.sqrt(1 + m * m); inl = d <= 2.0
            if best is None or inl.sum() > best[0].sum(): best = (inl, m)
        inl, m = best
        if inl.sum() < 40: break
        pp = pts[inl]; c = np.polyfit(pp[:, 0], pp[:, 1], 1); out.append(dict(x0=float(pp[:, 0].min()), x1=float(pp[:, 0].max()), slope=float(c[0]), icpt=float(c[1]), n=int(inl.sum()))); pts = pts[~inl]
    return out


def metrics(hi, lo, L):
    x0, x1 = int(L["x0"]), int(L["x1"]); sl = L["slope"]; up = sl < 0                         # y crece hacia abajo: pendiente de píxeles negativa = línea sube
    h = Z._fill(hi); l = Z._fill(lo); atr = float(np.nanmean(lo[x0:x1 + 1] - hi[x0:x1 + 1]))
    xs = np.arange(x0, x1 + 1); y = L["icpt"] + sl * xs
    ext = abs(L["icpt"] + sl * x1 - (L["icpt"] + sl * x0))
    price_side = l[x0:x1 + 1] if up else h[x0:x1 + 1]                                          # soporte: mínimos (y máx), resistencia: máximos (y mín)
    dist = (y - price_side) if up else (price_side - y)                                        # >0 = precio del lado correcto
    dist = np.where(up, price_side - y, y - price_side) if False else (price_side - y if up else y - price_side)
    # lado correcto: soporte → precio (low) por ENCIMA de la línea → y_low < y_line  → y_line - y_low > 0 ; resistencia → y_high > y_line → y_high - y_line > 0
    good_side = (y - price_side) if up else (price_side - y)
    cross = float(np.mean(good_side < -0.2 * atr))
    return dict(len=x1 - x0, extent_px=round(ext, 1), extent_atr=round(ext / atr, 1), slope_atr_per_bar=round(abs(sl) * 1.0 / atr, 4), atr_px=round(atr, 1), mean_dist_atr=round(float(np.mean(np.abs(good_side))) / atr, 2),
                max_dist_atr=round(float(np.max(good_side)) / atr, 2), cross_frac=round(cross, 3), dir="up" if up else "down")


if __name__ == "__main__":
    out = {}
    for n in range(22, 32):
        if n == 31: continue                                                     # igual a 30
        hi, lo, blue = load(n); Ls = lines(blue, 2)
        out[n] = [dict(L, **metrics(hi, lo, L)) for L in Ls]
        for L in out[n]: print(n, {k: L[k] for k in ("x0", "x1", "len", "dir", "extent_atr", "slope_atr_per_bar", "mean_dist_atr", "max_dist_atr", "cross_frac", "atr_px")})
    json.dump(out, open("docs/research/ema_trend/feedback_lines.json", "w"), indent=1)
