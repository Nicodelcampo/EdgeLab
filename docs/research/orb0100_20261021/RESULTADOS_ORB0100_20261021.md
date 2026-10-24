# Resultados ORB0100 — rango 01:00-01:15 NY (estrategia de Instagram) y 48 variantes, NQ IS/OOS + ES externo

Estado: MEDIDO. Manifiesto `MANIFIESTO_ORB0100_20261021.md` (antes de correr). Codigo `tools/orb0100/orb0100.py`.
Salida `RESULTADOS_ORB0100.json` (48 celdas completas) y `.csv` (todas las operaciones). Senales: NQ 166 dias, ES 178.
IS = NQ ago-dic 2025 (104 dias con senal); OOS = NQ ene-mar 2026 (62); ES = mismo periodo (178).

## La estrategia tal como vino (TP 0,5R, SL rango, entrada a mercado, sin filtro)
| | n | acierto | pts/op | USD/op | factor | max DD USD | IC 95 % pts/op |
|---|---|---|---|---|---|---|---|
| IS, costos MNQ | 104 | 63,5 % | -1,35 | -2,71 | 0,85 | 543 | [-5,8, +2,9] |
| OOS, costos MNQ | 62 | 71,0 % | +2,27 | +4,53 | 1,19 | 372 | [-5,8, +9,9] |
| OOS, costos NQ | 62 | 71,0 % | +2,66 | +53,2 | 1,22 | 3.622 | [-5,7, +10,6] |
| ES externo | 178 | 62,4 % | -0,44 | -22,0 | 0,81 | 7.777 | [-1,2, +0,3] |
El +70 % de acierto del tablero de NT8 coincide con el OOS (NT8 mira sobre todo 2026), pero en IS y en ES la regla pierde:
con TP 0,5R el equilibrio exige ~67 % y la estrategia anda por ese borde.

## Grilla (48 celdas, costos MNQ)
- Diagnostico: OOS **47/48 celdas positivas** (mediana +4,7 pts) contra IS 18/48 (mediana -0,53) y ES 17/48 (mediana -0,08):
  el trimestre ene-mar 2026 de NQ favorece casi cualquier variante (efecto de periodo; se reporta, no se usa para elegir).
  Correlacion IS-OOS entre celdas 0,22 (algo de consistencia); IS-ES ~0.
- Patrones: **filtro VWAP > EMA > ninguno**; **SL en el otro lado del rango > SL en la mitad** (la mitad aumenta friccion
  relativa y pierde en todas); **TP mas grande (1-1,5R) > 0,5R**; **entrada limite** reduce drawdown y el costo de entrada
  pero gana menos (se pierden las rupturas que no vuelven).
- Friccion: MNQ cuesta 0,62 pts/op de comision vs 0,225 en NQ: con la misma regla, NQ ahorra ~0,4 pts/op (~8 % de la mejor celda).

## Seleccion (solo IS) y supervivencia
| celda (TP / SL / entrada / filtro) | IS pts/op (n) | OOS pts/op [IC] | ES pts/op [IC] | sobrevive |
|---|---|---|---|---|
| **1,5R / rango / mercado / VWAP** | +5,47 (67), PF 1,39, DD $518 | +15,4 [-4,1, +34,9] | **+0,24** [-1,5, +2,1] | **si (al limite)** |
| 1,0R / rango / mercado / VWAP | +4,58 (67), PF 1,40, DD $372 | +11,4 [-3,1, +25,3] | -0,45 | no |
| 0,75R / rango / mercado / VWAP | +2,75 (67) | +6,8 | -0,20 | no |

## Lectura
- La regla original no tiene edge neto demostrable: pierde en IS y en ES; lo positivo es el trimestre 2026.
- La familia "rango 01:00 + ruptura + VWAP a favor + TP grande" es la unica direccion consistente (IS y OOS positivos), y
  una celda pasa la regla escrita, pero con ES casi en 0 y ningun IC excluyendo 0. Multiplicidad: 48 celdas.
- Siguiente paso permitido por el manifiesto: **una** replicacion NQ abr-sep 2026 de esa celda exacta (requiere OK de Nico).

Aporte al referente: convierte una estrategia de redes en numeros con costos e IS/OOS; descarta la version original y deja
una sola variante con consistencia para una prueba unica.
