# Kaggle spec v2 — primera implementación de infraestructura

## Alcance y estado

Rama aislada: `infra/kaggle-spec-framework-v2-20261009`. Base de integración leída: `foundation/f0b-compatibility-probe@617064e0b86fd2490f2834b5da731cd26aaa23ea`.

Esto implementa un primer camino común para **preflight y materialización de agregados**, no un motor universal de contraste de papers. No modifica specs históricos, el runner v1, datos publicados, costos, hipótesis económicas ni autorizaciones. No abre resultados futuros/P&L. El adaptador verificado registra únicamente evidencia técnica en el Hipocampo durable existente: episodios no adjudicados y outcomes=False, nunca trials ni aprobaciones.

## Hecho

- `tools/kaggle_spec_v2.py`: spec JSON validada, selección por catálogo fijado, generación de scripts autocontenidos sin `git clone`, metadata privada e internet desactivado.
- Contrato indivisible; reparto determinista por cantidad de sesiones entre hasta `max_shards` kernels. No reparte un mismo contrato entre dos kernels.
- Primarios únicamente; ninguna alternativa silenciosa, ningún `EDGELAB_ALLOW_MISSING`. Verifica todos los paths del shard antes de leer ticks; admite layout plano y `/kaggle/input/datasets/<owner>/<slug>/...`.
- Una pasada por los row groups relevantes de cada archivo dentro de cada shard; calcula a la vez 1 s, 30 s y 60 s. Selecciona exclusivamente las sesiones aprobadas y el contrato que determina el resolver.
- OHLC/último precio en **price_ticks**, trades, volumen total, comprador, vendedor, sin clasificar y firmado (`buy - sell`). Bid/ask de la última ejecución: un valor ausente queda ausente, nunca se sustituye con una cotización anterior.
- Cada barra publica `available_utc_ns = bucket_end`. No se puede usar el cierre/volumen final de una barra como si se conociera dentro de ella. No rellena barras vacías ni cruza sesiones o contratos.
- Conservación exacta de trades/volumen por sesión entre ticks, barras y totales del catálogo fijado. Un parquet truncado o de otra identidad no pasa por casualidad sólo porque sus agregados sean autoconsistentes.
- `results.json`, `attestation.json`, `plan.json`, manifest de archivos y `output.zip` con `output.zip.sha256`, tanto para éxito como para fallos atrapados durante la ejecución. No declara `holdout_touched=false` cuando no pudo comprobar el firewall.
- Unión con orden fijo y verificación de hashes, plan, identidad del runner, shards completos, ausencia de duplicados, cobertura exacta de sesiones y attestation.
- `load_bars`: consumidor del almacén unido, con hashes y cobertura; no reduce una muestra si falta una sesión ni inventa cobertura fuera de la ventana materializada.

## Firewall vigente

Se usa HOLDOUT-A3, primera **fecha de sesión** sellada `2026-10-01`. Para índices, la barrera UTC se deriva de `2026-09-30 17:00 America/Chicago`, no del número ns obsoleto de CURRENT ni de medianoche UTC.

Antes de deserializar un row group, el runner exige estadísticas de timestamp y rechaza grupos relevantes que contengan cualquier timestamp desde esa barrera. Si un grupo mezcla preholdout y holdout, **ABSTAIN**: no se lee para filtrarlo después. Los grupos fuera del rango solicitado se omiten sólo por sus metadatos. La fecha de sesión de filas autorizadas se calcula con la función del loader v15, no con otra convención introducida aquí.

El veredicto es `PASS_INTEGRITY_NOT_EDGE`: no significa señal predictiva, rentabilidad ni permiso para usar abr–sep como replicación. Las autorizaciones de campañas siguen fuera de este módulo.

## Identidades congeladas

Catálogo `nicolasbuttaro/edgelab-data-catalog/15`:

- `edgelab_data.py`: `0211e190f64437e20e5cdee3523fc86b155240b3613d7ed48767da73982cb3e8`
- `RESOLVER.json`: `9b21eeff751d4397465fcc6831ea615b7dd401a5605a5997f52c8bfd9248117c`

