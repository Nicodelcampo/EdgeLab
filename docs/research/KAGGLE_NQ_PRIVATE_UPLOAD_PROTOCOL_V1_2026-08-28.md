# Protocolo operativo de upload privado — NQ pre-holdout

**Fecha:** 2026-08-28  
**Estado:** `UPLOAD_COMPLETED_OWNER_RECONCILED_PENDING_POST_UPLOAD_REHASH`  
**Dataset canónico:** `nicolasbuttaro/edgelab-ticks-nq-preholdout`  
**Upload ejecutado:** `true`  
**Owner reconciliado:** `true`  
**Post-upload rehash:** `pending`  
**Corrida científica autorizada:** `false`

## 1. Historial de autoridad

La autorización original permitió exclusivamente un create privado. El upload terminó bajo `nicolasbuttaro`, mientras el metadata original esperaba `nicodelcampo`. La diferencia fue registrada como desviación y el propietario decidió explícitamente aceptar `nicolasbuttaro` como custodio Kaggle canónico.

Autoridades:

- `docs/research/KAGGLE_NQ_PRIVATE_UPLOAD_AUTHORIZATION_2026-08-28.md`;
- `docs/research/KAGGLE_NQ_PRIVATE_UPLOAD_EXECUTION_2026-08-28.md`;
- `docs/research/KAGGLE_NQ_PRIVATE_UPLOAD_OWNER_RESOLUTION_2026-08-28.md`.

## 2. Estado remoto reportado

```text
DATASET_ID                  = nicolasbuttaro/edgelab-ticks-nq-preholdout
VERSION                     = v1
VISIBILITY                  = private_OPERATOR_ATTESTED
UNAUTHENTICATED_ACCESS      = 404_OPERATOR_ATTESTED
REMOTE_FILES                = 8/8_OPERATOR_ATTESTED
OWNER_IDENTITY_RECONCILED   = true
POST_UPLOAD_REHASH          = pending
```

## 3. Integridad esperada

```text
PARQUET_FILES               = 5
PARQUET_ROWS                = 119153201
PARQUET_BYTES               = 2265885160
MAX_TS_UTC_NS               = 1782856799856000000
HOLDOUT_OPEN_UTC_NS         = 1782856800000000000
STRICT_MARGIN               = 144 ms
FILES_SHA256_ENTRIES        = 7
FILES_SHA256_SELF_HASH      = dddd3c83bc9fee7e3bf71181b051b1c54aea28f8c7ca4eafe96a606be4401bce
EFFECTIVE_REGISTRY_SHA256   = f9bcf5eee1e68bd4797a959f7e22d3344ae383d9d33c4c59a783ef10ce35e31f
PACKAGE_MANIFEST_SHA256     = 4d1053090d80930ee7494e008148b0b8a64829568d861065e054ed2f88f91506
```

## 4. Metadata histórico

El metadata local original con ID `nicodelcampo/...` queda preservado como evidencia pre-upload, no como metadata canónico futuro. No se cambia retroactivamente su hash.

Para futuras versiones o recreaciones, el ID debe ser:

```text
nicolasbuttaro/edgelab-ticks-nq-preholdout
```

## 5. Próximo gate — rehash post-upload

Sobre `/kaggle/input/edgelab-ticks-nq-preholdout/`:

1. verificar inventario remoto;
2. verificar las siete entradas de `files.sha256`;
3. verificar el self-hash de `files.sha256`;
4. recomputar filas y bytes de los cinco Parquet;
5. recomputar `ts_max`;
6. confirmar ausencia física de holdout;
7. emitir certificación post-upload.

Resultado requerido:

```text
POST_UPLOAD_BYTE_REHASH = PASS
```

Si cualquier valor difiere:

```text
FAIL_CLOSED
NO_KERNEL
NO_AUTOMATIC_RETRY
```

## 6. Firewalls

```text
KAGGLE_DATASET_BUILD_EXECUTED    = true
KAGGLE_DATASET_UPLOAD_AUTHORIZED = true
KAGGLE_DATASET_UPLOAD_EXECUTED   = true
OWNER_IDENTITY_RECONCILED        = true
POST_UPLOAD_REHASH               = pending
BIGTRAP2_RERUN_AUTHORIZED        = false
BT2A_NQ_SWEEP_AUTHORIZED         = false
BT2A_NQ_GATE1_AUTHORIZED         = false
HOLDOUT_AUTHORIZED               = false
SCIENTIFIC_RUN_AUTHORIZED        = false
```

## Aporte al referente

El owner observado queda reconciliado como custodio canónico; el único siguiente gate permitido es el rehash post-upload, sin autorización científica implícita.
