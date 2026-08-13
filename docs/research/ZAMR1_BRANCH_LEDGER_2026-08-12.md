# ZAMR-1 — branch ledger (2026-08-12)

Registro ordenado para handoff entre personas o LLMs. Leer junto con `ZAMR1_HANDOFF_2026-08-12.md`.

## Commits adjudicados

1. `6d6fab1` — contrato target-free, parameter DAG, schemas y tests.
2. `136a3d6` — validación de parámetros fail-closed.
3. `ebbb205` — Notebook Kaggle 00 y runbook.
4. `3e9fd6d` — transporte CSV permitido sólo para Z0 sintético.
5. `a7121bf` — hardening de preflight y bloqueo M0 de upload real.
6. `be7bcf6` — auditoría de los dos Parquet, plan ejecutable de 22 sesiones y handoff reproducible.
7. `bd4787a` — builder real Z1 target-free para seis frames.
8. Este commit — tests mínimos del transform y ledger durable.

## Estado en HEAD

- Z0 sintético: PASS con hardening.
- Inputs Z1: auditados; hashes y roll congelados.
- Muestra Z1: 22 sesiones, 1–30 junio, sin duplicados de roll ni holdout.
- Builder: implementado y validado sintácticamente; corrida real aún no ejecutada.
- Paridad seis frames: `NOT_ESTABLISHED`.
- Licencia: `NO_UPLOAD`; override del usuario separado y no presentado como permiso.

## Regla de continuación

No reescribir historia ni cambiar hashes/sesiones/roll/defaults para obtener PASS. Primero ejecutar la suite. Después ejecutar el builder con los archivos exactos. Conservar íntegros `events_long`, `zones_long`, manifests, reporte contractual, recursos y hashes. Si falla cualquier gate, registrar traceback y causa raíz en un nuevo commit. No abrir Z2 ni outcomes/P&L/holdout.

## Archivos de entrada obligatorios

- `docs/research/ZAMR1_HANDOFF_2026-08-12.md`
- `specs/zamr1_structural_contract_v0.json`
- `specs/zamr1_parameter_registry_v0.json`
- `specs/zamr1_z1_pilot_plan_2026-08-12.json`
- `edgelab/research/zamr1/z1_builder.py`
- `tests/research/test_zamr1_contracts.py`
- `tests/research/test_zamr1_kaggle_preflight.py`
- `tests/research/test_zamr1_z1_builder.py`
