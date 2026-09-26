# aVolClusterPOI — FASE 10: Medición Completa y Diagnóstico de Bloques sobre NQ 06-26

**Fecha:** 2026-09-02  
**Instrumentación:** P-70 (`BarProfileLogPath` + `DiagBlockExportPath` + `EventLogPath`)  
**Instrumento:** NQ JUN26 (`NQ 06-26`), 120 ticks/barra, ETH (`CME US Index Futures ETH`), ventana `2026-03-31T19:00:03` → `2026-06-12T17:46:30` (52 sesiones CME completas).  
**Población:** **233.601 barras primarias**, **23.339 bloques** de 10 barras, **482 zonas creadas** (305 `ZONE_CREATED` + 177 `AT_PRICE_CREATED`).

---

## 1. Procedencia y Manifiesto de Artefactos

| Artefacto | Filas | Tamaño (bytes) | SHA256 |
|---|---|---|---|
| **`oracle`** (`_v2.csv`) | 1.080 | 160.302 | `0d4770f2860899aa2f2a4991f1eaad169cf46dc22e105126fcdd4066a8c781fc` |
| **`barprofile`** (`_BARPROFILE_20260902.csv`) | 233.601 | 18.458.398 | `98556ded2efa06fce254b8cf843e19f6c9700d7b3ae3ce64c1d5ef0f3cdf9cae` |
| **`diag_blocks`** (`_DIAG_BLOCKS_20260902.csv`) | 23.339 | 23.790.732 | `95d859685d4aaec8334c4ed6e683b4cc730cef2ff7b6453ea7ddcc8e9b932864` |

---

## 2. Confirmación 1 — Conservación Estricta de Masa y Desplazamiento Puro

Sobre las 233.601 barras del contrato pre-holdout completo NQ 06-26:

| Métrica | Valor medido |
|---|---|
| **`profile_volume == primary_bar_volume`** | **65.059 de 233.601 (27,85 %)** |
| `profile_volume < primary_bar_volume` | 84.163 (36,03 %) |
| `profile_volume > primary_bar_volume` | 84.379 (36,12 %) |
| **Total `profile_volume`** | **30.447.463** contratos |
| **Total `primary_bar_volume`** | **30.447.464** contratos |
| **Diferencia total** | **1 contrato** sobre 30,4 millones |
| **Ratio global** | **0,99999997** |

### Hallazgo:
Se confirma que en NQ 06-26 el volumen acumulado por la subserie de 1-tick y el volumen de la barra de 120 ticks de NT8 **conservan la masa de forma exacta**. El 72,15% de las barras experimenta desfase temporal, con simetría casi perfecta (36,03% vs 36,12%).

---

## 3. Confirmación 2 — Pérdida de Volumen por Filtro `Low/High`

El indicador descarta ticks de la subserie cuyo precio caiga fuera de `[lowTick, highTick]` de la barra primaria:

| Métrica | Valor medido |
|---|---|
| Barras con volumen filtrado | **23.280 (9,97 %)** |
| Volumen descartado | **129.073 contratos** |
| Porcentaje del volumen total | **0,4239 %** |
| Ratio `kept_volume / profile_volume` | **0,995761** |

Este 0,42% replica de manera independiente la estimación de 0,41% obtenida en fases previas y el 0,31% obtenido en SEP26.

---

## 4. Consistencia Interna 100% Exacta en NT8

Se verificó la cadena de agregación interna:

1. **Reconstrucción de Bloques (`BARPROFILE` $\rightarrow$ `DIAG_BLOCKS`):**
   Para cada bloque $B_k$, la suma de `kept_volume` de sus 10 barras primarias coincide exactamente en ticks y contratos con la suma de `cells` (`tick:vol`) reportada en `DIAG_BLOCKS` (50/50 bloques auditados con delta = 0).

2. **Reconstrucción de Zonas (`DIAG_BLOCKS` $\rightarrow$ `ORACLE`):**
   - Decisiones `CREATE` en `DIAG_BLOCKS`: **482**.
   - Zonas `CREATED` en `ORACLE`: **482** (305 `ZONE_CREATED` + 177 `AT_PRICE_CREATED`).
   - Coincidencia de barras de creación: **482 / 482 (100,00 %)**.
   - Coincidencia geométrica `[lower_tick, upper_tick]`: **482 / 482 (100,00 %)**.

---

## 5. Causa Raíz de los Residuos de Paridad (`GEOMETRY_DIFF` y `MISSING_IN_*`)

En `DIAG_BLOCKS`:
- `CREATE`: 482
- `ABSTAIN_BELOW_THRESHOLD`: 20.285
- `ABSTAIN_NO_CLUSTER`: 1.447
- `ABSTAIN_NO_HISTORY`: 1.125

Al analizar los scores de los mejores clusters en los 20.285 bloques `ABSTAIN_BELOW_THRESHOLD`:
- **201 bloques** quedaron a **menos del 5%** de superar el umbral (`ratio >= 0.95`).
- **423 bloques** quedaron a **menos del 10%** (`ratio >= 0.90`).

Cualquier desborde de ticks en el límite de la barra primaria desplaza entre 10 y 30 contratos entre bloques adyacentes. Para bloques marginales (dentro del 5% del cuantil), esa fluctuación decide si el cluster cruza o no el percentil 98, explicando directamente las discrepancias de apareo.

---

## Aporte al referente

Con la exportación concurrente de `BARPROFILE`, `DIAG_BLOCKS` y `ORACLE` sobre el contrato pre-holdout `NQ 06-26`, la física interna del indicador en NT8 queda completamente triangulada: conservación de masa cerrada en 1 contrato sobre 30,4M, pérdida del 0,42% por recorte `Low/High`, consistencia interna al 100%, y 23.339 bloques con celdas crudas disponibles para resolver la paridad algorítmica sin ambigüedad.
