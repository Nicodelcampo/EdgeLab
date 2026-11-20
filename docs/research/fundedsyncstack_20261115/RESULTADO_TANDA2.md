# FundedSync tanda 2 — resultado (2026-11-16)
Estado: RESULTADO. Pre-registro `PREREGISTRO_TANDA2.md` (+ enmienda 1). Datos en `tanda2/` (L1_SALIDAS, L2_CATASTROFE, L3_L4_TENDENCIA_RUGOSA,
L3_MEDIODIA, L4bis_KNN). Herramienta `tools/fundedsync_tanda2.py`. Nada usó el holdout.

## L1. Salida al cierre en vez de salida técnica — CONFIRMADA para S y W (mecanismo), no alcanza para hacerlas rentables
Prueba en S&P, Dow y Russell 2012 → 2026-09 (índices que estos módulos nunca vieron), diferencia diaria en ATR, BH q 0,10 sobre 4:
| Módulo | Δ diario (ATR) | p | Mejor en | Lectura |
|---|---|---|---|---|
| **S** (sin giro de SuperTrend, stop 3 ATR) | +0,046 | < 0,001 | 3/3 | **CONFIRMADA** |
| **W** (sin recruce del VWAP, al cierre 15:00 CT) | +0,121 | < 0,001 | 3/3 | **CONFIRMADA** |
| A20 (sin giro de SuperTrend) | +0,002 | 0,30 | 1/3 | no |
| N (sin «ruptura fallida») | +0,009 | 0,40 | 2/3 | no |
Neto por operación original → variante: S en S&P −1,03 → −0,61, Dow −6,79 → −2,66, Russell −0,57 → −0,27, Nasdaq −0,02 → +1,13; W en S&P −0,75 →
−0,29, Dow −4,37 → −0,94, Russell −0,51 → −0,84, Nasdaq −0,59 → +1,82. **Las salidas técnicas rápidas destruyen valor (confirmado fuera de muestra),
pero sin ellas S y W siguen sin ventaja neta fuera del Nasdaq, y el peor día empeora** (cola más larga al quedarse hasta el cierre).

## L2. Canasta T+Z+R con stop de catástrofe 0,5 × ATR20 (desarrollo, descriptivo) y forward
| | 2012–2019 | 2020–2023 | 2024–2026 |
|---|---|---|---|
| Z sin → con stop (pts/op) | −1,2 → −1,2 | +26,6 → +24,6 | +40,2 → +36,6 |
| Z peor operación | −171 → −101 | −306 → −202 | −344 → −198 |
| R sin → con stop | +2,5 → +2,3 | +28,1 → +36,6 | +75,9 → +53,2 |
| R peor operación | −136 → −88 | −417 → −160 | −196 → −219 |
El stop corta la cola de Z casi gratis (−2 a −4 pts/op, peor operación ≈ −200 en vez de −344). En R es mixto: mejora 2020–2023 y cuesta 2024–2026
(corta operaciones que se recuperaban). **Forward desde 2026-11-14 armado** (`tools/fundedsync_cadena.py forward/traer_forward`, e-proceso por módulo y
canasta) y agregado a la tarea diaria.

## L3. Anticipar días de tendencia — NO se puede con estos datos
- A las 10:30 (E2: el resto del día eficiente), los 8 predictores y el combinado dan **AUC 0,47–0,55 en los 4 índices** (B y C): azar.
- A las 12:00 (enmienda 1, E3: la tarde continúa la mañana), 6 predictores + combinado: **AUC 0,45–0,55**: azar.
- Sólo «pasa» la eficiencia de la primera hora para el día completo (E1, AUC 0,71–0,75), y es mecánico: la etiqueta incluye esa misma hora.
- Conclusión: con precio, volumen, gap, noche, volatilidad y pronóstico de volatilidad **la continuación intradía no es anticipable**; coincide con
  H del precio ≈ 0,53–0,56 (caminata aleatoria). Para reglas de ruptura la palanca no es predecir el día sino **perder poco cuando no lo es** (L1, L2).

## L4. Volatilidad rugosa / Hurst (documento CastleQuant): se replica y sirve para PRONOSTICAR VOLATILIDAD, no para predecir dirección
- H de la log-volatilidad diaria: **0,06–0,08** en NQ, S&P y Dow, 0,04–0,07 en Russell, estable en los tres tramos; con lags 5–50 (menos ruido de
  medición) sigue en 0,06–0,07 → la rugosidad no es sólo ruido de medición a lags cortos.
- H del precio (R/S): 0,53–0,56 → precio ≈ caminata aleatoria (no confundir H de la vol con H del precio).
- Pronóstico del log-rango de mañana (2016 → 2026-09, fuera de muestra), error relativo a la caminata aleatoria: **rugoso 0,66–0,69, HAR 0,67–0,70**,
  AR(1) 0,91–1,03. Igual que el documento: el rugoso gana por muy poco a HAR; ambos −30 % contra la caminata aleatoria.
- Usos para EdgeLab: (1) **dimensionar y poner stops con la volatilidad pronosticada** (rugoso/HAR) en lugar del ATR de ayer: el stop y la fricción en R
  dependen del rango del día, y el pronóstico rugoso lo anticipa mejor (conecta con F-STOP-CORTO-ES-FRICCION); (2) régimen de reversión de la
  volatilidad (día de vol alta → mañana más baja); (3) **no** sirve para anticipar días de tendencia (L3).

## L4bis. Capa KNN sombra (idea de T) sobre reglas propias — no mejora
- PREAPERTURA-NQ: con la regla pre-registrada (≥ 50 % de vecinos ganadores) **no toma ninguna operación**: la regla gana pocas veces y mucho (29–33 %
  de ganadoras), así que el voto mayoritario nunca da sí. Falla de diseño del filtro para reglas de baja tasa de acierto.
- CVGAP-ES-C: en la réplica, tomadas +0,16 R contra salteadas +0,51 R (n 33/15; p 0,75): el filtro saltea las mejores.
- Lectura: la capa KNN de T no es transferible tal cual. Una versión con la media de R de los vecinos (no el voto) es una hipótesis nueva para datos no
  usados.

## Corrección 2026-11-16: horario de Russell en L1
El CSV de Russell venía en UTC y se leyó como hora del servidor (NY + 7): las sesiones de Russell estaban corridas 2–3 horas. Se corrigió el
lector (`m1_intradia.EN_UTC`) y se re-corrió L1. **La conclusión no cambia**: S y W siguen confirmadas en 3/3 índices (BH). Russell
corregido: S +0,031 ATR/día (p 0,002), W +0,043 (p 0,0007); A20 y N no. Conjunto S&P+Dow+Russell: S +0,046, W +0,107 (antes +0,121).
