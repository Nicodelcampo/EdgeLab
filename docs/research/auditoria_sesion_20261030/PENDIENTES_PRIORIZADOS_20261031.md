# Pendientes priorizados (2026-10-31)

Estado: VIGENTE. Nada se descarta: cada punto tiene motivo y condición para reactivarlo.

## Ahora
1. Medir las 12 reglas con su `tope` real en el kernel (el recorte a posteriori da t 4,02 y está inflado).
2. Backtest independiente de las familias que no se aplanan (AVCL, CVGAP, BT2-ES, RACIMOS-NQ).
3. Momentum: filtro y confirmación, una definición fija, calibrar en DESC y evaluar en OOS. Requiere guardar el lado de la operación.
4. Pre-registro de la canasta, y recién ahí abrir el holdout con `canasta_regimen` corregido (#158).

## Después
5. `INTRADAY-MOM-EOD`, familia nueva chica (ES, NQ, YM).
6. U1 con zonas HFT en varios activos: cientos de celdas, no millones.
7. Variantes cercanas de lo que sobrevive, leyendo los 650 posts y el scrap.

## En cola, con condición
- Acciones underperformers (finvizfinance): cuando haya una estrategia firme y datos sin sesgo de supervivencia.
- TensorTrade: leer primero; aprendizaje por refuerzo sólo si aporta algo más que su simulador.
- Filtros transversales del patch V2: como perilla pre-registrada; la tabla sintética no vale.
- Momentum de 1 a 12 meses: cuando haya muchos instrumentos.
- SV1: reconciliar estados y actualizar; requiere al Claude Code de SV1 o permiso ampliado. Sigue pausado.
- NT8: arnés de paridad contra Strategy Analyzer cuando haya una confirmada.
- Sistema multiagente y modularización en espiral: informe largo pendiente.

## Agregado 2026-10-31
- Tope: se decide una vez, con DESC. Riesgo de cuenta (pérdidas de −268 en NQ): límite común de la canasta, por tamaño o pérdida diaria.
- Prueba de perturbación: ±1 nivel en cada perilla de las reglas con acta, antes de congelar la canasta.
