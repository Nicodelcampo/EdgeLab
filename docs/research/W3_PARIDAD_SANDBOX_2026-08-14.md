# W3 — Paridad sandbox de aVolClusterPOI v0.5 sobre ES 09-26 — 2026-08-14

Réplica diagnóstica, target-free, no adjudicadora (precedente W1). Cierra la pata ES del plan de paridad con el paquete mensual `paquete_w3_ES_0926_mensual.zip`.

## 0. Resultado en una línea

**Paridad de creación demostrada: 100 % exacta antes del defecto de datos del 11-jun (119/119, todos los campos), 98,7 % después (307/311); el único día divergente es el 11-jun, por un defecto de datos (P-15), no del kernel.**

## 1. Paquete y verificación

| pieza | sha256 | estado |
|---|---|---|
| `ES_09-26_2026-04_ticks.parquet` (13.825) | `fd9a4839a24fb5ea…` | ✓ coincide con lo declarado |
| `ES_09-26_2026-05_ticks.parquet` (27.120) | `65e26fa587f5a590…` | ✓ |
| `ES_09-26_2026-06_ticks.parquet` (12.944.494) | `e11d664d51d7ea88…` | ✓ |
| oráculo `avolcluster_v05_ES_0926.csv` (1.066 eventos) | `7e2b470139316727…` | ✓ (el mismo ya verificado en P-11) |

- Ensamble mensual: costuras estrictamente crecientes, sin solapes; 12.985.439 ticks; monótono global ✓; contrato uniforme `ES 09-26` ✓; 67 sesiones CME ETH.
- Nota de manifiesto (declarada): `total_ticks_90d = 13.015.395` vs suma de partes 12.985.439 → 29.956 ticks fuera del corte mensual (mismo patrón que el 6E 90d, que incluía horas post-30-jun).
- Kernel `avolclusterpoi.py` y `sessions.py` **byte-exactos** del repo (blobs `e472a06899e3d76287072fdbeef4b95604101eb3` y `491211fd2720087bb8e21c86f7faae572ba66606`, verificados por git-blob en el sandbox).
- Desviación declarada: celdas = volumen total por nivel, vectorizado (≡ `fps.total` por construcción; aVol no usa la clasificación bid/ask). Identidad por barra (|Σceldas − volumen| ≤ 0,5): 0 violaciones.

## 2. Warmup replicado con exactitud

El oráculo declara en su primer evento (05-01 11:01 ART) `session_index=22, samples=25`: la instancia NT8 cargó desde el 01-abr (21–22 sesiones de historia). El replay, arrancando el perfil en la primera sesión del parquet, reproduce **(22, 25) exactamente** — y el primer evento coincide al segundo: `ZONE_CREATED 29374–29375, score 81` (oráculo: idéntico).

## 3. Resultado global y segmentado (corte en el defecto del 11-jun)

| segmento | matched | missing | extras | notas |
|---|---|---|---|---|
| 05-01 → 06-10 | **119/119 (100 %)** | 0 | 0 | ZONE_CREATED: **0/96 con algún campo distinto** (score, threshold, samples, session_index, direction, distance, bucket, tiempo — todos exactos) |
| 06-11 | 16 | 21 | 21 | divergencia de fase de bloques (~2 barras) → P-15 |
| 06-12 → 06-30 | **307/311 (98,7 %)** | 4 | 6 | creaciones se re-alinean al instante; residuos = contaminación de historial del 06-11 + drift de conteo de sesiones desde el 21-jun |
| **global** | **442/467 (94,6 %)** | 25 | 27 | **TODAS las emparejadas: Δtiempo = 0 (al segundo), Δbucket = 0, Δdistance = 0** |

Oráculo: 467 creaciones (308 ZONE_CREATED + 159 AT_PRICE_CREATED) + 302 ZONE_INVALIDATED + 297 FIRST_TOUCH = 1.066. El replay emite 469 (314 + 155).

## 4. Los tres residuos, todos explicados

1. **P-15 — el 11-jun diverge por datos, no por kernel.** Mis bloques cierran ~2 min antes que los del oráculo desde la mañana (offset estable durante todo el RTH): mi serie tiene ~2 barras menos que la de NT8 ese día. Mi parquet no muestra hueco propio en RTH (19 gaps de 60–93 s, todos en la madrugada del 10→11 CT, horario ilquido). Requiere la comparación nativo-vs-parquet minuto a minuto en local — mismo patrón que P-14 (6E, 25-jun), que resultó ser defecto del build, no de la fuente.
2. **`direction` en AT_PRICE: artefacto cosmético.** Los 148 Δdirection son 100 % AT_PRICE_CREATED: el oráculo escribe `NEUTRAL`, el kernel `None`. En ZONE_CREATED: 294/294 exacta. Nota de unificación: que el kernel emita `NEUTRAL`.
3. **Drift de `session_index` desde el 21-jun (domingo).** El conteo de sesiones diverge por 1 desde la frontera domingo 21 → lunes 22 (96 pares post). Es una etiqueta (no alimenta la matemática), pero arrastra `samples` (67) en buckets cuya historia cambia de composición. Documentado para alinear la convención del SessionIterator en la frontera dominical.

## 5. Notas de formato (para el próximo agente)

- El oráculo aVol es **CSV con comas y header** (`event_seq,event_type,bar_index,bar_close_time,session_index,bucket,zone_id,lower_tick,upper_tick,score,threshold,samples,touch_count,reason,direction,anomaly_ratio,cluster_share,density,quality_score,distance_ticks,burst_count,touch_bar,mfe_ticks,mae_ticks,outcome`) — distinto del formato pipe de BigTrap2. En eventos de creación, la columna `reason` lleva el KIND (`OFF_PRICE`/`AT_PRICE`).
- La comparación de ciclo de vida (302 INVALIDATED / 297 FIRST_TOUCH) queda como trabajo futuro — las creaciones son el ancla de paridad (precedente W1).

## 6. Estado

**W3 CERRADA a nivel diagnóstico**: el kernel aVol v0.5 reproduce el oráculo ES 09-26 al 100 % fuera del día defectuoso. Etiqueta formal: de la corrida local gobernada tras regenerar junio ES (P-15). Cero outcomes, cero P&L, cero holdout.
