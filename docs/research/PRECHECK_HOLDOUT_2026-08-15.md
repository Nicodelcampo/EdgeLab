# Auditoria del precheck de re-corte y de los dos indices sellados

Fecha: 2026-08-15 (UTC-3). Rama: `research/bigtrap2-local-displacement-null`.
Insumos auditados: `docs/research/bundle_index.json` (commit `69eb269`) y
`docs/research/recut_index.json` (commit `4e3bb5a`), producidos en la maquina
gobernada local con `pyarrow` sobre los 11 archivos reales.

Este documento registra lo que se pudo verificar de forma independiente desde
el sandbox, lo que no, y cuatro hallazgos. Ninguna etiqueta formal se emite
aca: el sandbox es diagnostico y no adjudica.

## 1. Lo que cierra

| Verificacion | Resultado |
| --- | --- |
| `rows_keep + rows_drop == rows_total` en los 11 archivos | cierra 11/11 |
| Suma de `rows_keep` vs `totals.rows_keep` | 48.510.023 = 48.510.023 |
| Suma de `rows_drop` vs `totals.rows_drop` | 62.827.237 = 62.827.237 |
| Suma de fuga naive vs `totals` | 101.364 = 101.364 |
| Suma de `rows_total` de los 11 | 111.337.260 |
| Particion del censo: 967.077.396 limpios + 111.337.260 objetivo | 1.078.414.656 = censo local declarado |
| `by_asset` del bundle: suma de filas | 967.077.396 = `total_rows` |
| `by_asset` del bundle: suma de bytes | 16.096.746.939 = `total_bytes` = 14,991 GiB |
| `columns_total` | 585 = 45 x 13 |
| `trade_date_max_keep` en los 11 | 20260630 en todos |
| `ts_max_keep_ns` < apertura de sesion CME | cumple en los 11 |

El residuo del censo cierra al tick sin que nadie lo forzara: los 11 archivos
en cuarentena tienen exactamente las filas que faltaban entre el censo total y
los 45 elegibles.

### Validacion cruzada independiente

`6E_09-26_ticks.parquet` reporta **871** filas filtradas por la frontera CME
exacta frente al corte UTC ingenuo. Es exactamente el numero que el auditor
externo midio para H-1 (fuga UTC de 871 filas), por otra via y sobre otro
archivo (el paquete de 90 dias, 1.131.047 ticks). Dos artefactos producidos por
caminos distintos coinciden al tick en la ventana de 2 horas. Ademas el sha256
de origen de ese archivo (`6ffcdf04...`) es uno de los cinco parquets canonicos
declarados del proyecto.

Fuga total prevenida: 101.364 ticks. El 57 % (58.035) esta en un solo archivo,
`MNQ_09-26`, que es el de mayor actividad en la reapertura de Globex.

## 2. Hallazgo 1: falso positivo de deriva de codigo por CRLF

`recut_index.json` declara en `code_identity` cuatro modulos cuyos
`git_blob_sha1` NO coinciden con los blobs commiteados:

| Modulo | blob local | bytes local | blob repo | bytes repo | delta |
| --- | --- | --- | --- | --- | --- |
| `identity.py` | `f4e4e654...` | 6.586 | `77395791...` | 6.383 | +203 |
| `inventory.py` | `e3f1ca6e...` | 7.595 | `26259483...` | 7.381 | +214 |
| `sessions_cme.py` | `a59f5887...` | 6.340 | `57c5d24f...` | 6.168 | +172 |
| `instruments.py` | `9888fe7c...` | 2.791 | `30ea647e...` | 2.717 | +74 |

No es deriva semantica. Se probo con hash, no con hipotesis: se transcribio el
`sessions_cme.py` commiteado al sandbox (verificando primero que la copia daba
blob `57c5d24f...`, es decir transcripcion byte-exacta), se convirtio LF -> CRLF
y el resultado dio blob `a59f5887...` con 6.340 bytes, identico al declarado por
el manifiesto. El delta de bytes es igual a la cantidad de lineas del archivo
(172), y el mismo patron se repite en los otros tres.

