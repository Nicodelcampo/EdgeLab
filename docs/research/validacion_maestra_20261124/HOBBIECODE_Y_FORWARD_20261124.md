# Subida de Ticks NT8, Resultados Forward (`2026-11-23`) y Auditoría A5 de `@hobbiecode` (Gann HiLo y Supertrend Oro H1)

> [!IMPORTANT]
> **Integridad A5 / A4 verificada:**
> - **Holdout sellado:** Los ticks de NT8 (`E:\DatosNT8\HOLDOUT_SELLADO`) se procesaron estrictamente mediante [`nt8_sellado_diario.py`](file:///E:/EdgeLab-fundedsync/tools/nt8_sellado_diario.py) sin leer retornos ni precios fuera de los runners pre-registrados (`cartera_v2_forward.py`).
> - **Estrategias `@hobbiecode`:** Todas las métricas, ablaciones, grillas (`CSCV s=16`), *phase-shifts* y correlaciones se evaluaron **exclusivamente sobre la partición `DESC` (`bloque == "DESC"` < `2026-10-01`)** de [`hobbiecode_gann_st_desc.py`](file:///C:/Users/Usuario/.gemini/antigravity/brain/6d51dfbd-ecbb-4249-894c-b2e8b3258c4b/scratch/hobbiecode/hobbiecode_gann_st_desc.py) y [`gann_m1_verify.py`](file:///C:/Users/Usuario/.gemini/antigravity/brain/6d51dfbd-ecbb-4249-894c-b2e8b3258c4b/scratch/hobbiecode/gann_m1_verify.py). `REP`, `HOLDOUT`, `EMBARGO` y `TERMINAL` no fueron abiertos.

---

## 1. Subida a Kaggle (`edgelab-holdout-sellado` v8) y Estado del Spot

1. **Sincronización segura de [`C:/EdgeLab/sellado`](file:///C:/EdgeLab/sellado):**
   - El espejo local estaba desactualizado al `2026-11-02`; se respaldó en `C:\EdgeLab\sellado_bak_20261102` y se ejecutó `nt8_sellado_diario.py iniciar` descargando la versión 7 del `2026-11-16`.
2. **Conversión de [`E:/DatosNT8/HOLDOUT_SELLADO`](file:///E:/DatosNT8/HOLDOUT_SELLADO):**
   - **`ES`, `NQ`, `YM` (`20261116..20261123`, 6 sesiones cada uno):** todas **100% completas (`tarde 0.0 min, temprano 0.0 min`)**.
   - **`GC` (`20261102..20261123`, 16 sesiones):** todas **100% completas (`tarde 0.0 min, temprano 0.0 min`)**.
   - **`20261124` (`ES/GC/NQ/YM`):** marcada automáticamente como `INCOMPLETA_NO_SUBIDA` (`temprano 1140.0 min`), excluida correctamente sin `--forzar`.
3. **Publicación en Kaggle:**
   - Subida ejecutada con `nt8_sellado_diario.py subir`; **`nicolasbuttaro/edgelab-holdout-sellado` versión 8** confirmada en estado **`ready`** (`lastUpdated: 2026-11-25T01:21:38.513Z`, con todos los parquets hasta `20261123`).
4. **Cobertura del spot Dukascopy en el dataset:**
   - Inspección de metadatos (`time_utc_ns` sin leer retornos) confirmó que `USATECHIDXUSD_ticks.parquet`, `USA500IDXUSD_ticks.parquet` y `XAUUSD_ticks.parquet` llegan hasta **`2026-11-15 23:59:59+00:00`** (viernes `2026-11-13` + primera hora del domingo).
   - Por eso se lanzó `cartera_v2_forward.py` (que sí evalúa las reglas de futuros NT8 `20261116..20261123`), mientras que los runners 100% dependientes de spot posterior al `13-nov` (`fundedsync_cadena`, `franklin_seguimiento`, `som_seguimiento`, `turtles_oro_seguimiento`) quedan listos para correr en cuanto se sincronice Dukascopy vía `dukascopy_descarga.py`.

---

## 2. Resultados Forward (`cartera_v2_forward.py`) hasta `2026-11-23`

Se lanzaron y completaron las **12/12 reglas** (commit `c523d256`) en [`FORWARD.json`](file:///E:/EdgeLab-fundedsync/docs/research/cartera_20261116/FORWARD.json) y [`FORWARD_V3.json`](file:///E:/EdgeLab-fundedsync/docs/research/cartera_20261116/FORWARD_V3.json) (ventana `20261114..20261123`, `6` sesiones con operaciones; `1 R de cartera = USD 200`):

| Cartera / Regla | `n` | `salteadas_M1` | `R_total` | `USD` | `e-valor` | Estado |
|---|---:|---:|---:|---:|---:|---|
| **`CARTERA v2` (Global)** | **6 ses.** | — | **`-13,72`** | **`-$2.744`** | `0,837` | `SIN_DECIDIR` |
| **`CARTERA v3` (Global)** | **6 ses.** | — | **`-16,29`** | **`-$3.257`** | `0,809` | `SIN_DECIDIR` |
| `CVGAP-ES-C` (`v2`, `v3`) | 5 | 0 | `-5,98` | `-$1.195` | `0,812` | `SIN_DECIDIR` |
| `PREAPERTURA-NQ` (`v2`, `v3`) | 4 | 0 | `-3,67` | `-$734` | `0,889` | `SIN_DECIDIR` |
| `U1-ZONAS-BT2-NQ` (`v2`) | 8 | 0 | `-6,27` | `-$1.254` | `0,822` | `SIN_DECIDIR` |
| **`U1-ZONAS-BT2-ES`** (`v2`) | 4 | 0 | **`+2,20`** | **`+$439`** | `1,073` | `SIN_DECIDIR` |
| `DRC-NQ-R` (`v3`) | 3 | 3 | `-8,54` | `-$1.709` | `0,761` | `SIN_DECIDIR` |
| **`U1-ZONAS-AVCL-ES-C`** (`v3`) | 1 | 0 | **`+0,77`** | **`+$154`** | `1,025` | `SIN_DECIDIR` |
| **`U1-ZONAS-AVCL-NQ`** (`v3`) | 2 | 0 | **`+1,13`** | **`+$227`** | `1,037` | `SIN_DECIDIR` |
| `U1-RACIMOS-GRILLA-NQ` + reglas spot (`CONF-CVR`, `U1-ORO`, `CVGAP-CFD`) | 0 | 0 | `0,00` | `$0` | `1,000` | Sin ops / sin spot |

> [!NOTE]
> **Coherencia con la auditoría previa:** En apenas 6 sesiones reales de noviembre (`20261116..20261123`), **`-9,65 R` (`-$1.930`) de los `-13,72 R` de `v2` provienen exactamente de `CVGAP-ES-C` (`-5,98 R`, refutada en M1 2018–2025) y `PREAPERTURA-NQ` (`-3,67 R`, frágil sub-minuto en `Intento 1`)**. Mientras tanto, `U1-ZONAS-BT2-ES` y `U1-ZONAS-AVCL-ES/NQ` aportaron positivo. El protocolo preregistrado sigue en `SIN_DECIDIR` (espera `60` sesiones), pero confirma en vivo la prioridad de migrar hacia la manga ortogonal `Tier 1/2`.

---

## 3. Veredicto EdgeLab A5 (`DESC`) — Estrategia 1: `@hobbiecode Gann HiLo Oro H1` (`DgDFTnXgKj-`)

### 3.1 Hallazgo Metodológico Crítico: El Espejismo H1 vs Ejecución Intrabar M1 Exacta

Evaluar órdenes `Buy Stop` (`High 51`) con `SL = 1 * ATR(95)` en velas H1 sin secuencia intrabar M1 engaña completamente el resultado:

| Modo de Simulación (`GC 2008–2025 DESC` / `XAUUSD DESC`) | `n` | `R_bruto` | `R_neto CFD` | `WR` | `PF` | `t_cluster` | `avg_bars` |
|---|---:|---:|---:|---:|---:|---:|---:|
| H1 optimista (`no_same_bar_sl`, ignora SL en vela de entrada) — `GC` | 1.104 | `+0,2385` | **`+0,1593`** | 40,9% | **1,279** | **`+3,07`** | 3,46 |
| H1 optimista (`no_same_bar_sl`) — `XAUUSD` | 261 | `+0,3277` | **`+0,2727`** | 42,5% | **1,489** | **`+2,46`** | 3,46 |
| **M1 intrabar exacto (`m1_exact`, orden minuto a minuto real) — `GC`** | **1.119** | `+0,0933` | **`+0,0142`** | **37,7%** | **1,023** | **`+0,30`** | 3,11 |
| **M1 intrabar exacto (`m1_exact`) — `XAUUSD`** | **266** | `+0,1381` | **`+0,0830`** | **38,3%** | **1,137** | **`+0,81`** | 3,05 |

- **Explicación del video/post:** Si el backtest H1 (o MT5 en modo rápido) no simula ticks/M1 dentro de la vela de disparo del `Buy Stop`, inventa un edge aparente de **`t = +3,07` (`PF 1,28–1,49`)**. Al exigir la secuencia real minuto a minuto en M1 (`gann_m1_verify.py`), ese edge **se desploma a `t = +0,30` en `GC` y `+0,81` en `XAUUSD`**.
- Además, la tasa de llenado real del `Buy Stop` en `High 51` con expiración 10 velas es apenas **`3,4%`** en `GC` (`3,9%` en `XAUUSD`): **96,6% de las señales expiran sin entrar**.

### 3.2 Edge vs Beta de Oro, Regímenes Bajistas y Transferencia Multi-Activo (`M1 Exacto`, `DESC`)

| Activo / Ventana / Variante (`M1 Exacto`) | `n` | `R_bruto` | `R_CFD` | `R_Fut` | `R_Stress ($25+slip)` | `WR (CFD)` | `PF (CFD)` | `t (CFD)` | `MaxDD R` | `% Años +` |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **`GC` Full (`2008–2025 DESC`)** | 1.119 | `+0,0933` | `+0,0142` | **`-0,0663`** | **`-0,5002`** | 37,7% | 1,023 | `+0,30` | `-63,5` | 37% |
| `GC 2020–2025 DESC` | 395 | `+0,1262` | `+0,0676` | `+0,0080` | `-0,3134` | 38,0% | 1,111 | `+0,83` | `-17,2` | 50% |
| **`GC` Oro Bajista `2011–2015 DESC`** | 199 | `-0,0561` | **`-0,1361`** | **`-0,2174`** | `-0,6561` | 34,2% | **0,791** | `-1,36` | `-29,8` | **0%** |
| `GC` Oro Bajista `2022 DESC` | 39 | `+0,0966` | `+0,0379` | `-0,0217` | `-0,3435` | 38,5% | 1,063 | `+0,15` | `-6,4` | 100% |
| `GC` Filtro `uptrend_pullback` (`dir==1`) | 881 | `+0,0762` | `-0,0028` | `-0,0831` | `-0,5162` | 37,0% | 0,996 | `-0,05` | `-66,0` | 37% |
| `GC` Espejo Short (`Sell Stop Low 51`) | 944 | `+0,0799` | `+0,0002` | `-0,0809` | `-0,5179` | 34,7% | 1,000 | `+0,00` | `-102,8` | 42% |
| `GC` Salida 10 velas (`exit_10`) | 1.058 | `+0,1179` | `+0,0387` | `-0,0419` | `-0,4763` | 32,9% | 1,055 | `+0,65` | `-44,4` | 58% |
| **`XAUUSD` Full `DESC`** | 266 | `+0,1381` | `+0,0830` | `+0,0270` | `-0,2750` | 38,3% | 1,137 | `+0,81` | `-17,8` | 40% |
| `XAUUSD` Oro Bajista `2022 DESC` | 19 | `+0,0175` | **`-0,0523`** | `-0,1233` | `-0,5060` | 26,3% | **0,919** | `-0,12` | `-5,5` | **0%** |
| **`EURUSD` Full `DESC`** | 208 | `-0,0425` | **`-0,1679`** | — | — | 29,8% | **0,755** | `-1,50` | `-38,9` | 25% |
| **`GBPUSD` Full `DESC`** | 223 | `-0,0307` | **`-0,1571`** | — | — | 32,7% | **0,758** | `-1,69` | `-48,1` | 25% |
| **`ES` Full `DESC`** | 1.498 | `-0,0548` | **`-0,1331`** | **`-0,2533`** | — | 36,6% | **0,784** | **`-3,95`** | `-203,5` | 24% |
| **`NQ` Full `DESC`** | 1.524 | `+0,0119` | **`-0,0887`** | **`-0,1467`** | — | 35,7% | **0,860** | **`-2,40`** | `-167,1` | 24% |

- **Phase-Shift H1 (`M1 Exacto`) en `GC`:** `0m = +0,0142 (t=+0,30)` -> `15m = -0,0093 (t=-0,20)` -> `30m = -0,0222 (t=-0,49)` -> `45m = -0,0116 (t=-0,25)` (**1/4 fases positivas**). En `XAUUSD`: 4/4 positivas (`+0,048` a `+0,111`, pero `t = +0,50..+1,11`).
- **Ortogonalidad vs `Core4` (`GC DESC 2008–2025`):** `corr_d = -0,017`, `corr_m = +0,211`, **pierde `-11,51 R` en los peores 20% meses de `Core4`**, `stag 2025-05..09 = +6,38 R`.
- **Veredicto Gates EdgeLab:** **NO PASA (`DESCARTAR`):** `t = +0,30` (`GC`) / `+0,81` (`XAUUSD`) vs gate `>= 2,5`; `WR = 38%` vs `>= 50%`; negativa en futuros, negativa con costos `$25+slip` (`-0,50 R`), negativa en `2011–2015` bajista y negativa en `EURUSD/GBPUSD/ES/NQ`.

---

## 4. Veredicto EdgeLab A5 (`DESC`) — Estrategia 2: `@hobbiecode Supertrend Oro H1` (`DgGO2-fATcK`)

### 4.1 Baseline `ATR=10, Factor=3.0, Flip` Multi-Símbolo (`DESC`)

| Activo / Ventana | `n` | `R_bruto` | `R_CFD` | `WR` | `PF` | `t_cluster` | `Sharpe_yr` | `MaxDD R` | `% Años +` |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **`GC` Full (`2008–2025 DESC`)** | 243 | `+0,0440` | `+0,0286` | 39,5% | 1,034 | **`+0,19`** | `+0,04` | `-32,0` | 42% |
| `GC 2020–2025 DESC` | 81 | `-0,1744` | **`-0,1859`** | 39,5% | 0,814 | **`-0,63`** | `-0,25` | `-28,0` | 33% |
| `XAUUSD Full DESC` | 52 | `+0,0776` | `+0,0653` | 32,7% | 1,065 | **`+0,15`** | `+0,07` | `-23,7` | 60% |
| `EURUSD Full DESC` | 42 | `+0,0101` | `-0,0337` | 45,2% | 0,969 | `-0,07` | `-0,03` | `-18,0` | 50% |
| `GBPUSD Full DESC` | 38 | `+0,5636` | `+0,5378` | 60,5% | 1,874 | `+1,44` | `+0,72` | `-6,4` | 100% |
| `ES Full DESC` | 203 | `-0,2417` | `-0,2581` | 45,3% | 0,767 | `-1,22` | `-0,26` | `-91,4` | 43% |
| `NQ Full DESC` | 331 | `+0,1237` | `+0,1009` | 45,0% | 1,131 | `+0,83` | `+0,18` | `-41,9` | 62% |

### 4.2 Grilla `6 × 7` (`42` Celdas), `CSCV PBO`, Ablaciones y *Phase-Shift* H1 (`DESC`)

- **Grilla `ATR_LENGTH [7..21] × FACTOR [1.5..5.0]` (`42` celdas):**
  - `GC Full DESC`: `92,9% > 0` CFD (`88,1%` Fut), mediana `+0,118 R` (`t = +1,29`), pero **`PBO (CSCV s=16) = 0,574`** (`N_eff = 6,25`) — el pico elegido en muestra (`ATR 21, Factor 5.0`) sobreajusta peor que azar (`> 0,50`). En `2020–25` baja a `59,5% > 0` (`PBO = 0,405`).
  - `XAUUSD Full DESC`: `81,0% > 0`, mediana `+0,305 R` (`t = +0,99`), **`PBO = 0,523`** (`N_eff = 5,75`).
- **Ablaciones clave en `GC` / `XAUUSD` (`DESC`):**
  - `H1 + EMA200`: `GC n=187`, `+0,0869 R_cfd` (`PF=1,113`, `t=+0,52`, `DD=-26,5 R`); `XAUUSD n=44`, `+0,2995 R_cfd` (`PF=1,344`, `t=+0,67`, `DD=-13,1 R`).
  - `H1 + EMA200 + Stop 2·ATR + TP 2:1`: `GC +0,1111 R_cfd` (`PF=1,177`, `t=+1,06`, `DD=-10,8 R`), pero `XAUUSD -0,1362 R_cfd` (`t=-0,65`).
  - `H1 + ADX>25`: `GC +0,0235 R` (`t=+0,12`), `XAUUSD -0,3627 R` (`t=-0,54`).
  - `M15 raw` (`GC`): `n=687`, `+0,0655 R` (`t=+0,54`, `DD=-89,5 R`); `H4 raw` (`GC`): `n=55`, `-0,1238 R` (`t=-0,45`).
- **Phase-Shift H1 (`10/3.0`):** en `GC` retenido `4/4` (`+0,029` a `+0,289 R`, `corr = 0,38..0,51`), pero en `XAUUSD` **muy inestable al minuto de cierre H1**: `0m = +0,065`, **`15m = -0,158`**, `30m = +0,618`, **`45m = -0,244`** (`2/4` positivas, `corr = 0,23..0,54`).
- **Ortogonalidad vs `Core4`:** Aunque el filtro `ST + EMA200` presenta correlación mensual negativa (`corr_m = -0,358` en `GC`, `-0,413` en `XAUUSD`) y sumó `+9,01 R` (`GC`) / `+13,49 R` (`XAUUSD`) en los peores meses de `Core4`, **perdió `-2,89 R` (`GC`) y `-4,74 R` (`XAUUSD`) durante el estancamiento mayo–sep 2025** y tiene `t = +0,52..+0,67` (con apenas ~18 ops/año). Para oro en `FTMO Swing`, **`Turtles_GC_CFD` ya validada es estrictamente superior** (`Sharpe 0,97`, `MaxDD -1,5 R`, `+2,61 R` en mayo–sep 2025, `P(pay) 97,5%` en MC).
- **Veredicto Gates EdgeLab:** **DESCARTAR Supertrend solo (`t=+0,19`, `PF=1,034`, `PBO=0,574`)**. La variante `H1 + EMA200` queda muy por debajo del gate (`t>=2,5`) y no supera a `Turtles_GC_CFD` en potencia ni en eficiencia de riesgo.
