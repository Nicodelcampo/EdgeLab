# Catálogo Cuantitativo Post-Fricción: 14 Estrategias Finalistas (Concretum, Quantpedia, QuantifiedStrategies, QuantConnect & TradingView OS)

Estado: VIGENTE — segunda ola de recolección guiada por la evidencia de EdgeLab (`T-REGIMEN` + `R AtrPhase` ambos `REGIMEN_ROBUSTO`, `ROBOQUANT` bruto vivo sin neto en stops chicos, `OPTION-ALPHA` refutada, `AUDITORIA_ANTIGRAVITY_20261119.md`).

---

## 1. Los 7 Requisitos Estrictos de Admisión

Para evitar repetir las `>140` variantes de indicadores técnicos puros ya refutadas por fricción o falta de señal en EdgeLab:

1. **Baja fricción estructural (`<= 0,04 R`, techo `0,06 R`):** stops amplios (`>= 0,40–1,75 × ATR20_D1`) u horizonte de varias horas a múltiples días (`1–10d`). Quedan fuera scalping `M1/M3/M5` y micro-trailing.
2. **Mecanismo económico real o flujo forzado (categorías A–E):**
   - **(A)** Flujos institucionales intradía / expansión de volatilidad / VWAP (Concretum/Zarattini 2025–2026, Baltussen 2021, Gao 2018).
   - **(B)** Futuros de Oro (`GC`) — sesgos Asia / Londres AM Fix → COMEX NY, gaps overnight y tendencia (descorrelacionado del flujo 0DTE de renta variable).
   - **(C)** Régimen de Volatilidad (`VIX`, `VIX9D`, `VXN`, `GVZ`, pendiente `VIX9D/VIX`) operando `ES/NQ/GC` con `cboe_volatility_daily.parquet`.
   - **(D)** Calendario institucional y eventos fijos (*Pre-FOMC Drift*, *Turnaround Tuesday*, *Turn-of-Month*, *OPEX Friday*) con `us_market_events_calendar_2006_2026.parquet`.
   - **(E)** Reversión a la media multi-día / swing filtrada por tendencia o volatilidad (`IBS`, Connors *Double Seven*, rotación `ES/GC`).
3. **Baja complejidad (`<= 4` perillas físicas)** sin fechas excluidas hardcodeadas ni *repainting*.
4. **Unidades invariantes al precio nominal (`%`, `ATR`, `sigma` implícita, `K36`/`K52`).**
5. **Potencia alcanzable (`K49`)** en canasta `ES`, `NQ`, `YM`, `GC`.
6. **Baja correlación con señales ya activas (`T`, `R`, `RQ5`, `RQ6`, `Dual Thrust`).**
7. **Causalidad estricta (`K48`) y control pareado natural.**

---

## 2. Tabla Resumen — Las 14 Estrategias Finalistas

