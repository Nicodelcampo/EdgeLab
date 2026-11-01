# PRERANGE-BASE — pre-registro (2026-11-01)

Estado: VIGENTE (pre-registrado antes de correr; pedido de Nico: «hacé lo que más convenga para tener más posibilidades de buenos
resultados» con la estrategia de las 8:12). Referente: `docs/NORTH_STAR.md`, cuerpo sha256
`16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Etapa: EF2 → embudo. Módulo: `edgelab/research/prerange_base.py`.

## Por qué así
PRERANGE-ZONAS (28.512 celdas por canal) no nominó nada en DESC en NQ, ES ni YM, y la canasta de pistas de NQ quedó con potencia 0,17
(media +5,7 pts/op, IC90 [−2,9; +15,0]). El cuello es la potencia: ~240 disparos por gatillo repartidos en miles de celdas. Las dos
palancas que más suben la probabilidad de detectar un efecto real son **menos celdas** y **más sesiones nuevas**:
- 144 celdas por canal (gatillo × alto del rango × las 16 ejecuciones de siempre); sin filtro de zonas.
- Historia de los CFD de Dukascopy **2023-01-03 → 2025-07-31**, que ninguna familia del rango de las 8:12 miró (PRERANGE-HFT y
  PRERANGE-ZONAS usaron futuros desde 2025-08). DESC ene-2023 → jun-2024 (~375 sesiones), réplica jul-2024 → jul-2025.
- Si algo sobrevive, las mismas celdas ya tienen su versión en futuros 2025-08 → 2026-09 dentro de PRERANGE-ZONAS (nivel "cualquiera"
  de las cantidades) como evidencia adicional, y el holdout desde 2026-10-01 queda para la confirmación.

## Justificación económica
El rango previo a la apertura de NY acumula stops y órdenes en sus extremos; el barrido de un extremo después de las 09:12 libera ese
flujo. La regla mide si después del barrido el precio vuelve (RETORNO) o sigue (CONTINUACION), con entradas confirmadas (reingreso,
giro del 25 % o cierre afuera), nunca en el extremo.

## Espacio de eventos
Ver `docs/research/prerange_hft_20261030/SPEC_PRERANGE_HFT.md` (mismos disparos). Se mide el barrido; las zonas quedan afuera a
propósito (son la parte que multiplicaba las celdas). El alto del rango en ATR es el único estado agregado.

## Cómo se refuta
0 nominadas por maxT (alfa 0,05 por canal) en DESC y canasta de pistas en contra con potencia, o media ≤ 0 en la réplica / holdout.
Instrumentos: DK:USA500IDXUSD (ES), DK:USATECHIDXUSD (NQ), DK:USA30IDXUSD (YM), con los costos canónicos de cada uno.

## Controles
`tests/research/test_prerange_base.py`: preflight, causalidad, paridad lote/escalar y que la mecánica sea la de `prerange_hft`.
