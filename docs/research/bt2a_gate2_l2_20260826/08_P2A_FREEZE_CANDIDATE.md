# P2-A freeze candidate V1-R1

**Fecha:** 2026-08-26
**Base:** `761f50ba93158cc78c846b8774b7ac21a31b3b57`
**Rama propuesta:** `work/bt2a-gate2-p2a-freeze-20260826`
**Estado:** `READY_FOR_HUMAN_FREEZE_COMMIT_APPROVAL_V1_R1`

## Contrato estadístico

El spec aprobado permanece byte por byte sin cambios:

```text
spec file sha256    = 0705ae8377e91bd3fc4ed60ad712acd1b4e52b436e53d094dcdb957e8fbf08d5
spec payload sha256 = 176ca3e0c37f44823bfe5f8cf64849b55dcf12b5114d930d5ec8776c1566468c
```

Se conservan B={5,9,18,30}, H_ticks={25,50,100,250}, H_seconds={5,30,120}, semilla 20260821, 10.000 controles, 10.000 réplicas Webb y Holm sobre las 16 celdas primary.

## Correcciones adversariales V1-R1

1. Recalcula y valida los 234 checkpoints del Event Store y su payload agregado contra el hash congelado.
2. Fija en el runner el hash completo del spec y valida método, confianza, agregación, token, lock y Python 3.12.14.
3. Convierte grids incompletos, duplicados o valores no finitos en `P2_DIAGNOSTIC_INCONCLUSIVE`.
4. `--validate-only` devuelve código 2 cuando el estado es `NOT_READY`.
5. Cada checkpoint P2-A queda ligado al spec y al checkpoint Event Store vigente; la finalización revalida payload, grid, conteos y procedencia antes de agregar.
6. Rechaza índices de sesión fuera de 0..233.

## Verificación

```text
Python 3.12.14 exacto
45 passed
MALFORMED_CHECKPOINTS_REJECTED=True
MUTATED_CONTRACT_REJECTED=True
NONFINITE_IS_INCONCLUSIVE=True
NOT_READY_EXIT_CODE=2
new outcomes opened=false
holdout touched=false
freeze commit published=false
```

## Autorización requerida

La aprobación V1 no se reutiliza porque cambió el diff de implementación. Para publicar exclusivamente el commit V1-R1 se requiere:

```text
APRUEBO_CONGELAR_BT2A_P2A_V1_R1
```

El token de ejecución P2-A sigue separado y no corresponde todavía.

## Aporte al referente

V1-R1 conserva el diseño estadístico y cierra los cuatro caminos fail-open encontrados por la revisión adversarial; no abre outcomes ni habilita promoción.