Causa: checkout Windows con `core.autocrlf`. Consecuencia: `identity.git_blob_sha1`
hashea los bytes del working tree, asi que en Windows **nunca** va a igualar el
blob commiteado. El campo `code_identity` era inutil para verificar
reproducibilidad y generaba una acusacion falsa de deriva en cada corrida.

Mitigacion aplicada: `tools/verify_indices.py` clasifica cada modulo como
`LF_EXACTO`, `CRLF_NORMALIZADO` o `DERIVA`, tolerando el fin de linea sin tapar
deriva real (si los bytes o el sha256 no cuadran con la variante, es `DERIVA`).
Pendiente en el board como P-26: agregar `git_blob_sha1_lf` de forma aditiva a
`edgelab/kaggle/identity.py` para que el manifiesto lo traiga de fabrica.

## 3. Hallazgo 2: la cuarentena no es "los contratos 09-26"

De los 11 archivos, dos no son 09-26: `GC_08-26_ticks.parquet` y
`MBT_07-26_ticks.parquet`. El criterio real no es el contrato sino el
solapamiento con el holdout, y hay contratos de julio y agosto que tambien
cruzan la frontera. Importa para la opcion de presupuesto "solo front month":
recortar por contrato no equivale a recortar por solapamiento.

## 4. Hallazgo 3: ticks conservados dentro de la pausa de mantenimiento

Nueve de los once archivos terminan su prefijo conservado en `20:59:59.xxx` UTC,
que es `15:59:59` CT, justo antes de la pausa diaria 16:00-17:00 CT. Dos no:

| Archivo | `ts_max_keep_ns` | UTC | CT |
| --- | --- | --- | --- |
| `NQ_09-26` | 1782856799856000000 | 21:59:59,856 | 16:59:59 |
| `MBT_07-26` | 1782856798984000000 | 21:59:58,984 | 16:59:58 |

No es un leak: por la regla congelada esos ticks pertenecen al trade date
20260630 y son datos de research. Pero caen en una hora en la que el mercado
esta halted, asi que son impresiones de pre-apertura, settlement o skew de
reloj. Se marca como aviso de calidad (`calidad.pausa_mantenimiento`) y
queda para los chequeos de integridad, que hoy no cuentan filas dentro de la
pausa. Propuesta aditiva: `rows_in_maintenance_break` por archivo en el
manifiesto de re-corte.

## 5. Hallazgo 4: la proyeccion de `--precheck` subestima el presupuesto

`projected_bundle` del manifiesto informa 45 archivos, 49 top-level y
`ABSTAIN_CAPACITY`. Eso es correcto para el codigo pero enganoso para la
decision: en modo `--precheck` no hay salidas, asi que la proyeccion solo cuenta
los limpios. El arbol `research-v2` real, despues del re-corte, tiene:

- 45 limpios + 11 re-cortados + 4 de metadata = **60 archivos top-level**
- 16.096.746.939 B + aprox. 0,74e9 B (43,6 % de las filas de los 11) = **aprox. 15,7 GiB**
- 967.077.396 + 48.510.023 = **1.015.587.419 ticks**

Con eso, el gate de Kaggle `top_level_files_kaggle` pasa de `pass` (49 <= 50) a
**fallar** (60 > 50), y el de contrato sigue fallando (60 > 20), igual que el de
tamano (15,7 > 10). El re-corte mejora la legalidad del holdout y **empeora** el
cuadro de capacidad. `tools/verify_indices.py` proyecta el arbol post-re-corte y
avisa cuando el manifiesto informa menos archivos que los que va a haber.

## 6. Correccion al doc del 14-ago

`docs/research/RECUT_HOLDOUT_2026-08-14.md` afirmaba, sin medicion, que los
contratos 09-26 estaban en ZSTD y el 06-26 en SNAPPY. La medicion lo refuta:
**10 de los 11 son SNAPPY** y solo `ZB_09-26` es ZSTD. La herramienta preserva
la compresion por archivo, asi que el comportamiento es correcto; lo que estaba
mal era la afirmacion del documento. Queda corregido aca.

## 7. `tools/verify_indices.py`

