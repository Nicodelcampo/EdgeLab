# Manifiesto ES-ESCALONADAS: ¿la zona escalonada detectada en tiempo real tiene excursión neta? — PRE-REGISTRO (2026-09-30)

**North Star:** `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8` · Snapshot de detectores: auditor
`d31fbd8` (`ES_ESCALONADAS_SNAPSHOT_PRECONGELAMIENTO_20260929.json`) · Código de detección: `tools/escalonadas_det.py`.
**Estado:** PRE-REGISTRO. Se corre sólo con OK de Nico. Pedido: «probar todas las variantes posibles, rigurosos; si no hay
efecto, luego filtro por tendencia» (el filtro de tendencia será un pre-registro aparte, después de éste).

## Hipótesis, justificación y refutación
- **H:** tras detectarse en tiempo real una escalera de ≥ 3 picos que no se superan (techos que no suben / pisos que no
  bajan), una entrada en la dirección de la escalera gana más que la misma operación en momentos al azar emparejados.
- **Justificación económica:** absorción pasiva escalonada que cede de un lado; agotada la contraparte, la salida sigue
  la pendiente sin volver a los picos.
- **Refutación:** ninguna celda supera al control tras max-T, o el R neto con costos ES es ≤ 0.

## Población (event-space enumerado)
Candidatos considerados: creación/confirmación de la zona [elegido], 2.º pico con entrada anticipada [descartado: 85–95 %
de esas entradas no forman zona, se mide sólo como secundaria descriptiva], toque posterior del nivel [no], estado
continuo [no: la hipótesis es de evento]. Evento = la **detección en tiempo real** de cada zona.

## Datos
- ES 03-26, ticks NT8 `nt8_research_v2/ES_parquet/ES_03-26_ticks.parquet` (sha `948067cf…`), con bid/ask.
- **Descubrimiento:** feb-2026 (22 sesiones; el mes en que se ajustaron los detectores con los juicios de Nico).
- **Réplica (una vez, sólo celdas que sobrevivan):** mar-2026 hasta el roll, mismo contrato, nunca mirado.
- Holdout desde la sesión del 1-oct-2026 intacto; abr–sep no se tocan.

## Variantes (celdas) — número efectivo de hipótesis = 32
- Familia: **planas** / **empinadas** (parámetros del snapshot, sin cambios).
- Confirmación: **por velas** (pivote 2 velas; entrada a mercado en el primer tick tras el cierre de la vela de detección)
  / **por precio** (orden stop al nivel pico ∓ 2 ticks; llenado en el primer tick que opera en/through el nivel, al bid
  para ventas y al ask para compras).
- Objetivo: **4, 8, 12, 16 ticks** desde el precio de llenado.
- Stop: **último pico conocido al detectar + 1 y + 2 ticks** (lado contrario), llenado tick a tick al peor lado.
- 2 × 2 × 4 × 2 = **32 celdas**. Horizonte: 150 velas 25t o fin de sesión (liquidación al último tick).
- Una operación a la vez por familia y dirección (no se superponen entradas de la misma serie).

## Métrica y referencia
- Primaria por celda: **R neto** por operación = (resultado en ticks − costos) / riesgo en ticks.
  Costos ES: comisión US$ 2,50 por lado (0,40 ticks ida y vuelta) + deslizamiento observado en el replay (ya incluido
  en el llenado bid/ask). No se transportan costos de otro instrumento.
- **Control empírico emparejado:** 3 entradas por evento en velas al azar de OTRAS sesiones del mismo mes, misma franja
  ±30 min, mismo tercil de volatilidad previa (RMS de cambios firmados, 20 velas), misma dirección y misma geometría
  (distancia de stop y objetivo en ticks), mismo replay tick a tick. Diferencia pareada evento − control.
- Inferencia: bootstrap por sesión con pesos comunes a todas las celdas, **max-T sobre las 32**; celda evaluable con
  ≥ 30 operaciones y ≥ 8 sesiones. Se publica MDE, n, sesiones y el landscape completo.
- Dos canales: direccional (R) y no direccional (llega a ±objetivo antes que al stop simétrico) + MFE/MAE completos.

## Secundarias (descriptivas, no deciden)
Entrada anticipada con 2 picos en el nivel (todas las entradas, no sólo las que forman zona); resultado bruto sin costos;
por hora del día.

## Riesgos
- Febrero es el mes de ajuste de los detectores con juicios de Nico mirando el gráfico completo: el descubrimiento está
  contaminado por selección visual → sólo la réplica en marzo puede confirmar.
- Stops de 3–4 ticks contra costos de ~0,4 ticks + deslizamiento: el neto puede ser muy distinto del bruto.
- ~100 zonas/día en planas: muchas operaciones solapadas en el tiempo; el bootstrap por sesión cubre la dependencia.
- Orden intravela resuelto por ticks; la fila de cola en órdenes límite no aplica (entradas stop/mercado).
