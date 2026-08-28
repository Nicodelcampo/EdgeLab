# Reconciliación y estado de sincronización — Fase 1 Kaggle NQ

**Fecha:** 2026-08-28  
**Dictamen:** `PASS_WITH_TRACEABILITY_CORRECTIONS`  
**Paquete:** `COMPLETE_PRIVATE_RESEARCH_PACKAGE`  
**Alcance de evidencia:** `OPERATOR_ATTESTATION_RECONCILED_BY_REMOTE_AUDITOR`

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

## 2. Linaje Git reconciliado

### PR #24 — infraestructura Kaggle

```text
branch              = infra/kaggle-frozen-execution-v1-20260828
lineage_anchor_head = 0007a50a441f63abaef74e252a86af80901023f9
base_branch         = research/avolcluster-nq-gate1-infra-v1-20260828
base_sha            = 7bbb33828c9e0efb02af850463b4957943934d43
commits_at_anchor   = 6
```

El valor `0007a50a441f63abaef74e252a86af80901023f97bbb338` era una concatenación inválida del HEAD de PR #24 y el prefijo de su base. No debe utilizarse como identificador Git.

Los seis commits hasta el anchor son:

```text
1204c5c83a9dc82379c0ed336589c76f2ca27493
 e72eca32200fc0fa1ee1a3a83ddb59a0c5d61ff0
092a5c59a6e4088387e586acb29d20e1f9dc1040
1b38cb117bc84ad87ced72d6615a1c2d3f6ef7e8
4ad4f2e7ca5a48aa9b42414fc94fc4575fb2ead5
0007a50a441f63abaef74e252a86af80901023f9
```

### PR #23 — BigTrap2 NQ V2

```text
branch       = research/bigtrap2-nq-tickframes-sweep-v1-20260828
observed_head = f96fffcbdbce64a53b8bad2212f7fba9bc1228f7
base_branch  = infra/kaggle-frozen-execution-v1-20260828
base_anchor  = 0007a50a441f63abaef74e252a86af80901023f9
```

PR #23 estaba correctamente apilado sobre PR #24 en el snapshot auditado.

### BT2A NQ — Fase 3

```text
branch                      = research/bt2a-nq-target-free-selection-v1-20260828
implementation_anchor_head  = d194b50fca0559525ba592b371d6aa1eb173409b
status                      = PHASE3_FAIL_CLOSED_PREFLIGHT_IMPLEMENTED
scientific_run_authorized   = false
```

La rama no está vacía ni meramente creada: ya contiene el preflight fail-closed de Gate 1, su spec draft, tests y workflow contractual.

## 3. CI reconciliado

Snapshot remoto auditado:

```text
PR24_DEDICATED_CONTRACT       = PASS
PR23_DEDICATED_BT2_CONTRACT   = PASS
PR24_GENERAL_PYTEST           = FAIL
PR23_GENERAL_PYTEST           = FAIL
```

El verde aplica exclusivamente a los workflows contractuales dedicados. No debe describirse el estado como CI global verde. Las causas de la suite general requieren un diagnóstico separado contra sus bases.

La ejecución local combinada declarada fue:

```text
test_bigtrap2_nq_tickframes_sweep.py = 15/15 PASS
test_kaggle_frozen_execution.py      =  9/9 PASS
TOTAL_LOCAL_OPERATOR_ATTESTED        = 24/24 PASS
```

El resultado local, el tiempo de 3.72 s y los worktrees `CLEAN` son atestaciones del operador. GitHub confirma los contratos dedicados, pero no puede inspeccionar `D:\EdgeLab-kaggle` ni `D:\EdgeLab-nq-bt2`.

## 4. Alcance de certificación física

```text
REMOTE_AUDITOR_REHASHED_LOCAL_FILES = false
PACKAGE_BYTES_LOCAL                 = OPERATOR_ATTESTED
POST_UPLOAD_REHASH_REQUIRED         = true
```

Los hashes, conteos, tamaños, manifiestos y aritmética fueron reconciliados remotamente. La verificación independiente byte a byte debe repetirse después del upload privado y antes de iniciar cualquier kernel Kaggle.

“Publicado en el linaje del repositorio” significa que se publicaron la certificación y los metadatos; no significa que el dataset haya sido subido.

## 5. Firewalls

```text
KAGGLE_DATASET_BUILD_EXECUTED  = true
KAGGLE_DATASET_UPLOAD_EXECUTED = false
BIGTRAP2_RERUN_AUTHORIZED      = false
BT2A_NQ_SWEEP_AUTHORIZED       = false
BT2A_NQ_GATE1_AUTHORIZED       = false
HOLDOUT_AUTHORIZED             = false
SCIENTIFIC_RUN_AUTHORIZED      = false
```

## 6. Dictamen final

```text
PACKAGE_ARITHMETIC_RECONCILIATION = PASS
HOLDOUT_MARGIN                     = PASS_144_MS
PR24_LINEAGE                       = CORRECTED
PR23_STACKED_LINEAGE               = PASS_AT_AUDITED_SNAPSHOT
BT2A_PHASE3_STATUS                 = PREFLIGHT_IMPLEMENTED_NOT_RUN
DEDICATED_CONTRACT_CI              = PASS
GENERAL_REPOSITORY_CI              = FAIL
LOCAL_FILES_AND_WORKTREES          = OPERATOR_ATTESTED
DATASET_UPLOAD                     = NOT_EXECUTED
SCIENTIFIC_RUN                     = NOT_EXECUTED
FINAL_VERDICT                      = PASS_WITH_TRACEABILITY_CORRECTIONS
```

## Aporte al referente

La Fase 1 queda reconciliada con margen correcto de 144 ms, linaje Git no concatenado, CI dedicado separado de CI general y estado BT2A Fase 3 actualizado, sin convertir evidencia local atestada en verificación física remota.
