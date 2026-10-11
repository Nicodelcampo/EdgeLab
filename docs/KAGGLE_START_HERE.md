# Kaggle: entrada única para cualquier agente

**Punto de descubrimiento:** `nicolasbuttaro/edgelab-data-catalog`.
El token sólo da acceso a los datasets privados: no certifica calidad ni habilita
research. El snapshot actual está **BLOCKED_FOR_RESEARCH**; sirve para descubrimiento
 y QA estructural. No hay aún un release ES/NQ certificado para uso causal.

## Contrato portable y comandos

`edgelab/kaggle/discovery.json` reúne las seis referencias versionadas, 31 archivos
con bytes/SHA, ventanas, usos permitidos, fuente en cuarentena y bloqueos con sus
criterios de resolución. Incluye los 18 primarios auditados; no todas las alternativas,
otros instrumentos ni snapshots futuros. Nunca usar `latest` o buscar por basename.

Desde el repo o una wheel instalada (sin Arrow, navegador ni token):

```bash
python -m edgelab.kaggle.discovery
python -m edgelab.kaggle.discovery --purpose research
```

El primero devuelve el plan JSON. El segundo termina con STOP y exit 2 antes de
abrir mounts. `tools/kaggle_data_entrypoint.py` es la entrada equivalente del repo.
El inventario se distribuye **en el repo/wheel**: no afirmar que es un archivo de
catalog v15 en Kaggle; una nueva versión de archivos no ha sido publicada.
La descripción del dataset ya enlaza el commit inmutable publicado por #75
(`18924be6d84303f08075825c72ba6691850ca529`). Esa publicación fue de metadata:
no creó archivos nuevos en catalog v15 ni aprobó research.
[Pendientes concretos de Kaggle y repo](ESTADO_Y_PENDIENTES.md#6-kaggle-qué-hay-y-qué-falta-exactamente).

## Descargar y adjuntar sin ambigüedad

1. Leer este contrato desde el commit de repo enlazado por el catálogo y registrar
   su SHA. No sobrescribir pins con hashes calculados de archivos desconocidos.
2. Descargar cada `version_ref` con Kaggle MCP/CLI, respetando privacidad y licencia.
   En MCP, pasar ownerSlug, datasetSlug, datasetVersionNumber explícitos y
   hasDatasetVersionNumber=true; no elegir una alternativa por parecido de nombre.
3. Adjuntar esas versiones al kernel privado/offline. La descripción de un notebook
   o un PASS de procesamiento de Kaggle no prueba que sus mounts sean correctos.
4. Crear un JSON local `mounts.json`: cada clave es la referencia versionada exacta
   del inventario y su valor es el directorio real de esa versión. No poner tokens.
5. Verificar **todos los archivos enumerados**, incluyendo bytes de parquet:

```bash
python -m edgelab.kaggle.discovery --purpose structural_qa --verify-mounts mounts.json
```

No deserializa precios ni ejecuta hipótesis; leer hashes de ~5 GB puede tardar.
Falta, hash/tamaño distintos, versión omitida, ruta fuera del mount o fallback
necesario → STOP. `PASS_INPUT_BYTES_ONLY` no es saneamiento, completitud ni permiso
para investigar. El token no se almacena, imprime ni copia al repo.

## Qué elegir hoy

- Catálogo **v15**: inventario y selección histórica, **no régimen causal aprobado**.
- Agregados **v1**, 1/30/60 s: fixtures técnicos/QA; heredan las selecciones y
  discrepancias. No asumir una serie líquida/completa porque sus sumas reconcilien.
- Cuatro fuentes raw fijadas: auditoría; NQ preholdout v6 / NQ_09-26_ticks.parquet
  tiene discrepancia sin resolver. No cambiarlo automáticamente por otra fuente.
- Loader `edgelab_data.py` v15: no usar como gate de research; sus fallbacks no
  sustituyen identidad/versión/hash ni revisión causal.

Bloqueos: [roll ES prematuro](infra/KAGGLE_ROLL_SELECTION_20261010.md),
[fuente NQ](infra/KAGGLE_FULL_RAW_AUDIT_20261010.md), calendario/huecos,
máscara retrospectiva y límites/procedencia de liquidez.

Un futuro release listo debe resolverlos con nuevas versiones y evidencia fijada,
no cambiando un booleano del inventario. Su consumidor es
`research_access.load_research_bars`, con gate previo, cobertura diaria revisada,
regímenes y límites de liquidez. [API y límites](COMPONENT_KAGGLE.md) ·
[Matriz de lectores](DATA_CONSUMER_MATRIX.md).

## MNQ / AVZVOL: revisión acotada

[Procedencia candidata](infra/AVZVOL_LINEAGE_RECOVERY_20261010.md) y
[calidad declarada/warmup/liquidez](infra/AVZVOL_MNQ_METADATA_QUALITY_20261010.md).
`tools/audit_avzvol_mnq_metadata.py` revisa JSON fijados, no raw ni outcomes.
Exit 0 no aprueba datos; devuelve `REQUIRES_SOURCE_QUALITY_REVIEW`.
No sustituye `discovery.json` por estos candidatos ni certifica mounts históricos.

La [QA física MNQ](infra/AVZVOL_MNQ_RAW_QUALITY_20261010.md) mide ahora seis
archivos candidatos fijados: SHA/bytes/filas y estructura. No reemplaza discovery,
no certifica consumo histórico ni liquidez/calendario. `PASS_RAW_STRUCTURE_ONLY`
no autoriza research. P4 económica permanece bloqueada por pedido del usuario.

La [revisión causal de selección AVZVOL](infra/AVZVOL_CAUSAL_SELECTION_REVIEW_20261010.md)
refuerza el gate de metadatos: no basta el volumen del elegido; se requieren
competidores D-1 completos y conocidos al cutoff. Es evidencia externa pendiente,
no un certificado emitido por el token, catálogo o tests. No se modificó catalog v15.

## AVZVOL: diagnóstico sintético de controles

[Guía y API descriptivos](research/AVZVOL_CONTROL_CENSUS_DIAGNOSTICS_20261010.md):
`python tools/avzvol_design_smoke.py --report control-census`. Sólo covariables
inventadas; no autorización, certificación, inferencia ni benchmark de outcomes.
P2 requiere censo/política/protocolo revisados; P4 permanece prohibida.

[AVZVOL: causalidad de zonas y controles](research/AVZVOL_ZONE_CAUSAL_REVIEW_20261010.md):
revisión de fuente fijada y ejemplos inventados. Pseudo no acredita control sin
racimo; censo as-of y política de sesiones siguen pendientes, sin outcomes nuevos.

## Uso acotado de datos disponibles, solicitado posteriormente

[Revisión descriptiva de O5 expuesto](research/AVZVOL_EXPOSED_O5_REVIEW_20261010.md): se reutilizaron los seis
exports existentes con hashes y faltantes explícitos. No es réplica ciega,
contraste incremental zone-free, certificación de raw ni promoción. No se
alteran los gates/pins pendientes de P1–P3; P4 permanece prohibida.

## Cinta causal de clasificación negativa propuesta

[Contrato y helper probado](research/AVZVOL_ZONE_NEGATIVE_TAPE_20261010.md): distingue cero zonas con calibración de
UNKNOWN por bloques/calibración/as-of faltantes. Sin zona en una ventana no
acredita ausencia de racimo ni consolidación. Sólo fixtures inventados; el censo
real, protocolo y calidad siguen pendientes. No libera gates ni P4.

## Productor de cinta y riesgo de ventana O5

[API, reproducción y auditoría](research/AVZVOL_DETECTOR_TAPE_AND_O5_BOUNDARY_20261010.md): productor del detector histórico
instrumentado, sin loaders ni estados finales. Censo real pendiente. Desfase
de una barra en el guard O5 documentado; QA acotada de etiquetas existentes no
lo descarta. No outcomes nuevos ni certificación; P4 sigue prohibida.


## Revisión O5 expuesta: no promoción del catálogo

[Robustez y sensibilidad con faltantes](research/AVZVOL_O5_ROBUSTNESS_20261010.md):
resultados descriptivos sobre seis exports fijados. No nuevos datos/kernel,
no certificación, no holdout ni economía. El filtro de extremo seleccionado no
recupera el panel completo ni acredita continuidad/reloj; no convertirlo en release.
