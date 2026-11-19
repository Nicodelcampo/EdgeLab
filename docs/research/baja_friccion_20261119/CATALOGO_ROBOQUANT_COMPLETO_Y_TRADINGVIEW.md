# Catálogo Completo Roboquant (32/32 Gratuitas + Auditoría de Código Rust) & 11 Estrategias Open-Source de TradingView (Baja Fricción)

Estado: VIGENTE — relevamiento exhaustivo realizado tras los hallazgos de `OPTION-ALPHA` (refutada), `ROBOQUANT` (señal bruta real en `RQ2`/`RQ5`/`RQ6`), `FRICCION-RQ` (sesgo `K52` de puntos fijos) y `T-REGIMEN` (`REGIMEN_ROBUSTO`).
- **Criterios de filtrado de esta recolección:**
  1. **Descartado:** bots de Option Alpha (`NO_REPETIR` en futuros), scalping M1 con micro-stops (`frR > 0,08 R`), martingalas/DCA sin stop y scripts cerrados (*invite-only*).
  2. **Priorizado:** stops estructurales amplios (`>= 0,50–1,0 × ATR20_D1` para lograr fricción canónica `<= 0,04–0,06 R`), marcos `15m–1D`, estacionalidad/calendario, bandas de volatilidad normalizadas, pullbacks a VWAP con filtro de *chop* y rupturas de baja resistencia (*Time-at-Price* / volumen).

---

## Parte A — Roboquant Marketplace: Cobertura 100 % Gratuita (`32/32` Estrategias)

En el primer relevamiento sólo figuraban `18` plantillas visibles; al abrir los listados completos (*"See all"*) quedan relevadas las **`32/32` estrategias gratuitas** (`11` *Free from creators* + `21` *Roboquant strategies* oficiales), sumando **13 estrategias nuevas** además de las auditadas por código fuente.

### A.1. Las 13 Estrategias NUEVAS de Roboquant (Oficiales / Open-Source)

#### Prioridad Alta para EdgeLab (stops amplios / 15m–1H / estructurales)

| Estrategia Roboquant | Símbolo / TF Showcase | Stats Showcase | Lógica Exacta y Parámetros |
|---|---|---|---|
| **Charles Monger Investment Strategy by Shujat** | `ES 1H` (`2020-01 – 2026-09`) | Return `+1115.5%` · PF `1.32` · DD `55.5%` · `449` trades | **Banda de histéresis con 2 EMAs de `200` barras (`charles_monger.rq`):** `ema_top = EMA(high, 200)`, `ema_bot = EMA(close, 200)`. Máquina de estados `close < ema_bot => Red`, `close > ema_top => Green`, interior `Gray` (sin cambios). Sólo opera flips completos `Red ↔ Green` (si salta el SL, espera el próximo flip de régimen). Showcase: `trade_mode=Long only`, `SL = 1.0%` (~60 pts ES). *(Carril 2 multi-día / swing).* |
| **4H FU Retest** (`BF3`) | `MES 15m` (`2020-01 – 2026-09`) | Return `+107.9%` · PF `1.37` · DD `37.7%` · `158` trades | **Barrido pre-NY (4H `06:00–10:00` vs `02:00–06:00 ET`) + Retest:** setup alcista cuando la segunda ventana barre bajo el mínimo de la primera y cierra arriba de su máximo/punto medio (espejo bajista). Entre `10:00` y `14:00 ET`, primer retest a la mitad de la caja, máx 1 trade/día, **stop amplio `4.0 × ATR(14)`**, target `0.5 × stop` (`2.0 × ATR`). |
| **Previous Day Extreme** (`BF4`) | `NQ 15m` (`2024-09 – 2026-09`) | Return `+128.7%` · PF `1.27` · DD `22.6%` · `495` trades | **Bandas extremas del `25 %` del rango CME previo (`18:00 ET` rollover):** cuando entra en el cuartil inferior (`[Prev_Lo, Prev_Lo + 0.25·R]`) y confirma cierre 15m sobre el High de la barra previa → Largo (espejo Corto en cuartil superior). Showcase: **stop `2.5 × ATR(14)`**, target `2.7 × ATR(14)`, 1 trade/sesión. |
| **M30 ORB + M5 Breakout** | `MNQ 5m` (`2023-11 – 2026-10`) | Return `+345.7%` · PF `1.22` · DD `33.7%` · `706` trades | Rango `09:30–10:00 ET` en `5m`, primer cierre fuera con **filtro de régimen Daily ATR** y `RVOL >= 1.4 × SMA(vol, 20)`. Stop amplio `3.0 × ATR(14)` (5m), TP `1.5R`, flatten `15:00 ET`. |
| **The Double Helix** | `MNQ 1H` (`2020-01 – 2026-09`) | Return `+14.0%` · PF `1.14` · DD `9.8%` · `810` trades | Canal 3 EMAs en 1H (`EMA(H, 44)`, `EMA(L, 44)`, `EMA(C, 200)`). Entrada `11:30–14:00 ET` cuando cierra fuera del canal alineado con `EMA(200)`, trailing stop en la banda opuesta hasta flip (mantiene overnight). *(Carril 2 multi-día).* |
| **PDH/PDL Sweep Fade** | `MNQ 5m` (`2024-09 – 2026-09`) | Return `+217.6%` · PF `1.41` · DD `37.0%` · `245` trades | Ruptura intradía (`09:45–13:00 ET`) de `PDH`/`PDL` que cierra de vuelta adentro; **stop y TP en ATR Diario (`0.3× Daily ATR` SL, `0.1× Daily ATR` TP)**. |
| **MNQ Range Breakout** | `MNQ 15m` (`2025-09 – 2026-09`) | Return `+56.5%` · PF `1.35` · DD `8.8%` · `356` trades | Caja overnight de 15m (`01:00 ET` Asia) con filtro de ancho `<= 0.2%`, TP `3.9R`, y 1 tiro inverso (`2.9R`) si salta SL. |
| **S/R Zones + Anchored VWAP** | `MNQ 1H` (`2023-01 – 2026-09`) | Return `+240.7%` · PF `1.65` · DD `31.3%` · `100` trades | Pivots `10/4` validados por `>= 1× ATR(19)`, rebote en soporte bajo VWAP semanal anclado (en EdgeLab requiere reemplazar stop fijo 5 pts por ATR amplio). |

