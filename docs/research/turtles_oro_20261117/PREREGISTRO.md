# Turtles en oro con cierre del viernes: réplica, mejora y camino al forward (pre-registro, 2026-11-17)

Estado: PRE-REGISTRO — commiteado antes de correr. Pedido de Nico: «¿cuánto opera Turtles 55/20? Hacé tu mayor esfuerzo por mejorarla, en
rentabilidad y, si opera poco, en potencia. Y luego al forward». North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
Origen: pista `F-TURTLES-ORO-VIERNES` (catálogo SQX, `docs/research/sqx_catalogo_20261117/RESULTADO.md`). Método: `docs/research/
mejora_estrategias_20261116/CRITERIOS_Y_PLAN.md` (criterios C1–C5, una perilla por vez, elegir en pares y confirmar en impares). Etapa EF3.

## Qué es la regla hoy (medido en el catálogo, 2011 → 2026-09)
**83 operaciones en 15 años: 5,6 por año**; 78 de 83 salen por el cierre del viernes (mediana 3 velas). No es un turtle de tendencia larga: es
**«ruptura al cierre del máximo (mínimo) de 55 días en oro, con EMA20 > EMA350 y ATR10 < ATR200, y mantener hasta el viernes»** (stop 2 ATR20).
Original sin cierre semanal: 34 operaciones y 3 explican 32 de 33 R (cola de 2025); por eso la pista es la variante del viernes.

## 1. Réplica en datos NO mirados (2004–2010)
El catálogo leyó el M1 desde 2010-06 (primeras operaciones en 2011). El XAUUSD M1 de Dukascopy empieza en 2003-05: **2004–2010 nunca se
evaluó con esta regla**. Prueba única pre-registrada: base (regla del catálogo, sin cambios) en operaciones con entrada 2004-01-01 → 2010-12-31:
**replica si R neto > 0 y p < 0,10** (bootstrap por sesión, `reels_20261116.tramo`); con menos de 30 operaciones, NO_EVALUABLE (no mata). Se
publica el MDE.

## 2. Mejora (desarrollo 2011-01 → 2026-09-29, sin 2004–2010)
Base = la regla del catálogo (`sqx_catalogo.turtle_v()` con perillas de fábrica, idéntica a `turtle(55, 20, True)`: test). Motor del catálogo
con el orden dentro de la barra por M1 (enmienda 1 del catálogo). Costos canónicos (GC; SI con spread estimado, 2 ticks, comisión Topstep 4,32).

| Variante | Categoría | Perilla | Mecanismo / cómo podría refutarse |
|---|---|---|---|
| `reentrada_lunes` | frecuencia | si el turtle sin cierre semanal seguiría adentro, re-entra a la apertura de la sesión siguiente al viernes | Recupera la tendencia larga sin fin de semana; se refuta si las re-entradas pierden (la ventaja era sólo la semana de la ruptura) |
| `canal_20` | frecuencia | canal de entrada 20 en vez de 55 | Más rupturas (sistema 1 de los turtles); se refuta si las rupturas cortas son ruido en el oro |
| `h4` | frecuencia | misma regla en velas H4 | Ruptura de ~9 días: más señales; se refuta si la fricción o el ruido intradía la anulan |
| `metales` | frecuencia | base en GC + plata (SI, D1 de SQX) | Mismo mecanismo en el metal hermano: más N; se refuta si la plata no acompaña (el efecto es sólo del oro 2020–26) |
| `sin_filtro_vol` | filtro | sin ATR10 < ATR200 | El filtro corta rupturas con volatilidad, que son las que siguen; se refuta si sin él baja el t |
| `sin_filtro_tend` | filtro | sin EMA20 vs EMA350 (los dos lados siempre) | El filtro de tendencia podría ser redundante con la ruptura de 55 |
| `solo_largos` | filtro | sin cortos | Deriva estructural del oro; se refuta si los cortos aportan |
| `entrada_stop` | entrada | orden stop en el borde del canal (entra en la ruptura, no al cierre) | Captura el tramo de la ruptura del propio día; se refuta si las rupturas intradía fallan más |

- **Elección (años pares 2012…2026):** elegibles con fricción mediana ≤ 0,08 R y **no menos años pares positivos que la base**; finalistas =
  las 3 de mayor **t del R mensual** (meses sin operaciones = 0) + la combinación de las dos mejores de categorías distintas que superen a la
  base (si su fricción ≤ 0,08). Máximo 4.
- **Confirmación (años impares 2011…2025):** diferencia mensual variante − base > 0 con p < 0,10 (bootstrap por mes, 20.000), **BH q 0,10
  sobre las finalistas**, R de la variante > 0 en impares, **y R > 0 en 2004–2010** (descriptivo para la base, requisito para la ganadora).
  Si hay más de una, gana la de mayor t mensual en impares.
- Se publica todo (pares, impares, 2004–2010, ops/año, R/op, R bruto, R/mes, t mensual, años positivos, drawdown en R, fricción).

## 3. Holdout y forward (se decide ahora, se ejecuta después de la mejora)
- Familia nueva `TURTLES-ORO` (linaje de `SQX_CATALOGO`): **una apertura** del holdout 2026-10-01 → 2026-11-13 con XAUUSD sellado, regla
  **congelada**: la base, y la ganadora si la hay (en paralelo, como versión 2). Acta propia antes de abrir.
- Lectura: CONFIRMADA si R > 0 y Fisher (holdout × desarrollo) < 0,05; EN_CONTRA si R < −1 EE; si no, NO_CONCLUYENTE. Con ~1 operación por
  mes esperamos NO_CONCLUYENTE: lo decide el forward (e-proceso, `edgelab/funnel/secuencial.py`), bajo demanda con `tools/seguimiento_forward.py`.
- Operable en GC o MGC (micro): nada abierto el fin de semana.

## Justificación económica / cómo podría refutarse
Ruptura de máximos de 55 días en un activo con demanda persistente (bancos centrales, cobertura): los participantes que entran tarde empujan
la semana de la ruptura (momentum de corto plazo tras nuevo máximo). Se refuta con la réplica 2004–2010 negativa con potencia, o con un forward
cuyo e-proceso cae.

## Contador y linaje
`turtles_oro_20261117/REPLICA` 1 + `turtles_oro_20261117/MEJORA` 8 variantes + 1 combinación = 10. Linaje `TURTLES-ORO` ← `SQX_CATALOGO`.
