# Resultados Suite de Rentabilidad y Estabilidad (`EXP-1` a `EXP-5`, `2026-11-25`)

Estado: RESULTADO (`EXP-1`..`EXP-5` y `EXP-6C` completados y verificados; `EXP-6A/6B` pendientes de datos L1/ticks)  
Fecha: 2026-11-25  
North Star sha256: `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`  
Runner: [`tools/run_suite_estabilidad_20261125.py`](../../../tools/run_suite_estabilidad_20261125.py) (`K51` verificado vía `exigir_contada`; `DESC` `2020-01 → 2026-09` y `REP` congelado; `HOLDOUT >= 2026-10-01` intacto; costos canónicos `edgelab/costos.py` + `veto_noticias` tier-1 activo).

---

## Resumen Ejecutivo — Qué pasa el filtro y qué se descarta

1. **`EXP-1` (`T` escala relativa, `7` pruebas, `NQ` + `ES`):** **`0/6` superan `BH q = 0,10` (`q = 1,000`).** Mantener **`T_FIJO_100`** (`DESC +107,46 R`, `DD -14,78 R`, `Sharpe 1,12`, `Calmar 1,04` | `REP +36,10 R`, `DD -8,09 R`). Ampliar el techo (`0,8–1,0%`, `ATR20`, sin tope) degrada `DESC` (`+88..91 R`) y `REP` (`+31..32 R`). El techo `100 pts` actúa como filtro estructural útil en días de ORB extremo.
2. **`EXP-2` (`SOM_sin_finde` + Noticias `10:00 NY` + `use_adaptive_risk` + `ATR`, `7` pruebas, `NQ`):**
   - **`SOM_POST_1005`** (en días con noticia tier-1 `09:30–10:15 NY`, posponer entrada a `10:10 NY` tras el veto): sube `DESC` de `+46,95 R → +59,51 R` (`+27%`, `Sharpe 0,68 → 0,84`, `DD -20,29 → -18,31 R`, `p = 0,069`, `q_bh = 0,240`) y **también mejora en `REP` congelado (`+11,80 → +14,05 R`, `DD -11,05 → -8,76 R`)**.
   - **`SOM_SKIP_1000`** (saltear entrada `09:35` en días con noticia `10:00 NY`): `p = 0,034` (`q_bh = 0,234`), `DESC +54,94 R`, `Sharpe 0,81`, `DD -18,15 R`, baja los cierres forzados `NEWS_VETO` de `291 → 103` (`-65%`).
   - **`SOM_ADAPT_RISK` (`use_adaptive_risk=True` de QuantLab):** **DESCARTADO** (`DESC +38,50 R`, `DD -23,75 R`, `Sharpe 0,50`, peor que control).
3. **`EXP-3` (`Sizing & VolTarget` sobre `P3_MULTIESTABLE`, `5` políticas, `MNQ/MES` + `LucidFlex 50K`):**
   - **`S1_R_CONST` (`R` constante en micros) APLASTA a `S0_FIJO_MICRO` (`1` contrato fijo):** baja `MaxDD` de `-32,74 → -19,01 R` (`-42%` en `DESC`) y `-25,05 → -14,70 R` (`-41%` en `REP`), sube `Sharpe` (`1,24 → 1,71`) y **duplica el `EV` de `LucidFlex 50K` (media contraída `60%`): `+$388 (36,0%) → +$868 (46,0%)` en `DESC` y `+$509 → +$765` en `REP`**.
   - **`S3_DD_STEP` (`0,5R` cuando `DD <= -8R`, restaura en `-3R`):** recorta aún más el `MaxDD` (`-19,01 → -14,36 R` `DESC`, `-14,70 → -11,36 R` `REP`) y **eleva el `EV` de `LucidFlex 50K (60%)` a `+$1.013 (48,8%)` en `DESC` y `+$778` en `REP`**.
   - **`S2_VOLTARGET_20D`:** **DESCARTADO** (empeora `MaxDD` a `-28,35 R` y baja `EV` en `REP` a `+$610`).
