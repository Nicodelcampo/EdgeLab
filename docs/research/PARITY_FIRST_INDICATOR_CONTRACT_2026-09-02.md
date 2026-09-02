# Contrato de diseño «paridad primero» para indicadores EdgeLab (2026-09-02)

Regla que gobierna los indicadores nuevos. Nace de dos fallas medidas hoy, no de teoría.

## Evidencia que lo motiva

| indicador | mecanismo de la falla | medición |
|---|---|---|
| `aVolClusterPOI` | mediana de ~66 celdas × 2 como umbral duro | ruido ±1 en volumen → **66 % de turnover de zonas** (`avolcluster_sensitivity_20260902/`) |
| `HFTZonesNQImpulseV2_5` | `_timingZeroFraction >= MaxZeroIntervalFraction` con umbral 0,50 | la fracción real en NQ es **0,51**: la sesión entera cambia de clasificación por un margen de 0,01 |

Ambos comparten la misma falla: **una decisión binaria apoyada sobre un valor continuo que
vive en el borde del corte**. Y ambos leen la subserie de 1 tick de NT8
(`Closes[1][0]`, `Volumes[1][0]`), que no se reproduce exactamente desde el parquet
(`avolcluster_parity_full_20260902/`: sólo 16 de 22.200 bloques con celdas idénticas).

## Las siete reglas

1. **Aritmética entera en toda decisión.** Precio en ticks enteros, volumen entero,
   proporciones en *basis points* enteros (`vol * 10000 / total >= MinShareBps`). Nunca
   comparar floats para decidir.
2. **Prohibido el reloj entre ticks.** Nada de `ms` entre prints. Es el dato menos
   reproducible: en NQ el 51 % de los ticks comparte timestamp exacto.
3. **Prohibidos los estadísticos continuos como umbral duro.** Nada de mediana, cuantil ni
   percentil decidiendo. Se permite **ranking** (top-K) y **conteo** (≥ N celdas).
4. **Todo empate se rompe de forma determinista y declarada** — por precio ascendente. Sin
   ordenamientos dependientes de inserción o de hash.
5. **Sin estado que cruce sesiones sin declararlo.** Si hay historia, se resetea en el
   límite de sesión y el reset se emite en el log.
6. **Un solo origen de datos por magnitud.** El footprint se arma una vez, con una regla
   escrita, y ningún filtro descarta ticks en silencio (el `.cs` viejo descartaba con
   `Low[0]/High[0]` sin reasignar).
7. **Log de decisión completo.** Cada bloque emite todos los insumos que lo determinaron,
   de modo que el cruce contra Python sea celda por celda y no por agregados.

## Criterio de aceptación

Un indicador cumple el contrato si, sometido al mismo test de sensibilidad que corrimos hoy
(perturbar el volumen por tick en ±1 sobre dos tercios de los ticks), su **turnover de zonas
es menor al 5 %**. aVolClusterPOI da 66 %. Ese es el número a batir, y es medible antes de
confiar en cualquier resultado del indicador.
