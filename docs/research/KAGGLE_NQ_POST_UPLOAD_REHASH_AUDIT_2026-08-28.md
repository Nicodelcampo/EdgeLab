# Auditoría del dictamen post-upload NQ

**Fecha:** 2026-08-28  
**Dataset:** `nicolasbuttaro/edgelab-ticks-nq-preholdout`  
**Resultado reclamado:** `POST_UPLOAD_BYTE_REHASH = PASS`  
**Resultado aceptado:** `FAIL_CLOSED_POST_UPLOAD_CONTROL_HASH_DRIFT`

## Evidencia que sí coincide

```text
5/5 PARQUET SHA-256       = PASS
EFFECTIVE REGISTRY SHA-256 = PASS
PARQUET ROWS              = 119153201 PASS
PARQUET BYTES             = 2265885160 PASS
MAX_TS_UTC_NS             = 1782856799856000000 PASS
HOLDOUT ABSENT            = PASS_OPERATOR_ATTESTED
```

Esto demuestra que los cinco Parquet y el effective registry reportados coinciden con la evidencia de Fase 1.

## Divergencias de control

La evidencia canónica previamente versionada exige:

```text
PACKAGE_MANIFEST_SHA256 = 4d1053090d80930ee7494e008148b0b8a64829568d861065e054ed2f88f91506
FILES_SHA256_SELF_HASH  = dddd3c83bc9fee7e3bf71181b051b1c54aea28f8c7ca4eafe96a606be4401bce
```

El kernel v3 reportó:

```text
PACKAGE_MANIFEST_SHA256 = 3dd22d7e21a3bab3de4ec0c044120fa1e94f1b0bbd942fa2c02be108fde5da46
FILES_SHA256_SELF_HASH  = 0f12f20194756a178f9e7c22fde17362eaaccecde05054071856831ed9b2f7e5
```

Por tanto:

```text
CANONICAL_PAYLOAD_HASHES_MATCH = 6/7
MANIFEST_MATCH                 = false
CHECKSUM_SELF_HASH_MATCH       = false
```

No puede calificarse como bit-exact contra el build de Fase 1 mientras esas diferencias no estén explicadas y reproducidas.

## Hipótesis admisibles, no demostradas

Las diferencias podrían provenir de:

- regeneración del manifest después de cambiar el owner;
- regeneración de `files.sha256` para incluir el nuevo manifest;
- conversión de terminadores de línea;
- otra transformación de control-plane.

Ninguna hipótesis se acepta sin los bytes o contenidos exactos de ambos archivos remotos y un diff semántico contra los originales.

## Reconciliación requerida

1. descargar o imprimir íntegramente el `kaggle_research_package_manifest.json` remoto;
2. descargar o imprimir íntegramente el `files.sha256` remoto;
3. comparar el manifest remoto contra el manifest Fase 1;
4. documentar quién, cuándo y por qué lo regeneró;
5. demostrar que los cinco registros Parquet permanecen idénticos;
6. ejecutar `tools/verify_kaggle_nq_post_upload.py` desde el commit exacto que lo contiene;
7. conservar el JSON de salida sin editar.

## Path Kaggle

El path observado fue:

```text
/kaggle/input/datasets/nicolasbuttaro/edgelab-ticks-nq-preholdout
```

El notebook permite configurarlo mediante `EDGELAB_DATA_DIR`; no debe asumirse el path corto por defecto.

## Firewalls

```text
POST_UPLOAD_REHASH_PASSED       = false
CONTROL_HASH_DRIFT_RECONCILED   = false
SCIENTIFIC_FREEZE_ALLOWED       = false
BIGTRAP2_RERUN_AUTHORIZED       = false
SCIENTIFIC_RUN_AUTHORIZED       = false
```

## Aporte al referente

Los datos Parquet parecen íntegros y físicamente pre-holdout, pero el manifest y el checksum file no son bit-exact contra la evidencia versionada; el gate permanece cerrado hasta reconciliar esos bytes de control.
