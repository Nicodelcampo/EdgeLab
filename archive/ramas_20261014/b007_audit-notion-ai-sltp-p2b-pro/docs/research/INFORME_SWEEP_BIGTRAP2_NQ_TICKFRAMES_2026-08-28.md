# INFORME DE INVESTIGACIÓN: Sweep Retrospectivo de Resoluciones de Barra de BigTrap2 sobre NQ (Evidencia Expuesta V1)

**Fecha:** 2026-08-28  
**Rama:** `research/bigtrap2-nq-tickframes-sweep-v1-20260828`  
**Spec Vinculada:** [`specs/bigtrap2_nq_tickframes_sweep_v1.json`](../specs/bigtrap2_nq_tickframes_sweep_v1.json)  
**Resultado Canónico:** [`docs/research/bigtrap2_nq_tickframes_sweep_result.json`](bigtrap2_nq_tickframes_sweep_result.json)  
**Clasificación Sidecar:** [`docs/research/bigtrap2_nq_tickframes_sweep_result_classification.json`](bigtrap2_nq_tickframes_sweep_result_classification.json)  
**SHA-256 del Resultado:** `4716148209c44ea42e801a0717ead2eb357cf4d635b0f0c01ed72e161d342713`  
**Estado:** `COMPLETE_RETROSPECTIVE_SWEEP_PUBLICATION_WITH_EXPOSURE`  

---

## 1. Resumen Ejecutivo y Declaración de Integridad

> [!WARNING]
> **Reclasificación Contractual por Exposición de Lifecycle y Holdout:**  
> Esta corrida inicial utilizó una lectura sin acotar en memoria de `NQ_09-26_ticks.parquet` (`HOLDOUT_ROWS_DECODED = true`) e invocó el kernel con lifecycle (`update_zones`), accediendo a trayectorias de precios posteriores a la barra de creación (`FUTURE_PRICE_PATH_ACCESSED = true` y `FIRST_TOUCH_ACCESSED = true`).  
> Los resultados se preservan formalmente como evidencia empírica expuesta, pero **no habilitan selección de ganador ni construcción de Event Store**.

```text
SWEEP_EXECUTION_COMPLETE               = true
CREATION_COUNTS_PUBLISHED              = true
STRICT_TARGET_FREE_EXECUTION           = false
FUTURE_PRICE_PATH_ACCESSED             = true
FIRST_TOUCH_ACCESSED                   = true
PNL_ACCESSED                           = false
HOLDOUT_ROWS_DECODED                   = true
HOLDOUT_FIREWALL_PROVEN                = false
WINNER_SELECTED                        = false
CONFIRMATORY_ELIGIBLE                  = false
EVENT_STORE_BUILD_ELIGIBLE             = false
TOTAL_CONFIGURATIONS_TESTED            = 112
TOTAL_INSTRUMENT_CONTRACTS             = 5 (NQ 09-25, 12-25, 03-26, 06-26, 09-26)
TOTAL_CME_SESSIONS                     = 234
TOTAL_EXECUTION_TIME_SECONDS           = 16391.9 (~4.55 horas)
COVERAGE_PRE_HOLDOUT                   = 100% (234/234 sesiones)
```

---

## 2. Advertencia Metodológica Fundamental: Densidad Bruta vs. Saturación Espuria

> [!WARNING]
> **Densidad bruta alta NO equivale a mayor calidad de señal.**  
> En una sesión típica de CME (duración efectiva ~1.380 minutos en RTH/ETH), una configuración con $3.723{,}6\text{ eventos/sesión}$ genera en promedio **~2,7 a 4,5 eventos por minuto**. Frente a un universo de ~25 zonas de AVolClusterPOI por sesión, cualquier ventana temporal o espacial alrededor de una zona encontraría eventos BigTrap2 casi con certeza por mero azar.  
> Esto inflaría artificialmente la tasa de "confluencia" o coincidencia causal trivial.