#### Restantes 5 estrategias nuevas de Roboquant (baja prioridad / descartables en EdgeLab)
9. **Continuation Havoc** (`MNQ 15m`, PF `1.10`, `2.520` trades): ruptura de vela previa en `09:30–10:30 ET`, stop muy corto.
10. **S&R Sweep** (`NQ 5m`, PF `1.25`, `977` trades): sweep pivot `3/3` + `EMA(30)` (parecida a QFL/Sweep M5).
11. **Williams %R Long** (`ES 3m`, PF `1.07`, `20.663` trades): frecuencia excesiva en `3m`.
12. **DTR Range Breakout Return** (`MNQ 1m`, PF `1.23`): descartada (M1 pre-market).
13. **Scarface ORB** (`MNQ 1m`, PF `1.35`): descartada (M1 ORB 5m).

---

### A.2. Auditoría Crítica del Código Fuente Rust (`.rq` + `.set`) de las 6 Estrategias Top de Roboquant

La inspección directa del código fuente abierto reveló **diferencias críticas respecto a las descripciones de catálogo y presets** que explican resultados inflados o permiten rescatar la señal académica pura:

1. **`Noise-Band Intraday Momentum — MNQ`** (`noise_band_momentum.rq`, autor `sird`):
   - **Hallazgo crítico:** El showcase (`+1384%`, Sharpe `2.09`, PF `1.78`) **NO** corre el paper de Zarattini et al. (2024): sus defaults activan `exit_mode = 2` (**trailing tick-a-tick de `6.0` puntos** con `qty = 50` MNQ y `exit_at_session_end = false`) y traen **2 fechas malas excluidas a mano (`skip_date_1 = 20230106`, `skip_date_2 = 20230517`)**.
   - **Fórmula real del paper dentro del código (`exit_mode = 0`):** la banda es **normalizada en `%`** (`sigma(t) = mean_{60d} |P(t) - Open| / Open`) y **ajustada por gap nocturno**: `Upper = max(Open, PrevClose) * (1 + sigma(t))`, `Lower = min(Open, PrevClose) * (1 - sigma(t))`, con entrada confirmada por `VWAP` en slots de `30m`. Esta versión causal y normalizada (con stop amplio `0.75 × ATR20`) es **`BF2`**.