| # | Estrategia | Mec. | Carril | Instrumentos | Fuente Principal |
|---:|---|---|---|---|---|
| 1 | **Daily IBS Mean Reversion + Filtro Régimen VIX** | E + C | Carril 2 (Swing 1–5d) | `ES`, `NQ`, `YM`, `RTY` (NO `GC`) | QuantifiedStrategies |
| 2 | **Larry Connors' Double Seven (Trend-Filtered 7D MR)** | E + B | Carril 2 (Swing 2–10d) | `ES`, `NQ`, `YM`, `RTY`, **`GC`** | Connors (2010) / QS |
| 3 | **Concretum Open-Centered ATR-Band + Asymmetric Overnight Long** | A | Carril 1/2 Híbrido | `ES`, `NQ`, `YM` | Concretum Group (Mar 2026) |
| 4 | **NY VIX9D/VIX Channel Trend (US Futures Day Trade)** | A + C | **Carril 1 (`FM1`)** | `ES`, `NQ`, `YM`, `GC` (`GVZ`) | TradingView OS (`exlux`, Pine v6) |
| 5 | **Turnaround Tuesday (IBS-Conditioned Monday Overreaction)** | D + E | Carril 2 (Swing 1–4d) | `ES`, `NQ`, `YM`, `RTY` | Larry Williams / QS |
| 6 | **Turn-of-the-Month (Ultimo) Institutional Cashflow Drift** | D | Carril 2 (Multi-día 7d) | `ES`, `NQ`, `YM`, `RTY` (NO `GC`) | Lakonishok-Smidt / QS / QC |
| 7 | **Dual eVRP (`VIX - RV10`) + Term Structure (`VIX9D/VIX`) Overlay** | C | Carril 2 (Régimen) | `ES`, `NQ` (+ rotación `GC`) | Concretum (SSRN 5316487, 2025) |
| 8 | **High-VIX Extreme Spike (`BB 2σ`) & Rolling 2Y Percentile (`P80–P90`)** | C | Carril 2 (Swing 2–10d) | `ES`, `NQ`, `YM` (`VXN` en `NQ`) | QC / QS / Bansal-Stivers (2023) |
| 9 | **VIX-Conditioned Pre-FOMC Announcement Relief Drift** | D + C | Carril 1/2 Evento | `ES`, `NQ`, `YM` (test `GC`) | Lucca-Moench / Martello-Ribeiro / QP |
| 10 | **Gold (`GC`) Overnight-Gap Breakout Continuation (COMEX)** | B | **Carril 1 (`FM5`)** / Carril 2 | **`GC`** | QS + Auditoría OHLC Quantpedia |
| 11 | **Dynamic Breakout II (Adaptive Volatility-Lookback Breakout)** | B + A | Carril 2 (Swing/Trend) | **`GC`**, `ES`, `NQ` | George Pruitt / QuantConnect |
| 12 | **Intermarket `ES/GC` Relative-Strength Macro Rotation** | E + B | Carril 2 (Macro Swing) | **`ES` + `GC`** | QuantifiedStrategies / Quantpedia |
| 13 | **Multi-VIX Z-Score Normalized Volatility-Crush Momentum** | C | Carril 2 (Swing 1–7d) | `ES`, `NQ` | TradingView OS (`EdgeTools`, Pine v6) |
| 14 | **Asian-Range to London/COMEX Session Breakout (`GC`)** | B | **Carril 1 (`FM6`)** | **`GC`** | TradingView OS (`xsixs`, Pine v5) |

---

## 3. Especificación Completa de las 14 Finalistas

### 1. Daily IBS (Internal Bar Strength) Mean Reversion + Filtro Régimen VIX
- **Fuente:** QuantifiedStrategies (`https://www.quantifiedstrategies.com/ibs-internal-bar-strength-indicator-strategies/`).
- **Carril e instrumentos:** Carril 2 (Multi-día 1–5d) en `ES`, `NQ`, `YM`, `RTY` (**excluir `GC`**). Intrasesión adaptada en `FM3`.
- **Reglas exactas (`ibs_entry=0,20`, `ibs_exit=0,80`, `vix_ma=100`):**
  - En barra diaria RTH (`09:30–16:00 ET`), `IBS_t = (Close_t - Low_t) / max(High_t - Low_t, tick)`.
  - **Long** al cierre RTH (`15:55 ET`) si `IBS_t < 0,20` **y** `VIX_{t-1} > SMA(VIX, 100)_{t-1}` (`VXN` en `NQ`).
  - **Stop amplio:** `1,50 × ATR20_D1`. **Salida:** cierre RTH del primer día con `IBS_t > 0,80` (o `Close_t > High_{t-1}`), máx `10` días.
  - **Control pareado:** comprar fuerza (`IBS_t > 0,80`).
- **Evidencia (1993–2026):** SPY `+0,41%/trade`, PF `1,90`, `68%` WR (`919` trades); con `VIX > SMA100`: `+0,53%/trade`, PF `2,19`. QQQ: `+0,56%/trade`, CAGR `16,6%`. *Alerta QS:* entrar al Open siguiente en vez de `15:55 ET` reduce el retorno (`0,41% → 0,31%`).

### 2. Larry Connors' Double Seven (Trend-Filtered 7D Swing MR — incluye `GC`)
- **Fuente:** Connors & Alvarez (2010), auditado 2000–2026 en QS (`https://www.quantifiedstrategies.com/larry-connors-double-seven-strategy-does-it-still-work/`).
- **Reglas exactas (`trend_len=200`, `lookback=7`, `stop_atr=1,75`):** Long al cierre RTH si `Close_t > SMA(Close, 200)` **y** `Close_t <= min(Close_{t-6..t})`. Stop `1,75 × ATR20_D1`. Salida cuando `Close_t >= max(Close_{t-6..t})`. **Control pareado:** mínimo de 7d debajo de `SMA200`.
- **Evidencia (2000–2026 QS):** SPY `+1,00%/trade` PF `2,41`; QQQ `+1,32%/trade` PF `2,11`; **GLD (`GC`) `+0,78%/trade` PF `1,91`**; DIA `+0,68%` PF `1,73`; IWM `+0,84%` PF `1,43`. Baja frecuencia (~6–8/año/activo).

