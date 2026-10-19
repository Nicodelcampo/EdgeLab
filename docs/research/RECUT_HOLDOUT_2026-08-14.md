# Re-corte fisico del holdout: `tools/recut_holdout.py` (14-ago-2026)

Estado: herramienta en el repo, self-test en verde (42 checks, 0 fallas).
No corrio todavia contra los datos reales.

## 1. Por que hace falta

El builder v2 midio el arbol local `E:/EdgeLab/data/nt8` y dejo 11 archivos en
cuarentena con `kind=HOLDOUT_OVERLAP` / `recut_required`: son los contratos
09-26, que por construccion contienen ticks de julio y agosto de 2026, es decir
dentro del holdout. El builder los detecta pero NO los corta, porque los
parquets de origen son inmutables por doctrina.

Esta herramienta produce las copias saneadas en un arbol nuevo
(`--out-base`, default `E:/EdgeLab/data/nt8_research_v2`), sin tocar el origen.

## 2. Hallazgo de la corrida del builder: el veredicto tapo dos gates

La cadena de decision del builder (`VERDICT_PRECEDENCE`) evalua en este orden:

    FAIL_INSTRUMENTS -> FAIL_LAYOUT -> FAIL_INTEGRITY -> ABSTAIN_LICENSE
    -> ABSTAIN_HOLDOUT -> ABSTAIN_CAPACITY -> PASS

Como `ABSTAIN_LICENSE` esta antes que los otros dos, el veredicto reportado
**oculta** que tambien fallaron:

| Gate | Estado real en la corrida | Por que |
| --- | --- | --- |
| G-LIC | FALLA (reportado) | `LICENSE_GATE_OPEN`: P-07 sin decision humana |
| G-HOLDOUT | FALLA (tapado) | 11 archivos en cuarentena por solape |
| G-BUDGET | FALLA (tapado) | 14,991 GiB > 10 GiB y 49 archivos top-level > 20 |

El veredicto `ABSTAIN_LICENSE` es correcto, pero **no** significa que la
licencia sea el unico bloqueo. Es el primero de tres.

## 3. Consecuencia: el re-corte solo no habilita `research-v2`

El re-corte cierra G-HOLDOUT, pero **empeora** el conteo de archivos, porque
devuelve al bundle los 11 contratos 09-26 saneados:

| Dimension | Antes del re-corte | Despues del re-corte | Limite | Resultado |
| --- | --- | --- | --- | --- |
| Archivos top-level (contrato) | 45 + 4 = 49 | 56 + 4 = 60 | 20 | FALLA |
| Archivos top-level (Kaggle) | 49 | 60 | 50 | FALLA (antes pasaba) |
| Tamano del input | 14,991 GiB | ~16 GiB | 10 GiB | FALLA |

Por eso la herramienta emite un bloque `projected_bundle` que calcula el
presupuesto con `inventory.budget_gates` y anticipa mecanicamente el veredicto
del builder tras el re-corte, asumiendo licencia aprobada. Con los numeros
actuales ese veredicto proyectado es `ABSTAIN_CAPACITY`.

Esto es una decision humana pendiente (no la toma la herramienta):

1. Enmendar el presupuesto del contrato Kaggle v2 (subir 10 GiB / 20 archivos)
   con justificacion escrita.
2. Publicar solo el mes de front-month por activo (menos archivos, menos GiB).
3. Pre-registrar un subconjunto de activos y publicar solo esos.
4. Podar columnas del esquema para bajar bytes por tick.

## 4. Regla de corte

Se conserva la fila si:

    ts_utc_ns < session_bounds_utc_ns(HOLDOUT_FIRST_TRADE_DATE)[0]

es decir, la apertura de la sesion CME del primer trade date de holdout:
**2026-06-30T22:00:00Z** (17:00 CT del 30 de junio). El corte NO es a
medianoche UTC del 1 de julio: entre ambos hay una brecha de **7200 s** que
contiene ticks que ya pertenecen al trade date 20260701.

La herramienta calcula igual el corte UTC ingenuo y reporta
`rows_leaked_by_naive_utc_cut` por archivo: cuantas filas de holdout habria
dejado pasar el corte equivocado. En el parquet de 90 dias de `6E 09-26` ese
numero fue 871 (H-1 del auditor externo). Aca queda medido para cada archivo.

## 5. Garantias implementadas

1. **Origen inmutable.** Nunca se escribe ni se borra en el arbol de origen. Si
   `--out-base` es el arbol de origen o esta dentro de el, aborta. Esa barrera
   se evalua siempre, incluso si el indice de entrada esta mal.
2. **Identidad encadenada.** El `sha256` de cada origen debe coincidir con el
   que registro el builder en `bundle_index.json`; si no, `FAIL_SOURCE` y no se
   escribe nada.
