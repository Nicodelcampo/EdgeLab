# OPTION-ALPHA (Top 20 Live) — Diseño para EdgeLab (2026-11-18)

Estado: VIGENTE — diseño congelado previo a calibración M1↔ticks y corrida DESC/REP (partición HOLDOUT-A5).

## 1. Fuente y criterio de selección
- Relevamiento completo del leaderboard oficial de **Option Alpha Live Trading (30 días)**: [`CATALOGO_TOP20.md`](CATALOGO_TOP20.md).
- De los 20 bots extraídos se separaron:
  1. **Puro VRP lejano sin señal direccional (`#1 xDTE $140-$350`, `#7 Tasty Condor`) o martingala sin stop (`#12 Martingale - TQQQ`, `#18 DCA - Multiple Symbols`)**: no se trasladan tal cual a futuros lineales (el cobro de prima a ±200 pts no existe en futuros y promediar sin SL viola el control de riesgo).
  2. **Señales operables en futuros M1 (`ES`, `NQ`, `YM`) con traducción exacta y causal (`OA1`–`OA8`)**: cubren timing intradía (`13:45 EST`), ruptura de Initial Balance (`60m ORB` con días/FOMC/Daily Bias), momentum en velas 10m Heikin Ashi BB-MACD, swing dip sobre `SMA200` y fade tras contención de rango (`EM%`).

## 2. Datos complementarios integrados (`M1NT8` v3)
- Además de las barras M1 no ajustadas de NT8 (`ES`, `NQ`, `YM`, `RTY`, `EMD`, `GC`), se generaron y subieron a `nicolasbuttaro/edgelab-nt8-m1-futuros` dos Parquets diarios sin *lookahead bias*:
  - `cboe_volatility_daily.parquet`: `VIX`, `VXN`, `RVX`, `VXD`, `GVZ`, `VIX9D`, `VIX1D` con `open`, `prev_close`, `ivr_252_prev_close`, `ivr_252_open`, `ivp_252_prev_close` y tasas `DTB3` / `DFF`.
  - `us_market_events_calendar_2006_2026.parquet`: sesiones NYSE `2006–2026`, `is_early_close` (`46` cierres anticipados 13:00 ET), `is_fomc_day` (`171` decisiones FOMC oficiales de la Fed), `is_fomc_statement_day`, `days_to_next_fomc`, `is_monthly_opex` y `is_vix_expiry`.

## 3. Reglas traducidas (`edgelab/research/option_alpha_a5.py`)
1. **`OA1` / `OA1N` (`#2 1:45pm Taco`)**: a las `13:45 ET`, fade contra el punto medio del ORB `15m` (`9:30–9:45`), stop `max(R15, 0.25·ATR20)`, salida `15:59 ET`. `OA1` = volatilidad calma/normal (`ATR20/C ≤ p75` causal de 120 sesiones); `OA1N` = alta volatilidad.
2. **`OA2` / `OA2N` (`#4 1:45pm Sandwich`)**: ancla `P0 = cierre 13:45 ET`; primer desvío `>= 0.25·R_am` entre `13:46–14:30 ET` → fade 1:1 hacia `P0` hasta `15:59 ET`, Lun/Mar/Jue/Vie (`OA2`) vs miércoles (`OA2N`).
3. **`OA3` (`#10 Opening Range Breakout 60m`)**: primer cierre M1 fuera del `60m ORB` (`10:30–12:00 ET`), stop en borde opuesto, salida `15:59 ET`.
4. **`OA4` / `OA4N` (`#20 60Min ORB 10 Wide`)**: ruptura `60m ORB` (`10:30–14:00 ET`), stop en mitad del `60m ORB`, TP `0.5R` o cierre `15:59 ET`, miércoles/viernes (`OA4`) vs Lun/Mar/Jue (`OA4N`).
5. **`OA5` / `OA5N` (`#17 ORB Intelligence Daily Bias`)**: ruptura `60m ORB` (`10:30–13:00 ET`) a favor del bias diario (`mid_ORB60_hoy` vs sesión previa) vs en contra (`OA5N`), stop en `mid_ORB60`.
6. **`OA6` (`#11 THE SPX 0DTE`)**: velas `10m` completas (`10:00–14:00 ET`) con Heikin Ashi + `EMA(8/21)` + `MACD(12,26)` fuera de Bollinger Band `1.5σ`, stop en extremo de vela `10m ± 0.1·ATR20`, salida `15:59 ET`.
7. **`OA7` (`#9 Trendy Short Put Spread`)**: a las `10:30 ET`, si `prev_rth_close > SMA200` causal y retroceso `<= -0.10·ATR20`, largo con SL `1·ATR20` y TP `0.5·ATR20` o cierre `15:59 ET`.
8. **`OA8` / `OA8N` (`#8 NFH` / `#19 Theta Fly`)**: tras deriva a `13:30 ET` contenida (`|C_1330 - Open_930| <= 0.65·ATR20`), primer desvío `>= 75%` del medio rango hasta `14:30` → fade al medio (`OA8`) vs día tendencial (`OA8N`).
