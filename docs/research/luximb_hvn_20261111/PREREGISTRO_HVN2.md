# LUXIMB-HVN2 — el nodo de volumen más allá de B, redefinido en relativo (exploración sobre desarrollo)

Estado: PRE-REGISTRO (2026-11-11, OK de Nico: «las dos»). Escrito antes de generar las tablas. Etapa **EF2 exploratoria**.
Referente: `docs/NORTH_STAR.md`, cuerpo sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
Familia `LUXIMB_HVN2` (linaje: `LUXIMB_HVN`). Módulo `edgelab/research/luximb_hvn2.py` con el contrato de la cadena estándar
(`docs/research/CADENA_DE_CORRIDA.md`); preflight en verde (contrato, causalidad, motor calibrado, kernel sintético).

## Por qué
`F-LUXIMB-HVN-DEFINICION`: con la definición de LUXIMB-HVN el nodo casi nunca aparece (3 de 925 eventos del visor) y las hipótesis
H-HVN-1/2 quedaron SIN POTENCIA. La pregunta de Nico sigue abierta: ¿la vuelta después de extenderse más allá de B ocurre donde
había un nodo de volumen del pasado?

## Rasgos (perfil por nivel de precio de las L = 240 / 1.440 velas anteriores al inicio del impulso)
`hvr_L` = densidad por nivel en la franja más allá de B (alto rg/2) / mediana por nivel de la ventana; `poc_d_L` y `poc_f_L` =
distancia (en rangos) y fuerza (sobre la mediana) del nivel de más volumen dentro de [B, B + rg]; `poc_cf_1440` = nodo fuerte (≥ 3
veces la mediana) a ≤ 1/4 de rango más allá de B.

## Definiciones, filtros y ejecuciones (fijados acá)
Definiciones: visor `D3_20_a0_z2`, control `D3_20_a0_z0`, `D3_20_a0_z3` (≥ 5 zonas) y `D2_20_a0_z2` (impulso más chico).
Filtros: hvr ≥ 1,5 / 2 / 3 y < 1 en las dos ventanas, y `poc_cerca_fuerte`. Ejecuciones: MERCADO stop 0,35 / 0,5 · D, objetivo
0,5 / 1,0 · D, sin o con BE a 0,25·D (8); VUELTA e = 0,1 / 0,25 / 0,5, r = 0,1 / 0,2, b = 0,1, objetivo A o mitad, c = e + 0,5 (12).
Celdas: 4 × 20 × (1 + 9) = 800 por corte (`tablas.conteo`), registradas como `luximb_hvn2/desarrollo`.

## Datos
Desarrollo ya mirado por el linaje: NQ y USATECH, 2025-08-05 → 2026-03-31 y 2026-04-01 → 2026-09-25/30. Nada de esto confirma: lo
que aparezca sobre el nulo de la búsqueda se congela y se confirma en datos no usados (USATECH 2023–2025 ya queda gastado por
H-ZONAS; la confirmación sería en forward o en el holdout desde 2026-10-23, una apertura de la familia).

## Hipótesis previa (antes de ver tablas)
- **H-HVN2:** en el visor, con la entrada en la vuelta VUELTA e 0,25 / r 0,1 / objetivo A, el R neto con `hvr_1440` ≥ 1,5 es mayor
  que con `hvr_1440` < 1.

## Cómo podría refutarse
Con `hvr` ≥ 1,5 o `poc_cerca_fuerte`, la vuelta rinde igual o peor que sin nodo (con n suficiente: ≥ 30 operaciones por celda).

## Adenda (2026-11-11, antes de ver ninguna tabla): filtros de VWAP
Pedido de Nico: «probá filtrar con VWAP diario, VWAP de NY y ambos; no hay una manera definida, usá todas las mejores». La cadena
agrega a toda tabla `edgelab/research/rasgos_comunes.py`: VWAP anclado a la sesión y a las 09:30 de Nueva York, con su desvío
ponderado por volumen, y 10 filtros (hacia / contra cada VWAP, los dos hacia / los dos contra, lejos ≥ 1 desvío, lejos y hacia).
Las celdas suben en consecuencia (`tablas.conteo`) y la diferencia se registra aparte (`.../vwap`). Las tablas lanzadas antes de esta
adenda se relanzan con el código nuevo y no se miran.
