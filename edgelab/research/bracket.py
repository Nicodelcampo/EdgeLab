"""Bracket bilateral tick a tick (compra stop arriba, venta stop abajo; SL/TP desde la entrada; salida por tiempo o fin de sesión).

Movido de `tools/vtd_bracket_stage1.py::sim` (2026-10-25) para reutilizarlo en kernels sin los efectos de importar ese script; el script
lo importa de acá. Lógica sin cambios. Entra al precio del primer tick que cruza el nivel (con el hueco real) más `slip`.
"""
from __future__ import annotations

from edgelab.research.areas_expansion import njit


@njit(cache=False)
def sim(px, tick_bar, bar_last_tick, sess_last_tick, i0, bar0, up, dn, sl, tp, slip, entry_bars, hold_bars):
    """Bracket: buy stop >= up / sell stop <= dn desde el tick i0; SL/TP desde el precio de entrada; salida por tiempo.
    Devuelve (entró, dir, pnl_ticks, motivo) con motivo 0 = sin entrada, 1 = SL, 2 = TP, 3 = tiempo/sesión."""
    n = len(px)
    lim_entry = min(bar_last_tick[min(bar0 + entry_bars, len(bar_last_tick) - 1)], sess_last_tick)
    t = i0
    d = 0
    entry = 0.0
    while t <= lim_entry and t < n:
        p = px[t]
        if p >= up:
            d = 1
            entry = p + slip
            break
        if p <= dn:
            d = -1
            entry = p - slip
            break
        t += 1
    if d == 0:
        return 0, 0, 0.0, 0
    eb = tick_bar[t]
    lim_exit = min(bar_last_tick[min(eb + hold_bars, len(bar_last_tick) - 1)], sess_last_tick)
    t += 1
    while t <= lim_exit and t < n:
        p = px[t]
        if d == 1:
            if p <= entry - sl:
                return 1, d, (p - slip) - entry, 1
            if p >= entry + tp:
                return 1, d, tp, 2
        else:
            if p >= entry + sl:
                return 1, d, entry - (p + slip), 1
            if p <= entry - tp:
                return 1, d, tp, 2
        t += 1
    tt = min(lim_exit, n - 1)
    pe = px[tt] - slip * d
    return 1, d, (pe - entry) * d, 3
