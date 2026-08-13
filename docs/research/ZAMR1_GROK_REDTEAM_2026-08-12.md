# ZAMR-1 — revisión adversarial Grok 4.6 (2026-08-12)

Rol: red-team. No implementa el landscape. No abre outcomes, P&L ni holdout.
Autoridad: specs/contratos > código/tests/CI/artefactos > Notion > chat.

## Veredicto

```text
Z0_SYNTHETIC = PASS_WITH_HARDENING
REMOTE_CI = PASS_WITH_LIMITATIONS
Z1_PLAN = CONDITIONALLY_VALID
Z1_BUILDER_V1 = REJECTED_FOR_EXECUTION
Z1_BUILDER_V2 = HARDENED_NOT_EXECUTED
Z2 = NOT_AUTHORIZED
LICENSE = NO_UPLOAD + USER_RISK_OVERRIDE
```

La infraestructura Z0 y el recorte de 22 sesiones son aprovechables. El builder v1 no debía ejecutarse contra datos reales. Los defectos de reloj de sesión, geometría, procedencia Kaggle y licencia stale eran suficientes para contaminar `session_key` y `zone_*_tick`.

## Hallazgos bloqueantes (corregidos en v2)

### R-01 Reloj de sesión civil vs CME ETH

`first_touch_census.session_date_ct` formatea la fecha civil Chicago. Un tick a las 17:00 CT pertenece al trade date siguiente. El plan Z1 se construyó con corte 17:00; el builder v1 filtraba con fecha civil. Mezclar ambas definiciones desplaza zonas del after-hours al día calendario incorrecto.

Z1 no hereda `session_date_ct`. Usa `session_date_cme` y exige `session_definition=cme_eth_1700_america_chicago`. No se reescribe F2.7 en este commit: el hallazgo queda abierto como deuda de consistencia histórica.

### R-02 Conversión de precio con `round(price/tick_size)`

BigTrap2 rellena medio tick. `round()` con banker’s rounding ya produjo alturas 0/1/2 para zonas de un tick. v2 invierte el padding de medio tick. Queda prohibido volver a `price/tick_size`.

### R-03 Git obligatorio rompe Kaggle

v1 exigía `git rev-parse` en un árbol limpio. Kaggle no es un checkout gobernado. v2 acepta `CODE_COMMIT` + `EDGELAB_CODE_DIRTY=false` y falla cerrado si falta cualquiera.

### R-04 Spec de licencia stale

`specs/zamr1_license_decision_v0.json` seguía en `PENDING_SOURCE_TERMS` con provider null después de identificar CQG y decidir `NO_UPLOAD`. Eso invita a otro LLM a “resolver M0” otra vez o a marcar `RAW_ALLOWED`. La spec se actualiza sin convertir el override del usuario en permiso contractual.

## Hallazgos no bloqueantes, no cerrados

- **R-05 Warmup 09-26 insuficiente.** El archivo empieza el 8 de junio; no hay 20 días de lead del mismo contrato antes del 12. Limitación declarada. No mezclar 06-26 como warmup del front.
- **R-06 Exports no canónicos.** Hashes distintos de F2.7. No sustituyen `124b375...` / `6ffcdf...`.
- **R-07 P-02 `max_age`.** 2000 barras pueden ser inalcanzables. No interpretar competing risks todavía.
- **R-08 Paridad NT8.** Las seis resoluciones siguen `NOT_ESTABLISHED`.
- **R-09 CI `-k`.** Excluir por nombre es frágil. v2 salta el test de parquet local por `conftest` cuando el archivo no existe.
- **R-10 Builder v1 ilegible.** Compactado en una línea. v2 se reescribe para auditoría.
- **R-11 P-01.** v2 falla si alguna sesión seleccionada no produce zonas.
- **R-12 Recurso ≥2×.** Se mide; no se adjudica sin corrida real.
- **R-13 Upload a Kaggle.** Sigue siendo transferencia a un tercero. El runner existe; la carga de ticks es override del usuario, no `RAW_ALLOWED`.

## Qué no se tocó a propósito

- Artefacto F2.7 ni su interpretación geométrica.
- Outcomes, targets, P&L, holdout.
- aVol, Z2–Z6, frames fuera de las seis preregistradas.
- `session_date_ct` global: cambiarlo reabriría F2.7/F1.1 sin protocolo.

## Instrucción al siguiente modelo

No ejecutar Z1 con el builder v1. Usar `zamr1_z1_bigtrap2_defaults_v2`. No relajar R-01/R-02/R-03 para obtener PASS. No autorizar Z2 sin corrida real, determinismo, P1A, firewall, P-01 y margen de recursos.