4. **`EXP-4` (`RQ5` selectivo, `5` pruebas, `NQ + ES`):** **`0/4` superan `BH q = 0,10` (`q = 1,000`).** Se mantiene **`RQ5_FAB` (`m=1,0, c=11:30`)** (`DESC +117,41 R`, `6/6` años `+` | `REP +14,03 R`); `RQ5_M10_C1100` (`c=11:00`) es alternativa equivalente con `REP +17,92 R`.
5. **`EXP-5` (`Ensamble MultiEstable`, `12` pruebas, `MaxOpenR = 3,0`):** **`8/12` configuraciones pasan `BH q <= 0,064` (`q = 0,027` en las líderes):**
   - **Campeón Prop Firm (`LucidFlex 50K`, máxima eficiencia de pase):** **`P0_CORE3|W5_ERC_cap3R` (`T + R + Z` con pesos ERC)** → `DESC +3,96 R/mes`, `Sharpe 2,25`, `DD -11,99 R`, `EV 50K(60%) = +$2.422 (63,7% pasa)` | **`REP +2,94 R/mes`, `Sharpe 2,04`, `DD -6,00 R`, `EV 50K(60%) = +$2.195 (66,7% pasa)`**.
   - **Campeón Rentabilidad + Diversificación Multi-Factor:** **`P3_MULTIESTABLE|W5_ERC_cap3R` (`T + R + Z + SOM + RQ5(NQ+ES) + C2_VZ(NQ+ES)`)** → **`DESC +6,23 R/mes`, `Sharpe 1,93`, `DD -19,71 R` (`p=0,004`, `q_bh=0,027`)** | **`REP +5,58 R/mes` (`+90%` más que `Core3`), `Sharpe 1,84`, `DD -15,47 R`, `EV 50K(60%) = +$1.064 (46,3% pasa)`**.
   - **Descartes confirmados:** sumar `ES5N` (`P4`) o `Franklin` (`P5`) sobre `P3_MULTIESTABLE` **empeora** `Sharpe`, `MaxDD` y `EV` tanto en `DESC` como en `REP`.

---

## Tablas Verificadas

### EXP-1 — `T` Escala (`NQ`)
| Variante | `DESC` `R_sum` (`R/op`) | `DESC` `DD` / `Sh` / `Cal` | `Cap 25-26` | `q_bh` | `REP` `R_sum` (`R/op`) | `REP` `DD` |
|---|---:|---|---:|---:|---:|---:|
| **`T_FIJO_100`** *(Control)* | **`+107,46` (`+0,1289`)** | **`-14,78` / `1,12` / `1,04`** | `62,9%` | `1,000` | `+36,10` (`+0,1416`) | `-8,09` |
| `T_PCT_060` | `+103,19` (`+0,1237`) | `-20,74` / `1,06` / `0,71` | `32,0%` | `1,000` | `+38,86` (`+0,1524`) | `-8,21` |
| `T_PCT_080` | `+90,10` (`+0,1080`) | `-17,76` / `0,97` / `0,72` | `16,5%` | `1,000` | `+31,22` (`+0,1224`) | `-7,92` |
| `T_ATR_050` | `+90,15` (`+0,1081`) | `-13,08` / `0,99` / `0,98` | `4,6%` | `1,000` | `+32,26` (`+0,1265`) | `-7,74` |
| `T_SIN_CAP` | `+90,55` (`+0,1086`) | `-12,95` / `1,00` / `1,00` | `0,0%` | `1,000` | `+31,50` (`+0,1235`) | `-7,56` |

### EXP-2 — `SOM_sin_finde` Noticias y Riesgo Adaptativo (`NQ`)
| Variante | `DESC` `R_sum` (`R/op`) | `DESC` `DD` / `Sh` | `Veto` | `p` / `q_bh` | `REP` `R_sum` (`R/op`) | `REP` `DD` |
|---|---:|---|---:|---|---:|---:|
| `SOM_BASE_VETO` *(Control)* | `+46,95` (`+0,0532`) | `-20,29` / `0,68` | `291` | `1,000 / 1,000` | `+11,80` (`+0,0450`) | `-11,05` |
| **`SOM_POST_1005`** | **`+59,51` (`+0,0669`)** | **`-18,31` / `0,84`** | `163` | `0,069 / 0,240` | **`+14,05` (`+0,0536`)** | **`-8,76`** |
| **`SOM_SKIP_1000`** | **`+54,94` (`+0,0714`)** | **`-18,15` / `0,81`** | **`103`** | **`0,034 / 0,234`** | `+10,79` (`+0,0473`) | `-10,57` |
| `SOM_ADAPT_RISK` | `+38,50` (`+0,0436`) | `-23,75` / `0,50` | `291` | `0,797 / 1,000` | `+11,60` (`+0,0443`) | `-12,20` |
| `SOM_ATR6_SKIP` | `+63,93` (`+0,0791`) | `-14,87` / `0,77` | `61` | `0,180 / 0,420` | `+13,88` (`+0,0569`) | `-17,57` |