La spec exige referencias `owner/slug/version`. El manifest declara explícitamente que la identidad raw es el pin de versión y que **no se calculó sha256 completo de cada parquet**: no se disfraza tamaño/path de hash de contenido. Los hashes de código, catálogo y salidas sí se calculan. El commit de base explica procedencia; el hash del runner embebido identifica el código real, no se afirma que Kaggle corrió un árbol git limpio.

## Prueba pequeña con catálogo real

`specs/kaggle/aggregates_smoke_v2_20261009.json` selecciona exclusivamente `2026-01-05` (descubrimiento), ES y NQ. La generación local resolvió:

| Shard | Contrato | Fuente primaria | Archivo |
|---|---|---|---|
| k01 | ES_03-26 | edgelab-nt8-historical-missing-20261001 v1 | ES_03-26_ticks_ext.parquet |
| k02 | NQ_03-26 | edgelab-nt8-historical-missing-20261001 v1 | NQ_03-26_ticks_ext.parquet |

**Actualización tras acceso autorizado al navegador:** los dos kernels v2 se ejecutaron con datos reales y terminaron COMPLETE / `PASS_INTEGRITY_NOT_EDGE`. ES: 832.580 trades, volumen 1.195.973; NQ: 421.020 trades, volumen 453.961. Es conservación de datos, no resultado económico.

Outputs descargados vía custom MCP; hashes de ambos zips verificados contra los sidecars. Merge de k01+k02 PASS y lectura de los seis archivos con `load_bars` PASS. Ejecuciones: ES 356881769, NQ 356881572. Esta evidencia cubre **una sola sesión por instrumento**, no la cobertura histórica completa ni un benchmark de aceleración.

```bash
python tools/kaggle_spec_v2.py generate \
  --spec specs/kaggle/aggregates_smoke_v2_20261009.json \
  --catalog /ruta/al/catalogo-v15 --out /ruta/generados

# Cada directorio generado tiene entry.py y kernel-metadata.json.
# El CLI oficial admite dataset_sources con owner/slug/version.
# La publicación/ejecución consume recursos: primero revisar metadata y mounts.
kaggle kernels push -p /ruta/generados/k01
kaggle kernels push -p /ruta/generados/k02

# Descomprimir/verificar cada output.zip antes de unir; nunca mezclar campañas.
python tools/kaggle_spec_v2.py merge --plan /ruta/k01/evidence/plan.json \
  --inputs /ruta/k01/evidence /ruta/k02/evidence --out /ruta/store
```

Para sólo comprobar inputs, cambiar `mode` a `preflight` antes de generar el plan. Un plan modificado luego de generarse se rechaza contra el resolver/spec.

## Pruebas y evidencia

Suite sintética: `tests/infra/test_kaggle_spec_v2.py`, **29 pruebas locales PASS** (26 del armazón + 3 del adaptador durable). Incluye división de una barra entre row groups, última cotización nula, conservación, hash incorrecto, fuente truncada, holdout mixto, ausencia de estadísticas, mounts faltantes, plan adulterado, reparto por contrato, cobertura del consumidor y unión incompleta/duplicada/adulterada. La prueba de holdout usa timestamps fabricados, no datos de mercado sellados.

Kernel de prueba privada, offline, exclusivamente sintética:
`https://www.kaggle.com/code/nicolasbuttaro/edgelab-framework-v2-synthetic-20261009`.

**Kaggle v2: COMPLETE, 25 pruebas PASS en 4,24 s, sin lectura de datos de mercado reales.** Ver `KAGGLE_SPEC_V2_EVIDENCE_20261009.json` para evidencia comprobada.

## Adjuntos: workaround verificado, MCP aún sin resolver

Prueba privada `https://www.kaggle.com/code/nicolasbuttaro/edgelab-mount-verified-20261009`.

El MCP devolvió un kernel/version guardado, pero el reporte v1 mostró `catalog_mounts=[]` e `inputs=[]` al enviar `datasetDataSources` y su setter con la referencia del catálogo. La variante de ID numérico v2 tampoco montó nada; ese formato no debe recomendarse porque el cliente oficial documenta refs, no IDs. Se probó después la referencia oficial **con versión**. La v3 también terminó en ERROR con `catalog_mounts=[]` e `inputs=[]`; el reporte se descargó y leyó (ejecución 356878011). El estado final figura en el JSON de evidencia.

