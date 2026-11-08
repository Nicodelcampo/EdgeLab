# Market Replay NT8: CVGAP-CFD-NQ, del 31/7 al 28/8/2026 (EdgeLabSignalReplay v1.2)

Estado: VIGENTE — primera medición válida de fricción en Market Replay (entrada en la misma vela que Python: apertura de k+2).
Comparación: `tools/senales_nt8.py comparar` → `../COMPARACION.json` y `../comparacion_por_operacion.csv`.

| | |
|---|---|
| Señales en el replay | 18 (2 del tramo histórico, 3 omitidas por posición abierta) |
| Operadas | 15; los motivos de salida coinciden con Python en 15 de 15 (7 stop, 5 objetivo, 3 tiempo) |
| Slippage de entrada | media **0,60 pts**, mediana 0,75, p90 1,15 (NQ: 0,25 pts = 1 tick) |
| Slippage en la salida por stop | media **0,61 pts** |
| Slippage en la salida por objetivo | 0 (el replay llena en el nivel: optimista) |
| P&L bruto NT8 frente a bruto Python, por operación | mediana −0,75 pts |

## Lectura

- **Costo ida y vuelta estimado:** entrada 0,60 + salida unos 0,28 de media (0,61 en los stops, que son 7 de 15) ≈ **0,9 pts de
  slippage**. Con la comisión (unos $4,5 ida y vuelta ≈ 0,23 pts de NQ) queda en ≈ **1,1 pts**. La fricción canónica de NQ es de
  **1,55 pts**: **el escenario G3 es conservador** frente a lo medido.
- **Límites:** son 15 operaciones, y el replay no tiene cola, impacto ni latencia de red. Tomarlo como **cota optimista**. El slippage real se mide
  en simulación con datos en vivo o en la cuenta de la prop firm.
- **Paridad de ejecución:** confirmada también en el replay (mismo motivo de salida en 15 de 15).
