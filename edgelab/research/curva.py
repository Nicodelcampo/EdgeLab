"""Curva de capital en R por tramos (IS / OOS / confirmación / holdout) como SVG, sin matplotlib (no está en el entorno).
AUTOMATIZACION_PROCESOS_20261111 I9: antes cada familia dibujaba la suya (op2_holdout)."""
from __future__ import annotations

import numpy as np

COLORES = {"IS": "#3b6ea8", "OOS": "#d08a2c", "CONFIRMACION": "#7a5cb0", "HOLDOUT": "#2f9e6b"}


def resumen(y) -> dict:
    y = np.asarray(y, float); c = np.cumsum(y)
    return dict(n=int(len(y)), r_medio=float(y.mean()) if len(y) else 0.0, r_total=float(c[-1]) if len(y) else 0.0,
                max_drawdown_r=float((np.maximum.accumulate(np.r_[0, c]) - np.r_[0, c]).max()) if len(y) else 0.0)


def svg(tramos: list, titulo: str, subtitulo: str = "", ancho: int = 980, alto: int = 500) -> tuple:
    """`tramos`: [(nombre, etiqueta de fechas, serie de R por operación en orden)]. Devuelve (svg, {nombre: resumen})."""
    W, Hh, ml, mr, mt, mb = ancho, alto, 70, 20, 64 + 16 * len(tramos), 50
    res, pts, x0, acum = {}, [], 0, 0.0
    for nom, fechas, y in tramos:
        y = np.asarray(y, float); y = y[np.isfinite(y)]
        if not len(y): continue
        r = res[nom] = dict(resumen(y), fechas=fechas); c = acum + np.cumsum(y)
        pts.append((nom, np.r_[x0, np.arange(x0 + 1, x0 + len(y) + 1)], np.r_[acum, c])); x0, acum = x0 + len(y), float(c[-1])
    if not pts: return "", res
    ys = np.concatenate([p[2] for p in pts]); lo, hi = min(0.0, ys.min()), max(0.0, ys.max()); pad = (hi - lo) * 0.08 or 1.0; lo, hi = lo - pad, hi + pad
    X = lambda v: ml + (W - ml - mr) * v / max(x0, 1); Y = lambda v: mt + (Hh - mt - mb) * (hi - v) / (hi - lo)
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{Hh}" viewBox="0 0 {W} {Hh}" font-family="Helvetica,Arial,sans-serif">',
         f'<rect width="{W}" height="{Hh}" fill="#fff"/>', f'<text x="{ml}" y="24" font-size="15" font-weight="bold" fill="#222">{titulo}</text>',
         f'<text x="{ml}" y="42" font-size="11.5" fill="#555">{subtitulo}</text>']
    for k in range(6):
        v = lo + (hi - lo) * k / 5
        o.append(f'<line x1="{ml}" x2="{W - mr}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="#eee"/><text x="{ml - 8}" y="{Y(v) + 4:.1f}" font-size="10.5" fill="#666" text-anchor="end">{v:+.1f} R</text>')
    o.append(f'<line x1="{ml}" x2="{W - mr}" y1="{Y(0):.1f}" y2="{Y(0):.1f}" stroke="#888" stroke-width="0.8"/>')
    for i, (nom, xs, yv) in enumerate(pts):
        col = COLORES.get(nom.upper(), "#555"); r = res[nom]; yy = 64 + 16 * i
        o.append(f'<rect x="{X(xs[0]):.1f}" y="{mt}" width="{X(xs[-1]) - X(xs[0]):.1f}" height="{Hh - mt - mb}" fill="{col}" opacity="0.05"/>')
        o.append('<polyline fill="none" stroke="%s" stroke-width="1.8" points="%s"/>' % (col, " ".join(f"{X(a):.1f},{Y(b):.1f}" for a, b in zip(xs, yv))))
        o.append(f'<rect x="{ml}" y="{yy - 9}" width="14" height="3" fill="{col}"/><text x="{ml + 20}" y="{yy}" font-size="11.5" font-weight="bold" fill="{col}">{nom}</text>')
        o.append(f'<text x="{ml + 120}" y="{yy}" font-size="11" fill="#444">{r["fechas"]} · n {r["n"]} · {r["r_medio"]:+.3f} R/op · total {r["r_total"]:+.1f} R · DD máx {r["max_drawdown_r"]:.1f} R</text>')
    o.append(f'<text x="{(W + ml) / 2:.0f}" y="{Hh - 14}" font-size="11" fill="#666" text-anchor="middle">operación (orden cronológico, {x0} en total)</text></svg>')
    return "\n".join(o), res
