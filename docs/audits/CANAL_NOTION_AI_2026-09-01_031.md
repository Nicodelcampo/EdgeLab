# Canal 031 — auditoría de `27a583a`: el censo no habilita tolerancia todavía

**Fecha:** 2026-09-01

## Lo que sí cierra

El commit remoto `27a583a55923612e1814b9dca9f489ea61d1a084` existe y contiene
constructor, README, CSV y JSON. Los conteos publicados cierran entre sí:

- 19 `GEOMETRY_DIFF` + 57 `MISSING_IN_NT8` = 76;
- decisiones NT8 de los 57: 43 `ABSTAIN_BELOW_THRESHOLD` + 12
  `ABSTAIN_NO_HISTORY` + 2 `CREATE` = 57;
- mecanismos declarados: 44 + 31 + 1 = 76.

El CSV diagnóstico canónico está registrado como blob
`276acc7e0fd7d0dc5ae8ea1fba0254457de8770c`, 22.998.868 bytes. La corrección
CRLF/LF es coherente con `.gitattributes`; el hash de contenido LF declarado es
`81f32a97a65a6eee801eb6639f613349f31a2c02354862c128126af1adabf9da`.

## Bloqueos encontrados

### 1. “0 TIME_MATCH_AMBIGUOUS” no está demostrado por el constructor

`build_censo.py` construye:

```python
diag_by_time[d["bar_close_time"]] = d
```

Si dos bloques tienen el mismo `bar_close_time`, el último sobrescribe al anterior sin
alarma. Después un lookup exacto parece unívoco aunque hubiera duplicados. Antes de
afirmar 76/76 exactos hay que publicar:

- cantidad de timestamps duplicados en las 22.508 filas;
- assert de unicidad, o clave compuesta `bar_close_time + bar_index/bucket`;
- número de candidatos por caso, no sólo delta temporal.

### 2. `EDGE_LEVELS_MISSING` es una etiqueta no derivada

`classify()` llama `EDGE_LEVELS_MISSING` a **cualquier** diferencia de conjuntos de
precios. No verifica que los niveles exclusivos sean contiguos ni estén fuera del hull
de niveles compartidos. Incluso hay casos con niveles exclusivos en ambos extremos y
uno con un nivel exclusivo de NT8. Hasta ejecutar esa comprobación, el nombre correcto
es `CELL_LEVEL_SET_DIFF`, no “edge”.

### 3. “0 ALGORITHM_DIFF” es más fuerte que la prueba

El script concluye `NO_CELL_DIFFERENCE_FOUND` sólo cuando los diccionarios de celdas son
idénticos. Que todos los residuos tengan alguna diferencia de input no prueba que no
coexista una divergencia algorítmica. La prueba empírica correcta es ejecutar la lógica
Python sobre **las celdas NT8 y el estado NT8** y verificar que reproduce decisión,
cluster y geometría NT8. El censo no hace ese replay contrafactual.

La comparación línea por línea del código sigue siendo evidencia fuerte contra un bug
de traducción; la formulación válida es “0 casos de output distinto con input idéntico
en esta muestra”, no “0 ALGORITHM_DIFF demostrado”.

### 4. `best_score` del diagnóstico vale 0 en abstenciones por construcción

El parche `78b5c94` exporta `diagBestPassScore`, no el máximo score candidato. Ese valor
sólo se actualiza cuando `score >= threshold`; por eso los 43
`ABSTAIN_BELOW_THRESHOLD` aparecen con `nt8_best_score=0`. Falta exportar el verdadero
`best_candidate_score` aunque no pase. Sin eso no se puede medir el margen NT8 al
umbral ni diseñar una tolerancia cuantitativa.

También `diagHistCount` queda en 0 si el bucket tiene menos del mínimo; debe exportar el
conteo real 0…19, no sólo distinguir suficiente/insuficiente.

### 5. Los 12 `ABSTAIN_NO_HISTORY` no están “resueltos” como simple warmup

Python tenía historia suficiente en esos casos: los registros previos publican entre
27 y 121 scores históricos, todos por encima de `MinSamplesPerBucket=20`; NT8 declara
historia insuficiente. Eso es una divergencia material de estado de `SessionProfile`,
no una mera etiqueta de “fecha temprana”. Hay que comparar por caso:

- `hist_samples` real NT8;
- `n_history_scores` Python;
- sesiones incluidas en cada FIFO;
- bucket y fronteras de sesión.

Hasta explicar esa diferencia, esos 12 siguen `UNRESOLVED_HISTORY_STATE_DIFF`.

### 6. Los dos `CREATE` no están vinculados aún a un `nt8_id`

En el loop `MISSING_IN_NT8`, `nt8_id` queda `None` y no se exportan las geometrías
seleccionadas. El timestamp exacto + `decision=CREATE` hace muy plausible un fallo de
matching, pero para probar que `tol_geom_ticks=0` es la causa hay que publicar:

- `nt8_id` correspondiente;
- geometría Python y NT8 en la misma unidad;
- distancia calculada por el matcher;
- cuál condición exacta rechazó la pareja.

### 7. El censo no cubre todos los residuos del gate

El gate también tiene **48 `MISSING_IN_PYTHON`**. Los 76 son el alcance de las tareas
anteriores, no el residual completo de paridad. Para diseñar tolerancia hay que censar
19 + 57 + 48 = **124 casos residuales**, además de informar el denominador de eventos.

El trace Python versionado contiene bloques de creación; para saber por qué Python
abstuvo en esos 48 hace falta exportar/reconstruir todos los bloques Python, incluidos
los `ABSTAIN`.

### 8. Reproducibilidad del script

`build_censo.py` usa rutas absolutas locales (`C:/ProyectosQuant/...` y
`C:/kg/tracedump_final/...`) aunque los inputs ya están commiteados. Debe usar rutas
relativas al repo para ser ejecutable por un tercero.

## Orden de corrección

Sin corrida pesada:

1. hacer el builder repo-relative;
2. detectar duplicados y usar clave compuesta;
3. renombrar/clasificar set-diffs verificando posición de borde;
4. vincular los dos `CREATE` a sus `nt8_id` y reproducir el rechazo del matcher;
5. corregir el export NT8 para `best_candidate_score` e `hist_samples` real.

Con nueva corrida diagnóstica pre-holdout:

6. exportar todos los bloques Python para censar los 48 `MISSING_IN_PYTHON`;
7. comparar el estado histórico en los 12 `NO_HISTORY`;
8. replay contrafactual de las celdas NT8 con la lógica Python.

## Dictamen

`27a583a` mejora radicalmente la clasificación de los 76 casos, pero **no habilita aún
una tolerancia**. Gate formal: `FAIL`. Los cuatro outliers dejan de ser misteriosos en
su decisión inmediata, pero dos abren una deuda de matching y dos pertenecen a una
divergencia de historial todavía sin causa raíz.

**Aporte al referente:** evita fijar una tolerancia sobre un score NT8 que hoy se exporta
como cero en todas las abstenciones, detecta que “exact match” puede ocultar colisiones
de timestamp, y reincorpora los 48 residuos omitidos para que la decisión futura use el
universo completo y no sólo el subconjunto asignado.
