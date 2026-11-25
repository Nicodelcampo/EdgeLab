# Estabilidad entre épocas (`DESC`) y Matriz Multi-Activo de Pruebas NT8

Fecha: 2026-11-25  
Restricción de protocolo: toda exploración de estabilidad y diseño de variantes usa **únicamente el bloque `DESC`** (`2012–2025`, `a5_bloque == "DESC"`). **`REP` y `HOLDOUT` (`>= 2026-10-01`) permanecen intactos** para cualquier variante nueva hasta su pre-registro en `K51`.

---

## 1. Diagnóstico: ¿por qué muchas curvas en NT8 parecen ganar sólo desde 2024?

Al inspeccionar las series reales en `DESC` (`R_neto_mini` vs puntos con `1` contrato fijo), la aparente concentración de ganancias en `2024–2026` responde a **tres causas distintas** según la familia:

1. **Ilusión de escala por usar `ContratosFijos = 1` en un índice que multiplicó ~3x su precio/ATR:**
   - Entre `2020` y `2026`, la mediana del stop de `SOMEOD`/`SOM_sin_finde` subió de `103,75 pts` (`$2.075/NQ`) a `260,50 pts` (`$5.210/NQ`); en `R` subió de `122,4` (`2020–23`) a `158,1` (`2024–25`); en `Z` de `131,9` a `171,1`; en `T` de `70,2` a `95,8`.
   - En términos normalizados a riesgo (`R`), **`R`, `Z`, `V`, `C2_VZ` y `RQ5 (ES y NQ)` ya eran rentables antes de 2024**, con `6/7` a `8/8` años positivos:

| Estrategia (`DESC`) | `2012–17` `R/op` | `2018–23` `R/op` (`sum R`) | `2024–25` `R/op` (`sum R`) | Años `> 0` (`18–25` o `19–25`) | Diagnóstico real |
|---|---:|---:|---:|---:|---|
| **`R` (`R_osc30_end660_ATR50`, NQ)** | — | `+0,248` (`+24,6 R`, `n=99`) | `+0,477` (`+21,9 R`, `n=46`) | **7/7** (`2019–25`) | Ya ganaba `+0,307 R` en `2020–23` |
| **`Z` (`Z_b15_e20_eff40_ATR50`, NQ)** | — | `+0,159` (`+12,3 R`, `n=77`) | `+0,138` (`+4,3 R`, `n=31`) | **6/7** (`2019–25`) | Más alta antes de `2024` (`+0,198 R` en `20–23`) |
| **`V` (`V_nm25_noCap_mae30`, NQ)** | — | `+0,088` (`+41,4 R`, `n=469`) | `+0,130` (`+29,0 R`, `n=224`) | **6/6** (`2020–25`) | Estable `2020–25`; cae en `2025S2–2026` (NT8 verificado) |
| **`T` (`T_stop100_BE15R_calFalse`, NQ)** | — | `+0,086` (`+51,5 R`, `n=598`) | `+0,206` (`+53,1 R`, `n=258`) | **6/7** (`2019–25`) | Ya fuerte `2022–23` (`+32,6` y `+16,5 R`); techo `100 pts` distorsiona `2025–26` |
| **`SOM_sin_finde` (`NQ`)** | *+0,008* (`2008–11`) / *+0,019* (`12–19`) | `+0,022` (`+14,9 R`, `n=667`) | `+0,088` (`+24,0 R`, `n=271`) | **4/7** (`2019–25`) | Ganó `2020–21` (`+35,6 R`); bache `2022–23` (`-11,2 R`); veto recorta `2024` |
| **`RQ5` (`fábrica L60 m1 c11:30`, `ES`)** | `-0,086` (`n=580`) | `+0,082` (`+45,2 R`, `n=551`) | `+0,133` (`+21,2 R`, `n=160`) | **8/8** (`2018–25`) | Muy pareja desde `2018` (`+2,1` a `+20,0 R/año`) |
| **`RQ5` (`fábrica L60 m1 c11:30`, `NQ`)** | `-0,022` (`n=564`) | `+0,064` (`+37,4 R`, `n=581`) | `+0,143` (`+23,1 R`, `n=161`) | **7/8** (`2018–25`) | Solo `2019` negativo (`-11,2 R`) |
| **`C2_VZ` (`ES + NQ`)** | `+0,051` (`n=191`) | **`+0,163`** (`+30,7 R`, `n=189`) | `+0,020` (`+0,9 R`, `n=48`) | **6/8** (`2018–25`) | **Anticíclica:** rinde fuerte en `2019 (+14 R)`, `2020 (+9,5)`, `2023 (+7,0)` |
| **`C2_EVRP` (`ES + NQ`)** | `+0,042` (`n=140`) | `+0,071` (`+9,4 R`, `n=132`) | `+0,223` (`+6,2 R`, `n=28`) | **5/8** (`2018–25`) | Negativa `2022–23` (`-7,5 R`); más selectiva post-`2024` |
| **`Franklin` (`1000\|rango\|ninguno`, `NQ`)** | `-0,010` (`12–19`) | negativa `18–19` | `+0,093` (`23–26`) | régimen `>= 2020` | Negativa pre-2020 por fricción relativa y régimen intradía |

