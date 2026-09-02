# aVolClusterPOI — export diagnóstico por bloque en NT8 (instrucciones)

**Estado: parche escrito y verificado sintácticamente (balance de llaves/paréntesis
contra el original, no compilado — no tengo NinjaTrader acá). Falta que Nico lo
compile y lo corra.** Cambio 100% aditivo a `nt8/aVolClusterPOI.cs`: dos
propiedades nuevas (`DiagBlockExportEnabled`, `DiagBlockExportPath`), ambas
`false`/`""` por defecto — con los defaults, el indicador se comporta exactamente
igual que antes. No toca `blockCells`, la mediana, el clustering, el umbral
histórico ni `CreateZone` — sólo lee esas variables después de calculadas y las
vuelca a un CSV separado.

## Qué exporta

Un renglón por **cada bloque procesado**, `CREATE` o `ABSTAIN` (a diferencia del
`EventLogPath` existente, que sólo exporta zonas creadas):

```
diag_seq,bar_index,bar_close_time,session_index,bucket,
n_cells,median,hot_threshold,best_score,threshold,hist_samples,decision,
selected_lower_tick,selected_upper_tick,selected_score,selected_count,
n_clusters,clusters,cells
```

- `decision` ∈ `CREATE`, `ABSTAIN_FEW_CELLS` (<3 celdas), `ABSTAIN_NO_CLUSTER`
  (ningún cluster de tamaño ≥`MinClusterTicks`), `ABSTAIN_NO_HISTORY` (bucket
  sin `MinSamplesPerBucket` muestras), `ABSTAIN_BELOW_THRESHOLD` (hubo
  clusters pero ninguno superó el umbral histórico),
  `ABSTAIN_DISTANCE_OR_QUALITY_FILTER` / `ABSTAIN_AT_PRICE_FILTERED` (sólo
  aplican si `EnablePredictiveFilter=true`, que en la corrida del oráculo
  existente está en `false` — en ese caso este código nunca se alcanza).
- `clusters`: **todos** los clusters candidatos (no sólo el elegido), formato
  `lower:upper:score:count` separados por `|`.
- `cells`: **todas** las celdas del bloque (`blockCells` crudo), formato
  `tick:vol` separados por `|`, ordenadas por tick ascendente.

## Cómo correrlo (mismos parámetros que el oráculo ya commiteado)

Sobre el mismo chart NQ JUN26 / CME US Index Futures ETH / 120t que generó
`data/nt8_oracles/avolcluster_v05_NQ0626_120t_20260407_20260612.csv`, agregar
el indicador de nuevo (o editar la instancia existente) con:

- `DiagBlockExportEnabled = true`
- `DiagBlockExportPath = <ruta nueva>` -- **el CSV se sobreescribe siempre**,
  usar un nombre de archivo distinto al del oráculo existente.
- Todos los demás parámetros **idénticos** a los ya usados (`WindowBars=10,
  MedianMultiplier=2, MaxGapTicks=1, MinClusterTicks=2, TimeBucketMinutes=30,
  DetectionPercentile=98, LookbackSessions=20, MinSamplesPerBucket=20`) --
  la primera línea `# meta,...` del CSV nuevo los vuelve a declarar, verificar
  que coincidan con la primera línea del oráculo viejo antes de comparar nada.
- Ventana de fechas: **la misma pre-holdout ya usada** (2026-04-07..06-12).
  No corresponde tocar el holdout para esto -- es validación target-free de
  geometría/detección, no de outcomes.

`EventLogPath` puede dejarse como estaba (o vacío) -- es independiente de
`DiagBlockExportPath`, no hace falta correr ambos exports a la vez, aunque no
hay conflicto si se corren juntos.

## Tamaño esperado

El trace dump Python de la misma ventana tuvo 28.477 bloques totales, con un
promedio de ~35-70 celdas por bloque cuando hay volumen (bloques de sesión con
poca actividad tienen menos). Un CSV con **todos** los bloques (no sólo los
414 que crearon zona) va a pesar más que el trace dump de Python (que sólo
volcó los 414 bloques de creación, 856 KB) -- estimo, sin dato real de NT8
para confirmarlo, un orden de magnitud de **decenas de MB**, no cientos.
No es una promesa: si al correrlo el archivo resulta demasiado grande para
manejar cómodo, se puede acotar después con un segundo parámetro de rango de
barras (`CurrentBar` mín/máx) -- no lo agregué ahora para no adivinar un
límite sin haber visto el tamaño real primero.

## Qué hacer con el CSV después

No hace falta que el `.cs` filtre por caso -- exporta todo y el cruce con los
casos de interés se hace del lado Python, contra datos ya commiteados:

- Los 19 `GEOMETRY_DIFF`: cruzar por `nt8_id` contra
  `data/nt8_oracles/avolcluster_v05_NQ0626_120t_20260407_20260612.csv`
  (columna `zone_id`) para obtener `bar_index`/`bar_close_time`, y buscar esa
  fila en el CSV diagnóstico nuevo.
- Los 4 outliers `ratio>1.30` (`py_id` 98, 201, 142, 237): sus bloques del
  lado Python ya están en
  `docs/research/avolclusterpoi_nq0626_evidencia_extractos_20260901/02_missing_in_nt8_57.json`
  (`session_end_ns`, `bucket`) -- cruzar por fecha/bucket aproximado, no hay
  `bar_index` NT8 exacto para un bloque que Python creó y NT8 no, así que este
  cruce va a ser por cercanía temporal, no por id exacto.
- `py_id=372` / `nt8_id=413`: buscar `zone_id=413` en el oráculo existente
  (`event_seq=930`, `bar_close_time=2026-06-03T17:01:10.376`) y esa misma
  hora/bucket en el CSV diagnóstico nuevo -- ahí está el `blockCells` real de
  NT8 para comparar celda por celda contra
  `docs/research/avolclusterpoi_nq0626_evidencia_extractos_20260901/03_py_id_372_block_cells.json`.

## Lo que este parche NO hace

- No cambia el comportamiento del indicador cuando `DiagBlockExportEnabled=false`
  (default) -- cero riesgo para cualquier uso existente del indicador.
- No decide tolerancias ni reclasifica el gate -- sólo genera el insumo que
  falta (`blockCells` real de NT8) para que la tarea 3/embudo 0 se resuelva
  con evidencia y no con inferencia vía `density`.
- No toca outcomes, P&L, ni el holdout.
