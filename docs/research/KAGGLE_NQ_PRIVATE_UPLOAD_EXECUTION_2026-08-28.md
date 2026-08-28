# Ejecución del upload privado NQ — reconciliación inicial

**Fecha:** 2026-08-28  
**Evidencia:** `OPERATOR_ATTESTED`  
**Estado:** `UPLOAD_COMPLETED_OWNER_IDENTITY_DEVIATION_PENDING_RECONCILIATION`

## Resultado reportado

El operador reportó creación exitosa, privada y con ocho archivos:

```text
Dataset = nicolasbuttaro/edgelab-ticks-nq-preholdout
Version = v1
Private = true
Files   = 8/8
Rows    = 119153201
Bytes   = 2265885160
Rehash  = pending
```

## Hallazgo

La autorización y el metadata pre-upload exigían:

```text
nicodelcampo/edgelab-ticks-nq-preholdout
```

El dataset observado quedó bajo:

```text
nicolasbuttaro/edgelab-ticks-nq-preholdout
```

Esto es una desviación de identidad. No se reportó exposición pública, pero la sustitución de owner no puede aceptarse retroactivamente sin una decisión explícita.

## Estado científico

```text
UPLOAD_EXECUTED             = true
OWNER_IDENTITY_RECONCILED   = false
POST_UPLOAD_REHASH          = pending
BIGTRAP2_RERUN_AUTHORIZED   = false
BT2A_NQ_GATE1_AUTHORIZED    = false
HOLDOUT_AUTHORIZED          = false
SCIENTIFIC_RUN_AUTHORIZED   = false
```

El rehash puede realizarse para verificar integridad de custodia. Freeze y ejecución científica permanecen bloqueados hasta reconciliar el owner.

## Aporte al referente

Se preservó el hecho físico del upload sin convertir una desviación de identidad en conformidad contractual; el próximo gate requiere decidir explícitamente qué owner Kaggle es canónico.
