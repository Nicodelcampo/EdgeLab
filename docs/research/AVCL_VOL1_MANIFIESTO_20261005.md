# AVCL-VOL-1 — ¿una zona de aVolClusterPOI precede expansión de volatilidad? — manifiesto (2026-10-05)

**Estado: PENDIENTE DE OK DE NICO (regla STOP: es información sobre precio futuro).** No se corrió nada.
NORTH_STAR: `docs/NORTH_STAR.md`, sha256 del cuerpo `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`.

## 1. Registro de familia
- **Familia:** AVCL-VOL-1, indicador aVolClusterPOI v0.5 (`nt8/aVolClusterPOI.cs`, kernel `avolclusterpoi_full.run_full`
  con paridad NT8 3.408/3.408 eventos en MNQ 12-26 50t). Independiente: no hereda resultados, costos ni presupuesto de
  multiplicidad de BigTrap2, HFTZones, GEX ni otras familias.
- **Parámetros congelados** (los del chart de Nico que produjo el oráculo, no elegidos por resultado): Window 10,
  Median ×2, Max Gap 1, Min Cluster 2, Session Relative Buckets ON, bucket 30 min, Lookback 20 sesiones,
  **Detection Percentile 95**, Min Samples 20, filtro predictivo OFF, top-K OFF. (Ciclo de vida irrelevante: el evento
  es la creación.)
- **Barra:** 50 tick (la validada por oráculo). 25t queda fuera hasta tener oráculo propio.

## 2. Espacio de eventos y estados (regla de población: enumerar antes de congelar)
| Familia de entrada | ¿Se mide? | Por qué |
|---|---|---|
| **Creación OFF_PRICE** (precio ya fuera del cluster) | **SÍ** | evento causal en la barra de cierre de bloque; dos lados (soporte/resistencia) |
| **Creación AT_PRICE** (precio dentro del cluster) | **SÍ** | es la "compresión con participación" de la hipótesis |
| Primer toque / toque n-ésimo | no (campaña posterior) | depende de la creación; medir antes si la creación informa |
| Invalidación / expiración | no | fin de vida, no anticipación |
| Confluencia / ráfaga (burst ≥ 3) | descriptivo dentro de la creación | estrato, no población propia |
| Estado continuo (distancia a la zona activa más cercana, nº de zonas activas) | no (registrado como alternativa) | más potencia, pero otra pregunta; se pre-registra aparte si la creación da señal |

## 3. Hipótesis
**Justificación económica.** Volumen concentrado en pocos precios dentro de 10 barras = transferencia de inventario
grande en un rango estrecho (absorción, acumulación/distribución). En microestructura, la llegada de información se ve
primero en volumen; la resolución de esa transferencia suele producir expansión de rango. AT_PRICE = compresión con
participación, candidato natural a expansión.

**H1 (no direccional, primaria).** Tras la creación, la volatilidad realizada de los H minutos siguientes, normalizada
por la de los H minutos previos, es mayor que en **bloques de control sin creación** emparejados.
**H2 (direccional, sólo si H1 pasa).** OFF_PRICE: la expansión se aleja de la zona más que la atraviesa. AT_PRICE: el
lado de salida depende del contexto declarado (cierre del bloque en el tercio alto/bajo del rango del bloque; régimen
de gamma del día previo, `gex_{t-1} < 0`).

**Cómo podría refutarse.** H1: la diferencia evento − control no supera el nulo (IC por sesión cruza 0) en ninguno de
los dos tipos, o desaparece dentro de estratos de volatilidad previa. H2: proporción "se aleja" ≈ 50 % (dentro del
nulo) o el contexto no separa los lados.

## 4. Medición
- **Unidad:** creación de zona (barra de cierre de bloque, causal). Ventana hacia adelante desde el **cierre** de esa
  barra (la zona no existe antes).
