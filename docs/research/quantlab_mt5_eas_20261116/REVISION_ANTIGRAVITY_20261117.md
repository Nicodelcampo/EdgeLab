# Revisión independiente con MT5 Strategy Tester, SQX y DLL de EdgeLab (2026-11-17)

Estado: VIGENTE — revisión cruzada de Antigravity (MT5 Tester como árbitro), incorporada en `RESULTADO_SOM.md` y `CRITERIOS_AUDITORIA.md`.

**Rama:** `claude/vibrant-clarke-s9z6e2` (comparado `74e1cdb7` vs `2c08a2c3`)  
**Árbitro principal:** MetaTrader 5 Build 5956 (`MetaTester 5`, modo *1 minute OHLC*, inputs de fábrica)  
**Datos de referencia nuevos generados:** [`som_tester_usatech_2024_2026.csv`](file:///C:/Users/nicoc/.gemini/antigravity/brain/79352924-80c3-409e-9be9-296eeef88676/scratch/wt_claude/docs/research/quantlab_mt5_eas_20261116/reference_data/som_tester_usatech_2024_2026.csv) (`617` operaciones en `USATECH` M5, `2024-01-02` → `2026-09-28`, corte estricto `< 2026-09-30 22:00 UTC`)

> **Alcance de esta auditoría:** Verifica exclusivamente los puntos 1–8 solicitados contra los `.ex5` reales en el Strategy Tester de MT5, la configuración viva de StrategyQuant X (`list_data`), el IL desensamblado original y los módulos Python actuales de EdgeLab. No modifica reglas congeladas ni código de estrategia (`SOM sin_finde` intacto; `fundedsyncstack` sólo lectura).

---

## Tabla resumen de veredictos

| # | Punto auditado | Veredicto | Evidencia principal | Archivo / referencia |
|---|---|---|---|---|
| 1 | Llenado del stop con gap (`min(o, sl)` / `max(o, sl)`) | **Refutado contra MT5 Tester (modo Instant/CFD); Válido como regla conservadora de futuros** | El EA real usa SL nativo en servidor vía `CTrade`; en los `8` gaps de apertura + `1` salto de sesión en `USATECH` (`#296`, `#519`, `#557`, `#506`, etc.), el MT5 Tester llenó al `SL` exacto mientras Python llenó a `open` (`px`). **Bug menor en Python (líneas 308–310):** si el SL salta en la vela de entrada, usa `init_sl` sin regla de gap y deja `mae_usd = 0.0`. | [`session_open_momentum.py`](file:///C:/Users/nicoc/.gemini/antigravity/brain/79352924-80c3-409e-9be9-296eeef88676/scratch/wt_claude/edgelab/research/quantlab_mt5/session_open_momentum.py#L210-L218) / [`L304-L310`](file:///C:/Users/nicoc/.gemini/antigravity/brain/79352924-80c3-409e-9be9-296eeef88676/scratch/wt_claude/edgelab/research/quantlab_mt5/session_open_momentum.py#L304-L310) |
| 2 | Stop en la vela de entrada (`16:35`) | **Verificado (con omisión de trailing en Python)** | En MT5 la orden `CTrade::PositionOpen` entra a `16:35:00` con `sl = init_sl` ya activo en el servidor durante toda esa barra (`16:35:00–16:39:59`), aunque en `0/189` (`EURUSD`) y `0/617` (`USATECH`) saltó el `INIT_SL` en esa primera vela. **Matiz faltante en Python:** en `30/617` trades de `USATECH` el EA sí activó y movió el *trailing stop* (`+0.50 R`) dentro de `16:35:00–16:39:59`, mientras Python evalúa trailing recién desde `16:40`. | [`session_open_momentum.py`](file:///C:/Users/nicoc/.gemini/antigravity/brain/79352924-80c3-409e-9be9-296eeef88676/scratch/wt_claude/edgelab/research/quantlab_mt5/session_open_momentum.py#L227-L237) / [`som_tester_usatech_2024_2026.csv`](file:///C:/Users/nicoc/.gemini/antigravity/brain/79352924-80c3-409e-9be9-296eeef88676/scratch/wt_claude/docs/research/quantlab_mt5_eas_20261116/reference_data/som_tester_usatech_2024_2026.csv) |
| 3 | Flags `close_weekend`, `rotar`, `permitir` apagados | **Verificado** | `pytest tests/research/test_quantlab_mt5_traduccion.py -v` pasó `4/4`. En junio 2026 (`14/14` trades de `som_tester_trades_189.csv`) nada cambió. En la ventana completa may-jun (`23` trades), con las 3 opciones apagadas únicamente cambia el precio de salida del trade `#2` (`2026-05-21`, gap del `2026-05-25 00:00`: `1.16301` → `1.16373` por el Punto 1), arrastrando `-0.01` lot por compounding posterior. | [`contracts.py`](file:///C:/Users/nicoc/.gemini/antigravity/brain/79352924-80c3-409e-9be9-296eeef88676/scratch/wt_claude/edgelab/research/quantlab_mt5/contracts.py#L108-L120) / [`test_quantlab_mt5_traduccion.py`](file:///C:/Users/nicoc/.gemini/antigravity/brain/79352924-80c3-409e-9be9-296eeef88676/scratch/wt_claude/tests/research/test_quantlab_mt5_traduccion.py#L1-L169) |
| 4 | Corte anti-holdout `2026-09-30 22:00 UTC` | **Verificado** | Todos los datasets de referencia y la nueva corrida `USATECH` terminan estrictamente antes de `2026-09-30T22:00:00Z` (máximo real: `2026-09-28 19:20:40 EST+07` = `16:20:40 UTC` en trades, y `2026-09-29 23:14 EST+07` = `20:14 UTC` en barras). | [`holdout.py`](file:///C:/Users/nicoc/.gemini/antigravity/brain/79352924-80c3-409e-9be9-296eeef88676/scratch/wt_claude/edgelab/holdout.py#L1-L53) / [`indicators.py`](file:///C:/Users/nicoc/.gemini/antigravity/brain/79352924-80c3-409e-9be9-296eeef88676/scratch/wt_claude/edgelab/research/quantlab_mt5/indicators.py#L20-L30) |
| 5 | Comparación operación por operación `USATECH` M5 (`2024-01` → `2026-09-29`) | **Verificado con `98.88%` de presencia (`616/623`) y `100%` señal/entrada/SL/motivo** | MT5 generó `617` trades y Python `622` (`616` fechas comunes). Sobre las `616` comunes: `100%` lado, `100%` entrada (`<=0.02`), `100%` SL inicial (`<=0.05`), `100%` motivo (`INIT_SL`/`TRAIL_SL`), `98.54%` (`607/616`) misma vela M5 de salida, `92.53%` (`570/616`) salida `<=0.50` pts y `69.16%` (`426/616`) salida `<=0.05` pts. Las `6` faltantes en MT5 (`1` en Python) se explican al `100%` por bloqueos a las `16:30:00` cuando el trade previo cerró entre `16:30:40` y `16:34:40`. | [`som_tester_usatech_2024_2026.csv`](file:///C:/Users/nicoc/.gemini/antigravity/brain/79352924-80c3-409e-9be9-296eeef88676/scratch/wt_claude/docs/research/quantlab_mt5_eas_20261116/reference_data/som_tester_usatech_2024_2026.csv) |
| 6 | Gatillos de `QLB` Slots 0, 1 y exacto de Slot 2 | **No verificable (Slots 0 y 1; sub-filtro Slot 2)** / **Verificado caja negra parcial (Slot 2)** | La lógica booleana de entrada de los 3 slots vive compilada en x64 nativo dentro de `QLB_K_XAUUSD_3x_speed_q4_turn.ex5`. Las reglas de Python (`EMA10/50 + ATR5/20 >= 0.85`, `hi20/lo20`, `c > c[1] or c > ema10`) son inferencias no verificables sin fuente/deconstrucción. De Slot 2 (`turn_of_month_january_momentum_2`) sólo se verifica por caja negra (`qlb_tester_trades_57.csv`): `37/37` `BUY`, `PERIOD_H1`, `SL = 2.5*ATR(14)`, `TP = 5.0*ATR(14)`, `MaxHold = 40` barras H1, ventana inicio de mes días `1–8` (enero extendido `2–13`) con reentrada casi continua en barras H1 al cerrar el trade previo. | [`qlb_k_xauusd_basket.py`](file:///C:/Users/nicoc/.gemini/antigravity/brain/79352924-80c3-409e-9be9-296eeef88676/scratch/wt_claude/edgelab/research/quantlab_mt5/qlb_k_xauusd_basket.py#L1-L135) / [`qlb_tester_trades_57.csv`](file:///C:/Users/nicoc/.gemini/antigravity/brain/79352924-80c3-409e-9be9-296eeef88676/scratch/wt_claude/docs/research/quantlab_mt5_eas_20261116/reference_data/qlb_tester_trades_57.csv) |
| 7 | Zonas horarias exportadas de SQX (Hallazgo H1) | **Verificado** | Consultado `list_data(detail=true)` sobre los `150` datasets en SQX: exactamente los `10` símbolos `*_M1_dukas` tienen `timezone="EST+07"` (NY+7); los `6` citados por H1 (`USSC2000IDXUSD`, `DEUIDXEUR`, `EUSIDXEUR`, `GBRIDXGBP`, `JPNIDXJPY`, `LIGHTCMDUSD`) más otros `11` símbolos Dukascopy M1 y `10` índices `[[...]]` de `SQ Equity data` tienen `timezone="UTC"`. Se reporta además que `@EW` + `103` acciones `SQ Equity data` usan `"Exchange"`. | SQX MCP `list_data(detail=true)` (vía `http://127.0.0.1:8080/mcp`) |
| 8 | `FUNDEDSYNCSTACK` `stop_price` en módulo `T` (Hallazgo H2) | **Verificado** | Sólo `run_t` (`modulos_w_n_t.py`) muta `active_stop_price` en cierres de 15m al activarse el stop administrado (`L2182–2187`) y escribe `stop_price=active_stop_price` (`L1876`, `L1928`, `L1952`). En el DLL C# original (`mod_T_ftm.txt`), `FtmEngine` conserva `activeInitialStopTicks` intacto (`L720`, `L1714`) separado de `ChangeModuleStopFromNq(2)` (`L1645`). Se propone añadir `initial_stop_price` sin alterar cálculos ni resultados. | [`modulos_w_n_t.py`](file:///C:/Users/nicoc/.gemini/antigravity/brain/79352924-80c3-409e-9be9-296eeef88676/scratch/wt_claude/edgelab/research/fundedsyncstack/modulos_w_n_t.py#L1876-L2187) / [`mod_T_ftm.txt`](file:///C:/Users/nicoc/.gemini/antigravity/brain/79352924-80c3-409e-9be9-296eeef88676/scratch/wt_claude/docs/research/fundedsyncstack_20261115/il_por_modulo/mod_T_ftm.txt#L720) |

---

## Detalle técnico por punto

### Punto 1 — Llenado del stop cuando hay gap de apertura (`min(o, sl)` / `max(o, sl)`)

**Cómo opera el EA real (`SessionOpenMomentum.ex5`):**
1. En el Strategy Tester de MT5 (`EURUSD` en [`som_tester_trades_189.csv`](file:///C:/Users/nicoc/.gemini/antigravity/brain/79352924-80c3-409e-9be9-296eeef88676/scratch/wt_claude/docs/research/quantlab_mt5_eas_20261116/reference_data/som_tester_trades_189.csv) y `USATECH` en [`som_tester_usatech_2024_2026.csv`](file:///C:/Users/nicoc/.gemini/antigravity/brain/79352924-80c3-409e-9be9-296eeef88676/scratch/wt_claude/docs/research/quantlab_mt5_eas_20261116/reference_data/som_tester_usatech_2024_2026.csv)), el EA **no cierra manualmente por stop en código MQL5**, sino que adjunta el nivel `sl` a la orden mediante `CTrade::PositionOpen` y lo actualiza vía `CTrade::PositionModify`. Quien ejecuta la orden de stop es el motor del servidor / Strategy Tester según el modo de ejecución del símbolo.
2. **Prueba con trades concretos en `USATECH` (`NQ_M1_dukas`, símbolo custom clonado desde `EURUSD` en modo `SYMBOL_CALC_MODE_CFDLEVERAGE`, `Model=1` M1 OHLC):** en todos los gaps reales de apertura de sesión/lunes o saltos donde la barra M5 abrió más allá del `last_sl` activo, **MT5 Tester llenó al precio exacto de `last_sl` (`0.00` deslizamiento), mientras Python llenó al `open` de la barra:**

| Fecha entrada | Lado | Hora cierre MT5 | `last_sl` activo | `open` real bar M5 en `NQ_M1_dukas` | Llenado MT5 Tester | Llenado Python (`min(o,sl)`/`max(o,sl)`) | Brecha (`open - sl`) |
|---|---|---|---|---|---|---|---|
| `2025-02-04` (`#250`) | `BUY` | `2025-02-05 01:00:00` | `21468.22` | `21455.142` | `21468.22` | `21455.14` (`TRAIL_SL`) | `-13.08` pts |
| `2025-04-11` (`#296`) | `SELL` | `2025-04-14 01:05:00` | `18835.40` | `18909.709` | `18835.40` | `18909.71` (`INIT_SL`) | `+74.31` pts |
| `2025-06-19` (`#340`) | `SELL` | `2025-06-20 01:05:00` | `21545.70` | `21602.265` | `21545.70` | `21602.26` (`TRAIL_SL`) | `+56.57` pts |
| `2025-10-30` (`#420`) | `SELL` | `2025-10-31 01:00:00` | `25924.88` | `26014.503` | `25924.88` | `26014.50` (`TRAIL_SL`) | `+89.62` pts |
| `2026-03-19` (`#506`) | `SELL` | `2026-03-23 14:18:00` | `23734.65` | `24459.564` | `23734.65` | `24459.56` (`TRAIL_SL`) | `+724.91` pts *(gap datos `14:05→14:15`)* |
| `2026-04-10` (`#519`) | `BUY` | `2026-04-13 01:00:00` | `24975.28` | `24772.308` | `24975.28` | `24772.31` (`INIT_SL`) | `-202.97` pts |
| `2026-06-12` (`#557`) | `SELL` | `2026-06-15 01:00:00` | `29750.76` | `29905.253` | `29750.76` | `29905.25` (`INIT_SL`) | `+154.49` pts |
| `2026-07-10` (`#576`) | `BUY` | `2026-07-13 01:00:00` | `29749.10` | `29726.297` | `29749.10` | `29726.30` (`TRAIL_SL`) | `-22.80` pts |

**Conclusión auditora sobre el cambio de Claude:**
- Si el árbitro es exactamente **MT5 Strategy Tester bajo símbolo CFD/FX clonado de `EURUSD`**, el cambio `px = min(o, sl) if side > 0 else max(o, sl)` **no reproduce al Tester** (el Tester llena al precio de `sl`).
- Sin embargo, como modelo económico de **futuros CME reales** (`NQ`, `ES`, `YM` en ejecución Exchange sin garantía de stop ante gaps), una orden stop disparada tras un gap de apertura se convierte en orden a mercado al primer precio cotizado (`open`); el cambio de Claude vuelve la backtest **correctamente más conservadora** para futuros.
- **Error puntual detectado en la línea [`session_open_momentum.py:308-310`](file:///C:/Users/nicoc/.gemini/antigravity/brain/79352924-80c3-409e-9be9-296eeef88676/scratch/wt_claude/edgelab/research/quantlab_mt5/session_open_momentum.py#L304-L310):** si el `init_sl` se toca en la misma vela de entrada `i == entry_idx`, Claude escribió `_finalize_som_trade(pos, cur_ts, init_sl, ...)` en lugar de aplicar `min(o, init_sl)` / `max(o, init_sl)`, y retorna sin actualizar `pos["mae_pts"]` / `pos["mfe_pts"]`, lo que reportaría `mae_usd = 0.0` (afortunadamente hubo `0` casos en `2024–2026`).

---

### Punto 2 — Chequeo de stop y comportamiento dentro de la vela M5 de entrada (`16:35`)

1. **Parada por SL en la vela de entrada (`Verificado`):** En los logs de `MetaTester 5` se observa que `CTrade::OrderSend: market buy/sell ... sl: <init_sl>` adjunta el `sl` en el servidor en `16:35:00` en el instante mismo de apertura. Por tanto, cualquier tick posterior entre `16:35:00` y `16:39:59` que alcance `init_sl` dispara el stop en esa misma vela.
2. **Frecuencia real observada:** En ambas corridas oficiales de MT5 Tester (`0/189` en `EURUSD` y `0/617` en `USATECH`), `same_m5_bar` fue `0` (ninguna operación alcanzó `-1.0 R` dentro de sus primeros 5 minutos), y en Python `USATECH 2024–2026` `bars == 1` también fue `0`.
3. **Diferencia real observada en la vela de entrada (omisión en Python):** Aunque no hubo SL en `16:35`, **el EA real sí evalúa y activa el trailing stop (`+0.50 R`) dentro de la vela de entrada `16:35`**, mientras `session_open_momentum.py` evalúa `sl_hit` y `trail_start_r` desde la vela `16:40` (salvo el `if (l <= init_sl)` agregado al final del loop). En el log del Tester de `USATECH` hubo **exactamente `30` modificaciones de SL dentro de `16:35:00–16:39:59`**, por ejemplo:
   - `2024.03.21 16:38:00`: `#94 buy 18055.423` → `position modified ... sl: 18368.08`
   - `2024.08.02 16:38:00`: `#260 sell 19415.832` → `position modified ... sl: 18597.58`
   - `2024.11.07 16:35:00`: `#390 buy 20605.023` → `position modified ... sl: 20823.41`
   - `2024.11.21 16:38:40`: `#410 sell 20711.498` → `position modified ... sl: 20650.09`
   - `2025.07.01 16:35:40`: `#692 sell 22607.12` → `position modified ... sl: 22617.75`
   - `2025.08.01 16:36:00`: `#730 sell 23544.71` → `position modified ... sl: 23040.55`

---

### Punto 3 — Verificación de flags agregados (`close_weekend`, `rotar`, `permitir`)

1. **Suite de pruebas:** Re-corrido `python -m pytest tests/research/test_quantlab_mt5_traduccion.py -v` sobre el árbol actual (`2c08a2c3`) → **`4 passed in 141.57s`** (previamente `32.67s`).
2. **Comparación exacta contra `som_tester_trades_189.csv` (junio 2026):** Con `SessionOpenMomentumConfig(close_weekend=False, rotar=False)` y `permitir=None` sobre `eurusd_m5_may_jun2026.csv`, las **`14/14`** operaciones de junio (`2026-06-01` al `2026-06-24`, última incluida en `som_tester_trades_189.csv`) coinciden en dirección, hora de entrada (`16:35`), vela de salida y motivo.
3. **Diferencia exacta entre commit `74e1cdb7` y `HEAD` (`2c08a2c3`) sobre `eurusd_m5_may_jun2026.csv` (`23` operaciones):**
   - Sólo cambia la salida del trade `#2` (`2026-05-21 16:35:00`, Sell, `stop_price = 1.16301`) que en Dukascopy alcanza el gap de apertura del lunes `2026-05-25 00:00`: en `74e1cdb7` cerró a `1.16301` (`-1290.48 USD`) y en `HEAD` cierra a `1.16373` (`-1494.24 USD`, regla de gap del Punto 1).
   - Ese delta de `-203.76 USD` en balance produce únicamente una variación de `-0.01` lot por compounding en las operaciones posteriores (`qty` p. ej. `5.35` → `5.34`), sin alterar ni una sola señal, entrada, vela de salida ni precio de salida en el resto de los `22` trades (`14/14` en junio idénticos al pip vs MT5).

---

### Punto 4 — Corte anti-holdout (`2026-09-30 22:00 UTC`)

Verificado en [`holdout.py`](file:///C:/Users/nicoc/.gemini/antigravity/brain/79352924-80c3-409e-9be9-296eeef88676/scratch/wt_claude/edgelab/holdout.py#L1-L53), [`indicators.py`](file:///C:/Users/nicoc/.gemini/antigravity/brain/79352924-80c3-409e-9be9-296eeef88676/scratch/wt_claude/edgelab/research/quantlab_mt5/indicators.py#L20-L30) y en todos los archivos bajo `docs/research/quantlab_mt5_eas_20261116/reference_data/`:

| Archivo | Registros | Primer timestamp | Último timestamp | Margen respecto a `2026-09-30T22:00:00Z` |
|---|---|---|---|---|
| `eurusd_m5_may_jun2026.csv` | `8,928` barras M5 | `2026-05-15T00:00:00Z` | `2026-06-26T23:55:00Z` | `95` días antes |
| `eurusd_h1_h4_2025_2026.json` | `9,213` H1 / `2,308` H4 | `2025-01-02T00:00:00Z` | `2026-06-26T23:00:00Z` (H1) / `20:00:00Z` (H4) | `95` días antes |
| `som_tester_trades_189.csv` | `189` trades | `open: 2025-06-02T16:35:00Z` | `close: 2026-06-24T18:53:40Z` | `98` días antes |
| `qlb_tester_trades_57.csv` | `57` trades | `open: 2026-01-02T01:00:00Z` | `open: 2026-06-23T16:00:00Z` / `close: 2026-06-23T14:31:40Z` | `99` días antes |
| `usatech_m1_preholdout.csv` *(input MT5)* | `993,260` barras M1 | `2023.11.01 01:00` (`EST+07`) | `2026.09.29 23:14` (`EST+07` ≈ `20:14 UTC`) | `25+` horas antes |
| `som_tester_usatech_2024_2026.csv` *(nuevo)* | `617` trades | `open: 2024-01-02 16:35:00` (`EST+07`) | `close: 2026-09-28 19:20:40` (`EST+07` ≈ `16:20:40 UTC`) | `> 53` horas antes |

Ningún dato cruza la frontera `2026-09-30 22:00 UTC`. *(Observación menor en `indicators.py:86`: en `HEAD` la firma de `load_ohlc_data` cambió el valor por defecto `end=DEFAULT_PRE_HOLDOUT_END` por `end=None`, pero cuando `enforce_pre_holdout=True` continúa imponiendo el techo `HOLDOUT_APERTURA_UTC_ISO`.)*

---

### Punto 5 — Comparación operación por operación `USATECH` M5 (`2024-01-01` → `2026-09-29`, inputs de fábrica)

**Configuración del test en MT5 Strategy Tester:**
- EA: `SessionOpenMomentum.ex5` con inputs de fábrica (`InpOpenNY=16:30`, `InpFastEma=12`, `InpTrailEma=120`, `InpTrailStartR=0.5`, `InpRiskMode=0`, `InpRiskPercent=1.0`, `InpUseAdaptiveRisk=true`, `InpVolRiskFloor=0.5`, `InpVolRiskCap=2.0`, `InpRandomizer=false`, `InpCloseEod=false`).
- Datos cargados al símbolo custom `USATECH` (`CFDLEVERAGE`, `BASE=PROFIT=MARGIN="USD"`, `digits=2`, `point=0.01`, `tick_size=0.01`, `tick_value=0.20`, `contract_size=20.0`, spread `0`): `993,260` barras M1 de `NQ_M1_dukas-M1-.csv` (`2023.11.01 01:00` → `2026.09.29 23:14`, `EST+07`), generando `3,745,460` ticks y `187,468` barras M5.
- Resultado MT5 Tester: **`617` trades cerrados** (`1,235` deals, `0` rechazos), balance final `266,934.79 USD` desde `100,000.00 USD`.
- Traducción Python (`correr_session_open_momentum` sobre `NQ_M1_dukas-M1-.csv` remuestreado a M5, `close_weekend=False, rotar=False, permitir=None`, pre-holdout `2023-11-01` → `2026-09-29`, filtrando entradas `>= 2024-01-01`): **`622` trades**.

**Métricas de concordancia operación por operación:**

| Métrica | Cantidad | Porcentaje | Base de cálculo |
|---|---|---|---|
| Coincidencia en existencia del trade (fechas comunes) | `616` / `623` | **`98.88%`** | Unión de fechas (`616` comunes + `6` sólo Python + `1` sólo MT5) |
| Mismo lado (`BUY` / `SELL`) | `616` / `616` | **`100.00%`** | Trades comunes |
| Mismo precio de entrada (`<= 0.02` pts) | `616` / `616` | **`100.00%`** | Trades comunes |
| Mismo SL inicial (`<= 0.05` pts) | `616` / `616` | **`100.00%`** | Trades comunes |
| Mismo motivo de salida (`INIT_SL` vs `TRAIL_SL`) | `616` / `616` | **`100.00%`** | Trades comunes |
| Misma vela M5 de salida | `607` / `616` | **`98.54%`** | Trades comunes |
| Precio de salida idéntico dentro de `<= 0.50` pts | `570` / `616` | **`92.53%`** | Trades comunes |
| Precio de salida idéntico dentro de `<= 0.05` pts | `426` / `616` | **`69.16%`** | Trades comunes (`68.38%` sobre unión `623`) |

**Explicación exacta de las diferencias:**

1. **Los `6` trades sólo en Python y `1` sólo en MT5 (`7/7` explicados por cierre entre `16:30:40` y `16:34:40`):**
   - El EA real imprime `[Momentum] A Momentum position is still open at the NY open - no new trade today` exactamente a las **`16:30:00`** (apertura de la vela M5 de señal) si todavía hay una posición abierta, y **bloquea el día completo aunque esa posición cierre por SL segundos o minutos después antes de las `16:35:00`**.
   - Python (`session_open_momentum.py` líneas `209–222`) procesa primero `sl_hit` dentro de la vela `16:30` (cerrando la posición y poniendo `pos = None`) antes del chequeo de bloqueo en `16:30`, por lo que llega libre a `16:35` y **sí entra**:
     - `2024-07-04`: `#220` cerró por SL en MT5 a las **`16:32:40`** → bloqueado en MT5, operado en Python.
     - `2025-01-27`: `#486` cerró por SL en MT5 a las **`16:31:40`** → bloqueado en MT5, operado en Python.
     - `2025-07-09`: `#702` cerró por SL en MT5 a las **`16:32:40`** → bloqueado en MT5, operado en Python.
     - `2025-08-28`: `#756` cerró por SL en MT5 a las **`16:30:40`** → bloqueado en MT5, operado en Python.
     - `2025-08-29` *(único trade sólo en MT5)*: consecuencia directa del anterior; el trade tomado por Python el `2025-08-28` seguía abierto el `2025-08-29 16:30`, bloqueando a Python pero dejando libre a MT5.
     - `2025-12-22`: `#894` cerró por SL en MT5 a las **`16:34:40`** → bloqueado en MT5, operado en Python.
     - `2026-01-14`: `#916` cerró por SL en MT5 a las **`16:31:40`** → bloqueado en MT5, operado en Python.

2. **Los `9` trades con desfase de vela M5 de salida (`607/616` iguales, `9` distintos):**
   - Causa técnica: en MT5 el trailing EMA 120 tiene un *throttle* por reloj (`each 300 s`, ej. modificaciones a `:20` o `:40` seg según cuándo se abrió/movió, más evaluación posible en la vela `16:35`), y los stops intravela se disparan por ticks M1 OHLC antes de que termine la vela M5. En casos fronterizos el precio toca la EMA justo al segundo `:40` de una barra o justo antes del reajuste de la barra siguiente (`2024-05-08` `17:08:20` vs `17:00`, `2024-05-30` `20:10:40` vs `20:00`, `2024-07-08` `17:38:40` vs `17:45`, `2024-09-26` `21:30:20` vs `21:55`, `2025-01-07` → `01-08 10:56:40` vs `11:00`, `2025-03-06` → `03-07 10:05:40 @ 20146.71` vs `04:15:00 @ 20183.34` donde `high=20183.598`, `2025-12-12` → `12-15 06:57:20` vs `07:30`, `2026-03-16` `22:42:40` vs `22:25`, `2026-08-26` → `08-27 08:12:20` vs `08:15`).

3. **Las `9` diferencias de salida `> 5.0` pts:** Son exactamente los **`8` gaps de apertura** detallados en la tabla del Punto 1 (MT5 llenó al SL; Python llenó al `open`) más `2025-03-06` (`20146.71` vs `20183.34` por el desfase de vela M5 de arriba). Las restantes variaciones `< 0.50` pts (`~144` trades entre `0.05` y `0.50` pts) provienen exclusivamente del redondeo de la EMA120 en los pasos de 300 s vs cierre exacto M5.

---

### Punto 6 — Verificación de gatillos de `QLB_K_XAUUSD_3x_speed_q4_turn.ex5` (Slots 0, 1 y 2)

1. **Slots 0 y 1 (`No verificable`):**
   - Tanto el docstring de [`qlb_k_xauusd_basket.py`](file:///C:/Users/nicoc/.gemini/antigravity/brain/79352924-80c3-409e-9be9-296eeef88676/scratch/wt_claude/edgelab/research/quantlab_mt5/qlb_k_xauusd_basket.py#L15-L18) como las pruebas en MT5 confirman que las condiciones booleanas de entrada están compiladas en bytecode nativo x64 dentro de `QLB_K_XAUUSD_3x_speed_q4_turn.ex5` y **no** son expuestas en logs ni en parámetros.
   - Específicamente, la fórmula de Python del Slot 0 (`EMA10 vs EMA50` + `ATR5/ATR20 >= 0.85`) y la del Slot 1 (`Close > Highest(High, 20)` + `EMA10/50`) **son aproximaciones inferidas y no pueden verificarse ni refutarse contra el `.ex5` mediante caja negra** (además, en el período de referencia ene–jun 2026, Slot 1 realizó `0` operaciones por el filtro Q4).
2. **Slot 2 (`turn_of_month_january_momentum_2` — `Parcialmente verificable por caja negra; gatillo exacto no verificable`):**
   - Lo **sí verificado** en los `37` trades de Slot 2 dentro de [`qlb_tester_trades_57.csv`](file:///C:/Users/nicoc/.gemini/antigravity/brain/79352924-80c3-409e-9be9-296eeef88676/scratch/wt_claude/docs/research/quantlab_mt5_eas_20261116/reference_data/qlb_tester_trades_57.csv): `37/37` son `BUY` (sólo largos), operan en `PERIOD_H1` al cierre/apertura de barra horaria, con `SL = 2.5 * ATR(14)_H1` y `TP = 5.0 * ATR(14)_H1` (`RR = 2.00`), y cierre temporal `TIME_CLOSE` a las `40` barras H1.
   - **Ventana temporal observada de Slot 2:** activo en los primeros días del mes (en ene–jun 2026 abrió en días `[1, 2, 3, 4, 5, 6, 7, 8, 9, 13]`: específicamente `01-02..01-13` en enero —efecto *January* extendido— y dentro de `día 1..8` entre febrero y junio: `02-02..02-06`, `03-02..03-05`, `04-01..04-08`, `05-01..05-06`, `06-01..06-04`).
   - **Comportamiento al estar plano dentro de la ventana:** en la mayoría de los cierres intra-ventana, Slot 2 vuelve a comprar casi inmediatamente en la barra H1 siguiente (`2026-01-05 03:56 → 04:00`, `14:58 → 15:00`, `01-06 04:46 → 05:00`, `11:27 → 12:00`, `17:25 → 18:00`, `01-08 10:00 → 11:00`, etc.), aunque omite horas puntuales (`2026-01-02 13:00`, `2026-02-02 17:00..02-03 01:00`, `2026-06-03 16:00..06-04 01:00`). La subcondición booleana exacta que filtra esas horas puntuales vive en código nativo x64 y **no es verificable** sin inventar reglas (por lo que `c[sig] > c[sig-1] or c[sig] > ema10[sig]` en [`qlb_k_xauusd_basket.py:131`](file:///C:/Users/nicoc/.gemini/antigravity/brain/79352924-80c3-409e-9be9-296eeef88676/scratch/wt_claude/edgelab/research/quantlab_mt5/qlb_k_xauusd_basket.py#L131) permanece como inferencia no confirmada).

---

### Punto 7 — Auditoría de zonas horarias en StrategyQuant X (Hallazgo H1)

Consultado directamente el servidor vivo de StrategyQuant X mediante `list_data(detail=true)` (`150` datasets en total):

- **`timezone="EST+07"` (`10` datasets — exactamente todos los `*_M1_dukas`):**
  `DJ_M1_dukas`, `EURJPY_M1_dukas`, `EURUSD_M1_dukas`, `GBPJPY_M1_dukas`, `GBPUSD_M1_dukas`, `NQ_M1_dukas`, `SP_M1_dukas`, `USDCHF_M1_dukas`, `USDJPY_M1_dukas`, `XAUUSD_M1_dukas` (`source="Dukascopy"`, `timeframe="M1"`, hasta `2026-10-01`).
- **`timezone="UTC"` (`35` datasets):**
  - Confirmados los **`6`** símbolos citados en el hallazgo H1: `DEUIDXEUR`, `EUSIDXEUR`, `GBRIDXGBP`, `JPNIDXJPY`, `LIGHTCMDUSD`, `USSC2000IDXUSD` (`source="Dukascopy"`, `timeframe="M1"`, hasta `2026-09-30`).
  - **Otros `11` símbolos Dukascopy M1 también en `"UTC"`:** `AUDUSD`, `BRENTCMDUSD`, `BUNDTREUR`, `COPPERCMDUSD`, `DOLLARIDXUSD`, `GASCMDUSD`, `NZDUSD`, `UKGILTTRGBP`, `USDCAD`, `USTBONDTRUSD`, `XAGUSD`.
  - Además en `"UTC"`: `10` índices `[[...]]` de `SQ Equity data` (`[[Dow Jones Industrial Average]]`, `[[Nasdaq 100]]`, `[[Nasdaq Biotechnology]]`, `[[Russell 1000]]`, `[[Russell 2000]]`, `[[Russell 3000]]`, `[[S&P 100 limited]]`, `[[S&P 100]]`, `[[S&P 500]]`, `[[S&P MidCap 400]]`), `7` archivos `NULO_*` (`source="File"`, excepto `NULO_EURUSD_M1_dukas_H1_s1` con `timezone=""`) y `PRUEBA_IMP`.
- **`timezone="Exchange"` (`104` datasets):**
  `@EW` (`SQ Futures data`, `M1`, `2009-01-02` → `2024-10-29`) y los `103` símbolos restantes de acciones individuales de `SQ Equity data`.

**Veredicto:** **Verificado al 100%.** La asimetría horaria observada en los archivos exportados de `edgelab-sqx-m1` / `edgelab-sqx-barras` refleja fielmente la configuración actual de los símbolos dentro de SQX (sólo `*_M1_dukas` están configurados en `EST+07`; todos los demás Dukascopy M1 están en `UTC`).

---

### Punto 8 — `FUNDEDSYNCSTACK` `stop_price` vs stop inicial (Hallazgo H2)

**Verificación en el código Python y en el IL original:**
1. En [`modulos_w_n_t.py`](file:///C:/Users/nicoc/.gemini/antigravity/brain/79352924-80c3-409e-9be9-296eeef88676/scratch/wt_claude/edgelab/research/fundedsyncstack/modulos_w_n_t.py#L1876-L2187) (exclusivamente en el módulo `T` / `run_t`; los demás módulos en `modulos_a1_a20_f_s.py`, `modulos_p_c_v_o.py` y `modulos_r_z_e_q.py` tienen stop estático):
   - Al entrar (`L1899–1901`), se asigna `active_stop_price = round_tick(entry_price - side * s_dist, tick_size)`.
   - En cada cierre de 15m (`L2182–2187`), si `close_r >= active_managed_stop_trigger_r`, muta `active_stop_price = round_tick(entry_price + side * risk_pts * active_managed_stop_lock_r, tick_size)` y marca `managed_stop_activated = True`.
   - Al registrar el cierre del trade (`L1876`, `L1928`, `L1952`), se escribe `stop_price=active_stop_price` (el stop **activo** al momento de salir, no el inicial).
2. **Contraste con la DLL C# original ([`mod_T_ftm.txt`](file:///C:/Users/nicoc/.gemini/antigravity/brain/79352924-80c3-409e-9be9-296eeef88676/scratch/wt_claude/docs/research/fundedsyncstack_20261115/il_por_modulo/mod_T_ftm.txt#L720)):**
   - El motor original (`FtmEngine`) almacena `activeInitialStopTicks` (`L720`), lo mantiene inmutable durante toda la operación para calcular el riesgo `1R` inicial (por ejemplo en `ManageConditionalExit1530` en `L1714`), mientras mueve el `StopOrder` vivo mediante `ChangeModuleStopFromNq(2)` (`L1645`).
   - En cambio, si un script de auditoría en EdgeLab calcula `1R = abs(entry_price - stop_price)` sobre la salida de `T` (como hace [`motor_cartera.py`](file:///C:/Users/nicoc/.gemini/antigravity/brain/79352924-80c3-409e-9be9-296eeef88676/scratch/wt_claude/edgelab/research/fundedsyncstack/motor_cartera.py#L2172-L2176) o los medidores en R), una vez que `T` mueve el stop a breakeven (`lock_r = 0.0` → `stop_price == entry_price`) o a ganancia positiva (`lock_r > 0`), `abs(entry_price - stop_price)` da `0` o un R artificialmente encogido.

**Propuesta concreta (sin cambiar resultados actuales ni romper el esquema existente):**
1. En `edgelab/research/fundedsyncstack/contracts.py`: añadir el campo opcional `initial_stop_price: float = float("nan")` al final de `TradeRecord` (y en `TRADE_COLUMNS` si los consumidores iteran por nombre, manteniendo intacta la semántica de `stop_price` para compatibilidad retroactiva).
2. En `modulos_w_n_t.py` (`run_t`): guardar `initial_stop_price = active_stop_price` justo tras la línea `L1901` al entrar y pasarlo en los 3 llamados a `_make_trade_record` (`L1876`, `L1928`, `L1952`), dejando `initial_stop_price = stop_price` en los demás módulos estáticos. En `motor_cartera.py:2172-2176`, usar `initial_stop_price` cuando sea finito para calcular `stop_dist` de sizing/métricas en `1R` inicial. *(Nota: por instrucción de no alterar código ni resultados fuera de pedido explícito, esta propuesta queda documentada aquí sin editar `fundedsyncstack/`.)*
