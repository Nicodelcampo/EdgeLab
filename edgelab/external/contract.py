# -*- coding: utf-8 -*-
"""Contrato de identidad y de predicción para modelos externos.

## Por qué una identidad de modelo separada de `config_id`

`identity.config_id` sirve para kernels determinísticos: mismos params + mismo
código ⇒ misma salida, siempre. Un modelo pre-entrenado rompe las dos mitades de
esa premisa:

1. La salida depende de **pesos** que no viven en el repo y que el autor puede
   re-subir bajo el mismo nombre.
2. Con muestreo Monte Carlo la salida depende de una **semilla**, y sin semilla
   dos corridas idénticas dan features distintas — que es lo mismo que decir que
   el backtest no es reproducible.

Por eso `ModelIdentity` exige `weights_sha256` y `seed` explícitos. No es
burocracia: sin eso, un resultado positivo no se puede volver a producir, y un
resultado que no se puede reproducir no es evidencia de nada.

## El campo que importa de verdad: `generated_at_ns`

Toda la trampa de look-ahead del punto 1 del análisis de Kronos se reduce a
confundir dos instantes:

    generated_at_ns  — el cierre de la ÚLTIMA barra que el modelo pudo ver
    target_ts_ns     — el instante que la predicción describe

`predictor.predict()` sobre la serie completa devuelve algo indexado por
`target_ts_ns`. Si eso se une a la serie de barras por índice, cada barra recibe
una predicción generada con datos de esa misma barra o posteriores. El AUC de
0.9997 sale de ahí, y sale sin que nadie escriba una línea de código
"tramposa" — sale de un `join` que parece obvio.

`PredictionRecord` hace imposible guardar una predicción sin declarar los dos.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict


class ContractError(ValueError):
    """Violación del contrato de modelo externo."""


@dataclass(frozen=True)
class ModelIdentity:
    """Identidad content-addressed de un modelo externo y su configuración.

    `weights_sha256` es obligatorio y **no** puede ser el nombre del repo: el
    mismo tag de HuggingFace puede apuntar a pesos distintos en dos momentos.
    Si no se puede hashear el archivo de pesos, no se puede afirmar que dos
    corridas usaron el mismo modelo — y entonces no se puede comparar nada.
    """
    name: str                    # p.ej. "Kronos-small"
    revision: str                # commit/tag del repo de pesos
    weights_sha256: str          # hash del archivo de pesos REAL
    context_bars: int            # max_context efectivo
    lookback_bars: int           # cuántas barras se le pasan
    horizon_bars: int            # cuántas predice
    n_paths: int                 # caminos Monte Carlo (1 = determinista)
    seed: int                    # semilla del muestreo
    bar_spec: str                # "time:5", "time:1", …
    extra: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.weights_sha256 or len(self.weights_sha256) < 16:
            raise ContractError(
                "weights_sha256 obligatorio: sin el hash de los pesos reales dos "
                "corridas no son comparables. El nombre del modelo NO alcanza — "
                "el mismo tag puede apuntar a pesos distintos.")
        if self.lookback_bars > self.context_bars:
            raise ContractError(
                "lookback_bars=%d > context_bars=%d: el modelo trunca en silencio "
                "y el feature deja de ser lo que dice ser."
                % (self.lookback_bars, self.context_bars))
        if self.n_paths > 1 and self.seed is None:
            raise ContractError(
                "muestreo estocástico (n_paths=%d) sin semilla: el backtest no "
                "sería reproducible." % self.n_paths)
        if self.horizon_bars < 1:
            raise ContractError("horizon_bars debe ser >= 1")

    @property
    def model_id(self) -> str:
        """Hash estable de TODO lo que cambia la salida del modelo."""
        d = asdict(self)
        return hashlib.sha256(
            json.dumps(d, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()[:16]


@dataclass(frozen=True)
class PredictionRecord:
    """Una predicción, con los dos timestamps separados por construcción.

    `available_at_ns` es el tercero, y es el que consume el backtest: el instante
    en que la predicción **existe y se puede usar**. No coincide con
    `generated_at_ns` porque generar 30 caminos Monte Carlo sobre 400 barras de
    contexto lleva tiempo real. Ignorar esa latencia es un look-ahead más chico
    que el del `join` ingenuo, pero sigue siendo look-ahead: en vivo esa
    predicción no habría estado lista.

    Mismo vocabulario que `edgelab.research.sim`, a propósito: ahí `available_at`
    ya decide qué step puede ejecutar una señal.
    """
    model_id: str
    generated_at_ns: int      # cierre de la última barra vista por el modelo
    target_ts_ns: int         # instante que la predicción describe
    available_at_ns: int      # cuándo la predicción está lista para usarse
    values: dict              # p_up, sigma_pred, spread_q90_q10, …

    def __post_init__(self):
        if self.target_ts_ns <= self.generated_at_ns:
            raise ContractError(
                "target_ts (%d) <= generated_at (%d): eso no es una predicción, "
                "es una descripción del pasado. Casi siempre significa que el "
                "índice del DataFrame del modelo se usó como si fuera el instante "
                "de generación." % (self.target_ts_ns, self.generated_at_ns))
        if self.available_at_ns < self.generated_at_ns:
            raise ContractError(
                "available_at (%d) < generated_at (%d): la predicción estaría "
                "disponible antes de que existieran sus datos de entrada."
                % (self.available_at_ns, self.generated_at_ns))

    @property
    def latency_ns(self) -> int:
        return self.available_at_ns - self.generated_at_ns


class Predictor:
    """Interfaz que debe cumplir cualquier modelo externo para entrar al store.

    Deliberadamente angosta. El modelo recibe **sólo** las barras hasta `t`
    inclusive y devuelve records; no recibe el DataFrame completo ni un índice
    sobre el que pueda mirar hacia adelante. Es la misma idea que el firewall del
    holdout: la forma más confiable de no leer el futuro es no tenerlo a mano.
    """

    identity: ModelIdentity

    def predict_at(self, bars, i):
        """Predice desde la barra `i`, viendo `bars[:i+1]` y nada más.

        Devuelve `list[PredictionRecord]` — más de uno si el modelo emite varios
        horizontes. Implementaciones concretas NO deben aceptar `bars` completo y
        rebanar internamente: la rebanada la hace el llamador, y el test de
        causalidad de `causality.py` lo verifica truncando la entrada.
        """
        raise NotImplementedError

    def cost_estimate_s(self) -> float:
        """Segundos por llamada a `predict_at`. Alimenta `feasibility.py`.

        Obligatorio y no opcional: un feature que no se puede computar sobre el
        rango de backtest no es un feature, es una idea.
        """
        raise NotImplementedError
