# FundedSync: mecanismos, contextos y combinaciones (pre-registro, 2026-11-16)

Estado: PRE-REGISTRO — commiteado antes de calcular ninguna condición. Pedido de Nico: «research profundo de los mecanismos de las
estrategias de la cartera, no sólo T; probablemente haya un par más rentables que no pasan todos los controles; mejorarlas, extraer
mecanismos útiles, combinarlos o inspirar corridas». North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
Etapa EF2 (exploración) + EF3 (réplica dirigida, una vez). Familia `FUNDEDSYNC` (ya usó su holdout: **nada de esto mira el holdout**).
Herramienta: `tools/fundedsync_mecanismos.py`. Datos: operaciones de `cadena/FUNDEDSYNC_OPS.csv.gz` (15 módulos, 1 contrato, costos NQ) y M1 del
Nasdaq (`edgelab-sqx-m1`) para el contexto diario.

## Partición
- **A (descubrimiento): 2020-01-01 → 2023-12-31.** (2012–2019 queda fuera: los umbrales en puntos de los módulos no son comparables.)
- **B (confirmación, una vez): 2024-01-01 → 2026-09-29.** Ya visto por módulo en total (`RESULTADO_CADENA.md`), nunca condicionado.

## Ejes (fijos, conocidos ANTES de la entrada; 25 niveles por módulo)
lado (L/S); hora de entrada NY (09:30–10:30, 10:30–12:00, 12:00–14:00, 14:00–16:15, fuera de la rueda); día de la semana (5); vol20 (tercil del
rango RTH medio de 20 días contra sus 250 previos); tend60 (signo del retorno de 60 días al cierre previo); **noche** (tercil del rango 18:00 →
09:30 relativo, contra 250 previos: el factor de ASIA); gap (tercil de |apertura − cierre previo| / ATR20); ORB15 (tercil del rango 09:30–09:45 /
ATR20, sólo para entradas desde las 09:45). Terciles con cortes causales (cada día contra sus 250 días previos).

## Selección en A y prueba en B
- Celda = (módulo, nivel de un eje). Evaluable con n ≥ 30 en A. **Elegida** si en A su neto medio > 0 y supera al resto del módulo con t de la
  diferencia ≥ 2 (bootstrap por sesión).
- En B, cada elegida: H «neto de la celda > neto del resto del módulo» y «neto de la celda > 0»; p de una cola por bootstrap de sesiones; **BH
  q 0,10 sobre las elegidas** (las 375 celdas cuentan en el contador global). Pasa = nominada por BH en las dos.
- Lectura: lo que pasa es una **mejora candidata** (filtro de contexto de ese módulo) que va a forward/papel con su propio pre-registro; lo que
  no pasa queda como descripción. Nada se combina ni se ajusta mirando B.

## Descriptivo (no decide)
Por módulo: neto bruto vs fricción; por tipo de salida (stop, objetivo, tiempo, condición) y lado; correlación diaria entre módulos en A;
canasta T+Z+R; cuánto del resultado de cada módulo cae en días de tendencia (|cierre − apertura RTH| ≥ 0,8 × rango del día, etiqueta ex post,
sólo para entender el mecanismo, nunca como filtro).

## Mecanismos a extraer (síntesis cualitativa, con la evidencia de arriba)
ORB/ruptura (T, F, Q, V, N), tendencia intradía (Z, S, A1/A20 con SuperTrend), fase de volatilidad (R), reversión a VWAP/pullback (P, W, R),
gap (C), tenencia nocturna (O), cruce de medias (E). Para cada familia: qué contexto la enciende, si la ventaja es bruta o la come la fricción,
y qué es transferible a las familias de EdgeLab (ASIA, CVGAP, U1, PREAPERTURA).

## Justificación económica / cómo podría refutarse
Los mecanismos de ruptura y tendencia dependen de que haya información nueva que el mercado tarda en absorber (noche movida, gap, volatilidad);
los de reversión, de liquidez sin información. Refutación: ninguna celda elegida en A pasa BH en B.
Contador global: 375 pruebas (familia `FUNDEDSYNC`).