2. **Tope de stop fijo en puntos (`100 pts` en `T`):**
   - En `DESC` de `T_NQ`, la fracción de operaciones que chocan contra el techo `>= 99,5 pts` pasó de **`0%` (2019) → `16,2%` (2020) → `56,0%` (2022) → `51,6%` (2025) → `86,5%` (2026)**. Un tope fijo en puntos convierte al módulo en otra regla conforme el índice sube.
3. **Baches cíclicos reales (`SOM 2022–2023`, `Franklin pre-2020`) + impacto del `NEWS_VETO` (`09:58 NY`):**
   - El calendario tier-1 (`10:00 NY`) cierra `20,8%` (`21,5%` en NT8) de las operaciones de `SOM_sin_finde` y `17,8%` en `SOMEOD`. En `2024`, ese cierre recorta a `SOM_sin_finde` de `+3.614 pts` (sin veto) a `+836 pts` (con veto), concentrando visualmente las ganancias en `2025–2026`.

---

## 2. Cómo lograr curvas más estables sin perder rentabilidad (variantes candidatas a pre-registrar `K51`)

Tres palancas concretas medidas en `DESC` (antes de re-abrir `REP`, requieren pre-registro `K51`):

1. **Palanca de Sizing (`R`-constante en micros `MNQ/MES` vs `1` contrato fijo):**
   - Operar `ContratosFijos = 0` sobre `MNQ` (ej. `Risk1R_USD = 200`) estabiliza la pendiente en dólares entre `2020–2023` y `2024–2026` porque normaliza el crecimiento de `3x` en puntos del `NQ`.
2. **Palanca de diseño invariante de escala en reglas activas:**
   - **`T` con techo relativo (`stop_max_pct ≈ 0,90 %` del precio o `stop = 1,0 × ORB` sin techo fijo `100 pts`):** evita que en `2025–2026` el `52–87%` de los trades queden recortados a un stop fijo arbitrario. *(En `fundedsync_multiactivo_oro_20261122`, quitar el techo fijo en `ES` elevó `T` de `+0,019 → +0,055 R`)*.
   - **`SOM_sin_finde` con gestión causal pre-noticia / filtro de compresión:** en lugar de abrir a las `09:35 NY` los días con dato tier-1 a las `10:00 NY` (y cerrar `23 min` después a pérdida/costo de spread en el `21%` de los días), **posponer o saltar entradas cuando haya evento tier-1 entre `09:30` y `10:15 NY`** (a pre-registrar en `K51`).
   - **`RQ5` con severidad adaptativa (`m = 1,2` o corte `11:00 NY`):** en `rq5_regimen_20261119` mostró dosis-respuesta monotónica (`m=0,8: +0,028` → `m=1,0: +0,038` → `m=1,2: +0,044 R`) y menos operaciones ruidosas en `2019`.
3. **Palanca de Ensamble descorrelacionado (`T + R + Z + SOM_sf + RQ5 (NQ+ES) + C2_VZ`):**
   - Combinando sleeves en `DESC` (`2020-01 → 2026-09 DESC`, ponderación `1 R` base + `0,5 R` en `RQ5_NQ`, `RQ5_ES` y `C2_VZ`), `C2_VZ` y `T/R/Z` compensan el bache `2022–2023` de `SOM`, manteniendo casi idéntico Sharpe y MaxDD pero duplicando el rendimiento anual de `2020–2023`:

| Cartera (`DESC 2020-01 → 2026-09`) | Suma `R` | `MaxDD` | Sharpe anual | Promedio `2020–23` | Promedio `2024–25` | Desglose anual (`2020 → 2026 DESC`) |
|---|---:|---:|---:|---:|---:|---|
| **`Core3 (T+R+Z)`** | `+196,5 R` | `-12,1 R` | `1,87` | `+23,4 R/año` | `+39,6 R/año` | `+13,7 \| +15,0 \| +40,8 \| +24,0 \| +50,2 \| +29,1 \| +23,8` |
| **`Core4 (+V)`** | `+260,2 R` | `-18,4 R` | `1,88` | `+33,7 R/año` | `+54,1 R/año` | `+16,7 \| +35,4 \| +44,8 \| +37,9 \| +69,7 \| +38,6 \| +17,1` |
| **`Core3 + SOM_sf`** | `+255,9 R` | `-16,6 R` | `1,84` | `+29,5 R/año` | `+51,6 R/año` | `+34,1 \| +30,3 \| +35,5 \| +18,0 \| +57,0 \| +46,2 \| +34,9` |
| **`MultiEstable` (`Core3+SOM_sf + 0,5*(RQ5_NQ+RQ5_ES+C2_VZ)`)** | **`+323,9 R`** | **`-17,4 R`** | **`1,87`** | **`+40,8 R/año`** | **`+62,9 R/año`** | **`+54,5 \| +35,7 \| +42,0 \| +31,0 \| +71,5 \| +54,3 \| +34,9`** |

