# Veredicto Maestro de Estrategias y Colocación en Carteras (`2026-11-24`)

> [!IMPORTANT]
> **Integridad A5 / A4 y Cobertura Completa Verificada:**
> - **Holdout sellado al `2026-11-23`:** `nicolasbuttaro/edgelab-holdout-sellado` **v8** (`ES/NQ/GC/YM` NT8 100% completos `tarde 0.0 min, temprano 0.0 min`) y **v9** (`USATECHIDXUSD` 17.81M ticks, `USA500IDXUSD` 5.81M ticks, `XAUUSD` 16.58M ticks hasta `2026-11-24T23:59:59Z` vía `JForex4`). Todos los runners preregistrados completaron con `faltan: []`.
> - **Validaciones fuera de muestra (`REP` limpia `2020–2025` / histórica):** Ninguna estrategia descartada fue abierta en `HOLDOUT` (`>= 2026-10-01`). Las métricas de `OOS REP` y las simulaciones Monte Carlo (`N=3.000`, bootstrap `252` días) provienen de particiones limpias no tocadas durante el descubrimiento.

---

## 1. Estado Forward Sellado al `2026-11-23` (`edgelab-holdout-sellado` v8 + v9)

### 1.1 Resumen de Runners de Régimen y Referencia (`fw20261123`)