3. **Sello del indice.** Se recomputa `index_sha256` sobre el contenido del
   indice sin esa clave y se compara con el declarado. Si no cierra,
   `FAIL_INDEX`. Tambien se exige `tool == tools/build_kaggle_bundle.py@v2` y
   `schema_version == 2`, y se rechaza un indice con veredicto `FAIL_*`.
4. **Sin constantes duplicadas.** La herramienta carga el builder por path y
   reutiliza `ASSET_FOLDERS`, `FILENAME_RE`, `TS_COLUMN`,
   `HOLDOUT_FIRST_TRADE_DATE`, `RESEARCH_MAX_TRADE_DATE` y `NAIVE_UTC_CUT_NS`.
   No se re-tipea ninguna tabla (ese fue el defecto D-5 del builder v1).
5. **Monotonia verificada, corte como prefijo.** Primero se verifica que
   `ts_utc_ns` sea no decreciente en todo el archivo; solo entonces el corte se
   hace como prefijo `[0, k)`. Si hay una inversion, `FAIL_UNSORTED` y no se
   escribe: un prefijo sobre datos desordenados perderia filas validas o
   dejaria pasar holdout.
6. **Verificacion post-escritura por digest.** Re-codificar un parquet cambia
   los bytes, asi que no sirve comparar sha256 de archivo. Se comparan digests
   sha256 **por columna** del prefijo conservado, calculados en el origen y
   releidos de la salida. El digest es independiente del tamano de lote. Ademas
   se verifica esquema identico, conteo de filas, `ts_max`, monotonia y
   `trade_date_max <= 20260630`. Si algo no cierra, la salida se renombra a
   `.rejected` y el veredicto es `FAIL_VERIFY`.
7. **Compresion preservada** por archivo (los 09-26 son ZSTD, el 06-26 es
   SNAPPY).
8. **Mismo nombre de archivo** en la salida, para que `FILENAME_RE` del builder
   siga parseando el contrato. El arbol de salida es un `--base` valido.
9. **Los 45 limpios se enlazan** (hardlink, con fallback a copia) y se verifica
   su `sha256` post-enlace, para que `--out-base` sea el bundle completo.
10. **Manifiesto sellado.** `recut_index.json` se emite siempre, incluso sin
    PASS, y trae su propio `recut_index_sha256`.

## 6. Veredictos

| Veredicto | Exit | Significado |
| --- | --- | --- |
| `PASS` | 0 | todos los objetivos cortados y verificados |
| `FAIL_INDEX` | 1 | indice ausente, ilegible, sin sello valido, de otro tool o `FAIL_*` |
| `FAIL_SOURCE` | 1 | origen ausente o `sha256` distinto al del indice |
| `FAIL_UNSORTED` | 1 | `ts_utc_ns` no monotono |
| `FAIL_VERIFY` | 1 | la salida no cierra contra el prefijo medido |
| `ABSTAIN_BACKEND` | 2 | pyarrow no disponible |
| `ABSTAIN_COVERAGE` | 2 | algun archivo queda vacio tras el corte |

## 7. Uso

    # 1. medicion sin escribir nada (recomendado primero)
    python tools/recut_holdout.py --index E:/EdgeLab/kaggle_dataset/bundle_index.json --precheck

    # 2. re-corte real
    python tools/recut_holdout.py --index E:/EdgeLab/kaggle_dataset/bundle_index.json

    # 3. volver a correr el builder contra el arbol saneado
    python tools/build_kaggle_bundle.py --base E:/EdgeLab/data/nt8_research_v2 ...

El paso 3 deberia dar G-HOLDOUT en PASS y dejar a la vista los dos gates que
seguian tapados.

## 8. Cobertura del self-test (42 checks)

| Grupo | Que prueba |
| --- | --- |
| S1 | frontera del corte y brecha de 7200 s |
| S2 | sello del indice, tool inesperado, indice `FAIL_*`, sin escritura |
| S3 | `--precheck`: conteos, filas filtradas por el corte ingenuo, trade date |
| S4 | re-corte real, nombre parseable, compresion, origen intacto, sello |
| S5 | idempotencia (`ALREADY_RECUT`) |
| S6 | proyeccion del presupuesto, incluido `ABSTAIN_CAPACITY` |
| S7-S9 | `FAIL_SOURCE`, `FAIL_UNSORTED`, `ABSTAIN_COVERAGE` |
| S10 | escritura corta detectada, salida marcada `.rejected` |
| S11 | digest independiente del tamano de lote |
| S12 | `--out-base` dentro del origen aborta |

La ruta pyarrow queda aislada en `ArrowBackend` y no la cubre el self-test
(el sandbox no tiene pyarrow). Por eso el primer uso real debe ser `--precheck`.

## 9. Pendiente asociado

- `bundle_index.json` de la corrida local **no esta commiteado**. El criterio
  `a` de P-23 pide la corrida y su indice: la corrida ocurrio, el indice todavia
  no esta en el repo.
- Decision de presupuesto (seccion 3) antes de cualquier publicacion.
- P-07 sigue siendo humano: el gate de licencia esta cerrado en codigo.