### 3. Concretum Open-Centered ATR-Band + Asymmetric Overnight Long Hold
- **Fuente:** Concretum Group (Pagani & Zarattini, mar 2026, `https://concretumgroup.com/breaking-the-rules-of-intraday-trading/` y `https://concretumgroup.com/conditional-profitability-of-intraday-shorts/`).
- **Reglas exactas (`atr_len=14`, `k_band=0,50`):** ancla `Open_0930 ± 0,50 × ATR14_D1` (causal `t-1`). Ruptura `M5/M15` (`09:35–15:00 ET`) entra en dirección del quiebre con **SL en `Open_0930`** (`>= 0,50 × ATR14_D1`). **Short** cierra EOD `15:59 ET` (sin filtrar por VIX/SMA200, dado `p=0,91` de Concretum en shorts intradía); **Long** en versión híbrida Carril 2 mantiene overnight hasta `09:31 ET` siguiente (SL nocturno `1,25 × ATR20_D1`). Intrasesión implementada en **`FM2` / `FM2N`**.
- **Evidencia (SPY 2006–2026 bruto):** EOD simétrico CAGR `14,1%` Sharpe `0,88` DD `-25,6%` → Asimétrico Long Overnight CAGR `~20%` Sharpe `~1,07` DD `-34,1%` con los mismos trades y costos.

### 4. NY VIX9D/VIX Channel Trend (`FM1` — Open-Source Pine v6)
- **Fuente:** `exlux` (`https://www.tradingview.com/script/TlOcVraF-NY-VIX-Channel-Trend-US-Futures-Day-Trade-Strategy/`, Nov 2025, 148 líneas).
- **Reglas exactas (`window_min=30`, `vix_factor_sl=1,0`, `vix_factor_tp=1,0`, `exit_cut_min=30`):** usa `VIX9D_{t-1}` (fallback `VIX_{t-1}`; `VXN` en `NQ`; `GVZ` en `GC`). Calcula movimiento implícito diario `sigma_d = (IV_{t-1} / 100) / sqrt(252)` y fija bandas en `Open_0930 × (1 ± sigma_d)`. A las `10:00 ET` (`window_min = 30`), entra **Long** si `Close_1000 > Open_0930` y **Short** si `< Open_0930` (1 trade/sesión), con `SL = TP = max(sigma_d × Open_0930, 0,50 × ATR20_D1)` y cierre máximo a las `15:30 ET`. **Control pareado:** fade contra el desplazamiento de los primeros `30m`. Implementada en **`FM1` / `FM1N`**.

### 5. Turnaround Tuesday (IBS-Conditioned Monday Overreaction Reversal)
- **Fuente:** Larry Williams / QS (`https://www.quantifiedstrategies.com/turnaround-tuesday-strategy/`).
- **Reglas exactas:** Solo en **Lunes** (`DayOfWeek == Lunes`, sin `early_close`). Long al cierre RTH (`15:55 ET`) si `Close_Mon < Close_Fri` y `IBS_Mon < 0,50` (o variante alta convicción `Close_Mon < Open_Mon` e `IBS_Mon < 0,20`). SL `1,50 × ATR20_D1`. Salida cuando `Close_t > High_{t-1}` o máx `4` días (viernes). **Control pareado:** lunes alcista (`IBS > 0,80`). Intrasesión adaptada en **`FM4` / `FM4N`**.
- **Evidencia (SPY 1993–2026):** `495` trades, `+0,46%/trade`, `69%` WR, CAGR `7,0%` estando sólo `17%` del tiempo invertido.

### 6. Turn-of-the-Month (Ultimo) Institutional Cashflow Drift
- **Fuente:** Lakonishok & Smidt (1988); QS (`https://www.quantifiedstrategies.com/turn-of-the-month-trading-strategy/`); QuantConnect Library.
- **Instrumentos:** `ES`, `NQ`, `YM`, `RTY` (**NO `GC`**, refutado en QS `2,2%` vs `7,6%` B&H).
- **Reglas exactas:** Long al cierre del 5.º último día hábil del mes (`T-5`, o `T-1` variante QC) hasta cierre del 3.er día hábil del mes nuevo (`T+3`), SL catástrofe `2,00 × ATR20_D1`. **Control:** días del medio del mes (`T+4 → T-6`). Evidencia S&P 500 1960–2026: CAGR `7,11%` (vs `6,95%` B&H) con mitad de drawdown (`-27%` vs `-56%`).

