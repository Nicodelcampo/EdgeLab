# Re-corte fisico del holdout: ejecucion real y auditoria del arbol `research-v2`

**Fecha:** 15-ago-2026
**Corrida:** maquina local gobernada (`nicolasbuttaro-eng`), backend `pyarrow`, `E:\EdgeLab\data\nt8` -> `E:\EdgeLab\data\nt8_research_v2`
**Herramienta:** `tools/recut_holdout.py@v1` (blob `f794711d1c3cd92cd2d2a1d645c3828c83603853`)
**Manifiesto auditado:** `docs/research/recut_index.json` @ commit `46280d9890dcfcda6f5ab43558c7604d636ade9f`, blob `a64c28cc481f4a9eadb59c105b53569e15c94c25`, sello `recut_index_sha256 = 84179713e6140a0b06b079e172f2737270b7066b30d5170be7e05b221554a153`
**Auditoria:** `Nicodelcampo` (sandbox diagnostico). El auditor no tiene acceso a los parquets: audita el manifiesto commiteado y la aritmetica, no los datos.

Este documento es diagnostico. No emite etiquetas formales, no abre holdout y no mira P&L.

---

## 1. Secuencia ejecutada

| Paso | Comando | Resultado |
| --- | --- | --- |
| 1 | `verify_indices.py --bundle docs/research/bundle_index.json --recut docs/research/recut_index.json` | 34/38 ok, 0 fallas, 4 avisos, `WARN_MAINTENANCE` |
| 2 | `recut_holdout.py --index docs/research/bundle_index.json --out-base E:/EdgeLab/data/nt8_research_v2` | `[PASS] 11/11`, 48.510.023 conservadas, 62.827.237 descartadas, 101.364 filas que el corte UTC ingenuo habria filtrado |
| 3 | `verify_indices.py --recut E:/EdgeLab/data/nt8_research_v2/recut_index.json` | 33/36 ok, 0 fallas, 3 avisos, `WARN_MAINTENANCE` |

Se respeto la regla de gobernanza: el paso 2 solo se ejecuto porque el paso 1 no devolvio ningun `FAIL_*`.

---

## 2. Que quedo probado

### 2.1 Los dos sellos se recomputaron (cierra el criterio `a` de P-23)

| Indice | Sello declarado | Recomputado |
| --- | --- | --- |
| `bundle_index.json` | `6d46269c7e35a8a7...` | identico |
| `recut_index.json` (precheck) | `b571b7ad554984c4...` | identico |
| `recut_index.json` (corrida real) | `84179713e6140a0b...` | identico |

Hasta esta corrida los sellos estaban **declarados** pero nunca recomputados por una herramienta independiente. Ahora lo estan, mecanicamente, con `canonical_sha256_json` (claves ordenadas, separadores compactos, excluyendo el propio campo del sello).

### 2.2 Las fuentes inmutables siguen intactas *despues* de escribir

`chain.sha256_por_archivo`: **sha256 medido == sellado en 11/11**, medido despues del re-corte fisico. Es la linea mas importante de toda la corrida: prueba que escribir el arbol nuevo no toco ni un byte del arbol de origen.

### 2.3 Aritmetica re-verificada a mano contra el manifiesto anterior

Para cada activo: `filas_limpias (bundle) + filas_conservadas (re-corte) = filas del arbol nuevo`, y lo mismo en bytes. Las 22 identidades cierran **exactas**:

| Activo | Filas limpias | + conservadas | = total declarado | Bytes limpios | + salida | = total declarado |
| --- | --- | --- | --- | --- | --- | --- |
| 6B | 7.364.010 | 427.742 | 7.791.752 | 131.594.820 | 8.889.245 | 140.484.065 |
| 6E | 17.670.842 | 1.084.345 | 18.755.187 | 300.133.682 | 21.410.542 | 321.544.224 |
| 6J | 13.953.028 | 674.550 | 14.627.578 | 230.870.360 | 12.599.160 | 243.469.520 |
| ES | 250.063.610 | 12.743.000 | 262.806.610 | 3.551.151.253 | 219.193.735 | 3.770.344.988 |
| GC | 35.350.462 | 2.804.464 | 38.154.926 | 708.145.816 | 70.053.164 | 778.198.980 |
| MBT | 4.342.695 | 126.735 | 4.469.430 | 93.338.488 | 3.565.243 | 96.903.731 |
| MES | 157.731.749 | 9.334.111 | 167.065.860 | 2.645.828.892 | 195.150.343 | 2.840.979.235 |
| MNQ | 323.024.325 | 11.482.403 | 334.506.728 | 5.673.557.832 | 240.465.471 | 5.914.023.303 |
| NQ | 112.917.737 | 6.235.464 | 119.153.201 | 2.193.360.120 | 152.697.147 | 2.346.057.267 |
| YM | 20.023.825 | 1.027.629 | 21.051.454 | 419.836.938 | 26.033.207 | 445.870.145 |
| ZB | 24.635.113 | 2.569.580 | 27.204.693 | 148.928.738 | 20.196.773 | 169.125.511 |