---

## 3. Matriz Multi-Activo: qué estrategias probar en NT8 por activo y cuáles NO repetir

Basado en `fundedsync_multiactivo_oro_20261122`, `rq5_regimen_20261119`, `som_transfer_20261117`, `transfer_rty_emd_20261119`, `a20_multiactivo_20261119`, `carril2_20261119`, `franklin_confirmacion_20261118` y `externas_estructurales_a5_20261118`:

| Activo NT8 | Estrategias **SÍ PROBAR** en NT8 (con evidencia `DESC`/`REP` positiva o bajo revisión activa) | Estrategias **`NO_REPETIR`** / Descartadas |
|---|---|---|
| **`NQ` / `MNQ`** | **Núcleo:** `T`, `R`, `Z`, `SOM_sin_finde` (`SOMEOD` como control). **Complementos:** `RQ5`, `Franklin` (con y sin `VetoPreap`), `C2_VZ`, `C2_EVRP`, `ES5N`, y reglas footprint `U1-RACIMOS-GRILLA-NQ` / `CONF-CVR-CFD-NQ-R` (`EdgeLabSpiralBasketExecutor`). *(Nota `V`: verificar caída desde 2025S2).* | `A1, P, Q, W_tal_cual` (`F-FUNDEDSYNC-SIN-VENTAJA`), `A20` fuera de monitoreo forward, `ES1–ES8` originales (`EXTERNAS_ESTRUCTURALES` refutadas). |
| **`ES` / `MES`** | **`RQ5`** (`8/8` años positivos `2018–25`, `+0,093 R p=0,007`), **`C2_VZ` y `C2_EVRP`** (`CARRIL2 ES+NQ`), **`ES5N`** (`+0,083 R` neto en `ES DESC`), **`T` y `R`** (`EdgeLabCandidataFS` preset `ES_Core_US500`), **`Franklin` (`+Veto PREAPERTURA-ES`)**, **`U1-ZONAS-BT2-ES`**. | `Z` (colapsa en `REP`: `-0,221 R`), `V`, `W`, `A1`, `P`, `Q`, `A20`, `E`. |
| **`YM` / `MYM`** | **`N` (`N_d5_fbTrue_ATR25`)** (único módulo FundedSync positivo en `DESC +0,017 / REP +0,033`, potencia baja). Eventualmente `T` con techo `100` en exploración Sim (`+0,074 R DESC`, gira a `-0,041` en `REP`). | **`RQ5`** (`-0,022 R p=0,72`), **`SOM`** (`F-SOM-TRANSFER-NO`), **`Franklin`** (`-0,042` mini / `-0,088` micro neto), **`A20`** (`-0,074 R`, `0/8` vecinos), **`R, Z, V, W, A1, P, Q`**. |
| **`RTY` / `M2K`** *(solo Sim)* | **`RQ5`** (`+0,046 R p=0,099` en `DESC`; decae en `2024–25`), **`T` escalada (`1,25× ORB`)** en Sim (`+0,049 R p=0,087` en `DESC`). **Nota:** falta costo canónico medido para `M2K`; no usar en cuentas reales sin medir spread. | **`Z`** (`NO_REPETIR`: `F-Z-RTY-REP-COLAPSA`, `-0,258 R` en `REP`), **`SOM`** (`-0,020 R`, `F-SOM-TRANSFER-NO`), **`A20`** (`-0,034 R`, `0/8` vecinos), **`Franklin`** (`+0,002 R` neto), **`C2_VZ`** (`+0,035 R` sin significancia). |
| **`GC` / `MGC`** | **Ninguna de las reglas de índices transferidas como core.** Sólo monitoreo/referencia pasiva de **`U1-ORO-GRILLA`** (footprint nativo en `EdgeLabSpiralBasketExecutor`) y, si se investiga en `Sim`, **`N_d3_ATR50`** (`+0,043 R DESC`, no significativa) o `ES2N` (`Dual Thrust expandido`). | **Todas las reglas de índices por transferencia directa (`0/60` variantes en `GC`, `F-ORO-TRANSFER-NO`)**: `T, R, Z, V, W, A20, A1, P, Q, Franklin, SOM, ES1`. |
| **`6E` / `M6E`** | **Ninguna de la pila actual hasta diseñar reglas FX nativas.** (Eventual prueba exploratoria solo de rupturas/regímenes nativos de divisas tras medir fricción en `M6E`). | **`SOM` Londres `03:00`** (`-0,041 R`, `F-SOM-TRANSFER-NO`). |
| **`CL`, Bonos (`ZN/ZB`), DAX/Nikkei/FTSE** | **BLOQUEADAS por protocolo hasta medir costos canónicos (`edgelab/costos.py`)** y resolver desfases DST en índices europeos/asiáticos. | No ejecutar estrategias de índices USA sin costo medido ni validación previa `K33`. |
