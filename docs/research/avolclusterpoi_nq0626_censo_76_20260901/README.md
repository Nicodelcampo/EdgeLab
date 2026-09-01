# Censo de los 76 residuos aVolClusterPOI NQ 06-26 — 2026-09-01

**Estado: censo completo, evidencia directa (`DIRECT`) en 76/76 casos, 0
`TIME_MATCH_AMBIGUOUS`. Cruce puro sobre artefactos ya generados — sin
correr el gate de nuevo, sin tocar outcomes.** Responde a la instrucción del
canal 030 (commit `4cfd27d`) de extender el hallazgo de 3 casos a los 19
`GEOMETRY_DIFF` + 57 `MISSING_IN_NT8` completos.

## Insumos y procedencia

- `data/nt8_oracles/avolcluster_v05_NQ0626_120t_DIAG_20260901.csv` — export
  diagnóstico real de NT8, blob git `276acc7e0fd7d0dc5ae8ea1fba0254457de8770c`,
  22.998.868 bytes (git `cat-file -s`, contenido LF canónico),
  sha256 `81f32a97a65a6eee801eb6639f613349f31a2c02354862c128126af1adabf9da`.
  **Corrección de procedencia**: el hash citado en el commit `58f57b9`
  (`f42e416b...`) era del archivo en disco con CRLF (`.gitattributes` normaliza
  `*.csv` a LF en el blob vía `text=auto`, pero lo tira CRLF al checkout en
  Windows) — mismo contenido, representación de fin de línea distinta. El
  hash de arriba es el reproducible desde `git cat-file`.
- `docs/research/avolclusterpoi_nq0626_reports_20260901/paridad_avolclusterpoi_nq0626.json`
  (sha256 `e654ace2...`, ya commiteado) — fuente de los 19 `GEOMETRY_DIFF` y
  57 `MISSING_IN_NT8`.
- `data/nt8_oracles/avolcluster_v05_NQ0626_120t_20260407_20260612.csv` —
  oráculo de zonas NT8 original, para `bar_close_time` exacto de cada `nt8_id`.
- Trace dump Python (`00_raw_zones.json`, `00_raw_creation_blocks.json`, ya
  commiteados en `avolclusterpoi_nq0626_evidencia_extractos_20260901/`).

Script: `build_censo.py` (en esta misma carpeta). Salidas:
`censo_76_residuos.json` (machine-readable, un objeto por caso, con las
celdas divergentes completas) y `censo_76_residuos.csv` (tabla plana para
lectura rápida).

## Método de emparejamiento

- `GEOMETRY_DIFF` (19 casos): `nt8_id` → `bar_close_time` exacto del oráculo
  de zonas → fila exacta en el CSV diagnóstico. Los 19 calzaron exacto
  (`time_delta_seconds=0`).
- `MISSING_IN_NT8` (57 casos): `py_id` → `created_ms` (UTC) del lado Python →
  se resta 3h (offset chart→UTC confirmado en la entrega anterior) → se busca
  esa marca exacta en el CSV diagnóstico; si no hay match exacto se busca el
  bloque más cercano y se marca `TIME_MATCH_AMBIGUOUS` si la diferencia
  supera 1 ms. **Los 57 calzaron exacto** — 0 ambiguos.

## Resultado: evidence_level

```
DIRECT: 76 / 76
TIME_MATCH_AMBIGUOUS: 0
```

## Resultado: mecanismo (clasificado por diferencia real de `blockCells`)

```
SHARED_CELL_VALUE_NOISE:                    44   (58%)
EDGE_LEVELS_MISSING+SHARED_CELL_VALUE_NOISE: 31   (41%)
EDGE_LEVELS_MISSING:                          1   (1%)
NO_CELL_DIFFERENCE_FOUND (= ALGORITHM_DIFF):  0   (0%)
```

