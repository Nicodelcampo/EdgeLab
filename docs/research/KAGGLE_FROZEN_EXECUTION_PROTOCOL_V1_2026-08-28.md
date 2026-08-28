# Protocolo de Ejecución Congelada en Kaggle/Cloud V1

**Estado:** `INFRASTRUCTURE_PREPARED_PRIVATE_CUSTODY_APPROVED_RUN_NOT_AUTHORIZED`  
**Holdout:** trade dates `20260701–20261231`; apertura física `2026-06-30T22:00:00Z`.  
**North Star:** `d85364e21951980c0e9273ed1883ce14413db157052162ed38ac9ab2403375a1`.

## Decisión

Las próximas corridas pesadas pueden ejecutarse en Kaggle u otro notebook cloud. La plataforma cambia; la hipótesis, el spec, el kernel y los firewalls no. No se promete una duración de 15–30 minutos: CPU, RAM, cuotas e I/O se registran por corrida y el speedup se acepta sólo después de un benchmark reproducible.

## Reglas obligatorias

1. **Custodia privada aprobada no equivale a redistribución.** `docs/research/DATA_LICENSE_DECISION.md` está `APPROVED` por directiva del propietario sólo para datasets privados y cómputo de EdgeLab. La visibilidad pública, compartir con terceros y licencias abiertas siguen prohibidos.
2. **Los Parquet crudos que cruzan julio no son inputs de research cloud.** El dataset privado histórico contiene holdout y queda clasificado como `raw_custody`. Para una campaña exploratoria se construye localmente un paquete físicamente pre-holdout. El manifest del paquete conserva los hashes de los archivos fuente y registra hashes nuevos para cualquier recorte.
3. **La licencia no autoriza una corrida científica.** Cada ejecución conserva freeze propio, commit exacto, token de campaña y attestation post-run.

## Arquitectura de dos freezes

### Freeze A — paquete de datos

1. Verificar cada fuente contra `docs/datos_manifiesto.json` y el input registry de la campaña.
2. Verificar bytes y SHA-256 completos; ningún archivo puede faltar o saltarse con warning.
3. Recortar localmente cualquier archivo que cruce `1782856800000000000 ns`.
4. Emitir:
   - `kaggle_research_package_manifest.json`;
   - `effective_input_registry.json`;
   - `files.sha256`;
   - `dataset-metadata.json` con `isPrivate=true`;
   - Parquet físicamente pre-holdout.
5. Congelar el SHA-256 físico del manifest en el spec de ejecución.

Preflight NQ de ejemplo:

```powershell
python tools/prepare_kaggle_research_dataset.py `
  --preflight-only `
  --input-registry specs/bt2a_gate1_nq_all5_input_registry_2026-08-27.json `
  --source-dir E:/EdgeLab/data/nt8/NQ_parquet `
  --output-dir E:/EdgeLab/kaggle_nq_research `
  --dataset-id nicodelcampo/edgelab-ticks-nq-preholdout
