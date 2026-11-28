# Auditoría de Falsos Negativos, Mesetas, Phase-Shift y Cartera Ortogonal para Acelerar Payouts y Reducir Espera Forward

Estado: VIGENTE (documento de la validación de producción, 2026-11; encabezado agregado el 2026-11-25)  

> [!IMPORTANT]
> **Integridad A5 verificada en todos los scripts:** No se abrió ni calculó P&L en ninguna partición sellada:
> - `FLUJOS_MACRO` (`FM1–FM8`), `CARRIL2`, `EXTERNAS_ESTRUCTURALES` (`ES5N`, `Dual Thrust`), `MEJORA-SF` y `Z_RTY` se evaluaron **estrictamente en `DESC` (`bloque == "DESC"`)**; su `REP` y `HOLDOUT` permanecen intactos.
> - `SOM` y `FRANKLIN` base se evaluaron únicamente en `DESC` y `REP` (sin leer `HOLDOUT`).
> - `RQ5` (`DESC`, `REP`, `HOLDOUT` hasta `2026-09-30`), `Turtles Oro` y `Core5 / ESCoreUS500` (`<= 2026-09-30`) ya cuentan con aperturas registradas previas; el terminal (`>= 2026-10-01`) y `E:\DatosNT8\HOLDOUT_SELLADO` (`2026-11-01..2026-11-23`) no fueron leídos en sus retornos.

---

## 1. Errores Metodológicos y Falsos Negativos Detectados en EdgeLab

