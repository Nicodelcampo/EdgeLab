"""EXP-029/030 (Sweep Fade / Impulse Fade en ES tick) portados al CONTRATO de
EdgeLab: acá viven SOLO las funciones de señal. Fills, PnL, exits, causalidad,
preflight y gauntlet los hace el harness con el motor compartido.

Señales (params pre-registrados del ledger EXP-029/030/031, sin re-tunear):
  SWEEP  : >=10 ticks consecutivos misma direccion en <=500ms, movimiento
           >=5t, RTH 13-21 UTC, cooldown 60s. Fade (contra el sweep).
           Headline: tp24/sl8.
  IMPULSE: |mov| >=12t en <=2s, RTH, cooldown 60s. Fade. Headline: tp24/sl3.

Cambios estructurales vs la version del ecosistema viejo (por el motor):
  - entrada al tick SIGUIENTE de la señal, LONG paga ASK / SHORT vende BID
    (la version vieja llenaba al LAST del propio tick de señal, sin spread:
    sospecha principal = bid-ask bounce);
  - fees 0.5t RT (el spread ya lo cobra el fill).
Se corre ademas una DESCOMPOSICION con quotes degeneradas (bid=ask=last,
fees=1t) que replica la convencion vieja, para cuantificar cuanto del "edge"
anterior era el fill regalado.

Ejecutar:  python -m strategies.tickfade
"""
import sys
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from numba import njit

from edgelab.config import ES_TICKS, poison_mask
from edgelab.engine import run_grid, run_ledger
from validation.harness import full_audit

TICK = 0.25
RTH0, RTH1 = 13, 21          # horas UTC (ventana amplia EST/EDT, como EXP-031)
COOLDOWN_MS = 60_000
MAX_HOLD_MS = 300_000
TP_GRID = np.array([4, 6, 8, 12, 16, 24], dtype=np.float64)
SL_GRID = np.array([2, 3, 4, 6, 8], dtype=np.float64)

SWEEP_N = 10; SWEEP_MS = 500
IMP_T = 12; IMP_MS = 2000


