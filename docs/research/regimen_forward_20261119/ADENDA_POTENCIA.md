# REGIMEN-FORWARD: adenda de potencia — la canasta T+R decide en ≈ 15 meses (≈ 33 con la mitad del efecto), no en 4–8 (2026-11-19)

Estado: VIGENTE — corrige la línea «Potencia previa» del pre-registro (`PREREGISTRO.md`); **no cambia ninguna regla de decisión** (cotas,
umbrales, mu0 y cortes siguen congelados). North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
Código: `tools/regimen_forward_tiempo.py` (descriptivo, sobre desarrollo ya mirado; `edgelab/funnel/secuencial.py::EProceso`).

- **El error:** el pre-registro estimó «e ≥ 20 en ≈ 4–8 meses» con una cuenta aproximada. La simulación del e-proceso real, con sus cotas
  [−6, +16], da:

| Media supuesta (R por día con operación) | EDGE | Corte por drawdown | Sin decidir (≈ 6 años) | Mediana hasta EDGE |
|---|---|---|---|---|
| desarrollo (+0,266) | 99,8 % | 0,2 % | 0 % | **≈ 14,5 meses** |
| contraída a la mitad (+0,133) | 74 % | 22 % | 4 % | **≈ 33 meses** |
| cero | 0,2 % | 98,6 % | 1 % | — |

- **Lectura:** el diseño discrimina bien (sin ventaja casi nunca da EDGE y el drawdown la corta), pero es lento: las cotas anchas [−6, +16]
  limitan cuánto apuesta el e-proceso. La futilidad con mu0 0,13 casi no actúa antes que el drawdown.
- **Posible mejora (cambio de semántica de validación → decisión de Nico, no se aplica):** cotas más ajustadas al rango diario real
  (p. ej. percentiles 0,5–99,5 % de desarrollo) o un e-proceso de mezcla por operación en lugar de por día acelerarían la decisión.
- Las demás series (T, R, SOM, Franklin) tienen frecuencias y efectos menores: sus tiempos del pre-registro también son optimistas; se
  reportan pero la decisión es la de la canasta.
