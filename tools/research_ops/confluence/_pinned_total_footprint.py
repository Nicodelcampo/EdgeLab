"""AVZP2 NT8 total-footprint CSR, copied from foundation f397a318.

This is NOT the aggressive footprint for BigTrap2. Original tie assignment and
OHLC clipping preserved; source uses numpy. Copy normalized from MCP UTF-8.
No loader or authorization. Validate range/overflow/budget externally before a
large run; preserving a function does not certify its market inputs.
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np

@dataclass
class TotalFootprintCSR:
    """Footprint TOTAL por barra en formato CSR (volumen por tick de precio), vectorizado con numpy.
    `bar_cells(b)` -> (ticks, vols) de la barra b, ordenados por tick. Mismo contenido que `Footprints.total[b]`
    construido con `build_footprints(..., nt8_subseries=True)` (ya filtrado al [low, high] de la barra), sin dicts:
    decenas de veces más rápido y una fracción de la memoria en contratos de >100 M ticks."""
    offsets: np.ndarray    # int64, len n_bars + 1
    ticks: np.ndarray      # int64
    vols: np.ndarray       # float64

    def bar_cells(self, b):
        a, z = self.offsets[b], self.offsets[b + 1]
        return self.ticks[a:z], self.vols[a:z]

def build_total_footprint_csr_nt8(ticks: TickSeries, bars: BarSeries) -> TotalFootprintCSR:
    """Regla NT8 de subserie 1-tick (idéntica a build_footprints(nt8_subseries=True)): tick con timestamp igual al
    cierre de una barra → barra siguiente; ráfaga de barras con el mismo cierre → intercalado P,S,P,S; fuera de
    [low, high] de la barra asignada → descartado."""
    ends = np.asarray(bars.end_ns, dtype=np.int64)
    ts = np.asarray(ticks.ts_ns, dtype=np.int64)
    nb = len(ends)
    assign = np.searchsorted(ends, ts, side="right")
    L = np.searchsorted(ends, ts, side="left")
    multi = np.flatnonzero((assign - L) > 1)
    if len(multi):                                   # rank del tick dentro de su timestamp (ticks ya ordenados por ts)
        tm = ts[multi]
        first = np.r_[True, tm[1:] != tm[:-1]]
        grp_start = np.maximum.accumulate(np.where(first, np.arange(len(tm)), 0))
        j = np.arange(len(tm)) - grp_start
        lim = assign[multi] - L[multi] - 1
        use = j < lim
        assign[multi[use]] = L[multi[use]] + 1 + j[use]
    ok = assign < nb
    b = assign[ok]
    p = np.asarray(ticks.price_ticks, dtype=np.int64)[ok]
    v = np.asarray(ticks.volume, dtype=np.float64)[ok]
    inr = (p >= np.asarray(bars.low_t, dtype=np.int64)[b]) & (p <= np.asarray(bars.high_t, dtype=np.int64)[b])
    b, p, v = b[inr], p[inr], v[inr]
    pmin = int(p.min()) if len(p) else 0
    key = b * (int(p.max()) - pmin + 1 if len(p) else 1) + (p - pmin)
    uk, inv = np.unique(key, return_inverse=True)
    vol = np.bincount(inv, weights=v)
    width = (int(p.max()) - pmin + 1) if len(p) else 1
    ub = uk // width
    ut = uk % width + pmin
    offsets = np.zeros(nb + 1, dtype=np.int64)
    np.add.at(offsets, ub + 1, 1)
    return TotalFootprintCSR(np.cumsum(offsets), ut.astype(np.int64), vol)
