# Ejecución del upload privado NQ — estado reconciliado

**Fecha:** 2026-08-28  
**Evidencia:** `OPERATOR_ATTESTED`  
**Estado:** `UPLOAD_COMPLETED_OWNER_RECONCILED_PENDING_POST_UPLOAD_REHASH`

## Dataset canónico

```text
Dataset = nicolasbuttaro/edgelab-ticks-nq-preholdout
Version = v1
Private = true_OPERATOR_ATTESTED
Files   = 8/8_OPERATOR_ATTESTED
Rows    = 119153201
Bytes   = 2265885160
Rehash  = pending
```

## Resolución del owner

La autorización original esperaba `nicodelcampo`, pero el create quedó bajo `nicolasbuttaro`. Después de registrar la desviación, el propietario eligió explícitamente aceptar `nicolasbuttaro` como custodio Kaggle canónico.

```text
OWNER_IDENTITY_RECONCILED = true
CANONICAL_OWNER           = nicolasbuttaro
```

El metadata pre-upload anterior permanece como evidencia histórica y no debe reutilizarse en futuras versiones.

## Estado científico

```text
UPLOAD_EXECUTED             = true
POST_UPLOAD_REHASH          = pending
BIGTRAP2_RERUN_AUTHORIZED   = false
BT2A_NQ_GATE1_AUTHORIZED    = false
HOLDOUT_AUTHORIZED          = false
SCIENTIFIC_RUN_AUTHORIZED   = false
```

## Aporte al referente

El upload y su owner quedan reconciliados sin alterar retroactivamente la evidencia; el próximo gate es exclusivamente el rehash post-upload.
