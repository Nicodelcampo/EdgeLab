# Protocolo operativo de upload privado — NQ pre-holdout

**Fecha:** 2026-08-28  
**Estado actual:** `UPLOAD_COMPLETED_OWNER_IDENTITY_DEVIATION_PENDING_RECONCILIATION`  
**Spec:** `specs/kaggle_nq_private_upload_v1.draft.json`  
**Upload autorizado:** `true`  
**Upload ejecutado:** `true`  
**Post-upload rehash:** `pending`  
**Corrida científica autorizada:** `false`

## 1. Autoridad original

El propietario autorizó exclusivamente:

```text
TOKEN        = AUTHORIZE_UPLOAD_KAGGLE_NQ_PREHOLDOUT_PRIVATE_V1
EXPECTED_ID  = nicodelcampo/edgelab-ticks-nq-preholdout
MECHANISM    = KAGGLE_CLI_CREATE_ONLY
VISIBILITY   = private_only
```

No se autorizó versionado automático, upload web, notebook científico, sweep, Event Store, outcomes ni holdout.

## 2. Resultado reportado por el operador

```text
CLI_EXIT_CODE                = 0
OBSERVED_OWNER               = nicolasbuttaro
OBSERVED_SLUG                = edgelab-ticks-nq-preholdout
OBSERVED_ID                  = nicolasbuttaro/edgelab-ticks-nq-preholdout
OBSERVED_VERSION             = v1
OBSERVED_VISIBILITY          = private
UNAUTHENTICATED_ACCESS       = 404_OPERATOR_ATTESTED
REMOTE_FILES                 = 8/8_OPERATOR_ATTESTED
POST_UPLOAD_REHASH           = pending
```

## 3. Desviación vinculante

El owner observado no coincide con el owner autorizado:

```text
EXPECTED_OWNER = nicodelcampo
OBSERVED_OWNER = nicolasbuttaro
OWNER_MATCH     = false
```

Por lo tanto, el upload se registra como físicamente completado pero no como conforme con el contrato de identidad original.

```text
DEVIATION = KAGGLE_OWNER_IDENTITY_MISMATCH
PUBLIC_EXPOSURE_REPORTED = false
SCIENTIFIC_GATE = BLOCKED
```

La privacidad reportada evita clasificar el hecho como exposición pública, pero no permite sustituir retroactivamente el owner sin una decisión explícita.

## 4. Decisiones admisibles

### Opción A — aceptar el owner observado

El propietario puede declarar explícitamente que `nicolasbuttaro` es la identidad Kaggle autorizada para esta custodia. Después se debe:

1. documentar la relación de identidad;
2. actualizar el dataset ID canónico;
3. generar metadata corregido para trazabilidad futura;
4. mantener v1 privada;
5. ejecutar rehash post-upload.

### Opción B — mantener el owner original

Si el owner requerido continúa siendo `nicodelcampo`:

1. eliminar el dataset recién creado;
2. registrar el borrado;
3. corregir autenticación/metadata;
4. repetir el create bajo una nueva ceremonia;
5. no reutilizar automáticamente esta autorización.

No se ejecutará ninguna de las dos opciones sin decisión expresa.

## 5. Integridad del payload

El operador reportó:

```text
REMOTE_DATA_FILES           = 8
PARQUET_FILES               = 5
PARQUET_ROWS                = 119153201
PARQUET_BYTES               = 2265885160
MAX_TS_UTC_NS               = 1782856799856000000
HOLDOUT_OPEN_UTC_NS         = 1782856800000000000
STRICT_MARGIN               = 144 ms
```

Estos valores siguen bajo atestación hasta el rehash dentro de Kaggle. El rehash puede ejecutarse como verificación diagnóstica de custodia, pero no habilita freeze ni corrida mientras la identidad permanezca sin reconciliar.

## 6. Rehash post-upload

Sobre `/kaggle/input/edgelab-ticks-nq-preholdout/` se deben verificar los siete payloads contenidos en `files.sha256`, además de inventario, self-hash, filas, bytes, `ts_max` y ausencia física de holdout.

Resultado requerido:

```text
POST_UPLOAD_BYTE_REHASH = PASS
```

Si un byte difiere:

```text
FAIL_CLOSED
NO_KERNEL
NO_AUTOMATIC_RETRY
```

## 7. Firewalls

```text
KAGGLE_DATASET_BUILD_EXECUTED    = true
KAGGLE_DATASET_UPLOAD_AUTHORIZED = true
KAGGLE_DATASET_UPLOAD_EXECUTED   = true
OWNER_IDENTITY_RECONCILED        = false
POST_UPLOAD_REHASH               = pending
BIGTRAP2_RERUN_AUTHORIZED        = false
BT2A_NQ_SWEEP_AUTHORIZED         = false
BT2A_NQ_GATE1_AUTHORIZED         = false
HOLDOUT_AUTHORIZED               = false
SCIENTIFIC_RUN_AUTHORIZED        = false
```

## Aporte al referente

El upload privado se registra como completado, pero el cambio de `nicodelcampo` a `nicolasbuttaro` abre una desviación de identidad gate-blocking que debe resolverse explícitamente antes del freeze científico.
