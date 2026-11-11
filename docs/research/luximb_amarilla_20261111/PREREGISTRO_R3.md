# LUXIMB-AMARILLA-R3 — stops más cortos (pre-registro, 2026-11-11)

Estado: VIGENTE. Etapa EF2 (exploratorio). Familia LUXIMB_AMARILLA (mismo linaje). North Star sha256 16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345.

- Regla: la de R2 `ctrl|W2|{amarilla,sin_filtro}|e2|DESPUES`, entrada en contra, filtros VWAP comunes. Stops: extremo (referencia),
  borde externo + 0,1·H_am, borde externo + 0,5·H_am, mitad borde–extremo. Objetivos 50 % y 75 %. 2 × 8 × filtros, DESC y REP, NQ y USATECH.
- Justificación económica: con el stop en el extremo de la excursión el riesgo es ≥ 1,5·H para ganar ≈ 0,25·H; si la falla de la
  extensión ya se confirmó al cruzar el borde interno, volver más allá del borde externo invalida la idea, y ahí debería ir el stop.
- Cómo podría refutarse: las variantes de stop corto no superan al stop en el extremo en R neto, o no superan el nulo de la búsqueda.
- Sin holdout (ya usado por la familia). Si una variante sirve, va a forward congelada.
