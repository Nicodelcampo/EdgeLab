# Especificación Pre-Registrada: Familia `TORI-TREND-TOQUE3` (`2026-10-29`)

- **Módulo experimental:** `edgelab/research/tori_trend_toque3.py`
- **Origen en la Biblioteca de Ideas:** Paper de Tori Trades (*"The Trend Is Your Friend Until the End: A Stopping-Time Theory of Swing Trading with Trendlines and Market Structure"*, 26-oct-2026) + Post #943 (`@ifriendlytrader`), acoplado en espiral con `ZONAS-GAPS` y `EmaCorridorTrendVolW2`.
- **Mecanismo económico:** Los operadores sistemáticos y discrecionales de swing colocan órdenes de defensa y stops detrás de rectas de soporte/resistencia definidas por pivotes confirmados (`k in {3, 5, 8}`). En el 3.er contacto tras un enfriamiento mínimo, la absorción de liquidez (mecha + volumen) regenera la tendencia; inversamente, cuando el cierre quiebra la recta por más de `0,30 * ATR14` (tiempo de parada `tau`), la activación en cascada de stops impulsa la reversión o el throwback hacia los gaps abiertos en el camino.
- **Cómo podría refutarse:** `0` celdas nominadas por FDR (`q <= 0,10`) en `DESC`, fallo ante placebo/latencia en `INTEGRIDAD`, o media neta `<= 0` en `OOS`/`HOLDOUT`.
