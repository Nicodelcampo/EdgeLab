# AVZVOL: cobertura declarada y liquidez MNQ

**REQUIRES_SOURCE_QUALITY_REVIEW. No hay certificación de raw, calendario, reloj,
liquidez, consumo histórico ni ausencia de sesgo.**
Base revisada: `e1c8cb13ff2b31d2fece93b1c16bec76dfb9452b`.
[Registro para agentes](../../config/research/avzvol_mnq_metadata_review_20261010.json).
Complementa la [recuperación de procedencia](AVZVOL_LINEAGE_RECOVERY_20261010.md).
Alcance: los seis contratos MNQ candidatos de AVZVOL. Sin otras campañas.

## Comprobaciones realizadas, y su alcance exacto

Se descargaron por versión explícita los seis `_sessions_ext.json`, los tres
manifiestos canonical y `catalog.json` v15. Se conservaron SHA de los documentos,
no credenciales ni URLs firmadas. El grano es una etiqueta de fecha de fuente
por contrato; no una sesión del exchange certificada. El profiler genérico
transpone estos JSON: no se usaron sus estadísticas de floats ni ese grano erróneo.
El checker parsea enteros nativos, valida fechas/campos/rangos y rechaza claves
JSON duplicadas.

- **261 sesiones aprobadas** del resolver candidato tienen resumen de fuente y
  conteo de trades coincidente: cero ausentes y cero discrepancias de conteo.
  Se recomprobó por un segundo recorrido directo independiente del checker.
- La suma de `ticks` de cada uno de los seis documentos concuerda con las filas
  declaradas en su manifiesto de productor. Para canonical también con
  `AUDIT_MANIFEST.json`. Se verificaron hashes de los documentos de sesiones y
  manifiestos contra `files.sha256` canonical.
- Es concordancia de **declaraciones**: no un escaneo físico de parquets, una
  comprobación de quotes ni continuidad upstream. Un hueco intrasesión puede
  existir aunque todos los totales coincidan. No se inventó un umbral de gap.

## Hallazgo 1: aprobar las fechas de eventos no protege el warmup

En el source v1 fijado, `run_contract` carga el rango completo, construye barras
con él y llama a `zp2_run` **antes** de calcular `appr = isin(...)`. Las fechas
rechazadas y anteriores a las primeras fechas aprobadas no quedan fuera del
input del detector por esa máscara posterior. El tamaño/efecto de esa exposición
NO se cuantificó: no se ejecutaron precios ni se recalcularon outcomes.

El inicio pedido es el midnight Chicago de la primera sesión aprobada menos
**45 días absolutos**. La revisión conserva la aritmética histórica, incluso
al atravesar DST; no la reemplaza por 45 fechas locales.

Ejemplos de lo que declaran los metadatos candidatos:

- MNQ 09-25: el rango se pide desde `2025-06-20T05:00:00Z`, pero la primera
  observación declarada es `2025-08-01T20:00:00.008Z`. No hay evidencia declarada
  para la parte inicial de ese warmup. No se cuenta ese intervalo como sesiones
  abiertas: falta el calendario aplicable. El mínimo del documento de compresión
  concuerda con el primer timestamp de la fuente; no se certifica raw por ello.
- MNQ 12-25: el inicio pedido es `2025-08-03T05:00:00Z`; la primera observación
  declarada es `2025-09-11T03:00:34.052Z`. También requiere decisión explícita sobre
  disponibilidad/historia de ese contrato antes de permitirle alimentar umbrales.

Otros resúmenes pueden intersectar el límite de warmup: su primer/último tick
no permite saber cuántos ticks quedaron dentro del filtro. El checker conserva
ese límite y no llama «cobertura completa» a un cero de leading-absence. Las
etiquetas extra en la ventana son candidatos a revisar, NO un conteo medido de
sesiones que alteraron el detector.

No se imputó historia, rellenó ticks, desplazó fechas ni reparó thresholds.
Si la revisión de método cambia warmup, censura o universo, es una identidad
nueva de desarrollo; no una actualización silenciosa del resultado original.

## Hallazgo 2: la máscara publicada de liquidez no acredita causalidad

Las reglas de `RESOLVER.json` v15 declaran elegibilidad con una fracción de la
mediana del contrato y exclusión por una fracción de la mediana del líder de
**TODO el instrumento**; también usan minutos típicos de la muestra y conflictos
agregados de fuentes. No declaran un cutoff histórico por decisión ni ventanas
as-of que permitan certificar esa máscara como causal. La concordancia de sus
filas aprobadas no subsana este problema de selección.

