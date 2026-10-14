"""Escaneo por (fecha cruda, hora cruda): conteos, volumen, rangos de sello y calidad de grilla/quotes.

Es la evidencia base para (a) verificar el huso por ajuste al calendario CME, (b) censar cobertura por sesión, (c) medir
volumen y spread de D-1 para la selección causal. No calcula retornos ni precios agregados.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from edgelab.data.liquid_release.nt8_text import iter_decoded

N_SPREAD = 34        # bin 0 = locked (spread 0 ticks), 1..32 = ticks, 33 = >=33 ticks
GRID_TOL = 1e-6
_SUM_KEYS = ("n", "vol", "n_vol_le0", "off_last", "off_bid", "off_ask", "noquote", "crossed", "locked",
             "last_gt_ask", "last_lt_bid")


class HourlyAccumulator:
    def __init__(self, tick_size: float):
        self.tick = float(tick_size)
        self.rows = {}
        self.nonmono = 0
        self.prev_ts = None
        self.dup_consecutive = 0
        self.prev_row = None
        self.min_ts = None
        self.max_ts = None

    def add(self, b: dict):
        n = len(b["date"])
        if n == 0:
            return
        ts, last, bid, ask, vol = b["ts_raw_ns"], b["last"], b["bid"], b["ask"], b["vol"]
        # monotonía y duplicados exactos consecutivos (informativo: timestamps iguales NO son duplicación)
        dts = np.diff(ts)
        self.nonmono += int((dts < 0).sum())
        if self.prev_ts is not None and ts[0] < self.prev_ts:
            self.nonmono += 1
        same = ((dts == 0) & (last[1:] == last[:-1]) & (bid[1:] == bid[:-1]) & (ask[1:] == ask[:-1])
                & (vol[1:] == vol[:-1]))
        self.dup_consecutive += int(same.sum())
        if self.prev_row is not None and (ts[0], last[0], bid[0], ask[0], vol[0]) == self.prev_row:
            self.dup_consecutive += 1
        self.prev_ts = ts[-1]
        self.prev_row = (ts[-1], last[-1], bid[-1], ask[-1], vol[-1])
        self.min_ts = ts.min() if self.min_ts is None else min(self.min_ts, ts.min())
        self.max_ts = ts.max() if self.max_ts is None else max(self.max_ts, ts.max())
        tk = self.tick
        gl, gb, ga = last / tk, bid / tk, ask / tk
        off_last = np.abs(gl - np.rint(gl)) > GRID_TOL
        off_bid = (np.abs(gb - np.rint(gb)) > GRID_TOL) & (bid > 0)
        off_ask = (np.abs(ga - np.rint(ga)) > GRID_TOL) & (ask > 0)
        noquote = ~((bid > 0) & (ask > 0))
        crossed = (~noquote) & (ask < bid)
        sp = np.rint((ask - bid) / tk)
        locked = (~noquote) & (sp == 0) & ~crossed
        has_sp = (~noquote) & (~crossed)
        sbin = np.clip(np.where(has_sp, sp, 0), 0, N_SPREAD - 1).astype(np.int64)
        key = b["date"].astype(np.int64) * 24 + b["hour"]
        uk, first, inv = np.unique(key, return_index=True, return_inverse=True)
        m = len(uk)
        rev_first = np.unique(key[::-1], return_index=True)[1]
        last_idx = n - 1 - rev_first
        vf = vol.astype(np.float64)

        def cnt(mask):
            return np.bincount(inv, weights=mask.astype(np.float64), minlength=m).astype(np.int64)

        hist = np.bincount((inv * N_SPREAD + sbin)[has_sp], minlength=m * N_SPREAD).reshape(m, N_SPREAD)
        cols = dict(n=np.bincount(inv, minlength=m).astype(np.int64),
                    vol=np.bincount(inv, weights=vf, minlength=m).astype(np.int64),
                    n_vol_le0=cnt(vol <= 0), off_last=cnt(off_last), off_bid=cnt(off_bid), off_ask=cnt(off_ask),
                    noquote=cnt(noquote), crossed=cnt(crossed), locked=cnt(locked),
                    last_gt_ask=cnt((~noquote) & (last > ask + 1e-12)), last_lt_bid=cnt((~noquote) & (last < bid - 1e-12)),
                    first_ts=ts[first], last_ts=ts[last_idx])
        for i, k in enumerate(uk):
            r = self.rows.get(int(k))
            if r is None:
                self.rows[int(k)] = {**{kk: int(v[i]) for kk, v in cols.items()}, "hist": hist[i].astype(np.int64).copy()}
            else:
                for kk in _SUM_KEYS:
                    r[kk] += int(cols[kk][i])
                r["first_ts"] = min(r["first_ts"], int(cols["first_ts"][i]))
                r["last_ts"] = max(r["last_ts"], int(cols["last_ts"][i]))
                r["hist"] += hist[i]

    def frame(self) -> pd.DataFrame:
        recs = []
        for k, r in sorted(self.rows.items()):
            d = {kk: v for kk, v in r.items() if kk != "hist"}
            d["raw_date"], d["raw_hour"] = k // 24, k % 24
            d["spread_hist"] = r["hist"].tolist()
            recs.append(d)
        return pd.DataFrame(recs)


def scan_file(path, tick_size, *, cutoff_prefix=None, chunk_bytes=64 << 20, compute_sha=True):
    """-> (DataFrame por hora, dict del archivo)."""
    acc = HourlyAccumulator(tick_size)
    it, stats = iter_decoded(path, chunk_bytes=chunk_bytes, cutoff_prefix=cutoff_prefix, compute_sha=compute_sha)
    for b in it:
        acc.add(b)
    info = dict(rows_ok=stats.rows_ok, rows_invalid_shape=stats.rows_invalid_shape, rows_invalid_ts=stats.rows_invalid_ts,
                rows_unparseable=stats.rows_unparseable, bytes_read=stats.bytes_read, sha256=stats.sha256,
                sha256_complete=stats.sha256_complete, truncated_at_cutoff=stats.truncated_at_cutoff,
                nonmonotonic=acc.nonmono, dup_consecutive=acc.dup_consecutive,
                min_ts_raw_ns=None if acc.min_ts is None else int(acc.min_ts),
                max_ts_raw_ns=None if acc.max_ts is None else int(acc.max_ts), invalid_samples=stats.invalid_samples)
    return acc.frame(), info