### Dimensiones Críticas a Auditar antes de Fijar Selección
Antes de declarar o congelar una configuración operativa para el Event Store de BigTrap2 NQ, deben auditarse rigurosamente de forma *target-free*:
1. **Fracción de barras activas y tasa de eventos por minuto:** Evitar configuraciones donde $>10\%$ de las barras disparan absorción.
2. **Tiempo mediano entre eventos sucesivos e inter-arrival time:** Distinguir eventos aislados de ráfagas (*burstiness*).
3. **Colapso de episodios (*Episode Collapse*):** Agrupar múltiples burbujas continuas generadas en el mismo micro-movimiento en un único evento representativo.
4. **Período refractario (*Refractory Period*):** Aplicar una ventana mínima de enfriamiento (ej. 3 a 5 barras o 30 segundos) para eliminar duplicados espaciales y temporales.
5. **Estabilidad entre contratos (09-25 a 09-26):** Comprobar que la frecuencia no sufra saltos estructurales por cambio de volumen.
6. **Tasa de coincidencia aleatoria contra zonas AVol:** Medir el solapamiento nulo contra timestamps permutados para descontar confluencias espurias.

---

## 3. Grilla Evaluada (112 Configuraciones)

La grilla factorial exacta cubrió:
* **7 Resoluciones de Barra:**
  * Micro-ticks: `tick_10`, `tick_25`, `tick_50`, `tick_100`, `tick_120`, `tick_240`.
  * Barras de Tiempo: `time_1m`.
* **4 Ratios de Desbalance (Imbalance Ratio):** `2.5`, `3.0`, `3.5`, `4.0`.
* **4 Umbrales de Volumen Mínimo Atrapado (MinTrapVolume):** `10`, `20`, `50`, `100` contratos.

Total: $7 \times 4 \times 4 = 112\text{ configuraciones}$ evaluadas sobre los 5 contratos Parquet de NQ.

---

## 4. Comparativa por Tipo de Resolución de Barra (Datos Exactos V1)

| Tipo de Barra | Eventos Promedio | Cobertura Promedio | % Compradores (Buy Ratio) | Configuración Máxima Densidad | Eventos Máx | Ev/Ses Máx | Ancho Mediano (Ticks) | Ancho p95 (Ticks) |
|---|---|---|---|---|---|---|---|---|
| **`tick_10`** | $31.091{,}8$ | $88{,}5\%$ | $51{,}6\%$ | `tick_10_IMB25_VOL10` | $112.317$ | $480{,}0$ | $2{,}0\text{ t}$ | $4{,}0\text{ t}$ |
| **`tick_25`** | $126.418{,}0$ | $94{,}1\%$ | $50{,}5\%$ | `tick_25_IMB25_VOL10` | $554.509$ | $2.369{,}7$ | $3{,}0\text{ t}$ | $8{,}0\text{ t}$ |
| **`tick_50`** | $208.783{,}6$ | $98{,}4\%$ | $50{,}6\%$ | `tick_50_IMB25_VOL10` | $849.592$ | $3.630{,}7$ | $5{,}0\text{ t}$ | $14{,}0\text{ t}$ |
| **`tick_100`** | $250.047{,}7$ | $99{,}4\%$ | $50{,}7\%$ | `tick_100_IMB25_VOL10` | $871.322$ | $3.723{,}6$ | $7{,}0\text{ t}$ | $24{,}0\text{ t}$ |
| **`tick_120`** | $250.642{,}2$ | $99{,}4\%$ | $50{,}6\%$ | `tick_120_IMB25_VOL10` | $830.209$ | $3.547{,}9$ | $8{,}0\text{ t}$ | $28{,}0\text{ t}$ |
| **`tick_240`** | $220.198{,}2$ | $100{,}0\%$ | $50{,}2\%$ | `tick_240_IMB25_VOL10` | $589.818$ | $2.520{,}6$ | $12{,}0\text{ t}$ | $44{,}0\text{ t}$ |
| **`time_1m`** | $129.515{,}9$ | $99{,}9\%$ | $49{,}8\%$ | `time_1m_IMB25_VOL10` | $309.364$ | $1.322{,}1$ | $12{,}0\text{ t}$ | $73{,}0\text{ t}$ |

---

## 5. Top 15 Configuraciones Globales (Datos Exactos V1)

