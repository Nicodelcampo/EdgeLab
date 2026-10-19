# EdgeLab — resultado P2-A congelado

**Estado:** `COMPLETE_P2A_POST_OUTCOME_DIAGNOSTIC`
**Clasificación:** `P2_DIAGNOSTIC_MECHANISM_SUPPORTED`
**Sesiones:** 234 (máxima sesión CME: `20260630`)
**Payload:** `296f8352a46751c3a9a26a32ec29661ddcecba7ac57874a967dc591a92766e28`

## Celdas primarias positivas tras Holm (familia de 16)

| Barrera (ticks) | Horizonte (ticks) | Punto | IC 95% | p | p Holm |
|---:|---:|---:|---:|---:|---:|
| 9 | 25 | 0.02380852 | [0.01193237, 0.03546375] | 9.999e-05 | 0.00159984 |
| 30 | 100 | 0.01546812 | [0.00677754, 0.02387699] | 0.00049995 | 0.0069993 |
| 30 | 250 | 0.03245809 | [0.02030684, 0.04464621] | 9.999e-05 | 0.00159984 |

No hubo celdas primarias negativas tras Holm. Las 12 celdas por reloj son secundarias y descriptivas; no participaron en la clasificación.

## Interpretación permitida

El patrón cumple la regla congelada de soporte diagnóstico del mecanismo. No es P&L realizado, no selecciona una combinación ganadora y no autoriza SL/TP productivo, P2-B, edge ni promoción.

## Firewall

- `EDGE_DECLARED=false`
- `confirmatory_eligible=false`
- `promotion_eligible=false`
- P2-B no ejecutado
- Outcomes L2/HMM no abiertos
- Holdout `2026-07-01`–`2026-12-31` no analizado

## Integridad

- 234/234 checkpoints validados.
- 16 celdas primarias y 12 secundarias.
- Holm aplicado únicamente a las 16 celdas primarias de `K_ABS − N_RAND`.
- Contrato, Event Store, runtime y lock coinciden con las identidades congeladas.