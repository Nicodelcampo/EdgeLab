"""Motor de ejecucion tick COMPARTIDO de EdgeLab — se escribe UNA vez, se
verifica con la bateria anti-bugs, y NINGUNA estrategia reimplementa fills,
PnL ni exits. Esto elimina por construccion las clases de bug que mataron
edges anteriores (signo invertido EXP-043, fill al last sin spread, lookahead
de la decision EXP-041):

  - La estrategia entrega SOLO (indices_de_decision, direcciones). El indice
    es el ULTIMO tick de informacion usada; el motor entra en el tick
    SIGUIENTE (causalidad forzada por el motor, no por disciplina del autor).
  - Entrada: LONG paga el ASK, SHORT vende el BID (spread real, siempre).
  - TP (limit): se acredita al precio del limit SOLO si el last opera A TRAVES
    (>= tp+1 tick long / <= tp-1 tick short) — sin suerte de cola.
  - SL (stop-market): dispara por LAST (asi disparan los stops en CME); fill
    al bid/ask de ese tick, nunca mejor que el nivel del stop.
  - Timeout: fill al bid (long) / ask (short) del ultimo tick de la ventana.
  - PnL SIEMPRE = dir * (exit - entry) / tick - fees. Una sola formula, un
    solo lugar.

Convencion de `reason`: 0=tp, 1=sl, 2=timeout.
"""
import numpy as np
import pandas as pd
from numba import njit

FEES_RT = 0.5   # ticks round-trip (exchange+broker), el spread ya lo paga el fill


@njit(cache=True)
def _run(sig_i, sig_d, times_ms, last, bid, ask, tp_t, sl_t, max_hold_ms, tick, fees):
    n = len(last); ns = len(sig_i)
    entry_i = np.full(ns, -1, np.int64)
    entry_px = np.full(ns, np.nan)
    exit_i = np.full(ns, -1, np.int64)
    exit_px = np.full(ns, np.nan)
    pnl = np.full(ns, np.nan)
    reason = np.full(ns, -1, np.int8)
    tp_px_o = np.full(ns, np.nan)
    sl_px_o = np.full(ns, np.nan)
    for k in range(ns):
        k0 = sig_i[k] + 1                 # causalidad: entra al tick SIGUIENTE
        d = sig_d[k]
        if k0 >= n - 1:
            continue
        epx = ask[k0] if d == 1 else bid[k0]
        tp_px = epx + d * tp_t * tick
        sl_px = epx - d * sl_t * tick
        t_end = times_ms[k0] + max_hold_ms
        ei = -1; xpx = np.nan; rs = np.int8(2)
        j = k0 + 1
        while j < n and times_ms[j] <= t_end:
            lp = last[j]
            if d == 1:
                if lp <= sl_px:
                    ei = j; xpx = min(bid[j], sl_px); rs = np.int8(1); break
                if lp >= tp_px + tick:
                    ei = j; xpx = tp_px; rs = np.int8(0); break
            else:
                if lp >= sl_px:
                    ei = j; xpx = max(ask[j], sl_px); rs = np.int8(1); break
                if lp <= tp_px - tick:
                    ei = j; xpx = tp_px; rs = np.int8(0); break
            j += 1
        if ei < 0:
            ei = min(j, n - 1) - 1 if min(j, n - 1) - 1 > k0 else k0 + 1
            if ei >= n:
                continue
            xpx = bid[ei] if d == 1 else ask[ei]
            rs = np.int8(2)
        entry_i[k] = k0; entry_px[k] = epx
        exit_i[k] = ei; exit_px[k] = xpx
        pnl[k] = d * (xpx - epx) / tick - fees
        reason[k] = rs
        tp_px_o[k] = tp_px; sl_px_o[k] = sl_px
    return entry_i, entry_px, exit_i, exit_px, pnl, reason, tp_px_o, sl_px_o


def run_ledger(sig_i, sig_d, times_ms, last, bid, ask, tp_t, sl_t,
               max_hold_ms=300_000, tick=0.25, fees=FEES_RT):
    """Ejecuta las señales y devuelve el LEDGER completo (DataFrame estandar)."""
    e_i, e_px, x_i, x_px, pnl, rs, tp_px, sl_px = _run(
        np.asarray(sig_i, np.int64), np.asarray(sig_d, np.int64),
        times_ms, last, bid, ask, float(tp_t), float(sl_t),
        max_hold_ms, tick, fees)
    ok = e_i >= 0
    reason_map = np.array(["tp", "sl", "time"])
    return pd.DataFrame({
        "dir": np.asarray(sig_d)[ok], "entry_i": e_i[ok], "entry_px": e_px[ok],
        "entry_t": times_ms[e_i[ok]], "exit_i": x_i[ok], "exit_px": x_px[ok],
        "pnl_ticks": pnl[ok], "reason": reason_map[rs[ok]],
        "tp_px": tp_px[ok], "sl_px": sl_px[ok]})


def run_grid(sig_i, sig_d, times_ms, last, bid, ask, tp_grid, sl_grid,
             max_hold_ms=300_000, tick=0.25, fees=FEES_RT):
    """PnL neto (ns, ntp, nsl) para el grid — mismas señales, mismo motor."""
    ns = len(sig_i)
    out = np.full((ns, len(tp_grid), len(sl_grid)), np.nan)
    for a, tp in enumerate(tp_grid):
        for s, sl in enumerate(sl_grid):
            e_i, _, _, _, pnl, _, _, _ = _run(
                np.asarray(sig_i, np.int64), np.asarray(sig_d, np.int64),
                times_ms, last, bid, ask, float(tp), float(sl),
                max_hold_ms, tick, fees)
            out[:, a, s] = pnl
    return out