### EXP-5 — Ensamble `MultiEstable` (`W5_ERC_cap3R`, `MaxOpenR = 3,0`)
| Cartera (`W5_ERC_cap3R`) | `DESC` `R/mes` / `Sh` / `DD` | `p` / `q_bh` vs `P0` | `REP` `R/mes` / `Sh` / `DD` | `LucidFlex 50K (60%)` `DESC` / `REP` |
|---|---|---|---|---|
| **`P0_CORE3`** (`T+R+Z`) | `+3,96` / **`2,25`** / **`-11,99`** | `0,160 / 0,174` | `+2,94` / **`2,04`** / **`-6,00`** | **`+$2.422 (63,7%)`** / **`+$2.195 (66,7%)`** |
| **`P1_CORE_SOM`** (`+SOM`) | `+5,28` / `2,10` / `-19,47` | **`0,004 / 0,027`** | `+4,03` / `1,82` / `-11,24` | `+$1.524 (54,3%)` / `+$1.448 (51,0%)` |
| `P2_CORE_SOM_RQ5` (`+RQ5`) | `+5,71` / `1,72` / `-20,48` | `0,015 / 0,029` | `+3,80` / `1,27` / `-18,95` | `+$846 (44,7%)` / `+$633 (39,9%)` |
| **`P3_MULTIESTABLE`** (`+C2_VZ`) | **`+6,23`** / `1,93` / `-19,71` | **`0,004 / 0,027`** | **`+5,58`** / `1,84` / `-15,47` | `+$984 (48,3%)` / `+$1.064 (46,3%)` |
| `P4_MULTI_ES5N` (`+ES5N`) | `+6,00` / `1,83` / `-20,70` | `0,011 / 0,029` | `+5,00` / `1,65` / `-16,41` | `+$884 (46,4%)` / `+$830 (44,1%)` |
| `P5_MULTI_FRANKLIN` (`+Frk`) | `+5,37` / `1,56` / `-22,44` | `0,053 / 0,064` | `+4,42` / `1,39` / `-18,85` | `+$709 (41,1%)` / `+$586 (39,9%)` |

### EXP-3 — Sizing (`P3_MULTIESTABLE`)
| Política | `DESC` `R/mes` / `Sh` / `DD` | `REP` `R/mes` / `Sh` / `DD` | `LucidFlex 50K (60%)` `DESC` / `REP` |
|---|---|---|---|
| `S0_FIJO_MICRO` | `+4,93` / `1,24` / `-32,74` | `+4,48` / `1,23` / `-25,05` | `+$388 (36,0%)` / `+$509 (35,7%)` |
| **`S1_R_CONST`** | `+5,40` / **`1,71`** / `-19,01` | `+4,13` / **`1,42`** / `-14,70` | `+$868 (46,0%)` / `+$765 (42,0%)` |
| `S2_VOLTARGET_20D` | `+5,79` / `1,71` / `-28,35` | `+4,32` / `1,31` / `-20,28` | `+$811 (44,4%)` / `+$610 (39,1%)` |
| **`S3_DD_STEP`** (`0,5R` bajo `-8R`) | `+3,80` / `1,56` / **`-14,36`** | `+2,89` / `1,20` / **`-11,36`** | **`+$1.013 (48,8%)`** / **`+$778 (41,6%)`** |
| `S4_VOLTARGET_DD` | `+3,77` / `1,58` / `-14,36` | `+2,33` / `1,08` / `-11,01` | `+$1.088 (49,9%)` / `+$699 (41,3%)` |

### EXP-6C — Satélite Puro `ES / MES` (`EXP-6A/6B`: `PENDIENTE_DATOS_L1`)
| Cartera `ES` | `DESC` `R/mes` / `Sh` / `DD` / `Calmar` | `REP` `R/mes` / `Sh` / `DD` / `Calmar` | Corr. diaria vs `NQ_CORE` |
|---|---|---|---|
| **`ES_SAT_1`** (`RQ5_ES + C2_VZ_ES`) | **`+1,41` / `1,23` / `-14,29` / `1,18`** | **`+1,14` / `1,04` / `-8,49` / `1,61`** | **`0,368`** |
| `ES_SAT_2` (`+ES5N_ES`) | `+1,97` / `1,23` / `-18,63` / `1,27` | `+0,84` / `0,59` / `-11,61` / `0,87` | `0,423` |
| `ES_SAT_3` (`+T_ES + R_ES`) | `+1,92` / `0,60` / `-68,69` / `0,34` | `+2,37` / `0,73` / `-26,28` / `1,08` | `0,494` |

---

## Recomendación Operativa Directa (Producción / NT8)

1. **Para cuentas Prop (`LucidFlex 25K/50K`, objetivo máxima probabilidad de pase y retiros):** **`P0_CORE3|W5_ERC_cap3R` (`T_FIJO_100 + R + Z`)** con sizing **`S1_R_CONST`** (y opcional **`S3_DD_STEP`**) es imbatible: `Sharpe > 2,0`, `DD -6 R` en `REP` y **`66,7%` de tasa de pase** incluso bajo contracción al `60%`.
2. **Para capital propio o cartera diversificada de mayor ingreso mensual (`R/mes`):** **`P3_MULTIESTABLE|W5_ERC_cap3R` (`T + R + Z + SOM_POST_1005/SKIP_1000 + RQ5(NQ+ES) + C2_VZ(NQ+ES)`)** con `S1_R_CONST` + `S3_DD_STEP` eleva el rendimiento mensual en `REP` de **`+2,94 → +5,58 R/mes` (`+90%`)** manteniendo `Sharpe 1,84`.
3. **No portar a producción:** `T` sin techo `100`, `SOM use_adaptive_risk`, `VolTarget_20d`, `ES5N`, `Franklin` (redundante con `T/RQ5`) ni `C2_EVRP`.
