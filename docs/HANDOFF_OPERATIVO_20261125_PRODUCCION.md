# Handoff Operativo y Continuidad — Paso a Producción / Cashflow (`2026-11-25`)

> **Estado:** `VIGENTE`
> **Rama activa:** `fix/fundedsync-il-parity` (base heredada: `c523d256`)
> **Lectura obligatoria al retomar:**
> 1. Este documento (`docs/HANDOFF_OPERATIVO_20261125_PRODUCCION.md`)
> 2. [`docs/research/validacion_maestra_20261124/VEREDICTO_MAESTRO_CARTERAS_20261124.md`](research/validacion_maestra_20261124/VEREDICTO_MAESTRO_CARTERAS_20261124.md)
> 3. [`docs/HANDOFF_AUDITOR_20261123_FUNDEDSYNC.md`](HANDOFF_AUDITOR_20261123_FUNDEDSYNC.md)
> 4. [`docs/ESTADO_VIVO.md`](ESTADO_VIVO.md)

---

## 1. Situación Actual de Cuentas y Prioridad Inmediata (Generar Flujo de Caja Real)

El foco actual de Nico pasó de la exploración masiva de nuevas familias a **explotar los edges validados en cuentas reales/evals, verificar calidad de ejecución real y maximizar payouts**, mientras siguen corriendo los forwards sellados y se traducen a bots los 2–3 satélites de mayor ROI.

### 1.1 Cuentas disponibles HOY en NinjaTrader 8 / Tradovate
1. **Cuenta real/eval activa: `LucidFlex 25K` (`LFE02575951920002`)** *(en drawdown — única cuenta fondeable/eval activa por ahora)*
   - **Balance observado (`2026-11-25`):** `$24.270,10` (`-$729,90` desde `$25.000`).
   - **Reglas LucidFlex 25K:** Max Loss Limit `$1.000` (EOD trailing; si no cerró nunca por encima de `$25.000`, piso = `$24.000`, margen restante **`<= $270,10`** — verificar en el dashboard de Lucid si hubo cierre EOD positivo previo). Target `$1.250` (`$26.250`). Consistencia eval `40%` (`$500/día`, o `50%` si tiene add-on). Máx `20` micros / `2` minis.
   - **Configuración exacta lista en [`nt8/strategies/EdgeLabFundedSyncPortfolio.cs`](../nt8/strategies/EdgeLabFundedSyncPortfolio.cs) + [`nt8/strategies/EdgeLabFundedSyncCore.cs`](../nt8/strategies/EdgeLabFundedSyncCore.cs):**
     - Gráfico: **`MES 1-Minute ETH`** (`>= 500` días cargados).
     - **`Preset = ES_Core_US500`** *(alternativa: `Core5_R25` sobre `MNQ` con `EvalRisk1R = $60`, pero `MES` tiene stops en USD mucho más manejables para un colchón de `$270`)*.
     - **`PropProfile = LucidFlex_25K_Rescate`** (`EvalRisk1R = $60` auto-escalado `×6 = $360` cuando `Preset == ES_Core_US500` para compensar el peso `1/6`, `MaxMicros = 1`, `MaxOpenR <= 1.0`, `EvalDailyCapUSD = $470`, `DailyLossLimitUSD = $120`, `HardFlattenHHMM_ET = 1635`).
     - **`EnableExecAuditLog = true`** (telemetría real activada).
     - Colocar además **Daily Loss Limit en Tradovate en `$120–$130`**.
2. **Cuenta demo de servidor NT8: `DEMO2xy4tfNV`** *(NO usar `Sim101` ni `Playback101` para medir ejecución real)*.
   - Usar **`EdgeLabExecutionProbe`** ([`nt8/strategies/EdgeLabExecutionProbe.cs`](../nt8/strategies/EdgeLabExecutionProbe.cs)) en `MES 1m` y `MNQ 1m` con `Mode = MarketOnBarClose` (y luego `PassiveLimitThenCross`), `Quantity = 1`, `IntervalBars = 3`, `HoldBars = 1`, `MaxRoundTrips = 15`, sincronizando reloj Windows (`w32tm /resync`) y cerrando MT5/JForex4 durante la prueba.
   - Auditar el CSV generado (`Documents\NinjaTrader 8\EdgeLab\exec_audit\EdgeLab_LiveExecution_Audit_*.csv`) con:
     ```powershell
     python tools/audit_live_execution.py --account DEMO
     ```
     *(si Tradovate demo reporta comisión `$0` en NT8, pasar `--comm-rt-usd 1.24`).*

---

