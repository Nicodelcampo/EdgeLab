# A20-MULTIACTIVO: A20 de FundedSync en YM, RTY y EMD, índices donde nunca se midió (pre-registro, 2026-11-19)

Estado: PRE-REGISTRO — se commitea antes de correr.
- **Pedido de Nico:** «pruebas de robustez de picos o mesetas y multiactivo; que pasen por la cadena entera; luego abrimos el holdout»
  (sobre las reglas frecuentes que la revisión del 19-nov mostró descartadas por un promedio de épocas).
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Etapa EF3** (DESC de A5 en instrumentos nuevos). **Familia:** `A20_MULTIACTIVO`; linaje padre `FUNDEDSYNC` (información).
- **Herramienta:** `tools/a20_multiactivo.py`, con el mismo motor y la misma medida en R que NETO-PISTAS (stop duro propio de A20).
  `registro_global.exigir_contada` al inicio (K51).

Antecedentes:
- **A20-REGIMEN** (`../a20_regimen_20261119/RESULTADO.md`): INTERMEDIO en NQ; positiva desde 2022, ES −0,079.
- **REVISION_DESCARTADAS** (`../REVISION_DESCARTADAS_20261119.md`):
  - NQ 2018–2025-07: +0,052 R/op, 20 ops/mes;
  - 2022–2025-07: +0,185;
  - número efectivo de la grilla 1,19.
- **Factor:** F-A20-FUERA-DEL-FORWARD.
- **Por qué otros índices:**
  - **A20 no tiene holdout limpio en NQ ni en ES.** Sus operaciones se calcularon en todos los meses, y la familia FUNDEDSYNC ya abrió la
    ventana terminal.
  - En YM, RTY y EMD **nunca se calculó nada**. Sus meses HOLDOUT de A5 son la única confirmación limpia posible fuera del forward.

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v4 — §0–§7 (K33 costos estimados de EMD, K36 escalas, K49 potencia, K51, K55/K56).

Potencia previa:
- **Frecuencia:** A20 opera ≈ 20 veces por mes por índice, o sea ≈ 10 por mes en meses DESC por índice.
- **Muestra:** en 2018–2025-07, cada índice tiene ≈ 900 operaciones DESC y entre los tres ≈ 2.700.
- **Desvío:** el de NQ fue 2,3 R por operación (cola derecha).
- **MDE80 de la fábrica agrupada:** ≈ 0,12 R; por índice ≈ 0,22 R.
- **Lectura:** es una exploración de transferencia; un nulo no mata y se publica su MDE. El plan de potencia del holdout se registra antes
  de abrirlo.

Diagnóstico de mecanismo:
- La grilla de A20 tiene 1,19 variantes efectivas en NQ: tres de sus cuatro perillas casi no cambian las operaciones.
- Por eso no se lee «N/N vecinos» como meseta. Se publican, por índice, las operaciones por variante y el número efectivo con
  `edgelab.research.diagnostico_grilla`.
- La lectura es la fábrica y la dosis-respuesta de la perilla que sí mueve.

## Justificación económica
- **Mecanismo:** A20 sigue tendencias intradía con SuperTrend y un stop duro. Su ganancia viene de pocas operaciones grandes en días de
  tendencia: cola derecha, ≈ 25 % de aciertos.
- **Por qué se transferiría:** si el mecanismo es el momentum intradía de los índices y no un ajuste a NQ, debería aparecer en otros
  índices con fricción relativa baja.

## Reglas y decisión (fijas)
- **Variantes:** fábrica (7; 2,0; 2,5; 1,5) y los 8 vecinos a un paso: 9 variantes × 3 índices = **27 pruebas**.
- **Datos:** M1 real de futuros de NT8, 2008 → 2025-07; **régimen declarado 2018-01-01 → 2025-07-31**, sólo meses DESC de A5. Se guardan
  operaciones de DESC y REP; HOLDOUT y EMBARGO se descartan sin leerse.
- **Costos:** fricción canónica. EMD con spread ESTIMADO, declarado (`costos.estimados_permitidos` citando este archivo).
- **R neto:** (resultado − fricción) / riesgo inicial del stop duro.
- **TRANSFIERE:** la fábrica positiva en ≥ 2 de los 3 índices **y** ≥ 6 de 8 vecinos positivos en ≥ 2 índices.
- **Si TRANSFIERE:** apertura del holdout A5 de YM+RTY+EMD (meses HOLDOUT 2018–2025, regla congelada = fábrica, N fijo = todas las
  operaciones), con su plan de potencia registrado antes, y A20 entra en la vigilancia forward como serie separada.
- **Si no:** NO_TRANSFIERE con MDE. A20 queda sólo en NQ y sólo en forward.

## Cómo podría refutarse
- La fábrica ≤ 0 en los tres índices con MDE publicado.
- Vecinos en contra.
- El holdout de los índices nuevos con media ≤ 0.
