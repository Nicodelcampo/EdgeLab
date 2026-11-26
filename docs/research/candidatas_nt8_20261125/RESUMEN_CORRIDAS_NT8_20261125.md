# Resumen de Corridas NT8 Nuevas (2026-11-25) — `RQ5`, `C2_VZ`, `C2_EVRP`, `ES5N`, `Franklin`

Estado: RESULTADO (control de ejecución en NT8 con veto de noticias tier-1 activo; no sustituye confirmación en holdout terminal `>= 2026-10-01`)  
Fecha: 2026-11-25  
Parámetros comunes NT8: `Minute / 1`, `CME US Index Futures ETH`, `2019-01-02 → 2026-09-30`, `Contratos fijos = 1`, `Veto de noticias = true` (`±2 min`, `±5 min` FOMC).  
Archivos CSV archivados en [`corridas_nt8_nuevas/`](corridas_nt8_nuevas/).

---

## 1. Métricas verificadas en `R_neto_mini` (descontando fricción canónica y `NEWS_VETO`)

| Estrategia NT8 | Archivo CSV | `n` | Suma `R` neto | `R/op` | `MaxDD_R` | Años `+` | `Jun–Sep 2026` | Corr. diaria vs `RQ5_ES` | Lectura operativa |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| **`RQ5_NQ`** | [`NT8_RQ5_NQ.csv`](corridas_nt8_nuevas/NT8_RQ5_NQ.csv) | 1.288 | **`+76,18 R`** | `+0,059` | `-13,59 R` | **7/8** | `-8,05 R` *(año `2026`: `+2,07 R`)* | `0,632` | **Fuerte:** 7/8 años `+`, en `2026` sigue `+2,07 R` en `R`. |
| **`RQ5_ES`** | [`NT8_RQ5_ES.csv`](corridas_nt8_nuevas/NT8_RQ5_ES.csv) | 1.195 | **`+47,27 R`** | `+0,040` | `-16,78 R` | **7/8** | `-10,23 R` *(año `2026`: `-9,12 R`)* | `1,000` | **Fuerte:** 7/7 años `+` en `2019–25`; bache `-10 R` en `Q3 2026`. |
| **`C2_VZ_NQ`** | [`NT8_C2_VZ_NQ.csv`](corridas_nt8_nuevas/NT8_C2_VZ_NQ.csv) | 320 | **`+24,48 R`** | **`+0,076`** | **`-4,75 R`** | **8/8** | **`+2,23 R`** *(año `2026`: `+4,15 R`)* | **`-0,002`** | **Excelente estabilizador:** `8/8` años `+`, corr `0,00` vs `RQ5`. |
| **`C2_VZ_ES`** | [`NT8_C2_VZ_ES.csv`](corridas_nt8_nuevas/NT8_C2_VZ_ES.csv) | 336 | **`+18,08 R`** | `+0,054` | **`-4,73 R`** | **7/8** | **`+2,21 R`** *(año `2026`: `+3,35 R`)* | **`-0,020`** | **Excelente estabilizador:** `7/8` años `+`, corr `0,00` vs `RQ5`. |
| **`Franklin_VetoPreap_NQ`** | [`NT8_Franklin_VetoPreap_NQ.csv`](corridas_nt8_nuevas/NT8_Franklin_VetoPreap_NQ.csv) | 531 | **`+36,21 R`** | `+0,068` | `-13,55 R` | **6/8** | `-3,90 R` | `0,256` | **El filtro `VetoPreap` mejora:** `+34,0 → +36,2 R` y baja DD `-19,1 → -13,6 R`. |
| **`Franklin_NQ`** *(base)* | [`NT8_Franklin_NQ.csv`](corridas_nt8_nuevas/NT8_Franklin_NQ.csv) | 743 | `+34,01 R` | `+0,046` | `-19,08 R` | `6/8` | `-5,92 R` | `0,336` | Dominada por `Franklin_VetoPreap_NQ`. |
| **`C2_EVRP_NQ`** | [`NT8_C2_EVRP_NQ.csv`](corridas_nt8_nuevas/NT8_C2_EVRP_NQ.csv) | 615 | `+12,55 R` | `+0,020` | `-8,18 R` | `6/8` | `-0,05 R` | `-0,008` | **Descartada:** devuelve ~100% en `2022–2024`; inferior a `C2_VZ`. |
| **`C2_EVRP_ES`** | [`NT8_C2_EVRP_ES.csv`](corridas_nt8_nuevas/NT8_C2_EVRP_ES.csv) | 652 | `+0,68 R` | `+0,001` | `-9,48 R` | `6/8` | `-0,09 R` | `0,004` | **Descartada:** prácticamente `0` neto con veto de noticias. |
| **`ES5N_ES`** | [`NT8_ES5N_ES.csv`](corridas_nt8_nuevas/NT8_ES5N_ES.csv) | 411 | `+9,65 R` | `+0,023` | `-16,52 R` | `4/8` | `-10,01 R` | `0,461` | **Descartada:** `MaxDD` casi `2×` su ganancia total y duplica `RQ5_ES`. |

---

## 2. Diagnóstico del patrón de caída en Junio–Septiembre 2026: factor común, NO sobreajuste

1. **Por qué cayeron juntas `RQ5_ES`, `RQ5_NQ`, `ES5N_ES` y `Franklin_NQ` en Jun–Sep 2026:**
   - Todas pertenecen al **mismo factor económico**: *continuación / momentum intradía a partir de las 10:00 NY hasta el cierre 16:00 NY* (correlación diaria entre `0,26` y `0,63`).
   - Ninguna fue optimizada sobre `2026` (`RQ5` es la regla publicada por Zarattini et al. 2024; `Franklin` viene de Traders Hub). El tramo Jun–Sep 2026 fue un régimen de baja persistencia intradía + compresión de volatilidad.
2. **Prueba de descorrelación en el mismo trimestre (`Jun–Sep 2026`):**
   - Mientras el bloque de momentum `10:00 NY` caía (`-3,9 R` a `-10,2 R`), **`C2_VZ` (compresión de volatilidad, correlación `0,00` contra `RQ5`) ganó `+2,23 R` en `NQ` y `+2,21 R` en `ES`**, rompiendo máximos históricos.
   - Combinando **`0,5×RQ5_NQ + 0,5×RQ5_ES + 0,5×C2_VZ_NQ + 0,5×C2_VZ_ES`** sobre los propios CSVs de NT8 (`2019–2026`): **`+83,00 R`**, `MaxDD = -13,36 R`, **`8/8` años positivos (`2019–2026`)**.
3. **Papel del sizing (`Contratos fijos = 1` vs `R` constante):**
   - En `RQ5_NQ`, `2026` parece perder fuerte en dólares (`-354 pts`) pero **está positivo en `R` (`+2,07 R`)**. El riesgo constante (`Contratos fijos = 0` en micros `MNQ/MES`) elimina la amplificación visual `3×` de `2025–2026`, pero **no** salva estrategias con mal `Calmar` (`ES5N_ES`, `C2_EVRP`).
