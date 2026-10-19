# -*- coding: utf-8 -*-
"""Features de modelos EXTERNOS pre-entrenados (Kronos y cualquier sucesor).

Separado a propósito de `edgelab.bridge`: el bridge produce features
*determinísticas y auditables línea por línea* desde NT8. Un modelo externo
pre-entrenado es lo contrario — pesos opacos, muestreo estocástico, distribución
de entrenamiento ajena al dominio. Mezclarlos en el mismo paquete invitaría a
tratarlos con el mismo nivel de confianza, y no lo merecen.

**Ninguno de estos módulos importa `torch`, `transformers` ni descarga pesos.**
El paquete define el contrato, el almacenamiento point-in-time y los gates; el
modelo real entra por detrás de una interfaz y se puede reemplazar por un mock
determinista para testear todo el pipeline sin GPU. Que la suite corra sin torch
no es una comodidad: es lo que permite que el firewall causal se verifique en
cada commit.

Módulos:

  `contract`    — identidad del modelo, `PredictionRecord`, la ABC `Predictor`
  `pit_store`   — almacenamiento con la invariante de DOS timestamps
  `causality`   — detector adversarial de look-ahead (target-free)
  `mock`        — predictor determinista sin dependencias, para tests
  `kronos`      — adaptador real, falla ruidosamente si no está instalado
  `feasibility` — calculadora de costo de cómputo, ANTES de gastar nada

Estado: **infraestructura, no adopción.** Que exista este paquete no significa
que Kronos entre al proyecto. Correr cualquier evaluación de lift contra P&L
exige el manifiesto de campaña y el OK de Nico (`docs/campaigns/CAMP-002…`).
"""

from .contract import ModelIdentity, PredictionRecord, Predictor  # noqa: F401
from .pit_store import PITFeatureStore, LookAheadError  # noqa: F401

__all__ = ["ModelIdentity", "PredictionRecord", "Predictor",
           "PITFeatureStore", "LookAheadError"]
