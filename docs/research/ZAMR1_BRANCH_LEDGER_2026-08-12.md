# ZAMR-1 — branch ledger (actualizado 2026-08-13)

Leer con `ZAMR1_HANDOFF_2026-08-12.md`, `ZAMR1_GROK_REDTEAM_2026-08-12.md` y `ZAMR1_Z1_ENGINEERING_PILOT_2026-08-13.md`.

## Commits

1. `6d6fab1` — contrato target-free, DAG, schemas y tests.
2. `136a3d6` — validación fail-closed de parámetros.
3. `ebbb205` — Notebook Kaggle 00 y runbook.
4. `3e9fd6d` — CSV sólo para Z0 sintético.
5. `a7121bf` — hardening preflight y bloqueo M0.
6. `be7bcf6` — auditoría de Parquet, plan de 22 sesiones y handoff.
7. `bd4787a` — builder Z1 v1. **Rechazado para ejecución real.**
8. `2064720` — tests mínimos v1 y ledger inicial.
9. `e4340a6` — CI remoto PASS con limitaciones.
10. `c994af6` — reloj CME, revisión Grok y conftest.
11. `20777ce` — builder v2.
12. `b1f0a56` — plan pinneado y warmup 09-26.
13. `a7cdf92` — tests reloj/geometría/procedencia.
14. `a7959f8` — licencia `NO_UPLOAD`.
15. `28460b9` — CI sin `-k`.
16. `ba3b40b` — exports del paquete.
17. `de27ae5` — Notebook Kaggle 01.
18. `aaf4544` — runbook Z1.
19. `283462b` — handoff canónico.
20. `93e4931` — ledger Grok v2.
21. `8a586f5` — gate legal fail-closed; Notebook 01 bloqueado bajo `NO_UPLOAD`.
22. Este commit — acta y payload de la corrida local Z1 provisional; handoff y ledger actualizados.

## Estado

- Z0: PASS con hardening.
- Builder v1: REJECTED_FOR_EXECUTION.
- Builder v2: HARDENED_NOT_EXECUTED formalmente.
- Corrida local equivalente: ENGINEERING_PASS_PROVISIONAL.
- Determinismo byte a byte: NOT_ADJUDICATED.
- Paridad: NOT_ESTABLISHED.
- Licencia: NO_UPLOAD.
- Z2: NOT AUTHORIZED.

## Continuación

Endurecer procedencia/contrato/bundle/determinismo del builder v2, ejecutar dos veces el builder exacto sobre los hashes congelados y adjudicar recursos. No abrir Z2 ni outcomes/P&L/holdout.
