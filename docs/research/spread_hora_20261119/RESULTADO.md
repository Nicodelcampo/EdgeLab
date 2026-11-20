# Spread real por hora del día en NQ, ES y YM: el costo canónico es correcto y la hora casi no cambia nada (medición, 2026-11-19)

Estado: RESULTADO — medición sin retornos (target-free), pedida en FRICCION-RQ («otras maneras de reducir la fricción»).
Kernel `tools/medir_spread_main.py` (criterio del atlas v4: ask − bid con libro válido, 08:30–15:00 CT, sesiones de desarrollo
2025-08-05 → 2026-03-31 del release `liquid_tick_v1`), ahora con desglose por hora CT. Datos: `SPREAD_{NQ,ES,YM}.json`.

| Hora CT | NQ media (mediana, % a 1 tick) | ES media (% a 1 tick) | YM media (% a 1 tick) |
|---|---|---|---|
| 08 | 3,57 (3; 11 %) | 1,11 (94 %) | 2,11 (30 %) |
| 09 | 3,23 (3; 15 %) | 1,09 (95 %) | 1,92 (41 %) |
| 10 | 2,90 (2; 19 %) | 1,07 (95 %) | 1,82 (44 %) |
| 11 | 2,82 (2; 21 %) | 1,08 (95 %) | 1,86 (44 %) |
| 12 | 2,81 (2; 22 %) | 1,08 (95 %) | 1,87 (43 %) |
| 13 | 2,79 (2; 23 %) | 1,09 (95 %) | 1,89 (44 %) |
| 14 | 2,73 (2; 26 %) | 1,08 (95 %) | 1,73 (50 %) |
| Sesión (canónico) | 3,03 | 1,09 | 1,90 |

- El spread canónico (`costos_canonicos.json`) coincide con lo medido. Operar sólo después de las 10:00 CT ahorraría ≈ 0,2–0,3 ticks en NQ
  (≈ 4 % de su fricción de 6,2 ticks) y nada en ES. La hora del día **no es una palanca** de fricción; no se propone cambiar el canónico.
- La primera hora (08 CT = 09:30–10:30 ET) es la más cara en NQ e YM: las reglas de apertura (ORB, T) pagan ≈ 0,5 ticks más que la media
  en NQ, que el canónico ya promedia.
- NQ no es un mercado de 1 tick (mediana 2–3): su fricción relativa sólo baja con stops/objetivos más grandes en puntos o con menos
  operaciones, no con elegir horario.
