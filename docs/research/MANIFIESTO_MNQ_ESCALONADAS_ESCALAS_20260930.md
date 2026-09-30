# Manifiesto MNQ-ESCALONADAS-ESCALAS: grilla escala × SL × TP × BE — PRE-REGISTRO (2026-09-30)

**North Star:** `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8` · OK de Nico: «hagamos el análisis
propuesto anteriormente» (30/09): grilla con descubrimiento **ene-2026** y réplica única **mar-2026** (sin los 11 meses,
para no gastar horas de cómputo).
**Antecedente:** exploración visual en feb-2026 (`HFT_ZONAS_ES_MEDIDO…`, anexo 30/09): 150t neto +0,25 R/op con un caso
elegido mirando. Febrero queda FUERA (ya mirado).

## Hipótesis y refutación
- **H:** la escalera plana detectada en tiempo real (confirmación por precio) en MNQ, operada en su dirección con orden
  stop, gana neto más que la misma mecánica al azar; y la ventaja neta depende de la escala (costo fijo diluido).
- **Justificación:** absorción escalonada que cede; con velas más grandes el costo fijo (~4 ticks) pesa menos por R.
- **Refutación:** ninguna celda supera al control tras max-T, o R neto ≤ 0 en las que lo superen.

## Detectores (congelados, sin marcas de MNQ)
Familia PLANAS del snapshot `d31fbd8` transferida a MNQ escalando todo lo que está en ticks por el rango medio de vela
medido en feb-2026: 25t ×4,5; 150t ×12,42; 500t ×23,49 (`tools/escalonadas_det.py --escala`). Velas 150t/500t = 6/20 velas
25t dentro de cada sesión (`tools/agregar_velas.py`). EMPINADAS no se prueba (casi inexistente a 150t/500t).

## Celdas — número efectivo de hipótesis = 108
- Escala: 25t / 150t / 500t.
- SL en ticks = múltiplo del «SL base» de la escala (5 / 14 / 26, el caso visual escalado): ×1, ×2, ×4.
- TP: 1, 2, 3, 5, 10 R. BE: ninguno / 1R / 2R, sólo si TP > BE.
- Por escala 3 × (1 + 2 + 3 + 3 + 3) = 36 → **108**. max-T sobre las 108.

## Mecánica, costos y control
- Entrada: orden stop al nivel de disparo (`det_precio`) dentro de la vela de detección, llenado al bid/ask del primer
  tick que lo opera. SL/BE stop al peor lado; TP límite con 1 tick de penetración; horizonte 1.500 velas o fin de sesión.
  **Comisión + fees 3 ticks ida y vuelta.** Ticks NT8 `nt8_research_v2/MNQ_parquet/MNQ_03-26_ticks.parquet`.
- **Control con la misma mecánica:** 3 por evento, velas al azar de otras sesiones del mes, misma escala, franja ±30 min
  y tercil de volatilidad; orden stop a la misma distancia (apertura de la vela de detección → nivel de disparo) desde la
  apertura de la vela siguiente a la elegida, en la misma dirección, con el mismo SL/TP/BE en ticks; si no se llena en
  20 velas se re-sortea (máx. 30 intentos).
- Bootstrap por sesión con pesos comunes, max-T sobre 108; celda evaluable con ≥ 30 operaciones y ≥ 8 sesiones; MDE.
- Réplica en marzo sólo de celdas que sobrevivan en enero **y** tengan R neto > 0.

## Riesgos
Enero con 21 sesiones: 500t tendrá ~50 zonas (probable «inconclusa»); SL base elegido mirando febrero (sólo escala la
grilla, no la decide); transferencia ES→MNQ sin marcas propias; tres escalas del mismo detector están correlacionadas.