```

La custodia privada ya está aprobada. La construcción efectiva del paquete sigue requiriendo el token operativo separado:

```text
AUTHORIZE_BUILD_KAGGLE_RESEARCH_DATASET_V1
```

El tool **no sube** datos. Después de un `COMPLETE_PRIVATE_RESEARCH_PACKAGE`, la carga se hace explícitamente como dataset privado. Nunca versionar credenciales ni pegarlas en notebooks.

### Freeze B — campaña de cómputo

Copiar `specs/kaggle_frozen_execution_v1.template.json` a un archivo propio de la campaña y congelar:

- commit Git completo de 40 caracteres;
- SHA físico del package manifest;
- SHA del registry fuente y de `datos_manifiesto`;
- argv exacto, sin shell;
- kernel/blob y parámetros efectivos en el spec científico de la campaña;
- estrategia de paralelismo y orden determinista de merge;
- outputs obligatorios;
- token único de ejecución.

`DRAFT_TEMPLATE_NOT_EXECUTABLE` pasa a `FROZEN_PREFLIGHT_READY` sólo cuando todos los placeholders fueron reemplazados y `run_capability=true` fue aprobado formalmente.

## Paralelismo

No se paraleliza “por contrato o sesión” por defecto.

- Un sweep puramente independiente puede usar `config_id × contract` si cada worker lee una ventana físicamente acotada, no comparte estado y el merge está ordenado.
- Un builder con estado encadenado entre sesiones o contratos debe permanecer serial. En particular, el `SessionProfile` AVol cruza sesiones; dividirlo por contrato sin checkpoint inicial certificado cambia la semántica.
- `max_workers>1` exige `safe_partition_key` congelada. El harness aborta si falta.
- BLAS/OMP queda en un thread por worker para evitar oversubscription.

## Notebook

`notebooks/kaggle/10_frozen_job_runner.py`:

1. clona/fetchea el commit exacto y hace checkout detached;
2. comprueba `HEAD`;
3. ejecuta preflight por defecto;
4. sólo corre con `EDGELAB_EXECUTE=1` y token;
5. llama al envelope `tools/run_kaggle_frozen_job.py`.

Variables requeridas:

```text
EDGELAB_EXPECTED_COMMIT=<40 hex>
EDGELAB_EXECUTION_SPEC=specs/<campaign>.json
EDGELAB_DATA_DIR=/kaggle/input/<private-dataset>
EDGELAB_EXECUTE=0
```

En la ceremonia de ejecución:

```text
EDGELAB_EXECUTE=1
EDGELAB_AUTHORIZATION_TOKEN=<token congelado de la campaña>
```

## Evidencia descargable

Una corrida autorizada emite:

- `run_status.json` con `head_start`, `head_end`, dirty state y recursos observados;
- stdout/stderr completos;
- `execution_attestation.json` con acceso real a future path, first touch, P&L y holdout;
- resultados y checkpoints del runner científico;
- `artifact_manifest.json` con bytes y SHA-256 por archivo;
- `/kaggle/working/output.zip` determinista;
- `/kaggle/working/output.zip.sha256`.

La descarga no autoriza publicación. Localmente:

1. verificar el SHA del ZIP;
2. extraer en un directorio nuevo;
3. verificar `artifact_manifest.json`;
4. correr la suite contractual específica de la campaña;
5. comparar conteos/hashes contra checkpoints;
6. recién entonces publicar artefactos pequeños; Parquet/runs grandes permanecen gitignoreados salvo decisión expresa.

## Gates de aceptación

```text
PRIVATE_CLOUD_CUSTODY_APPROVED        = true
DATASET_VISIBILITY                    = private_only
PUBLIC_OR_THIRD_PARTY_SHARING         = forbidden
SOURCE_BYTES_AND_SHA256               = exact
RESEARCH_DATASET_HOLDOUT_PRESENT      = false
CODE_HEAD_START_EQUALS_END            = true
CODE_DIRTY                            = false
SHELL_EXECUTION                       = false
PARALLEL_PARTITION_PROVEN_SAFE        = required_if_workers_gt_1
OUTPUT_MANIFEST_COMPLETE              = true
LOCAL_PUBLICATION_TESTS               = PASS
CLOUD_RESULT_AUTOMATICALLY_ACCEPTED   = false
```

## Estado actual

```text
KAGGLE_CLOUD_INFRA_PREPARED = true
KAGGLE_PRIVATE_CUSTODY      = APPROVED
KAGGLE_DATASET_BUILD        = READY_NOT_EXECUTED
KAGGLE_RESEARCH_RUN         = false
HOLDOUT_AUTHORIZED          = false
OUTCOMES_AUTHORIZED         = false
```

## Aporte al referente

El cómputo cloud queda habilitado como custodia privada y medio reproducible, sin transformar esa aprobación en permiso para abrir holdout, outcomes o campañas no congeladas.
