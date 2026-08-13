# ZAMR-1 — handoff reproducible (2026-08-12)

Documento canónico para retomar EdgeLab sin depender del chat. Autoridad: specs/contratos ejecutables > código/tests/CI/artefactos > Notion > PDFs > chat > supuestos.

## Rama y estados

- Rama: `research/zamr1-zone-atlas`
- Base F2.7: `1b8e168`
- Draft PR: https://github.com/Nicodelcampo/EdgeLab/pull/13
- Revisión adversarial: `docs/research/ZAMR1_GROK_REDTEAM_2026-08-12.md`
- Corte exclusivo: `2026-06-30T22:00:00Z` (`1782856800000000000` ns)
- Reloj Z1: `cme_eth_1700_america_chicago` vía `session_date_cme`. No usar `session_date_ct` para Z1.

Estados:

```text
F2.7_FORMAL_RUN_COMPLETE_REFLECTION_POSITIVE
ZAMR1_Z0_PASS_WITH_HARDENING
ZAMR1_Z1_INPUT_AUDIT_PASS
ZAMR1_Z1_SESSION_PLAN_READY_22_SESSIONS
ZAMR1_Z1_BUILDER_V1_REJECTED_FOR_EXECUTION
ZAMR1_Z1_BUILDER_V2_HARDENED_NOT_EXECUTED
Z2_NOT_AUTHORIZED
LICENSE = NO_UPLOAD + USER_RISK_OVERRIDE
```

Prohibido: outcomes, retornos futuros, P&L, selección económica y lectura del holdout.

F2.7: `delta_reflection=0.0481526536`, IC95 `[0.0306759691,0.0656293381]`, 201 sesiones. Evidencia geométrica, no alpha.

## Datos y muestra Z1

- 09-26: `654e006e...`, export extendido no canónico.
- 06-26: `fd2e358d...`, export extendido no canónico.
- No sustituir hashes F2.7 `6ffcdf...` / `124b375...`.
- Roll: 06-26 hasta 11 jun inclusive; 09-26 desde 12 jun.
- 22 sesiones, 1–30 junio.
- Limitación: warmup 09-26 ~4 sesiones, no 20 días.

## Builder vigente

Usar sólo `zamr1_z1_bigtrap2_defaults_v2`.

Correcciones v2: reloj CME 17:00 CT; inversa de medio tick; procedencia offline `CODE_COMMIT` + `EDGELAB_CODE_DIRTY=false`; P-01 fail-closed; plan pinneado.

No ejecutar el builder v1.

## Kaggle Z1

Ver `kaggle/zamr1/README.md` y `kaggle/zamr1/notebooks/01_build_z1.py`. Subir ticks es override de riesgo, no `RAW_ALLOWED`.

## Gates antes de Z2

Suite PASS; corrida real PASS; determinismo; cero holdout/columnas prohibidas/duplicados; P1A en 12 unidades; margen >=2x; P-02 resuelto o excluido; P-01 fail-closed; paridad `NOT_ESTABLISHED` hasta oráculo.

## Instrucción mínima para otro LLM

> Trabajá sólo en `research/zamr1-zone-atlas`. Leé este handoff, `ZAMR1_GROK_REDTEAM_2026-08-12.md`, el contrato, el plan Z1 y `z1_builder.py` v2. No uses `session_date_ct` para Z1. No abras outcomes/P&L/holdout. No relajes R-01/R-02/R-03. No autorices Z2 sin todos los gates.
