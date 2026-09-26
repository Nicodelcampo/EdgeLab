# -*- coding: utf-8 -*-
"""Predictores mock — deterministas, sin dependencias, para testear el pipeline.

Dos, y el segundo importa tanto como el primero:

  `MockPredictor`      causal y determinista. Sirve para verificar que el
                       pipeline funciona.
  `LeakyMockPredictor` **mira el futuro a propósito**. Sirve para verificar que
                       el detector lo atrapa.

Sin el segundo, `causality.py` sería un test que nunca se vio fallar — o sea,
decoración. La misma lógica que llevó a inyectar la regresión ULP en
`test_ulp_sweep.py`.
"""
from __future__ import annotations

import math

from .contract import ModelIdentity, PredictionRecord, Predictor

_PESOS_FALSOS = "0" * 64   # placeholder explícito: NO son pesos reales


def identidad_mock(name="Mock", n_paths=1, horizon_bars=12, lookback_bars=64,
                   **kw):
    return ModelIdentity(
        name=name, revision="mock", weights_sha256=_PESOS_FALSOS,
        context_bars=512, lookback_bars=lookback_bars,
        horizon_bars=horizon_bars, n_paths=n_paths, seed=0,
        bar_spec=kw.pop("bar_spec", "time:5"), extra=kw)


class MockPredictor(Predictor):
    """Determinista y causal: sólo usa `bars[:i+1]`.

    `p_up` sale de la pendiente de las últimas `lookback` barras y `sigma_pred`
    del desvío de sus retornos. No pretende predecir nada — pretende tener la
    misma FORMA que Kronos (mismas tres columnas, mismos dos timestamps) para
    que todo lo de alrededor se pueda testear sin GPU.
    """

    def __init__(self, identity=None, latency_ns=0, bar_ns=300 * 10**9):
        self.identity = identity or identidad_mock()
        self.latency_ns = int(latency_ns)
        self.bar_ns = int(bar_ns)

    def predict_at(self, bars, i):
        lb = min(self.identity.lookback_bars, i + 1)
        vent = bars[i - lb + 1: i + 1]
        cierres = [float(b["close"]) for b in vent]
        rets = [cierres[k + 1] / cierres[k] - 1.0
                for k in range(len(cierres) - 1) if cierres[k]]
        if rets:
            mu = sum(rets) / len(rets)
            var = sum((r - mu) ** 2 for r in rets) / max(1, len(rets) - 1)
            sigma = math.sqrt(var)
            p_up = 1.0 / (1.0 + math.exp(-mu / (sigma + 1e-12)))
        else:
            mu, sigma, p_up = 0.0, 0.0, 0.5
        gen = int(bars[i]["ts_ns"])
        return [PredictionRecord(
            model_id=self.identity.model_id,
            generated_at_ns=gen,
            target_ts_ns=gen + self.identity.horizon_bars * self.bar_ns,
            available_at_ns=gen + self.latency_ns,
            values=dict(p_up=round(p_up, 10), sigma_pred=round(sigma, 12),
                        spread_q90_q10=round(sigma * 2.563, 12)))]

    def cost_estimate_s(self):
        return 0.0005


class LeakyMockPredictor(MockPredictor):
    """**Mira el futuro a propósito.** Existe para que el detector se pruebe.

    Reproduce el bug real, no una caricatura: en vez de mirar `bars[:i+1]`, mira
    `bars[i + horizon]`. Es lo que pasa cuando se corre `predict()` sobre la serie
    completa y se une por el índice que devuelve el modelo, que es `target_ts`.
    """

    def predict_at(self, bars, i):
        j = min(i + self.identity.horizon_bars, len(bars) - 1)
        futuro = float(bars[j]["close"])
        ahora = float(bars[i]["close"])
        gen = int(bars[i]["ts_ns"])
        return [PredictionRecord(
            model_id=self.identity.model_id,
            generated_at_ns=gen,
            target_ts_ns=gen + self.identity.horizon_bars * self.bar_ns,
            available_at_ns=gen + self.latency_ns,
            values=dict(p_up=1.0 if futuro > ahora else 0.0,   # <- el futuro
                        sigma_pred=abs(futuro / ahora - 1.0),
                        spread_q90_q10=0.0))]


def barras_sinteticas(n=600, start_ns=1_780_000_000_000_000_000,
                      bar_ns=300 * 10**9, seed=7, p0=20000.0):
    """Serie OHLCV determinista para tests. Random walk con LCG propio."""
    x = seed & 0xFFFFFFFF
    out, p = [], p0
    for k in range(n):
        x = (1103515245 * x + 12345) & 0x7FFFFFFF
        p *= 1.0 + ((x % 2001) - 1000) / 1e6
        o = p * (1.0 + ((x % 7) - 3) / 1e5)
        out.append(dict(ts_ns=start_ns + k * bar_ns, open=o, high=max(o, p) * 1.0001,
                        low=min(o, p) * 0.9999, close=p, volume=100 + x % 900))
    return out
