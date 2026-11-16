# FUNDEDSYNCSTACK por la cadena de EdgeLab (pre-registro, 2026-11-16)

Estado: PRE-REGISTRO — commiteado antes de correr. Pedido de Nico: «pasá las reglas nuevas por nuestra cadena; y las vamos a usar para
inspirar otros análisis». North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Etapa EF3 (réplica con
potencia de reglas ajenas) → EF5 (holdout, una apertura, sólo si algo pasa). Familia `FUNDEDSYNC`. Uso de la traducción: decisión de Nico
(la licencia del producto original es responsabilidad del licenciatario); acá sólo se mide.

## Objeto (congelado)
Los 15 módulos de `edgelab/research/fundedsyncstack` (A1, A20, F, S, P, C, V, O, W, N, T, R, Z, E, Q) **con sus valores de fábrica**, en
NQ, una operación de un contrato cada vez (sin el motor de cartera ni el sizing del vendedor). Nada se ajusta.

## Datos y costos
M1 de Dukascopy del Nasdaq (USATECH, `nicolasbuttaro/edgelab-sqx-m1`), 2012 → 2026-09-29, pasado a UTC; delta = proxy del paquete (no hay
delta real). Costos del futuro NQ (`edgelab/costos.py`, base 1,5455 pts por ida y vuelta, como la fuente M1DK). Tramos: DESC 2012–2019,
OOS 2020–2023, RECIENTE 2024-01 → 2025-07, PSEUDO 2025-08 → 2026-09 (el período en que el vendedor muestra resultados).
Lo anterior a 2025 es, con alta probabilidad, fuera de la muestra en que el vendedor diseñó los módulos: es la réplica que importa.

## Medida
- Neto por operación en puntos (bruto − 1,5455). R = neto / riesgo inicial (|entrada − stop|) donde el módulo pone stop; los módulos sin
  stop (salida por tiempo o condición) se informan en puntos y quedan marcados «sin stop» (no operables en una prop sin agregar uno).
- t por sesión del neto (puntos) por módulo y tramo; R por operación, % ganadoras, operaciones por mes, peor operación.

## Escala (corrección antes de lanzar)
Los módulos usan umbrales en puntos absolutos pensados para NQ ≈ 20.000 (p. ej. riesgo máximo 125 pts); en 2012–2019 el NQ cotizaba 2.500–8.000,
así que DESC no mide la misma regla. **Tramo principal: OOS 2020–2023** (NQ 7.000–17.000, anterior al vendedor); DESC queda informativo.

## Nulo de la búsqueda (15 módulos contados)
`m1_intradia.sintetica_m1` (cada minuto toma la barra relativa del mismo minuto de otro día): 20 réplicas de los 15 módulos; umbral = p95
del máximo t neto en OOS 2020–2023 sobre los 15. Contador global: 15 pruebas.

## Lectura (fijada antes)
Un módulo es **PISTA** si: t neto OOS (2020–2023) > umbral del nulo **y** neto > 0 en RECIENTE (y en PSEUDO como dato). **RÉGIMEN** si sólo PSEUDO (y quizá RECIENTE)
es positivo: vale lo dicho para reglas de régimen (se busca la variable que lo enciende, no se lo descarta). **SIN VENTAJA** si el neto es
≤ 0 en la mayoría de los tramos. Sólo las PISTA (o una canasta de ellas, congelada) pasan a la apertura única del holdout (2026-10-01 → última
sesión sellada, ticks de NQ), con su propio acta antes de abrir.

## Para inspirar otros análisis
Cada módulo deja una ficha en el banco de ideas (`tools/ideas.py`) con su mecanismo, el resultado de esta cadena y qué parte de la idea es
transferible a nuestras familias (aunque el módulo no tenga ventaja).

## Justificación económica / cómo podría refutarse
Las del vendedor por módulo (`INGENIERIA_INVERSA_FUNDEDSYNCSTACK.md`): absorción, ruptura de rango de apertura, barridos, pullbacks, gaps,
overnight, VWAP, tendencia diaria, KNN de rupturas. Refutación: ningún módulo supera al nulo con neto > 0 fuera del período del vendedor.
