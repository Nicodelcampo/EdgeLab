# Analizador de estrategias (como el Strategy Analyzer de NT8)

Estado: VIGENTE
Fecha: 2026-10-26. Pedido de Nico: «un módulo donde solamente se mandan estrategias a backtestear».
Referente: `docs/NORTH_STAR.md`, cuerpo sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
Código: `edgelab/research/analizador.py`, CLI `tools/analizar.py`, ejemplo `edgelab/research/estrategias/ejemplo_ruptura_rango.py`,
tests `tests/research/test_analizador.py`.

## Uso
1. Escribir la estrategia en `edgelab/research/estrategias/<nombre>.py`: `NOMBRE`, `FAMILIA`, `INSTRUMENTO`, `PARAMETROS` (opcional,
   barrido) y `senales(barras, **params)` → lista de `{available_at, dir, target_pts, stop_pts, time_stop_min}`.
2. `python tools/analizar.py edgelab.research.estrategias.<nombre> 20240102 20260331 --kaggle` (o `--entrada <carpeta>` con datos
   locales). Devuelve, por variante: operaciones, neto total y por operación, IC90 por sesiones, acierto, profit factor, mejor/peor,
   drawdown, MAE/MFE, salidas, por mes y el neto sin las 5 mejores.

## Qué garantiza (no es un motor nuevo)
- **Fills**: `edgelab/research/sim.py`, el simulador sellado por spec (entrada en la barra siguiente a la señal, gana el adverso si
  objetivo y stop caen en la misma barra, cierre de sesión, firewall del holdout). `edgelab/engine.py` es legacy y no se usa.
- **Costos**: sólo la fricción canónica de `edgelab/costos.py` (la del futuro de referencia si el instrumento es un CFD), una vez por
  operación. Sin costo medido no corre.
- **Holdout**: pedir una ventana que toque la sesión del 2026-10-01 es un error.
- **Look-ahead**: antes de simular se verifica que las señales hasta un corte no cambien al ver datos posteriores (`NO CAUSAL`).
- **Multiplicidad**: cada corrida registra sus variantes en el contador global ANTES de correr; el reporte dice cuántas pruebas lleva la
  familia y marca EXPLORATORIO. Nada sale promovido: lo prometedor se pre-registra y va al embudo (réplica no mirada, holdout).

## Límites
Barras M1 (dentro de la barra no se sabe el orden de máximo y mínimo: el simulador asume el adverso). Una posición por vez por
estrategia. Para ticks reales con bid/ask, el simulador es el mismo pero hay que pasarle steps de ticks (pendiente).