### 7. Dual eVRP (`VIX - RV10`) + Term Structure (`VIX9D/VIX`) Regime Overlay
- **Fuente:** Zarattini, Aziz & Mele (2025, SSRN `5316487`, código Python abierto en `https://concretumgroup.com/automating-a-vix-volatility-strategy-with-python-and-interactive-brokers/`).
- **Reglas exactas:** `eRV10 = stdev(log_ret, 10) × sqrt(252) × 100`, `eVRP = VIX - eRV10`, `Contango = (VIX9D / VIX) < 1,0`. Estados: (1) `eVRP > 0 & Contango` → Long 100%; (2) `eVRP <= 0 & Contango` → Long 50%; (3) `eVRP <= 0 & Backwardation` → Defensivo (Cash o rotación `GC`); (4) `eVRP > 0 & Backwardation` → Cash 0%. Paper original 2008–2025: CAGR `16,3%`, Sharpe `1,00`, Sortino `1,67`.

### 8. High-VIX Extreme Spike (`BB 2σ`) & Rolling 2Y Percentile (`P80–P90`)
- **Fuentes:** QuantConnect (`https://www.quantconnect.com/research/15380/vix-predicts-stock-index-returns/p1`); Bansal & Stivers 2023 via Quantpedia (`https://quantpedia.com/time-varying-equity-premia-with-a-high-vix-threshold/`); QS (`https://www.quantifiedstrategies.com/using-vix-to-trade-spy-and-sp-500/`).
- **Reglas exactas:**
  - *Variante A (QS BB 2σ):* Long en `ES`/`NQ` al cierre cuando `VIX > SMA(VIX, 20) + 2,0 × Std(VIX, 20)` (`VXN` para `NQ`), SL `2,00 × ATR20_D1`, salida tras `2` cierres alcistas consecutivos (`Close_t > Close_{t-1} > Close_{t-2}`). Evidencia QS `k=2,0`: `75,7%` WR, `+0,93%/trade`; `k=2,5`: `84%` WR, `+1,44%/trade`.
  - *Variante B (Bansal-Stivers):* régimen Long cuando `VIX > Percentil_80(504d)` causal vs baja vol `< P10(504d)`. Evaluada intrasesión en **`FM7`**.

### 9. VIX-Conditioned Pre-FOMC Announcement Relief Drift
- **Fuentes:** Lucca & Moench (2015); Martello & Ribeiro (2018); Quantpedia (`https://quantpedia.com/fomc-equity-drift-occurs-in-periods-of-high-uncertainty/`).
- **Reglas exactas (`us_market_events_calendar_2006_2026.parquet` + CBOE):** sólo cuando `days_to_next_fomc == 1` **y** `VIX_{t-1} > median(VIX, 252d)_{t-1}`: Long a las `14:00 ET` de `FOMC-1` (o `09:30 ET` del día `is_fomc_day`) y salida estricta a las `13:55 ET` del día FOMC (**nunca** cruzar las `14:00 ET`). **Evidencia:** `+109 bps` en IV > mediana vs `+9,7 bps` en IV <= mediana; sin filtro y cruzando el comunicado, QuantConnect OOS dio Sharpe `-0,40`.

### 10. Gold (`GC`) Overnight-Gap Breakout Continuation (`FM5`)
- **Fuentes:** QuantifiedStrategies (`https://www.quantifiedstrategies.com/when-gold-gaps-up-or-down/` y `https://www.quantifiedstrategies.com/gold-overnight-trading-strategy/`); auditoría OHLC Quantpedia feb 2025 (`https://quantpedia.com/dangers-of-relying-on-ohlc-prices-the-case-of-overnight-drift-in-gdx-etf/`).
- **Reglas exactas:** en **`GC`**, evaluar a `09:31 ET` (evitar artefacto de subasta de minuto `:30` advertido por Quantpedia): si `Open_0931 > max(High_{t-5..t-1})` **y** `Gap >= 1,5 × SMA(|Gap|, 25)` → Long `GC` con SL `0,75–1,00 × ATR20_D1`, salida `16:00 ET` (Carril 1 **`FM5`**) o Open siguiente (Carril 2). **Evidencia (GLD 2006–2026):** `151` trades, `60,3%` WR, `+0,17%/trade` RTH (`+0,29%/trade` hasta Open siguiente). **Control pareado:** Short en gap bajista simétrico (`FM5N`).

