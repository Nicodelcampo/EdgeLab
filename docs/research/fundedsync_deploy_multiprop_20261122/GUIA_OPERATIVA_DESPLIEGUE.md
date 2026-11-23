# Guia Operativa de Despliegue — Suite NT8 `EdgeLabFundedSync` y Arquitectura Multi-Prop

**Motor Compartido:** [EdgeLabFundedSyncCore.cs](file:///C:/Users/nicoc/.gemini/antigravity/scratch/EdgeLab-fundedsync/nt8/strategies/EdgeLabFundedSyncCore.cs)  
**Estrategia Principal (`P_OPT_SF_v2` / Selector):** [EdgeLabFundedSyncPortfolio.cs](file:///C:/Users/nicoc/.gemini/antigravity/scratch/EdgeLab-fundedsync/nt8/strategies/EdgeLabFundedSyncPortfolio.cs)  
**Variantes Especializadas NT8:**  
- [EdgeLabFundedSyncCore6.cs](file:///C:/Users/nicoc/.gemini/antigravity/scratch/EdgeLab-fundedsync/nt8/strategies/EdgeLabFundedSyncCore6.cs) (`P_OPT_Core6`, 6m NQ sin `SOMEOD`)  
- [EdgeLabFundedSyncCore5AltaConv.cs](file:///C:/Users/nicoc/.gemini/antigravity/scratch/EdgeLab-fundedsync/nt8/strategies/EdgeLabFundedSyncCore5AltaConv.cs) (`Core5_AltaConv`: `R+Z+T+N+SOMEOD`, menor DD en `REP`)  
- [EdgeLabFundedSyncSnipersRZ.cs](file:///C:/Users/nicoc/.gemini/antigravity/scratch/EdgeLab-fundedsync/nt8/strategies/EdgeLabFundedSyncSnipersRZ.cs) (`Tier1_Snipers_RZ`: `R+Z`, baja frecuencia `~5 ops/mes`)  
- [EdgeLabFundedSyncSingleModule.cs](file:///C:/Users/nicoc/.gemini/antigravity/scratch/EdgeLab-fundedsync/nt8/strategies/EdgeLabFundedSyncSingleModule.cs) (Auditor aislado por modulo para Strategy Analyzer)  
**Oraculo de Paridad (`2025-2026`):** [REFERENCIA_PARIDAD_P_OPT_SF_v2.csv](file:///C:/Users/nicoc/.gemini/antigravity/scratch/EdgeLab-fundedsync/docs/research/fundedsync_deploy_multiprop_20261122/REFERENCIA_PARIDAD_P_OPT_SF_v2.csv)  
**Resumen Completo:** [RESULTADO.md](file:///C:/Users/nicoc/.gemini/antigravity/scratch/EdgeLab-fundedsync/docs/research/fundedsync_deploy_multiprop_20261122/RESULTADO.md)

---

## 1. Como Organizar Estrategias de `2–4 ops/mes` vs `15–20 ops/mes`

Los 7 modulos del stack operan en **tres regimenes temporales distintos**:

| Tier de Frecuencia | Modulos | Cadencia Individual | Rol Estadistico en Cartera |
|---|---|---|---|
| **Tier 1: Snipers (`2–4 ops/mes`)** | `R_osc30_end660_ATR50`, `Z_b15_e20_eff40_ATR50` | `~2.4` y `~2.7 ops/mes` (`5.2 ops/mes` juntos, `20.3%` dias activos) | Mayor Sharpe y menor drawdown, pero insuficientes por si solos para evaluaciones mensuales o reglas de consistencia `40%`. |
| **Tier 2: Swing/Breakout Intermedio (`6–11 ops/mes`)** | `W_slope_allowReFalse_ATR25`, `N_d5_fbTrue_ATR25` | `~6` a `~11 ops/mes` | Puente de flujo tendencial RTH (`W`) y rupturas multi-dia (`N`). |
| **Tier 3: Flujo Diario (`15–21 ops/mes`)** | `V_nm25_noCap_mae30`, `T_stop100_BE15R_calFalse`, `SOMEOD_ext_NQ` | `~15` a `~21 ops/mes` cada uno (`~82–83%` dias activos juntos) | Garantizan flujo diario continuo y diversifican la fecha de captura de ganancias sin sacrificar Sharpe agregado. |

**Regla de arquitectura recomendada (unificar en un grafico vs separar cuentas):**
1. **Dentro de una misma cuenta Prop (`Evaluation` o `Funded`):** **NO separar en cuentas distintas ni en multiples instancias de grafico** salvo para auditoria aislada. Los 7 modulos deben correr unificados dentro de un solo **Coordinador con Sleeves Virtuales + Sincronizador de Posicion Neta Unica** (`EdgeLabFundedSyncPortfolio` o `EdgeLabFundedSyncCore5AltaConv`).
2. **Por que funciona unir `2–4/mes` con `15–20/mes` bajo `W5` + `MaxOpenR = 3.0`:**
   - Los pesos `W5_freq_dur_conc` multiplican el `1R` de los snipers de baja frecuencia (`R = 1.653354`, `Z = 1.965598` en `P_OPT_SF_v2`) para que cada disparo poco frecuente aporte `~1.7–2.3x` sin inflar la exposicion diaria media.
   - `MaxOpenR = 3.0` prioriza de forma causal el cupo simultaneo, evitando sobre-apalancamiento si coinciden señales el mismo dia.
   - El **Neteo Interno (`CollisionPolicy = Netting`)** cancela exposiciones opuestas antes de enviar ordenes a NT8, ahorrando comisiones y drawdown intradia.
3. **Cuando SI separar (`EdgeLabFundedSyncSnipersRZ`):**
   - Solo para **cuenta personal propia** o **cuenta fondeada ya con colchon consolidado (`>$2,500`)** donde no haya costo mensual de evaluacion ni meta de consistencia rapida (`DESC Calmar = 5.37`, `DD = -3.3 R`).

---

## 2. Comparativa Cuantitativa de Variantes de Cartera (`MaxOpenR = 3.0`, `POST_2020`)

| Variante (`W5`) | Modulos Incluidos | Pesos `W5` (`R, Z, T, V, W, N, SOMEOD`) | `DESC`: `ops/m \| act \| R/m \| Sh \| DD \| Cal \| %m>0` | `REP`: `ops/m \| act \| R/m \| Sh \| DD \| Cal \| %m>0` | Estrategia NT8 |
|---|---|---|---|---|---|
| **`P_OPT_SF_v2 (7m)`** | `R, Z, T, V, W, N, SOMEOD` | `1.653, 1.966, 0.768, 1.020, 0.916, 1.252, 0.911` | `78.0 \| 83.2% \| +8.21 \| 2.24 \| -19.6 \| 5.04 \| 78%` | `79.7 \| 82.1% \| +5.86 \| 1.74 \| -23.4 \| 3.01 \| 86%` | `EdgeLabFundedSyncPortfolio` (`Preset = P_OPT_SF_v2`) |
| **`P_OPT_SF_v2 (7m) [W0]`** | `R, Z, T, V, W, N, SOMEOD` | `1.000` c/u | `78.0 \| 83.2% \| +7.94 \| 2.10 \| -20.5 \| 4.64 \| 80%` | `79.7 \| 82.1% \| +5.85 \| 1.66 \| -23.8 \| 2.95 \| 86%` | `EdgeLabFundedSyncPortfolio` (`Preset = CustomWeights`) |
| **`P_OPT_Core6 (6m)`** | `R, Z, T, V, W, N` | `1.733, 2.061, 0.747, 1.003, 0.900, 1.215, 0` | `57.1 \| 80.5% \| +7.88 \| 2.31 \| -21.1 \| 4.47 \| 78%` | `58.7 \| 79.9% \| +5.23 \| 1.67 \| -21.3 \| 2.94 \| 64%` | `EdgeLabFundedSyncCore6` |
| **`P_OPT_SF_SinW (6m)`** | `R, Z, T, V, N, SOMEOD` | `1.747, 2.077, 0.719, 1.003, 0, 1.256, 0.875` | `71.8 \| 83.0% \| +7.20 \| 2.18 \| -18.2 \| 4.75 \| 74%` | `73.0 \| 82.1% \| +5.76 \| 1.91 \| -19.8 \| 3.49 \| 86%` | `EdgeLabFundedSyncPortfolio` (`Preset = P_OPT_SF_SinW`) |
| **`Core5_AltaConv (5m)`** | `R, Z, T, N, SOMEOD` | `1.802, 2.277, 0.710, 0, 0, 1.262, 0.849` | `55.0 \| 83.0% \| +6.56 \| 2.30 \| -15.8 \| 4.99 \| 72%` | **`55.4 \| 82.1% \| +4.95 \| 1.93 \| -11.8 \| 5.04 \| 93%`** | `EdgeLabFundedSyncCore5AltaConv` |
| **`Tier1_Snipers_RZ (2m)`** | `R, Z` | `0.733, 1.613, 0, 0, 0, 0, 0` | `5.2 \| 20.3% \| +1.48 \| 2.21 \| -3.3 \| 5.37 \| 70%` | `5.1 \| 18.7% \| +0.90 \| 1.57 \| -4.4 \| 2.48 \| 57%` | `EdgeLabFundedSyncSnipersRZ` |
| **`Tier23_Flow_TVNS (4m)`** | `T, V, N, SOMEOD` | `0, 0, 0.774, 1.078, 0, 1.327, 0.985` | `66.6 \| 83.0% \| +5.40 \| 1.66 \| -23.1 \| 2.81 \| 74%` | `67.9 \| 82.1% \| +4.72 \| 1.54 \| -18.4 \| 3.08 \| 79%` | `EdgeLabFundedSyncPortfolio` (`Preset = Tier23_Flow_TVNS`) |

---

## 3. Eleccion de Estrategia NT8 y Arquitectura Multi-Prop Segun Cuenta

| Cuenta / Escenario | Estrategia NT8 Recomendada | Perfil `PropProfile` / `1R` (`Eval / Funded`) | Cap Micros | Colchon Post-Retiro | Caja p10 (`REP 60%`) | Neto 12m Esperado (`REP real_100 / 60%` \| `A5_HOLDOUT`) |
|---|---|---|---|---|---|---|
| **LucidFlex 150K (`L02` Eq / `L10` Flujo)** | `EdgeLabFundedSyncPortfolio` (`P_OPT_SF_v2`) o `Core5AltaConv` | `LucidFlex_150K_Equilibrado` (`$450/$450`) o `MaxFlujo` (`$650/$450`) | `100` | `$2,500` | `$16,807` (`L02`) · `$25,909` (`L10`) | `+$25,418 / +$11,529` (`L02`) · `+$33,603 / +$15,916` (`L10`) \| `+$5,298` / `+$6,644` |
| **Tradeify Select Flex 150K (promo `<= $275`)** | `EdgeLabFundedSyncPortfolio` (`P_OPT_SF_v2`) | `Tradeify_SelectFlex_150K` (`$650/$450`, DLL `$0`) | `120` | `$2,500` | `$23,356` (`MP1 Netting`) | `+$39,714 / +$16,069` (`Tradeify`) · `+$66,036 / +$27,876` (`MP1`) \| `+$5,513` / `+$10,092` |
| **LucidFlex 50K / Topstep NoAct 50K (`< $10k`)** | `EdgeLabFundedSyncCore5AltaConv` (o `P_OPT_SF_v2`) | `LucidFlex_50K_Conservador` (`$200/$200`) / `Topstep_NoAct_50K` (`$300/$200`, Flatten `1605`) | `40–50` | `$1,250` / `$1,000` | `$6,266` – `$9,534` | `+$15,280 / +$8,538` (`L17`) · `+$25,012 / +$13,550` (`Topstep`) \| `+$6,218` / `+$8,562` |
| **FundedNext Flex 150K (promo)** | `EdgeLabFundedSyncCore5AltaConv` | `FundedNext_Flex_150K` (`$600/$400`, EOD, sin Consistencia) | `80` | — | — | Ver tabla Etapa C (`RESULTADO.md`) |
| **Fondeada con Colchon / Cuenta Personal** | `EdgeLabFundedSyncSnipersRZ` (`R+Z`) o `Core5AltaConv` | `Personal_Custom` (`EnforceEvalDailyCap = false`) | `40–100` | N/A | N/A | Bajo drawdown (`-3.3 R` DESC / `-4.4 R` REP en `R+Z`) |

**Reglas duras de seleccion Multi-Prop:**
1. **NO operar Apex ni AlphaFutures** con ejecucion automatizada (`algo_policy = "prohibido"`).
2. **NO operar TakeProfitTrader PRO con este portafolio** si se escala rapido (`intraday_trailing` en funded penaliza holds medios).
3. **NUNCA pagar precios retail** en Tradeify (`$369`) o FundedNext (`$490`): esperar promociones del `30%–44%` (`<= $275`).
4. **Topstep XFA (`Combine_NoAct`):** excelente complemento en evaluacion/XFA por NT8 sin activation fee; si asciende a Live Account real no admite API automatizada.

---

## 4. Paridad Medida C# Headless vs Oraculo Python (`2025-01-02 .. 2026-11-17`, `6,194,249` barras `bip1`)

Verificacion ejecutada compilando `EdgeLabFundedSyncCore.cs` (`csc.exe /warnaserror`, `0` errores, `0` warnings) contra [REFERENCIA_PARIDAD_P_OPT_SF_v2.csv](file:///C:/Users/nicoc/.gemini/antigravity/scratch/EdgeLab-fundedsync/docs/research/fundedsync_deploy_multiprop_20261122/REFERENCIA_PARIDAD_P_OPT_SF_v2.csv):

| Modulo | Trades REF (Py) | Trades C# | Match Entrada Exacta / Day+Side | `sumR` Py vs C# | `meanDiff (R)` | Correlacion Diaria (`R`) | Nota de Paridad |
|---|---|---|---|---|---|---|---|
| **`R_osc30_end660_ATR50`** | `61` | `61` | `61/61 (100.0%)` | `+24.75` vs `+24.75` | `+0.0000` | `1.0000` | `0` diferencias > 0.01 R (`maxEnDiff = 0.000`, `maxSlDiff = 0.000`). |
| **`W_slope_allowReFalse_ATR25`** | `134` | `134` | `134/134 (100.0%)` | `+24.70` vs `+24.70` | `-0.0000` | `1.0000` | `0` filas con diferencia (`maxEnDiff = 0.000`). |
| **`Z_b15_e20_eff40_ATR50`** | `53` | `54` | `53/53 (100.0%)` | `+9.74` vs `+8.74` | `-0.0219` | `0.9762` | `53/53` exactos; trade `#54` corresponde a la sesion parcial final `2026-11-17`. |
| **`V_nm25_noCap_mae30`** | `403` | `409` | `403/403 (100.0%)` | `+4.98` vs `+5.69` | `+0.0016` | `0.9957` | `6` re-entradas intradia validas en vivo al liberarse el sleeve tras SL `-0.30 ATR20`. |
| **`N_d5_fbTrue_ATR25`** | `196` | `201` | `196/196 (100.0%)` | `+14.85` vs `+17.22` | `+0.0099` | `0.9850` | `5` re-entradas intradia validas tras SL `-0.25 ATR20` en tiempo real. |
| **`SOMEOD_ext_NQ`** | `480` | `480` | `479/480` Day+Side | `+61.55` vs `+64.55` | `+0.0062` | `0.9931` | `maxEnDiff = 0.000`; diferencia de `1m` solo por etiqueta apertura `09:35` M5 vs cierre fill `09:36` M1 + redondeo SL a `0.25`. |
| **`T_stop100_BE15R_calFalse`** | `423` | `424` | `415/423` (`413` exact) | `+72.77` vs `+73.36` | `+0.0010` | `0.9641` | Calendario NYSE causal + riesgo dual (`1.25*orb` IL interno, `1.0*orb` SL + `+1.5R` BE). |
| **Prop Pass (`LucidFlex 150K`)** | — | `2,154` | — | — | — | — | `MAX_OPEN_R = 3.0000` (`<= 3.0`), `FLATTEN_VIOL = 0` tras `16:40 ET`. |

---

## 5. Instalacion y Configuracion en NinjaTrader 8 (Suite Completa de 6 Archivos `.cs`)

1. **Copiar los 6 archivos `.cs` desde `nt8/strategies/` a `Documents\NinjaTrader 8\bin\Custom\Strategies\`:**
   - `EdgeLabFundedSyncCore.cs` (obligatorio siempre junto a cualquiera de los 5 wrappers)
   - `EdgeLabFundedSyncPortfolio.cs` (contiene tambien `FundedSyncNt8Adapter`, necesario para compilar en conjunto)
   - `EdgeLabFundedSyncCore6.cs`
   - `EdgeLabFundedSyncCore5AltaConv.cs`
   - `EdgeLabFundedSyncSnipersRZ.cs`
   - `EdgeLabFundedSyncSingleModule.cs`
   Presionar **F5 (Compile)** en NinjaScript Editor (`0 errors, 0 warnings`).
2. **Configurar grafico base (`OBLIGATORIO`):**
   - Instrumento: `NQ` (o `MNQ` para ejecucion micro nativa). Si operas en `NQ` y quieres particion hibrida (`floor(|net|/10)` `NQ` + `|net| % 10` `MNQ`), informar el contrato micro vigente en `SecondaryMnqSymbol` (ej. `MNQ 12-26`).
   - Timeframe: **`1 Minute`** (`BarsPeriodType.Minute, Value = 1`).
   - Trading Hours: **`CME US Index Futures ETH`** (corte `18:00 ET`).
   - **Dias a cargar (`Days to load`):** **`>= 500` trading days (~2 anos calendario)** para warmup completo de KNN trimestral de `T` (`>= 100` muestras) y ventana de `252` sesiones RTH de `V`.
3. **Parametros y Verificacion Strategy Analyzer:**
   - Seleccionar `PropProfile` (`LucidFlex_150K_Equilibrado`, `Tradeify_SelectFlex_150K`, `Topstep_NoAct_50K`, `FundedNext_Flex_150K`, etc.) para aplicar automaticamente `1R`, `MaxMicros`, `EvalDailyCap`, `DailyLossLimit` y `HardFlatten`; usar `Personal_Custom` para valores manuales.
   - Para auditar un modulo individual con sus parametros exactos (`ROscAtrMult`, `ZBucketMin`, `ZEmaPeriod`, `ZMinEffPct`, `TStopOrbMult`, `TBeTriggerR`, `VNoiseMult`, etc.), adjuntar `EdgeLabFundedSyncSingleModule` con `EnableParityCsvLog = true`.
   - En `SOMEOD_ext_NQ`, `ATR(14)` M5 (`NY+7h`) corresponde a media simple de True Range (`SMA(TR, 14)`), y los cierres EOD ocurren a las `15:55 ET`.
   - **Prohibido** operar en grupo o copy-trading cruzado entre terceros que viole terminos de la prop firm; usar siempre neteo interno (`CollisionPolicy = Netting`) en cuenta unica.
