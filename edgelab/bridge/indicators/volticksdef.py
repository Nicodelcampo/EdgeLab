# -*- coding: utf-8 -*-
"""VolTicksDef — espejo de nt8/VolTicksDef.cs (Calculate = OnBarClose).

Marca la barra cuando ratio = Volume[0] / media(Volume, AvgPeriod barras, incluida la actual) >= umbral, con umbral =
cuantil P² (Jain & Chlamtac) de los ratios: el de la sesión si ResetThresholdEachSession y ya tiene
>= max(5, MinSessionSamples) muestras; si no, el global. La "zona" es el rango [Low, High] de la barra marcada.

Detalles que se replican a propósito (paridad):
- arranca en CurrentBar >= max(5, AvgPeriod); el reseteo de sesión sólo ocurre desde ahí;
- suma móvil secuencial (sum += V[0] − V[AvgPeriod]) en double; la primera suma recorre V[0..AvgPeriod−1];
- P²: se alimenta primero el global y después el de sesión; Value = h[2] (NaN hasta 5 muestras).
"""
from __future__ import annotations

import math

import numpy as np

NAME, VERSION = "VolTicksDef", "log1"
DEFAULTS = dict(avg_period=200, detection_percentile=99.75, reset_threshold_each_session=True, min_session_samples=30)


class P2Quantile:
    def __init__(self, quantile):
        self.q = max(0.0001, min(0.9999, quantile))
        q = self.q
        self.dn = [0.0, q / 2.0, q, (1.0 + q) / 2.0, 1.0]
        self.reset()

    def reset(self):
        self.init = []
        self.initialized = False
        self.count = 0
        self.h = [0.0] * 5
        self.n = [0.0] * 5
        self.np_ = [0.0] * 5

    def add(self, x):
        h, n, npp = self.h, self.n, self.np_
        if not self.initialized:
            self.init.append(x)
            self.count += 1
            if len(self.init) == 5:
                self.init.sort()
                for i in range(5):
                    h[i] = self.init[i]
                    n[i] = float(i + 1)
                q = self.q
                npp[0] = 1.0; npp[1] = 1 + 2 * q; npp[2] = 1 + 4 * q; npp[3] = 3 + 2 * q; npp[4] = 5.0
                self.initialized = True
            return
        self.count += 1
        if x < h[0]:
            h[0] = x; k = 0
        elif x < h[1]:
            k = 0
        elif x < h[2]:
            k = 1
        elif x < h[3]:
            k = 2
        elif x <= h[4]:
            k = 3
        else:
            h[4] = x; k = 3
        for i in range(k + 1, 5):
            n[i] += 1
        for i in range(5):
            npp[i] += self.dn[i]
        for i in (1, 2, 3):
            d = npp[i] - n[i]
            if (d >= 1 and (n[i + 1] - n[i]) > 1) or (d <= -1 and (n[i - 1] - n[i]) < -1):
                s = 1 if d > 0 else (-1 if d < 0 else 0)
                hp = self._parabolic(i, s)
                if h[i - 1] < hp < h[i + 1]:
                    h[i] = hp
                else:
                    h[i] = self._linear(i, s)
                n[i] += s

    def _parabolic(self, i, d):
        n, h = self.n, self.h
        n0, n1, n2 = n[i - 1], n[i], n[i + 1]
        h0, h1, h2 = h[i - 1], h[i], h[i + 1]
        a = (n1 - n0 + d) * (h2 - h1) / (n2 - n1)
        b = (n2 - n1 - d) * (h1 - h0) / (n1 - n0)
        return h1 + (d / (n2 - n0)) * (a + b)

    def _linear(self, i, d):
        return self.h[i] + d * (self.h[i + d] - self.h[i]) / (self.n[i + d] - self.n[i])

    @property
    def ready(self):
        return self.initialized

    @property
    def value(self):
        return self.h[2] if self.initialized else math.nan


def run(bars, params=None, first_bar_of_session=None):
    """Devuelve dict(rows=[...] una por barra evaluada, zones=[...] barras marcadas). `first_bar_of_session`: array bool
    por barra (Bars.IsFirstBarOfSession); por defecto, cambio de sesión CME entre barras consecutivas."""
    p = {**DEFAULTS, **(params or {})}
    P = int(p["avg_period"])
    vol = np.asarray(bars.volume, dtype=np.float64)
    hi, lo = np.asarray(bars.high_t), np.asarray(bars.low_t)
    nb = len(vol)
    if first_bar_of_session is None:
        from edgelab.bridge.bars import session_ids
        sid = session_ids(np.asarray(bars.start_ns, dtype=np.int64))
        first_bar_of_session = np.r_[True, sid[1:] != sid[:-1]]
    qg = P2Quantile(p["detection_percentile"] / 100.0)
    qs = P2Quantile(p["detection_percentile"] / 100.0)
    rsum, rper = 0.0, 0
    rows, zones = [], []
    start = max(5, P)
    for b in range(start, nb):
        if p["reset_threshold_each_session"] and first_bar_of_session[b]:
            qs.reset()
        if rper != P:
            rsum = 0.0
            for i in range(min(b + 1, P)):
                rsum += vol[b - i]
            rper = P
        else:
            rsum += vol[b]
            rsum -= vol[b - P]
        avg = rsum / P
        if avg <= 0:
            continue
        ratio = vol[b] / avg
        qg.add(ratio)
        qs.add(ratio)
        if p["reset_threshold_each_session"] and qs.ready and qs.count >= max(5, int(p["min_session_samples"])):
            thr = qs.value
        elif qg.ready:
            thr = qg.value
        else:
            thr = math.nan
        flagged = bool(thr > 0 and ratio >= thr)
        rows.append((b, bool(first_bar_of_session[b]), vol[b], avg, ratio, qs.value, qs.count, qg.value, qg.count, thr, flagged))
        if flagged:
            zones.append(dict(bar=b, end_ns=int(bars.end_ns[b]), ratio=ratio, threshold=thr,
                              high_tick=int(hi[b]), low_tick=int(lo[b]), volume=float(vol[b]), avg=avg))
    return dict(indicator=NAME, version=VERSION, params=p, rows=rows, zones=zones)
