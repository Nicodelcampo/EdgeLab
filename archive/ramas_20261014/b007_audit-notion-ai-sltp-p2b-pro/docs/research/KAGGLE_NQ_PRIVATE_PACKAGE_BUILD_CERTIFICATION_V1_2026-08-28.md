# Certificación de Fase 1 — paquete privado NQ pre-holdout

**Estado:** `COMPLETE_PRIVATE_RESEARCH_PACKAGE`  
**Builder HEAD:** `4ad4f2e7ca5a48aa9b42414fc94fc4575fb2ead5`  
**Dataset ID preparado:** `nicodelcampo/edgelab-ticks-nq-preholdout`  
**Visibilidad obligatoria:** `private_only`  
**Upload ejecutado:** `false`

## Alcance de auditoría

El operador reportó la construcción local ejecutada con `AUTHORIZE_BUILD_KAGGLE_RESEARCH_DATASET_V1`. Este registro reconcilia aritmética, identidades declaradas y firewalls. El auditor remoto no tiene acceso a `E:\EdgeLab\kaggle_nq_research` y, por lo tanto, no afirma haber rehecho los SHA-256 sobre los bytes locales. La futura verificación del dataset adjunto en Kaggle deberá rehacer esos hashes antes de cualquier kernel.

La versión legible por máquina está en `KAGGLE_NQ_PRIVATE_PACKAGE_BUILD_CERTIFICATION_V1_2026-08-28.json`.

La reconciliación de ramas, CI y alcance de evidencia está en `RECONCILIACION_SINCRONIZACION_PHASE1_KAGGLE_2026-08-28.md`.

## Identidad declarada

| Artefacto | SHA-256 físico | SHA-256 lógico reportado | Bytes |
|---|---|---|---:|
| `kaggle_research_package_manifest.json` | `4d1053090d80930ee7494e008148b0b8a64829568d861065e054ed2f88f91506` | `f44e76c48be9d5e9017baa9efac2626e98c88cc3fd0b7840acfc8c1707641554` | 3.449 |
| `effective_input_registry.json` | `f9bcf5eee1e68bd4797a959f7e22d3344ae383d9d33c4c59a783ef10ce35e31f` | `3dd102216f239cb62730d2d80bd42f7368b5da3569af6b95473da5bdf5e414c` | 3.122 |
| `files.sha256` | `dddd3c83bc9fee7e3bf71181b051b1c54aea28f8c7ca4eafe96a606be4401bce` | N/A | 645 |
| `dataset-metadata.json` | `2114192e9b249eea7bf2cf23a0150dc31251e95c51397174ded8f52389237ab4` | N/A | 342 |

## Reconciliación

```text
PARQUET_FILES                    = 5
PACKAGED_ROWS                    = 119153201
REMOVED_HOLDOUT_ROWS             = 8737419
PACKAGED_PARQUET_BYTES           = 2265885160
RECUT_FILE                       = NQ_09-26_ticks.parquet
RECUT_FILE_SHA256                = 1030715b216210e9443077212fd2e26303966c031243167d097d8465f81fb64f
RESEARCH_DATASET_HOLDOUT_PRESENT = false
```

La suma de los cinco conteos de filas da exactamente `119153201`; la suma de bytes da exactamente `2265885160`. Las `8737419` filas eliminadas pertenecen exclusivamente a `NQ 09-26`.

## Corrección de unidad

```text
1782856800000000000 - 1782856799856000000 = 144000000 ns
                                                  = 144 ms
                                                  = 144000 µs
```

El margen correcto es **144 milisegundos**, no 144 microsegundos. Esto no modifica el veredicto: el máximo timestamp empaquetado permanece estrictamente antes de la apertura del holdout.

## Alcance de evidencia

```text
EVIDENCE_SCOPE                      = OPERATOR_ATTESTATION_RECONCILED_BY_REMOTE_AUDITOR
REMOTE_AUDITOR_REHASHED_LOCAL_FILES = false
POST_UPLOAD_BYTE_REHASH_REQUIRED     = true
```

La ausencia física fue certificada por el builder y atestada por el operador. La auditoría remota reconcilió las identidades y la aritmética declaradas, pero la verificación física independiente queda pendiente del rehash del dataset privado ya adjuntado en Kaggle.

## CI

```text
DEDICATED_KAGGLE_CONTRACT = PASS
GENERAL_REPOSITORY_PYTEST = FAIL
```

El check contractual dedicado valida la infraestructura fail-closed. No implica que la suite general del repositorio esté verde.

## Firewalls

```text
KAGGLE_DATASET_BUILD_EXECUTED  = true
KAGGLE_DATASET_UPLOAD_EXECUTED = false
BIGTRAP2_RERUN_AUTHORIZED      = false
BT2A_NQ_SWEEP_AUTHORIZED       = false
BT2A_NQ_GATE1_AUTHORIZED       = false
HOLDOUT_AUTHORIZED             = false
SCIENTIFIC_RUN_AUTHORIZED      = false
```

## Dictamen

`PASS_PHASE1_PACKAGE_BUILD_OPERATOR_ATTESTED`

Freeze A queda construido y reconciliado. La aprobación no autoriza upload, freeze científico, ejecución de BigTrap2/BT2A, outcomes ni holdout.

## Aporte al referente

El paquete NQ privado quedó construido con 119.153.201 filas y ausencia física declarada de holdout; sus hashes quedan registrados para verificación byte a byte tras el upload privado y antes de cualquier kernel.