**Workaround comprobado:** en la interfaz se agregó el dataset con Add Input → búsqueda por URL → Add Dataset → Save & Run All. La prueba v4 terminó COMPLETE y leyó `/kaggle/input/datasets/nicolasbuttaro/edgelab-data-catalog/edgelab_data.py` con el hash esperado. El mismo procedimiento agregó catálogo v15 y fuente histórica v1 a ambos kernels ES/NQ. El custom MCP se mantuvo como vía para crear kernels, consultar estado y obtener URLs de descarga de los outputs. Esperar la confirmación del commit antes de navegar fuera del editor.

No hay pruebas suficientes para atribuir el fallo de adjuntos por MCP a permisos, a Kaggle, a un serializador o a un campo concreto del conector. Guardar un kernel no demuestra que los inputs estén adjuntos. No se usa una URL firmada como input permanente ni una descarga de internet como sustituto de ejecución congelada.

## Pendiente, sin afirmar completado

1. **Smoke ES/NQ y workaround de mounts: cerrados.** Resolver todavía los adjuntos directamente por MCP o CLI oficial para no depender del navegador en cada kernel.
2. Ampliar la paridad contra el loader, medir tiempo/memoria y cobertura sobre datos reales; conservación por sesión y consumidor ya pasaron, todavía no hay medición de aceleración.
3. Materializar la cobertura completa y publicar un **dataset privado de agregados**. No se publicó ninguno en esta tanda; el MCP expuesto no tiene creación/versionado integral de datasets.
4. Añadir adaptadores de hipótesis/métricas/reglas económicas, con aprobación humana y autorización independiente de outcomes.
5. **Adaptador durable cerrado y smoke ingerido:** `tools/kaggle_hippocampus_ingest.py` valida el almacén inmutable antes de escribir, usa el mismo lock del store de producción, conserva la cadena previa y evita duplicados. El smoke creó cinco registros verificados; la corrida histórica aún está en curso.
6. Añadir lanzamiento/polling/descarga de k kernels; hoy se generan kernels y se unen sus outputs, no se ofrece un scheduler completo.

## Aporte al referente

Reduce duplicación de infraestructura y hace verificables inputs/sesiones, agregados y evidencia sin convertir un PASS técnico en un edge ni gastar holdout. El mount real y el smoke de una sesión ES/NQ quedaron verificados sin internet; los adjuntos vía MCP y la materialización histórica completa siguen pendientes.

## Corrida histórica y continuidad durable

Spec `aggregates_es_nq_full_v2_20261009.json`: 521 sesiones aprobadas (ES 243, NQ 278), cuatro shards por contrato. Las fechas solicitadas 2025-07-01..2026-09-30 no implican continuidad de mercado: el resolver selecciona ES 2025-07-18..2026-09-25 y NQ 2025-08-04..2026-09-25. Las sesiones ausentes no se inventan.

El consumidor de evidencia verifica manifest, attestation y cobertura antes de anexar cinco registros (episode, expectation, step, success, lesson) al Hipocampo. Éxito técnico permanece UNADJUDICATED; lesson PROPOSED/LOW, outcomes=False. El recibo queda fuera del almacén inmutable. Se conserva cada ancla anterior en ANCHORS.json y se agrega una nueva, sin cambiar hashes históricos.

### Formato de agresor reexportado

La primera tanda histórica v2: k01 PASS; k02/k03/k04 ABSTAIN por etiqueta no contemplada. Diagnóstico privado `edgelab-aggressor-diagnostic-20261010` v2 leyó sólo agresor de row groups con timestamps demostrablemente anteriores al holdout; confirmó `unknown` (6 filas en el primer row group de NQ_09-25). `unknown` se conserva como unknown_volume y aporta cero al volumen firmado, igual que neutral/unclassified. Otras etiquetas no previstas siguen fallando con el listado explícito. Una nueva prueba confirma trades/volumen y signo; los cuatro shards se regeneraron con el mismo hash de runner. No se mezcla el k01 viejo con la nueva tanda.
