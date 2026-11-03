# Corridas en R descartadas: riesgo con residuo de coma flotante (03/11/2026)

Estado: DESCARTADAS — no se miran; se relanzan con el código corregido (regla de `GUIA_GRILLA_MASIVA.md`).

**Causa raíz.** `grilla_generica.riesgo_ops` excluía el riesgo exactamente 0, pero no el residuo de coma flotante de un stop puesto en la
entrada (|entrada − stop| ≈ 1e-10). Dividir por ese número dio operaciones de ±1e8 a ±1e9 R. Lo encontró el atlas de ideas: medias
marginales de millones de R en estas 6 familias, y en ninguna otra.

**Arreglo.** Un riesgo menor a medio tick queda NaN, igual que el riesgo 0 que ya se excluía. No es un cambio de semántica: restituye la
declarada (una operación sin riesgo no se mide en R). Test: `tests/research/test_auditoria_operaciones.py::test_riesgo_ops_descarta_residuo_de_coma_flotante`.

| Campaña | Desenlace descartado |
|---|---|
| TAU-GC-R | SIN_CANDIDATAS |
| U1-6B-GRILLA-C-R | SIN_CANDIDATAS |
| U1-6E-CONFIRMA-GBP-C-R | BLOQUEADA (preflight: 2 nominadas por FDR sobre ruido; probablemente la misma causa) |
| U1-6E-GRILLA-C-R | SIN_CANDIDATAS |
| U1-ES-GRILLA-R | INTEGRIDAD_FALLA |
| U1-YM-GRILLA-R | INTEGRIDAD_FALLA |

Las otras 62 campañas del relanzamiento en R no tienen medias marginales anómalas (máximo 2,6R por nivel en ZGAP-CFD) y se conservan.
