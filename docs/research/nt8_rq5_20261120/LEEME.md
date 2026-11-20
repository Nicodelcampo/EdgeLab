# Estrategias NT8 de RQ5 y de la canasta (2026-11-20)

Estado: VIGENTE — código para paper y forward. **No compilado en este entorno** (no hay compilador de C#): compilar en NinjaTrader 8 y
correr la paridad antes de usarlo.
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Ninguna es un edge promovido.**

## Archivos
- **`nt8/strategies/EdgeLabRQ5.cs`:** RQ5, fábrica de RQ5-REGIMEN, en el instrumento del gráfico. La regla exacta está en el encabezado del
  archivo y sale de `edgelab/research/rq5_regimen.py` y `ejecucion.py`.
- **`nt8/strategies/EdgeLabCanasta.cs`:** la misma RQ5 en el gráfico (NQ/MNQ) más índices opcionales, y una guarda de cuenta.
  - **DLL:** USD por día, medido sobre toda la cuenta.
  - **Piso:** valor líquido mínimo de la cuenta.
  - **Plano:** a la hora fijada (16:45 ET para Lucid).
  - La guarda actúa sólo en tiempo real y cierra **todas** las posiciones de la cuenta, también las de otras estrategias (FundedSync).

## Paridad
- **Archivo:** `RQ5_NQ_REFERENCIA_PARIDAD.csv`, con las 88 señales de Python en NQ de 2025-01 a 2025-07 (fecha, hora de cierre ET, lado,
  cierre, stop, objetivo, ATR).
- **Cómo:** gráfico de 1 minuto de NQ, Market Replay o backtest en esas fechas, con unos 4 meses de calentamiento para la historia de la
  banda (≥ 10 sesiones por horario; L = 60).
- **Comparación:** las líneas «RQ5;SEÑAL;…» de la ventana Output contra el CSV. Tienen que coincidir la fecha, la hora y el lado, y el
  stop y el objetivo dentro de un tick.
- **Diferencias esperables:** días de datos faltantes en NT8, y el ATR de los primeros días si el calentamiento es corto.

## Diferencias declaradas con Python
- **Llenado fuera de rango:** si el llenado ya pasó el stop o el objetivo, Python descarta la operación; NT8 la cierra en el acto
  (INVALIDA).
- **Salida de las 16:00:** NT8 sale con la orden al cierre de la vela de las 16:00 (llena en la apertura siguiente); Python, al cierre de
  la vela que abre a las 15:59.
- **Stop dentro de la vela:** Python lo cobra en su nivel; NT8, al precio real de llenado. El slippage real es lo que mide el forward.
