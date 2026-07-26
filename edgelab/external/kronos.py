# -*- coding: utf-8 -*-
"""Adaptador de Kronos (shiyu-coder/Kronos) — **NO instalado, a propósito**.

## Estado: no adoptado

Este módulo es el enchufe, no el modelo. `torch`, `transformers` y los pesos
**no** están en el entorno y no los instalé: `requirements/core-bridge-dev.lock`
declara "sin dependencias pesadas nuevas; sin CUDA", y meter el stack de
PyTorch en el lock es una decisión de infraestructura que le corresponde a Nico.

Que el módulo exista sin el modelo tiene un valor concreto: todo el pipeline
—store point-in-time, detector de causalidad, calculadora de factibilidad,
gates— se testea hoy contra `MockPredictor`, y el día que Kronos entre lo hace
detrás de una interfaz ya verificada. El orden inverso —instalar primero,
construir los controles después— es cómo se llega a un AUC de 0,9997.

## Lo que hay que decidir ANTES de instalarlo

| # | decisión | por qué no la tomo yo |
|---|---|---|
| 1 | agregar `torch` + `transformers` (~2,5 GB) al lock | cambia el entorno reproducible del proyecto entero |
| 2 | CPU o GPU | el lock dice "sin CUDA"; sin GPU el precomputado cambia de escala (ver `feasibility.py`) |
| 3 | dónde viven los pesos y cómo se hashean | `ModelIdentity` exige `weights_sha256`; sin eso nada es reproducible |
| 4 | si el gasto se justifica antes de tener el resultado del paso 2 | la campaña está pre-registrada y sin correr en `docs/campaigns/CAMP-002…` |

## Riesgo declarado: fuera de distribución

El preentrenamiento es mayormente cripto y acciones. Futuros intradía —sesiones
ETH/RTH, gaps de overnight, GLOBEX— es otro régimen de microestructura. **Este es
el dominio del proyecto entero.** No es un detalle a verificar después: es la
hipótesis principal a refutar, y por eso el criterio de refutación de CAMP-002
está escrito antes de correr nada.

Hay un segundo riesgo, más sutil y menos comentado: Kronos se preentrenó con
datos que **incluyen el período de backtest** de cualquiera que lo use sobre
historia reciente. Eso no es look-ahead en el sentido del punto 1 —el modelo no
ve el futuro de *esta* serie— pero sí es contaminación de la muestra: el modelo
ya "vio" regímenes parecidos durante el entrenamiento. Es irreparable con
zero-shot y hay que declararlo en cualquier resultado positivo.
"""
from __future__ import annotations

from .contract import ModelIdentity, PredictionRecord, Predictor

DISPONIBLE = False
_MOTIVO = ("torch/transformers no están instalados y los pesos no están "
           "descargados. Es deliberado: ver el docstring de este módulo.")

try:  # pragma: no cover - por diseño no se cumple en este entorno
    import torch  # noqa: F401
    DISPONIBLE = True
    _MOTIVO = ""
except Exception as _e:  # pragma: no cover
    pass


class KronosNoInstalado(RuntimeError):
    pass


def identidad_kronos(weights_sha256, *, name="Kronos-small", revision="main",
                     lookback_bars=400, horizon_bars=12, n_paths=30, seed=20260726,
                     bar_spec="time:5"):
    """`ModelIdentity` de una config de Kronos.

    `context_bars` sale del model zoo: mini 2048, small y base 512. El default
    `lookback_bars=400` es el recomendado por los autores y entra en 512.
    """
    contextos = {"Kronos-mini": 2048, "Kronos-small": 512, "Kronos-base": 512}
    return ModelIdentity(
        name=name, revision=revision, weights_sha256=weights_sha256,
        context_bars=contextos.get(name, 512), lookback_bars=lookback_bars,
        horizon_bars=horizon_bars, n_paths=n_paths, seed=seed, bar_spec=bar_spec,
        extra=dict(repo="shiyu-coder/Kronos", licencia="MIT",
                   ood="futuros intradia NO representados en el preentrenamiento",
                   contaminacion="el preentrenamiento puede cubrir el periodo de backtest"))


class KronosPredictor(Predictor):
    """Adaptador real. Falla ruidosamente si el modelo no está.

    Deliberadamente **no** hay fallback silencioso a un heurístico: un feature
    que a veces es Kronos y a veces otra cosa produce un backtest que no
    corresponde a ningún modelo.
    """

    def __init__(self, identity: ModelIdentity, model=None, tokenizer=None,
                 device="cpu", bar_ns=300 * 10**9, latency_ns=0):
        if model is None and not DISPONIBLE:
            raise KronosNoInstalado(
                "KronosPredictor no se puede construir: %s\n"
                "Para testear el pipeline usá edgelab.external.mock.MockPredictor, "
                "que tiene la misma interfaz y las mismas tres columnas." % _MOTIVO)
        self.identity = identity
        self.model, self.tokenizer, self.device = model, tokenizer, device
        self.bar_ns, self.latency_ns = int(bar_ns), int(latency_ns)

    def predict_at(self, bars, i):
        """Muestreo Monte Carlo desde la barra `i`, viendo `bars[:i+1]`.

        Las tres columnas salen de la distribución de caminos, no de un punto:

          `p_up`            fracción de caminos que terminan por encima del último
                            cierre observado — la confianza direccional del modelo
          `sigma_pred`      desvío de los retornos previstos — el régimen
          `spread_q90_q10`  dispersión entre caminos — la confianza del modelo
                            en sí mismo, que es la más interesante de las tres y
                            la que un modelo puntual no puede dar

        `generated_at_ns` es el cierre de `bars[i]` y `target_ts_ns` el de la
        barra `i + horizon`. Nunca el índice que devuelve el modelo.
        """
        if self.model is None:
            raise KronosNoInstalado(_MOTIVO)
        lb = min(self.identity.lookback_bars, i + 1)
        ventana = bars[i - lb + 1: i + 1]          # <- la rebanada, siempre acá
        caminos = self._muestrear(ventana)         # (n_paths, horizon) de cierres
        ultimo = float(bars[i]["close"])
        finales = sorted(c[-1] for c in caminos)
        n = len(finales)
        p_up = sum(1 for f in finales if f > ultimo) / n
        rets = [c[k + 1] / c[k] - 1.0 for c in caminos for k in range(len(c) - 1)]
        mu = sum(rets) / len(rets) if rets else 0.0
        sigma = (sum((r - mu) ** 2 for r in rets) / max(1, len(rets) - 1)) ** 0.5
        q = lambda p: finales[min(n - 1, max(0, int(round(p * (n - 1)))))]  # noqa: E731
        gen = int(bars[i]["ts_ns"])
        return [PredictionRecord(
            model_id=self.identity.model_id, generated_at_ns=gen,
            target_ts_ns=gen + self.identity.horizon_bars * self.bar_ns,
            available_at_ns=gen + self.latency_ns,
            values=dict(p_up=p_up, sigma_pred=sigma,
                        spread_q90_q10=(q(0.90) - q(0.10)) / ultimo))]

    def _muestrear(self, ventana):  # pragma: no cover - requiere el modelo
        raise KronosNoInstalado(
            "el muestreo real se implementa cuando Kronos entre al lock; la "
            "forma de la salida ya está fijada por los tests contra MockPredictor.")

    def cost_estimate_s(self):
        """Segundos por llamada. **Hay que medirlo, no estimarlo de memoria.**

        El default es un placeholder pesimista para que `feasibility.py` no dé
        una respuesta optimista basada en un número inventado.
        """
        return float(self.identity.extra.get("medido_s_por_llamada", 2.0))
