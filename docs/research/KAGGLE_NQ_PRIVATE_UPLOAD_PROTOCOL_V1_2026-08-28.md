# Protocolo operativo de upload privado — NQ pre-holdout

**Fecha:** 2026-08-28  
**Estado:** `AUTHORIZED_PRIVATE_UPLOAD_PENDING_EXECUTION`  
**Spec:** `specs/kaggle_nq_private_upload_v1.draft.json`  
**Upload autorizado:** `true`  
**Upload ejecutado:** `false`  
**Corrida científica autorizada:** `false`

## 1. Alcance autorizado

La directiva explícita del propietario emitida el `2026-08-28T20:40:08.393Z` autoriza únicamente crear un dataset privado nuevo desde el paquete local certificado.

```text
TOKEN            = AUTHORIZE_UPLOAD_KAGGLE_NQ_PREHOLDOUT_PRIVATE_V1
DATASET_ID       = nicodelcampo/edgelab-ticks-nq-preholdout
LOCAL_SOURCE     = E:\EdgeLab\kaggle_nq_research
MECHANISM        = KAGGLE_CLI_CREATE_ONLY
VISIBILITY       = private_only
PUBLIC_SHARING   = forbidden
```

No autoriza una nueva versión de un dataset existente, upload por web, notebook, sweep, Event Store, outcomes ni holdout.

## 2. Inventario

```text
LOCAL_ELEMENTS             = 9
FILES_SHA256_ENTRIES       = 7
FILES_SHA256_SELF_HASH     = 1
CONTROL_METADATA           = 1
REMOTE_DATA_FILES_EXPECTED = 8
```

Los ocho payloads remotos esperados son cinco Parquet, `effective_input_registry.json`, `kaggle_research_package_manifest.json` y `files.sha256`. `dataset-metadata.json` es control-plane para Kaggle CLI. Si Kaggle lo expone como archivo, debe coincidir exactamente con el metadata local y el inventario real debe registrarse como nueve.

## 3. Identidad local vinculante

```text
DATASET_METADATA_SHA256   = 2114192e9b249eea7bf2cf23a0150dc31251e95c51397174ded8f52389237ab4
FILES_SHA256_SELF_HASH    = dddd3c83bc9fee7e3bf71181b051b1c54aea28f8c7ca4eafe96a606be4401bce
EFFECTIVE_REGISTRY_SHA256 = f9bcf5eee1e68bd4797a959f7e22d3344ae383d9d33c4c59a783ef10ce35e31f
PACKAGE_MANIFEST_SHA256   = 4d1053090d80930ee7494e008148b0b8a64829568d861065e054ed2f88f91506
PARQUET_ROWS              = 119153201
PARQUET_BYTES             = 2265885160
MAX_TS_UTC_NS             = 1782856799856000000
HOLDOUT_OPEN_UTC_NS       = 1782856800000000000
STRICT_MARGIN             = 144 ms
```

## 4. Preflight runtime obligatorio

Antes de crear el dataset, el operador debe:

1. confirmar que Kaggle CLI está autenticado funcionalmente;
2. comprobar mediante consulta autenticada que el owner efectivo es `nicodelcampo`;
3. confirmar que no existe el slug exacto `edgelab-ticks-nq-preholdout`;
4. abortar si existe; no cambiar automáticamente de `create` a `version`;
5. exigir `id` exacto e `isPrivate=true` en el metadata local;
6. recalcular el hash del metadata;
7. verificar las siete entradas de `files.sha256` y su self-hash;
8. rechazar cualquier archivo local adicional.

Estados de aborto:

```text
ABSTAIN_UPLOAD_OWNER_MISMATCH
ABSTAIN_UPLOAD_SLUG_COLLISION
ABSTAIN_UPLOAD_METADATA_MISMATCH
ABSTAIN_UPLOAD_HASH_MISMATCH
ABSTAIN_UPLOAD_INVENTORY_MISMATCH
```

## 5. Comando autorizado

Si todos los preconditions pasan, queda autorizado exactamente:

```powershell
kaggle datasets create -p "E:\EdgeLab\kaggle_nq_research"
```

No queda autorizado ningún fallback a `kaggle datasets version`.

## 6. Verificación post-upload

Después del create, detener toda ejecución científica y comprobar separadamente:

```text
PROCESSING_STATUS = ready
OWNER             = nicodelcampo
SLUG              = edgelab-ticks-nq-preholdout
VISIBILITY        = private
```

`kaggle datasets status` valida procesamiento, no privacidad. La privacidad debe confirmarse mediante sesión web autenticada o API autenticada que exponga `isPrivate`.

Registrar versión, timestamp, URL privada, tamaño e inventario remoto.

Antes de cualquier kernel:

1. adjuntar el dataset únicamente a un notebook de preflight;
2. recalcular hashes de los siete payloads;
3. verificar self-hash e inventario;
4. verificar filas, bytes y `ts_max`;
5. confirmar ausencia física de holdout;
6. emitir certificación post-upload.

Si un byte difiere:

```text
FAIL_CLOSED
NO_KERNEL
NO_AUTOMATIC_RETRY
```

## 7. Rollback

Si aparece público, con owner/slug incorrecto o con inventario inesperado:

1. detener toda acción;
2. eliminar el dataset recién creado cuando corresponda;
3. registrar incidente;
4. no reintentar sin nueva ceremonia.

## 8. Separación científica

```text
KAGGLE_DATASET_BUILD_EXECUTED  = true
KAGGLE_DATASET_UPLOAD_AUTHORIZED = true
KAGGLE_DATASET_UPLOAD_EXECUTED = false
POST_UPLOAD_REHASH             = pending
BIGTRAP2_RERUN_AUTHORIZED      = false
BT2A_NQ_SWEEP_AUTHORIZED       = false
BT2A_NQ_GATE1_AUTHORIZED       = false
HOLDOUT_AUTHORIZED             = false
SCIENTIFIC_RUN_AUTHORIZED      = false
```

## Aporte al referente

El propietario autorizó exclusivamente el create privado NQ por Kaggle CLI; ejecución científica, versionado, outcomes y holdout permanecen fuera de alcance y el upload sigue pendiente de ejecución por un operador con acceso local y credenciales.
