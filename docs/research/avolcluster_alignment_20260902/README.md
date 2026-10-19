# Alineación de barras NT8↔Python — hipótesis REFUTADA (2026-09-02)

Kernel `avolcluster-alignment-20260902`, code_commit `484c5e7`. Target-free, sin tocar código.

## La hipótesis

Tras el cruce completo (sólo 16 de 22.200 bloques con celdas idénticas, 82 % con ruido de
valor, 9.479 celdas que sólo NT8 tenía), la sospecha principal era que **las barras de 120
ticks estuvieran desalineadas**: si el bloque de Python cubriera las barras 10-19 y el de
NT8 las 11-20, todo divergiría sin ningún bug de lógica.

## Refutada

| | |
|---|---|
| `median_abs_dt_ns` | **0** |
| bloques mapeados con Δt < 1 s | **22.507 / 22.507** |
| offset dominante | **0**, con **99,98 %** (4.501 de 4.502) |
| `sum_abs_diff` en offset 0 | **53.809** |
| `sum_abs_diff` en offset ±1 | ~1.052.434 / ~1.112.682 |

El offset 0 es **20 veces mejor** que sus vecinos inmediatos. La partición coincide y los
timestamps de cierre de barra son idénticos al nanosegundo. **No hay desalineación.**

Esto se apoya además en la estructura del CSV: **0 de 51 sesiones** tienen huecos internos
—los bloques son exactamente consecutivos de 10 barras— y los gaps entre sesiones (10-19
barras) son el resto que NT8 descarta al cerrar cada sesión.

## Lo que queda aislado

Con la alineación descartada, el problema está acotado: **mismas barras, mismos
timestamps, distinto volumen por celda**.

- celdas exactas con offset 0: **2 de 4.502**
- volumen total exacto con offset 0: **623 de 4.502 (13,8 %)**

Que el volumen **total** difiera en el 86 % de los bloques significa que no es sólo una
cuestión de asignar volumen al precio equivocado: hay ticks de más o de menos.

## Valor de haber refutado esto

Era la explicación que cubría todos los síntomas a la vez y no costaba nada creer. Medirla
costó una corrida de 54 segundos y evitó rediseñar el particionado —o peor, "arreglarlo"
introduciendo un offset que habría empeorado todo 20 veces.

Siguiente test, ya acotado: NT8 descarta por barra los ticks fuera de `[Low[0], High[0]]`.
Ese filtro se puede **replicar exactamente** en Python y medir si el footprint converge.