Identidades globales:

- Filas: `967.077.396 + 48.510.023 = 1.015.587.419` = `total_rows` declarado.
- Bytes: `16.096.746.939 + 970.254.030 = 17.067.000.969` = `total_bytes` declarado = **15,895 GiB**.
- Particion del censo: `967.077.396 + 111.337.260 = 1.078.414.656` = censo local completo.
- Columnas: `56 x 13 = 728`. Contratos: `5 x 10 + 6 (MBT) = 56`. Limpios enlazados: 45. Re-cortados: 11.
- Por archivo: `rows_keep + rows_drop = rows_total` en 11/11, y `fuga_naive <= rows_drop` en 11/11.

### 2.4 Que sigue **sin** probar

1. **Los digestos de salida son auto-atestiguados.** `output_sha256` / `output_blob_sha1` / `output_bytes` los calculo el mismo proceso que escribio los archivos. Ningun tercero los recalculo. -> lo cierra `tools/verify_tree.py` (seccion 5).
2. **No existe prueba fisica de "cero holdout".** La afirmacion se apoya en `ts_max_keep` declarado por el escritor y en la elegibilidad por archivo del builder, no en una medicion independiente de `max(ts_utc_ns)` sobre los 56 parquets. -> lo cierra `verify_tree.py --maxts`.
3. **`research-v2` no es publicable.** Sigue bloqueado por licencia (`ABSTAIN_LICENSE`, criterio CME) y ahora por capacidad con **tres** compuertas en rojo (seccion 4).

---

## 3. Hallazgos nuevos

### H-5. Mi propia proyeccion subestimo el tamano del arbol (defecto de `verify_indices.py`)

El paso 3 imprimio `research-v2 proyectado: 60 archivos top-level, 15.752 GiB`. El manifiesto real, que ya trae los bytes **medidos** de cada salida, dice **15,895 GiB**.

| | Bytes | GiB |
| --- | --- | --- |
| Estimado por `verify_indices.py` (proporcional a filas) | 16.913.581.212 | 15,752 |
| Medido en el manifiesto real | 17.067.000.969 | 15,895 |
| Diferencia | 153.419.757 (146,3 MiB) | +0,143 |

Sobre el total el error es de 0,9 %; sobre la porcion re-cortada es de **+18,8 %** (816.834.273 estimados vs 970.254.030 medidos). Causa: post-corrida la herramienta sigue extrapolando `source_bytes x keep/total` en lugar de leer `output_bytes`, que ya esta en el manifiesto. Es un defecto de la herramienta, no de la corrida. -> **P-27**.

### H-6. Re-escribir cuesta ~19 % mas bytes por fila, en 11/11 activos

Comparando cada activo contra sus propios archivos limpios (mismo instrumento, mismo codec):

| Activo | B/fila limpios | B/fila re-cortado | Delta |
| --- | --- | --- | --- |
| 6B | 17,87 | 20,78 | +16,3 % |
| 6E | 16,99 | 19,75 | +16,3 % |
| 6J | 16,54 | 18,68 | +12,9 % |
| ES | 14,20 | 17,20 | +21,1 % |
| GC | 20,03 | 24,98 | +24,7 % |
| MBT | 21,49 | 28,13 | +30,9 % |
| MES | 16,77 | 20,91 | +24,6 % |
| MNQ | 17,56 | 20,94 | +19,2 % |
| NQ | 19,42 | 24,49 | +26,1 % |
| YM | 20,97 | 25,33 | +20,8 % |
| ZB (ZSTD) | 6,05 | 7,86 | +30,0 % |

Las 11 van en la misma direccion, con magnitudes de 12,9 % a 30,9 %, sobre dos codecs distintos: es sistematico, no un efecto del contenido. Hipotesis principal: la granularidad de escritura (`DEFAULT_BATCH_ROWS = 262.144`) produce mas grupos de fila que el archivo original, y cada grupo reinicia diccionarios y RLE. Confusion residual: los re-cortados son prefijos truncados, asi que amortizan el footer sobre menos filas.

**Experimento decisivo (barato):** re-escribir `ES_09-26` (12.743.000 filas, 219.193.735 B) variando una cosa por vez: `row_group_size = 1.048.576`; luego `compression="zstd"`; luego sin las dos columnas redundantes de H-7. Medir bytes en cada paso.

### H-7. Dos pares de columnas son redundantes en los 11 archivos

