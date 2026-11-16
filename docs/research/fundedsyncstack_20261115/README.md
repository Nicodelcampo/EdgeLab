# FUNDEDSYNCSTACK (1.0.0.5) — Ingeniería Inversa y Traducción Completa a Python

Este paquete contiene la ingeniería inversa completa y la traducción 1:1 a Python de los **15 submódulos** y del **motor de cartera / netting** de `FUNDEDSYNCSTACK5.dll` (2026-10-29.1-FUNDEDSYNCSTACK).

## Estructura en el repositorio

- **Paquete Python (edgelab.research.fundedsyncstack)**:
  - `edgelab/research/fundedsyncstack/__init__.py`: API pública (MODULOS, SENALES, CONFIG_CLASSES, correr_modulo, correr_todos, simular_cartera).
  - `edgelab/research/fundedsyncstack/contracts.py`: contratos de datos (BarSeries, MultiSeriesContext, TradeRecord, TRADE_COLUMNS de 16 columnas).
  - `edgelab/research/fundedsyncstack/base_series.py`: cargador causal M1 (load_m1_data con guardia anti-holdout sobre sellado), constructor de las 10 series (ip1..bip10, uild_multi_series) e indicadores exactos de NinjaTrader 8 (
t_sma, 
t_ema, 
t_atr, 
t_adx).
  - `edgelab/research/fundedsyncstack/motor_cartera.py`: motor de cartera (PortfolioConfig, PortfolioEngine, ModuleState, RollingValues, simular_cartera), tablas de sizing (TryGetOptimizedEvaluationQuantity, RampartQuantity, ActiveLucidMicroContractCap), rotación 3-de-5 (S, P, C, R, E), calendario estricted-news-days.csv y cierre diario CME (15:44:00 CT).
  - `edgelab/research/fundedsyncstack/modulos_a1_a20_f_s.py`: Lote 1 (A1 Absorb 1m, A20 Absorb 20m, F Fabio ORB 5m, S Swas 3m).
  - `edgelab/research/fundedsyncstack/modulos_p_c_v_o.py`: Lote 2 (P NqPullback 1m, C CapstoneGap 1m US STOCK, V VaultBreak 5m RTH, O Overnight 1m ETH + 1d RTH).
  - `edgelab/research/fundedsyncstack/modulos_w_n_t.py`: Lote 3 (W VwapCross Long-only 1m, N NDayLong 1m + 1d ETH, T FtmEngine ORB 15m + KNN K=15 de 14 features con pares shadow y refinamiento en 2 etapas).
  - `edgelab/research/fundedsyncstack/modulos_r_z_e_q.py`: Lote 4 (R AtrPhase 10m ETH, Z ZetaTrendDay 26 buckets de 15m RTH, E EmaDivergence 15m ETH, Q Rampart 5m ETH).
  - `edgelab/research/fundedsyncstack/cli.py`: CLI para correr cualquier módulo o la cartera completa desde línea de comandos.
- **Documentación y Metadatos Extraídos (docs/research/fundedsyncstack_20261115/)**:
  - `INGENIERIA_INVERSA_FUNDEDSYNCSTACK.md`: informe completo de ingeniería inversa (arquitectura, los 15 módulos, sizing, hallazgos forenses del IL y desglose empírico del backtest de NinjaTrader).
  - `defaults_dump.txt`: los 302 valores por defecto extraídos de State.SetDefaults.
  - `props_meta.txt`: los 325 atributos [NinjaScriptProperty], [Display], [Range] y [Browsable].
  - `static_arrays.json`: constantes estáticas embebidas en el binario (AtrPhaseStandaloneBlockedEntrySessions, ZetaNonFullNyse, exclusiones de FtmEngine, PortfolioBuild).
  - `il_por_modulo/`: desensamblado IL completo particionado en 17 archivos por módulo (964 métodos indexados).
- **Suite de Tests (	ests/research/test_fundedsyncstack_traduccion.py)**:
  - Verifica carga, guardia anti-holdout, construcción de las 10 series, los 15 módulos y la cartera consolidada.

## Uso rápido desde cualquier agente en Python

~~~python
from edgelab.research.fundedsyncstack import (
    MODULOS,
    load_m1_data,
    build_multi_series,
    correr_modulo,
    correr_todos,
)

df_m1 = load_m1_data("ruta/a/NQ_M1.csv", start="2025-06-01", end="2026-10-01", tz_input="UTC")
ms = build_multi_series(df_m1, tz_input="UTC")

# Ejecutar un módulo individual (ej. S, O, o V con ventana de 60 días)
df_s = correr_modulo("S", ms)
df_v = correr_modulo("V", ms, daily_atr_length=60)

# Ejecutar los 15 módulos y la simulación consolidada de cartera
res = correr_todos(ms, incluir_cartera=True)
print(res["resumen_df"])
print(res["cartera"]["comparison"])
~~~