2. **`MNQ Midday Continuation`** (`mnq_midday_continuation.rq`, autor `sird`, **`BF1`**):
   - Basada en **Gao, Han, Li & Zhou (2018)** y **Baltussen, Da, Lammers & Martens (2021)** en sólo `40` líneas limpias.
   - `ADR20 = SMA(rth_hi - rth_lo, 20)` sobre sesiones RTH completadas. A las `10:30 ET`, si `|Close_1030 - Open_930| >= 0.20 × ADR20`, entra a favor del movimiento con **stop amplio `1.0 × ADR20`** y mantiene hasta cierre RTH (`15:55 ET`). Sin curvas ni parámetros sobreajustados.
3. **`Friday Range Revisit - Monday Short`** (`friday_range_monday_short.rq` + `Tom.set`, Oficial):
   - **Hallazgo crítico:** el `ATR(14)` del código está calculado en **marco diario (`timeframe("1D")`)**, no en barras de `5m`! Por eso `0.10 × ATR(14)` equivale a `~35–50 pts` en `NQ` y `1.0 × ATR(14)` apunta a un R:R `10:1`.
4. **`T-Mean Reversion`** (`t_mean_reversion.rq` + `T-Reversion_RQ.set`):
   - **Hallazgo crítico:** el tracker diario en UTC actualiza `last_friday_red` al cerrar el día UTC del viernes (`date_num != cur_day`), pero el preset `T-Reversion_RQ.set` entra el **Viernes `18:00 UTC`** antes de ese cierre, por lo que en el showcase evalúa el viernes de la **semana anterior (`t - 7 días`)**, no el viernes recién terminado.
5. **`Sigma Breakout`** (`sigma_breakout.rq`): `30m` RTH (`09:30–16:00 ET`), `sigma(slot)` en **puntos absolutos** de los últimos `N = 2` días × `1.5`, sin ajuste de gap, sin stop fijo, voltea al cruzar banda opuesta. *(Ya capturada en esencia por `RQ5`/`BF2`).*
6. **`Trend Day Pullback`** (`topstep50k_r3_trend_pullback.rq`): desde `10:30 ET` exige lado de `VWAP` y `range_pos >= 0.50`, pullback `<= 1.25× ATR(14, 5m)`, SL `1.0× ATR(14, 5m)` (tope `80 pts`), `2R`, cutoff `12:30 ET`. *(Ya evaluada en `RQ6`).*

---

## Parte B — 11 Estrategias Open-Source de TradingView (Editors' Picks, TASC & Top Pine v4–v6)

Todas verificadas con **código Pine abierto** y seleccionadas por diversidad estructural (cero clones de RSI simple, SuperTrend ni EMA cross):