El manifiesto trae `digest_columns` (sha256 por columna). En **11/11 archivos**:

- `digest(ts_utc_ns) == digest(ts_local_ns)`
- `digest(sequence) == digest(source_row)`

22 igualdades de sha256 independientes. Consecuencias:

1. **`ts_local_ns` no aporta informacion**: si fuera hora local de Chicago diferiria del UTC en 5-6 h. Es un duplicado.
2. **`sequence` no es un numero de secuencia del exchange**, es (casi con certeza) el indice de fila del origen, igual que `source_row`. Cualquier analisis de microestructura que asuma secuenciacion del mercado (orden de eventos dentro del mismo timestamp, deteccion de huecos) **no esta soportado por estos datos** y debe pre-registrarse como limitacion.
3. El esquema tiene **11 columnas informativas de 13** (y `instrument` + `contract` son constantes por archivo, ya presentes en la ruta y el nombre). Podar es la unica palanca de presupuesto que no cuesta ciencia.

Los digestos prueban indistinguibilidad bajo la funcion de digesto de la herramienta; la comparacion directa columna a columna la zanja: `verify_tree.py --columns`.

### H-8. Los 45 limpios son enlaces duros: el arbol no es una copia fisica

`linked_clean[*].method = "hardlink"` en 45/45, con `sha256_matches_index: true` en todos. Entonces:

- El arbol nuevo ocupa en disco ~0,97 GiB de datos nuevos, no 15,9 GiB.
- **45 de los 56 archivos comparten inodo con `E:\EdgeLab\data\nt8`.** Cualquier escritura in-place sobre un archivo de `research-v2` mutaria el parquet inmutable de origen. Hoy la inmutabilidad depende de que nadie escriba in-place, no de una barrera.
- Al subir a Kaggle los enlaces se materializan: los 15,895 GiB son reales para la publicacion.

Mitigacion propuesta: quitar el bit de escritura en los dos arboles y verificarlo (`verify_tree.py` lo chequea y avisa). -> **P-29**.

### H-9. El aviso de proyeccion subestimada se apago solo (confirma el hallazgo del 15-ago)

Paso 1: 38 chequeos, 4 avisos. Paso 3: 36 chequeos, 3 avisos. El que desaparecio es `presupuesto.proyeccion_del_manifiesto`, que en el precheck disparaba porque el manifiesto proyectaba 49 archivos top-level contando solo los limpios. El manifiesto real proyecta **60** y coincide con lo que calcula el verificador. El hallazgo "la proyeccion del precheck subestima el arbol" quedo confirmado y cerrado por los propios datos.

### H-10. `WARN_MAINTENANCE` persiste y ahora esta horneado en el arbol limpio

`NQ_09-26` (`ts_max_keep = 1782856799856000000`) y `MBT_07-26` (`1782856798984000000`) terminan **dentro** de la pausa de mantenimiento 16:00-17:00 CT (21:00-22:00 UTC), a 144 ms y ~1 s de la reapertura. Los otros 9 cortan en 15:59:5x CT, justo antes de la pausa. No es fuga de holdout (el trade date sigue siendo 20260630), pero son ticks con el mercado detenido y ahora forman parte de `research-v2`. Falta el contador aditivo `rows_in_maintenance_break` para saber **cuantos** son. -> **P-26**.

---

## 4. Presupuesto: el arbol empeoro, y cual es la ruta a 10 GiB

| Compuerta | Valor | Limite | Estado |
| --- | --- | --- | --- |
| `input_size_gib` | 15,895 | 10,0 | **rojo** (+58,9 %) |
| `top_level_files_contract` | 60 | 20 | **rojo** |
| `top_level_files_kaggle` | 60 | 50 | **rojo** (en el precheck estaba en verde con 49) |
| `dataset_size_kaggle` | 15,895 | 200,0 | verde |

Veredicto proyectado: `ABSTAIN_CAPACITY`. **Tres** compuertas en rojo, una mas que en la proyeccion del precheck.

Dos familias de problema, con soluciones distintas:

**Tamano (15,895 GiB > 10).** Hay una ruta medible que no reduce la ciencia:
1. podar `ts_local_ns` y `source_row` (H-7): dos columnas int64 duplicadas de otras dos, sobre 13;
2. re-encodear con ZSTD en lugar de SNAPPY (10 de 11 fuentes son SNAPPY);
3. subir `row_group_size` (H-6).
Hay que **medirlo sobre `ES_09-26`** antes de prometer nada. No es aceptable estimarlo: justamente H-5 es un error de estimacion.

**Cantidad de archivos (60 > 20 y > 50).** No se arregla comprimiendo. Requiere decision de alcance: menos contratos por activo (solo front-month), subconjunto de activos pre-registrado, o renegociar el numero del contrato v2. Es decision de Nico, no del auditor. -> **P-25**.

