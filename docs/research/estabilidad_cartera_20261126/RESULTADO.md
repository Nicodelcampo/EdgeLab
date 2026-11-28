# ESTABILIDAD-CARTERA: la caída del final es de las estrategias de la mañana; ninguna mitigación pasa el criterio; C2_VZ, N, F y las intradía de tendencia suman estabilidad (resultado, 2026-11-26)

Estado: RESULTADO — pre-registrado (`PREREGISTRO.md`), 1 lectura contada. Descriptivo; lo elegido sobre datos vistos se confirma sólo en
forward.
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Datos:** `RESULTADO.json` y `SERIES_DIARIAS.csv.gz`.
- **Gráficos:** `CURVAS_ESTRATEGIAS_CAIDA_FINAL.png` y `CURVAS_CARTERAS_CON_CANDIDATAS.png`.
- **Herramienta:** `tools/estabilidad_cartera.py`.

Diagnóstico de grilla: no hay grilla de perillas: 3 mitigaciones fijas y un tamiz con criterio fijo sobre ≈ 60 series.
Episodios: la caída de mayo a septiembre de 2026, por estrategia, en la tabla A.

## A. La caída del final (mayo → septiembre 2026, USD con 1 micro)

| Estrategia | Caída final | Percentil entre sus caídas | Peor caída histórica | Resultado del tramo |
|---|---|---|---|---|
| RQ5 MNQ | −6.173 | 99 | −6.784 | −4.841 |
| Franklin MNQ | −3.071 | 98 | −4.387 | −1.593 |
| RQ5 MES | −2.626 | 98 | −3.285 | −2.465 |
| ES5N MES | −1.747 | 96 | −3.185 | −1.747 |
| T MNQ | −1.616 | 99 | −2.037 | **+2.374** |
| V MNQ | −1.237 | 94 | −3.220 | −449 |
| R, Z | −334 / −419 | 67 / 60 | | +2.392 / +1.524 |
| SOM, C2_VZ NQ/ES (Interdía) | ≈ 0 | | | **+3.645 / +3.859 / +1.557** |
| **INTRADIA8** | **−10.831** | **99** (2.ª peor) | −13.964 | −4.806 |
| **INTERDIA3** | −48 | 16 | −10.896 | **+9.061** |

**Lectura de A:**
- **No es un factor común:** la correlación media entre las 8 de Intradía bajó en el tramo (0,21 contra 0,26 del resto).
- **Mercado en el tramo:** NQ subió 10,6 % con volatilidad baja (18,5 % anual contra 22 %).
- **De dónde viene la caída:** casi entera de las estrategias de **la mañana** (RQ5, Franklin y ES5N: rupturas o sesgo alrededor de las
  10:00). Entre ellas tienen la correlación más alta de la cartera (0,47–0,62) y las tres están en el percentil 96–99 de sus caídas.
- **Lo que no cayó:** T, R y Z (tendencia del día) y la Interdía ganaron en el tramo.
- **Qué significa:** una caída en el percentil 96–99 todavía puede ser ruido; ninguna supera su peor caída histórica. Pero es la señal que
  hay que vigilar: si pasan su peor caída, eso ya no es un tramo malo.

## B. Mitigaciones (walk-forward 2020-07 → 2026-09, sólo información pasada)

| Intradía | Sharpe anual | Caída máx. | Peor mes | Tramo final |
|---|---|---|---|---|
| M0 pesos iguales (base) | 1,80 | −13.964 | −4.242 | −4.806 |
| M1 inverso de volatilidad | 1,75 | −14.503 | −5.883 | −4.457 |
| **M2 freno por curva de 3 meses** | 1,67 | **−7.661** | **−2.253** | **−1.756** |
| M3 poda por t de 12 meses | 1,76 | −11.029 | −2.468 | −4.065 |

En Interdía pasa lo mismo: M2 baja la caída máxima de −10.896 a −7.668 y el Sharpe pasa de 1,21 a 1,05.

