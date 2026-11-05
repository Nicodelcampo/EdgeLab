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


# Sesiones del holdout que NINGÚN análisis usa (2026-11-02, Nico: «asegurate que cualquier agente no use los días que no se deben usar»).
# Medido target-free sobre el dataset sellado v5 (docs/research/canasta_7_20261030/SELLADO_CONTEO_v5.json): sesión con menos del 50 % de
# los ticks de la mediana del instrumento en octubre, más los días que NT8 no tiene (10-07 en CME). Los domingos de FX son restos del
# fin de semana, no sesiones. Los lectores sellados (`fuentes_ticks.bloques_nq_sellado` / `bloques_spot_sellado`) las descartan siempre;
# `tests/test_holdout_unico.py` lo verifica. Una sesión sólo sale de esta tabla con datos completos re-sellados y re-medidos.
_CME = ("NQ", "MNQ", "ES", "MES", "YM", "MYM", "GC", "MGC", "6B", "6E", "6J", "MBT")
SESIONES_EXCLUIDAS_HOLDOUT = {
    **{s: {20261007} for s in ("NQ", "MNQ", "ES", "MES", "GC", "MGC", "YM", "MYM")},     # NT8 no tiene el 7-oct (YM a medias)
    "ES": {20261007, 20261029, 20261030}, "MES": {20261007, 20261029, 20261030},          # 40 % y 47 % de una sesión normal
    "6B": {20261029}, "6E": {20261029},
    "USATECHIDXUSD": {20261029}, "USA500IDXUSD": {20261012, 20261029}, "USA30IDXUSD": {20261029}, "XAUUSD": {20261029},
    "EURUSD": {20261004, 20261011, 20261018, 20261025, 20261029}, "GBPUSD": {20261004, 20261011, 20261018, 20261025, 20261029},
    "USDJPY": {20261004, 20261011, 20261012, 20261018, 20261025, 20261029},
}


def sesion_excluida(instrumento: str, trade_date) -> bool:
    """True si la sesión `trade_date` (YYYYMMDD) del `instrumento` (futuro o símbolo Dukascopy) no se usa en ningún análisis."""
    return int(str(trade_date).replace("-", "")[:8]) in SESIONES_EXCLUIDAS_HOLDOUT.get(str(instrumento).upper().replace("DK:", ""), set())
