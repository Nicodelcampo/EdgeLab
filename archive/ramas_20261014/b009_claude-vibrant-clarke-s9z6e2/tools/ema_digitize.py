#!/usr/bin/env python3
"""Digitaliza capturas de NinjaTrader (velas rojo/verde, EMA naranja, línea azul del usuario) a series por columna de píxeles.
Salida: docs/research/ema_trend/templates.json (solo geometría de píxeles de las capturas del usuario; sin datos de mercado)."""
import json, sys
from pathlib import Path
import numpy as np
from PIL import Image

IM = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/claude-0/-home-user-EdgeLab/c1d99ed7-90f8-5ca5-8a93-7e5ff1aefe21/images")
NAMES = {15: "down_A", 16: "up_B", 17: "down_C", 18: "down_D"}


def near(a, c, tol): return (np.abs(a.astype(int) - np.array(c)).sum(-1) <= tol)


def digitize(path):
    a = np.array(Image.open(path).convert("RGB")); H, W, _ = a.shape
    red, grn = near(a, (255, 4, 4), 60), near(a, (53, 206, 53), 60); cand = red | grn
    ema = near(a, (219, 166, 35), 90) | near(a, (236, 210, 145), 40); blue = near(a, (102, 151, 237), 60)
    hi = np.full(W, np.nan); lo = np.full(W, np.nan); em = np.full(W, np.nan)
    for x in range(W):
        ys = np.flatnonzero(cand[:, x])
        if len(ys): hi[x], lo[x] = ys.min(), ys.max()
        ye = np.flatnonzero(ema[:, x])
        if len(ye): em[x] = ye.mean()
    bx = np.flatnonzero(blue.any(0)); out = dict(width=W, height=H, hi=hi.tolist(), lo=lo.tolist(), ema=em.tolist())
    if len(bx):
        x0, x1 = int(bx.min()), int(bx.max()); y0 = float(np.flatnonzero(blue[:, x0]).mean()); y1 = float(np.flatnonzero(blue[:, x1]).mean()); out["blue"] = dict(x0=x0, x1=x1, y0=y0, y1=y1)
    # píxeles por barra: separación mediana entre columnas con vela (cada vela ocupa ~ w px; el paso entre velas = distancia entre inicios de racha de columnas con vela)
    has = ~np.isnan(hi); starts = np.flatnonzero(has[1:] & ~has[:-1]) + 1
    out["candle_starts"] = int(len(starts)); out["cols_with_candle"] = int(has.sum())
    return out


if __name__ == "__main__":
    res = {NAMES[n]: digitize(IM / f"{n}.png") for n in NAMES}
    Path("docs/research/ema_trend/templates.json").write_text(json.dumps(res))
    for k, v in res.items(): print(k, v["width"], v["height"], "blue", v.get("blue"), "ema_cols", int(np.sum(~np.isnan(v["ema"]))), "candle_cols", v["cols_with_candle"], "starts", v["candle_starts"])
