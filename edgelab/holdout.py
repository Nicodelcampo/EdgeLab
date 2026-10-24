"""Frontera del holdout — ÚNICA fuente de verdad en código (enmienda HOLDOUT-A4, decisión de Nico del 2026-10-22).

El holdout es el mismo para TODOS los instrumentos y para todo tipo de dato (ticks, barras, L2): las sesiones CME desde
el trade date 2026-10-01 en adelante. Esa sesión abre a las 17:00 CT del 2026-09-30 = 22:00 UTC.

Todo lo anterior a esa apertura es desarrollo (descubrimiento y, donde una familia lo pre-registró, réplica).
Ver `docs/incidents/AMENDMENT_HOLDOUT-A4_2026-10-22.md`.

Formas equivalentes (usar la que pida cada consumidor, nunca un literal propio):
"""
from __future__ import annotations

HOLDOUT_PRIMERA_SESION = "2026-10-01"                    # trade date CME (la sesión se etiqueta por su día de cierre)
HOLDOUT_PRIMERA_SESION_INT = 20261001                    # mismo, como YYYYMMDD
HOLDOUT_APERTURA_UTC_ISO = "2026-09-30T22:00:00"         # instante de apertura de esa sesión (17:00 CT, UTC-5)
HOLDOUT_APERTURA_UTC_NS = 1_790_805_600_000_000_000      # mismo, en ns desde epoch
HOLDOUT_APERTURA_UTC_S = HOLDOUT_APERTURA_UTC_NS // 1_000_000_000

# Corte FÍSICO de los artefactos de datos viejos (research-v2, datasets Kaggle `*-preholdout`, release v1): 2026-06-30 22:00 UTC.
# No es el holdout: es dónde terminan esos archivos. Lo que está entre esta fecha y la apertura del holdout es desarrollo
# y vive en las extensiones jul-sep (p. ej. `nt8_ext_2026q3`) o en el release líquido.
CORTE_FISICO_RESEARCH_V2_UTC_NS = 1_782_856_800_000_000_000


def es_holdout_trade_date(td) -> bool:
    """td: 'YYYY-MM-DD', YYYYMMDD (int/str) o date."""
    s = str(td).replace("-", "")[:8]
    return int(s) >= HOLDOUT_PRIMERA_SESION_INT


def es_holdout_ns(ts_utc_ns: int) -> bool:
    return int(ts_utc_ns) >= HOLDOUT_APERTURA_UTC_NS