## 2. Inventario de Código Operativo vs Pendiente de Traducción

### 2.1 Bots ya compilables / listos en repo
- **NT8 (`C#`):** instalados y sincronizados en `C:\Users\Usuario\Documents\NinjaTrader 8\bin\Custom\Strategies\` (verificados con `csc.exe`, **0 errores**; en NT8 Editor presionar `F5`):
  - `EdgeLabFundedSyncCore.cs`, `EdgeLabFundedSyncPortfolio.cs`, `EdgeLabFundedSyncCore5AltaConv.cs`, `EdgeLabFundedSyncCore6.cs`, `EdgeLabFundedSyncSingleModule.cs`, `EdgeLabFundedSyncSnipersRZ.cs`, `EdgeLabExecutionProbe.cs`, `EdgeLabRQ5.cs` *(en carpeta local de NT8 Custom Strategies)*.
- **cTrader (`ctrader/Shared/`) y MT5 (`mt5/Experts/EdgeLabFundedSync/`):** 6 bots (`Portfolio`, `Core5AltaConv`, `Core6`, `SnipersRZ`, `SingleModule`, `ESCoreUS500`), paridad 100% verificada en backtest (`HANDOFF_AUDITOR_20261123`).

### 2.2 Estrategias VALIDADAS que faltan codificar para producción (Máximo ROI)
Ver métricas completas `DESC` vs `REP` limpia y Monte Carlo en [`VEREDICTO_MAESTRO_CARTERAS_20261124.md`](research/validacion_maestra_20261124/VEREDICTO_MAESTRO_CARTERAS_20261124.md):
1. **`C2_VZ` (`CARRIL2`, compresión `VIX z < -1` en `ES+NQ`)** + **`Turtles_GC_CFD` (`XAUUSD` / `MGC`, cierre viernes)**:
   - Son **Swing** (mantienen overnight / hasta viernes): **NO entran en LucidFlex** (flat `16:40 ET`), sí en **`FTMO Swing 100K`** y **Bóveda Personal**.
   - Junto con `Core + RQ5_ES_CFD`, disparan el Sharpe OOS `REP 2020–25` de `2,53 → 3,47–3,61`, llevan `Worst20%M` de `-$6.503 → -$120 / +$817`, duplican el neto 12m en FTMO Swing (`+$10.637 → +$22.812`, `9,38` payouts/año, `99,1%` `P(pay)` y `83,1%` bajo estrés 60% con `p10 = -$540`).
   - `C2_EVRP` quedó validada también como co-satélite Swing de `CARRIL2` (`Full REP +0,322 R_cfd, PF=2,46, t=+2,84, corrM=-0,298`).
2. **`RQ5_ES` (`MES` / `US500.cash`):** único satélite Intraday-Flat validado en Futuros + CFD (`5/5` phase-shifts `+`, `corrM = -0,183`, `Worst20%M +7,68 R_cfd / +6,84 R_fut`). Existe `EdgeLabRQ5.cs` en NT8 local (sin los defaults específicos `ES_CFD`), pero falta portarlo a MT5/cTrader y ajustarlo a `US500.cash`.
3. **`SOM_ES_CFD`** + **`ES5N_ES_CFD` (`10:00 NY`, peso chico `<=12–15%`)**: satélites intradía CFD para **`The5ers HS 100K`** (`+$15.885` neto 12m, `7,36` payouts/año).

### 2.3 Reglas y Hallazgos sobre Noticias (Backtest vs Live)
- **Backtest Python:** **NO** filtra noticias (`calFalse` en `T`, `restricted-news-days.csv` de `motor_cartera.py` no existe en el repo). Todos los números `DESC`/`REP` ya incluyen CPI/NFP/FOMC.
- **NT8 (Futuros):** **NO** filtra noticias. LucidFlex permite noticias, pero con `$270` de colchón evitar `08:30 ET` (CPI/NFP) y `14:00 ET` (FOMC) por slippage.
- **MT5 (CFDs):** [`FS_CoordinatorAndAdapter.mqh`](../mt5/Include/EdgeLabFundedSync/FS_CoordinatorAndAdapter.mqh) tiene `NewsGuard` horario fijo (`"0830,1000,1400"` ET, ±2 o ±5 min) activo por defecto en `FTMO_STD`, `THE5ERS_HS` y `FUNDINGPIPS_STD` (apagado en `FTMO_SWING`). **Limitación:** no usa calendario económico real y **solo bloquea entradas nuevas, NO cierra trades ya abiertos** (cuidado en The5ers/FTMO Standard si un trade abierto toca SL/TP en noticia).

---

## 3. Sincronización de Datos Sellados y Forwards al `2026-11-23`

- Dataset Kaggle `nicolasbuttaro/edgelab-holdout-sellado` actualizado hasta **v9**:
  - **Futuros NT8 (`v8`):** `python tools/nt8_sellado_diario.py diario --espejo C:\EdgeLab\sellado --fuente E:\DatosNT8\HOLDOUT_SELLADO`
  - **Spot Dukascopy (`v9`):** el downloader HTTP directo (`dukascopy_descarga.py`) daba `HTTP 503`; usar estrategia JForex4 [`tools/jforex/HDAUTO_SPOT_NOV.java`](../tools/jforex/HDAUTO_SPOT_NOV.java) + [`tools/sync_jforex_bin_sellado.py`](../tools/sync_jforex_bin_sellado.py) + `kaggle datasets version -p C:\EdgeLab\sellado`.
- **Nota técnica sobre `tools/fundedsync_cadena.py`:** al correr `fw20261123` en Kaggle, `paridad_vendedor.py` falló con `NameError: __file__` porque `kaggle_kernel.py`/`construir()` hace `exec(compile(...))` sin definir `_s.__dict__['__file__']`. Para esta corrida se usó el wrapper [`docs/research/validacion_maestra_20261124/scripts/push_cadena_fw_fixed.py`](research/validacion_maestra_20261124/scripts/push_cadena_fw_fixed.py). Conviene inyectar `_s.__dict__['__file__']` directamente en `fundedsync_cadena.py` en un próximo mantenimiento.
- **Forwards recolectados (`fw20261123`):**
  - `regimen_forward` (`faltan: []`): `FRANKLIN +7,47 R` (`n=4`), `T +3,42 R` (`n=5`), `CANASTA_TR +2,42 R` (`6 ses.`), `SOM +1,68 R` (`n=6`), `Turtles_GC +1,01 R` cerrada + `1` abierta, veto `PREAPERTURA-ES` evitó `-2,06 R`, `CARTERA_B -$392,54` (`corr -0,067` vs `v2`).
  - `cartera_20261116`: `v2 -13,57 R` (`-$2.714`), `v3 -16,14 R` (`-$3.227`), arrastradas por reglas ya refutadas/apagar (`CVGAP-ES-C`, `PREAPERTURA-NQ Intento 1`, `DRC-NQ-R`). Solo mantener en demo las de footprint/zonas todavía en `SIN_DECIDIR`.

---

## 4. Continuidad entre Agentes (Estado del Sistema 4 Capas `55f238a17`)

Verificado el `2026-11-25`:
- Commit [`55f238a17`](https://github.com) (`2026-11-21`, *"persistencia fail-closed en 4 capas"*): **`python tools/contexto_vivo.py --check` pasa OK** y **`pytest tests/test_persistencia_contexto.py` pasa 4/4**.
- **Qué falta extender ahora que el foco está en aplicar los bots y cobrar payouts:**
  1. **Capa de Operaciones/Producción (`ESTADO_PRODUCCION.md` + `config/cuentas_activas.json`):** `ESTADO_VIVO.md` resume bien research (`FACTORES.jsonl`, `A5`), pero no registra qué cuentas reales/props están vivas, su equity/MLL actual, qué bot + `.set` exacto corre en cada gráfico/VPS y los resultados de `audit_live_execution.py`.
  2. **Sincronizar `docs/research/FACTORES.jsonl` + `ESTADO_VIVO.md`:** cargar los descartes cerrados del `2026-11-24` (`BF1..BF8`, `Z_RTY`, `FM2`, `RQ2`, `RQ6`, `ES5N_NQ`, `PREAPERTURA Int0/1`, `C2_VBB/DBO/P80`, `HobbieCode Gann/ST`) y correr `python tools/contexto_vivo.py --write` para que el sistema `NO_REPETIR` los bloquee automáticamente a futuros agentes.
  3. **Alinear rama declarada en `CLAUDE.md` / `AGENTS.md`:** `tools/estado.py` hoy reporta `MAL rama distinta de la declarada` porque `CLAUDE.md` sigue apuntando a `foundation/f0b-compatibility-probe` mientras todo el desarrollo live/bots está en `fix/fundedsync-il-parity` (mergear o actualizar la rama declarada).
  4. **Check automático de deriva NT8/MT5 vs repo (`sync_ctrader_mt5_bots.py --check`):** evitar que un agente edite `nt8/strategies/*.cs` o `mt5/*` sin copiarlo a `Documents\NinjaTrader 8\bin\Custom\Strategies\` o viceversa.