**Cero `ALGORITHM_DIFF` en los 76 casos** — ningún caso tiene `blockCells`
idénticas de los dos lados y una geometría o decisión distinta. En todos los
76, la causa está en la entrada al clustering (celdas), nunca en el
clustering mismo. Esto extiende a los 76 casos completos lo que antes sólo
estaba verificado línea por línea contra el `.cs` para el algoritmo en
abstracto.

Distribución (descriptiva, sin proponer tolerancia — eso queda para la
siguiente etapa):
- `n_value_diffs` (ruido en celdas compartidas): mediana 4, máximo 27.
- `py_only_vol` (volumen en ticks completamente ausentes de NT8): mediana 0
  (44/76 casos sin ninguna pérdida de ticks), máximo 141.
- Cantidad de ticks perdidos por caso: mediana 0, máximo 49.

## Resultado: decisión real de NT8 en los 57 `MISSING_IN_NT8`

```
ABSTAIN_BELOW_THRESHOLD: 43   (hubo cluster(s), ninguno superó el umbral historico)
ABSTAIN_NO_HISTORY:      12   (bucket sin MinSamplesPerBucket=20 muestras aun)
CREATE:                   2   (NT8 SI creo zona -- ver abajo)
```

### Los 2 casos `CREATE`: no son falla de detección, son falla de emparejamiento del gate

`py_id=201` y `py_id=237` — los dos con mayor `ratio` (1.457 y 1.748) de los
4 outliers que habían quedado como hipótesis abierta en
`AVOLCLUSTERPOI_PARITY_NQ0626_TASKS123_FINDINGS_2026-09-01.md`:

| py_id | NT8 decision | nt8_best_score | nt8_threshold | ticks perdidos (Python→NT8) | vol perdido |
|---|---|---|---|---|---|
| 201 | CREATE | 709 | 587 | 13 | 27 |
| 237 | CREATE | 1028 | 636 | 43 | 106 |

NT8 **sí detectó y creó una zona** en ambos bloques, con margen cómodo sobre
su propio umbral. El gate los cuenta como `MISSING_IN_NT8` porque
`match_zones` corre con `tol_geom_ticks=0` y la geometría de la zona NT8
(recortada por la misma pérdida de ticks de borde, aquí a una escala mucho
mayor que los `GEOMETRY_DIFF` típicos) queda demasiado lejos de la zona
Python para que el emparejador los reconozca como el mismo evento. Es el
mismo mecanismo de fondo (pérdida de ticks de borde) empujado a una
magnitud donde dejó de ser "geometría distinta del mismo evento" y pasó a
ser "dos eventos sin pareja" desde la óptica del gate.

### Los otros 2 outliers (`98`, `142`): confirman la hipótesis de historial corto

Ambos con decisión real `ABSTAIN_NO_HISTORY` — el bucket de NT8 todavía no
tenía las `MinSamplesPerBucket=20` muestras históricas necesarias en esa
fecha (temprano en la ventana de datos). Esto **confirma con dato real** la
hipótesis que `TASKS123_FINDINGS` había dejado explícitamente como "no
verificado, declarado como hipótesis, no hecho".

## Lo que este censo NO hace (a propósito)

- No propone una tolerancia ni una distribución de aceptación — eso es la
  siguiente etapa del orden operativo del canal 030, a cargo del auditor.
- No re-corre el gate de paridad.
- No decide si `EDGE_LEVELS_MISSING` es aceptable o requiere corregir el
  filtro `Low[0]/High[0]` del `.cs` — sigue siendo decisión de Nico.
- No atribuye la pérdida de ticks a esa línea exacta del `.cs` con prueba
  directa (sigue siendo la misma atribución "muy plausible, no observación
  directa" que señaló el canal 030 — este censo no agrega una prueba A/B ni
  un log de los ticks descartados en ese `continue`; sólo confirma que la
  pérdida ocurre en 32/76 casos, en volumen y ubicación consistentes con ese
  mecanismo).