- **Horizontes (corregidos 2026-10-05 a pedido de Nico, con medición previa target-free de MNQ 12-26 50t,
  20→25-sep):** en RTH una barra de 50t dura 0,6 s de mediana (~100 barras/min); un bloque de 10 barras ≈ 6 s;
  rango mediano 22/52/75 ticks en 10/50/100 barras; ±12 ticks se recorren en ~4 s. Los 15/60 min originales
  (1.500-6.000 barras) estaban fuera de escala. **H ∈ {10, 50, 200} barras de 50t** (~6 s, ~30 s, ~2,5 min en RTH),
  reloj de eventos (barras), no de minutos. RTH y ETH se reportan por separado (ETH ~6× más lenta). Se descarta el
  evento si la ventana cruza el fin de sesión.
- **Métrica H1:** `log(RV_adelante / RV_atrás)` con ventanas de H barras a cada lado, RV = suma de retornos cuadrados
  barra a barra. Canal adicional: `log(rango_adelante / rango_atrás)`.
- **Control emparejado (lo central):** bloques cerrados **sin** CREATE (ABSTAIN_BELOW_THRESHOLD o NO_CLUSTER) del mismo
  contrato, misma franja de 30 min (± 1), mismo decil de volumen total del bloque y mismo decil de RV previa; se
  sortean hasta 5 controles por evento, sin reemplazo, sin solapamiento temporal con el evento. Mide si la
  **concentración** del volumen agrega algo sobre el volumen y la volatilidad ya presentes.
- **Estadístico:** media(evento) − media(control), por tipo (OFF, AT) y horizonte.
- **Nulo:** permutación de la etiqueta evento/control **dentro de cada estrato** (contrato × franja × decil vol × decil
  RV), 20.000 sorteos, semilla 20261005. Inferencia agrupada por sesión (bootstrap de sesiones para el IC).

## 5. Datos y alcance
- MNQ, serie líder por sesión vía `edgelab_data` (sólo sesiones aprobadas), 2025-07-01 → 2026-09-30. Cada contrato se
  calcula continuo con su propia calibración (Do not merge), footprint con la regla NT8 de subserie 1-tick.
- **Holdout desde la sesión del 2026-10-01: no se toca.**
- N esperado: ~25-35 creaciones por sesión × ~250 sesiones ≈ 6.000-9.000 eventos (OFF+AT). MDE se publica antes de
  mirar diferencias.

## 6. Multiplicidad
Etapa 1 (H1): 2 tipos × 3 horizontes × 2 canales (RV, rango) = **12 pruebas**, Holm sobre 12 (RTH; ETH descriptivo).
Etapa 2 (H2, sólo si alguna H1 pasa para ese tipo): OFF 3 horizontes + AT 2 contextos × 3 horizontes = hasta **9**,
Holm sobre las que se habiliten. Todo se registra en `TRIAL_REGISTRY_GLOBAL.jsonl`.

## 7. Riesgos declarados
- Agrupamiento de volatilidad (confusor principal) → control emparejado por decil de RV previa y franja.
- Eventos solapados (ráfagas de zonas) → inferencia por sesión; reporte aparte de eventos con burst ≥ 3.
- Rolls: las sesiones de roll pueden tener volumen atípico → estrato por contrato; se informa sin ellas también.
- 50t ≠ lo que Nico mira en 25t: el resultado vale para 50t.
- Nota: el test de reacción del propio indicador (target 12t / stop 8t / 50 barras) se resuelve en ~4 s en RTH; su
  "aciertos 44 %" mide sobre todo ruido de microestructura. No se usa como evidencia.

## 8. Qué NO hace
No define entradas, salidas ni P&L. Si H1 pasa, el siguiente paso (régimen de volatilidad para dimensionar o filtrar
estrategias, o P&L bruto de una regla única) va en otro manifiesto con otro OK.

## Nota de implementación (antes de la corrida completa, 2026-10-05)
- Controles: además de no solaparse con su evento, se exige que estén a **más de 2H barras de cualquier creación**,
  para que un control no contenga el efecto de otra zona (más conservador; a H=200 reduce controles).
- Prueba de humo de software sobre 5 sesiones (2026-09-21→25, 50 permutaciones) para verificar la cadena; esas cifras
  no se usan ni se interpretan. La corrida formal es en Kaggle con 20.000 permutaciones sobre todo el rango.