@njit(cache=True)
def _sweep_signals(times_ms, last, rth0, rth1, sweep_n, sweep_ms, cooldown_ms):
    n = len(last)
    idx = np.empty(n // 50 + 16, np.int64)
    dirs = np.empty(n // 50 + 16, np.int64)
    m = 0; last_sig = -np.int64(1) << 60
    i = 1
    while i < n - 2:
        h = (times_ms[i] // 3600000) % 24
        if h < rth0 or h >= rth1 or times_ms[i] - last_sig < cooldown_ms:
            i += 1; continue
        d = 0; consec = 1; j = i
        while j < n - 1 and times_ms[j] - times_ms[i] < sweep_ms:
            if last[j] > last[j - 1]:
                if d == -1: break
                d = 1; consec += 1
            elif last[j] < last[j - 1]:
                if d == 1: break
                d = -1; consec += 1
            else:
                consec += 1
            j += 1
        if d != 0 and consec >= sweep_n:
            move_t = abs(last[j - 1] - last[i - 1]) / 0.25
            if move_t >= sweep_n * 0.5:
                idx[m] = j - 1          # ultimo tick de informacion usada
                dirs[m] = -d            # fade
                m += 1
                last_sig = times_ms[j - 1]
                i = j
                continue
        i += 1
    return idx[:m], dirs[:m]


@njit(cache=True)
def _impulse_signals(times_ms, last, rth0, rth1, move_t, window_ms, cooldown_ms):
    n = len(last)
    idx = np.empty(n // 50 + 16, np.int64)
    dirs = np.empty(n // 50 + 16, np.int64)
    m = 0; last_sig = -np.int64(1) << 60; st = 0
    for i in range(1, n - 2):
        t = times_ms[i]
        while t - times_ms[st] > window_ms:
            st += 1
        h = (t // 3600000) % 24
        if h < rth0 or h >= rth1 or t - last_sig < cooldown_ms:
            continue
        dlt = (last[i] - last[st]) / 0.25
        if dlt >= move_t:
            idx[m] = i; dirs[m] = -1; m += 1; last_sig = t
        elif dlt <= -move_t:
            idx[m] = i; dirs[m] = 1; m += 1; last_sig = t
    return idx[:m], dirs[:m]


def sweep_señales(times_ms, last, bid, ask):
    """Señales sweep EXCLUYENDO las ventanas envenenadas de la cinta
    (roll weeks con contratos entrelazados — hallazgo EXP-044)."""
    idx, dirs = _sweep_signals(times_ms, last, RTH0, RTH1, SWEEP_N, SWEEP_MS, COOLDOWN_MS)
    ok = ~poison_mask(times_ms[idx])
    return idx[ok], dirs[ok]


def impulse_señales(times_ms, last, bid, ask):
    idx, dirs = _impulse_signals(times_ms, last, RTH0, RTH1, IMP_T, IMP_MS, COOLDOWN_MS)
    ok = ~poison_mask(times_ms[idx])
    return idx[ok], dirs[ok]


def sweep_señales_raw(times_ms, last, bid, ask):
    """Version SIN excluir veneno — solo para la descomposicion forense."""
    return _sweep_signals(times_ms, last, RTH0, RTH1, SWEEP_N, SWEEP_MS, COOLDOWN_MS)


def impulse_señales_raw(times_ms, last, bid, ask):
    return _impulse_signals(times_ms, last, RTH0, RTH1, IMP_T, IMP_MS, COOLDOWN_MS)


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("Cargando ES_ticks.parquet...")
    tbl = pq.read_table(ES_TICKS, columns=["timestamp", "last", "bid", "ask"])
    times_ms = tbl.column("timestamp").to_numpy(zero_copy_only=False) \
        .astype("datetime64[ms]").astype(np.int64)
    last = tbl.column("last").to_numpy(zero_copy_only=False).astype(np.float64)
    bid = tbl.column("bid").to_numpy(zero_copy_only=False).astype(np.float64)
    ask = tbl.column("ask").to_numpy(zero_copy_only=False).astype(np.float64)
    print(f"{len(last):,} ticks")

    jobs = [("SWEEP FADE (EXP-029)", sweep_señales, sweep_señales_raw, (24.0, 8.0)),
            ("IMPULSE FADE (EXP-030)", impulse_señales, impulse_señales_raw, (24.0, 3.0))]
    for name, fn, fn_raw, headline in jobs:
        res = full_audit(name, fn, times_ms, last, bid, ask,
                         TP_GRID, SL_GRID, headline,
                         max_hold_ms=MAX_HOLD_MS, tick=TICK)

        # ---- FORENSE: replica de la convencion VIEJA (fill al last, sin
        # spread, stop teletransportado al nivel, cost 1t) sobre señales SIN
        # excluir el veneno, partida dentro/fuera de las ventanas de roll ----
        i2, d2 = fn_raw(times_ms, last, bid, ask)
        old = run_grid(i2, d2, times_ms, last, last, last,
                       np.array([headline[0]]), np.array([headline[1]]),
                       max_hold_ms=MAX_HOLD_MS, tick=TICK, fees=1.0)[:, 0, 0]
        floor = -(headline[1] + 1.0)                    # stop teletransportado
        old_tele = np.maximum(old, floor)
        pois = poison_mask(times_ms[np.clip(i2 + 1, 0, len(times_ms) - 1)])
        ok = ~np.isnan(old_tele)
        vin = old_tele[ok & pois]; vout = old_tele[ok & ~pois]
        print(f"\nFORENSE {name} — replica convencion VIEJA (ledger EXP-029/030):")
        print(f"  total          : n={int(ok.sum())} exp={old_tele[ok].mean():+.2f}t")
        print(f"  DENTRO del veneno (roll weeks): n={len(vin)} exp={vin.mean():+.2f}t "
              f"(aporte {vin.sum():+.0f}t)")
        print(f"  FUERA del veneno               : n={len(vout)} exp={vout.mean():+.2f}t "
              f"(aporte {vout.sum():+.0f}t)")


if __name__ == "__main__":
    main()