El repaso cuantitativo de [audit1_epoch_cfd_and_plateaus.py](file:///C:/Users/Usuario/.gemini/antigravity/brain/6d51dfbd-ecbb-4249-894c-b2e8b3258c4b/scratch/audit1_epoch_cfd_and_plateaus.py) y [audit2_phase_shift_local.py](file:///C:/Users/Usuario/.gemini/antigravity/brain/6d51dfbd-ecbb-4249-894c-b2e8b3258c4b/scratch/audit2_phase_shift_local.py) sobre los `.csv.gz` y M1/ticks locales reveló **7 fuentes concretas de falsos negativos y sesgos opuestos**:

| # | Error / Sesgo Detectado | Estrategias Afectadas | Evidencia Cuantitativa Verificada |
|---:|---|---|---|
| **1** | **Dilución de época `2006–2017` + fricción de futuros sobre precios bajos** | `RQ5 (ES/NQ)`, `SOM (ES/NQ)`, `FRANKLIN (NQ/ES)`, `FM1`, `FM2/FM2N`, `Dual Thrust` | En `2006–2017` la fricción canónica de futuros comía `0,08–0,18 R` por operación (`NQ 1.859 → 15.022`, `ES 1.233 → 4.478`). Promediar `2006–2025` enterró bordes reales de `2020–2025`. Ej.: `FRANKLIN NQ` pasó de `-0,041 R (DESC)` / `-0,118 R (REP)` en `2006–17` a **`+0,098 R (DESC)` / `+0,143 R (REP)`** en `2020–25`. |
| **2** | **Evaluación únicamente con fricción de futuros en estrategias aptas para CFD RTH (`$0` comisión)** | `RQ5 ES`, `SOM ES`, `FM1/FM2 NQ`, `Turtles Oro` | En CFD RTH (`HardFlatten = 16:40 ET`, cero swap nocturno), la fricción baja **-36,5% en NQ** (`1,5455 → 0,981 pts`), **-60,6% en ES** (`0,8877 → 0,350 pts`) y **-50,4% en GC** (`0,6050 → 0,300 pts`). **`RQ5 ES` `2020–25 DESC` salta de `+0,1157 R_fut` a `+0,1387 R_cfd` (`t = +3,04`, `sin3mej = +0,0893`)** y su `REP` sube de `+0,0561` a `+0,0765 R_cfd`. |
| **3** | **Sesgo de época INVERSO en `CARRIL2`** | `C2_D7`, `C2_IBS`, `C2_TT` vs **`C2_VZ`** | La reversión clásica de corto plazo **sólo vivió en `2006–2017`** (`C2_D7 +0,145 R t=+2,77 → -0,009 R` en `2020–25`; `C2_IBS +0,096 → -0,047 R`; `C2_TT +0,116 → -0,033 R`). En contraste, **`C2_VZ` (`Z-score` compresión VIX < -1)** se fortaleció en el régimen moderno (`+0,042 R` en `2006–17` → **`+0,1336 R t=+2,99` en `2018–25` DESC**, **`+0,1086 R t=+2,09` en `2020–25` DESC**). |
| **4** | **Artefacto de reloj sub-minuto oculto en `PREAPERTURA-NQ` (`Intento 1`) + escala histórica** | `PREAPERTURA-NQ (Intento 1)` vs `Intento 0` | En [ATRAS.json](file:///E:/EdgeLab-fundedsync/docs/research/atras_m1_20261117/ATRAS.json), `PREAPERTURA-NQ` perdió `-548,6 R` en `2006–17`, `-29,2 R` en `2018–19` y ganó **`+27,7 R` en `2020–22` (`3/3` años `+`)**. Pero al correr *phase-shift* sobre 95M de ticks reales de `NQ` (`2025-08..2026-07`), **`Intento 1` (reentrada) colapsó de `+48,3 R (d00s)` a `+0,2 R (d15s)` y `-20,0 R (d45s)`** (`-39,2 R` a `-2m`). En cambio, **`Intento 0` (primer quiebre, sin reentrada) mantuvo `+24,5 R` (`4/4` sub-minuto `+`, `5/5` multi-minuto `+`, `medRet = 100%`)**. |
| **5** | **Hallazgo enterrado en controles de campaña (`ES5N`)** | `EXTERNAS_ESTRUCTURALES` (`ES5N`) | `ES5` (fade de `RSI10`) perdió, pero su control pre-registrado **`ES5N` (continuación 10:00 NY tras `|open-drive 30m| >= 0,12·ATR20` con `RSI10` neutro `40..60`)** ganó **`+0,0827 R_fut` en ES (`n=704`) y `+0,0777 R_fut` en NQ (`n=765`) en `2006–2025 DESC`**. En `ES M1 2020–25 CFD` rindió **`+0,202 R/op` (`5/5` phase shifts `+`, `corr=0,924`)**. |
| **6** | **Rechazo por potencia individual (`K49`) + desfase de ramas git** | `Turtles GC`, `Z_RTY`, `FM2`, `C2_VZ`, `RQ5` | Varias estrategias reales con `1,5–6 ops/mes` fueron frenadas por falta de potencia individual (requerían `60–120` meses solas). Además, la rama local `fix/fundedsync-il-parity` se ramificó antes de PR #202 (`RQ5`, `canasta_correlacion_20261120`, `filtros_contexto_20261120` estaban sólo en `origin/foundation/f0b-compatibility-probe`). |
| **7** | **Falsa expectativa de cobertura en `A20` y redundancia oculta en `FRANKLIN_NQ`** | `A20`, `FRANKLIN_NQ` | Aunque `A20` tiene beta negativa a `NQ` (`-0,51`), **su correlación mensual con `Core4` es positiva (`+0,335` mensual / `+0,343` diaria)**: gana los mismos días bajistas que `T` y quema en meses alcistas (`Worst20%M = -7,1 R`, `MaxDD -62,4 R`). Por su parte, `FRANKLIN_NQ` tiene **`corrD = +0,505` con `Core4_NQ` (`Worst20%M = -17,0 R`)** y reduce el neto de prop MC al mezclarlo a igual volatilidad. |

---

## 2. Mesetas, PBO (`CSCV s=16`), `N_eff` y Desplazamiento Horario de Velas M1 (*Phase-Shift*)

### 2.1 Mesetas y PBO en Grillas (`2020–2025` / `2018–2025`)

| Familia / Activo | Partición | Variantes | % Celdas > 0 | Mediana Grilla (CFD/Fut) | Fábrica | `PBO (s=16)` | `N_eff` | Diagnóstico Meseta |
|---|---|---:|---:|---:|---:|---:|---:|---|
| **`RQ5 NQ` (CFD)** | `DESC 2020–25` | 324 | **100,0%** | **+0,0955** (`+0,0899` fut) | +0,1032 | **0,091** | 1,79 | Meseta sólida total |
| **`RQ5 ES` (CFD)** | `DESC 2020–25` | 324 | **100,0%** | **+0,1036** (`+0,0791` fut) | +0,1387 | **0,346** | 1,63 | Meseta sólida total |
| **`FRANKLIN NQ` (CFD)** | `DESC 2020–25` | 32 | **100,0%** | — | +0,1064 | 0,544 | 2,75 | Meseta positiva; alta corr con Core |
| **`FRANKLIN ES` (CFD)** | `DESC 2020–25` | 32 | 78,1% | — | +0,1384 | **0,185** | 3,48 | Meseta buena (pero `REP -0,017 R`) |
| **`SOM NQ` (CFD)** | `DESC 2020–25` | 81 | 90,1% | — | +0,0553 | **0,155** | 1,72 | Meseta estable (`SOMEOD` ya en Core5) |
| **`SOM ES` (CFD)** | `DESC 2020–25` | 81 | **100,0%** | — | +0,0463 | 0,906 | 1,71 | Todas >0 (`REP +0,042 R`), pero elegir máx sobreajusta |
| **`Z RTY` (Fut)** `[DESC_ONLY]` | `DESC 2018–25` | 27 | **100,0%** | **+0,1725** | +0,1650 | 0,668 | 3,98 | Meseta en Russell (`96,3% >0` en `2020+`) |
| **`Dual Thrust GC`** | Ticks `2025–26` (`n=11..39`) | 8 (`k×rr`) | 0% (reciente) | -0,13 a -0,18 | -0,177 | — | — | **Positivo en 20a DESC (`+0,051 R`, `n=900`), pero negativo en `2025–26` (`n=15`)** |

### 2.2 Resultados de *Bar-Open Phase Shift* (Multi-Minuto `±2m` y Sub-Minuto `{0,15,30,45}s`)

| Estrategia | Activo y Muestra | Tipo Shift | Base (`0`) | Fases > 0 | Retención Mediana | Corr. Diaria vs Base | Veredicto |
|---|---|---|---:|---:|---:|---:|---|
| **`RQ5_ES_CFD`** | `ES M1 2020–25 DESC` (`n=525`) | Multi-min `{-2..+2}m` | `+45,0 R` (`+0,086/op`) | **5 / 5** | **100,0%** | **0,883** | **PASA ROBUSTO** |
| **`ES5N_ES_CFD`** `[DESC]` | `ES M1 2020–25 DESC` (`n=162`) | Multi-min `{-2..+2}m` | `+32,7 R` (`+0,202/op`) | **5 / 5** | **100,7%** | **0,924** | **PASA ROBUSTO** |
| **`FRANKLIN_ES_CFD`** | `ES M1 2020–25 DESC` (`n=292`) | Multi-min `{-2..+2}m` | `+33,4 R` (`+0,115/op`) | **5 / 5** | **146,7%** | 0,781 | Pasa shift, falló `REP` ES |
| **`SOM_ES_CFD`** | `ES M1 2020–25 DESC` (`n=845`) | Multi-min `{-2..+2}m` | `+17,3 R` (`+0,020/op`) | **4 / 5** (`-2m: -3,1 R`) | 99,7% | 0,752 | **PASA** (evitar `-2m`) |
| **`SOM_NQ_CFD`** | `NQ Ticks 2025–26` (`n=191`) | Sub-min `{0..45}s` / Multi `±2m` | `+20,3 R` (`+0,106/op`) | **4/4** y **5/5** | **83,8% / 100%** | **0,863 / 0,824** | **PASA ROBUSTO** |
| **`RQ5_NQ_CFD`** | `NQ Ticks 2025–26` (`n=122`) | Sub-min `{0..45}s` / Multi `±2m` | `+8,7 R` (`+0,071/op`) | **4/4** y **4/5** | **86,6% / 50,4%** | 0,745 / 0,807 | **PASA** (`d15s +10,3 R`) |
| **`PREAPERTURA_NQ_Int0`** | `NQ Ticks 2025–26` (`n=192`) | Sub-min `{0..45}s` / Multi `±2m` | `+24,5 R` (`+0,128/op`) | **4/4** y **5/5** | **72,3% / 100%** | **0,881 / 0,819** | **PASA** (1er quiebre) |
| **`PREAPERTURA_NQ_Int1`** | `NQ Ticks 2025–26` (`n=148`) | Sub-min `{0..45}s` / Multi `±2m` | `+48,3 R` (`+0,326/op`) | **2/4** y **3/5** | **-11,2%** / 55,8% | 0,724 / 0,723 | **FRÁGIL AL RELOJ** (`d45s -20 R`) |
| **`FRANKLIN_NQ_CFD`** | `NQ Ticks 2025–26` (`n=73`) | Sub-min `{0..45}s` | `+0,8 R` (`+0,010/op`) | **2 / 4** (`-3,9/-5,1 R`) | -208% | 0,831 | Débil en 2025–26 sub-min |
| **`DT_X038_GC`** | `GC Ticks 2025–26` (`n=15`) | Sub-min `{0..45}s` | `-2,6 R` CFD (`-0,177/op`) | **0 / 4** | 50,4% | 0,818 | Negativa en muestra 2025–26 |

---

## 3. Veredicto sobre las Estrategias de la Captura (`Estabilidad mensual en R2.html`)

Clasificación exacta cruzando [BATERIA.json](file:///E:/EdgeLab-fundedsync/docs/research/cartera_20261116/BATERIA.json), [ATRAS.json](file:///E:/EdgeLab-fundedsync/docs/research/atras_m1_20261117/ATRAS.json) y el nuevo *phase-shift* en ticks reales:

1. **Refutadas en M1 histórico (incluso tras corregir bug K40):**
   - **`CVGAP-ES-C`**: en M1 `2018–2025` dio `-0,044 R/op` (`n=769`, `-33,6 R`, sólo `3/8` años `+`; `-3,2 R` en `2020–25`). **Descartada (`EN_CONTRA_ATRAS`)**.
2. **Falso negativo parcial resuelto (pero frágil al reloj exacto):**
   - **`PREAPERTURA-NQ` (`Intento 1`)**: no perdió `-0,188 R/op` en `2018–22` (era bug K40), sino `-0,002 R/op` (`+27,7 R` en `2020–22`). Sin embargo, **su sub-minuto phase-shift en ticks `2025–26` colapsa de `+48,3 R (00s)` a `-20,0 R (45s)`**. No escalar `Intento 1`; explorar en cambio **`Intento 0` (primer quiebre)** que sí pasó `4/4` y `5/5` shifts (`+24,5 R`).
3. **Estrategias de Ticks / Footprint / CFD NUNCA evaluadas en M1 18 años (siguen vivas como bloque ortogonal `cartera_20261116` `v2`):**
   - **`U1-RACIMOS-GRILLA-NQ`** (`TickDev +0,165 R`, `fric 0,017 R`, elegible `6/6`), **`U1-ZONAS-BT2-NQ`** (`+0,087 R`, `fric 0,032`, `6/6`), **`U1-ZONAS-BT2-ES`** (`+0,097 R`, `fric 0,047`, `6/6`), **`CONF-CVR-CFD-NQ-R`** (`+0,135 R`, `fric 0,034`, `6/6`), **`CVGAP-CFD-ES-C`** (`+0,073 R`, `fric 0,040`, `6/6`).
   - Descartadas por regla en `v2`: `CVGAP-CFD-NQ` (octubre en contra), `U1-ZONAS-AVCL-NQ/ES` y `DRC-NQ-R` (`fric 0,09–0,15 R`), `TORI-NQ-R` (`fric 0,080 R`), `U1-CRUZADO` (sin datos/elegibilidad).
   - **La exportación de ticks de noviembre (`2026-11-01..23`) destraba el holdout conjunto de este bloque de footprint.**

---

## 4. Ortogonalidad vs `Core5_R25`, Mitigación de Drawdown/Estancamiento y Payouts Prop

Todos los números de abajo provienen de [audit3_orthogonality_eprocess_and_mc.py](file:///C:/Users/Usuario/.gemini/antigravity/brain/6d51dfbd-ecbb-4249-894c-b2e8b3258c4b/scratch/audit3_orthogonality_eprocess_and_mc.py) y [audit3_mc_prop.csv](file:///C:/Users/Usuario/.gemini/antigravity/brain/6d51dfbd-ecbb-4249-894c-b2e8b3258c4b/scratch/audit3_mc_prop.csv) (validación `Core4_Proxy` vs `Core5_Exact` en `2025-01..07`: `corr = 0,7806`, riesgo diario normalizado al real `$851,8/día` de `Core5`).

### 4.1 Correlación y Amortiguación Real en Meses Malos / Estancamiento

| Candidato | Partición | Corr. Diaria vs Core | Corr. Mensual vs Core | Retorno en **peores 20% meses Core** (`Core = -10,1 R`) | Ventana Estancamiento `2025-05..09` (`Core5 = +0,69 R`) | Sharpe | MaxDD R |
|---|---|---:|---:|---:|---:|---:|---:|
| **`Turtles_GC_CFD` (`entrada_stop`)** | `OPEN D+R` | **+0,006** | **-0,021** | **+1,0 R** (en `1,9 op/m`) | **+2,61 R** (`corr = +0,023`) | 0,97 | -1,5 |
| **`RQ5_ES_CFD` (`US500.cash`)** | `OPEN D+R` | +0,339 | +0,265 | **+3,4 R** | -4,75 R (`corr = +0,312`) | **1,54** | -14,5 |
| **`SOM_ES_CFD` (`US500.cash`)** | `OPEN D+R` | +0,363 | +0,428 | -13,1 R | — | 0,97 | -19,0 |
| **`FRANKLIN_NQ_CFD`** | `OPEN D+R` | +0,505 | +0,452 | -17,0 R | — | 0,90 | -14,8 |
| **`C2_VZ` (VIX compresión `z<-1`)** | `[DESC_ONLY]` | **-0,030** | **-0,314** | **+14,8 R** *(vs Core DESC `-7,8 R`)* | — | 0,87 | -5,7 |
| **`Z_RTY` (mediana grilla)** | `[DESC_ONLY]` | **-0,021** | **-0,113** | **+7,8 R** *(vs Core DESC `-7,8 R`)* | — | 0,09 | -20,1 |
| **`FM2_NQ_CFD` (Concretum Band)** | `[DESC_ONLY]` | +0,446 | +0,479 | -9,9 R | — | 1,34 | -10,7 |
| **`FM1_NQ_CFD`** | `[DESC_ONLY]` | +0,402 | +0,477 | -5,7 R | — | 1,38 | -11,0 |

> [!TIP]
> **Lección estructural clave sobre el estancamiento:** En índices intraday (`Core5`, `RQ5`, `Franklin`, `SOM`), todos comparten exposición al flujo direccional de RTH de acciones US (`corr 0,34–0,51`). Quienes **realmente amortiguan el estancamiento y los peores meses de `Core5`** son los activos/mecanismos fuera de esa dirección: **`Turtles_GC` (oro, `corr ≈ 0,00`, `+2,61 R` en mayo–sep 2025)**, **`C2_VZ` (`corrM = -0,314`, `+14,8 R` en peores 20% meses)**, y **`Z_RTY` (`corrM = -0,113`, `+7,8 R`)**.

### 4.2 Impacto en Prop Firms (`N=2.000` rutas bootstrap sobre **`REP` limpio `2020–2025`**, 12 meses = 252 días)

| Cartera (`std` calibrado a `$852/d` en fondeada) | Firm / Régimen | Neto 12m Medio | `P(Retiro)` | `# Retiros / 12m` | Caja Mín `p10` | Efecto |
|---|---|---:|---:|---:|---:|---|
| **`Core4_Base`** | `LucidFlex 150K` (`REP 100%`) | `+$12.993` | 97,2% | 5,32 | `-$857` | Referencia |
| **`Core4 + RQ5_ES_CFD`** *(igual vol)* | `LucidFlex 150K` (`REP 100%`) | `+$13.258` | **97,8%** | **5,47** | `-$857` | `+3%` payouts, mejor `Calmar` |
| **`Core4 + Turtles_GC (0,35x)`** *(igual vol)* | `LucidFlex 150K` (`REP 100%`) | **`+$15.263`** | **98,9%** | **6,13** | **`-$643`** | **`+$2.270` neto y `-25%` caja riesgo** |
| **`Core4 + Ortho4_CFD`** *(igual vol)* | `LucidFlex 150K` (`REP 100%`) | **`+$13.946`** | **97,6%** | **5,70** | `-$857` | **`+$953` neto, `+0,38` retiros/cuenta** |
| **`Core4 + Ortho4 (+15% aditivo)`** | `LucidFlex 150K` (`REP 100%`) | **`+$15.425`** | **98,5%** | **6,30** | `-$1.071` | **`+0,98` retiros/año por cuenta** |
| `Core4_Base` → `Core4 + Turtles (0,35x)` → `+Ortho4 (+15%)` | `LucidFlex 150K` (**`REP 60% Estrés`**) | `+$7.070` → `+$8.090` → **`+$8.448`** | `85,0%` → `88,0%` → **`89,2%`** | `3,18` → `3,52` → **`3,81`** | `-$1.500` / `-$1.286` / `-$1.735` | Sube `P(pay)` hasta `+4,2 pp` bajo estrés |
| **`Core4_Base`** | `FTMO Swing 100K` (`REP 100%`) | `+$14.658` | 92,3% | 6,33 | `-$540` | Referencia CFD Intradía (`$0` swap) |
| **`Core4 + Turtles_GC (0,35x)`** *(igual vol)* | `FTMO Swing 100K` (`REP 100%`) | **`+$18.727`** | **97,5%** | **7,57** | `-$540` | **`+$4.069` (+28%), `+1,24` retiros** |
| **`Core4 + Ortho4_CFD`** *(igual vol)* | `FTMO Swing 100K` (`REP 100%`) | **`+$16.111`** | **94,8%** | **6,88** | `-$540` | **`+$1.453`, `+0,55` retiros** |
| **`Core4 + Ortho4 (+15% aditivo)`** | `FTMO Swing 100K` (`REP 100%`) | **`+$20.528`** | **96,5%** | **7,57** | `-$540` | **`+$5.870` (+40%) con riesgo fijo `$540`** |
| **`Core4_Base` → `+Ortho4 (+15%)`** | `FTMO Swing 100K` (**`REP 60% Estrés`**) | `+$6.542` → **`+$9.855`** | `69,4%` → **`78,8%`** | `3,39` → **`4,31`** | `-$1.080` | **`+9,4 pp P(pay)` y `+51%` neto bajo estrés** |
| **`Core4_Base` → `+Turtles` → `+Ortho4 (+15%)`** | `The5ers HS 100K` (`REP 100%`) | `+$16.224` → `+$20.329` → **`+$22.119`** | `95,3%` → `98,5%` → **`97,9%`** | `7,02` → `8,23` → **`8,14`** | `-$495` | Payouts máximos en estático CFD |

> [!WARNING]
> **Advertencia sobre `Turtles_GC` en cuentas intraday-flat:** `Turtles_GC` mantiene posiciones multi-día (cierre el viernes): **NO entra en LucidFlex / Tradeify** (obligan flat `16:40 ET`), sí califica perfecto en **`FTMO Swing 100K`** (sin restricción de fin de día) y **Bóveda Personal (`MGC`)**.

---

## 5. Estrategia Concreta para Minimizar / Mitigar la Espera de Forward desde Hoy

En [audit3_orthogonality_eprocess_and_mc.py](file:///C:/Users/Usuario/.gemini/antigravity/brain/6d51dfbd-ecbb-4249-894c-b2e8b3258c4b/scratch/audit3_orthogonality_eprocess_and_mc.py) medimos exactamente la espera del `EProceso` de [secuencial.py](file:///E:/EdgeLab-fundedsync/edgelab/funnel/secuencial.py):
- **Individuo suelto:** `Franklin_NQ` tarda **`94` meses**, `SOM_ES` **`86` m**, `Turtles_GC` **`83` m**, `C2_VZ` **`104` m**, `RQ5_ES` **`43` m** para cruzar `e >= 20` (al 100% del efecto).
- **Canasta agrupada (*Pooled Orthogonal Sleeve*, 4 estrategias `D+R`):** baja la espera a **`31` m (`e>=10`) / `39` m (`e>=20`)** al agrupar varianza ortogonal.
- **Evaluación integrada en cartera (`Core + Manga Ortogonal`, `Sharpe = 2,70`):** cruza `e >= 10` en **`18` meses** y `e >= 20` en **`22` meses** (`64%` de probabilidad dentro de `24` meses).

**Cómo mitigarlo operativamente sin quedarte meses parado en demo:**

1. **Tier 1 — Despliegue Inmediato Hoy (Ya pasaron `DESC + REP` + Meseta + *Phase-Shift*):**
   - **En FTMO Swing / The5ers (`CFD RTH`, cierre `16:40 ET` salvo `Turtles_GC` en FTMO Swing):** Sumar a `Core5_R25 (US100) + ESCore (US500)` una **Manga Ortogonal CFD al 20% del presupuesto de riesgo** compuesta por **`RQ5_ES_CFD` (`US500.cash`)** + **`Turtles_GC_CFD` (`XAUUSD`, solo FTMO Swing / Personal)** + **`SOM_ES_CFD`** (opcional a `0,25x`). El riesgo máximo del portfolio no aumenta si mantienes la suma `w` calibrada, y en el peor escenario el drawdown se acota al fee (`$495–$540`).
   - **En LucidFlex / Tradeify (futuros `NQ/ES`, flat `16:40 ET`):** Mantener `Core5_R25` (`SpeedEval -> Core5_R25`) + **manga `RQ5_ES` (`MES`) al `0,25x` en cuentas `150K`** (`5/5` phase shifts positivos, `100%` grilla positiva). No agregar `A20` ni `Franklin_NQ` (redundancia `0,50` con `Core5`).
2. **Tier 2 — Destrabe Histórico Inmediato SIN Esperar Forward (Pre-registrar y abrir `REP` sellado en Kaggle):**
   Tienes `3` estrategias con señal limpia en `DESC` (`2018–2025`) cuyo `REP` (y `HOLDOUT`) **todavía están vírgenes** — abrir su `REP` te da **`~14–22` meses equivalentes de historia limpia fuera de muestra en 1 hora**, reemplazando casi 2 años de espera forward:
   - **`ES5N` (`ES` + `NQ`, `10:00 NY`, `RSI10` neutro `40..60`, `SL 0,45·ATR20`):** `+0,202 R/op` en `ES 2020–25 CFD` (`5/5` shifts `+`, `corr 0,924`), sin look-ahead. Pre-registrar **una sola hipótesis** en `ES+NQ` (`CFD` y `Fut`) y abrir su `REP` sellado.
   - **`FM2 + FM2N` en `NQ` (`Open_930 ± 0,50·ATR14`, `12,2 ops/mes`):** `+0,094 R_cfd` en `DESC 2020–25`. Pre-registrar `FM2|FM2N` en `NQ` (`2020–2025` época moderna, `CFD` + `Fut`) para abrir `REP` limpio.
   - **`C2_VZ` (`CARRIL2` compresión `VIX z<-1`) + `Z_RTY`:** las dos mejores coberturas reales (`corrM = -0,314` y `-0,113`; `+14,8 R` y `+7,8 R` en los peores meses de `Core`). Pre-registrar apertura de `REP` para `C2_VZ` (para `FTMO Swing` / Bóveda Personal) y para `Z_RTY` (medir spread real de `M2K` primero).
3. **Tier 3 — Validación de `cartera_20261116` Footprint/Ticks + E-Proceso Agrupado por Fee Acotado:**
   - Subir los ticks de noviembre (`2026-11-01..23`) recién exportados a Kaggle para evaluar el holdout completo de **`U1-RACIMOS-GRILLA-NQ`, `U1-ZONAS-BT2-NQ/ES`, `CONF-CVR-CFD-NQ-R` y `CVGAP-CFD-ES-C`** (ya compilados en NT8).
   - Para todo lo que quede en vigilancia (*live forward*), correr un **único `EProceso` de cartera sobre la manga ortogonal combinada** en cuentas con **pérdida acotada al fee** (`1x FTMO Swing 100K` o `1x FundedNext/Lucid promo` a riesgo chico `0,25x`), de modo que recolectas `e-valor` real mientras la asimetría del payout cubre el costo de la prueba.

---

## 6. Estado de `E:\DatosNT8\HOLDOUT_SELLADO` (Listo para Subir a Kaggle)

Verificado en modo **solo lectura** (metadatos sin abrir precios/retornos):
- Carpeta origen: [`E:/DatosNT8/HOLDOUT_SELLADO`](file:///E:/DatosNT8/HOLDOUT_SELLADO) (`SELLADO.txt`: `2026-11-24T23:56:05Z EDGE_TICKHIST_V3_HOLDOUT_SELLADO`).
- Cobertura exacta en las 4 subcarpetas (`ES_12-26`, `GC_12-26`, `NQ_12-26`, `YM_12-26`): **20 archivos `.Last.utc.txt` por instrumento (`20261101` → `20261123`)** + `manifest.jsonl`, completos hasta las `21:01`.
- Espejo local [`C:/EdgeLab/sellado`](file:///C:/EdgeLab/sellado) (`dataset-metadata.json` presente) y credenciales `C:\Users\Usuario\.kaggle\kaggle.json` verificados.
- Comando exacto listo para ejecutar en cuanto confirmes:
  ```powershell
  python E:\EdgeLab-fundedsync\tools\nt8_sellado_diario.py diario --espejo C:\EdgeLab\sellado --fuente E:\DatosNT8\HOLDOUT_SELLADO
  ```
