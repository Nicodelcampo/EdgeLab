# Canal 033 — recuperación del trabajo interrumpido de paridad aVolClusterPOI

**Fecha:** 2026-09-01

## Estado encontrado

Al tomar el relevo, la rama remota
`research/avolcluster-nq-parity-oracle-20260901` seguía en `27a583a`. Ninguno
de los cambios locales posteriores relatados por Claude había llegado al
remoto.

## Hallazgo de matching confirmado

- `py_id=201` ↔ `nt8_id=143`: diferencia geométrica de 9 ticks completos.
- `py_id=237` ↔ `nt8_id=210`: diferencia geométrica de 13 ticks completos.
- `edgelab/bridge/parity.py` sólo candidatea si
  `gd <= max(tol_geom_ticks, 8)`; con `tol_geom_ticks=0`, el techo es 8.
- Ambos pares son rechazados antes de la clasificación de diferencias.
- `nt8_id=143` y `nt8_id=210` ya figuraban entre los 48
  `MISSING_IN_PYTHON`.

Consecuencia: son dos eventos detectados por ambos sistemas, representados
como cuatro filas del gate. El gate conserva 124 filas residuales, pero tras
vincular esos pares hay 122 grupos de eventos. Esto explica el matcher; no
autoriza elevar su tolerancia.

## Recuperación publicada en la rama de research

1. `eafbc0380253e029acc969e07c17ebb7912ef7ec`
   - extiende el diagnóstico Python a todos los bloques;
   - conserva `best_score`, `threshold`, `zones` y `abstain`;
   - agrega mediana, hot threshold, historial real, clusters, decisión y
     cluster seleccionado;
   - agrega pruebas target-free.
2. `78f4e81f1b89ea07a6ce616599246e2c1eb714fe`
   - agrega `avolclusterpoi_tracedump_full_runner.py`;
   - el runner está fijado a `eafbc03`;
   - preflight: 34.203.535 ticks, 285.063 barras, 28.477 bloques y 414 zonas;
   - exporta `all_blocks.json`, zonas, resumen, hashes y ZIP;
   - no lee outcomes ni P&L.
3. `d999393feb11e32b73b6050f9036bf7630c7e0c0`
   - elimina rutas `C:/...`;
   - preserva las 124 filas del gate;
   - falla cerrado ante timestamps ambiguos;
   - usa clave compuesta `(bar_close_time, bar_index)` donde está disponible;
   - separa `CELL_LEVEL_SET_DIFF` de `EDGE_LEVEL_SET_DIFF` mediante predicado
     explícito de borde;
   - recupera `best_candidate_score` NT8 desde `clusters`;
   - ejecuta replay del clustering sobre las celdas NT8;
   - enlaza automáticamente los dos pares partidos;
   - marca los otros 46 `MISSING_IN_PYTHON` como `NOT_YET_AVAILABLE` hasta
     recibir el trace completo.
4. `f9fc958e51f24111c34a9330c8a0ee073b6dd89e`
   - reconstruye el conteo histórico NT8 exacto usando el CSV existente:
     scores por bucket, sólo sesiones completas anteriores y FIFO de 20;
   - valida la reconstrucción contra todas las filas donde el logger antiguo sí
     publicó un conteo no censurado.

## Decisión sobre el `.cs`

No se reprodujo la edición local no versionada de `aVolClusterPOI.cs`.
Modificar el detector congelado sólo para telemetría ya no es necesario para
este censo:

- el verdadero `bestScore` se recupera sin pérdida desde la columna
  `clusters` del CSV existente;
- el `hist_samples` censurado se reconstruye exactamente por
  `session_index + bucket + FIFO(20)`;
- se evita una nueva compilación/corrida NT8 y se preserva la identidad del
  oráculo que produjo los 22.508 bloques.

## Verificación local

- `py_compile`: verde para kernel, builder y reconstruidor histórico.
- cuatro aserciones del kernel: verdes.
- cuatro aserciones del builder: verdes, incluida falla cerrada para clave
  compuesta duplicada.
- aserción sintética de reconstrucción histórica: verde.
- El sandbox no tenía `pytest`; las funciones de prueba se ejecutaron
  directamente y pasaron. No se simula una suite completa.

## Pendiente único para completar el censo

Ejecutar en Kaggle el launcher versionado y entregar
`avolclusterpoi_tracedump_full.zip` o, como mínimo, `all_blocks.json` y
`sha256_manifest.json`. Después:

```bash
python docs/research/avolclusterpoi_nq0626_censo_76_20260901/build_censo.py \
  --py-all-blocks /ruta/al/all_blocks.json
```

Hasta entonces:

- gate = `FAIL`;
- no hay propuesta de tolerancia;
- no se abren embudos con outcomes ni P&L;
- los 46 eventos unilaterales restantes y la diferencia 28.477 vs 22.508
  siguen pendientes de clasificación empírica.

**Aporte al referente:** recupera de forma auditable el trabajo perdido,
reduce cuatro códigos huérfanos a dos pares partidos, evita alterar el detector
congelado cuando la evidencia existente permite reconstruir la telemetría y
deja un único artefacto computacional pendiente antes de decidir tolerancia.
