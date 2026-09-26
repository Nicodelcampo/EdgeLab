# Auditoría del censo residual aVolClusterPOI NQ 06-26 — 2026-09-01

**Estado vigente: `FAIL`; censo completo todavía pendiente.** Los archivos
históricos `censo_76_residuos.*` de `27a583a` conservan la primera entrega,
pero no acreditan por sí solos cero ambigüedad ni explican todo el gate.

## Alcance real

El gate original contiene:

- 19 `GEOMETRY_DIFF`;
- 57 `MISSING_IN_NT8`;
- 48 `MISSING_IN_PYTHON`;
- 124 filas residuales.

El builder corregido preserva las 124 filas y reporta explícitamente
`NOT_YET_AVAILABLE` cuando falta el trace Python de todos los bloques. No llama
“completo” a un censo limitado a 19+57.

## Hallazgo mecánico: dos pares partidos por el matcher

La evidencia ya versionada permite enlazar:

| Python | NT8 | diferencia geométrica | techo de candidatura | resultado |
|---:|---:|---:|---:|---|
| 201 | 143 | 9 ticks completos | 8 | rechazado antes de clasificar |
| 237 | 210 | 13 ticks completos | 8 | rechazado antes de clasificar |

`match_zones` descarta candidatos con `gd > max(tol_geom_ticks, 8)`. Por eso
cada evento aparece dos veces en el gate: una fila `MISSING_IN_NT8` y otra
`MISSING_IN_PYTHON`. Son dos eventos detectados por ambos sistemas, no cuatro
eventos independientes. Las 124 filas corresponden actualmente a 122 grupos
de eventos tras esos enlaces.

Esto no autoriza a elevar el techo de 8 ticks: explica el matcher, no decide
qué geometría es aceptable.

## Correcciones del builder

- rutas relativas al repositorio;
- índice `timestamp -> lista`, sin sobrescritura silenciosa;
- clave compuesta `(bar_close_time, bar_index)` para filas con identidad NT8;
- `TIME_MATCH_AMBIGUOUS` si un lookup sólo temporal tiene más de un candidato;
- conteo publicado de timestamps duplicados;
- `CELL_LEVEL_SET_DIFF` por defecto;
- `EDGE_LEVEL_SET_DIFF` sólo cuando los niveles exclusivos forman tramos
  contiguos pegados al borde del hull compartido;
- `best_candidate_score` NT8 recuperado del campo `clusters`, no del antiguo
  `best_score` mal rotulado;
- replay del clustering sobre `blockCells` NT8 y comparación de mediana,
  threshold, clusters, decisión y geometría seleccionada;
- dimensiones separadas para input, replay algorítmico y rechazo del matcher.

## Historia

`ABSTAIN_NO_HISTORY` identifica la decisión inmediata de NT8, pero no resuelve
la causa raíz. En los 12 casos Python tenía entre 27 y 121 muestras; NT8 tenía
menos de 20. El CSV vigente registra cero cuando no alcanza el mínimo, por lo
que no conoce el conteo NT8 exacto. Sigue abierto como `HISTORY_STATE_DIFF`.

## Trace autorizado

El commit `eafbc0380253e029acc969e07c17ebb7912ef7ec` agrega el esquema Python
completo y conserva las claves públicas previas. El launcher
`notebooks/kaggle/avolclusterpoi_tracedump_full_runner.py` está fijado a ese
SHA y exporta los 28.477 bloques esperados, incluyendo `CREATE` y `ABSTAIN`.
No calcula outcomes ni P&L.

Al recibir `all_blocks.json`, ejecutar:

```bash
python docs/research/avolclusterpoi_nq0626_censo_76_20260901/build_censo.py \
  --py-all-blocks /ruta/al/all_blocks.json
```

Salidas: `censo_124_residuos.json` y `censo_124_residuos.csv`.

## Restricción

No se propone tolerancia y no se reclasifica el gate hasta completar los 46
`MISSING_IN_PYTHON` todavía no enlazados, reconciliar 28.477 bloques Python
contra 22.508 bloques NT8 y cerrar el estado histórico.

**Aporte al referente:** convierte un censo parcial con afirmaciones demasiado
fuertes en un procedimiento reproducible que conserva todos los residuos,
distingue pares partidos de eventos realmente unilaterales y falla cerrado
ante ambigüedad temporal.
