# Índice de Inspección Visual Lógica — HP007-CAMP-002
## Fase de Diseño Visual Target-Free (Visual Logic Design)

- **Activo Canónico:** `NQ 06-26` (Tick size: 0.25)
- **Ancla Contractual:** [`29cad93d6600ee4c07a7d716be35e4881d78f491`](https://github.com/Nicodelcampo/EdgeLab/commit/29cad93d6600ee4c07a7d716be35e4881d78f491)
- **Documento Rector:** [`docs/research/HP007_CAMP002_VISUAL_LOGIC_CATALOG_2026-09-15.md`](HP007_CAMP002_VISUAL_LOGIC_CATALOG_2026-09-15.md)
- **Watermark Mandatorio:** `PARITY_ABSTAIN — PYTHON EXPLORATORY VISUALIZATION ONLY`
- **Estado Oficial:** `READY_FOR_OWNER_VISUAL_REVIEW = YES`

> [!IMPORTANT]
> **Directiva del Propietario:** Queda prohibida toda medición empírica o estimación de edge.
> La función de este índice es permitir la inspección visual neutral de zonas y campos para que el propietario defina la semántica de los eventos.

---

## Tabla de Gráficos Generados

| ID Gráfico | ID Sesión | Fecha CME | Criterio de Selección | Configuración | Descripción de la Variante | Enlace Local |
|---|---|---|---|---|---|---|
| `HP007_VISUAL_SESS_01_BT2A_CFG_01` | `SESS_01` | `2026-03-17` | EARLIEST_ACTIVE_PRE_HOLDOUT_SESSION | `BT2A_CFG_01` | Baseline canonical setup from F0/P0 spec | [HP007_VISUAL_SESS_01_BT2A_CFG_01.png](visual_charts/HP007_VISUAL_SESS_01_BT2A_CFG_01.png) |
| `HP007_VISUAL_SESS_02_BT2A_CFG_01` | `SESS_02` | `2026-04-01` | MEDIAN_ACTIVITY_SESSION | `BT2A_CFG_01` | Baseline canonical setup from F0/P0 spec | [HP007_VISUAL_SESS_02_BT2A_CFG_01.png](visual_charts/HP007_VISUAL_SESS_02_BT2A_CFG_01.png) |
| `HP007_VISUAL_SESS_02_BT2A_CFG_04` | `SESS_02` | `2026-04-01` | MEDIAN_ACTIVITY_SESSION | `BT2A_CFG_04` | Highly selective absorption percentile (95.0%) | [HP007_VISUAL_SESS_02_BT2A_CFG_04.png](visual_charts/HP007_VISUAL_SESS_02_BT2A_CFG_04.png) |
| `HP007_VISUAL_SESS_02_BT2A_CFG_08` | `SESS_02` | `2026-04-01` | MEDIAN_ACTIVITY_SESSION | `BT2A_CFG_08` | Stacked absorption zones (min 2 adjacent price levels) | [HP007_VISUAL_SESS_02_BT2A_CFG_08.png](visual_charts/HP007_VISUAL_SESS_02_BT2A_CFG_08.png) |
| `HP007_VISUAL_SESS_02_BT2A_CFG_09` | `SESS_02` | `2026-04-01` | MEDIAN_ACTIVITY_SESSION | `BT2A_CFG_09` | Directional signed score mode (AbsDirectional) | [HP007_VISUAL_SESS_02_BT2A_CFG_09.png](visual_charts/HP007_VISUAL_SESS_02_BT2A_CFG_09.png) |
| `HP007_VISUAL_SESS_03_BT2A_CFG_01` | `SESS_03` | `2026-03-17` | CONTRACT_ROLL_BOUNDARY_SESSION | `BT2A_CFG_01` | Baseline canonical setup from F0/P0 spec | [HP007_VISUAL_SESS_03_BT2A_CFG_01.png](visual_charts/HP007_VISUAL_SESS_03_BT2A_CFG_01.png) |
| `HP007_VISUAL_SESS_04_BT2A_CFG_01` | `SESS_04` | `2026-04-08` | HIGH_VOLATILITY_WIDE_RANGE_SESSION | `BT2A_CFG_01` | Baseline canonical setup from F0/P0 spec | [HP007_VISUAL_SESS_04_BT2A_CFG_01.png](visual_charts/HP007_VISUAL_SESS_04_BT2A_CFG_01.png) |
| `HP007_VISUAL_SESS_05_BT2A_CFG_01` | `SESS_05` | `2026-05-22` | LOW_VOLATILITY_NARROW_RANGE_SESSION | `BT2A_CFG_01` | Baseline canonical setup from F0/P0 spec | [HP007_VISUAL_SESS_05_BT2A_CFG_01.png](visual_charts/HP007_VISUAL_SESS_05_BT2A_CFG_01.png) |

---

## Checklist para la Inspección Visual del Propietario

1. **Comparación de Sensibilidad en SESS_02 (Mediana de Actividad):**
   - Compare `HP007_VISUAL_SESS_02_BT2A_CFG_01` (Baseline 90%) con `BT2A_CFG_04` (Restrictiva 95%): ¿Qué densidad de zonas resulta interpretable sin saturar el espacio?
   - Observe `BT2A_CFG_08` (Zonas agrupadas min 2 filas): ¿Las zonas más gruesas capturan mejor los vacíos o los estrechan excesivamente?
   - Observe `BT2A_CFG_09` (Direccional): ¿Aporta mejor asimetría entre vacíos superiores e inferiores?
2. **Verificación de Rollover en SESS_03:**
   - Verifique en `HP007_VISUAL_SESS_03_BT2A_CFG_01` que la línea roja vertical `state_reset_flag == True` purgue adecuadamente el estado.
3. **Comportamiento en Extremos de Volatilidad:**
   - `HP007_VISUAL_SESS_04_BT2A_CFG_01` (Alta volatilidad, rango 3.608t / 902 pts): Evalúe si el desgaste por toques (`NO_WEAR` vs `FULL`) es visualmente perceptible.
   - `HP007_VISUAL_SESS_05_BT2A_CFG_01` (Bajo rango / compresión, rango 1.252t / 313 pts): Observe si los vacíos estrechos ($W < 5$ ticks) son absorbidos por el kernel gaussiano.

### Aporte al Referente
Se publica el paquete visual y el índice completo de inspección en `docs/research/HP007_CAMP002_VISUAL_INDEX_2026-09-15.md` y `docs/research/visual_charts/`. Quedan renderizadas las alternativas visuales comparables y neutrales sobre NQ 06-26 con watermark mandatorio, listas para la decisión semántica del propietario.
