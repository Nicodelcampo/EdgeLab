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

## Candidatas vigentes con la vara «por mes» (desarrollo 2018-01 → 2025-07, R neto; agregado 2026-11-19)
| Serie | Ops/mes | R/op | R/mes | t mensual | % meses + | Peor mes (R) |
|---|---|---|---|---|---|---|
| T (NQ) | 19,1 | +0,119 | +2,27 | 4,67 | 64 % | −5,6 |
| R AtrPhase (NQ, stop 0,25 × ATR20) | 3,0 | +0,380 | +1,14 | 3,57 | 60 % | −4,3 |
| Z-banda (NQ, promedio de 9) | 2,4 días | +0,281 | +0,68 | 3,72 | 58 % | −3,2 |
| SOM (NQ) | 14,9 | +0,044 | +0,65 | 1,73 | 43 % | −6,4 |
| SOM (NQ) con fricción ≤ 0,08 | 14,8 | +0,044 | +0,65 | 1,74 | 43 % | −6,4 |
| Franklin (NQ+ES) | 12,8 | +0,051 | +0,65 | 1,19 | 40 % | −11,1 |
| Franklin sólo días de ATR alto | 4,8 | +0,051 | +0,24 | 0,69 | 23 % | −9,9 |
| Canasta T+R | 22,1 | +0,155 | +3,41 | 5,55 | 68 % | −8,2 |
| Canasta T+R+Z-banda | 24,5 | +0,167 | +4,09 | 6,30 | 71 % | −8,2 |
| T+R+Z-banda+Franklin ATR alto | 29,3 | +0,148 | +4,34 | 5,69 | 71 % | −8,9 |

## En LucidFlex 25K (2020-01 → 2025-07, 1 MNQ por regla con USD 100 de riesgo, media contraída a la mitad, DLL $600, consistencia 50 %, retiro máximo, 8.000 cuentas)
| Canasta | % días con operación | USD/día (sd) | t | Pasa | Cobra | EV/cuenta | EV/mes | Días por cuenta | EV sin ventaja |
|---|---|---|---|---|---|---|---|---|---|
| T | 88 % | 22 (177) | 4,83 | 50 % | 19 % | +416 | +112 | 78 | +49 |
| R | 13 % | 9 (87) | 3,89 | 51 % | 16 % | +144 | +12 | 254 | −22 |
| Z-banda | 11 % | 5 (55) | 3,26 | 29 % | 2 % | −36 | −3 | 280 | −53 |
| SOM | 90 % | 15 (298) | 1,92 | 34 % | 10 % | +148 | +88 | 35 | +63 |
| Franklin | 41 % | 11 (179) | 2,30 | 35 % | 10 % | +161 | +34 | 101 | +18 |
| T+R | 89 % | 31 (218) | 5,46 | 47 % | 19 % | +441 | +144 | 64 | +41 |
| **T+R+Z-banda** | 90 % | 36 (224) | **6,11** | 49 % | 21 % | **+489** | +167 | 61 | +38 |
| T+R+Z-banda+SOM | 98 % | 51 (407) | 4,76 | 36 % | 12 % | +252 | **+184** | 29 | +37 |
| T+R+Z-banda+Franklin | 92 % | 47 (343) | 5,19 | 37 % | 13 % | +290 | +162 | 38 | +20 |
| T+R+Z-banda+SOM+Franklin | 98 % | 62 (528) | 4,46 | 31 % | 10 % | +193 | +163 | 25 | +17 |
- EV/mes es por cuenta en ciclo (compra, evaluación, fondeo, retiros): las canastas con SOM ganan más por mes porque las cuentas se resuelven
  más rápido (29 días contra 61), pero pasan menos (36 % contra 49 %) y dejan menos por cuenta. Datos en `FRECUENCIA_PROP_LUCID.json`.

Episodios: no aplica (tablas descriptivas por serie; cada regla tiene su descomposición en su acta).
