# Pre-registro — U1-ORO-GRILLA: el vecindario completo de U1 en el oro (señal XAU, operación GC)

Estado: PRE-REGISTRO (commiteado antes de correr). Fecha: 2026-10-25.
Referente: `docs/NORTH_STAR.md`, cuerpo sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
Familia `U1_ORO_GRILLA`. Etapa del embudo: **EF2** (DESC) → réplica → holdout, conducido por `edgelab/research/embudo.py`.
Campaña: `config/autopilot/grillas/campanas/U1-ORO-GRILLA.json`. Experimento: `edgelab/research/u1_oro.py` (tests `tests/research/test_u1_oro.py`).
Pedido de Nico (2026-10-25): «priorizá las corridas del oro inspiradas en las de USATECH; las más rentables, más variantes».

## 1. Qué se barre
- La grilla completa de U1-INDAGA (N, x, A/H, volumen y velocidad de ida y vuelta, franjas, VWAP; 48 ejecuciones sin BE) más la
  perilla **escala** ∈ {0,5; 1; 2} del área: W = 40 pts y G = 1 pt × escala × (rango M1 mediano del oro en el mes anterior) / 6,25
  (rango M1 mediano de USATECH en el descubrimiento de U1, medido en `U1_ORO.json`). Causal por mes; el primer mes no dispara; un
  área no cruza el borde de un mes.
- **4.478.976 celdas por canal**, dos canales (`total` y `reciente`): el embudo registra 8.957.952 pruebas en el contador global
  antes de lanzar el DESC.

## 2. Datos y períodos
- DESC 2025-08-05 → 2026-03-31; OOS y pistas a réplica 2026-04-01 → 2026-09-30 (no usados por esta familia; la transferencia
  congelada `U1_ORO` sí los miró para la celda base: queda como linaje).
- Señal: XAU de Dukascopy (v4 recortada). Ejecución: GC del release con la fricción canónica (`edgelab/costos.py`).
- Holdout desde el 2026-10-23, N fijo 150, una sola apertura.

## 3. Decisión
La del embudo vigente (decisiones del 2026-10-24): tamiz FDR q 0,10 en DESC (linaje como información, campaña nueva); si 0
nominadas, top-20 pistas a réplica con un paso de LORD++; integridad (alineación, placebo, latencia), OOS por régimen con potencia,
topes, ACTA con α reservado y holdout a N fijo.

## 4. Justificación económica
U1 fue lo más rentable medido en USATECH→NQ. Si el regreso a áreas de huecos de cotización es microestructura del feed CFD de
24 h, el vecindario de la regla (otra escala, otro A/H, otra entrada) puede funcionar en el oro aunque la regla exacta no lo haga.

## 5. Cómo podría refutarse
0 nominadas y 0 pistas confirmadas; o confirmada con media neta ≤ 0 en el holdout. La transferencia congelada dio INCONCLUSO
(`RESULTADO_U1_ORO.md`): no se usa como ancla favorable.

## 6. Multiplicidad, linaje y riesgos
- Linaje: padres `U1_ORO` y `AREAS_EXP_1_CRUZADO` (bruto, ~19,4 M heredadas, como información en DESC).
- Riesgos: el spot no es el futuro a horizonte corto; cola sin tope (peor −44 USD en la transferencia); partir por mes pierde
  áreas en los bordes; noticias: el filtro de `edgelab/noticias.py` se aplica a las operaciones antes de cualquier confirmación.
