# ZAMR-1 — handoff reproducible (actualizado 2026-08-13)

Documento canónico para retomar EdgeLab sin depender del chat. Autoridad: specs/contratos ejecutables > código/tests/CI/artefactos > Notion > PDFs > chat > supuestos.

## Rama y estados

- Rama: `research/zamr1-zone-atlas`
- Base F2.7: `1b8e168`
- Draft PR: https://github.com/Nicodelcampo/EdgeLab/pull/13
- Revisión adversarial: `docs/research/ZAMR1_GROK_REDTEAM_2026-08-12.md`
- Evidencia Z1 local: `docs/research/ZAMR1_Z1_ENGINEERING_PILOT_2026-08-13.md`
- Payload de evidencia: `specs/zamr1_z1_engineering_pilot_2026-08-13.json`
- Corte exclusivo: `2026-06-30T22:00:00Z` (`1782856800000000000` ns)
- Reloj Z1: `cme_eth_1700_america_chicago` vía `session_date_cme`.

Estados:

```text
F2.7_FORMAL_RUN_COMPLETE_REFLECTION_POSITIVE
ZAMR1_Z0_PASS_WITH_HARDENING
ZAMR1_Z1_INPUT_AUDIT_PASS
ZAMR1_Z1_SESSION_PLAN_READY_22_SESSIONS
ZAMR1_Z1_BUILDER_V1_REJECTED_FOR_EXECUTION
ZAMR1_Z1_BUILDER_V2_HARDENED_NOT_EXECUTED
ZAMR1_Z1_LOCAL_ENGINEERING_PASS_PROVISIONAL
ZAMR1_Z1_FORMAL_NOT_CLOSED
BYTE_DETERMINISM_NOT_ADJUDICATED
ORACLE_PARITY_NOT_ESTABLISHED
Z2_NOT_AUTHORIZED
LICENSE_NO_UPLOAD
```

Prohibido: outcomes, retornos futuros, P&L, selección económica y lectura del holdout.

## Datos y muestra Z1

- 09-26: `654e006e...`, export extendido no canónico.
- 06-26: `fd2e358d...`, export extendido no canónico.
- No sustituir hashes F2.7 `6ffcdf...` / `124b375...`.
- Roll: 06-26 hasta 11 jun inclusive; 09-26 desde 12 jun.
- 22 sesiones, 1–30 junio; plan declara 1.651.076 ticks en sesiones seleccionadas.
- Limitación: warmup 09-26 ~4 sesiones, no 20 días.

## Evidencia de ingeniería del 13 de agosto

Los dos hashes coincidieron. Un runner local target-free ejecutó 12/12 unidades, observó 22/22 sesiones, 48.314 eventos y 8.718 zonas, sin duplicados, sin discrepancias P1A y sin cruzar el firewall. Pico RSS ~588 MiB y ~126 s de kernel.

La VM no tenía soporte Parquet estándar ni red. Se usó un lector offline mínimo y un runner de equivalencia; por eso este resultado es `PASS_PROVISIONAL`, no Z1 formal. Los hashes de los CSV temporales están registrados en el acta, pero los CSV no se consideran artefactos canónicos.

## Builder vigente

Usar sólo `zamr1_z1_bigtrap2_defaults_v2`. Correcciones v2: reloj CME 17:00 CT; inversa half-tick; procedencia offline; P-01 fail-closed; plan pinneado. No ejecutar v1.

## Licencia y Kaggle

`NO_UPLOAD` es vinculante para la operación. El commit `8a586f5` bloquea Notebook 01 antes de descubrir o leer ticks si la decisión no es `RAW_ALLOWED`. Un override de riesgo no es permiso contractual.

## Gates pendientes antes de Z2

1. validar contrato observado por fuente contra el plan;
2. registrar hash del plan;
3. separar identidad determinística de runtime/RSS/timestamps de ejecución;
4. bundle autocontenido con contrato, registro, validador y `hashes.sha256`;
5. ejecutar el builder exacto dos veces y comparar hashes de datos;
6. adjudicar margen ≥2× con el builder exacto;
7. mantener paridad `NOT_ESTABLISHED` hasta oráculo.

## Instrucción mínima para otro agente

> Trabajá sólo en `research/zamr1-zone-atlas`. Leé este handoff, la revisión Grok, el contrato, el plan y el acta Z1 del 13 de agosto. No uses `session_date_ct`. No abras outcomes/P&L/holdout. No subas ticks a Kaggle. No autorices Z2 sin cerrar builder formal, determinismo, bundle y recursos.
