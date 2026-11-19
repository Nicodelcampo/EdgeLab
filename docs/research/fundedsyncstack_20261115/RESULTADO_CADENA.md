# FUNDEDSYNCSTACK por la cadena — resultado (2026-11-16)
Estado: RESULTADO. Pre-registro `PREREGISTRO_CADENA.md`. Datos: `cadena/RESULTADO.json`, `cadena/EXTRA.json`, operaciones en
`cadena/FUNDEDSYNC_OPS.csv.gz`. 15 módulos de fábrica, 1 contrato, M1 del Nasdaq 2012 → 2026-09, costos NQ (1,5455 pts). Kernel 3 h 16 min.
**Nulo de la búsqueda (20 réplicas × 15 módulos): p95 del máximo t en OOS 2020–2023 = 1,92.**
**Causalidad por prefijo:** los 15 módulos dan las mismas entradas y salidas con y sin el futuro (sintético; T, R y Z además sobre datos
reales 2018–2024). T entrena su KNN sólo con operaciones «sombra» ya cerradas.

| Módulo | Neto por operación (pts) DESC / OOS / RECIENTE / PSEUDO | t OOS | Ops/mes | Stop | Lectura |
|---|---|---|---|---|---|
| **T** FtmEngine (ORB 15m + KNN) | +0,5 / **+13,2** / +17,2 / +22,6 | **4,37** | 19 | sí (mediana 36 pts) | **PISTA** |
| **Z** ZetaTrendDay | −1,2 / **+26,6** / +28,8 / +53,7 | **3,19** | 2 | no | **PISTA** (sin stop, n chico) |
| **R** AtrPhase 10m | +2,5 / **+28,1** / +56,5 / +104,2 | **2,46** | 3 | no | **PISTA** (sin stop, n chico) |
| C CapstoneGap | −2,9 / +10,3 / −4,4 / +19,6 | 2,26 | 5 | sí | régimen (RECIENTE < 0) |
| E EmaDivergence | −1,5 / +2,7 / −3,3 / −1,9 | 2,60 | 19 | sí | sin ventaja fuera de OOS |
| A20 Absorb 20m | −1,5 / −1,4 / +3,6 / +10,4 | −0,47 | 19 | sí | RÉGIMEN (reciente) |
| S Swas 3m | −1,2 / −2,0 / +7,2 / +5,1 | −1,30 | 35 | no | RÉGIMEN (reciente) |
| P NqPullback | −2,0 / −2,3 / +5,6 / +0,9 | −0,84 | 11 | sí | RÉGIMEN débil |
| N NDayLong | +3,8 / +2,7 / −1,6 / +25,4 | 0,82 | 10 | no | RÉGIMEN (último año) |
| O Overnight | +2,6 / +1,4 / +9,8 / +21,3 | 0,35 | 8 | no | positivo y débil en todos |
| F Fabio ORB 5m | −1,4 / +5,1 / +5,8 / +2,9 | 1,72 | 10 | sí | débil, no supera al nulo |
| V VaultBreak | +0,6 / +2,5 / −0,3 / +2,9 | 1,24 | 18 | sí | ≈ 0 |
| A1 Absorb 1m | −1,5 / −1,3 / −0,1 / +1,6 | −2,45 | 60 | sí | SIN VENTAJA (la fricción lo mata) |
| W VwapCross | −1,3 / +0,4 / 0,0 / −0,7 | 0,78 | 110 | no | SIN VENTAJA |
| Q Rampart | −1,6 / −1,3 / +2,1 / +1,3 | −1,99 | 24 | sí | SIN VENTAJA |

Lectura: **3 pistas** (T, Z, R) superan al nulo en 2020–2023 y siguen positivas en 2024–2025 y en el último año. T es la única operable tal
cual (stops, 19 operaciones por mes, peor operación −102 pts). Z y R no tienen stop (peor operación −306 y −417 pts) y operan 2–3 veces por
mes: para una prop necesitan un stop agregado (hipótesis nueva). El resultado del vendedor (NT8 2025-06 → 2026-09, con su sizing) mostraba T,
R y Z negativos; acá, con 14 años de historia (el KNN de T se entrena con más etiquetas) y un contrato, dan positivo: la diferencia no está
explicada y se resuelve en el holdout. Límites: datos de CFD con costos de futuro; delta proxy; los umbrales en puntos no son comparables
antes de 2020.
Siguiente (pre-registrado): apertura única del holdout de la familia FUNDEDSYNC para T, Z y R con acta propia.
