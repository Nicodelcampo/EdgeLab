# Acta: apertura INDIVIDUAL del holdout de las 12 nominadas, con código causal (2026-11-02), registrada antes de correr

Estado: VIGENTE. Pedido de Nico (2026-11-02): «si ya están todas las candidatas corregidas con la nueva regla causal, abrí el holdout
para todas, individualmente». Referente: `docs/NORTH_STAR.md`, cuerpo sha256
`16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Etapa EF5.

## Condición previa: cumplida
Las 12 nominadas están re-medidas con el código causal en DESC y réplica (`PROPUESTA_V3_CAUSAL_20261102.md`, las dos tablas). Todas
tienen el certificado de causalidad vigente.

## Qué se corre
- **Las 7 que todavía no corrieron sobre el sellado:** U1-ORO-GRILLA (GC), U1-YM-GRILLA (YM), U1-ES-GRILLA, U1-RACIMOS-GRILLA-ES,
  U1-ZONAS-BT2-ES, U1-ZONAS-BT2-NQ y U1-ZONAS-ES.
  - Cada una con su celda, cortes y tope congelados (`ACTA_HOLDOUT.json`), sesiones 10-01 → 10-30.
  - Las reglas de zonas usan el calentamiento de desarrollo.
- **Las 5 de la v3:** se usan sus corridas sobre el sellado ya hechas (`holdout_v3/`).

## Decisión por regla
Es la de su `ACTA_HOLDOUT.json`, sin cambios: «las primeras 150 operaciones desde el 2026-10-01, al paso RESERVADO de LORD++ de la
familia; CONFIRMADA si rechaza y media > 0; REFUTADA si media ≤ 0; si no, SIN_POTENCIA».
- Con el holdout disponible (un mes), ninguna regla llega a 150 operaciones.
- **No se decide antes de tiempo.** Cada regla queda **EN CURSO** con su n, media e IC90 interinos, informativos.
- La reserva de LORD++ se resuelve recién al llegar a n = 150, con los datos sellados que se vayan sumando.

## Integridad
- **Sesiones válidas:** al menos el 50 % de la mediana de ticks por sesión en cada fuente usada (`SELLADO_CONTEO.json`).
- Se informa por regla el resultado con todas las sesiones y con sólo las válidas.
- Si la diferencia no cambia ninguna lectura, se registra como de influencia baja.

## Resultado interino (2026-11-02), en `holdout_v3/INDIVIDUAL.json`
Sesiones 10-01 → 10-30. **Ninguna regla llega a su N fijo: todas EN CURSO.** No se resolvió ninguna reserva de LORD++. Media neta
por operación en puntos del instrumento de ejecución; IC90 por sesiones, interino.

| Regla | n / N fijo | Media | IC90 | Sólo sesiones válidas |
|---|---|---|---|---|
| CVGAP-NQ | 20 / 150 | −34,9 | [−69,3; −2,7] | igual |
| CVGAP-CFD-NQ | 16 / 150 | −22,9 | [−40,5; −0,6] | igual |
| U1-ZONAS-NQ | 17 / 449 | −14,6 | [−65,2; +23,7] | igual |
| U1-ES-GRILLA | 11 / 169 | −6,2 | [−13,5; −0,3] | igual |
| U1-ZONAS-BT2-ES | 6 / 150 | +0,2 | [−5,4; +3,9] | +3,2 (5) |
| U1-RACIMOS-GRILLA-ES | 13 / 150 | +4,5 | [−0,5; +7,7] | +6,1 (9) |
| U1-ZONAS-BT2-NQ | 10 / 150 | +6,9 | [−15,5; +23,6] | igual |
| U1-ORO-GRILLA | 3 / 150 | +7,7 | — | igual |
| U1-ZONAS-AVCL-NQ | 7 / 150 | +15,0 | [+6,4; +23,6] | igual |
| U1-RACIMOS-GRILLA-NQ | 5 / 150 | +43,7 | [+27,3; +60,1] | igual |
| U1-YM-GRILLA | 3 / 450 | +67,0 | — | igual |
| U1-ZONAS-ES | (corriendo) | | | |
| U1-CRUZADO (acta propia) | 18 | +25,8 | e-proceso NO_CONCLUYENTE | igual |

**Lectura interina.**
- Las dos CVGAP y U1-ES van en contra con el IC90 debajo de 0.
- Las U1 de zonas y racimos en NQ, más U1-CRUZADO, van a favor, pero con muy pocas operaciones.
- Nada se decide hasta N fijo; el holdout sigue acumulando con los datos sellados nuevos.

## Influencia de la integridad (días incompletos): BAJA
Según `SELLADO_CONTEO.json`:
- el 10-29 está incompleto en todas las fuentes;
- el 10-07, en NQ, ES y GC (YM no tiene ese día);
- el ES del 10-30 está a la mitad.

**Efecto medido.** En las reglas de NQ no hay operaciones en esos días, porque falta el dato: no hay operaciones contaminadas, pero
se pierden unas 2 de 22 sesiones (≈ 9 %) de oportunidades. En ES, 5 operaciones caen en sesiones incompletas (RACIMOS-ES 4, BT2-ES 1).
Sacarlas mueve la media (+4,5 → +6,1 y +0,2 → +3,2), pero no cambia el estado de ninguna regla (todas EN CURSO). La canasta tampoco
cambia de decisión (v3: −1,51 / −0,73).

Se registra y se tiene en cuenta: las revisiones siguientes usan sólo sesiones válidas, y hay que completar el 10-07 y el 10-29 en el
sellado.

## Canasta v4, revisión 1 (informativa: esas sesiones ya las miró la v3)
18 sesiones válidas en NQ, ES y CFD a la vez (10-01 → 10-28): **t = −0,93**, media −0,40. La primera revisión con decisión de la v4
es la de 40 sesiones.
