# Pre-registro: holdout forzado de las mejores pistas de DOBLE-RETROCESO (04/11/2026)

Estado: VIGENTE. Lo pidió Nico («probá las mejores en el holdout») y se registra antes de abrir el holdout. Referente `docs/NORTH_STAR.md`,
cuerpo SHA-256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.

**Excepción humana.** Ninguna pista cumple la regla con cota inferior del IC90 > 0. Se usa la regla original del 02/11
(`relanzamiento_causal_20261102/PREREGISTRO_NOMINACION_FORZADA.md`): por campaña, la pista con n de réplica ≥ 30, media de réplica > 0 y
media de DESC > 0, la de mayor cota inferior del IC90 de réplica; una por campaña. La herramienta es `tools/nominacion_forzada.py` sin
`--cota-min`. Cumplen 7: GC, YM, XAU, NQ, USA500, EURUSD y USATECH.

**Acta por regla:**
- N fijo 150;
- paso de LORD++ reservado en el libro de cada familia antes de mirar;
- sin tope, con la celda y los cortes congelados del DESC;
- holdout desde 2026-10-01; sólo las sesiones válidas del sellado (excluidas las de `holdout.py`).

**Advertencia:** son las mejores de una grilla de 746 mil celdas y sus canastas en réplica dieron ≤ 0. Lo esperable es que el holdout las
refute. Con N < 150 quedan EN CURSO.
