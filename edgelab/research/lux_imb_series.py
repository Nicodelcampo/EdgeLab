"""LUX-IMB (OG + VI) sobre una SERIE de barras, vectorizado, con el ciclo de vida del export de NT8.

Reconstruccion en Python del indicador `ImbalanceDetectorLuxAlgoMTF` (FVG apagado). **Target-free**: no mide retornos.
La deteccion por par de barras vive en `lux_imb.py` (referencia escalar); esta version hace lo mismo sobre arrays y
los tests las atan entre si. Contra el export real de 6E (`tools/verify_lux_imb_vs_6e_oracle.py`) reproduce:
familia, direccion, barra de origen, bordes, vencimiento, nivel de relleno y bandera de toque.

Semantica (`SEMANTICS_ID`):
- Cada par de barras CONSECUTIVAS de la lista (sin mirar huecos de tiempo). `t0` = tiempo de la barra previa; la zona
  esta disponible al cierre de la barra actual (`i_prev + 1`).
- OG alcista: low[i] > high[i-1]; bajista: high[i] < low[i-1]. Bordes segun `og_geometry` (`body` = `.cs` literal).
- VI: las desigualdades del `.cs` (ver `lux_imb.detect_volume_imbalances`).
- Vencimiento: `i_prev + 1 + extend_bars` (500). Si cae despues del final de los datos se proyecta con `bar_seconds`.
- `fill_level`: borde hacia la barra previa (alcista -> bottom, bajista -> top).
- `touched`: alguna barra en `[i_prev+2, i_prev+extend_bars]` CRUZA estrictamente el nivel (alcista: low < fill;
  bajista: high > fill). La barra de origen y la actual no cuentan.
Sin filtro de ancho (el export por defecto de NT8 no lo usa). Sin FVG.
"""
from __future__ import annotations

import numpy as np

SEMANTICS_ID = "lux_og_vi_series_v1"
OG, VI = 0, 1


def detect_series(o, h, l, c, *, og_geometry: str = "body", show_og: bool = True, show_vi: bool = True) -> dict:
    """Zonas OG/VI de la serie. Devuelve arrays paralelos ordenados por (i_prev, familia, direccion)."""
    if og_geometry not in ("wick", "body"):
        raise ValueError("og_geometry debe ser 'wick' o 'body'")
    o, h, l, c = (np.asarray(x, dtype=float) for x in (o, h, l, c))
    n = len(o)
    if not (len(h) == len(l) == len(c) == n):
        raise ValueError("arrays de distinto largo")
    po, ph, pl, pc = o[:-1], h[:-1], l[:-1], c[:-1]
    co, ch, cl, cc = o[1:], h[1:], l[1:], c[1:]
    p_bl, p_bh = np.minimum(po, pc), np.maximum(po, pc)     # cuerpo previo
    c_bl, c_bh = np.minimum(co, cc), np.maximum(co, cc)     # cuerpo actual
    out = []

    def add(mask, fam, direction, top, bottom):
        idx = np.nonzero(mask)[0]
        if len(idx):
            out.append((idx, np.full(len(idx), fam), np.full(len(idx), direction), top[idx], bottom[idx]))

    if show_og:
        bull, bear = cl > ph, ch < pl
        if og_geometry == "wick":
            add(bull, OG, 1, cl, ph); add(bear, OG, -1, pl, ch)
        else:
            add(bull, OG, 1, c_bl, p_bh); add(bear, OG, -1, p_bl, c_bh)
    if show_vi:
        vb = (co > pc) & (ph > cl) & (cc > pc) & (co > po) & (ph < c_bl)
        vs = (co < pc) & (pl < ch) & (cc < pc) & (co < po) & (pl > c_bh)
        add(vb, VI, 1, c_bl, p_bh); add(vs, VI, -1, p_bl, c_bh)
    if not out:
        e = np.array([], dtype=float)
        return dict(i_prev=e.astype(int), family=e.astype(int), direction=e.astype(int), top=e, bottom=e)
    i_prev, fam, dr, top, bot = (np.concatenate(x) for x in zip(*out))
    order = np.lexsort((dr, fam, i_prev))
    return dict(i_prev=i_prev[order].astype(int), family=fam[order].astype(int), direction=dr[order].astype(int),
                top=top[order], bottom=bot[order])


def lifecycle(z: dict, times, h, l, *, extend_bars: int = 500, bar_seconds: int = 60) -> dict:
    """Vencimiento, nivel de relleno y bandera de toque de cada zona (ver docstring del modulo)."""
    times = np.asarray(times, dtype=np.int64)
    h, l = np.asarray(h, dtype=float), np.asarray(l, dtype=float)
    n = len(times)
    i_prev, direction = z["i_prev"], z["direction"]
    end_idx = i_prev + 1 + extend_bars
    t1 = np.where(end_idx < n, times[np.minimum(end_idx, n - 1)], times[-1] + (end_idx - (n - 1)) * bar_seconds)
    fill = np.where(direction > 0, z["bottom"], z["top"])
    touched = np.zeros(len(i_prev), dtype=bool)
    for k in range(len(i_prev)):
        a, b = i_prev[k] + 2, min(n, i_prev[k] + extend_bars + 1)
        if a >= b:
            continue
        touched[k] = (l[a:b].min() < fill[k]) if direction[k] > 0 else (h[a:b].max() > fill[k])
    return dict(t0=times[i_prev], t1=t1.astype(np.int64), fill_level=fill, touched=touched)
