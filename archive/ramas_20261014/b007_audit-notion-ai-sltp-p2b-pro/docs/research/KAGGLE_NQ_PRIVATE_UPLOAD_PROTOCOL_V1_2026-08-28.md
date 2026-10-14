# Protocolo operativo de upload privado — NQ pre-holdout

**Estado:** `POST_UPLOAD_REHASH_FAIL_CLOSED_CONTROL_HASH_DRIFT`  
**Dataset canónico:** `nicolasbuttaro/edgelab-ticks-nq-preholdout`  
**Upload ejecutado:** `true`  
**Owner reconciliado:** `true`  
**Post-upload rehash:** `fail_closed_control_hash_drift`  
**Corrida científica autorizada:** `false`

## Evidencia aceptada

```text
PARQUET_FILES             = 5
PARQUET_ROWS              = 119153201
PARQUET_BYTES             = 2265885160
MAX_TS_UTC_NS             = 1782856799856000000
HOLDOUT_OPEN_UTC_NS       = 1782856800000000000
STRICT_MARGIN             = 144 ms
PARQUET_HASHES_MATCH      = 5/5_OPERATOR_ATTESTED
EFFECTIVE_REGISTRY_MATCH  = true_OPERATOR_ATTESTED
```

## Drift de control

```text
PHASE1_MANIFEST_SHA256 = 4d1053090d80930ee7494e008148b0b8a64829568d861065e054ed2f88f91506
CLOUD_MANIFEST_SHA256  = 3dd22d7e21a3bab3de4ec0c044120fa1e94f1b0bbd942fa2c02be108fde5da46
PHASE1_FILES_SELF_HASH = dddd3c83bc9fee7e3bf71181b051b1c54aea28f8c7ca4eafe96a606be4401bce
CLOUD_FILES_SELF_HASH  = 0f12f20194756a178f9e7c22fde17362eaaccecde05054071856831ed9b2f7e5
```

El reporte de `7/7 PASS` usa como esperado el hash remoto nuevo del manifest, no el hash canónico registrado en Fase 1. Contra la evidencia versionada, el resultado es `6/7` más self-hash distinto.

## Próximo gate

Entregar ambos archivos de control remotos, producir diff semántico y rerun con:

```text
tools/verify_kaggle_nq_post_upload.py
```

desde un commit exacto. El artefacto JSON debe conservarse sin editar.

## Firewalls

```text
KAGGLE_DATASET_UPLOAD_EXECUTED = true
OWNER_IDENTITY_RECONCILED      = true
POST_UPLOAD_REHASH_PASSED      = false
CONTROL_HASH_DRIFT_RECONCILED  = false
BIGTRAP2_RERUN_AUTHORIZED      = false
BT2A_NQ_GATE1_AUTHORIZED       = false
HOLDOUT_AUTHORIZED             = false
SCIENTIFIC_RUN_AUTHORIZED      = false
```

## Aporte al referente

El payload de mercado coincide, pero dos archivos de control difieren de Fase 1; no se congela BigTrap2 V2 hasta reconciliarlos.
