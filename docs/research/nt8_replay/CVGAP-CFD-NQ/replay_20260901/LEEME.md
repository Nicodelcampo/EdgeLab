# Replay NT8 del 2 al 4/9/2026 (CVGAP-CFD-NQ)

Estado: DESCARTADA como medida de fricción; vale como paridad de salidas.

- **Paridad de salidas: válida** (6/6 con el mismo motivo; stop y objetivo son niveles absolutos).
- **Slippage de entrada: no válido.** La señal se mandó al cierre de la vela de decisión k, así que NT8 llenó en la apertura de k+1.
  Python llena la entrada SIG en la apertura de k+2 (`niveles` arranca en k+1 con límite 2). La diferencia mezcla un minuto de precio
  con la fricción.
- `tools/senales_nt8.py` ya exporta `t = t_fill − 60` para las entradas a mercado. El `senales.csv` está regenerado; hay que volver a
  correr el replay.
