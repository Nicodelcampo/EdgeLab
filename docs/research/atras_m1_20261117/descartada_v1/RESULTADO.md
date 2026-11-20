# «Atrás» de 5 reglas congeladas de la v2 y la v4 sobre M1 real de futuros: REFUTADA_ATRAS (2026-11-17)

Estado: DESCARTADA (2026-11-18) — el motor de la grilla cobraba el stop en el extremo de la vela M1 (K40): pesimista con stops chicos. En la calibración, M1 dio menos que ticks en las 5 reglas (−0,01 a −0,16 R por sesión), dentro de 1 EE pero siempre del mismo lado. Corregido y relanzado (`../RESULTADO.md`). Antes: RESULTADO — decisión pre-registrada (`PREREGISTRO.md` §4), calibración commiteada antes (`CALIBRACION.json`). North Star sha256
`16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Datos: `ATRAS.json`, `resultados/`; fallidas (cuenta sin acceso al
dataset, sin datos producidos) en `FALLIDAS.jsonl`.

## Calibración (ago-25 → sep-26): las 5 calibran
Correlación por sesión M1 contra ticks de 0,89 a 0,998, mismo signo, y la media en M1 igual o menor que en ticks: el M1 reproduce las
reglas con sesgo conservador.

## Atrás: ventana primaria (años que su linaje no miró), costos canónicos
| Regla | Canasta | Ventana | Ops | Ops/mes | R/op | IC90 | Años + | Potencia (½ efecto dev) | Veredicto |
|---|---|---|---|---|---|---|---|---|---|
| CVGAP2-GC#11 | v4 | 2018 → jul-2025 | 431 | 4,7 | −0,16 | [−0,23, −0,09] | 1/8 | 0,99 | **EN_CONTRA_ATRAS** |
| COMEX-CIERRE-GC-R#0 | v4 | 2018 → jul-2025 | 523 | 5,7 | −0,23 | [−0,30, −0,16] | 0/8 | 0,97 | **EN_CONTRA_ATRAS** |
| IF-LUX-NQ-R2#1 | v4 | 2018 → 2022 | 95 | 1,6 | −0,14 | [−0,36, +0,08] | 1/5 | 0,50 | NO_CONCLUYENTE |
| CVGAP-ES-C | v2 | 2018 → jul-2025 | 769 | 8,5 | −0,08 | [−0,15, −0,02] | 1/8 | 1,00 | **EN_CONTRA_ATRAS** |
| PREAPERTURA-NQ | v2 | 2018 → 2022 | 656 | 10,9 | −0,19 | [−0,35, −0,01] | 0/5 | 0,57 | NO_CONCLUYENTE (IC90 entero < 0) |

**Canasta (suma por sesión):** 1.453 sesiones, −386 R, −0,27 R por sesión, p = 1,0, 0 de 8 años positivos → **REFUTADA_ATRAS**.
Descriptivo 2006/2008 → 2017: las cinco también negativas.

## No es fricción ni escala
El bruto (antes de costos) por año también es ≈ 0 o negativo, incluso en los años con fricción chica en R (PREAPERTURA-NQ 2020–2022:
fricción 0,04–0,08 R, bruto −0,03 a −0,07 R/op; CVGAP-ES-C 2020–2025: bruto alrededor de 0). La frecuencia por año es estable (sin
deriva de escala que cambie la regla).

## Lectura
- Las cinco reglas rindieron en el tramo donde se eligieron (ago-2025 → sep-2026, ticks y M1 coinciden), pero **en los años limpios
  anteriores no tenían ventaja ni bruta**. Es el sesgo de selección que el paso 2 de `urgencia_vs_evidencia_20261117` midió en todo el
  embudo («lo elegido no conserva nada»), confirmado ahora regla por regla con potencia.
- **Causa de fondo:** elegir entre miles de celdas con 14 meses de datos produce ganadoras de ruido. Ni la réplica de 6 meses ni el
  holdout corto alcanzan para separarlas. Es exactamente lo que la HOLDOUT-A5 corrige: descubrimiento y holdout sobre 18 años de M1.

## Consecuencias (pre-registradas)
- **v2:** CVGAP-ES-C sale en la próxima versión (pre-registro nuevo). PREAPERTURA-NQ queda NO_CONCLUYENTE pero con el IC90 entero en
  contra: no sostiene tamaño.
- **v4:** CVGAP2-GC#11 y COMEX salen en la próxima versión.
- No se habilita tamaño real para ninguna canasta. Las reglas de la v2 que no se pueden medir en M1 (U1-*, CONF-CVR, CVGAP-CFD-ES-C,
  U1-ORO) no están refutadas por esto, pero salieron del mismo embudo: su expectativa honesta es ≈ 0 hasta que una prueba larga diga
  otra cosa.
- La mirada queda registrada como consumida para el linaje de las 5 (`HOLDOUT_VENTANAS.jsonl`, tipo `consumida_atras`).