Se exige reconstrucción/documentación del builder realmente usado y comparación
con una política ex-ante congelada, sin outcomes para elegirla. No se afirma que
se midió el tamaño del sesgo en AVZVOL ni que toda regla retrospectiva cambie cada
resultado. No se traslada la anomalía del roll ES a MNQ.

Los cinco rolls MNQ de catalog v15 declaran fechas previas de lunes a viernes y
volúmenes old/new positivos. Eso no repite el caso dominical de ES en estos cinco
registros; **no es certificación**: los resúmenes descargados no traen volumen
por sesión, complete-session ni un censo verificado de todos los challengers.
No se comprobó por raw que ese D-1 estuviera completo y realmente fuera la
fuente/version elegida. Feriados, clocks y causalidad siguen pendientes.

## Hallazgo 3: no confundir hash anterior con parquet recomprimido

Los tres manifiestos canonical por contrato conservan un SHA de parquet distinto
del SHA publicado en `AUDIT_MANIFEST.json`/`files.sha256`. El audit declara
recompresión `zstd:19`, tamaños originales/comprimidos y el mismo número de filas.
Se registran ambos hashes, sin usar el anterior como pin del contenedor actual.

Esto explica una diferencia documental compatible con recompression; **no se
verificó equivalencia semántica de los bytes raw** y no se clasificó como corrupción
sólo por SHA distinto. Tampoco se cambió el pin de candidatos de la recuperación
anterior. Los manifiestos re-export declaran NO_DATA y conservación de fuente
vieja: no convertir fechas locales NT8 en trade dates CME sin revisar el conversor.

## Checker reutilizable por cualquier agente

`tools/audit_avzvol_mnq_metadata.py` usa sólo stdlib, JSON y hashes de documentos.
No importa loaders, Arrow, motor ni módulos del bundle; no lee parquets, red,
ticks/precios ni outcomes. El índice local tiene una fila por contrato:

```json
[{"contract":"MNQ_09-25","path":"/ruta/local/canonical.v1.MNQ_09-25_sessions_ext.json","sha256":"SHA_MEDIDO_DEL_DOCUMENTO"}]
```

Se requieren los seis contratos/archivos fijados, no sólo el ejemplo anterior:

```bash
python tools/audit_avzvol_mnq_metadata.py \
  --resolver /ruta/catalog.v15.RESOLVER.json \
  --catalog /ruta/catalog.v15.catalog.json \
  --lineage config/research/avzvol_lineage_candidates_20261010.json \
  --sessions-index /ruta/sessions-index.json \
  --out /ruta/metadata-review-private.json
```

**Exit 0 sólo significa revisión de metadatos completada** y el estado es
`REQUIRES_SOURCE_QUALITY_REVIEW`; todos los flags de aprobación permanecen false.
Exit 2 = STOP por input mal formado/hash distinto. Las ausencias y discrepancias
se conservan en el informe, no se corrigen ni habilitan research. El detalle por
fecha queda privado; el snapshot público contiene conteos y hashes, no calendarios
raw, rutas privadas ni precios.

## Lo necesario para cerrar, sin cambiar la historia

1. Verificar bytes/footer/estructura de los seis raw candidatos y mapear continuidad
   en todo el rango leído, incluidos warmup y fechas no aprobadas. Es QA, no permiso
   automático de inferencia; definir calendario aplicable antes de clasificar huecos.
2. Recuperar zona horaria, conversor/exportador, originales/logs y evidencia
   independiente de clocks y calidad de quotes. Los intervalos sin evidencia quedan
   UNKNOWN, no cero, y no se reparan inventando trades.
3. Revisar D-1 completo con todos los contratos competidores; congelar reglas
   as-of de liquidez/roll/elegibilidad y warmup antes de generar un resolver nuevo.
4. Publicar fuentes/resolver/agregados versionados con aprobación separada, registro
   de exposición y mandato específico de revisión del método. Si el montaje
   histórico no es verificable, preservarlo así; una nueva attestation no lo repara.

R7/K8 siguen abiertos. La spec incremental conserva `reviewed_input_pins`,
`source_quality_review_refs` y `match_policy` en null. Este lote no modifica
outputs, ledgers, O5, holdout, ccbus ni planificación autónoma local.
