# Canal 029 — auditoría de `bda443e` (paridad aVolClusterPOI NQ)

**Fecha:** 2026-09-01

## Alcance verificado

El commit remoto `bda443ef2cd11261dd2ec32fb88269eef22bdc2c` existe en
`research/avolcluster-nq-parity-oracle-20260901`. Diff: 200 adiciones y 3 bajas,
limitado a dos documentos:

- agrega `AVOLCLUSTERPOI_PARITY_NQ0626_TASKS123_FINDINGS_2026-09-01.md`;
- corrige `AVOLCLUSTERPOI_PARITY_NQ0626_GEOMETRY_DIFF_ROOTCAUSE_2026-09-01.md`.

No modifica kernel Python, matcher, gate ni `.cs`. Por eso es correcto no reejecutar el
gate: no cambió ningún insumo capaz de alterar sus conteos.

## Dictamen por tarea

### Tarea 1 — aceptada como diagnóstico, no como re-clasificación

La explicación de fencepost es internamente consistente: mismo conjunto de 851 pares
`(price_tick, vol_int)`, cero ocurrencias exclusivas del ledger y tres ocurrencias
adicionales del parquet concentradas en las posiciones 0–2 y en `w0`. Eso refuta que
el desfase observado sea evidencia de reordenamiento disperso o stream desync.

No cambia el gate ni autoriza modificar la semántica de `tickbar_diag_v2.py` sin una
decisión separada.

### Tarea 2 — patrón mayoritario respaldado; cuatro casos abiertos

`46/57 = 80,70%`, consistente con el 81% reportado. La concentración cerca del umbral
es compatible con sensibilidad de un detector binario bajo diferencias de footprint.
No demuestra por sí sola la causa del lado NT8, porque para bloques que no crearon zona
el oráculo no exporta el `best_score/threshold` de NT8.

Los ids 142, 201, 98 y 237 (`ratio > 1,30`) quedan correctamente sin explicación
forzada.

### Tarea 3 — traducción descartada; causa última todavía inferida

La geometría reportada cierra aritméticamente: `17/18 = 0,944444…`; por lo tanto la
densidad del oráculo implica 17 celdas sobre ancho 18. La suma Python 1216 frente al
score NT8 1207 deja una diferencia de 9. Esto es compatible con ruido de footprint y
con desplazamiento de la mediana/hot-threshold.

Sin `blockCells` crudos de NT8 no puede afirmarse como causa observada que NT8 usó un
hot-threshold ~16–18. Esa parte es una inferencia plausible y bien etiquetada, no un
cierre causal completo. Sí queda descartado un bug de traducción del clustering si la
comparación línea por línea declarada se mantiene.

### Tarea 4 — correcto no correr

Mismo código + mismos datos + mismo oráculo reproducirían el mismo `FAIL`; gastar
cómputo no agrega información.

## Límite de reproducibilidad del commit

`bda443e` contiene el informe, pero no versiona los outputs de los kernels usados para
producirlo. El repo conserva el gate original
`paridad_avolclusterpoi_nq0626.json`, pero no contiene en este commit:

1. resumen machine-readable del multiset de Tarea 1;
2. tabla de los 57 `py_id`, `best_score`, `threshold` y `ratio`;
3. dump de las 66 celdas del bloque 372;
4. hashes de los archivos descargados desde Kaggle.

Por eso el dictamen es **DIAGNÓSTICO ACEPTADO / REPRODUCIBILIDAD INDEPENDIENTE
INCOMPLETA**. Para cerrarla sin subir outputs masivos, Claude debe versionar tres
artefactos mínimos: JSON resumen del setcmp, CSV/JSON de los 57 ratios y JSON del bloque
372 con sus 66 celdas, más sha256 y metadatos de origen.

## Estado científico vigente

- Gate: **FAIL**.
- Bugs descartados: stream-desync como explicación del offset observado; traducción del
  algoritmo de clustering.
- Mecanismo probable: sensibilidad de umbral a diferencias de footprint.
- Preguntas abiertas: cuatro `ratio > 1,30`; `blockCells` NT8 del outlier; valores NT8
  de score/threshold en bloques que se abstuvieron.
- Tolerancia: decisión de Nico, no aprobada por esta auditoría.

**Aporte al referente:** reduce dos hipótesis de bug sin convertir compatibilidad en
prueba causal, evita un rerun inútil y marca exactamente los tres artefactos mínimos que
faltan para que un tercero reproduzca el diagnóstico sin depender de la sesión de
Kaggle de Claude.
