# Frecuencia de operaciones en prop firms: el criterio es el resultado por mes (directiva y datos, 2026-11-19)

Estado: VIGENTE — directiva de Nico y datos descriptivos sobre operaciones ya medidas (no cuenta pruebas, no elige variantes).
North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.

**Directiva (Nico):** «tratemos de que la cantidad de operaciones no sea baja, siempre y cuando el resultado sea mejor con muchas operaciones. No
conviene que opere poco en las prop. Pero si que opere poco es la única manera, está bien.»

**Cómo se aplica:** las variantes y las reglas se comparan por **R neto por mes** y su **consistencia** (t de la serie mensual, % de meses
positivos), no por R por operación. Ante resultados por mes iguales o mejores, gana la más frecuente. La elección sigue las reglas de selección
(versión nueva pre-registrada; nunca la mejor sobre datos ya mirados).

## Datos de referencia (NQ, 2018-01 → 2026-09, stop 0,25 × ATR20, medianas por cuartil de frecuencia)
| R (AtrPhase), 81 variantes | Ops/mes | R/op | R/mes | t mensual | % meses + |
|---|---|---|---|---|---|
| pocas | 0,86 | +0,392 | +0,419 | 2,39 | 32 % |
| medio-bajo | 2,06 | +0,414 | +0,857 | 3,57 | 51 % |
| medio-alto | 3,58 | +0,344 | +1,160 | 3,91 | 60 % |
| muchas | 5,44 | +0,222 | +1,166 | 3,45 | 62 % |
| fábrica | 2,93 | +0,419 | +1,230 | 4,23 | 63 % |
Spearman (ops/mes, ·): R/op −0,51; R/mes +0,80; t +0,45.

| Z, 27 variantes | Ops/mes | R/op | R/mes | t mensual | % meses + |
|---|---|---|---|---|---|
| pocas | 0,23 | +0,068 | +0,016 | 0,61 | 9 % |
| medio-bajo | 2,01 | +0,284 | +0,576 | 3,36 | 56 % |
| medio-alto | 2,31 | +0,267 | +0,611 | 3,54 | 58 % |
| muchas | 4,21 | +0,047 | +0,226 | 0,89 | 50 % |
| fábrica | 2,21 | +0,289 | +0,637 | 3,65 | 58 % |
Spearman (ops/mes, ·): R/op −0,30; R/mes +0,33; t +0,24.

Episodios: no aplica (tabla por cuartiles de frecuencia sobre todo el período; la descomposición por meses de cada variante está en los actas
de Z-PICO y NETO-PISTAS).
