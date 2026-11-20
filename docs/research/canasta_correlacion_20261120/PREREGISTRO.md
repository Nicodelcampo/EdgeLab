# CANASTA-CORRELACION: correlación entre A20, T, R, Z-banda y RQ5 y la canasta conjunta (pre-registro, 2026-11-20)

Estado: PRE-REGISTRO — descriptivo, se commitea antes de calcular.
- **Pedido de Nico (2026-11-20):** «Medí la correlación entre todas y también deja registrado eso y todo lo que hicimos. Luego genera una
  estrategia de nt8 por cada una de estas estrategias que son prometedoras. También genera una que una todas en la misma».
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Etapa EF2** (descriptivo sobre operaciones ya medidas). **Familia:** `CANASTA_CORRELACION`; linaje padres `FUNDEDSYNC` y
  `RQ5_REGIMEN` (información). Es 1 lectura (la canasta), sin selección.
- **Herramienta:** `tools/canasta_correlacion.py`. Reusa `tools/filtros_contexto.py::operaciones` (mismas reglas y R que sus actas). Llama a
  `registro_global.exigir_contada`.

Antecedentes:
- FILTROS-CONTEXTO: SIN_FILTRO.
- A20 holdout terminal: NO_CONCLUYENTE; A20 es sólo corta (−1 R por cada 1 % de NQ).
- RQ5-REGIMEN: REGIMEN_ROBUSTO en DESC, holdout A5 NO_CONCLUYENTE.
- Canasta B (T + Z + R) en forward.

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v4 — §0–§7 (K36 escalas: todo en R; K52 tamaño fijo de 1 R por operación; K56 episodios).

Potencia previa: no aplica a una prueba. Es una descripción de 91 meses (DESC + REP, 2018-01 → 2025-07) con entre 170 y 3.860 operaciones
por estrategia. Se publica el t mensual de la canasta. No se abre holdout ni se decide tamaño con esto.

Diagnóstico de mecanismo: no aplica (sin grilla). Las reglas son las fábricas ya congeladas. Se publican los episodios: el peor mes, la
máxima caída en R y los meses con NQ > +3 % y < −3 %.

## Justificación económica
- A20 vende tendencias. T, R, Z y RQ5 siguen tendencias en las dos direcciones.
- Si sus ganancias vienen de días distintos, o A20 cubre los meses alcistas en que las otras ganan, la canasta reduce la varianza mensual
  sin bajar el R por mes. Eso importa en una cuenta prop, por el DLL y la MLL.

## Qué se calcula (fijo)
- **Series:** R neto diario por estrategia (suma de sus operaciones; 0 los días sin operación), en los meses DESC y REP de A5 entre
  2018-01-01 y 2025-07-31. RQ5 va en dos formas: los cuatro índices (NQ, ES, YM, RTY) y sólo NQ.
- **Correlaciones:** Pearson y Spearman, diarias y mensuales, de cada par. También la correlación mensual con el retorno de NQ.
- **Canasta (1 R por operación en cada estrategia):** todas en NQ (A20 + T + R + Z-banda + RQ5-NQ), sin A20 y con RQ5 en los cuatro
  índices.
  - Por cada canasta: R/mes, t mensual, % de meses positivos, peor mes, máxima caída en R y peor racha de días.
  - También el R/mes por terciles de retorno mensual de NQ.

## Cómo podría refutarse
- Correlaciones altas entre todas (mensual > 0,5): no diversifican.
- La canasta con A20 no baja la caída máxima respecto de la canasta sin A20: A20 no cubre.
