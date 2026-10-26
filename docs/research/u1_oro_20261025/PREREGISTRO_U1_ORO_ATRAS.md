# Pre-registro — U1-ORO-GRILLA «hacia atrás»: la regla congelada sobre XAU 2023-01 → 2025-07

Estado: PRE-REGISTRO (commiteado antes de correr). Fecha: 2026-10-26.
Referente: `docs/NORTH_STAR.md`, cuerpo sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
Familia `U1_ORO_GRILLA`. Etapa EF4 (confirmación de una regla congelada en datos que la familia no usó).
Motivo: pedido de Nico (2026-10-26) «con los mismos datos, agregarle potencia a los experimentos que les falte»; método 1 de
`docs/research/POTENCIA_MISMOS_DATOS_20261026.md`.

## Regla (congelada por TOPES del embudo, `embudo/U1-ORO-GRILLA/estado.json`)
Celda `[0, 1, 0, 1, 2, 1, 3, 2, 3, 0, 16]` de `edgelab/research/u1_oro.py` con tope de pérdida ('pts', 50) y los cortes de variables
del DESC, sin cambios. Señal y ejecución sobre XAU de Dukascopy con la fricción canónica de GC (proxy declarado: GC sólo existe en el
release desde jul-2025). Escala causal mensual como en la grilla.

## Datos
XAU 2023-01-02 → 2025-07-31 (31 meses), anteriores al DESC de la familia (2025-08-05 → 2026-03-31) y nunca usados por ella. Nada del
holdout. Ritmo del DESC: 41 operaciones en 8 meses → se esperan ≈ 160.

## Decisión (una prueba)
Media neta por operación, bootstrap de sesiones, p unilateral; paso de LORD++ de la familia **reservado antes de lanzar**
(`U1_ORO_GRILLA::U1-ORO-ATRAS`). **A FAVOR** si rechaza al nivel reservado y la media adversa > 0; **EN CONTRA** si media ≤ 0 con MDE
menor que la media del DESC (+6,58 USD/oz); si no, **NO_CONCLUYENTE**. El holdout a N fijo (acta ya registrada) sigue siendo la
confirmación; esto no la reemplaza ni la cambia.

## Cómo podría refutarse
Media neta ≤ 0 con potencia en 2023–2025.

## Riesgos
Régimen distinto (el oro 2023–2025 tuvo otra volatilidad: la escala mensual lo absorbe en parte); proxy XAU vs GC.