| Ranking | Configuración (`cfg_id`) | Total Eventos | Cobertura | Ev/Sesión | Buy / Sell | Buy Ratio | Ancho Mediano | Ancho p95 |
|---|---|---|---|---|---|---|---|---|
| **1** | `tick_100_IMB25_VOL10` | $871.322$ | $100{,}0\%$ | $3.723{,}6$ | $435.520$ / $435.802$ | $0{,}500$ | $7{,}0\text{ t}$ | $24{,}0\text{ t}$ |
| **2** | `tick_50_IMB25_VOL10` | $849.592$ | $100{,}0\%$ | $3.630{,}7$ | $424.984$ / $424.608$ | $0{,}500$ | $5{,}0\text{ t}$ | $14{,}0\text{ t}$ |
| **3** | `tick_120_IMB25_VOL10` | $830.209$ | $100{,}0\%$ | $3.547{,}9$ | $413.971$ / $416.238$ | $0{,}499$ | $8{,}0\text{ t}$ | $28{,}0\text{ t}$ |
| **4** | `tick_100_IMB30_VOL10` | $795.546$ | $100{,}0\%$ | $3.399{,}8$ | $397.591$ / $397.955$ | $0{,}500$ | $7{,}0\text{ t}$ | $24{,}0\text{ t}$ |
| **5** | `tick_50_IMB30_VOL10` | $776.316$ | $100{,}0\%$ | $3.317{,}6$ | $388.349$ / $387.967$ | $0{,}500$ | $5{,}0\text{ t}$ | $14{,}0\text{ t}$ |
| **6** | `tick_120_IMB30_VOL10` | $759.477$ | $100{,}0\%$ | $3.245{,}6$ | $378.692$ / $380.785$ | $0{,}499$ | $8{,}0\text{ t}$ | $28{,}0\text{ t}$ |
| **7** | `tick_240_IMB25_VOL10` | $589.818$ | $100{,}0\%$ | $2.520{,}6$ | $293.748$ / $296.070$ | $0{,}498$ | $12{,}0\text{ t}$ | $44{,}0\text{ t}$ |
| **8** | `tick_100_IMB35_VOL10` | $581.827$ | $100{,}0\%$ | $2.486{,}4$ | $290.778$ / $291.049$ | $0{,}500$ | $5{,}0\text{ t}$ | $19{,}0\text{ t}$ |
| **9** | `tick_120_IMB35_VOL10` | $569.246$ | $100{,}0\%$ | $2.432{,}7$ | $284.002$ / $285.244$ | $0{,}499$ | $6{,}0\text{ t}$ | $22{,}0\text{ t}$ |
| **10** | `tick_25_IMB25_VOL10` | $554.509$ | $100{,}0\%$ | $2.369{,}7$ | $276.792$ / $277.717$ | $0{,}499$ | $3{,}0\text{ t}$ | $8{,}0\text{ t}$ |
| **11** | `tick_240_IMB30_VOL10` | $547.439$ | $100{,}0\%$ | $2.339{,}5$ | $272.628$ / $274.811$ | $0{,}498$ | $12{,}0\text{ t}$ | $45{,}0\text{ t}$ |
| **12** | `tick_100_IMB40_VOL10` | $541.640$ | $100{,}0\%$ | $2.314{,}7$ | $270.597$ / $271.043$ | $0{,}500$ | $5{,}0\text{ t}$ | $19{,}0\text{ t}$ |
| **13** | `tick_50_IMB35_VOL10` | $530.729$ | $100{,}0\%$ | $2.268{,}1$ | $265.308$ / $265.421$ | $0{,}500$ | $4{,}0\text{ t}$ | $11{,}0\text{ t}$ |
| **14** | `tick_120_IMB40_VOL10` | $529.670$ | $100{,}0\%$ | $2.263{,}6$ | $264.048$ / $265.622$ | $0{,}499$ | $6{,}0\text{ t}$ | $22{,}0\text{ t}$ |
| **15** | `tick_25_IMB30_VOL10` | $517.084$ | $100{,}0\%$ | $2.209{,}8$ | $258.180$ / $258.904$ | $0{,}499$ | $4{,}0\text{ t}$ | $8{,}0\text{ t}$ |

---

## 6. Candidato de Alineación de Clock: `tick_120_IMB25_VOL10`

- **Sincronización:** Comparte la misma resolución temporal de barra ($120\text{ ticks}$) que la infraestructura congelada de AVolClusterPOI Gate 1A (`tick_120_W5_M20_C4_P950`).
- **Comportamiento Direccional:** Neutralidad casi exacta ($50{,}1\%$ Sell vs $49{,}9\%$ Buy en $830.209$ eventos).
- **Condición Formal:** Se declara como **candidato técnico de alineación de clock**, **NO como ganador**. La selección final dependerá del filtro de no-saturación y del rerun en `v2` creation-only.

---

## Aporte al referente

El sweep retrospectivo V1 de 112 configuraciones de BigTrap2 sobre 234 sesiones de NQ queda documentado, reclasificado y preservado como evidencia empírica expuesta. Se establece formalmente la advertencia contra premiar saturación y se congela la infraestructura V2 creation-only y fail-closed antes de autorizar cualquier repetición o selección.
