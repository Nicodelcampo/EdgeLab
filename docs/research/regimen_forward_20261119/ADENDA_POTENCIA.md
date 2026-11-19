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

## Ejecutabilidad de R (agregado 2026-11-19, auditoría)
- El DLL de FundedSync **no tiene stop para R** (AtrPhase sólo sale por cierre de contado a las 16:00; `defaults_dump.txt` y
  `AtrPhaseConfig`). La R vigilada acá lleva el stop de catástrofe 0,25 × ATR20 que agregó NETO-PISTAS: medirla sobre las operaciones del
  vendedor está bien (el stop se aplica con la MAE), pero **operarla así exige implementar el stop por fuera del DLL**.
- Diferencia medida (NQ, fábrica): sin stop la media es parecida o mejor (+0,275 R contra +0,269 en 2008–2026; +0,67 contra +0,51 desde
  2021, en unidades de 0,25 × ATR20), pero la cola es mucho más pesada (peor operación −6,3 unidades ≈ −1,6 ATR20; percentil 1 % ≈ −4,5). Con
  1 MNQ y el ATR actual de NQ, una sola operación de la cola se acerca al límite diario de Lucid (DLL $600): **sin el stop, R no es apta
  para la cuenta**.
- Opciones (decisión de ejecución de Nico): (a) estrategia NT8 propia de R con el stop (la traducción en Python es la especificación); (b)
  correr el DLL con R y una orden de stop manual o del bróker a 0,25 × ATR20 del precio de entrada; (c) T sola en Lucid hasta resolverlo.

## Estrategia NT8 propia para R con stop (agregado 2026-11-19)
- `nt8/strategies/EdgeLabAtrPhaseStop.cs`: traducción de `run_r`/`_AtrPhaseEngine` (oscilador de fase en 10 min, VWAP, ventana 09:30–11:00,
  reversa, cierre 16:00 ET, reinicio por vencimiento) con el stop de catástrofe 0,25 × ATR20 de sesión (parámetro `MultiploStop`) y la lista
  de fechas del vendedor desactivada por defecto. Cierra antes de las 16:45 ET (Lucid).
- **No está compilada ni probada** (el contenedor no tiene NinjaTrader ni compilador C#). Antes de usarla: compilar en NT8 y correr el
  protocolo de paridad (`docs/nt8_indicator_parity_contract.md`) contra `R_REFERENCIA_PARIDAD.csv` (56 operaciones del simulador en Python,
  NQ 2024-01 → 2025-07, con la lista del vendedor ACTIVADA, como el simulador: poner `UsarFechasVendedor = true` para la paridad).
  Columnas: sesión, minuto de entrada ET (= apertura de la vela de 1 min siguiente al cierre de 10 min), lado, resultado en puntos sin
  stop, MAE, ATR20, distancia del stop y si el stop se habría tocado.
- **Paridad del algoritmo (verificada, 2026-11-19):** `tools/paridad_atrphase_nt8.py` reimplementa línea a línea la lógica del C# (velas de
  10 min armadas como NT8 desde el M1, llenado en el minuto siguiente, reversa un minuto después) y la compara con el simulador: **56/56
  entradas idénticas (minuto y lado), 0 sobrantes, 0 faltantes** (NQ 2024-01 → 2025-07, `PARIDAD_ALGORITMO.json`). El primer intento dio 0 %
  por la convención de sello (NT8 y el simulador sellan la vela de 1 min con su CIERRE); se corrigió la etiqueta, no la lógica. Queda la
  paridad dentro de NT8 (compilación, plantilla ETH, zona horaria de la PC, eventos de órdenes).
