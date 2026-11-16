# FundedSync, tanda 2: salidas, canasta T+Z+R, días de tendencia, volatilidad rugosa y capa KNN (pre-registro, 2026-11-16)

Estado: PRE-REGISTRO — commiteado antes de correr nada de lo que sigue. Pedido de Nico: «hacé todas (las 4 propuestas de
RESULTADO_MECANISMOS.md); seguí intentando anticipar los días de tendencia; fijate si el documento de volatilidad rugosa / Hurst (CastleQuant)
sirve acá u otros casos». North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Nada mira el holdout.
Datos: M1 de Dukascopy (`edgelab-sqx-m1`): Nasdaq (NQ_M1_dukas), S&P (SP_M1_dukas), Dow (DJ_M1_dukas), Russell (USSC2000IDXUSD), 2012 → 2026-09.
Costos del futuro equivalente (`edgelab/costos.py`): NQ 1,5455, ES 0,8877, YM 5,052, RTY 0,4436 pts.

## L1. Salida al cierre en vez de salida técnica (S, A20, W, N) — EF3, datos no usados
- Variantes (flags agregados al código con valor por defecto = original): S `exit_on_st_flip=False` + `use_hard_stop=True` (3 ATR, el del
  vendedor); A20 `exit_on_st_flip=False` (stop 1,5 ATR ya activo); W `exit_on_vwap_cross=False` (sin stop: queda al cierre de las 15:00 CT);
  N `use_failed_breakout_exit=False` (queda la salida por pérdida de volatilidad).
- **Datos de prueba: S&P, Dow y Russell 2012 → 2026-09** (estos módulos nunca corrieron ahí). Nasdaq se informa aparte (de ahí salió la idea).
- Estadístico por módulo: diferencia diaria de neto (variante − original), juntando los 3 índices; p de una cola por bootstrap de sesiones;
  **BH q 0,10 sobre 4 módulos**. Además: neto de cada versión por índice y tramo (2012–19, 2020–23, 2024–26) y peor día.
- Lectura: variante CONFIRMADA (es mejor) si BH y mejor en ≥ 2 de 3 índices. Si no, la salida técnica se queda.

## L2. Canasta T + Z + R a forward, con stop de catástrofe para Z y R
- Stop de catástrofe declarado ahora, sin mirar la distribución de pérdidas: **0,5 × ATR20 diario** (rango RTH medio de 20 días previos) para Z y
  R; se aplica con el MAE de cada operación (si MAE ≥ stop, resultado = −stop − fricción). T sin cambios.
- Desarrollo (NQ 2012–2026): sólo descriptivo (ya visto). Forward desde la sesión 2026-11-14 con e-proceso (cotas por operación en puntos
  [−400, 1.200]), junto a la cartera v2; EDGE si e ≥ 10. Contador: 1 prueba.

## L3. Anticipar días de tendencia (E0, sin retornos de estrategias)
- Etiquetas: **E1** día de tendencia completo (|cierre − apertura RTH| ≥ 0,8 × rango RTH); **E2** resto del día eficiente tras la primera hora
  (|cierre − precio 10:30| ≥ 0,6 × rango 10:30–16:00).
- Predictores conocidos a las 10:30 NY (todos causales): rango de la primera hora / ATR20; eficiencia de la primera hora (|p10:30 − apertura| /
  rango de la primera hora); volumen de ticks 09:30–10:30 / media de los 20 días previos; gap alineado con la primera hora (sí/no); noche (tercil);
  vol20 (tercil); **pronóstico de volatilidad del día** (HAR y rugoso, L4) / ATR20.
- Partición: A 2012–2019 (exploración), B 2020–2023 y C 2024 → 2026-09 (cada una una vez); los 4 índices.
- Métrica: AUC de cada predictor solo y de un logístico con todos (ajustado en A, probado en B y C sin reajustar). **Lectura: sirve si AUC ≥ 0,60
  en B y C en ≥ 3 de 4 índices** (el azar da 0,50). Contador: 7 predictores + 1 combinado × 2 etiquetas = 16.