### 11. George Pruitt's Dynamic Breakout II (Adaptive Volatility-Lookback)
- **Fuente:** QuantConnect Library (`https://www.quantconnect.com/research/15373/the-dynamic-breakout-ii-strategy/p1`).
- **Reglas exactas:** en `GC` (prioridad) y `ES`/`NQ`, `lookback_t = clamp(round(lookback_{t-1} × (1 + deltaVol30)), 20, 60)`. Entra al cierre diario por fuera de `BB(lookback_t, 2,0)` **y** canal Donchian `lookback_t`; SL `1,50 × ATR20_D1`; salida al cruzar `SMA(Close, lookback_t)`.

### 12. Intermarket `ES/GC` Relative-Strength Macro Rotation
- **Fuentes:** QS (`https://www.quantifiedstrategies.com/rotation-strategy-in-gold-and-sp500/`); Quantpedia ene 2026 (`https://quantpedia.com/cross-asset-price-based-regimes-for-gold/`).
- **Reglas exactas:** razón `Ratio_t = Close_ES / Close_GC`. Rebalanceo mensual: Long 100% `ES` si `Ratio_t > SMA(Ratio, 20 meses)`; si `<=`, Long 100% `GC`. Evidencia 1985–2020: CAGR `9,9%`, Max DD `-22%` (mitad del S&P 500), contribución ~50/50 entre `ES` y `GC`.

### 13. Multi-VIX Z-Score Normalized Volatility-Crush Momentum (`FM7N` / Open-Source Pine v6)
- **Fuente:** `EdgeTools` (`https://www.tradingview.com/script/6ZkpMLDe-Z-Score-Normalized-VIX-Strategy/`, abr 2025, `ES1!`).
- **Reglas exactas (`zscore_length=6`, `threshold=1,0`):** promedio de z-scores a 6 días sobre `VIX` + `VIX9D` (o `VXN` + `VIX9D` en `NQ`). Long `ES`/`NQ` cuando `combined_z < -1,0` (compresión que dispara compras *vanna/vol-control*), SL `1,25 × ATR20_D1`, salida cuando `combined_z > -1,0`.

### 14. Asian-Range to London/COMEX Session Breakout para Oro (`GC`, `FM6`)
- **Fuente:** `xsixs` Pine v5 Open-Source (`https://www.tradingview.com/script/Fh42LHOM-London-BreakOut-Classic/`, 961 boosts) con filtro de compresión y piso ATR de EdgeLab.
- **Reglas exactas:** caja asiática/pre-COMEX (`05:00–08:00 ET` en índices / `00:00–06:55 UTC` en `GC`, cubriendo Asia → LBMA AM Fix `05:30 ET`), filtrada a compresión `0,15 × ATR20_D1 <= BoxRange <= 0,60 × ATR20_D1`. Ruptura `15m` en Londres/NY (`08:15–13:30 ET`) con SL `max(|Entry - BoxMid|, 0,50 × ATR20_D1)`, TP `1,5R`, flatten cierre RTH. Implementada en **`FM6` / `FM6N`**.

---

## 4. Anexo Crítico & Descartes Explícitos

1. **Last-Half-Hour Momentum (Baltussen et al. 2021 / QC `Intraday ETF Momentum`):** incondicional en QC 2015–2020 dio Sharpe `-0,628`, pero bajo estrés extremo (`Crash 2020`) dio Sharpe **`+1,452`**. En **`FM8`** se implementa estrictamente condicionado a desplazamiento severo (`|Close_1530 - Open_0930| >= 0,75 × ATR20_D1`, contra control `FM8N` día calmo).
2. **Asimetría OPEX Friday (`is_monthly_opex`):** el viernes de OPEX mensual (Jueves Close → Viernes Close) acumuló **`-23,55%` compuesto** en `361` vencimientos (viento en contra intradía RTH por *gamma unwind*; útil como filtro `no_opex` en análisis secundario).
3. **Descartes explícitos:** Concretum `5-min ORB` (stop `0,05 × ATR14_D1`, muere por fricción), Pre-FOMC sin filtro VIX atravesando `14:00 ET` (Sharpe `-0,40`), `IBS` y `Turn-of-Month` en Oro `GC` (refutados en QS), y deriva `02:00–03:00 ET` de Boyarchenko (desaparecida post-2021).
4. **Necesidad arquitectónica de Carril 2:** `11` de las `14` finalistas son estrategias multi-día / overnight / calendario con fricción `< 0,01 R`. Para medirlas sin el corte diario `GAP_S = 1800 s` de `ejecucion.py`, se propone construir como siguiente paso un **runner liviano de Carril 2** evaluando directamente sobre marcas causales diarias (`15:55 ET` / `09:31 ET`) de `M1NT8` + `cboe_volatility_daily.parquet` + `us_market_events_calendar_2006_2026.parquet`.
