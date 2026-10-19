"""Anclas del sector de volumen de EmaCorridorTrendVol (espejo en Python de ComputeAnchors del indicador de NT8).

Definiciones (identicas al .cs; docs/research/EMACORRIDORTRENDVOL_ANCLAS_20261015.md):
  - POC: nivel de precio con mas volumen del sector; en empate, el mas cercano al centro de la banda.
  - Borde del Area de Valor 70 %: desde el POC se suma el par de niveles contiguos (arriba o abajo) con mas volumen hasta cubrir el 70 %
    del total; se devuelve el borde del lado del INTERIOR de la zona (VAL si la zona sube, VAH si baja).
  - Barra de maximo volumen: la barra de mayor volumen entre las del sector; precio = punto medio de su rango (o su cierre).
Sirve para validar el indicador y para la prueba empirica de anclas (que no esta ejecutada).
"""
from __future__ import annotations

import numpy as np


def sector_band(box_lo: float, box_hi: float, direction: int, tail_pct: float = 25.0, beyond_pct: float = 25.0):
    """Banda de precio del sector: ultimo tail_pct % del alto del rectangulo del lado del extremo + beyond_pct % mas alla del extremo."""
    h = box_hi - box_lo
    if direction > 0:
        return box_hi - tail_pct / 100.0 * h, box_hi + beyond_pct / 100.0 * h
    return box_lo - beyond_pct / 100.0 * h, box_lo + tail_pct / 100.0 * h


def sector_anchors(prices, volumes, tick_size, lo, hi, direction, bar_high=None, bar_low=None, bar_close=None, bar_volume=None, use_close=False):
    """prices/volumes: ticks DEL SECTOR (ya filtrados por tiempo). Devuelve dict(total, poc, va_low, va_high, va_edge, hv_bar) o None."""
    prices = np.asarray(prices, float)
    volumes = np.asarray(volumes, float)
    eps = tick_size * 0.01
    m = (prices >= lo - eps) & (prices <= hi + eps)
    prices, volumes = prices[m], volumes[m]
    total = float(volumes.sum())
    if total <= 0:
        return None
    ids = np.rint(prices / tick_size).astype(int)
    mn, mx = ids.min(), ids.max()
    n = mx - mn + 1
    v = np.zeros(n)
    np.add.at(v, ids - mn, volumes)

    mid = 0.5 * (lo + hi)
    poc_i = 0
    for k in range(1, n):
        if v[k] > v[poc_i] or (v[k] == v[poc_i] and abs((mn + k) * tick_size - mid) < abs((mn + poc_i) * tick_size - mid)):
            poc_i = k

    target, acc, a, b = 0.70 * total, v[poc_i], poc_i, poc_i
    while acc < target and (a > 0 or b < n - 1):
        up = (v[b + 1] if b + 1 < n else 0.0) + (v[b + 2] if b + 2 < n else 0.0)
        dn = (v[a - 1] if a - 1 >= 0 else 0.0) + (v[a - 2] if a - 2 >= 0 else 0.0)
        if b < n - 1 and (up >= dn or a == 0):
            acc += up
            b = min(n - 1, b + 2)
        else:
            acc += dn
            a = max(0, a - 2)
    va_low, va_high = (mn + a) * tick_size, (mn + b) * tick_size
    out = dict(total=total, poc=(mn + poc_i) * tick_size, va_low=va_low, va_high=va_high, va_edge=va_low if direction > 0 else va_high, hv_bar=None)
    if bar_volume is not None and len(bar_volume):
        j = int(np.argmax(bar_volume))
        out["hv_bar"] = float(bar_close[j]) if use_close else 0.5 * float(bar_high[j] + bar_low[j])
    return out