**Lectura de B:**
- **Con el criterio pre-registrado (Sharpe +0,2) no se adopta ninguna.**
- **M2 es un canje explícito:** pausar una estrategia mientras sus últimos 3 meses en sombra sean negativos corta a la mitad la caída
  máxima y el peor mes, y en el tramo final habría perdido −1.756 en lugar de −4.806. A cambio, cobra ≈ 30 % del USD/mes (ganancias que se
  pierde al pausar). Para una cuenta prop con piso fijo, la caída máxima puede pesar más que el Sharpe. Es decisión de Nico, y si se adopta,
  se declara antes y se sigue en forward.

## C. Estrategias descartadas o en revisión que suman estabilidad
Criterio fijo: t propia ≥ 2, ≥ 70 % de años positivos, correlación ≤ 0,3 con la base y que no empeore la caída máxima de la base.

- **Sobre Intradía:**
  - **C2_VZ NQ** (t 2,67, correlación −0,09, Sharpe +0,23);
  - **C2_VZ ES** (t 2,10, correlación −0,18);
  - **N** de FundedSync (t 2,10, correlación 0,20, caída máx. +1.523).
- **Sobre Interdía:** T, R, Z, Franklin y N cumplen, y además **F** de FundedSync (t 2,60, correlación 0,05) y **C2_D7 en oro** (hasta
  2025-07).
- **Cerca, pero con datos sólo hasta 2025-07:** de Carril 2, C2_VBBN NQ (t 2,57, 100 % de años +), C2_TOMN NQ/ES (t 2,0–2,2) y C2_D7N ES
  (t 2,69, correlación 0,39). Necesitan re-medirse hasta 2026-09.
- **No suman:** S (correlación 0,51), A20 (50 % de años +), ES5N NQ (correlación 0,66), T ES (correlación 0,55) y C2_EVRP NQ en las corridas
  NT8 (t 0,6).

**Carteras armadas con lo que cumple (descriptivo, elegido sobre datos vistos):**

| Cartera | USD/mes | Sharpe | % meses + | Caída máx. | Tramo final |
|---|---|---|---|---|---|
| INTRADIA8 (actual) | +1.362 | 1,67 | 63 % | −13.964 | −4.806 |
| INTRADIA8 + C2_VZ NQ/ES + N | +1.751 | 1,99 | 68 % | −13.712 | +4.666 |
| INTERDIA3 (actual) | +574 | 1,23 | 70 % | −10.896 | +9.061 |
| **INTERDIA3 + T + R + Z + F + Franklin + N** | **+1.591** | **2,25** | **74 %** | **−9.101** | **+16.884** |

La última mezcla estrategias de noche (SOM y C2_VZ) con intradía de tendencia (T, R, Z, F, N, Franklin). Es la más estable medida, pero
necesita una cuenta que permita mantener de noche. Sus componentes se eligieron mirando estos datos: la confirmación es el forward.

## D. Corridas que vale la pena lanzar (propuestas, ninguna lanzada)
1. **Carril 2 hasta 2026-09** (C2_VBBN, C2_TOMN, C2_D7, C2_D7N, C2_P80N; ES, NQ y oro). Sus datos terminan en 2025-07. Son de las pocas
   que diversifican; hay que ver si siguen en los 14 meses que faltan.
2. **N y F de FundedSync con la cadena A5 completa** (DESC, REP y holdout A5), ahora con la traducción corregida. Hoy sólo hay lectura
   descriptiva.
3. **Vigilancia secuencial de las tres de la mañana** (RQ5, Franklin y ES5N) con un e-proceso y una regla de baja declarada antes, en vez de
   apagarlas a ojo. Están en el percentil 96–99 de sus caídas.
4. **Paridad de `EdgeLabCartera` en NT8** (Nico): Intradía con datos desde 2024, para confirmar la corrección del OCO.
5. **Forward de la cartera mixta** (INTERDIA3 + T + R + Z + F + Franklin + N) en una cuenta Sim que permita mantener de noche. Es la única
   confirmación limpia de lo elegido acá.