---

## 5. Herramienta nueva: `tools/verify_tree.py@v1`

Cierra el hueco 2.4.1 y 2.4.2: recalcula desde cero lo que el manifiesto afirma sobre si mismo y mide lo que el manifiesto no puede atestiguar.

Familias de chequeo:

| Familia | Que hace |
| --- | --- |
| `manifiesto.*` | herramienta correcta, `precheck=false`, veredicto `PASS`, estados `RECUT` completos, 7 totales, `keep+drop=total` |
| `inventario.*` | nada falta, nada sobra, ningun nombre duplicado en dos carpetas, cada salida en la carpeta declarada, listado de archivos no-parquet |
| `salidas.digestos` | re-hashea las 11 salidas: bytes + sha256 + git-blob-sha1 |
| `enlaces.digestos` | re-hashea los 45 limpios contra el sello |
| `fuente.intacta` | re-hashea las 11 fuentes y las compara con el sello del bundle |
| `enlaces.inodo` | compara `(st_dev, st_ino)` con el origen: detecta si un "hardlink" declarado es en realidad una copia |
| `proteccion.escritura` | avisa si algun parquet conserva bit de escritura |
| `holdout.max_ts_fisico` | **con `--maxts`**: mide `max(ts_utc_ns)` en disco (estadisticas del footer, o escaneo si faltan) y exige que sea `<` la apertura de sesion CME. Prueba fisica de cero holdout |
| `columnas.*` | detecta pares de columnas con digesto identico y, con `--columns`, los compara lote a lote con pyarrow |

Precedencia de veredicto: `FAIL_HOLDOUT` > `FAIL_MANIFIESTO` > `FAIL_INVENTARIO` > `FAIL_FALTANTE` > `FAIL_DIGESTO` > `FAIL_FUENTE` > `FAIL_COLUMNAS` > `WARN_ENLACES` > `WARN_ESCRITURA` > `WARN_COLUMNAS` > `PASS`. `FAIL_*` sale con codigo 1; `WARN_*` con 0. Un manifiesto de precheck es rechazado de entrada: no describe ningun arbol.

Self-test: 19 casos adversarios (`S1`-`S19`) mas la logica pura de la prueba de holdout, **24 chequeos, 0 fallas**. Cubre salida ausente, bytes/sha256/blob alterados, fuente mutada despues de escribir, parquet intruso, nombre ambiguo, hardlink roto, permiso de escritura, digestos duplicados, totales que no cierran, estado que no es `RECUT`, particion rota, carpeta equivocada, veredicto de origen distinto de `PASS` y manifiesto sin frontera de corte.

Comando:

```
python tools/verify_tree.py --recut E:/EdgeLab/data/nt8_research_v2/recut_index.json --maxts --columns --json-out docs/research/verify_tree_2026-08-15.json
```

`--out-base` y `--base` se toman del manifiesto. Con estadisticas de footer presentes (`stats_missing_files: []` en el bundle) `--maxts` es cuestion de segundos; el re-hasheo completo son ~17 GB de lectura.

---

## 6. Tablero

| ID | Estado | Item |
| --- | --- | --- |
| P-18 | fisico cerrado, verificacion independiente pendiente | re-corte del holdout: hecho, 11/11 `RECUT`; falta `verify_tree.py --maxts` |
| P-23 | criterio `a` cerrado | indices commiteados **y** sellos recomputados |
| P-24 | abierto | auditar `edgelab/kaggle/streaming.py` (blob `08e3cee4...`, 11.100 B): sin revisar, sin sellar, ausente de `code_identity` |
| P-25 | abierto, decision de Nico | presupuesto v2: 3 compuertas en rojo; ruta medible en la seccion 4 |
| P-26 | abierto | aditivos: `git_blob_sha1_lf` en `identity.py`, `rows_in_maintenance_break` en `recut_holdout.py` |
| P-27 | **nuevo** | `verify_indices.py`: post-corrida usar `output_bytes` medidos en vez de la extrapolacion, y comparar estimacion vs medicion (H-5) |
| P-28 | **nuevo** | columnas redundantes y semantica de `sequence` (H-7): verificar con `--columns`, documentar el esquema real de 11 columnas informativas, pre-registrar la limitacion de microestructura |
| P-29 | **nuevo** | proteger contra escritura los dos arboles (H-8): los 45 limpios comparten inodo con el origen inmutable |

Pendiente de correccion documental: `docs/research/RECUT_HOLDOUT_2026-08-14.md` sigue afirmando que los 09-26 son ZSTD y el 06-26 SNAPPY. La medicion dice lo contrario: 10 de 11 son SNAPPY y solo `ZB_09-26` es ZSTD.
