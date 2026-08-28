# Reconciliación y estado de sincronización — Fase 1 Kaggle NQ

**Fecha:** 2026-08-28  
**Dictamen:** `PASS_WITH_PREEXISTING_GENERAL_CI_DEBT_OPERATOR_ATTESTED`  
**Paquete:** `COMPLETE_PRIVATE_RESEARCH_PACKAGE`  
**Alcance de evidencia:** `OPERATOR_ATTESTATION_RECONCILED_WITH_REMOTE_CHECK_STATUS`

## 1. Corrección temporal

```text
HOLDOUT_OPEN_UTC_NS = 1782856800000000000
MAX_PACKAGED_TS_NS  = 1782856799856000000
STRICT_MARGIN_NS    =          144000000
STRICT_MARGIN_MS    =                144
STRICT_MARGIN_US    =             144000
```

El margen correcto es **144 ms**, no 144 µs. La desigualdad estricta permanece válida:

```text
MAX_PACKAGED_TS_NS < HOLDOUT_OPEN_UTC_NS = true
```

## 2. Sincronización local atestada

| Worktree | Rama | HEAD inicial | HEAD final | Estado | Ahead/behind |
|---|---|---|---|---|---:|
| `D:\EdgeLab-kaggle` | `infra/kaggle-frozen-execution-v1-20260828` | `0007a50a441f63abaef74e252a86af80901023f9` | `a38f11425e36b19c23f0c1e943b9643f8241967e` | `CLEAN` | `0/0` |
| `D:\EdgeLab-nq-bt2` | `research/bigtrap2-nq-tickframes-sweep-v1-20260828` | `f96fffcbdbce64a53b8bad2212f7fba9bc1228f7` | `30cf3cea41346f33288f1a8dd31bcbe4aa1a0af4` | `CLEAN` | `0/0` |

La sincronización fue reportada mediante `git pull --ff-only`, sin conflictos ni archivos no rastreados. El estado de los discos locales es evidencia del operador; los HEAD finales sí fueron reconciliados con los refs remotos.

## 3. Linaje Git

### PR #24

```text
branch              = infra/kaggle-frozen-execution-v1-20260828
lineage_anchor_head = 0007a50a441f63abaef74e252a86af80901023f9
base_branch         = research/avolcluster-nq-gate1-infra-v1-20260828
base_sha            = 7bbb33828c9e0efb02af850463b4957943934d43
commits_at_anchor   = 6
```

El valor `0007a50a441f63abaef74e252a86af80901023f97bbb338` era una concatenación inválida del HEAD de PR #24 y el prefijo de su base. No debe utilizarse como identificador Git.

### PR #23

```text
branch        = research/bigtrap2-nq-tickframes-sweep-v1-20260828
sync_head     = 30cf3cea41346f33288f1a8dd31bcbe4aa1a0af4
base_branch   = infra/kaggle-frozen-execution-v1-20260828
base_sync_sha = a38f11425e36b19c23f0c1e943b9643f8241967e
```

### BT2A NQ — Fase 3

```text
branch                      = research/bt2a-nq-target-free-selection-v1-20260828
status_document_head        = 12f7c728dcea618f7c983305be7ba93d58876e0a
implementation_anchor_head  = d194b50fca0559525ba592b371d6aa1eb173409b
status                      = PHASE3_FAIL_CLOSED_PREFLIGHT_IMPLEMENTED_NOT_RUN
scientific_run_authorized   = false
```

La rama contiene preflight fail-closed, spec draft, tests y workflow contractual; no está vacía ni meramente creada.

## 4. Contratos dedicados

Ejecución local atestada sobre `30cf3cea41346f33288f1a8dd31bcbe4aa1a0af4`:

```text
Python                                      = 3.12.7 win32
test_bigtrap2_nq_tickframes_sweep.py        = 15 passed
test_kaggle_frozen_execution.py             =  9 passed
TOTAL                                       = 24 passed
DURATION                                    = 5.20 s
HEAD_BEFORE_EQUALS_HEAD_AFTER               = true
WORKTREE_CLEAN_BEFORE_AND_AFTER             = true
```

Los workflows remotos confirman:

```text
PR24_DEDICATED_KAGGLE_CONTRACT      = PASS
PR23_DEDICATED_BT2_NQ_CONTRACT      = PASS
```

