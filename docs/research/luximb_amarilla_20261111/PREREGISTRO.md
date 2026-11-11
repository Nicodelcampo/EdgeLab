# LUXIMB-AMARILLA — impulso LUX-IMB → caja amarilla → ruptura a favor → regreso → entrada en contra

Estado: PRE-REGISTRO (2026-11-11, pedido de Nico: «mezclá la lógica de expansión → caja amarilla → expansión → entrada con la de
LUX-IMB y expansiones; hacé variantes; revisá dos veces y lanzalo»). Escrito antes de generar ninguna tabla. Etapa **EF2 exploratoria**.
Referente: `docs/NORTH_STAR.md`, cuerpo sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
Familia `LUXIMB_AMARILLA`; linaje `LUXIMB_GRILLA` (impulso), `LUXIMB_HVN` y `CORREDOR_VOL_GAPS` (secuencia de la caja amarilla); hereda su
multiplicidad. Módulo `edgelab/research/luximb_amarilla.py` (cadena estándar; ejecuciones PRECIOS del motor único con stop
estructural; tests `tests/research/test_luximb_amarilla.py`).

## Regla (detalle en el docstring del módulo)
Marca LUX-IMB (visor z2, z3 ≥ 5 zonas, D2 z2, control z0 sin zonas) → sector amarillo de alto 0,5·H centrado en el extremo B, abierto W
veces la duración del impulso (W = 1, 2) → «amarilla» si su volumen por vela supera el P80 causal de los sectores cerrados antes (y
«sin_filtro» como control del volumen) → ruptura A FAVOR del impulso con excursión ≥ e·H_am (e = 1, 2, 4) → regreso ANTES (40 % de
la excursión), EN_CAJA (borde externo) o DESPUES (borde interno) → entrada a mercado EN CONTRA, objetivos 50 % / 75 % / origen del
impulso, stop en el extremo de la excursión o 0,25·H_am más allá.

## Variantes y conteo
4 bases × 2 W × 2 filtros de volumen × 3 excursiones × 3 puntos = 144 definiciones; 6 ejecuciones; filtros comunes de VWAP (10) →
`tablas.conteo` celdas por corte, registradas como `luximb_amarilla/desarrollo` (× 4 cortes).

## Controles (el espacio de eventos es el de LUXIMB-HVN §2 + la secuencia del padre)
(a) sin condición de zonas (`ctrl`): ¿aporta algo LUX-IMB a la secuencia de la caja?; (b) sin filtro de volumen (`sin_filtro`): ¿aporta
algo la caja AMARILLA (volumen alto) o basta la geometría?

## Datos
NQ y USATECH, DESC (2025-08 → 2026-03) y REP (2026-04 → 2026-09), ya mirados por el linaje. Lo que quede sobre el nulo de la
búsqueda y repita en DESC y REP en los dos activos se congela y se confirma en forward / holdout desde 2026-10-23 (una apertura).

## Justificación económica y cómo podría refutarse
- **Justificación:** el padre (CVGAP) apuesta a que una ruptura de una zona de mucho volumen que se agota y vuelve atrapa a los que
  entraron a favor; sumar el impulso con desequilibrios OG/VI selecciona impulsos «urgentes» cuyo origen quedó con órdenes sin llenar.
- **Refutación:** nada sobre el nulo de la búsqueda; real − control ≤ 0 en las dos comparaciones (zonas y volumen); o el signo no
  repite entre DESC y REP.

## Revisión doble (antes de lanzar)
1. Causalidad: la decisión es al cierre de la vela; el sector usa sólo velas ≤ kf; el percentil, sólo sectores cerrados antes; la
   entrada, en el tick siguiente (test de prefijo del preflight).
2. Secuencia: test con un recorrido a mano (tres puntos en orden; invalidación antes de armarse); objetivos y stops del lado correcto.
