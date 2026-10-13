# A/E contra componentes continuos — resultados de desarrollo

**COMPLETE y agregados reconciliados**: kernel138420049/v4 privadoCPU, sourceec12e3344e71fdd11311c711c84643faac4c26ea. Diez de doce fechas preseleccionadas disponibles; June18 y July2 no tienen ticks en sus rangos exactos. Sin reemplazos. Esto confirma la causa de rango vacío June18 que bloqueaba el helper estricto. v1/v2/v3 siguen fallidos; v4 NO es éxito retrospectivo del protocolo estricto12, sino de la enmienda publicada antes del envío.

## Respuesta

Componentes continuos reducen Brier 7.12% frente al prior, con mejor pérdida en10/10 sesiones. A/E juntos NO agregan mejora media: delta+0.000109566; mejoran sólo2/10 fechas vs componentes y4/10 vs control de capacidad. Diferencia pequeña, no inferencia ni edge.

| Predictor | Brier medio por sesión (menor mejor) |
|---|---|
| Frecuencias históricas | 0.647601 |
| Componentes continuos | 0.601465 |
| Componentes + capacidad | 0.601557 |
| Componentes + A | 0.601594 |
| Componentes + E | 0.601447 |
| Componentes + A/E | 0.601574 |

E sola: delta-0.000017446, mejora5/10 fechas, casi empate y sin estabilidad suficiente para recomendarla como filtro o edge. A empeora la media. Brier es pérdida probabilística3 clases[0,2], no P&L, acierto de trading ni performance neta.

## Soporte, heterogeneidad y límites

70,544 anclas utilizables comunes sobre120,148 anclas de evaluación, NO70,544 observaciones independientes. A_ONLY296, E_ONLY2926, BOTH16, NEITHER67306. Sólo dos sesiones de ajuste, ya inspeccionadas. No búsqueda lambda/configuración ganadora ni refit en evaluación. A/E usa exactamente calibraciónJune12 agregada original.

Chequeos dentro de cada estado y fase/dirección por media ponderada de anclas: AE empeora en los cuatro estados y en las cuatro celdasfase×dirección; estas medias NO son el headline equiponderado por sesión. En A_ONLY el deltaAEvscomponentes es+0.0204008; en BOTH+0.0513321 con sólo16anclas. E_ONLY+0.0001894. No confundir soporte escaso con ausencia del fenómeno ni pérdidas predictivas con mecanismo causal.

Gates quote/sign80%, gap2s, contexto60s, firstpassage midpoint60s con barrera causal; censura explícita y comparación sólo de eventos utilizables comunes. No corrección de selección/censura, inferencia, holdout, P&L, fills, mecanismos físicos ni autocanonización. No se han extraído ticks/filas/predicciones fuera de Kaggle.

## Ejecución eficiente

22,538,237ticks totales (ajuste+evaluación),53.367s runner y62.355s host incluyendo7.010s de transporte, sin tiempo de cola. Seis predictores reutilizan una sola lectura/primitivas/labels por sesión. No producto cartesiano de indicadores. La duración de esta prueba NO estima la campaña gigante de confluencias.

## Aprendizaje y próximo paso útil

La representación continua de presión/actividad/progreso/contexto aporta en este baseline; etiquetas A/E deterministas no añaden información y no dieron mejora representacional. Mantenerlas como descriptivos científicos, no gate operacional validado. Siguiente protocolo propuesto: probar componentes continuos y contexto causal con geometría/orden/llegada AVZP2/racimo, baseline de densidad/ocupación/selección igualado y unión geométrica bounded. No multiplicar umbrales A/E por este resultado ni reabrir campañas saturadas como evidencia nueva. Necesaria réplica temporal/contrato independiente antes de generalizar.

## Reproducción agregada

Los scripts sólo necesitan los JSON agregados boot/model, el package receiptV4 y el planAVAILABLE. `review_phenomena_models.py` exige --package-receipt explícito; `interpret_phenomena_models.py` genera la misma evidencia/CSV/spec byte-idénticos. Reconciliación por fase reconstruye independientemente cada score y la media de sesión. PASS_AGGREGATE_RECONCILIATION no es recuento independiente de ticks.

```bash
python -m tools.research_ops.audits.review_phenomena_models --raw-dir <aggregate_dir> --out review.json --package-receipt docs/research/ops/MNQ_PHENOMENA_MODEL_V4_PACKAGE_RECEIPT.json
python -m tools.research_ops.audits.interpret_phenomena_models --raw-dir <aggregate_dir> --out-dir <analysis_dir> --package-receipt docs/research/ops/MNQ_PHENOMENA_MODEL_V4_PACKAGE_RECEIPT.json
```

831 tests antes de instrumentación más2 de disponibilidad:833ResearchOps/18navegación antes de envío,21focales finalesPASS y CLI byte-reproPASS. Brain científico: propuesta revisada en repo, NO writer canónico autenticado. Debian/autopilot no desplegado ni modificado por esta corrida.
