# ZAMR-1 — branch ledger (2026-08-12)

Leer con `ZAMR1_HANDOFF_2026-08-12.md` y `ZAMR1_GROK_REDTEAM_2026-08-12.md`.

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
11. `20777ce` — builder v2: reloj CME, geometría half-tick, procedencia Kaggle.
12. `b1f0a56` — plan pinneado a `cme_eth_1700_america_chicago` y warmup 09-26.
13. `a7cdf92` — tests de reloj, geometría y procedencia offline.
14. `a7959f8` — licencia `NO_UPLOAD` con override separado.
15. `28460b9` — CI sin `-k`; skip por conftest.
16. `ba3b40b` — exports del paquete ZAMR-1.
17. `de27ae5` — Notebook Kaggle 01.
18. `aaf4544` — runbook Z1 y advertencia de licencia.
19. Este commit — ledger actualizado.

## Estado

- Z0: PASS con hardening.
- Builder v1: REJECTED_FOR_EXECUTION.
- Builder v2: HARDENED_NOT_EXECUTED.
- Paridad: NOT_ESTABLISHED.
- Licencia: NO_UPLOAD; override del usuario no es permiso.
- Z2: NOT AUTHORIZED.

## Continuación

No ejecutar v1. No usar `session_date_ct` en Z1. No relajar R-01/R-02/R-03. Primero CI, después builder v2 contra los hashes congelados. No abrir Z2 ni outcomes/P&L/holdout.