## 5. Diagnóstico de CI general

Comando reproducido localmente:

```text
python -m pytest -q --durations=10
```

Resultado reportado sobre la pila sincronizada:

```text
1212 passed
30 failed
35 skipped
2 xfailed
14 errors
364.62 s
```

La comparación del operador contra la base `7bbb33828c9e0efb02af850463b4957943934d43` reportó el mismo conjunto de fallos y errores, con delta de regresión cero para la pila PR #24 + PR #23.

### Reconciliación aritmética de grupos

| Grupo | Fallos | Errores | Clasificación |
|---|---:|---:|---|
| PyArrow schema — `test_audit_p3.py` | 0 | 13 | Deuda heredada |
| Store V2 / coverage propagation | 19 | 0 | Deuda heredada |
| Environment contract | 1 | 0 | Dependencia/entorno heredado |
| Distance-matched null CLI | 3 | 0 | Deuda heredada |
| Windows tempfile locking | 1 | 0 | Fixture/SO heredado |
| Demos y placebos auxiliares — remanente agregado | 6 | 1 | Deuda heredada |
| **Total** | **30** | **14** | **Reconciliado** |

La categoría remanente cierra la aritmética, pero no se recibieron los node IDs exactos por archivo. El detalle legible por máquina está en `GENERAL_CI_DEBT_RECONCILIATION_NQ_STACK_2026-08-28.json`.

### Alcance permitido del dictamen

```text
STACK_HEAD_REPORTED_REGRESSION_DELTA_VS_BASE = 0
PR24_ISOLATED_FULL_SUITE_COMPARISON_SUPPLIED = false
RAW_PYTEST_LOGS_COMMITTED                    = false
EXACT_FAILURE_NODE_IDS_COMMITTED             = false
```

Por ello se acepta `PASS_WITH_PREEXISTING_GENERAL_CI_DEBT_OPERATOR_ATTESTED`; no se eleva a certificación independiente ni se afirma una prueba aislada de PR #24 que no fue incluida en el informe suministrado.

## 6. Alcance de certificación física

```text
REMOTE_AUDITOR_REHASHED_LOCAL_FILES = false
PACKAGE_BYTES_LOCAL                 = OPERATOR_ATTESTED
POST_UPLOAD_REHASH_REQUIRED         = true
```

Los hashes, conteos, tamaños y aritmética fueron reconciliados. La verificación independiente byte a byte debe repetirse después del upload privado y antes de cualquier kernel Kaggle.

“Publicado en el linaje del repositorio” significa que se publicaron certificación y metadatos; no significa que el dataset haya sido subido.

## 7. Firewalls

```text
KAGGLE_DATASET_BUILD_EXECUTED  = true
KAGGLE_DATASET_UPLOAD_EXECUTED = false
BIGTRAP2_RERUN_AUTHORIZED      = false
BT2A_NQ_SWEEP_AUTHORIZED       = false
BT2A_NQ_GATE1_AUTHORIZED       = false
HOLDOUT_AUTHORIZED             = false
SCIENTIFIC_RUN_AUTHORIZED      = false
```

## 8. Dictamen final

```text
LOCAL_WORKTREE_SYNC             = PASS_OPERATOR_ATTESTED
REMOTE_HEAD_RECONCILIATION      = PASS
DEDICATED_CONTRACTS             = PASS
GENERAL_CI                      = FAIL_PREEXISTING_OPERATOR_REPRODUCED
STACK_REGRESSION_DELTA          = 0_OPERATOR_ATTESTED
BT2A_PHASE3_PREFLIGHT           = IMPLEMENTED_NOT_RUN
DATASET_UPLOAD                  = NOT_EXECUTED
SCIENTIFIC_RUN                  = NOT_EXECUTED
FINAL_VERDICT                   = PASS_WITH_PREEXISTING_GENERAL_CI_DEBT_OPERATOR_ATTESTED
```

## Aporte al referente

La sincronización y los contratos quedan aprobados; la deuda global se registra como idéntica a la base bajo atestación local, con aritmética completa y limitaciones explícitas, sin afirmar que no se abrieron datos: se construyó el paquete pre-holdout, pero no se ejecutó una nueva corrida científica ni se abrieron outcomes o holdout.
