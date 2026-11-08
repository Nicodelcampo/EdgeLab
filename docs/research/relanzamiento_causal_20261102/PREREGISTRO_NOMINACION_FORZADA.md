# Pre-registro: nominación de «las mejores» al holdout si el embudo no nomina ninguna (2026-11-02)

Estado: VIGENTE, registrado antes de ver las réplicas de 6 de las 11 campañas. Decisión de Nico (2026-11-02): «si no se nomina ninguna al
holdout, nominá las mejores». Referente: `docs/NORTH_STAR.md`, cuerpo sha256
`16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.

**Es una excepción humana al embudo.** Es una nominación sin confirmación en réplica: el holdout pasa a ser la ÚNICA prueba limpia de
estas reglas. Se declara así en cada acta.

## Regla de selección (fija)
Por cada familia del relanzamiento causal que termine sin candidata nominada por el embudo:
1. **Candidatas:** sus pistas a réplica con:
   - n de réplica ≥ 30 operaciones;
   - media neta de réplica > 0;
   - media neta de DESC > 0.
2. **Mejor:** la de mayor **cota inferior del IC90 por sesiones en la réplica**, el mismo orden que usa el embudo para congelar las
   pistas. Desempate por la media de la réplica. **Una por familia.**
3. **Sin pista que cumpla 1:** la familia no nomina.

Ni el máximo de P&L ni otra métrica: sólo ésta.

## Ejecución en el holdout
- **Regla congelada:** la celda y los cortes del DESC causal.
- **Sin tope de stop:** se usa el stop de la celda. La etapa TOPES del embudo no corrió para estas reglas, y elegir un tope ahora sería
  otra selección.
- **Acta por regla (`ACTA_HOLDOUT.json`):**
  - N fijo = 150 operaciones;
  - paso de LORD++ reservado en el libro de la familia antes de mirar;
  - decisión igual que las otras nominadas (CONFIRMADA si rechaza y media > 0; REFUTADA si media ≤ 0; si no, SIN_POTENCIA).
- **Sesiones:** 2026-10-01 → las disponibles en el sellado, sólo válidas (SELLADO_CONTEO). Con n < 150 queda EN CURSO.

## Transparencia sobre el orden
- **Ya vistas:** de CVGAP-ES-C, CVGAP-CFD-ES-C, U1-ZONAS-GRILLA-YM-C y U1-6E-CONFIRMA-GBP-C ya se vio el resultado agregado de la
  réplica (canasta y Simes), no el de cada pista.
- **No vistas:** U1-6B-FUT, U1-6B, U1-6E-FUT, U1-6E, U1-ZONAS-AVCL-ES y U1-ZONAS-BT2-YM. Esta regla se registra antes de sus réplicas.
- **U1-RACIMOS-GRILLA-YM-C** no tuvo pistas (0 celdas evaluables): no nomina.

## Cómo podría refutarse
Media ≤ 0 en el holdout a N fijo, o futilidad del e-proceso de la cartera si pasan a papel.
