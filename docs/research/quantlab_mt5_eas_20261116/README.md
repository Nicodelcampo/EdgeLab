# QuantLab MT5 EAs — Ingeniería Inversa y Traducción Python para EdgeLab

Paquete y documentación correspondientes a los Expert Advisors compilados de MetaTrader 5:
1. `QLB_K_XAUUSD_3x_speed_q4_turn.ex5` (v1.8): canasta multi-slot hedging (`speed_switch_momentum` H4, `q4_momentum_breakout` H1 Q4, `turn_of_month_january_momentum_2` H1 solo Long), con `SL = 2.5 * iATR(14)`, `TP = 5.0 * iATR(14)` (`RR = 2.00`), salida temporal (`120` barras H4 / `40` barras H1) y freno diario `4.0%`.
2. `SessionOpenMomentum.ex5` (v2.2): estrategia intradía `PERIOD_M5` sobre apertura NY (`16:30` -> ejecuta `16:35:00`), señal `Close vs EMA(12)`, `SL = 8.0 * iATR_M5(14)`, trailing dinámico sobre `EMA_M5(120)` activado a `+0.50 R` y Adaptive Risk (`0.50x .. 2.00x`).

## Estructura en el repositorio

- `edgelab/research/quantlab_mt5/`:
  - `contracts.py`: contratos de datos (`TRADE_COLUMNS` de 16 columnas), presets de instrumentos (`EURUSD`, `XAUUSD`, `USATECH`/`NQ`, `USA500`/`ES`) y configuraciones completas (`SessionOpenMomentumConfig`, `QlbBasketConfig`).
  - `indicators.py`: cargador causal `load_ohlc_data` con guardia anti-holdout (`< 2026-10-01` y bloqueo de rutas `sellado`), resampleo causal `resample_ohlc` e indicadores exactos MQL5 (`mql5_ema`, `mql5_sma`, `mql5_atr` como SMA de True Range).
  - `session_open_momentum.py`: motor fiel `correr_session_open_momentum` con diagnóstico de días omitidos por posición abierta y trailing por barra.
  - `qlb_k_xauusd_basket.py`: motor multi-slot hedging `correr_qlb_basket` y `correr_slot_qlb`.
  - `cli.py`: `correr_modulo_quantlab` (`SOM`, `QLB_S0`, `QLB_S1`, `QLB_S2`, `QLB_BASKET`) y `correr_todos_quantlab`.
- `docs/research/quantlab_mt5_eas_20261116/`:
  - `INGENIERIA_INVERSA_EX5_MT5.md`: análisis forense completo y comparación entre comportamiento verificado al 100% e inferido.
  - `mql5/`: reconstrucciones limpias en código fuente `.mq5`.
  - `reference_data/`: trades exactos de Strategy Tester build 5956 (`som_tester_trades_189.csv`, `qlb_tester_trades_57.csv`) y barras OHLC de referencia (`eurusd_m5_may_jun2026.csv`, `eurusd_h1_h4_2025_2026.json`).
- `tests/research/test_quantlab_mt5_traduccion.py`: suite de validación contra Strategy Tester y datos pre-holdout Dukascopy (`XAUUSD` / `EURUSD` `< 2026-10-01`).

## Uso rápido en EdgeLab

```python
from edgelab.research.quantlab_mt5 import (
    load_ohlc_data,
    correr_session_open_momentum,
    correr_qlb_basket,
    correr_todos_quantlab,
)

df_xau = load_ohlc_data(r"C:\StrategyQuantX145\user\mcp-work\edgelab_m1\XAUUSD_M1_dukas-M1-.csv", start="2024-01-01", end="2026-10-01")
res = correr_todos_quantlab(df_xau, instrument="XAUUSD")
print(res["resumen_df"])
```
