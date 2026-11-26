# Handoff Auditor — Bots cTrader/MT5, Bar-Open Phase Shift y Satélites Prop

Estado: HISTÓRICO (superado por `docs/HANDOFF_OPERATIVO_20261125_PRODUCCION.md`)  

> **Fecha:** 2026-11-23  
> **Rama:** `fix/fundedsync-il-parity`  
> **Modelo saliente:** Neon  
> **Modelo entrante:** Argon (auditoría e iteración multimodelo)  
> **Estado base heredado:** commit `b6adb8cf` (`nt8: suite completa 6 C# estrategias paridad IL/Python y guia por tiers de frecuencia`)  

---

## 1. Estado Técnico Certificado (Verificado Antes del Commit)

```text
CTRADER_COMPILATION            = 6/6 cBots compilados (0 errors, 0 warnings) via csc.exe /warnaserror /nowarn:1685 (incl. EdgeLabFundedSyncESCoreUS500)
CTRADER_VS_NT8_CORE_PARITY     = 1763 / 1763 trades INDEP (2025-2026), +197.100405 R vs +197.100405 R, max_diff=0.0, 0 unmatched
MT5_COMPILATION                = 6/6 EAs (.mq5) + 3 .mqh -> 12 .ex5 compilados (0 errors, 0 warnings) en MT5_Generic y MT5_The5ers
NT8_COMPILATION                = 6/6 estrategias EdgeLabFundedSync*.cs instaladas y compiladas (0 errors, 0 warnings) via csc.exe /warnaserror
MT5_NUMERICAL_BACKTEST_PARITY  = VERIFICADA_100_PORCIENTO_EN_TESTER (INDEP 1763/1763 +197.100404R, CORE5 1111/1111 +175.444567R, P7 1531/1531 +166.146542R; max_entry_diff=0.0, max_R_diff=1e-6)
ROADMAP_PATCH_ALINEACION       = Presets Core5_R25 / SpeedEval_TOnly / ES_Core_US500; perfiles Tradeify/FundedNext 50K en NT8; FundedDdBrake 4.5% (0.45% FTMO / 0.40% The5ers) activo por defecto en CFD; satelite EdgeLabFundedSyncESCoreUS500 en cTrader y MT5
AUDITORIA_BUGS_CORREGIDOS_ARGON= (1) MQL5 EMPTY_VALUE==DBL_MAX guard FsIsValidPos/FsIsValidFinite; (2) CopyRates O(1) incremental (~200x); (3) PendingEntryIsStopOrder direccional en cortos (NT8 + C# + MQL5); (4) LoadMoreHistory(300) en cTrader y auto-heal tickValue en MT5
BAR_PHASE_SHIFT_SUBMIN_322D    = Core5 12/12 fases >0 (d0=+152.07R, med=+105.06R, ret=71.5%); T sensible (35.9% ret); R/Z/N/SOMEOD 90.2%..108.0%
CFD_USATECH_SPREAD_AUDIT       = 14,127,594 ticks (2026-10-01..2026-11-15); RTH mediana=0.981 pts vs ETH=1.481 pts vs Fut=1.545 pts
OVERNIGHT_O_Y_SWAPS_CFD_2026   = Desbloqueado hasta 2026-11-17 (qty=1); swap CFD 8% anual + 3x miercoles absorbe ~90% del edge en CFD (REP +0.006 R/op, HOLDOUT -1.41R) -> O excluido de CFD y reservado a Futuros MNQ personales (0 swap)
ROADMAP_MULTIFRENTE_MC_SYNCED  = N=2000 x H=504d respetando topes legales por hogar + Freno Dinamico Caja (-$7.5K) + 30% Sweep a Boveda Personal (HOLDOUT Ratio Neto12/|p10| = 11.32x)
```

---

## 2. Fuente Canónica de Verdad e Inventario de Archivos Nuevos

