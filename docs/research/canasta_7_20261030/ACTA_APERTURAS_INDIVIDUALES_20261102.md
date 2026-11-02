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
