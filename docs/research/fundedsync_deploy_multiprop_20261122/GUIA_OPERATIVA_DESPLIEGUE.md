# Guia Operativa de Despliegue — `EdgeLabFundedSyncPortfolio` (`P_OPT_SF_v2`)

**Estrategia NT8:** [EdgeLabFundedSyncPortfolio.cs](file:///C:/Users/nicoc/.gemini/antigravity/scratch/EdgeLab-fundedsync/nt8/strategies/EdgeLabFundedSyncPortfolio.cs)  
**Oraculo de Paridad (`2025-2026`):** [REFERENCIA_PARIDAD_P_OPT_SF_v2.csv](file:///C:/Users/nicoc/.gemini/antigravity/scratch/EdgeLab-fundedsync/docs/research/fundedsync_deploy_multiprop_20261122/REFERENCIA_PARIDAD_P_OPT_SF_v2.csv)  
**Resumen Completo:** [RESULTADO.md](file:///C:/Users/nicoc/.gemini/antigravity/scratch/EdgeLab-fundedsync/docs/research/fundedsync_deploy_multiprop_20261122/RESULTADO.md)

---

## 1. Eleccion de Arquitectura Prop Firm Segun Capital Disponible

| Perfil | Firmas y Configuracion Recomendada | Riesgo `1R` (`Eval / Funded`) | Cap Micros | Colchon Post-Retiro | Caja p10 Requerida (`REP 60%`) | Neto 12m Esperado (`REP real_100 / 60%` | `A5_HOLDOUT real_100`) |
|---|---|---|---|---|---|---|
| **Conservador (`< $10k`)** | LucidFlex 50K (`L17`, promo `$78.33`) o **Topstep NoAct 50K** (`$95/mes`) + `MP3` 50K escalonado | `$200 / $200` (o `$300 / $200` Topstep) | `40–50` | `$1,250` (Lucid) / `$1,000` (Topstep) | `$6,266` – `$9,534` | `+$15,280 / +$8,538` (`L17`) · `+$25,012 / +$13,550` (`Topstep`) | `+$6,218` (`L17`) · `+$8,562` (`Topstep`) |
| **Equilibrado (`$15k–$25k`)** | LucidFlex 150K (`L02`) o **MP1 Duo** (`LucidFlex 150K + Tradeify Select Flex 150K promo`) | `$450 / $450` (Lucid `L02`) o `$650 / $450` (Duo) | `100–120` | `$2,500` | `$16,807` (`L02`) · `$23,356` (`Netting`) | `+$25,418 / +$11,529` (`L02`) · `+$66,036 / +$27,876` (`MP1`) | `+$5,298` (`L02`) · `+$10,092` (`MP1`) |
| **Max Flujo (`$30k+`)** | `L10` (`E10, stag1`) o **Tradeify 150K promo** + **LucidFlex 150K promo** | `$650 / $450` | `100–120` | `$2,500` | `$25,909` – `$33,423` | `+$33,603 / +$15,916` (`L10`) · `+$39,714 / +$16,069` (`Tradeify`) | `+$6,644` (`L10`) · `+$5,513` (`Tradeify`) |

**Reglas duras de seleccion Multi-Prop:**
1. **NO operar Apex ni AlphaFutures** con ejecucion automatizada (`algo_policy = "prohibido"`).
2. **NO operar TakeProfitTrader PRO con este portafolio** si se escala rapido (`intraday_trailing` en funded destruye el edge de holds medios en `A5_HOLDOUT`).
3. **NUNCA pagar precios retail** en Tradeify (`$369`) o FundedNext (`$490`): esperar promociones del `30%–44%` (`<= $275`).
4. **Topstep XFA (`Combine_NoAct`):** excelentisimo complemento en evaluacion/XFA por NT8 sin activation fee, teniendo en cuenta que si se asciende a Live Account real no admite API automatizada.

---

## 2. Instalacion y Configuracion en NinjaTrader 8

1. **Copiar estrategia:** copiar `nt8/strategies/EdgeLabFundedSyncPortfolio.cs` a `Documents\NinjaTrader 8\bin\Custom\Strategies\` y presionar **F5 (Compile)** en NinjaScript Editor.
2. **Configurar grafico base (`OBLIGATORIO`):**
   - Instrumento: `NQ` (o `MNQ` para ejecucion micro nativa).
   - Timeframe: **`1 Minute`** (`BarsPeriodType.Minute, Value = 1`).
   - Trading Hours: **`CME US Index Futures ETH`** (sesion electronica completa, corte `18:00 ET`).
   - **Dias a cargar (`Days to load`):** **`>= 500` trading days (~2 anos calendario)**.  
     *Motivo critico:* sin ~2 anos de historico M1, `T_stop100_BE15R_calFalse` no acumula `>= 100` operaciones sombra previas para activar su KNN trimestral de 14 features, y `V_nm25_noCap_mae30` necesita 252 sesiones RTH para `daily_atr`.
3. **Parametros recomendados al adjuntar:**
   - **Account Mode:** `Evaluation` al operar pruebas (`EvalRisk1R_USD = 200` para 50K, `450` para `L02` o `650` boost 150K); cambiar a **`Funded`** al pasar (`FundedRisk1R_USD = 200` en 50K, `450` en 150K).
   - **MaxOpenR:** `3.0` (causal, no modificar).
   - **MaxMicroContracts:** `40` (50K Lucid/Tradeify) o `100` (150K Lucid) / `120` (150K Tradeify).
   - **CollisionPolicy:** **`Netting`** (recomendado por defecto en cuenta unica NT8; netea posiciones opuestas entre los 7 modulos virtuales enviando solo el contrato neto agregado, reduciendo riesgo de cross-hedging y comisiones). Alternativa equivalente: `VetoOpposite`.
   - **SecondaryMnqSymbol:** dejar vacio si el grafico ya es `MNQ`. Si operas en un grafico principal `NQ` (e.g. `NQ 12-26`) y quieres dividir automaticamente cada orden neta en `floor(|net|/10)` contratos `NQ` + `(|net| % 10)` contratos `MNQ` (**ahorro hibrido de comision**), escribir aqui el contrato vigente exacto (ej. `MNQ 12-26`).
   - **HardFlattenHHMM_ET:** `1640` (`16:40 ET`, 5 minutos antes del limite de LucidFlex / Tradeify / FundedNext).
   - **EnforceEvalDailyCap:** `true` en evaluacion (`EvalDailyCapUSD = 3420` en 150K con regla 40%, `1140` en 50K con regla 40%); cambiar `EnforceEvalDailyCap = false` o usar modo `Funded` al fondearse.
   - **DailyLossLimitUSD:** `2700` (LucidFlex 150K), `1200` (LucidFlex 50K), o `0` (Tradeify Select Flex / Topstep sin DLL fija).
   - **EnableWTrail:** `false` (por defecto validado en Etapa A: `W_slope_allowReFalse_ATR25` sin trailing supero al trail `1.5->0.5`).
   - **Pesos `W5` por defecto:** `R = 1.653354`, `Z = 1.965598`, `T = 0.768284`, `V = 1.019769`, `W = 0.915674`, `N = 1.252428`, `SOMEOD = 0.911410`.

---

## 3. Protocolo de Verificacion Pre-Live (Strategy Analyzer)

1. Habilitar `EnableParityCsvLog = true` (`ParityCsvFileName = "EdgeLab_FundedSync_ParityTrades.csv"`).
2. Correr **Strategy Analyzer** sobre `NQ 1 Minute ETH` (`2024-01-01` a `2026-11-17` para incluir los 2 anos de warmup KNN + 2025-2026).
3. Comparar el CSV generado en `Documents\NinjaTrader 8\EdgeLab_FundedSync_ParityTrades.csv` contra [REFERENCIA_PARIDAD_P_OPT_SF_v2.csv](file:///C:/Users/nicoc/.gemini/antigravity/scratch/EdgeLab-fundedsync/docs/research/fundedsync_deploy_multiprop_20261122/REFERENCIA_PARIDAD_P_OPT_SF_v2.csv) (`2025-01-01..2026-11-17`):
   - Verificar coincidencia de timestamps de entrada NY (`en_ny`), signo (`side`), nivel de stop inicial (`stop_price`) y activacion BE `+1.5 R` en `T`.
   - En `SOMEOD_ext_NQ`, confirmar que `ATR(14)` M5 corresponde a media simple de True Range (`SMA(TR, 14)`), y que los cierres EOD ocurren a las `15:55 ET`.
4. Confirmar en Playback / Sim antes de cuenta real:
   - Flatten automatico a las `16:40 ET` (`0` posiciones overnight).
   - Desactivacion de compras manuales con mismo direccion/timing entre cuentas distintas de terceros (**prohibido operar en grupo / copy-trading cruzado entre cuentas o firms** si excede terminos de la prop firm; usar siempre cuentas propias y reglas de neteo interno en cuenta unica).
