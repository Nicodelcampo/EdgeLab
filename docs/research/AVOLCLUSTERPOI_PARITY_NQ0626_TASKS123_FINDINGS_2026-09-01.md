# aVolClusterPOI parity NQ 06-26 — tareas 1-3 del auditor (2026-09-01)

**Estado: diagnóstico con evidencia directa (trace dump celda-por-celda +
comparación de multisets), gate sigue en `FAIL` (no reclasificado). Ningún
fix de código aplicado — ver conclusión de cada tarea sobre si corresponde.**

Insumos usados (Kaggle, ambos `COMPLETE`, descargados y verificados):
- `tickbar-setcmp-nq0626` (pin `eb40171c947a9b7273a56307309a48136cf58a56`) —
  comparación por multiset (`Counter`) de pares `(price_tick, vol_int)` entre
  el ledger `TickBarDiag` y el parquet real, en la ventana desplazada +3h.
- `avolclusterpoi-tracedump-nq0626` (pin `8bf9fd02861666ec3dc58928b2043223466d5ffe`) —
  `run(..., debug_trace=True)` sobre el parquet completo real de NQ JUN26
  (34.203.535 ticks, 285.063 barras, 28.477 bloques, 414 zonas), volcando
  `cells` (volumen por tick) de cada bloque que creó zona.

## Tarea 1 — ¿el desfase de ~3 ticks es reordenamiento o contenido real?

**No es reordenamiento disperso. Es un artefacto de borde de ventana, y
tampoco es contenido nuevo.**

Sobre la ventana `[w0, w1)` desplazada +3h (`ev[0]..ev[-1]` del ledger):
ledger 20.378 eventos, parquet 20.381 ticks. `Counter` sobre pares
`(price_tick, vol_int)`:

- `n_distinct_pairs_ledger = n_distinct_pairs_py = 851` — mismo conjunto de
  pares distintos en ambos lados.
- `sum_only_in_ledger = 0` — el ledger no tiene ningún par que el parquet no
  tenga.
- `sum_only_in_py = 3` — el parquet tiene 3 ocurrencias de más de pares que
  **también existen en el ledger** (no son pares nuevos: `(96831,100)` con 2
  de más, `(96832,100)` con 1 de más).
- Las 3 posiciones "extra" en el parquet son `[0, 1, 2]` — **las tres primeras
  del arreglo**, con el mismo timestamp exacto: `1775167201908000000`, que es
  el primer timestamp del rango (`w0`).

Conclusión: los 3 ticks de más son duplicados de contenido ya presente,
concentrados exactamente en el instante de apertura de la ventana. Es
consistente con una diferencia de fencepost en el corte inclusivo/exclusivo
del extremo `w0` entre cómo el ledger cuenta el primer instante y cómo
`load_canonical_parquet(..., start_utc_ns=w0)` lo hace, no con un
desordenamiento del stream ni con contenido que uno de los dos lados no vio.

**No corresponde reclasificar TICKBAR-001 a partir de esto** — sigue siendo
el defecto de borde de barra ya documentado; esto sólo descarta que el
`~3 ticks` que motivó esta tarea sea evidencia de desincronización de stream.
Si se quiere que el classifier de `tools/tickbar_diag_v2.py` deje de contar
este caso como `STREAM_MISMATCH`, el fix acotado sería tratar el extremo
inicial de la ventana como medio-abierto en vez de cerrado — cambio al
*script de diagnóstico*, no al kernel de producción. No se aplicó porque no
fue pedido explícitamente y es un cambio de semántica de una herramienta de
validación (se consulta antes de tocarla, por la misma regla que aplica a
gates).

## Tareas 2 y 3 — los 57 `MISSING_IN_NT8` y el outlier de 8 ticks (`py_id=372`/`nt8_id=413`)

### El algoritmo de clustering está verificado idéntico

`nt8/aVolClusterPOI.cs` líneas 344-371 vs
`edgelab/bridge/indicators/avolclusterpoi.py::cluster_hot_ticks` —
mismo umbral (`mediana superior x MedianMultiplier`), mismo gap entero
(`MaxGapTicks=1`), mismo mínimo de cluster (`MinClusterTicks=2`), mismo
criterio de mejor cluster (score máximo). No hay bug de traducción en la
lógica de agrupamiento — ya se había verificado esto para el borde de precio
en el rootcause anterior; ahora se verificó también para la selección del
cluster en sí.

### El outlier (`py_id=372`, bloque real, 66 celdas, no sintético)

