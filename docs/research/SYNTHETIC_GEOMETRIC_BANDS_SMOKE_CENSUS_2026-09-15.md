# Censo Operativo de Software sobre Bandas Geométricas Sintéticas

- **Identificador del Estudio:** `SYNTHETIC_GEOMETRIC_BANDS_SOFTWARE_SMOKE_CENSUS`
- **Campaña:** `HP007-CAMP-002` (Fase Estructural — Checkpoint 1 Parcheado)
- **Fecha de Ejecución:** `2026-09-15`
- **Ancla Contractual:** Commit [`29cad93d6600ee4c07a7d716be35e4881d78f491`](https://github.com/Nicodelcampo/EdgeLab/commit/29cad93d6600ee4c07a7d716be35e4881d78f491)
- **Rama Canónica:** `work/hp007-rejection-revisit-campaign-v2-canonical-20260915`
- **Partición Evaluada:** `NQ 06-26` (Sesión CME `2026-06-03`, pre-holdout)
- **Archivo Fuente:** `data/nt8/NQ_parquet/NQ_06-26_ticks.parquet`
- **Ticks Analizados:** `572.504` transacciones
- **Runner Reproducible:** [`tools/run_synthetic_smoke_census.py`](../../tools/run_synthetic_smoke_census.py)
- **Datos Estructurados Machine-Readable:** [`docs/research/SYNTHETIC_GEOMETRIC_BANDS_SMOKE_CENSUS_2026-09-15.json`](SYNTHETIC_GEOMETRIC_BANDS_SMOKE_CENSUS_2026-09-15.json)

---

## 1. Naturaleza y Alcance Epistemológico del Censo

> [!IMPORTANT]
> **Advertencia de Interpretación Científica**:
> Este estudio es un **smoke test operativo de software** diseñado para comprobar el comportamiento dinámico de la máquina de estados de revisita, el aislamiento de holdout y la activación de las cuatro clases de censura.
> **Las diez bandas evaluadas son franjas geométricas sintéticas** colocadas uniformemente sobre el rango diario de precios. **No proceden de zonas activas de `BigTrap2Absorption` ni representan vacíos de liquidez reales**. Las tasas resultantes (60% `TRAVERSED`, 31% `REJECTED_AGAIN`) caracterizan exclusivamente el comportamiento geométrico sintético del software en esta corrida de prueba y **no constituyen evidencia estructural ni empírica de HP-007**.

---

## 2. Aislamiento Estricto de Holdout

- **Horizonte Evaluado:** `2026-06-02T22:00:00Z` a `2026-06-03T21:00:00Z`.
- **Límite de Holdout Sellado:** `2026-06-30T22:00:00Z` (`1782856800000000000` ns).
- **Resultado:** **CERO filas leídas o derivadas dentro o después del holdout**.

---

## 3. Especificación de Detección y Bandas Sintéticas

### 3.1. Parámetros (`RevisitSpec`)
- `approach_ticks`: `2` ticks
- `rejection_excursion_ticks`: `8` ticks
- `min_away_seconds`: `60.0` s
- `min_away_volume`: `50.0` contratos
- `max_episode_seconds`: `1800.0` s (30 min)
- `right_boundary_reason`: `"SESSION_END"`

### 3.2. Grilla Geométrica de 10 Bandas
Sobre un rango de cotización de 121.913 a 123.231 ticks (amplitud: 1.318 ticks), se generaron 10 bandas deterministas de 8 ticks de ancho (`BAND_01` a `BAND_10`), evaluando lado comprador (`side = +1`) y lado vendedor (`side = -1`). Sus especificaciones y hashes SHA-256 se encuentran registrados íntegramente en [`SYNTHETIC_GEOMETRIC_BANDS_SMOKE_CENSUS_2026-09-15.json`](SYNTHETIC_GEOMETRIC_BANDS_SMOKE_CENSUS_2026-09-15.json).

---

## 4. Resultados, Censura y Trazabilidad de Etapas

Se detectaron **426 episodios** (manteniendo los registros completos de eventos en almacenamiento local off-git, fuera del árbol de Git):

| Estado Terminal | Conteo | Porcentaje | Descripción Causal |
|---|---|---|---|
| **`TRAVERSED`** | `255` | 59.86% | Re-aproximó y cruzó la frontera lejana de la banda sintética. |
| **`REJECTED_AGAIN`** | `136` | 31.92% | Re-aproximó pero volvió a ser rechazado $\ge 8$ ticks. |
| **`CENSORED_MAX_FOLLOWUP`** | `33` | 7.75% | Transcurrió el plazo máximo de 30 minutos sin resolución. |
| **`CENSORED_SESSION_END`** | `2` | 0.47% | Cierre de la sesión regular alcanzado con el episodio activo. |
| **`CENSORED_CONTRACT_ROLL`** | `0` | 0.00% | Sesión pre-roll (roll forward de NQ 06-26 ocurre el 2026-06-11). |
| **`CENSORED_DATA_EDGE`** | `0` | 0.00% | Correctamente diferenciado de session end vía `right_boundary_reason`. |
| **Total** | **`426`** | **100.00%** | **No se observaron descartes silenciosos en los casos cubiertos por la suite.** |

### 4.1. Desglose de Etapa al Censurar (`stage_at_censoring`)
Para los 35 episodios censurados:
- `AWAY_ACCUMULATING`: `1` episodio (censurado mientras acumulaba tiempo/volumen de alejamiento).
- `AWAY_QUALIFIED`: `34` episodios (censurados tras calificar, esperando re-aproximación).

### 4.2. Manifiesto del Archivo Event-Level Off-Git
Siguiendo la política de repositorio liviano, los registros de episodios individuales no se versionan en Git:
- **Almacenamiento Local Off-Git:** `data/smoke_census/synthetic_geometric_bands_episodes_2026-09-15.json`
- **Registros Totales:** `426` episodios
- **Tamaño:** `220.375` bytes
- **SHA-256:** `a87dc4f9328888b30e0ae7cbc3eaff49ac07858fbea4169d7fcddf1b2eda735e`

---

## 5. Análisis de Dependencia y Superposición Cross-Band

> [!WARNING]
> **Advertencia de Multiplicación de Observaciones**:
> Las 10 bandas se evaluaron en el mismo flujo de ticks. Por ende, los episodios de distintas bandas no son independientes.

- **Máximo de episodios simultáneamente activos:** `11` episodios.
- **Episodios que solapan temporalmente con otra banda:** `380` de 426 (`89.20%`).
- **Conclusión metodológica:** Cualquier agregación estadística entre bandas en etapas posteriores requerirá clusterización de errores a nivel de sesión e identificación de propiedad unívoca para evitar inflación espuria de grados de libertad.

---

## 6. Métricas de la Fase de Alejamiento (Away Phase)

| Métrica | Mediana | Mínimo | Máximo |
|---|---|---|---|
| **Tiempo de alejamiento (`elapsed_away_seconds`)** | `68.5 s` | `43.1 s` | `1804.6 s` |
| **Volumen en alejamiento (`volume_away`)** | `1.090` | `50` | `96.541` |
| **Excursión máxima (`max_excursion_ticks`)** | `42.0 ticks` | `8 ticks` | `1.197 ticks` |

---

## 7. Dictamen Final del Smoke Census

1. La máquina de estados en [`void_revisit_episodes.py`](../../edgelab/research/void_revisit_episodes.py) resuelve correctamente las 4 censuras, no confunde cierre de sesión con límite de datos, preserva la causa específica en `boundary_reason` y audita el estadio de pérdida de cobertura (`stage_at_censoring`).
2. Se confirma la reproducibilidad total mediante [`tools/run_synthetic_smoke_census.py`](../../tools/run_synthetic_smoke_census.py).
3. **Condición de Parada Respetada**: No se realizan interpretaciones empíricas de estos datos hacia HP-007; el desarrollo queda detenido a la espera de oráculos reales de NT8.