Verificador fail-closed, solo stdlib + numpy, no lee parquets. Seis familias:

1. **Sellos**: recomputa `index_sha256` y `recut_index_sha256` con la misma
   canonicalizacion de `identity.sha256_json`. Un manifiesto editado a mano no
   cierra.
2. **Cadena**: `source_index` apunta al bundle exacto (sello, tool, veredicto),
   el conjunto objetivo es exactamente la cuarentena del bundle, y cada archivo
   coincide en `source_sha256` y `rows_total` con su registro sellado.
3. **Aritmetica**: por archivo, contra `totals`, fuga <= descarte y particion
   del censo.
4. **Frontera**: no le cree al manifiesto; re-deriva la apertura de sesion con
   `sessions_cme.session_bounds_utc_ns(20260701)` desde la tzdata del sistema y
   la compara contra el oraculo `1782856800000000000`.
5. **Identidad de codigo**: tolerante a CRLF, intolerante a deriva.
6. **Presupuesto honesto**: proyecta el arbol post-re-corte y contrasta con lo
   que declara el manifiesto.

Veredictos por precedencia: `FAIL_SEAL`, `FAIL_CHAIN`, `FAIL_ARITH`, `FAIL_CUT`,
`FAIL_STATUS`, `FAIL_CODE`, `WARN_MAINTENANCE`, `WARN_BUDGET`, `PASS`. Los
`FAIL_*` dan exit 1; los `WARN_*` no bloquean.

Self-test: 15 grupos, 20 checks, 0 fallas. Cubre sello adulterado en ambos
indices, cadena cruzada rota, `source_sha256` distinto al sellado, aritmetica
adulterada, censo que no particiona, `ts_max_keep` sobre la frontera,
`trade_date` de holdout conservado, precheck que declara salidas, CRLF vs
deriva real, bytes inconsistentes con la variante, ultimo tick en la pausa y
ausencia del bundle.

Durante el desarrollo el self-test encontro dos defectos propios: un fixture que
declaraba un solo modulo (el verificador exige los cuatro, fail-closed) y un
caso "sano" con `ts_max_keep` en `21:00:00Z`, que es el primer instante de la
pausa y disparaba el aviso de calidad.

## 8. Estado de P-23 y que falta

El criterio `a` de P-23 ahora si esta cerrado: `bundle_index.json` esta
commiteado y su veredicto `ABSTAIN_LICENSE` es reproducible desde el repo. Lo
que sigue abierto:

- **P-18**: mitigado en codigo y ahora medido, pero el re-corte fisico no se
  ejecuto. `research-v2` no existe todavia.
- **Licencia**: `ABSTAIN_LICENSE` sigue firme. Ningun re-corte lo mueve; es una
  decision documental con fuentes CME, no un problema de datos.
- **Capacidad**: `ABSTAIN_CAPACITY` empeora despues del re-corte (60 archivos,
  15,7 GiB). Requiere decision humana entre enmendar el presupuesto del
  contrato, publicar solo front month por activo, pre-registrar un subconjunto
  de activos, o podar columnas.
- **P-26** (nuevo): normalizacion de fin de linea en `identity.py`.

## 9. Orden de ejecucion para el re-corte fisico

```
python tools/verify_indices.py --bundle docs/research/bundle_index.json \
                              --recut  docs/research/recut_index.json
python tools/recut_holdout.py --index docs/research/bundle_index.json \
                              --out-base E:/EdgeLab/data/nt8_research_v2
python tools/verify_indices.py --bundle docs/research/bundle_index.json \
                              --recut  E:/EdgeLab/data/nt8_research_v2/recut_index.json
python tools/build_kaggle_bundle.py --base E:/EdgeLab/data/nt8_research_v2 \
                                    --dataset-id nicolasbuttaro/edgelab-cme-futures-universe
```

El re-corte re-verifica el sello del indice y el sha256 de cada origen antes de
escribir, verifica cada salida por digest y renombra a `.rejected` lo que no
cierre. Los parquets de origen son inmutables y la barrera de escritura aborta
si `--out-base` cae dentro del arbol de origen.