## L4. Volatilidad rugosa / exponente de Hurst (documento CastleQuant) aplicado a EdgeLab
- H de la log-volatilidad diaria (rango de Parkinson del día RTH) por variograma (lags 1–50) en los 4 índices y por tramo (2012–19, 2020–23,
  2024–26); además H del precio (retornos diarios, R/S) para separar «vol rugosa» de «precio con memoria».
- Pronóstico de la log-volatilidad de mañana: caminata aleatoria, AR(1), HAR (1/5/22 días) y rugoso (núcleo potencia (t−s)^(H−1/2) con H
  estimado en el tramo previo), ajustados en ventana expansiva; error cuadrático fuera de muestra 2016 → 2026-09.
- Usos que se evalúan (descriptivo, sin elegir reglas): (a) como predictor de L3; (b) para dimensionar/stop: correlación entre volatilidad
  pronosticada y el riesgo/resultado de las operaciones de la cartera v2 (desarrollo); (c) régimen de reversión de la volatilidad.
- Lectura: el documento «sirve» en EdgeLab si el pronóstico rugoso o HAR baja el error ≥ 10 % contra la caminata aleatoria **y** aporta a L3 o al
  sizing; si sólo replica H ≈ 0,1 sin uso operable, queda como conocimiento, no como filtro.

## L4bis. Capa KNN «sombra» (idea de T) sobre reglas propias: PREAPERTURA-NQ y CVGAP-ES-C
- Rasgos en la entrada (de M1, causales): retorno desde la apertura (bps), rango de 15 min (bps), ubicación del cierre en el rango de 15 min,
  distancia al VWAP de la sesión (bps), retorno de 60 min, retornos de 5/15/30 min, minuto del día, lado. Estandarizados con las operaciones previas.
- KNN k = 15 sobre las operaciones previas de la misma regla (mínimo 40), reentrenado cada trimestre; etiqueta = R > 0. **Opera sólo si ≥ 50 %
  de los vecinos ganaron.** Entrena en DESC y se evalúa en REP (la réplica de cada regla; vista en total, nunca filtrada).
- H: R/op de las filtradas > R/op de todas en REP, p por bootstrap de sesiones; BH sobre 2 reglas. Contador: 2.

## Justificación económica / cómo podría refutarse
L1: la salida técnica corta ganadoras en días de tendencia y paga fricción; refutación: la variante no mejora en índices no usados. L2: tres
mecanismos distintos y descorrelacionados; refutación: R forward ≤ 0. L3: el día de tendencia es flujo informado que deja rastro temprano (rango,
volumen, eficiencia); refutación: AUC < 0,60 fuera de A. L4: la volatilidad es antipersistente y pronosticable; refutación: sin mejora contra la
caminata aleatoria o sin uso en L3/sizing. L4bis: las operaciones de una regla se parecen a sus vecinas; refutación: el filtro no mejora la réplica.
Contador global total: 4 + 1 + 16 + 2 = 23 pruebas (familias FUNDEDSYNC, EL-DIA-TENDENCIA, PREAPERTURA y CVGAP).

## Enmienda 1 (2026-11-16, antes de correrla; Nico: «seguí intentando anticipar los días de tendencia»): decisión a las 12:00
L3 a las 10:30 dio AUC ≈ 0,50 para el resto del día (E2) en los 4 índices. Se agrega UNA prueba más, con la mañana ya vista:
- Etiqueta **E3**: la tarde (12:00 → 16:00) se mueve en la dirección de la mañana (09:30 → 12:00) y con eficiencia ≥ 0,5 (|cierre − p12:00| / rango de
  la tarde).
- Predictores a las 12:00: eficiencia de la mañana; rango de la mañana / ATR20; posición del precio respecto del VWAP de la mañana (en desvíos);
  volumen de la mañana / media de 20 días; pronóstico rugoso del día / ATR20; fracción del rango pronosticado ya recorrida a las 12:00.
- Misma partición A/B/C, mismos 4 índices, misma lectura (AUC ≥ 0,60 en B y C en ≥ 3 de 4). Contador: 6 + 1 combinado = 7.
