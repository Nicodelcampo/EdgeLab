# Apertura conjunta del holdout: todas las nominadas, con código causal (2026-11-02)

Estado: VIGENTE. Pedido de Nico: «cuando termine todo abrimos el holdout con las nominadas» → «sí». Referente: `docs/NORTH_STAR.md`,
cuerpo sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Holdout: sesiones 2026-10-01 → 2026-10-30. Sólo sesiones
válidas: el 10-07 y el 10-29 están incompletos en el sellado y el ES del 10-30 también. Influencia baja: ver
`canasta_7_20261030/ACTA_APERTURAS_INDIVIDUALES_20261102.md`.

## Qué se abrió y con qué regla
- **Las 12 nominadas por el embudo**, re-medidas con código causal: actas individuales, N fijo, paso de LORD++ reservado.
- **U1-CRUZADO:** acta propia, con e-proceso.
- **Las 3 de nominación forzada** (excepción humana, sin confirmación en réplica): CVGAP-ES-C, CVGAP-CFD-ES-C y U1-ZONAS-AVCL-ES-C.
  Tienen acta a N fijo 150 y además ficha en papel con e-proceso desde el 10-01.
- **Canasta v4**, con t por sesión.

Todo corrió con código causal certificado. La auditoría vela a vela de la canasta dio 0 fallas.

## Resultado
Media neta por operación, en puntos del instrumento de ejecución.

| Regla | Holdout n / N fijo | Media holdout | Desarrollo causal | z contra desarrollo | Estado |
|---|---|---|---|---|---|
| CVGAP-NQ | 20 / 150 | −34,9 | +15,5 | −2,70 | EN CURSO, **alerta** |
| CVGAP-CFD-NQ | 16 / 150 | −22,9 | +11,8 | −2,45 | EN CURSO, **alerta** |
| U1-ES-GRILLA | 11 / 169 | −6,2 | +0,2 | −1,71 | EN CURSO, alerta |
| U1-ZONAS-NQ | 17 / 449 | −14,6 | +14,3 | −1,43 | EN CURSO |
| U1-ZONAS-ES | 2 / 150 | +1,0 | +7,3 | −0,50 | EN CURSO |
| U1-ZONAS-BT2-ES | 5 / 150 | +3,2 | +2,9 | +0,09 | EN CURSO |
| U1-ZONAS-BT2-NQ | 10 / 150 | +6,9 | +4,7 | +0,18 | EN CURSO |
| U1-RACIMOS-GRILLA-ES | 9 / 150 | +6,1 | +2,4 | +0,62 | EN CURSO |
| U1-ORO-GRILLA | 3 / 150 | +7,7 | +3,0 | +0,66 | EN CURSO |
| U1-ZONAS-AVCL-NQ | 7 / 150 | +15,0 | +4,7 | +1,10 | EN CURSO |
| U1-YM-GRILLA | 3 / 450 | +67,0 | +3,1 | (2 sesiones) | EN CURSO |
| U1-RACIMOS-GRILLA-NQ | 5 / 150 | +43,7 | +16,7 | +1,36 | EN CURSO |
| U1-CRUZADO | 18 | +25,8 | +11,4 | +0,79 | e-proceso NO_CONCLUYENTE |
| CVGAP-ES-C (forzada) | 6 / 150 | +2,7 | +7,1 | −0,43 | EN CURSO; papel e_edge 1,02 |
| CVGAP-CFD-ES-C (forzada) | 3 / 150 | +6,7 | +2,9 | +0,52 | EN CURSO; papel e_edge 1,03 |
| U1-ZONAS-AVCL-ES-C (forzada) | 7 / 150 | +0,8 | +3,4 | −0,64 | EN CURSO; papel e_edge 1,01 |

- **Canasta v4:** revisión 1 informativa, t = −0,93 sobre 18 sesiones. La primera revisión con decisión es la de 40 sesiones.
- **Papel (3 forzadas):** los tres e-procesos quedan SIN_DECIDIR. e_edge ≈ 1 contra 20 para promover; e_futilidad ≈ 1 contra 10 para
  retirar.

## Lectura
1. **Ninguna regla confirma ni se refuta todavía.** Un mes da de 2 a 20 operaciones por regla, contra N fijos de 150 a 450. Es lo
   esperado, no un fracaso.
2. **La única señal fuerte es mala: las dos CVGAP sobre NQ.** Están 2,5–2,7 errores estándar por debajo de su desarrollo, en el mismo mes.
   Corregido por las reglas comparadas no es significativo, pero son las primeras candidatas a retiro si noviembre sigue igual.
3. **Lo demás es compatible con su desarrollo**, incluidas las 3 forzadas (|z| < 0,7) y las U1 de zonas y racimos en NQ, que van a
   favor con muy pocas operaciones.
4. **Las reglas son casi independientes entre sí** (Li-Ji 13/13): la canasta diversifica de verdad.

## Qué sigue
- **Datos:** sumar sesiones selladas nuevas (NT8 y Dukascopy diarios) y completar el 10-07 y el 10-29.
- **Chequeo diario (22:47 UTC):** re-corre el holdout individual, la canasta y el papel con cada sesión nueva.
- **Decisiones:** salen solas cuando cada regla llega a su N fijo, o en cuanto un e-proceso cruza su umbral.
