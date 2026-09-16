# Censo Target-Free Preliminar (Smoke Census): HP007-CAMP-002

- **Campaña:** `HP007-CAMP-002` (Fase Estructural — Checkpoint 1)
- **Fecha de Ejecución:** `2026-09-15`
- **Ancla Contractual:** Commit [`29cad93d6600ee4c07a7d716be35e4881d78f491`](https://github.com/Nicodelcampo/EdgeLab/commit/29cad93d6600ee4c07a7d716be35e4881d78f491)
- **Rama Canónica:** `work/hp007-rejection-revisit-campaign-v2-canonical-20260915`
- **Partición Evaluada:** `NQ 06-26` (Sesión CME `2026-06-03`)
- **Archivo Fuente:** `data/nt8/NQ_parquet/NQ_06-26_ticks.parquet`
- **Ticks Analizados:** `572.504` transacciones

---

## 1. Verificación de Seguridad y Firewall de Holdout

1. **Aislamiento Estricto de Holdout**:
   - Marca de tiempo inicial evaluada: `2026-06-02T22:00:00Z` (`1780437600000000000` ns).
   - Marca de tiempo final evaluada: `2026-06-03T21:00:00Z` (`1780520400000000000` ns).
   - Límite exterior de holdout sellado: `2026-06-30T22:00:00Z` (`1782856800000000000` ns).
   - **Resultado:** Cero filas leídas ni derivadas dentro o después del holdout. Sellado 100% íntegro.

---

## 2. Configuración de Detección Target-Free (`RevisitSpec`)

Para esta medición exploratoria preliminar se utilizaron parámetros target-free canónicos:
- `approach_ticks`: `2` ticks
- `rejection_excursion_ticks`: `8` ticks
- `min_away_seconds`: `60.0` segundos
- `min_away_volume`: `50.0` contratos
- `max_episode_seconds`: `1800.0` segundos (30 minutos)
- `crossing_buffer_ticks`: `0` ticks

Se distribuyeron 10 bandas de vacío candidatas congeladas sobre el rango de cotización de la sesión (rango: 121.913 a 123.231 ticks, amplitud total de 1.318 ticks), evaluando de forma independiente aproximaciones por el lado comprador (`side = +1`) y vendedor (`side = -1`).

---

## 3. Distribución de Estados Terminales y Censura

Se detectaron **425 episodios estructurados** ordenados causalmente (`first_approach < rejection_confirm < away_qualified < second_approach`):

| Estado Terminal | Conteo | Porcentaje | Descripción Causal |
|---|---|---|---|
| **`TRAVERSED`** | `255` | 60.0% | El precio re-aproximó al vacío congelado y atravesó su frontera lejana. |
| **`REJECTED_AGAIN`** | `136` | 32.0% | El precio re-aproximó pero volvió a ser rechazado alejándose $\ge 8$ ticks. |
| **`CENSORED_MAX_FOLLOWUP`** | `33` | 7.8% | Transcurrieron más de 30 minutos desde el inicio sin resolver. |
| **`CENSORED_DATA_EDGE`** | `1` | 0.2% | La frontera final del dataset fue alcanzada con el episodio activo. |
| **`CENSORED_CONTRACT_ROLL`** | `0` | 0.0% | Sesión pre-roll (el roll forward formal de NQ 06-26 ocurre el 2026-06-11). |
| **`CENSORED_SESSION_END`** | `0` | 0.0% | Ningún episodio calificado quedó truncado por cierre de sesión. |
| **Total** | **`425`** | **100.0%** | **Cero episodios ambiguos o no categorizados** |

---

## 4. Métricas del Periodo de Alejamiento (Away Phase)

| Métrica | Mediana | Mínimo | Máximo |
|---|---|---|---|
| **Tiempo de alejamiento (`elapsed_away_seconds`)** | `68.5 s` | `60.0 s` | `1804.6 s` |
| **Volumen negociado en alejamiento (`volume_away`)** | `1.096` | `50.0` | `96.541` |
| **Excursión máxima alcanzada (`max_excursion_ticks`)** | `42.0 ticks` | `8.0 ticks` | `1.197.0 ticks` |

---

## 5. Dictamen del Checkpoint 1

1. La máquina de estados de detección en [`edgelab/research/void_revisit_episodes.py`](file:///E:/EdgeLab/edgelab/research/void_revisit_episodes.py) implementa con total fidelidad causal la ordenación estricta y la taxonomía de cuatro censuras.
2. Los episodios se construyen exclusivamente con información target-free, sin ninguna relación con P&L, Sharpe ni optimizaciones directivas.
3. Se respeta la condición de parada: al estar en abstención la paridad de BigTrap2Absorption por falta de oráculo real exportado de NT8, **la investigación se detiene en este punto**. No se generan outcomes confirmatorios ni barridos amplios.