Fuentes verificadas: [`FORWARD_20261123.json`](file:///E:/EdgeLab-fundedsync/docs/research/regimen_forward_20261119/FORWARD_20261123.json), [`FORWARD_TZR.json`](file:///E:/EdgeLab-fundedsync/docs/research/fundedsyncstack_20261115/cadena/forward/FORWARD_TZR.json), [`CARTERA_B.json`](file:///E:/EdgeLab-fundedsync/docs/research/fundedsyncstack_20261115/cadena/forward/CARTERA_B.json), [`franklin/fw20261123/RESUMEN.json`](file:///E:/EdgeLab-fundedsync/docs/research/reels_20261116/seguimiento/fw20261123/RESUMEN.json), [`som/fw20261123/RESUMEN.json`](file:///E:/EdgeLab-fundedsync/docs/research/quantlab_mt5_eas_20261116/seguimiento/fw20261123/RESUMEN.json) y [`turtles/fw20261123/RESUMEN.json`](file:///E:/EdgeLab-fundedsync/docs/research/turtles_oro_20261117/seguimiento/fw20261123/RESUMEN.json).

| Sistema / Módulo | Runner | `n` (`20261114..23`) | `R_total` (o USD) | `R_medio` | `Drawdown` | `e_edge` (`e_fut`) | Estado Forward | Lectura Operativa |
|---|---|---:|---:|---:|---:|---:|---|---|
| **`FRANKLIN`** (`ES+NQ`) | `regimen_forward` / `franklin` | **4 ops** (`1 NQ, 3 ES`) | **`+7,47 R`** | `+1,87 R` | `-1,02 R` | **1,555** (`0,922`) | `SIN_DECIDIR` | Arrancó sólido (`NQ +1,25 R`, `ES +1,87/+5,37/-1,02 R`). Pre-noviembre (`RESULTADO_HOLDOUT`): `n=28, +0,267 R/op, p_h=0,233`. |
| **`T` (`fundedsyncstack`)** | `regimen_forward` / `cadena` | **5 ops** | **`+3,42 R`** (`+$684` `1 MNQ` / `+$342` `pts`) | `+0,68 R` | `-1,02 R` | **1,160** (`0,819`) | `SIN_DECIDIR` | Principal motor de `CARTERA_B`. Positivo en la semana. |
| **`CANASTA_TR`** (`T+R`) | `regimen_forward` | **6 ses.** | **`+2,42 R`** | `+0,40 R` | `-2,02 R` | **1,070** (`0,978`) | `SIN_DECIDIR` | Positiva tras las primeras 6 sesiones selladas. |
| **`SOM`** (`US500 / ES`) | `regimen_forward` / `som` | **6 ops** | **`+1,68 R`** (`e=1,052` en pts) | `+0,28 R` | `-1,24 R` | **1,076** (`0,961`) | `SIN_DECIDIR` | `5/6` positivos salvo `-1,00 R` el `19-nov` (`20-nov +2,00 R`). Pre-nov: `n=29, +0,161 R, p_h=0,241`. |
| **`Turtles Oro` (`GC`)** | `turtles_oro` | **1 cerrada + 1 abierta** | **`+1,01 R`** cerrada (`-0,34 R` al cierre `23-nov`) | `+1,01 R` | — | `1,033` | `SIN_DECIDIR` | Corto del `19-nov` cerró viernes en **`+1,01 R`**; nueva posición `23-nov` abierta en curso (`FIN`). Pre-nov `n=0`. |
| **`R` (`fundedsyncstack`)** | `regimen_forward` / `cadena` | 1 op | `-1,01 R` (`-$655` en `CARTERA_B`) | `-1,01 R` | `-1,01 R` | `0,901` (`1,018`) | `SIN_DECIDIR` | Solo 1 operación (tocó stop `0,25×ATR20_ses`). |
| **`Z` / `Z_BANDA`** (`fundedsyncstack`) | `cadena` / `regimen_forward` | 2 ops / 2 ses. | `-0,73 R` (`Z_BANDA`) / `-$422` (`Z`) | `-0,37 R` | `-1,01 R` | `0,950` (`0,890`) | `SIN_DECIDIR` | Muestra mínima (`n=2`). |
| **`CARTERA_B` (`T+Z+R`, 1 MNQ/regla)** | `fundedsync_cadena` | 6 ses. | **`-$392,54`** | — | `-$732,63` | `e=0,889` (`CANASTA`) | `SIN_DECIDIR` | **`corr = -0,067` vs `CARTERA v2`** (`0` días con ambas `< -$300`); distancia a límite `$3.107`. |
| **Veto `PREAPERTURA-ES` (sesgo Franklin)** | `franklin_seguimiento` | 3 (`2` vetadas) | `-3,15 R` sin veto → **`-1,09 R` con veto** | — | — | `1,069` | `SIN_DECIDIR` | El filtro evitó **`-2,06 R`** de pérdidas en las 2 sesiones vetadas. |

### 1.2 Desglose Forward de `cartera_20261116` (`v2` y `v3`) al `2026-11-23`

Fuentes: [`FORWARD.json`](file:///E:/EdgeLab-fundedsync/docs/research/cartera_20261116/FORWARD.json) y [`FORWARD_V3.json`](file:///E:/EdgeLab-fundedsync/docs/research/cartera_20261116/FORWARD_V3.json) (`1 R = USD 200`, `12/12` reglas actualizadas con futuros NT8 v8 + spot Dukascopy v9):

| Cartera / Regla | Versión | Sensor / Ejec. | `n` (`salteadas_M1`) | `R_total` | `USD` | `e-valor` | Estado | Relación con Auditoría A5 |
|---|---|---|---:|---:|---:|---:|---|---|
| **`CARTERA v2` (Global)** | `v2` | Mix Fut + Spot | **6 ses.** | **`-13,57 R`** | **`-$2.714`** | `0,840` | `SIN_DECIDIR` | Arrastrada por las 3 reglas abajo marcadas |
| **`CARTERA v3` (Global)** | `v3` | Mix Fut + Spot | **6 ses.** | **`-16,14 R`** | **`-$3.227`** | `0,812` | `SIN_DECIDIR` | Peor por `DRC-NQ-R` (`fric 0,153 R`) |
| `CVGAP-ES-C` | `v2, v3` | `ES → MES` | 5 (`0`) | **`-5,98 R`** | `-$1.195` | `0,812` | `SIN_DECIDIR` | **Ya refutada en M1 (`2018–25 -0,044 R/op`)** |
| `PREAPERTURA-NQ` (`Intento 1`) | `v2, v3` | `NQ → MNQ` | 4 (`0`) | **`-3,67 R`** | `-$734` | `0,889` | `SIN_DECIDIR` | **Artefacto sub-minuto (`00s` vs `45s -20 R`)** |
| `U1-ZONAS-BT2-NQ` | `v2` | `NQ → MNQ` | 8 (`0`) | **`-6,27 R`** | `-$1.254` | `0,822` | `SIN_DECIDIR` | Racha mala inicial; espera potencia `TickDev` |
| **`U1-ZONAS-BT2-ES`** | `v2` | `ES → MES` | 4 (`0`) | **`+2,20 R`** | **`+$439`** | `1,073` | `SIN_DECIDIR` | Positiva en vivo |
| **`U1-ZONAS-AVCL-NQ`** | `v3` | `NQ → MNQ` | 2 (`0`) | **`+1,13 R`** | **`+$227`** | `1,037` | `SIN_DECIDIR` | Positiva (`fric 0,093 R` alta) |
| **`U1-ZONAS-AVCL-ES-C`** | `v3` | `ES → MES` | 1 (`0`) | **`+0,77 R`** | **`+$154`** | `1,025` | `SIN_DECIDIR` | Positiva (`fric 0,090 R` alta) |
| **`CONF-CVR-CFD-NQ-R`** | `v2, v3` | `USATECH → MNQ` | 5 (`0`) | **`+0,15 R`** | **`+$30`** | `1,003` | `SIN_DECIDIR` | Actualizada con spot v9 (neutra positiva) |
| `DRC-NQ-R` | `v3` | `NQ → MNQ` | 3 (`3`) | **`-8,54 R`** | `-$1.709` | `0,761` | `SIN_DECIDIR` | Descartada por fricción excesiva (`0,153 R`) |
| `U1-RACIMOS-GRILLA-NQ`, `U1-ORO-GRILLA`, `CVGAP-CFD-ES-C` | `v2, v3` | NQ / XAU / USA500 | 0 (`0`) | `0,00 R` | `$0` | `1,000` | `SIN_DECIDIR` | Sin disparos en la ventana `16..23 nov` |

---

## 2. Veredicto Definitivo de Validación / Descarte (Todas las Estrategias Auditadas)

Fuentes: [`LOCAL_TIER2_REP.json`](file:///C:/Users/Usuario/.gemini/antigravity/brain/6d51dfbd-ecbb-4249-894c-b2e8b3258c4b/scratch/validation_full/LOCAL_TIER2_REP.json), [`FULL_VAL_RESUMEN.json`](file:///C:/Users/Usuario/.gemini/antigravity/brain/6d51dfbd-ecbb-4249-894c-b2e8b3258c4b/scratch/validation_full/FULL_VAL_RESUMEN.json), [`MASTER_PORTFOLIO_OPT.json`](file:///C:/Users/Usuario/.gemini/antigravity/brain/6d51dfbd-ecbb-4249-894c-b2e8b3258c4b/scratch/validation_full/MASTER_PORTFOLIO_OPT.json), [`hobbiecode_y_forward_20261124.md`](file:///C:/Users/Usuario/.gemini/antigravity/brain/6d51dfbd-ecbb-4249-894c-b2e8b3258c4b/hobbiecode_y_forward_20261124.md) y [`audit_estrategias_ortogonales_20261124.md`](file:///C:/Users/Usuario/.gemini/antigravity/brain/6d51dfbd-ecbb-4249-894c-b2e8b3258c4b/audit_estrategias_ortogonales_20261124.md).

### 2.1 Estrategias Validadas (`DESC` + `REP` Limpia + Robustez)

| Estrategia | Muestra `DESC` | Resultado `DESC` | Muestra `REP` Limpia | Resultado `REP` Limpia | Meseta / *Phase-Shift* / Ortog. | Veredicto Final |
|---|---|---|---|---|---|---|
| **`Core5_R25` (`Core4_NQ` proxy)** | `2012–25` | Base validada EdgeLab (`corr=0,78` vs exact) | `2020–25 REP` (`250d`) | **`+12,57 R, Sh=+2,53, DD=-3,3 R`** (`Worst20%M -2,41 R`) | Motor principal probado (`$851,8/d` real) | **VALIDADA — CORE PRINCIPAL** |
| **`ESCoreUS500`** | Multi-módulo ES | Edge validado en US500 CFD | `REP` + MT5 2024–26 | Complemento intradía en `US500.cash` | No sobreoptimizar en MT5 (`Lenta`) | **VALIDADA — CORE CFD ES** |
| **`C2_VZ` (`VIX Z < -1`)** | `2018–25` (`n=237`)<br>`Full` (`n=459`) | `+0,1395 R_cfd` (`t=+2,42`)<br>`+0,1005 R_cfd` (`t=+2,40`) | `2018–25` (`n=79`)<br>`Full` (`n=145`) | **`+0,3283 R_cfd` (`PF=3,29, t=+2,98, p=0,0014`)**<br>**`+0,2489 R_cfd` (`PF=2,60, t=+3,33, p=0,0004`)** | `NQ +0,3624 (t=+2,83)`, `ES +0,2983 (t=+2,71)`. **`corrM=-0,312`, `Worst20%M +3,68 R` (`+19,73 R` sum `2020–25`, `Sh=2,22`)** | **CONFIRMADA — SATÉLITE ESTRELLA SWING** |
| **`C2_EVRP` (`CARRIL2`)** | `Full` (`n=323`) | `+0,0729 R_cfd` (`t=+1,27`) | `Full` (`n=90`)<br>`2020–25` | **`+0,3220 R_cfd` (`PF=2,46, t=+2,84, p=0,0023, DD=-3,1 R`)**<br>**`+11,07 R, Sh=+1,71`** | **`corrD=+0,014`, `corrM=-0,298`, `Worst20%M +5,21 R`** | **CONFIRMADA — CO-SATÉLITE SWING** |
| **`Turtles_GC_CFD` (`entrada_stop`)** | `2008–25` + ticks | `+0,97 Sh`, `DD -1,5 R`, `+2,61 R` en stag `may–sep 25` | `2020–25 REP` | **`+8,81 R, Sh=+2,13, DD=-1,0 R`** | **`corrD=+0,062`, `corrM=-0,110`, `Worst20%M +0,94 R`**; multi-día cierre viernes | **VALIDADA — SATÉLITE ORO SWING** |
| **`RQ5_ES` (`CFD` y `Fut`)** | `2020–25` (`324` var.) | `100% >0`, `+0,1387 R_cfd` (`t=+3,04`, `PBO=0,346`) | `2020–25 REP` | **`+12,93 R_cfd (Sh=1,04)`** / `+9,48 R_fut (Sh=0,76)` | **`5/5` phase-shifts `+` (100% med.)**, **`corrM=-0,183`, `Worst20%M +7,68 R_cfd / +6,84 R_fut`** | **VALIDADA — SATÉLITE INTRADÍA FUT/CFD** |
| **`SOM_ES_CFD`** | `2020–25` (`81` var.) | `100% >0` (`+0,0463` fábrica) | `2020–25 REP` | **`+13,91 R_cfd, Sh=+1,16, DD=-6,5 R`** | **`corrM=+0,011`, `Worst20%M +8,44 R`**, `4/5` phase-shifts `+` (evitar `-2m`), `fw +1,68 R` | **VALIDADA — SATÉLITE CFD INTRADÍA** |
| **`ES5N_ES_CFD` (`10:00 NY`, `RSI 40..60`)** | `20yr Full` (`n=704`)<br>`2020–25` (`n=194`) | `+0,1383 R_cfd` (`t=+3,01`)<br>`+0,1844 R_cfd` (`t=+2,29`) | `20yr Full` (`n=178`)<br>`2020–25` (`n=49`) | **`+0,1860 R_cfd` (`PF=1,50, t=+2,17, p=0,015, diff +0,254`)**<br>`+0,0631 R_cfd` (`t=+0,46`) | **`5/5` shifts `+` (`corr 0,924`)**; en `2020–25 REP` mostró `corrM=+0,345, W20M=-2,53 R` (peso chico) | **VALIDADA `ES_CFD` (PESO PEQUEÑO)** *(NQ descartado)* |
| **`T` y `R` (`fundedsyncstack`)** | `2012–25 NQ` | Validados en cadena DLL (`vendedor_calibrado`) | Forward `20261123` | `T +3,42 R` (`n=5`), `R -1,01 R` (`n=1`) | Integradas en `Core5` / `CARTERA_B` | **VALIDADA — DENTRO DE CORE5** |
| **`FRANKLIN` (`NQ / ES`)** | `2020–25 NQ/ES` | `NQ 100% >0` (`+0,106`), `ES 78% >0` (`PBO=0,185`) | `REP` + `fw20261123` | `ES` falló `REP` (`-0,017 R`); `NQ` alta corr (`+0,505`); `fw +7,47 R (n=4)` | Redundante en cartera vs `Core4_NQ` (`W20M -17 R`) | **OBSERVACIÓN FORWARD / SECUNDARIA** |

### 2.2 Estrategias Auditadas y **Descartadas** (`DESC` o `REP` Limpia)

| Estrategia / Familia | Partición Evaluada | Resultado Exacto Observado | Motivo Técnico de Descarte |
|---|---|---|---|
| **`BAJA_FRICCION_A5` (`BF1..BF8`)** | `20yr DESC` (`n=3.007..10.708`) | **0 / 8 pasan BH `q=0,10`**: Fut `-0,022` a `-0,051 R` (`t=-1,33` a `-5,47`); CFD `-0,002` a `-0,023 R`. (`BF1 ESNQ 20+` `+0,059, t=+2,19`, sin fuerza en `Full` ni BH) | **Sin edge estructural neto tras costos** (`REP` intacto). |
| **`PREAPERTURA Intento 0` (`NQ_OP_SAL`, `GC_OP_SAL`, `ES/YM`)** | `DESC` (`2012–25`, `2020–25`) y `REP` gated | `ES/YM` negativos en `DESC`; `GC_OP_SAL REP -0,0611 R_cfd (t=-0,53)`; `NQ_OP_SAL`: `Full REP -0,1061 R_cfd (t=-1,07)`, **`2020–25 REP +0,0719 R_cfd (n=252, PF=1,09, t=+0,48, p=0,314)`** | `GC` falló `REP`; `NQ` perdió 14a `REP` y en `2020–25 REP` tiene `t=+0,48` (no escalable). |
| **`PREAPERTURA-NQ Intento 1`** | `M1 2006–25` + Ticks `2025–26` | Sub-minuto colapsa **`+48,3 R (00s) → +0,2 R (15s) → -20,0 R (45s)`**; `-3,67 R` en forward `20261123` | **Artefacto de reloj sub-minuto**; apagar de `cartera_v2/v3`. |
| **`Z_RTY` (`Russell M2K`)** | `2018–25 DESC` & `REP` limpia | `DESC +0,1898 (t=+1,56)`; **`REP 2018–25 -0,0575 R (n=33, t=-0,18)`**; **`REP 2020–25 -0,3408 R (n=27, PF=0,46, t=-1,96)`** | **Colapso severo en `REP` limpia (`PF 0,46`)**. Descartada. |
| **`FM2` (`Concretum Band`)** | `DESC` & `REP` limpia | `FM2_NQ_2020_25 REP -0,0628 R_cfd (t=-0,70)`; `NQ_full REP -0,0199 (t=-0,38)`; `ES_NQ 20+ REP +0,0133 (t=+0,16)`; `ALL4_full REP +0,0537 (t=+1,30, p=0,097)` | **No replica fuera de muestra en NQ/ES** (`corr_m=+0,326` con Core). |
| **`RQ2_ES_NQ`** | `DESC` & `REP` limpia | `2020–25 DESC -0,0915 (t=-1,24)` / `REP +0,1641 (t=+1,06)`; **`Full DESC +0,0157 → REP -0,1032 R_cfd (n=281, PF=0,80, t=-1,41)`** | Negativa en `2020–25 DESC` y en `Full REP`. |
| **`RQ6_ES_NQ`** | `DESC` & `REP` limpia | `2020–25 DESC +0,0810 (t=+2,31) → REP +0,0342 R_cfd (n=383, t=+0,59, p=0,279, corrM=+0,369, W20M=-2,95 R)`; **`Full REP -0,0171 (t=-0,50)`** | Se disuelve en `REP` y además correlaciona `+0,37` con `Core`. |
| **`C2_VBB / C2_DBO / C2_P80`** | `Full DESC` & `REP` | `C2_VBB REP -0,1084 (t=-0,78)`; `C2_P80 DESC -0,0935 / REP +0,0261 (t=+0,20)`; `C2_DBO DESC -0,3761 / REP -0,3712 (t=-2,18)` | Reversión fallida en `REP` (`C2_DBO` destruye capital). |
| **`C2_D7 / C2_IBS / C2_TT / C2_TOM` (`2020–25`)** | `2020–25 DESC` & `REP` | Fallan en `2020–25 DESC`: `D7 -0,0088 (t=-0,11)`, `IBS -0,0468`, `TT -0,0333`, `TOM +0,0219`; en `REP` `t=+0,39..+1,37` (`p>0,085`) | Solo vivieron en `2006–2017` (`D7 +0,145 → -0,009`). |
| **`ES5N_NQ` (`10:00 NY`)** | `DESC` & `REP` limpia | `20yr REP +0,0230 R_cfd (n=218, t=+0,32)`; **`2020–25 REP -0,0599 R_cfd (n=62, PF=0,87, t=-0,49)`** | Edge solo existe en `ES`, no replica en `NQ`. |
| **`HobbieCode Gann HiLo Oro H1`** | `M1 Exacto DESC` (`GC/XAU/FX/IDX`) | H1 optimista (`t=+3,07`) colapsa en M1 exacto: **`GC +0,0142 R_cfd (PF=1,023, t=+0,30, fill 3,4%)`**, `-0,0663 Fut`, `-0,500 Stress`, `1/4` phase-shift `+`, `2011–15 -0,136 R`, `W20M -11,51 R` | **Espejismo de backtest H1 sin intrabar M1**; negativa en futuros y bajistas. |
| **`HobbieCode Supertrend Oro H1`** | `M1/H1 DESC` + grilla `6×7` | `GC Baseline +0,0286 R_cfd (t=+0,19, DD=-32 R)`; `2020–25 -0,1859 R (t=-0,63)`; **`PBO=0,574` (`GC`) / `0,523` (`XAU`)**; `XAU` `2/4` phase-shift `+` | **Sobreajuste (`PBO > 0,50`) y falta total de significancia**. |
| **`Dual Thrust GC` (`X038`)** | Ticks `2025–26 DESC` | `-0,177 R_cfd` (`0/4` sub-minuto `+`, `n=15`) aunque `20yr DESC +0,051 R` | Muerta en régimen reciente de oro (`Turtles_GC` la supera ampliamente). |
| **`A20` (`fundedsyncstack`)** | `2012–25 NQ` | **`corrM = +0,335` / `corrD = +0,343` vs `Core`**, `Worst20%M -7,1 R`, `MaxDD -62,4 R` | Falsa cobertura: quema en meses alcistas y no protege caídas de `Core`. |
| **`CVGAP-ES-C`**, `CVGAP2-GC#11`, `COMEX-CIERRE-GC-R#0` | `ATRAS.json` M1 `2008–25` | `-0,044 R/op` (`-33,6 R`), `-0,128 R/op` (`-55,1 R`), `-0,181 R/op` (`-94,4 R`) | Refutadas en 18 años de M1 (`EN_CONTRA_ATRAS`) y `-5,98 R` en forward. |
| **`DRC-NQ-R`**, `TORI-NQ-R`, `U1-ZONAS-AVCL-ES/NQ`, `CVGAP-CFD-NQ` | `BATERIA.json` / `v2,v3` | Fricciones `0,090–0,153 R` (salvo `CVGAP-CFD-NQ` con oct en contra) y `-8,54 R` en `fw20261123` (`DRC`) | Fricción prohibitiva / inelegible; retirar de ejecución. |

---

## 3. Matriz Maestra de Roles en EdgeLab

| Nivel / Rol | Estrategias | Activo(s) | Modo Ejecución | `Corr_M` vs Core | `Worst20%M` (`OOS REP`) | Regla Operativa |
|---|---|---|---|---:|---:|---|
| **1. Core Activo** | **`Core5_R25` (`T+R+SOMEOD+...`)**, **`ESCoreUS500`** | `NQ/MNQ`, `US100`, `US500` | Futuros Intraday-Flat y CFD Intradía | `+1,00` | `-2,41 R` (`Core4`) | Base intocable en parámetros; no re-optimizar en MT5 sobre `2024–26`. |
| **2. Satélite Ortogonal Listo (Producción)** | **`C2_VZ` (`ES+NQ`)** | `US500` + `US100` (o `ES+NQ`) | **Swing CFD / Fut Personal** (hold 1–5d) | **`-0,312`** | **`+3,68 R`** (`+19,73 R` sum `Sh 2,22`) | Prioridad #1 para `FTMO Swing` y Bóveda Personal; amortigua fuerte meses malos del Core. |
| **2. Satélite Ortogonal Listo (Producción)** | **`C2_EVRP` (`ES+NQ`)** | `US500` + `US100` | **Swing CFD / Fut Personal** (hold 1–5d) | **`-0,298`** | **`+5,21 R`** (`+11,07 R` sum `Sh 1,71`) | Co-satélite Swing / reserva para diversificar `C2_VZ`. |
| **2. Satélite Ortogonal Listo (Producción)** | **`Turtles_GC_CFD` (`entrada_stop`)** | `XAUUSD` (o `MGC`) | **Swing CFD / Personal** (cierre viernes) | **`-0,110`** | **`+0,94 R`** (`Sh 2,13`, `DD -1,0 R`) | Prioridad #1 en oro; única que subió fuerte en estancamiento `may–sep 2025` (`+2,61 R`). |
| **2. Satélite Ortogonal Listo (Producción)** | **`RQ5_ES` (`CFD` y `Fut`)** | `US500.cash` / `MES` | **Intraday-Flat** (`16:40 ET`, Fut & CFD) | **`-0,183`** | **`+7,68 R`** CFD / **`+6,84 R`** Fut | **Único satélite validado para Futuros Intraday-Flat** (`LucidFlex`, `Tradeify`, `Topstep`, `The5ers`). |
| **2. Satélite Ortogonal Listo (Producción)** | **`SOM_ES_CFD`** | `US500.cash` | **Intraday-Flat CFD** (`$0` com.) | `+0,011` | **`+8,44 R`** (`Sh 1,16`) | Excelente amortiguador intradía en `The5ers` y `FTMO Swing` (evitar shift `-2m`). |
| **2. Satélite Secundario CFD** | **`ES5N_ES_CFD`** | `US500.cash` | **Intraday-Flat CFD** (`10:00 NY`) | `+0,345` | `-2,53 R` | Peso acotado (`<= 12–15%`); útil para sumar frecuencia en `The5ers` (`PF 1,50` 20a REP). |
| **3. Observación / Forward Activo (`SIN_DECIDIR`)** | **`U1-ZONAS-BT2-ES/NQ`**, **`U1-RACIMOS-GRILLA-NQ`**, **`CONF-CVR-CFD-NQ-R`**, **`CVGAP-CFD-ES-C`**, **`U1-ORO-GRILLA`** | `MNQ`, `MES`, `MGC` | **Demo / Sim Forward** (`1x` mínimo) | No medido 20a | Pendiente `60` ses. | Seguir en demo/`CARTERA v2 limpia` (apagando `CVGAP-ES-C` y `PREAPERTURA-NQ` de `v2`). |
| **3. Observación / Forward Activo (`SIN_DECIDIR`)** | **`FRANKLIN`**, **Veto `PREAPERTURA-ES`**, **`CARTERA_B` (`T+Z+R`)** | `ES/NQ` / `MNQ` | Demo / Sim Tracker | `+0,50` (`NQ`) | `-17,0 R` (`FNQ`) | Seguir e-process y el veto de `PREAPERTURA-ES`; **no asignar capital prop propio a `Franklin_NQ`** por redundancia con Core. |
| **4. Descartadas / Apagadas** | **`BF1..BF8`**, **`Z_RTY`**, **`FM2`**, **`RQ2`**, **`RQ6`**, **`C2_VBB/DBO/P80/D7/IBS/TT/TOM`**, **`ES5N_NQ`**, **`PREAPERTURA Int0 & Int1`**, **`HobbieCode Gann/ST`**, **`A20`**, **`CVGAP-ES-C`**, **`DRC-NQ-R`**, **`TORI`**, **`U1-AVCL`**, **`Dual Thrust GC`** | Todos | **APAGAR / NO OPERAR** | — | — | Retirar inmediatamente de EA/NT8 y scripts productivos. |

---

## 4. Mapa Exacto de Colocación por Cuenta / Prop-Firm (`OOS REP 2020–2025`, `N=3.000`)

Todos los números proceden de [`master_portfolio_opt.py`](file:///C:/Users/Usuario/.gemini/antigravity/brain/6d51dfbd-ecbb-4249-894c-b2e8b3258c4b/scratch/validation_full/master_portfolio_opt.py), [`MASTER_PORTFOLIO_OPT.json`](file:///C:/Users/Usuario/.gemini/antigravity/brain/6d51dfbd-ecbb-4249-894c-b2e8b3258c4b/scratch/validation_full/MASTER_PORTFOLIO_OPT.json) y [`MASTER_MC_PROP.csv`](file:///C:/Users/Usuario/.gemini/antigravity/brain/6d51dfbd-ecbb-4249-894c-b2e8b3258c4b/scratch/validation_full/MASTER_MC_PROP.csv), calibrando la referencia `1.0x` al riesgo diario real de `Core5` (`$851,76/día`; CFD 100K escalado a `0,85x` = `$724/día`). Regla de estrés `REP 60%` = mantiene la misma volatilidad diaria pero recorta el retorno medio al `60%` por degradación en vivo.

### 4.1 Composición Exacta por Cartera (`weights` en múltiplos de volatilidad diaria de cada sleeve)

| Cartera | Tipo / Restricción | Composición (`weights`) y Escala |
|---|---|---|
| **`Core_Solo`** | Baseline sin satélites | `Core4_NQ: 1.00` (calibrado a `$852/d`) |
| **`FUT_Intraday_Core+RQ5_ES_eqvol`** | Futuros Flat `16:40 ET` | `Core4_NQ: 0.80 + RQ5_ES_Fut (MES): 0.25` (normalizado a `$852/d`) |
| **`FUT_Intraday_Core+RQ5_ES_add15`** | Futuros Flat `16:40 ET` (aditivo) | `Core4_NQ: 1.00 + RQ5_ES_Fut (MES): 0.18` (`std $903/d`) |
| **`CFD_Flat_Core+OrthoIntraday_eqvol`** | CFD Flat `16:40 ET` | `Core4_NQ: 0.72 + RQ5_ES_CFD: 0.25 + SOM_ES_CFD: 0.15 + ES5N_ES_CFD: 0.15` (`$852/d`) |
| **`CFD_Flat_Core+OrthoIntraday_add15`** | CFD Flat `16:40 ET` (aditivo) | `Core4_NQ: 1.00 + RQ5_ES_CFD: 0.22 + SOM_ES_CFD: 0.12 + ES5N_ES_CFD: 0.12` (`std $990/d`) |
| **`SWING_Core+Turtles_C2VZ_eqvol`** | **CFD Swing / Personal** | `Core4_NQ: 0.65 + RQ5_ES_CFD: 0.20 + Turtles_GC_CFD: 0.30 + C2_VZ_CFD: 0.28` (`$852/d`) |
| **`SWING_FullOrtho_eqvol`** | **CFD Swing / Personal (Full)** | `Core4_NQ: 0.60 + RQ5_ES_CFD: 0.20 + SOM_ES_CFD: 0.12 + ES5N_ES_CFD: 0.12 + Turtles_GC_CFD: 0.30 + C2_VZ_CFD: 0.28` (`$852/d`) |
| **`SWING_FullOrtho_add15`** | **CFD Swing / Personal (Aditivo)** | `Core4_NQ: 0.90 + RQ5_ES_CFD: 0.22 + SOM_ES_CFD: 0.12 + Turtles_GC_CFD: 0.32 + C2_VZ_CFD: 0.30` (`std $979/d`) |

### 4.2 Resultados Monte Carlo por Prop Firm (`REP 100%` y `REP 60% Stress`)

| Prop Firm / Cuenta | Cartera Recomendada vs Baseline | Sharpe Mezcla | `Worst20%M` (`USD`) | Neto 12m (`100%` / `60%`) | `P(Payout)` (`100%` / `60%`) | `#Payouts/Año` (`100%` / `60%`) | Caja Mín `p10` (`100%` / `60%`) |
|---|---|---:|---:|---:|---:|---:|---:|
| **`LucidFlex 150K`** *(Futuros Flat)* | `Core_Solo` (ref.) | 2,53 | `-$6.503` | `+$11.994` / `+$6.298` | `96,0%` / `80,7%` | `4,90` / `2,83` | `-$857` / `-$1.286` |
| **`LucidFlex 150K`** *(Futuros Flat)* | `FUT_Core+RQ5_ES_eqvol` | 2,47 | **`-$3.745`** (`-42%` DD!) | `+$11.830` / `+$6.301` | `95,2%` / `81,2%` | `4,89` / `2,86` | `-$857` / `-$1.500` |
| **`LucidFlex 150K`** *(Futuros Flat)* | **`FUT_Core+RQ5_ES_add15`** | **2,51** | `-$5.176` | **`+$12.708`** / **`+$6.820`** | **`96,3%`** / **`83,1%`** | **`5,21`** / **`3,07`** | `-$857` / `-$1.500` |
| **`Tradeify / Topstep 150K`** *(Fut. Flat)* | `Core_Solo` (ref.) | 2,53 | `-$6.503` | `+$12.169` / `+$6.534` | `96,1%` / `81,5%` | `4,95` / `2,89` | `-$800` / `-$1.200` |
| **`Tradeify / Topstep 150K`** *(Fut. Flat)* | **`FUT_Core+RQ5_ES_add15`** | **2,51** | `-$5.176` | **`+$12.959`** / **`+$7.070`** | **`96,4%`** / **`84,0%`** | **`5,28`** / **`3,14`** | `-$800` / `-$1.400` |
| **`The5ers HS 100K`** *(CFD Flat)* | `Core_Solo` (ref.) | 2,53 | `-$6.503` | `+$12.141` / `+$5.324` | `91,6%` / `67,6%` | `6,49` / `3,45` | `-$495` / `-$495` |
| **`The5ers HS 100K`** *(CFD Flat)* | `CFD_Flat_Ortho_eqvol` | 2,46 | **`-$2.076`** (`-68%` DD!) | `+$11.685` / `+$5.159` | `91,5%` / `66,2%` | `6,36` / `3,39` | `-$495` / `-$495` |
| **`The5ers HS 100K`** *(CFD Flat)* | **`CFD_Flat_Ortho_add15`** | **2,54** | `-$4.158` | **`+$15.885`** / **`+$7.554`** | **`95,3%`** / **`75,3%`** | **`7,36`** / **`4,20`** | `-$495` / `-$990` |
| **`FTMO Swing 100K`** *(CFD Swing)* | `Core_Solo` (ref.) | 2,53 | `-$6.503` | `+$10.637` / `+$4.242` | `88,2%` / `60,0%` | `5,84` / `2,89` | `-$540` / `-$540` |
| **`FTMO Swing 100K`** *(CFD Swing)* | `SWING_Core+Turtles_C2VZ_eqvol` | **3,61** | **`-$120`** (`-98%` DD!) | `+$19.427` / `+$7.926` | `98,8%` / `79,4%` | `8,98` / `4,66` | **`-$540`** / **`-$540`** |
| **`FTMO Swing 100K`** *(CFD Swing)* | `SWING_FullOrtho_eqvol` | **3,48** | **`+$817`** (positivo!) | `+$18.389` / `+$7.434` | `98,4%` / `77,5%` | `8,68` / `4,44` | `-$540` / `-$540` |
| **`FTMO Swing 100K`** *(CFD Swing)* | **`SWING_FullOrtho_add15`** | **3,47** | **`-$262`** | **`+$22.812`** / **`+$9.967`** | **`99,1%`** / **`83,1%`** | **`9,38`** / **`5,18`** | **`-$540`** / **`-$540`** |
| **`Bóveda Personal $100K`** *(Uncapped)* | `Core_Solo` (ref.) | 2,53 | `-$6.503` | `+$33.945` / `+$20.281` | `99,5%` / `94,1%` | — | `-$10.562` / `-$14.651` |
| **`Bóveda Personal $100K`** *(Uncapped)* | **`SWING_Core+Turtles_C2VZ_eqvol`** | **3,61** | **`-$120`** | `+$48.515` / `+$29.012` | **`100,0%`** / `98,7%` | — | **`-$7.393`** / **`-$11.204`** |
| **`Bóveda Personal $100K`** *(Uncapped)* | **`SWING_FullOrtho_add15`** | **3,47** | **`-$262`** | **`+$53.642`** / **`+$32.066`** | **`100,0%`** / **`98,5%`** | — | `-$9.054` / `-$13.383` |

> [!TIP]
> **El Salto Estructural en FTMO Swing y Bóveda Personal:** Combinar `Core` + `RQ5_ES_CFD` + `Turtles_GC_CFD` + **`C2_VZ`** eleva el **Sharpe OOS de `2,53` a `3,47–3,61`**, borra el `Worst20%M` histórico del Core (`-$6.503 → -$120 / +$817`), duplica con creces el **Neto 12m en FTMO Swing (`+$10.637 → +$22.812` al 100%, y `+$4.242 → +$9.967` bajo estrés 60%)**, sube **`P(Payout)` bajo estrés de `60,0%` a `83,1%`** manteniendo el riesgo de caja `p10` clavado en **un solo fee (`-$540`)**, y acorta el **e-process de la cartera swing a `12` meses (`e>=10`) y `15` meses (`e>=20`, `97,3%` en `24m` al `100%`)** en lugar de `83–104` meses esperando estrategias individuales en demo.

---

## 5. Hoja de Ruta Operativa Inmediata (Sin Esperar Meses en Demo)

1. **Apagar hoy mismo (fugas confirmadas):**
   - De `cartera_20261116` en NT8/demo: **apagar `CVGAP-ES-C` (`-5,98 R` forward, refutada M1), `PREAPERTURA-NQ Intento 1` (`-3,67 R` forward, artefacto reloj), `DRC-NQ-R` (`-8,54 R` forward, fric `0,153 R`) y `TORI-NQ-R`**. Dejar corriendo en `v2 limpia` solo el bloque de footprint/zonas todavía vivo (`U1-ZONAS-BT2-ES`, `U1-RACIMOS-GRILLA-NQ`, `CONF-CVR-CFD-NQ-R`, `U1-ZONAS-BT2-NQ`, `U1-ORO-GRILLA`, `CVGAP-CFD-ES-C`) hasta juntar `60` sesiones.
   - Descartar completamente `HobbieCode Gann HiLo / Supertrend`, `BF1..BF8`, `Z_RTY`, `FM2`, `RQ2`, `RQ6`, `A20`, `C2_VBB/DBO/P80` y `PREAPERTURA Intento 0`.
2. **En MT5 (`EdgeLabFundedSyncESCoreUS500` / `Core5`):**
   - **NO correr optimización `Lenta (repaso completo)` sobre `2024.01–2026.11` en el Probador de Estrategias de MT5** (re-optimizar parámetros sobre `REP + HOLDOUT` destruye la validez fuera de muestra); usar el `.set` congelado y verificado de fábrica en EdgeLab.
3. **Prioridad de Codificación a EA (`MQL5` / `NinjaScript`) para Producción Inmediata (`Tier 1+2` ya validado en `REP` limpia):**
   - **Orden #1 — `C2_VZ` (`ES+NQ`, `VIX z<-1`) + `Turtles_GC_CFD` (`XAUUSD`):** desbloquean el salto de `Sharpe 2,53 → 3,61` en **`FTMO Swing 100K`** (hasta **`9,38` payouts/año**) y **`Bóveda Personal`**. (`C2_EVRP` queda como segundo módulo opcional de `CARRIL2`).
   - **Orden #2 — `RQ5_ES` (`MES` / `US500.cash`):** único satélite intraday-flat con pase completo en `Fut + CFD` (`+12,7k–$13,0k` neto 12m en **`LucidFlex 150K`** y **`Tradeify / Topstep 150K`**, recortando `Worst20%M` de `-$6.503` a `-$3.745`).
   - **Orden #3 — `SOM_ES_CFD` + `ES5N_ES_CFD` (`0,12x` peso chico):** completan **`The5ers HS 100K`** (`+$15.885` neto 12m, `7,36` payouts/año, `95,3%` `P(pay)`).
4. **Protocolo diario para seguir creciendo el holdout sellado sin fricciones:**
   - Futuros NT8: `python E:\EdgeLab-fundedsync\tools\nt8_sellado_diario.py diario --espejo C:\EdgeLab\sellado --fuente E:\DatosNT8\HOLDOUT_SELLADO`
   - Spot Dukascopy: estrategia `HDAUTO_SPOT_NOV.java` en `JForex4` (ajustar fecha inicio) → `sync_jforex_bin_sellado.py` → `kaggle datasets version -p C:\EdgeLab\sellado`.
   - Lanzar únicamente los runners preregistrados (`cartera_v2_forward`, `fundedsync_cadena`, `franklin_seguimiento`, `som_seguimiento`, `turtles_oro_seguimiento`, `regimen_forward`).
