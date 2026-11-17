# Acta de apertura del holdout y forward: TURTLES-ORO (2026-11-17)

Estado: VIGENTE — escrita y commiteada ANTES de abrir. Familia `TURTLES-ORO` (linaje `SQX_CATALOGO`), una sola apertura.
North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.

## Regla congelada
La **base** (la mejora no dejó ganadora, `RESULTADO.md`): `edgelab.research.sqx_catalogo.turtle_v()` con perillas de fábrica en velas D1 del
oro (sesión desde las 18:00 NY), `simular(viernes=True)` con orden dentro de la barra por M1. Ruptura al cierre del máximo (mínimo) de 55
días con EMA20 > EMA350 (<) y ATR10 < ATR200 (en la barra anterior); entra a la apertura siguiente; stop 2 ATR20; sale al cierre del viernes, por el
stop o por el canal de 20. Costo: fricción base de GC (0,605 puntos por vuelta, `edgelab/costos.py`). R = (puntos − 0,605) / |entrada − stop|.

## Datos
Desarrollo: XAUUSD M1 de Dukascopy (dataset `edgelab-sqx-m1`, hora del servidor = NY + 7, completo desde 2003 para que la EMA350 sea la
misma). Holdout/forward: XAUUSD sellado (`edgelab-holdout-sellado`, `fuentes_ticks.bloques_spot_sellado`, sesiones declaradas excluidas
fuera). **Hueco conocido**: la sesión del 2026-09-30 no está en ninguno de los dos (el M1 termina el 29-sep 16:59 NY y el sellado empieza en la
apertura del 1-oct); falta una barra D1 y se acepta (no se rellena).

## Ventanas y lectura
- **Holdout**: operaciones con entrada 2026-10-01 → 2026-11-13. Esperado ≈ 0,6 operaciones (5,3 por año).
- p de desarrollo para Fisher: **0,32** = p de la base 2004 → 2026-09 (0,0023, bootstrap por sesión) × 136 (Bonferroni por haberla elegido
  entre las 136 del catálogo). Lectura: CONFIRMADA si R > 0 y Fisher < 0,05; EN_CONTRA si R < −1 EE; si no, NO_CONCLUYENTE.
- **Forward**: sesiones desde 2026-11-14, bajo demanda (`tools/seguimiento_forward.py`), e-proceso (`EProceso(mu0=0, piso=−6, techo=6)`):
  EDGE si e ≥ 10; LIMITE_VIOLADO si un R sale de [−6, 6]. Potencia: para t = 2 con R 0,22 y desvío ≈ 0,64 hacen falta ≈ 34 operaciones
  (≈ 6 años); el forward de esta regla sola es lento, por eso va como pieza de diversificación de la cartera, no como decisión aislada.
- Nada de esto se usa para elegir ni ajustar.
