"""Subpaquete Kaggle de EdgeLab.

Cumple el Contrato Kaggle v2 (2026-08-11): EdgeLab construye semantica,
eventos, features, folds y manifests; Kaggle ejecuta analisis. Estos modulos
son la capa comun que TODO notebook formal debe importar, de modo que el
sello de holdout, el mapeo de sesiones y la identidad de la corrida sean
unicos y auditables en un solo lugar.

Dependencias: numpy + stdlib. pyarrow solo en inventory/streaming.
"""

from . import identity, integrity, seal, sessions_cme  # noqa: F401

__all__ = ["identity", "integrity", "seal", "sessions_cme"]