| # | Estrategia / Autor / URL | Marco y Familia | Reglas Exactas (Entrada, Filtros, Stop, Salida) | Carril EdgeLab |
|---:|---|---|---|---|
| **1** | **TASC 2026.06 One Percent A Week - Adaptive** (`PineCodersTASC` / Dion Kurczek) · [Script](https://www.tradingview.com/script/CSGmHoik-TASC-2026-06-One-Percent-A-Week-Adaptive/) | `15m–1D` · Estacionalidad semanal adaptativa | Largo al open del **Lunes** (`entry`); SL `-1.5%` (en 3x → escalar a ATR/0.5% en NQ); TP inicial `+7%` ajustado al cierre del Lunes (`> +0.3%` → amplía × `1.011`; `<= 0%` → baja a `+2.5%`); salida temprana al cierre del **Martes** si el Lunes subió `> 2%` y el total está `< 3%`; cierre el Viernes RTH. | **Carril 2 (Multi-día)** |
| **2** | **TASC 2025.05 Trading The Channel** (`PineCodersTASC` / Perry Kaufman) · [Script](https://www.tradingview.com/script/nTdxANi4-TASC-2025-05-Trading-The-Channel/) | `4H–1D` · Canal Regresión Lineal + ATR Sizing | Canal lineal `N=40`: `linreg`, `slope`, envolvente máx `t` / `b` (`upper/lower`). 3 reglas independientes: (T1) cambio de signo de `slope`; (T2) breakout `> upper` / `< lower`; (T3) mean-reversion en quintiles extremos `20%` del canal a favor de pendiente. Sizing `25000 / (ATR20 * pointvalue)`. | **Carril 2 (Multi-día)** |
| **3** | **TASC 2024.10 Adaptive Oscillator Threshold** (`PineCodersTASC` / Francesco P. Bufi) · [Script](https://www.tradingview.com/script/zDP76aFT-TASC-2024-10-Adaptive-Oscillator-Threshold/) | `4H–1D` · Mean Reversion adaptativa sin *falling knives* | Indicador `BAT = clamp(((linreg(C,8) - C[8])/9) / stdev(C,8), -0.5, 0.5)`. Umbral dinámico `thrs = 84 * BAT`. Compra Largo si `RSI(C, 2) < thrs` (cuando `slope <= 0`, `thrs <= 0` y bloquea compras en caída!). Salida temporal `28` barras o SL swing `2–3× ATR`. | **Carril 2 (Multi-día)** |
| **4** | **TASC 2026.07 Risk-On, Risk-Off, Or Caution** (`PineCodersTASC` / Di Prima & Baruffa) · [Script](https://www.tradingview.com/script/wu1VhNpf-TASC-2026-07-Risk-On-Risk-Off-Or-Caution/) | `1D` (rebalanceo semanal) · Régimen Macro | Score diario `s1 + s2 + s3` (`[0..3]`): `SPX > SMA(200)`, `VIX/VIX3M < 1.0`, `zscore(HYG/IEF, 100) > -2.0`. `3` = Risk-On `100%`, `2` = Caution `50%`, `0–1` = Risk-Off `0%`. Útil como **overlay macro** de EdgeLab usando nuestros parquets CBOE. | **Carril 2 (Overlay Macro)** |
| **5** | **Channel Breakout 100/50 + Daily ATR Stop + R-Ladder** (`Algonney`, 54 boosts) · [Script](https://www.tradingview.com/script/fB8YZHDd-Channel-Breakout-100-50-Daily-ATR-Stop-480-Trades-5-Coins/) | `4H` · Donchian Multi-Día + R-Ladder | Canales `100/50` barras `4H` causales (`[1]`); stop inicial **`2.0 × Daily ATR(14)`** desde cierre diario previo; TP `4R`; R-Ladder mueve SL a BE en `+2R`, `+1R` en `+3R`; salida anticipada si rompe canal opuesto `50` barras. | **Carril 2 (Multi-día)** |
| **6** | **Ω Volume Z-Score Strategy** (`OmegaTools`, `NQ1!`, 41 boosts) · [Script](https://www.tradingview.com/script/aLVOHVbF-Volume-Z-Score-Strategy/) | `15m–1H` · Doble Lente de Volumen | `z = (C - SMA21)/std21`, `rvol = V / SMA21(V)`, `volF = avg(clip(rvol, 0.5, 2), clip(rvol, 0.33, 3))`. **Doble lente:** entra en `z / volF > threshold` (favorece rupturas limpias sin clímax) alineado con tendencia de largo plazo (`SMA200`), sale en `z * volF` (clímax de agotamiento) o `2R`. | **Carril 1 (`BF5`)** |
| **7** | **GlowVwap \| Anchored VWAP Pullback Strategy** (`blitz_algo`, Gold `30m`, 409 boosts) · [Script](https://www.tradingview.com/script/Bvb4nAAT-GlowVwap-Anchored-VWAP-Pullback-Strategy/) | `15m–1H` · AVWAP `σ` Piso ATR + Anti-Chop | Desviación de VWAP de sesión con piso `s_eff = max(σ, 0.4×ATR14)`, aceptación (`2` cierres fuera de `0.15·s_eff`), pullback + vela verde/roja, **filtro anti-chop** (`rotaciones de signo sobre VWAP < 3`), stop `>= 0.55×ATR20_D1` / `1×s_eff`, TP `2R`. | **Carril 1 (`BF7`)** |
| **8** | **Aurora Value Trend \| Value Area Retest** (`blitz_algo`, 179 boosts) · [Script](https://www.tradingview.com/script/PGMAHksx-Aurora-Value-Trend-Value-Area-Retest-Strategy/) | `15m–4H` · Market Profile Semanal (`VAH`/`VAL`) | Construye perfil de volumen de la semana previa cerrada (70% VA = `wVah`/`wVal`) + filtro bilateral gaussiano adaptado a ATR + flujo EMA `9/34`; entra en retesteo de `wVah`/`wVal` a favor de tendencia con SL `1.5× ATR` y TP `2R`. | **Carril 2 / Perfil Semanal** |
| **9** | **Swing Exhaustion Fade \| Learned Odds** (`blitz_algo`, 480 boosts) · [Script](https://www.tradingview.com/script/QywP0C3E-Swing-Exhaustion-Fade-Learned-Odds-Liquidity-Sweeps/) | `15m–4H` · Cota Wilson Online + Liquidity Sweeps | ZigZag causal `2.5× ATR14`; aprende online por `(dir, rho, tamaño_ATR)` la probabilidad de giro con cota inferior de Wilson (`>= 0.60`) + sweep de clusters de liquidez en últimas `12` barras + tope `0.50× ADR14`, SL detrás del swing, TP `1.5R`, time stop `40` barras. | **Carril 2 (Swing)** |
| **10** | **LUBE** (`Jomy`, **Editors' Pick**, 2,021 boosts) · [Script](https://www.tradingview.com/script/i9tJOtjl-LUBE/) | `30m–1H` · Régimen Time-at-Price (LVN Breakout) | `friction = sum_{i=1..L, bl_i <= C <= bh_i} (1+L)/(i+L)` mide cuánto tiempo pasó el precio en el nivel actual. Entra en dirección del filtro `FIR(4)` cuando **`friction` cae al cuartil bajo (zona de baja resistencia)** vs control en zona de alta congestión. | **Carril 1 (`BF6`)** |
| **11** | **Gap Filling Strategy** (`alexgrover`, **Editors' Pick**, 1,423 boosts) · [Script](https://www.tradingview.com/script/ghocsiv7-Gap-Filling-Strategy/) | `15m–1H` · Apertura RTH (`upgap`/`dngap`) | Detecta gap verdadero fuera del rango previo (`open > high[1]` o `< low[1]`); modo Fade al límite previo vs modo Momentum con invalidación si cierra el gap. | Incluible en futuro módulo de gaps RTH |

---

## Parte C — Separación en 2 Carriles de Ejecución

Dado que el motor estándar intradía [`edgelab/research/ejecucion.py`](../../../edgelab/research/ejecucion.py) opera por sesión con `GAP_S = 1800 s`:

1. **Carril 1 — Intrasesión A5 de Baja Fricción (`edgelab/research/baja_friccion_a5.py`, listo para correr hoy en `ES`, `NQ`, `YM`, `GC`):**
   - `BF1` (`MNQ Midday Continuation`, `1.0× ADR20` SL), `BF2` (`Gap-Adjusted Noise-Band Paper Mode`, `0.75× ATR20` SL), `BF3` (`Pre-NY Sweep 4H FU Retest`, `0.65× ATR20` SL), `BF4` (`Previous Day Extreme 25% Reclaim`, `0.60× ATR20` SL), `BF5` (`Ω Volume Z-Score Double-Lens`, `0.60× ATR20` SL), `BF6` (`LUBE Time-at-Price LVN Breakout`, `0.60× ATR20` SL), `BF7` (`GlowVwap AVWAP Pullback + Anti-Chop`, `>= 0.55× ATR20` SL) y `BF8` (`Williams Volatility Expansion + Crabel NR Contraction`, prima de `Dual Thrust X038/X039`, `>= 0.50× ATR20` SL).
2. **Carril 2 — Swing / Multi-Día / Macro Overlay (requiere runner continuo multi-sesión o barras `4H/1D` sin corte de fin de día):**
   - `TASC 2026.06 One Percent A Week - Adaptive`, `Channel Breakout 100/50 + 2× Daily ATR`, `TASC 2024.10 Adaptive Oscillator Threshold`, `TASC 2025.05 Trading The Channel`, `Charles Monger 1H 200-EMA Hysteresis Band`, `Aurora Value Trend` (Weekly VA), `TASC 2026.07 Risk-On/Off/Caution` + **Pre-FOMC Drift / Overnight Drift**.
