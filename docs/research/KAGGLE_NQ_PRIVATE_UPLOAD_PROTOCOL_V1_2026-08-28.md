# Protocolo operativo de upload privado — NQ pre-holdout

**Fecha:** 2026-08-28  
**Estado:** `READY_FOR_PRIVATE_UPLOAD_AUTHORIZATION_OPERATOR_ATTESTED`  
**Spec:** `specs/kaggle_nq_private_upload_v1.draft.json`  
**Upload autorizado:** `false`  
**Upload ejecutado:** `false`

## 1. Alcance

Esta ceremonia autoriza únicamente la creación de un dataset privado nuevo a partir del paquete local ya construido. No autoriza una nueva versión de un dataset existente, upload por web, notebook, sweep, Event Store, outcomes ni holdout.

```text
DATASET_ID       = nicodelcampo/edgelab-ticks-nq-preholdout
LOCAL_SOURCE     = E:\EdgeLab\kaggle_nq_research
MECHANISM        = KAGGLE_CLI_CREATE_ONLY
VISIBILITY       = private_only
PUBLIC_SHARING   = forbidden
```

## 2. Inventario

```text
LOCAL_ELEMENTS             = 9
FILES_SHA256_ENTRIES       = 7
FILES_SHA256_SELF_HASH     = 1
CONTROL_METADATA           = 1
REMOTE_DATA_FILES_EXPECTED = 8
```

Los ocho payloads remotos esperados son cinco Parquet, `effective_input_registry.json`, `kaggle_research_package_manifest.json` y `files.sha256`. `dataset-metadata.json` es control-plane para Kaggle CLI y no se exige como payload remoto. Si Kaggle lo expone, debe coincidir exactamente con el metadata local y el inventario real debe registrarse como nueve.

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

La verificación física local permanece bajo atestación del operador hasta el rehash independiente post-upload.

## 4. Preflight runtime obligatorio

En la terminal personal de Nico, fuera del repositorio:

1. Confirmar que Kaggle CLI está disponible.
2. Ejecutar una consulta autenticada de datasets propios; `kaggle config view` por sí solo no prueba el owner.
3. Confirmar que la cuenta efectiva es `nicodelcampo`.
4. Buscar coincidencia exacta del slug `edgelab-ticks-nq-preholdout`.
5. Si existe, abortar. No cambiar automáticamente de `create` a `version`.
6. Releer el metadata local y exigir `id` exacto e `isPrivate=true`.
7. Recalcular el SHA-256 del metadata.
8. Verificar las siete entradas de `files.sha256` y su self-hash.
9. Rechazar cualquier archivo local adicional.

Estados de aborto:

```text
ABSTAIN_UPLOAD_OWNER_MISMATCH
ABSTAIN_UPLOAD_SLUG_COLLISION
ABSTAIN_UPLOAD_METADATA_MISMATCH
ABSTAIN_UPLOAD_HASH_MISMATCH
ABSTAIN_UPLOAD_INVENTORY_MISMATCH
```

## 5. Comando autorizado por esta ceremonia

Sólo después de recibir una directiva independiente que contenga el token exacto:

```text
AUTHORIZE_UPLOAD_KAGGLE_NQ_PREHOLDOUT_PRIVATE_V1
```

puede ejecutarse:

```powershell
kaggle datasets create -p "E:\EdgeLab\kaggle_nq_research"
```

La presencia del token en esta documentación no constituye autorización.

## 6. Verificación post-upload

`kaggle datasets status` valida procesamiento, no privacidad. Deben verificarse por separado:

```text
PROCESSING_STATUS = ready
OWNER             = nicodelcampo
SLUG              = edgelab-ticks-nq-preholdout
VISIBILITY        = private
```

La privacidad se confirma mediante sesión web autenticada o API autenticada que exponga `isPrivate`. Registrar versión, timestamp, URL privada, tamaño e inventario remoto.

Antes de cualquier kernel:

1. adjuntar el dataset únicamente a un notebook de preflight;
2. recalcular hashes de los siete payloads;
3. verificar self-hash e inventario;
4. verificar filas, bytes y `ts_max`;
5. confirmar ausencia física de holdout;
6. emitir una certificación post-upload.

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

El borrado es mitigación de emergencia, no sustituto de la verificación previa de privacidad.

## 8. Firewalls

```text
KAGGLE_DATASET_BUILD_EXECUTED  = true
KAGGLE_DATASET_UPLOAD_EXECUTED = false
BIGTRAP2_RERUN_AUTHORIZED      = false
BT2A_NQ_SWEEP_AUTHORIZED       = false
BT2A_NQ_GATE1_AUTHORIZED       = false
HOLDOUT_AUTHORIZED             = false
SCIENTIFIC_RUN_AUTHORIZED      = false
```

## Aporte al referente

El upload privado NQ queda formalizado como create-only por Kaggle CLI, con owner y colisión verificados en runtime, privacidad separada del estado de procesamiento y rehash obligatorio antes de cualquier kernel.