### A. Bots cTrader (C# 5.0, `AccessRights.None`) y Sincronizador
- **Fuente canónica de edición**: editar **SIEMPRE** en `ctrader/Shared/` y luego ejecutar `python tools/sync_ctrader_mt5_bots.py --target all`. El script propaga las copias a cada proyecto en `ctrader/<Bot>/<Bot>/`, a `C:\Users\nicoc\OneDrive\Documentos\cAlgo\Sources\Robots\`, y a ambas terminales MT5 (y recompila cTrader + MT5).
- Shared C# 5.0 core & adapter:
  - `ctrader/Shared/EdgeLabFundedSyncCfdCore.cs` (`EdgeLabFundedSyncCfd`: los 7 motores causales `R, Z, T, V, W, N, SOMEOD`, `PortfolioCoordinator`, `PercentOfInitialBalance` / `PercentOfCurrentBalance` / `FixedUsd`, `FundedDdBrake`, `NewsGuard`, `FeedHistoricalBar`, `FeedClosedBarAndFillAtNextOpen`, `EvaluateTick`)
  - `ctrader/Shared/FundedSyncCTraderAdapter.cs`
- 6 wrappers cBot (`.sln`, `.csproj`, `.cs` + copias sincronizadas):
  - `ctrader/EdgeLabFundedSyncPortfolio/`
  - `ctrader/EdgeLabFundedSyncCore5AltaConv/`
  - `ctrader/EdgeLabFundedSyncCore6/`
  - `ctrader/EdgeLabFundedSyncSnipersRZ/`
  - `ctrader/EdgeLabFundedSyncSingleModule/`
  - `ctrader/EdgeLabFundedSyncESCoreUS500/`
- Tooling & harness C#:
  - `tools/sync_ctrader_mt5_bots.py` (`--target nt8|ctrader|mt5|all`)
  - `tools/VerifyCfdCoreParity.cs` (harness CLI usado para validar paridad exacta vs NT8 y correr el barrido de fases sub-minuto y multi-minuto directamente contra el core C# de cTrader)

### B. Bots MetaTrader 5 (MQL5)
- Headers compartidos en `mt5/Include/EdgeLabFundedSync/`:
  - `FS_TypesAndTime.mqh` (conversión DST US/EU pura en MQL5, `FS_TZ_NY_PLUS_7_ALL_YEAR`, `FS_TZ_EU_DST_EET`, calendario NYSE y tabla `NonFullNyse` para `Z`)
  - `FS_ModuleEngines.mqh` (motores `R, Z, T, V, W, N, SOMEOD`)
  - `FS_CoordinatorAndAdapter.mqh` (`CFundedSyncCoordinator`, `CFundedSyncMt5Adapter`, detección automática `ORDER_FILLING_*`, warmup `CopyRates` M1, reconciliador Hedging/Netting, SL de emergencia, `OnTester()`)
- 6 EAs en `mt5/Experts/EdgeLabFundedSync/`:
  - `EdgeLabFundedSyncPortfolio.mq5`
  - `EdgeLabFundedSyncCore5AltaConv.mq5`
  - `EdgeLabFundedSyncCore6.mq5`
  - `EdgeLabFundedSyncSnipersRZ.mq5`
  - `EdgeLabFundedSyncSingleModule.mq5`
  - `EdgeLabFundedSyncESCoreUS500.mq5`
- Nota de Git: los binarios `.ex5` y `.dll` compilados quedan instalados en las rutas locales de MT5 / cAlgo fuera del repo; en Git se trackean los fuentes `.mqh`, `.mq5`, `.cs`, `.csproj`, `.sln`.

### C. Análisis Bar-Open Phase Shift (CME NQ y CFD `USATECHIDXUSD`)
- Script reproducible: `tools/fundedsync_bar_phase_shift.py`
- Artefactos en `docs/research/fundedsync_bar_phase_shift_20261123/`:
  - `RESULTADO.md`
  - `subminute_phase_summary.csv`, `subminute_phase_by_module.csv`
  - `multiminute_shift_summary.csv`, `htf_phase_someod.csv`
  - `cfd_usatech_spread_and_comparison.csv`
  - `bar_phase_shift_subminute_0_55s.png`, `bar_phase_shift_multiminute_htf.png`
- Hallazgo central:
  - En `322` sesiones reales con ticks CME `NQ` (`291` K30 `2025-08-05..2026-09-25` + `31` Sellado `2026-10-01..2026-11-13` excl. `2026-10-07`), **`Core5_AltaConv` es positiva en 12/12 fases sub-minuto** (`delta=0s +152.07R`, mediana `+105.06R`, retención `71.5%`).
  - `R` (`106.4%`), `Z` (`108.0%`), `N` (`90.2%`) y `SOMEOD` (`96.2%`) son robustos; **`T` (`ORB15`) concentra casi toda la sensibilidad sub-minuto** (`+55.00R` en `d=0s` -> `+21.22R` mediana, `35.9%` retención media, `corr=0.699`) al depender del corte exacto `09:30:00–09:45:00 NY`.
  - En `USATECHIDXUSD` (`14.13M` ticks, `2026-10-01..2026-11-15`), el spread mediano RTH (`0.981 pts`, `$0` comm) es ~36.5% menor que la fricción futuro mini (`1.545 pts`), y `Core5` neto en `31` días iguala al CME (`+13.96 R` vs `+13.94 R`).

### D. Monetización de Estrategias Rentables Excluidas
- Script reproducible: `tools/fundedsync_satelites_prop.py`
- Artefactos en `docs/research/fundedsync_satelites_prop_20261123/`:
  - `RESULTADO.md`
  - `correlacion_satelites.csv`, `mc_arquitecturas_satelites.csv`, `personal_blend_resumen.csv`
  - `satelites_monetizacion_prop.png`
- Hallazgos clave:
  - **Validado NO usar `V + W` ni en `P7` ni en props baratas aisladas**: fusionar en `P7` desploma HOLDOUT de `\$117,539` a `\$20,228`; correr `(V+W)` solo en cuentas baratas (`Bulenox \$65`, `FundedNext \$80`, `Lucid50 \$95`, `Topstep \$95`) pierde en HOLDOUT (`-\$1,419` a `-\$5,830`/año, `P(Net>0) <= 1.7%`).
  - **Ganador claro en CFD Swing**: acoplar **`O` Overnight** (`rho = 0.054..0.080` vs `Core5`, ventana disponible `<= 2025-10-13`) + **`ES/US500` CFD adaptado** (`rho = 0.448`, Sharpe `1.16`) sobre `Core5` en `FTMO_Swing_100K` eleva Neto 12m de `\$9,194 -> \$18,530` (`REP`) y `\$7,437 -> \$11,852` (`HOLDOUT`), con `\$20,147 / \$13,326` en `The5ers_HighStakes_100K` y mínima caja `p10 = -\$990 / -\$1,080`.
  - **`T_Only -> Core5` (`SpeedEval`)** en `LucidFlex 150K`: supera a `Core5` base en HOLDOUT (`\$29,371` vs `\$27,632`) y recorta `42.6%` el `p10` de caja (`-\$7,499` vs `-\$13,069`).
  - **`R_ATR25` dentro de `Core5`**: sube `REP 100%` (`\$221,701` vs `\$187,330`) y empata HOLDOUT (`\$117,355` vs `\$117,539`).

### E. Tests
- `tests/research/test_ctrader_mt5_and_phase_shift.py`: compila los 5 cBots, ejecuta smoke test C# real (`PercentOfInitialBalance`, `FundedDdBrake`, `NewsGuard`, `FeedClosedBarAndFillAtNextOpen`, `EvaluateTick`), valida archivos `.mq5/.mqh/.ex5`, prueba continuidad de chunks del remuestreador de ticks (`resample_ticks_to_shifted_m1`), y verifica los entregables en `docs/research/`.

---

## 3. Foco de Auditoría e Iteración Recomendado para Argon

1. **Paridad numérica trade-by-trade de MT5 MQL5 (prioridad crítica antes de live)**:
   - Aunque las 5 EAs MQL5 compilan limpio (`0/0`), **aún no se ejecutó una corrida backtest en MT5 Strategy Tester comparando sus trades contra `REFERENCIA_PARIDAD_P_OPT_SF_v2.csv` / NT8**.
   - Auditar especialmente:
     - `mt5/Include/EdgeLabFundedSync/FS_ModuleEngines.mqh`: selección parcial 15-NN de `CFtmOrbEngine` (`T`), `CZetaEngine` (`Z`), `CAtrPhaseEngine` (`R`) y `CSessionOpenMomentumEngine` (`SOMEOD`).
     - `mt5/Include/EdgeLabFundedSync/FS_TypesAndTime.mqh`: transición de semanas de desfase DST entre EE.UU. y Europa (marzo y octubre/noviembre) bajo `FS_TZ_NY_PLUS_7_ALL_YEAR` vs `FS_TZ_EU_DST_EET`.
     - `mt5/Include/EdgeLabFundedSync/FS_CoordinatorAndAdapter.mqh`: lógica de reconciliación Hedging/Netting, parciales y SL de emergencia.

2. **Especificaciones reales de bróker CFD en cTrader y MT5**:
   - Verificar en `FundedSyncCTraderAdapter.cs` y `FS_CoordinatorAndAdapter.mqh` el mapeo `UsdPerPointPerUnit`, `Symbol.TickValue`, `Symbol.TickSize`, `Symbol.QuantityToVolumeInUnits(1.0)` y `VolumeInUnits` sobre símbolos reales de índices en FTMO / The5ers / ICMarkets, incluyendo profundidad de warmup de `LoadMoreHistory()` / `CopyRates()` para alimentar `>= 20` días diarios y la tabla histórica de `T`.

3. **Auditoría de sensibilidad de `T` (`ORB15`) y feed CFD `09:30:00`**:
   - Revisar `docs/research/fundedsync_bar_phase_shift_20261123/RESULTADO.md`: `T` cae al `35.9%` cuando la vela se corre 5–55s o ±1m. Auditar si el feed real del bróker CFD en cTrader/MT5 tiene jitter de cierre de vela M1 o latencia en `09:30:00`, y evaluar si conviene atenuar `T` o anclar rango `09:30–09:45` por ticks en vivo.

4. **Extensión e implementación de `O` overnight + `ES/US500` (iteración de mayor retorno esperado en CFD)**:
   - **Gaps actuales conocidos a resolver en la iteración de Argon**:
     1. `data/fundedsync_post_il_20261122/NQ_fabrica_O.pkl` llega solo hasta **`2025-10-13`** (faltan Oct 2025 – Nov 2026 y holdout sellado). Extender `O` hasta `2026-11` usando el M1 canónico antes de promoverlo.
     2. La simulación CFD (`_sim_cfd_2phase_numba` en `tools/fundedsync_satelites_prop.py`) aplicó fricción conservadora global de spread (`1.438 pts`, cuando RTH real fue `0.981 pts`), pero **no modeló swaps nocturnos (especialmente triple swap de miércoles) para `O`**. Auditar swaps reales de FTMO Swing / The5ers sobre `US100` y re-correr el MC con swap incluido.
     3. Agregar módulos `O` y preset `ES/US500` a `EdgeLabFundedSyncCfdCore.cs` / `FS_ModuleEngines.mqh` si pasan la auditoría extendida.

5. **Validación cruzada de `R_maeATR25` y `SpeedEval` (`T_Only -> Core5`)**:
   - Confirmar que el swap `R_ATR50 -> R_ATR25` y el lifecycle switch `T_Only -> Core5` generalizan fuera de `LucidFlex 150K` (ej. `Tradeify 150K` y `FTMO Swing 100K`) sin sobreajuste ni degradación del drawdown p10.

---

## 4. Comandos de Reproducción Exactos

```powershell
# 1. Re-sincronizar y compilar cTrader (csc) + MT5 (MetaEditor64 x2 terminales)
python tools\sync_ctrader_mt5_bots.py --target all

# 2. Correr suite pytest completa (paridad multiprop + cTrader/MT5/phase shift)
pytest tests\research\test_fundedsync_integracion_multiprop.py tests\research\test_ctrader_mt5_and_phase_shift.py -v

# 3. Re-ejecutar analisis bar phase shift o satelites prop
python -u tools\fundedsync_bar_phase_shift.py
python -u tools\fundedsync_satelites_prop.py
```