Bloque real: `session_end_ns=1780520400000000000`, `bucket=44`,
`close_tick=122490`, `threshold=938.0` (histórico) — **coincide exacto con
el threshold NT8 reportado en el oráculo (938)**, así que `SessionProfile`
(historial de scores, cuantil empírico) está en paridad para este bloque.
La divergencia es interna a `cluster_hot_ticks`, no al historial.

- Python: mediana del bloque (66 celdas) = 6.0 → `hotThreshold=12.0`.
  Cluster resultante: ticks `122524..122549` (26 de ancho, 25 hot, score=1335).
- NT8 (oráculo CSV, evento `ZONE_CREATED` id=413): `lower=122524, upper=122541,
  score=1207, density=0.944444`. `density = clusterCount/width` con
  `width=upper-lower+1=18` da `clusterCount=17` exacto (`17/18=0.9444...`) —
  **NT8 excluye un tick dentro de 122524..122541** (hay un hueco de 1, permitido
  por `MaxGapTicks=1`), y **no extiende el cluster más allá de 122541**, mientras
  que en los datos de celda de Python **los 18 ticks de 122524 a 122541 superan
  el hotThreshold=12 sin huecos**, y el cluster sigue creciendo hasta 122549
  porque las celdas 122542..122549 (valores 17,16,17,24,12,15,18) también
  superan 12.

Con el `hotThreshold=12` de Python, nada de esto se explica por el gap-rule
en sí (que es idéntica) — se explica por el **valor del hotThreshold**: si
NT8 hubiera calculado un hotThreshold más alto (en el rango ~16-18 en vez de
12) sobre datos de celda ligeramente distintos, exactamente estos dos
síntomas aparecen juntos con una sola causa: (a) el hueco interno en
122524..122541 (un tick ahí, borderline, cae bajo un threshold más alto), y
(b) el corte en 122541 en vez de 122549 (las celdas 122542..122549, todas
≤24, quedan bajo un threshold ~16-18 pero sobre uno de 12).

La mediana de 66 celdas es el estadístico central de un bloque donde la
mayoría de las celdas tiene volumen bajo (colas de 1-9 en ambos extremos del
rango de precio) — es sensible a diferencias pequeñas de reconstrucción de
footprint ya documentadas como clase `FEATURE_DIFF` (256 casos, no bloqueante,
conocidas desde antes de esta tarea). Una diferencia de un puñado de unidades
de volumen en las celdas bajas, que en la suma total del bloque es
insignificante, puede desplazar la mediana lo suficiente para mover
`hotThreshold` y así el borde del cluster.

> **Actualización 2026-09-01 (posterior a esta entrega): confirmado con datos
> reales.** Se instrumentó `nt8/aVolClusterPOI.cs` con un modo diagnóstico
> aditivo que exporta `blockCells` reales por bloque, Nico lo compiló y
> corrió sobre la misma ventana. El bloque real de NT8 para este caso tiene
> **13 ticks completos ausentes** (122490-122504, suma de volumen=31) que el
> footprint de Python sí tiene, más 4 diffs de valor de ±1 a ±5 en ticks
> compartidos — eso explica exactamente el `clusterCount=17`/`width=18` y el
> corte en 122541 inferidos abajo vía `density`. Ver
> `AVOLCLUSTERPOI_NT8_DIAG_CONFIRMED_2026-09-01.md` para el detalle completo,
> incluidos dos casos adicionales (`nt8_id=9`, `nt8_id=27`) que confirman el
> mismo mecanismo con severidad proporcional a cuántos ticks se pierden en el
> borde. El párrafo original de abajo queda como registro de la inferencia
> previa, ya superada por el dato real.

**No se pudo confirmar con certeza total** porque el oráculo CSV no exporta
las celdas crudas de NT8 (`blockCells`) — sólo agregados por zona
(`score, threshold, density, cluster_share`). Lo que sí está confirmado con
datos reales, sin inferencia: el `clusterCount=17` sobre `width=18` (vía
`density`), el corte del cluster en 122541 (vía `upper` del oráculo), y que
la suma Python de 122524..122541 (1216) es cercana pero no igual al score
NT8 (1207) — diferencia de 9, del orden de magnitud de un ruido de
reconstrucción de footprint, no de un tick completo faltante.

