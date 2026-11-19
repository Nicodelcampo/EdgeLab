# LucidFlex con el marco de la guía: EV por examen, tiempos para pasar o quemar, y la cartera con el máximo de 5 fondeadas (2026-11-19)

Estado: VIGENTE — cálculo descriptivo sobre operaciones ya medidas (no elige reglas, no abre REP ni holdout, no cuenta pruebas). Pedido de
Nico: «rehacé los cálculos aprovechando esta guía. Y es un tema importante el tiempo que se demora en pasar o quemar una cuenta, sobre todo si
el máximo es 5 en Lucid. Investigá también si incumpliríamos alguna regla». North Star sha256
`16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Código: `tools/lucid_guia.py`; datos: `LUCID_GUIA.json`; reglas
contra estrategias: `CUMPLIMIENTO.md`.

## Qué se toma de la guía y qué cambia
- **De la guía** («Cómo exprimir a las casas de fondeo», RobotEdge):
  - el EV se mide por examen comprado, como una cascada: pasar → primer retiro → retiros siguientes;
  - la política de retiro es esperar el monto máximo;
  - las cuentas quemadas son parte del plan;
  - cuentan el plan de riesgo por día y el tiempo de cada cuenta.
- **Lo que la guía tiene viejo:** su tabla de LucidFlex 50K ($98, consistencia 50 %, sin DLL, colchón de $2.100, retiro de $2.000 en 3 días).
  Acá se usan las reglas oficiales del 2026-11-19 para los cuatro tamaños:

| Tamaño | Objetivo | Pérdida máx. EOD | DLL | Día mínimo para retiro | Tope por retiro | Máx. micros | Precio con DLL, 50 % (VAULT) | Sin DLL |
|---|---|---|---|---|---|---|---|---|
| 25K | 1.250 | 1.000 | 600 | 100 | 1.000 | 20 | 55 | 62 |
| 50K | 3.000 | 2.000 | 1.200 | 150 | 2.000 | 40 | 95 | 102 |
| 100K | 6.000 | 3.000 | 1.800 | 200 | 2.500 | 60 | 181 | 205 |
| 150K | 9.000 | 4.500 | 2.700 | 250 | 3.000 | 100 | 260 | 285 |

Reglas comunes:
- Piso EOD que se fija en +$100 al superar la pérdida máxima + $100 o al primer retiro.
- Retiro: 5 días con el mínimo diario y neto del ciclo > 0; 50 % del beneficio hasta el tope; mínimo $500; reparto 90/10; hasta 5 retiros.
- Al 5.º retiro la cuenta pasa a live y **se cierran todas las cuentas de simulación del hogar**.
- Límites: 10 evaluaciones, 5 fondeadas y 10 cuentas en total por hogar.

Precios:
- Lista de trader-review.io (2026-10-07) con el código VAULT (−30 %). El 25K coincide con lo verificado el 17-nov.
- Los de consistencia 40 % se estiman (en `LUCID_GUIA.json`); **sólo se simuló la consistencia de 50 %**.

## Modelo
- **Series:**
  - USD por sesión de las canastas en MNQ (`lucid_canastas.serie_senales`), 2020-01 → 2025-07 de desarrollo.
  - Tamaño por riesgo: micros = USD de riesgo / (riesgo en puntos × 2), con tope por regla = máximo de micros del tamaño / 3.
  - Fricción canónica de MNQ.
- **Riesgo por operación:** 100 o 200 USD en la 25K, escalado con la pérdida máxima del tamaño (50K: 200/400; 100K: 300/600; 150K: 450/900).
- **SOM** entra como `SOMEOD` (cierra 15:55 ET). La SOM de las tablas anteriores (`sin_finde`) deja posiciones de noche, y Lucid no lo
  permite (ver `CUMPLIMIENTO.md`).
- **Media:** la de desarrollo («dev»), la contraída a la mitad (lectura principal, como en las tablas anteriores) y cero (sin ventaja).
- **Bootstrap:** por bloques de 5 sesiones, recentrado a la media.
- **Por cuenta:** 20.000 cuentas, hasta 500 días hábiles por etapa.
- **Cartera:** 4.000 calendarios de 24 meses.
  - Todas las cuentas operan la misma canasta, o sea el mismo P&L el mismo día. Es lo único que no choca con la regla de cobertura.
  - Se compra una evaluación por día mientras haya lugar.
  - Una evaluación aprobada espera si ya hay 5 fondeadas.
  - El primer 5.º retiro termina la etapa de simulación. Las evaluaciones en curso se reembolsan si les queda ≥ 50 % del drawdown.
- **No modelado:**
  - lo que paga la cuenta live (empieza en $0, retiros diarios);
  - el tamaño máximo de la fondeada si escala con la ganancia (las fuentes no coinciden);
  - el DLL se aplica como un corte de la pérdida del día.

## 1. Por cuenta (media contraída, DLL, consistencia 50 %)
| Tamaño | Riesgo/op. USD | Canasta | Precio | Pasa | Días hábiles a pasar p10/50/90 | Días a quemar la evaluación p10/50/90 | Cobra si pasa | Retiros si cobra | Días de fondeada al 1.er retiro p10/50/90 | Quema la fondeada (si pasa) | Llega a 5 retiros (live) | Cobrado medio | EV por examen | EV por mes de cuenta |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 25K | 100 | T | 55 | 51 % | 13 / 32 / 66 | 12 / 29 / 63 | 39 % | 2,85 | 29 / 58 / 111 | 90 % | 5 % | +504 | +449 | +118 |
| 25K | 100 | T+R | 55 | 48 % | 11 / 29 / 66 | 10 / 24 / 55 | 40 % | 2,89 | 18 / 42 / 84 | 89 % | 5 % | +501 | +446 | +145 |
| 25K | 100 | T+R+ZB | 55 | 49 % | 10 / 26 / 60 | 10 / 22 / 50 | 42 % | 2,97 | 17 / 39 / 78 | 87 % | 7 % | +557 | +501 | +170 |
| 25K | 100 | T+R+ZB+SOMEOD | 55 | 34 % | 7 / 18 / 48 | 5 / 12 / 29 | 32 % | 2,81 | 9 / 17 / 34 | 91 % | 3 % | +272 | +216 | +159 |
| 25K | 200 | T | 55 | 49 % | 12 / 29 / 61 | 12 / 26 / 57 | 37 % | 2,80 | 26 / 53 / 103 | 91 % | 5 % | +463 | +408 | +121 |
| 25K | 200 | T+R | 55 | 46 % | 11 / 26 / 60 | 10 / 22 / 49 | 39 % | 2,86 | 17 / 38 / 74 | 89 % | 5 % | +463 | +408 | +150 |
| 25K | 200 | T+R+ZB | 55 | 48 % | 9 / 24 / 53 | 9 / 20 / 45 | 41 % | 2,94 | 15 / 34 / 70 | 87 % | 6 % | +524 | +468 | +180 |
| 25K | 200 | T+R+ZB+SOMEOD | 55 | 34 % | 6 / 17 / 46 | 4 / 11 / 27 | 32 % | 2,82 | 9 / 16 / 32 | 90 % | 3 % | +272 | +217 | +167 |
| 50K | 200 | T | 95 | 59 % | 57 / 125 / 246 | 39 / 96 / 209 | 55 % | 2,60 | 90 / 181 / 333 | 62 % | 4 % | +1.529 | +1.434 | +98 |
| 50K | 200 | T+R | 95 | 60 % | 39 / 89 / 178 | 31 / 71 / 157 | 58 % | 3,28 | 64 / 131 / 250 | 67 % | 11 % | +2.050 | +1.955 | +166 |
| 50K | 200 | T+R+ZB | 95 | 63 % | 35 / 79 / 162 | 28 / 66 / 141 | 60 % | 3,47 | 55 / 118 / 220 | 66 % | 15 % | +2.350 | +2.255 | +201 |
| 50K | 200 | T+R+ZB+SOMEOD | 95 | 43 % | 16 / 37 / 81 | 12 / 28 / 64 | 37 % | 2,89 | 21 / 48 / 101 | 89 % | 4 % | +828 | +733 | +215 |
| 50K | 400 | T | 95 | 44 % | 14 / 33 / 66 | 11 / 25 / 57 | 38 % | 2,81 | 23 / 49 / 94 | 90 % | 4 % | +844 | +749 | +239 |
| 50K | 400 | T+R | 95 | 43 % | 12 / 27 / 57 | 9 / 21 / 47 | 39 % | 2,88 | 16 / 35 / 69 | 89 % | 5 % | +862 | +767 | +307 |
| 50K | 400 | T+R+ZB | 95 | 45 % | 10 / 24 / 53 | 8 / 19 / 42 | 40 % | 3,00 | 14 / 32 / 64 | 87 % | 6 % | +956 | +861 | +365 |
| 50K | 400 | T+R+ZB+SOMEOD | 95 | 38 % | 8 / 20 / 47 | 6 / 14 / 33 | 34 % | 2,85 | 10 / 21 / 43 | 90 % | 4 % | +654 | +559 | +351 |
| 100K | 300 | T | 181 | 56 % | 117 / 233 / 398 | 54 / 132 / 299 | 60 % | 2,59 | 88 / 188 / 345 | 59 % | 4 % | +1.955 | +1.774 | +91 |
| 100K | 300 | T+R | 181 | 61 % | 78 / 160 / 307 | 40 / 96 / 226 | 63 % | 3,25 | 59 / 128 / 254 | 66 % | 13 % | +2.837 | +2.656 | +175 |
| 100K | 300 | T+R+ZB | 181 | 63 % | 65 / 140 / 270 | 36 / 84 / 193 | 65 % | 3,46 | 49 / 111 / 222 | 66 % | 17 % | +3.201 | +3.020 | +219 |
| 100K | 300 | T+R+ZB+SOMEOD | 181 | 46 % | 34 / 76 / 154 | 19 / 45 / 110 | 48 % | 3,04 | 25 / 59 / 121 | 84 % | 7 % | +1.494 | +1.313 | +230 |
| 100K | 600 | T | 181 | 39 % | 21 / 46 / 91 | 11 / 26 / 65 | 41 % | 2,71 | 17 / 36 / 71 | 90 % | 4 % | +959 | +778 | +258 |
| 100K | 600 | T+R | 181 | 39 % | 16 / 35 / 70 | 9 / 21 / 52 | 41 % | 2,80 | 12 / 26 / 52 | 89 % | 4 % | +1.014 | +833 | +349 |
| 100K | 600 | T+R+ZB | 181 | 40 % | 14 / 32 / 65 | 8 / 19 / 46 | 43 % | 2,92 | 11 / 24 / 49 | 87 % | 5 % | +1.128 | +948 | +423 |
| 100K | 600 | T+R+ZB+SOMEOD | 181 | 35 % | 11 / 24 / 52 | 6 / 14 / 35 | 37 % | 2,82 | 9 / 17 / 33 | 89 % | 4 % | +824 | +644 | +411 |
| 150K | 450 | T | 260 | 55 % | 90 / 181 / 338 | 41 / 102 / 237 | 61 % | 2,99 | 48 / 109 / 220 | 79 % | 9 % | +2.678 | +2.418 | +178 |
| 150K | 450 | T+R | 260 | 57 % | 60 / 128 / 248 | 32 / 75 / 179 | 62 % | 3,14 | 33 / 77 / 161 | 79 % | 12 % | +2.965 | +2.705 | +269 |
| 150K | 450 | T+R+ZB | 260 | 59 % | 52 / 112 / 219 | 28 / 67 / 158 | 63 % | 3,23 | 28 / 67 / 141 | 76 % | 14 % | +3.240 | +2.979 | +326 |
| 150K | 450 | T+R+ZB+SOMEOD | 260 | 49 % | 33 / 75 / 151 | 19 / 45 / 108 | 55 % | 2,97 | 19 / 45 / 95 | 83 % | 8 % | +2.142 | +1.882 | +347 |
| 150K | 900 | T | 260 | 39 % | 23 / 50 / 97 | 11 / 28 / 70 | 46 % | 2,63 | 12 / 29 / 60 | 89 % | 4 % | +1.288 | +1.028 | +339 |
| 150K | 900 | T+R | 260 | 39 % | 16 / 36 / 74 | 9 / 22 / 54 | 46 % | 2,76 | 10 / 21 / 44 | 87 % | 5 % | +1.351 | +1.091 | +460 |
| 150K | 900 | T+R+ZB | 260 | 41 % | 15 / 33 / 68 | 8 / 20 / 48 | 47 % | 2,88 | 9 / 20 / 41 | 85 % | 6 % | +1.495 | +1.235 | +556 |
| 150K | 900 | T+R+ZB+SOMEOD | 260 | 35 % | 11 / 24 / 52 | 6 / 14 / 35 | 42 % | 2,81 | 8 / 14 / 28 | 87 % | 4 % | +1.098 | +837 | +538 |

Días = días hábiles de operación (≈ 21 por mes). «Quema la fondeada» incluye las que cobran algún retiro y después se queman.

## 2. Sensibilidad del EV por examen a la media (DLL, 50 %)
| Tamaño | Riesgo/op. USD | Canasta | EV/examen media de desarrollo | EV/examen contraída (×0,5) | EV/examen sin ventaja | Pasa (dev / contr. / cero) | Sin DLL: EV contraída |
|---|---|---|---|---|---|---|---|
| 25K | 100 | T | +1.422 | +449 | +51 | 69 % / 51 % / 31 % | +442 |
| 25K | 100 | T+R+ZB | +1.709 | +501 | +43 | 72 % / 49 % / 27 % | +494 |
| 25K | 200 | T | +1.247 | +408 | +54 | 66 % / 49 % / 32 % | +401 |
| 25K | 200 | T+R+ZB | +1.590 | +468 | +51 | 70 % / 48 % / 27 % | +461 |
| 50K | 200 | T | +5.166 | +1.434 | +39 | 85 % / 59 % / 26 % | +1.427 |
| 50K | 200 | T+R+ZB | +6.632 | +2.255 | +78 | 90 % / 63 % / 26 % | +2.248 |
| 50K | 400 | T | +2.321 | +749 | +102 | 63 % / 44 % / 27 % | +742 |
| 50K | 400 | T+R+ZB | +2.908 | +861 | +105 | 66 % / 45 % / 25 % | +853 |
| 100K | 300 | T | +6.723 | +1.774 | -46 | 88 % / 56 % / 17 % | +1.750 |
| 100K | 300 | T+R+ZB | +8.685 | +3.020 | +18 | 92 % / 63 % / 19 % | +2.996 |
| 100K | 600 | T | +2.598 | +778 | +47 | 60 % / 39 % / 20 % | +754 |
| 100K | 600 | T+R+ZB | +3.361 | +948 | +65 | 64 % / 40 % / 20 % | +920 |
| 150K | 450 | T | +7.729 | +2.418 | +14 | 85 % / 55 % / 19 % | +2.393 |
| 150K | 450 | T+R+ZB | +8.944 | +2.979 | +72 | 88 % / 59 % / 20 % | +2.955 |
| 150K | 900 | T | +3.210 | +1.028 | +74 | 60 % / 39 % / 20 % | +1.004 |
| 150K | 900 | T+R+ZB | +4.142 | +1.235 | +91 | 65 % / 41 % / 20 % | +1.210 |

El DLL casi no cambia nada: con estos tamaños la pérdida de un día rara vez llega al DLL. Sin DLL la cuenta cuesta más y el EV baja en la
diferencia de precio.

## 3. Cartera con los límites de Lucid (media contraída, DLL, 50 %; 24 meses o hasta el paso a live)
Las filas con 5 evaluaciones a la vez y las demás canastas (T+R y T+R+ZB+SOMEOD) están en `LUCID_GUIA.json`.
| Tamaño | Riesgo/op. USD | Canasta | Evaluaciones a la vez | Neto 24 m medio | Neto 24 m p10 / p50 / p90 | P(neto > 0) | Neto primeros 12 m | Paso a live en 24 m | Meses hasta live p10/50/90 | Caja mínima p50 / p10 | Evaluaciones compradas | Fondeadas | Retiros | Neto 24 m SIN ventaja |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 25K | 100 | T | 1 | +3.483 | -774 / 2688 / 9015 | 82 % | +1.261 | 23 % | 10 / 16 / 22 | -387 / -829 | 13.7 | 6.4 | 4.7 | +315 |
| 25K | 100 | T | 10 | +13.776 | 187 / 15788 / 23930 | 90 % | +5.419 | 34 % | 10 / 16 / 22 | -1382 / -3705 | 48.1 | 19.6 | 18.3 | +1.970 |
| 25K | 100 | T+R | 1 | +3.939 | -664 / 3615 / 8559 | 84 % | +1.716 | 32 % | 8 / 15 / 22 | -387 / -829 | 14.4 | 6.4 | 5.3 | +303 |
| 25K | 100 | T+R | 10 | +16.777 | 2190 / 18347 / 28596 | 92 % | +7.802 | 48 % | 8 / 14 / 22 | -1438 / -3871 | 54.0 | 21.2 | 22.0 | +2.107 |
| 25K | 100 | T+R+ZB | 1 | +4.648 | -151 / 4736 / 9126 | 87 % | +2.166 | 41 % | 8 / 14 / 22 | -332 / -829 | 14.7 | 6.8 | 6.1 | +455 |
| 25K | 100 | T+R+ZB | 10 | +18.519 | 4952 / 19247 / 30194 | 95 % | +9.256 | 55 % | 7 / 14 / 22 | -1382 / -3597 | 52.5 | 21.5 | 23.8 | +2.793 |
| 25K | 100 | T+R+ZB+SOMEOD | 1 | +3.659 | -885 / 3852 / 8170 | 81 % | +1.837 | 42 % | 6 / 13 / 21 | -498 / -1382 | 22.5 | 7.4 | 5.5 | +638 |
| 25K | 100 | T+R+ZB+SOMEOD | 10 | +17.301 | 1257 / 18257 / 30526 | 91 % | +9.429 | 65 % | 6 / 12 / 21 | -2378 / -6465 | 99.5 | 30.1 | 25.3 | +4.176 |
| 25K | 200 | T | 1 | +3.533 | -830 / 2660 / 9070 | 80 % | +1.349 | 24 % | 9 / 16 / 22 | -387 / -885 | 14.8 | 6.8 | 4.8 | +428 |
| 25K | 200 | T | 10 | +14.121 | 101 / 16024 / 24773 | 90 % | +5.877 | 34 % | 9 / 16 / 22 | -1438 / -3982 | 53.1 | 21.6 | 19.0 | +2.467 |
| 25K | 200 | T+R | 1 | +4.055 | -427 / 3836 / 8668 | 83 % | +1.789 | 34 % | 8 / 14 / 22 | -387 / -940 | 15.6 | 6.7 | 5.5 | +377 |
| 25K | 200 | T+R | 10 | +17.252 | 3036 / 18352 / 29291 | 93 % | +8.336 | 49 % | 8 / 14 / 22 | -1526 / -4079 | 59.3 | 22.9 | 22.8 | +2.691 |
| 25K | 200 | T+R+ZB | 1 | +4.853 | -151 / 5139 / 9347 | 88 % | +2.355 | 42 % | 7 / 13 / 22 | -387 / -885 | 16.0 | 7.3 | 6.4 | +571 |
| 25K | 200 | T+R+ZB | 10 | +18.965 | 6034 / 19247 / 31023 | 95 % | +10.000 | 59 % | 7 / 13 / 21 | -1438 / -3760 | 56.7 | 22.7 | 24.6 | +3.519 |
| 25K | 200 | T+R+ZB+SOMEOD | 1 | +3.775 | -834 / 3907 / 8241 | 82 % | +1.897 | 44 % | 6 / 13 / 21 | -553 / -1382 | 23.1 | 7.5 | 5.6 | +669 |
| 25K | 200 | T+R+ZB+SOMEOD | 10 | +17.449 | 2035 / 18393 / 30556 | 92 % | +9.663 | 65 % | 6 / 12 / 21 | -2378 / -6576 | 102.4 | 30.7 | 25.7 | +4.421 |
| 50K | 200 | T | 1 | +1.620 | -476 / -286 / 6543 | 45 % | -27 | 2 % | 17 / 22 / 24 | -381 / -571 | 4.5 | 2.1 | 1.1 | -242 |
| 50K | 200 | T | 10 | +7.328 | -3332 / 6382 / 25667 | 55 % | -372 | 2 % | 18 / 22 / 23 | -1523 / -3332 | 20.4 | 7.4 | 5.2 | -1.989 |
| 50K | 200 | T+R | 1 | +4.001 | -571 / 1324 / 13734 | 66 % | +465 | 9 % | 16 / 21 / 24 | -381 / -666 | 5.9 | 2.9 | 2.5 | -136 |
| 50K | 200 | T+R | 10 | +16.232 | -3332 / 16001 / 36848 | 76 % | +2.343 | 12 % | 16 / 21 / 23 | -1714 / -3522 | 22.7 | 8.9 | 10.2 | -1.175 |
| 50K | 200 | T+R+ZB | 1 | +5.254 | -666 / 3029 / 15724 | 73 % | +871 | 15 % | 15 / 20 / 23 | -381 / -666 | 6.2 | 3.3 | 3.2 | -47 |
| 50K | 200 | T+R+ZB | 10 | +20.534 | -3046 / 23668 / 41669 | 83 % | +4.317 | 19 % | 15 / 20 / 23 | -1428 / -3427 | 22.6 | 9.3 | 12.6 | -658 |
| 50K | 200 | T+R+ZB+SOMEOD | 1 | +5.486 | -1238 / 3877 / 15248 | 78 % | +2.147 | 22 % | 9 / 16 / 22 | -666 / -1333 | 12.2 | 4.8 | 3.7 | +443 |
| 50K | 200 | T+R+ZB+SOMEOD | 10 | +27.005 | -2977 / 30855 / 49240 | 88 % | +10.948 | 35 % | 9 / 16 / 22 | -2856 / -7235 | 53.9 | 18.8 | 17.9 | +2.975 |
| 50K | 400 | T | 1 | +6.369 | -1428 / 5296 / 15629 | 82 % | +2.587 | 24 % | 9 / 16 / 22 | -666 / -1523 | 14.3 | 5.8 | 4.3 | +882 |
| 50K | 400 | T | 10 | +28.664 | 42 / 32555 / 50850 | 90 % | +11.907 | 36 % | 9 / 15 / 22 | -2761 / -7521 | 57.8 | 21.2 | 19.0 | +5.408 |
| 50K | 400 | T+R | 1 | +7.853 | -1238 / 7477 / 16382 | 84 % | +3.615 | 34 % | 7 / 14 / 22 | -666 / -1618 | 15.9 | 6.4 | 5.2 | +1.058 |
| 50K | 400 | T+R | 10 | +35.214 | 6014 / 37289 / 60144 | 94 % | +17.294 | 50 % | 7 / 13 / 22 | -2856 / -7711 | 64.0 | 23.1 | 22.9 | +7.312 |
| 50K | 400 | T+R+ZB | 1 | +9.368 | -199 / 9943 / 17611 | 87 % | +4.700 | 43 % | 7 / 13 / 21 | -666 / -1618 | 16.4 | 6.9 | 6.1 | +1.424 |
| 50K | 400 | T+R+ZB | 10 | +38.905 | 11509 / 39574 / 63560 | 96 % | +20.938 | 60 % | 7 / 13 / 21 | -2666 / -7235 | 61.5 | 23.1 | 24.9 | +8.757 |
| 50K | 400 | T+R+ZB+SOMEOD | 1 | +8.343 | -770 / 8429 / 16953 | 86 % | +4.101 | 42 % | 6 / 13 / 22 | -762 / -2094 | 20.4 | 7.3 | 5.7 | +1.326 |
| 50K | 400 | T+R+ZB+SOMEOD | 10 | +38.548 | 9008 / 38648 / 66175 | 94 % | +20.847 | 62 % | 6 / 12 / 21 | -3522 / -9425 | 86.6 | 28.4 | 26.0 | +9.061 |
| 100K | 300 | T | 1 | +654 | -722 / -361 / 3958 | 27 % | -244 | 0 % | 18 / 22 / 24 | -361 / -722 | 2.9 | 1.0 | 0.5 | -502 |
| 100K | 300 | T | 10 | +3.231 | -5418 / -1806 / 20694 | 33 % | -2.124 | 1 % | 18 / 21 / 24 | -2709 / -5418 | 17.2 | 5.1 | 2.8 | -4.556 |
| 100K | 300 | T+R | 1 | +2.818 | -903 / 1347 / 10528 | 53 % | +70 | 6 % | 17 / 21 / 24 | -542 / -903 | 3.8 | 1.7 | 1.6 | -511 |
| 100K | 300 | T+R | 10 | +14.196 | -5418 / 8541 / 43194 | 63 % | -303 | 8 % | 17 / 21 / 24 | -2709 / -5418 | 19.4 | 7.0 | 7.9 | -4.591 |
| 100K | 300 | T+R+ZB | 1 | +4.107 | -903 / 1708 / 15028 | 62 % | +376 | 13 % | 15 / 20 / 23 | -542 / -903 | 4.2 | 2.0 | 2.2 | -488 |
| 100K | 300 | T+R+ZB | 10 | +20.084 | -5418 / 19249 / 49410 | 73 % | +1.479 | 16 % | 15 / 20 / 23 | -2709 / -5797 | 20.0 | 7.7 | 10.5 | -4.242 |
| 100K | 300 | T+R+ZB+SOMEOD | 1 | +4.666 | -1625 / 2875 / 14847 | 69 % | +1.342 | 18 % | 11 / 17 / 23 | -903 / -1625 | 7.2 | 2.8 | 2.7 | -449 |
| 100K | 300 | T+R+ZB+SOMEOD | 10 | +26.908 | -9211 / 28332 / 54444 | 80 % | +7.626 | 30 % | 11 / 17 / 23 | -4515 / -10294 | 37.9 | 12.9 | 15.0 | -3.200 |
| 100K | 600 | T | 1 | +5.725 | -2528 / 4222 / 15208 | 71 % | +2.368 | 23 % | 8 / 14 / 22 | -1084 / -2528 | 11.8 | 4.2 | 3.5 | -72 |
| 100K | 600 | T | 10 | +32.056 | -9250 / 36745 / 64961 | 83 % | +13.190 | 37 % | 8 / 14 / 22 | -5606 / -15170 | 62.4 | 19.8 | 19.3 | -290 |
| 100K | 600 | T+R | 1 | +7.756 | -2528 / 7819 / 17097 | 78 % | +3.614 | 35 % | 7 / 13 / 22 | -1084 / -2890 | 13.9 | 5.0 | 4.6 | +53 |
| 100K | 600 | T+R | 10 | +40.170 | -2867 / 44180 / 73772 | 89 % | +19.498 | 53 % | 7 / 13 / 21 | -5779 / -15484 | 68.1 | 22.1 | 23.3 | +1.556 |
| 100K | 600 | T+R+ZB | 1 | +9.287 | -1181 / 10347 / 18527 | 85 % | +4.568 | 43 % | 6 / 13 / 22 | -1084 / -2815 | 14.3 | 5.4 | 5.3 | +271 |
| 100K | 600 | T+R+ZB | 10 | +45.058 | 6523 / 46588 / 79164 | 93 % | +24.300 | 62 % | 6 / 12 / 21 | -5418 / -14448 | 65.7 | 22.2 | 25.3 | +2.561 |
| 100K | 600 | T+R+ZB+SOMEOD | 1 | +8.743 | -2265 / 9346 / 18898 | 82 % | +4.370 | 43 % | 6 / 12 / 21 | -1445 / -3612 | 18.9 | 6.3 | 5.4 | +327 |
| 100K | 600 | T+R+ZB+SOMEOD | 10 | +43.465 | 339 / 45587 / 79360 | 90 % | +23.761 | 64 % | 6 / 12 / 21 | -6863 / -18880 | 88.4 | 26.8 | 26.4 | +2.725 |
| 150K | 450 | T | 1 | +2.521 | -1302 / -521 / 12198 | 47 % | -54 | 6 % | 15 / 20 / 24 | -781 / -1302 | 3.5 | 1.3 | 1.3 | -629 |
| 150K | 450 | T | 10 | +13.985 | -8333 / 7559 / 51396 | 58 % | -1.239 | 8 % | 16 / 20 / 23 | -4166 / -8854 | 21.3 | 7.1 | 7.2 | -5.832 |
| 150K | 450 | T+R | 1 | +5.139 | -1562 / 3577 / 15679 | 66 % | +845 | 16 % | 13 / 19 / 23 | -781 / -1562 | 4.5 | 1.9 | 2.3 | -532 |
| 150K | 450 | T+R | 10 | +28.376 | -9114 / 30084 / 63594 | 77 % | +4.165 | 25 % | 13 / 19 / 23 | -4687 / -9635 | 25.2 | 9.4 | 12.9 | -4.987 |
| 150K | 450 | T+R+ZB | 1 | +6.510 | -1562 / 4098 / 17858 | 74 % | +1.717 | 22 % | 11 / 17 / 22 | -781 / -1562 | 4.8 | 2.2 | 2.9 | -420 |
| 150K | 450 | T+R+ZB | 10 | +35.852 | -7828 / 42659 / 64896 | 84 % | +8.720 | 34 % | 12 / 18 / 23 | -4166 / -9635 | 25.6 | 10.0 | 15.7 | -4.275 |
| 150K | 450 | T+R+ZB+SOMEOD | 1 | +7.355 | -2083 / 5756 / 17858 | 78 % | +2.609 | 26 % | 9 / 15 / 22 | -1042 / -2083 | 6.9 | 2.9 | 3.4 | -266 |
| 150K | 450 | T+R+ZB+SOMEOD | 10 | +41.225 | -8411 / 48724 / 77094 | 86 % | +15.085 | 41 % | 9 / 15 / 22 | -5208 / -13280 | 37.0 | 13.6 | 18.8 | -2.485 |
| 150K | 900 | T | 1 | +7.274 | -3125 / 5236 / 18119 | 75 % | +3.076 | 26 % | 7 / 14 / 22 | -1562 / -3385 | 10.9 | 3.8 | 3.7 | +135 |
| 150K | 900 | T | 10 | +41.468 | -10196 / 47970 / 83892 | 85 % | +18.019 | 44 % | 7 / 14 / 22 | -7812 / -19790 | 60.2 | 19.3 | 21.2 | +661 |
| 150K | 900 | T+R | 1 | +9.882 | -2248 / 10814 / 20558 | 82 % | +4.704 | 40 % | 6 / 13 / 22 | -1562 / -3906 | 12.8 | 4.7 | 4.9 | +243 |
| 150K | 900 | T+R | 10 | +51.189 | 1081 / 54192 / 93685 | 90 % | +27.091 | 60 % | 6 / 12 / 21 | -7812 / -20337 | 65.5 | 21.5 | 25.3 | +2.182 |
| 150K | 900 | T+R+ZB | 1 | +11.603 | -1466 / 13075 / 21956 | 87 % | +5.958 | 49 % | 6 / 12 / 21 | -1302 / -3646 | 13.2 | 5.0 | 5.6 | +524 |
| 150K | 900 | T+R+ZB | 10 | +56.441 | 11682 / 56824 / 97326 | 93 % | +31.834 | 68 % | 6 / 11 / 20 | -7031 / -19274 | 63.3 | 21.4 | 27.0 | +4.483 |
| 150K | 900 | T+R+ZB+SOMEOD | 1 | +10.968 | -2672 / 11938 / 22738 | 83 % | +5.458 | 49 % | 5 / 12 / 21 | -1823 / -4948 | 17.9 | 5.9 | 5.8 | +445 |
| 150K | 900 | T+R+ZB+SOMEOD | 10 | +52.451 | 3808 / 54295 / 94459 | 91 % | +29.555 | 69 % | 5 / 12 / 21 | -9374 / -25780 | 85.3 | 25.6 | 27.7 | +3.430 |

«Caja mínima» = lo peor que llega a estar la caja acumulada (compras menos cobros) en el camino. «Neto 24 m SIN ventaja» = misma cartera con
media cero.

## 4. Datos que contestan las preguntas
- **Tiempo para pasar o quemar (25K, 100 USD, contraída):**
  - pasar: mediana de 26–32 días hábiles (≈ 1,5 meses); la cola p90 llega a 60–66 días;
  - quemar la evaluación: mediana de 22–29 días;
  - de fondeada al primer retiro: mediana de 39–58 días;
  - con SOMEOD todo es ≈ 2 veces más rápido (pasar 18, quemar 12, primer retiro 17), pero pasa el 34 % en vez del 48–51 %.
- **Riesgo chico en cuentas grandes = cuentas lentas:**
  - 50K con 200 USD: T tarda 125 días de mediana en pasar;
  - 100K con 300 USD: 233 días;
  - con el doble de riesgo baja a 33 y 46 días.
- **El techo del máximo de 5:**
  - la etapa de simulación termina en el primer 5.º retiro;
  - con 10 evaluaciones a la vez, en 25K (T, T+R, T+R+ZB) pasa a live el 34–59 % de los calendarios dentro de 24 meses (mediana a los 13–16 meses);
  - la cartera compra 48–59 evaluaciones y llega a 20–23 fondeadas en 24 meses.
- **Cartera, 24 meses, media contraída:**

| Configuración | Neto | P(neto > 0) | Sin ventaja |
|---|---|---|---|
| 25K T+R+ZB, 100 USD, 10 evaluaciones | +18.519 | 95 % | +2.793 |
| 50K T+R+ZB, 400 USD | +38.905 | 96 % | +8.757 |
| 100K T+R+ZB, 600 USD | +45.058 | 93 % | +2.561 |
| 150K T+R+ZB, 900 USD | +56.441 | 93 % | +4.483 |

  - Caja mínima p10: −3.597 / −7.235 / −14.448 / −19.274.
  - Con una sola evaluación a la vez el neto es ≈ 4 veces menor (25K +4.648; 150K +11.603).
- **Correlación entre cuentas:** todas las cuentas reciben el mismo P&L, así que las que arrancan el mismo día pasan o se queman juntas. Comprar
  varias el mismo día no diversifica; escalonar la compra (una por día) sí reparte el punto de partida.
- **Comparación con las tablas anteriores** (25K, T+R+ZB, 100 USD, contraída): EV por examen +501, contra +489 en
  `FRECUENCIA_PROP_20261119.md`. La diferencia sale del horizonte (500 días contra 250) y de exigir el retiro máximo. Con SOMEOD en lugar
  de `sin_finde`: +216 (antes +252).

## Justificación económica / cómo podría refutarse
- **Justificación:** la cuenta de Lucid es una opción (pérdida acotada al precio, retiros con tope). La canasta con media positiva
  la ejerce más veces que el azar (EV sin ventaja por examen: +39 a +105 en 25K–50K; −46 a +91 en 100K–150K).
- **Cómo podría refutarse:** el forward de la canasta (`regimen_forward_20261119/`) con media ≤ 0, o una regla de Lucid que cierre
  las cuentas (coordinación entre usuarios, `CUMPLIMIENTO.md`). Las dos llevan el EV hacia la columna «sin ventaja» o a perder los precios.

Aporte al referente: traduce la canasta candidata a dinero por examen y por mes con las reglas reales de los cuatro tamaños, el techo de 5
fondeadas y el cierre al pasar a live, y mide cuánto tarda cada cuenta en pasar o quemarse; deja escrito qué de la operativa violaría las reglas.
