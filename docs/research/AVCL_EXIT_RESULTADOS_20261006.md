# AVCL-EXIT — salida de la zona contra pseudo-zonas — resultados MNQ — 2026-10-06

- Manifiesto: `AVCL_EXIT_MANIFIESTO_20261006.md`. Kernel `edgelab-avcl-exit-20261006` (92 s), cache de la celda base.
- JSON: `avcl_vol1_20261005/AVCL_EXIT_RESULTADOS.json`. 9 pruebas, familia `AVCL_EXIT`.
- Unos 34 k salidas reales y unos 101 k de pseudo-zonas por k (RTH).

## Formal (9, Holm, bilaterales): real − pseudo
| k | continuación c_10 (ticks) | continuación c_50 (ticks) | `y_rg_10` en la salida |
|---|---|---|---|
| 4 | +0,15 (MDE 0,38), Holm 1 | −0,13 (MDE 0,76), Holm 1 | **+0,107** (MDE 0,007), Holm <1e-4 |
| 8 | +0,13 (MDE 0,37), Holm 1 | +0,04 (MDE 0,78), Holm 1 | **+0,078** (MDE 0,008), Holm <1e-4 |
| 16 | +0,10 (MDE 0,31), Holm 1 | +0,01 (MDE 0,75), Holm 1 | −0,002, Holm 1 |

**Lectura pre-registrada: la salida de una zona real NO continúa más que la de una banda idéntica sin anomalía.** La
continuación media es ≈ 0 con MDE de 0,3–0,8 ticks. Lo que sí hay, para k chico, es **más rango** después de la
salida, pero las dos colas suben (k = 8: continuación +1,4 pp, **falla +2,1 pp**). Es la misma expansión bidireccional
de siempre, ahora medida desde la salida.

## Perfil de las salidas (lo que explica la muestra)
- Lag mediano de **1 / 3 / 9 barras** (k 4 / 8 / 16), igual que en las pseudo-zonas. **La gran mayoría de las salidas
  son inmediatas**: las zonas OFF nacen pegadas al precio.
- La consolidación previa es rara: mediana 0 cierres dentro de la banda. Las salidas "tras consolidar" (≥ 5 cierres
  dentro) son unas 4,3 k de 34 k (13 %).
- Ruptura (atravesar) en OFF: 17 % real contra 18 % pseudo (k = 8). No hay diferencia.

## Descriptivos (k = 8)
| grupo | c_10 | c_50 | cola continuación H50 | cola falla H50 |
|---|---|---|---|---|
| AT | +0,31 (MDE 0,57) | +0,50 (MDE 1,13) | −0,2 pp | −0,3 pp |
| OFF | −0,04 | −0,26 | 0,0 | +0,4 |
| OFF ruptura | −0,04 | 0,00 | +1,5 pp (MDE 1,7) | +0,7 |
| **tras consolidar (cons ≥ 5)** | **+0,62** (MDE 0,86) | +0,57 (MDE 1,88) | **+2,3 pp** (MDE 1,5) | +0,8 pp |
| Q5 anomalía | +0,07 | −0,06 | −0,1 | −0,3 |

El único subconjunto que se inclina a "continuar" es **la salida tras consolidar**, que es justamente el caso de varias
capturas de Nico: c_10 +0,6 ticks y cola de continuación a H50 +2,3 pp, contra +0,8 pp de falla. **No es
significativo** (n = 4,3 k, MDE ≈ efecto) y es descriptivo. Queda como **la hipótesis más concreta para pre-registrar**,
con más datos: otros contratos/instrumentos, o 200t.

## Estado
- `SALIDA SIN CONTINUACIÓN PROPIA (población completa)`.
- `SALIDA TRAS CONSOLIDAR: candidata, no probada`.