~~**Conclusión de la tarea 3**: el outlier de 8 ticks no es un bug de
traducción del algoritmo de clustering (verificado idéntico línea por línea);
es sensibilidad del estadístico mediana a diferencias de footprint ya
conocidas y de otro modo insignificantes, amplificada porque el detector usa
esa mediana como umbral binario. Cerrar esto con certeza total requeriría
exportar `blockCells` desde el `.cs` para este bloque — no se hizo (cambio al
indicador de producción NT8, fuera del alcance de esta tarea de diagnóstico;
se consulta antes de tocar el `.cs`).~~ **Superado: ver la actualización de
arriba y `AVOLCLUSTERPOI_NT8_DIAG_CONFIRMED_2026-09-01.md`. La causa raíz sí
es una diferencia de footprint, pero no es ruido disperso genérico — es la
pérdida de ticks completos en el borde del bloque, del filtro `Low[0]/High[0]`
del `.cs`, con severidad variable según el bloque.**

### Los 57 `MISSING_IN_NT8` — patrón cuantificado, no anecdótico

Para cada uno de los 57, se cruzó `py_id` → bloque de creación real
(`best_score`, `threshold` del bloque) y se calculó `ratio = best_score /
threshold`:

```
n=57
min=1.001   mediana=1.053   max=1.748
ratio <= 1.05: 26/57 (46%)
ratio <= 1.10: 38/57 (67%)
ratio <= 1.15: 46/57 (81%)
ratio  > 1.30:  4/57 (ids 142, 201, 98, 237 -- ratios 1.327, 1.457, 1.538, 1.748)
```

El 81% de los `MISSING_IN_NT8` son creaciones **al borde del umbral de
detección en el lado Python** (score apenas por encima de su propio
threshold histórico). Esto es exactamente el modo de falla esperable de un
detector binario por umbral bajo cualquier ruido numérico cruzado entre
sistemas ya documentado (footprint/volumen, la misma clase que explica el
outlier de la tarea 3): si el score y el threshold de NT8 difieren de los de
Python por un margen pequeño -- inevitable dado que ya hay `FEATURE_DIFF` en
256 casos --, una creación con `ratio≈1.01-1.05` en Python cae fácilmente por
debajo de 1.0 del lado NT8 y no dispara zona ahí. No es evidencia de un
bug de traducción del kernel; es la firma esperada de sensibilidad de umbral.

Los 4 casos con `ratio>1.30` **no** encajan en ese mecanismo -- no están al
borde, Python los dispara con margen amplio. Se inspeccionaron
(`n_history_scores` de sus bloques: 68, 39, 27, 54) sin encontrar un patrón
único y confirmado (no todos están en el arranque de la serie ni comparten
bucket/sesión). **Quedan como hipótesis abierta, no resuelta**: podría ser
ruido de footprint más severo puntual, o un efecto de historial corto
(`lookback_sessions=20` aún no lleno en esa fecha) que hace más volátil el
cuantil histórico del lado que sea. No se afirma una causa aquí porque no
hay evidencia directa que la sostenga -- declarado explícitamente como no
cerrado, en vez de forzar una explicación.

## Tarea 4 — re-correr el gate

**No se re-corrió.** Las tareas 1-3 no identificaron ningún bug de código en
`avolclusterpoi.py` ni en `tools/paridad_oraculo.py` que amerite un fix antes
de re-correr -- el algoritmo de clustering y el borde de precio ya estaban
verificados idénticos al `.cs` antes de esta entrega, y esta entrega no
encontró una tercera divergencia de lógica, sino sensibilidad de umbral a
ruido de footprint ya conocido y ya clasificado (`FEATURE_DIFF`). Re-correr
el mismo código sobre los mismos datos daría el mismo resultado
(`FAIL`, mismos conteos) -- no hay razón para gastar el cómputo. Si se decide
tratar la sensibilidad de umbral como aceptable para esta familia (una
decisión de gate, no de código), eso se resuelve documentando una tolerancia,
no re-corriendo.

## Qué haría falta para cerrar esto con más certeza

1. Exportar `blockCells` crudo desde el `.cs` para bloques `GEOMETRY_DIFF`/
   `MISSING_IN_NT8` seleccionados -- confirmaría o refutaría directamente la
   hipótesis de sensibilidad de mediana de la tarea 3, en vez de inferirla
   de `density`.
2. Repetir la tarea 2 con un csv de oráculo que incluya `best_score` y
   `threshold` del lado NT8 para bloques que **no** crearon zona (hoy el
   oráculo sólo exporta eventos `ZONE_CREATED`/`AT_PRICE_CREATED` -- no hay
   forma de ver el score/threshold NT8 de un bloque que abstuvo, que es
   justo lo que se necesitaría para confirmar el mecanismo de umbral en los
   57 casos, no sólo inferirlo del lado Python).
