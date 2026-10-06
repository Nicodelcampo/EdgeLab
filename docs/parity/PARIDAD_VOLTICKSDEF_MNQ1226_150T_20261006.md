# Paridad VolTicksDef (log1) — MNQ 12-26, 150 tick (2026-10-06) — **PASS**

- Oráculo NT8: `data/nt8_oracles/volticksdef_MNQ1226_150t_20260715_20260930.csv` (logger agregado a `nt8/VolTicksDef.cs`,
  sin cambiar la firma).
- Chart: 2026-07-15 → 2026-09-30, Do not merge, parámetros por defecto (200 / 99,75 / reset por sesión / 30).
- Ticks: re-export NT8 20261005. Espejo: `edgelab/bridge/indicators/volticksdef.py`. Script: `tools/paridad_volticksdef.py`
  (alineación por índice de barra; con ráfagas de igual timestamp, la alineación por tiempo duplica filas).

| campo | coincidencia |
|---|---|
| barras (142.711 + parcial), tiempos de cierre | 100 % |
| volumen, promedio móvil | exacto |
| primera barra de sesión, n de muestras de sesión y global | 100 % |
| umbral de sesión, global y usado (P²) | **exacto bit a bit (100 %)** |
| ratio | exacto en 99,988 %; 17 barras con 1 ULP (1e-16) de diferencia |
| **marcas (zonas)** | **547 / 547, 0 diferencias en 142.511 barras** |

Lectura del CSV con `float_precision='round_trip'`: el parser por defecto de pandas no es exacto y fabrica diferencias
de 1 ULP.

Comportamientos del indicador a tener en cuenta (no son errores de paridad):
- En barras de ticks el ratio varía poco: las marcas tienen una mediana de unas 1,5 veces el promedio.
- Al arrancar la sesión, el umbral de sesión se usa recién con 30 muestras. Hasta entonces se usa el global. Con
  q = 0,9975, el umbral de sesión queda cerca del máximo visto en la sesión.
- La "zona" es el rango completo de la barra (mediana 15 ticks); puede ser enorme si la barra cruza un hueco.
