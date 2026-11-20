# A20 NQ en el holdout terminal: +31,9 R en 29 operaciones, todas cortas, con NQ cayendo 11 % (resultado, 2026-11-20)

Estado: RESULTADO — apertura única registrada antes de calcular (`FUNDEDSYNC::holdout_terminal_A20_NQ`, `ADENDA_HOLDOUT_TERMINAL_A20.md`).
Lectura **NO_CONCLUYENTE** (potencia 0,08).
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Datos:** `A20_TERMINAL.json`, `A20_TERMINAL_OPS.csv`, `A20_HOLDOUT_TERMINAL.png`. Herramienta `tools/a20_terminal.py`.

Episodios: por semana, en `A20_TERMINAL.json`.
- Dos semanas dan +28,5 de los +31,9 R: la del 12–16 de octubre (+10,4) y la del 2–6 de noviembre (+18,1).
- La semana del 9 al 13 de noviembre da −2,0.

## Resultado
- **Paridad:** el calentamiento de marzo a septiembre de 2026 reproduce `RZ_OPS` en 124 de 124 operaciones (misma entrada y mismo P&L).
- **Holdout (sesiones del 2026-10-01 al 2026-11-16, sin el 7-oct):**
  - n 29, en 22 sesiones;
  - **+1,10 R por operación**, +31,9 R en total;
  - p de una cola 0,072;
  - sd 3,71 y MDE80 1,72 R;
  - 52 % de aciertos.
- **Concentración:**
  - la mejor operación (5-nov, NQ −5,1 % en el día) da +15,9 R;
  - sin las 2 mejores quedan +7,2 R (+0,27 por operación);
  - sin las 3 mejores, +1,2 R.
- **Por mes:** octubre +15,8 R y noviembre (hasta el 16) +16,1 R.

## Lo que hay que saber para juzgarlo: A20 es una estrategia sólo corta
- **Todas sus operaciones son ventas**, en todos los años (`RZ_OPS`: lado −1 en el 100 % de 2021–2026).
- **En la ventana, NQ cayó:** −7,0 % en octubre y −4,3 % del 30-oct al 16-nov.
- **Descriptivo, sobre datos ya vistos.** Regresión del R mensual de A20 contra el retorno mensual de NQ:

| Ventana | Intercepto (R/mes con NQ plano) | t | Pendiente (R por cada 1 % de NQ) | t |
|---|---|---|---|---|
| 2018-01 → 2026-09 | +3,0 | 3,5 | −0,99 | −7,1 |
| 2022-01 → 2026-09 | +5,0 | 5,2 | −1,04 | −6,6 |

- **Lo que sale de la tabla:**
  - Por cada 1 % que cae NQ en el mes, A20 suma ≈ 1 R.
  - Con NQ plano, suma ≈ +3 a +5 R por mes.
  - Desde 2022 ganó +3,7 R/mes **aunque NQ subió 1,3 % por mes** en promedio. Esa parte no es beta corta.
- **El holdout cae dentro de lo que ese modelo predice:**
  - con el intercepto de 2022 y la pendiente, octubre predice ≈ +12 R (dio +15,8);
  - el medio noviembre predice ≈ +7 R (dio +16,1).
  - Es decir, el holdout no agrega evidencia de alfa más allá de la beta. Fue un mes y medio favorable a una estrategia corta.

## Lectura
- **NO_CONCLUYENTE**, sin potencia (K49): ni confirma ni refuta.
  - La regla no cambió.
  - La apertura queda gastada.
  - La confirmación de A20 es el forward.
- **Para decidir tamaño o canasta**, A20 debe tratarse como una posición corta de NQ con alfa propia:
  - **Cubre a T, R y Z**, que ganan con tendencia en cualquier dirección. Antes de sumarla hay que medir esa correlación.
  - **Pierde en los meses fuertes al alza:** −4,3 R/mes de media en los 48 meses con NQ > +3 % (2018–2026-09).
  - **En una cuenta prop** un mes alcista fuerte la lleva a la MLL. Una canasta T + R + A20 compensaría, pero eso hay que medirlo.
