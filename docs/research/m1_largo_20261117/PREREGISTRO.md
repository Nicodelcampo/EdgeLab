# M1 real de futuros sobre FundedSync (15 módulos) y SOM, y prueba de régimen análogo (pre-registro, 2026-11-17)

Estado: PRE-REGISTRO — commiteado antes de correr FundedSync y SOM sobre M1 de futuros. Pedido de Nico: «usá esos datos nuevos para
indagar en las que no han sido descartadas, en la cartera entera de donde salieron T, Z y R, y en los dos EA de MT5»; y la prueba de
régimen («pueden ser régimen», «dale»). North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Etapa EF4.
Herramienta: `tools/m1_largo.py`. Datos: `edgelab-nt8-m1-futuros` (NQ, ES, YM desde 2006; GC desde 2008), `m1_intradia.leer_m1nt8`
(corta en la frontera).

Antecedentes: `python tools/antecedentes.py "FundedSync SOM sobre M1 de futuros años viejos y régimen análogo"` → FUNDEDSYNC (408 pruebas;
F-FUNDEDSYNC-T-KNN pista viva, F-FUNDEDSYNC-SIN-VENTAJA no repetir), EL_DIA_TENDENCIA, SOM / SOM_TRANSFER, ATRAS_M1_V2V4 (refutada).

Potencia previa:
- m1l_T.csv (T sobre el CFD 2020+, riesgo ≥ 2): 16.9 ops/mes, R/op +1.864, sd 6.32, n para decidir 72, 4.3 meses → OK | lectura de N 800 con
  la mitad del efecto: potencia 0.994.
- m1l_SOM.csv (SOM sin_finde NQ 2020+): 19.7 ops/mes, R/op +0.079, sd 0.98, n para decidir 957, 48.6 meses → OK | lectura de N 800 con la
  mitad del efecto: potencia 0.306.

En 2006–2011 se esperan ≈ 4.000 operaciones de SOM y de T entre los 3 índices (potencia ≈ 0,8 para SOM a la mitad del efecto) y ≈ 500 de
Z y de R.

## 1. Qué no entra y por qué
- **QLB (EA de oro):** sus gatillos de los slots 0 y 1 están compilados y la traducción los infiere (`PREREGISTRO_MEDICION.md`, revisión
  de Antigravity): medirlos sería medir una suposición.
- **DRC-NQ-R:** velas de 50/100/250 ticks.
- **Las reglas del embudo con footprint, señal en CFD o velas de ticks.**
- Las 5 ya medidas en M1 entran sólo a la prueba de régimen (§4).

## 2. Variables de estado (sin resultados, ya calculadas: `ESTADO_<INST>.csv`)
- **Volatilidad:** por mes, la mediana del rango de la sesión CME / cierre; terciles sobre 2006-01 → 2025-07.
- **Tendencia:** el signo del retorno de 126 sesiones al empezar el mes.
- **Estado de referencia:** el par (tercil, signo) más frecuente en la ventana donde la estrategia se vio bien:
  - ago-25 → sep-26 para las 5 reglas del embudo;
  - 2020-01 → 2025-07 para T, Z, R y SOM.

## 3. FundedSync (15 módulos, fábrica, 1 contrato) y SOM (3 celdas) sobre futuros NQ, ES y YM, 2006 → jul-2025
- **Unidad:** FundedSync en neto / ATR20 diario (comparable entre épocas y entre módulos con y sin stop); SOM en R. Costos canónicos de
  cada futuro.
- **Calibración (diagnóstico, no compuerta):** NQ futuros contra la medición sobre el CFD en 2012-01 → 2025-07, por sesión.
  - Si un módulo no calibra, su medición sobre el CFD no representaba al futuro: lo que se opera es el futuro.
- **Confirmatorio, años limpios 2006-01-06 → 2011-12-30:** ninguna medición de FundedSync ni de SOM los tocó. T, Z, R y SOM (sin_finde),
  cada uno con los 3 índices juntos. Veredictos:
  - **A_FAVOR:** IC90 inferior > 0 y ≥ 60 % de años positivos;
  - **EN_CONTRA:** media ≤ 0 con potencia ≥ 0,8 para la mitad de su efecto de 2020–2025 en futuros;
  - si no, NO_CONCLUYENTE.
- **Descriptivo:** los 15 módulos por índice en 2006–2011, 2012–2019 y 2020–2025.

## 4. Régimen análogo (la hipótesis de Nico)
- **Estrategias:** las 5 reglas del embudo refutadas atrás y T, Z, R y SOM.
- **Ventana de prueba:** la primaria del «atrás» para las del embudo; 2006–2019 para T, Z, R y SOM.
- **Meses análogos:** los meses de la ventana de prueba en el estado de referencia.
- **Veredictos:**
  - **REGIMEN_APOYADO:** IC90 inferior > 0 en los análogos y ≥ 60 % de años positivos;
  - **REGIMEN_RECHAZADO:** media ≤ 0 en los análogos con potencia ≥ 0,8 para la mitad del efecto de referencia;
  - si no, NO_CONCLUYENTE.
- Se reportan también los meses no análogos.
- **Riesgo declarado:** los resultados por año de las 5 del embudo ya se vieron. Por eso el estado se fijó con variables genéricas (las dos
  más comunes en la literatura de regímenes) antes de cruzarlo con resultados, y no se prueba ninguna otra variable.

## 5. Contador, justificación y refutación
- **Contador:** 9 pruebas de régimen + 4 de años limpios = **13**, familia `M1LARGO_EXTERNAS_20261117` (linaje: FUNDEDSYNC, SOM,
  ATRAS_M1_V2V4_20261117).
- **Justificación económica:** la de cada estrategia (T: ruptura del rango de apertura con filtro KNN; Z: día de tendencia; R: fase de ATR;
  SOM: impulso de la apertura de NY). Si son ventajas estables deben aparecer en años no usados; si son de régimen, deben aparecer en los
  meses de estado análogo.
- **Cómo podría refutarse:** EN_CONTRA en años limpios y REGIMEN_RECHAZADO en los análogos.

## Enmienda 1 (2026-11-17, antes de ver ningún resultado de T en 2006–2011: con los valores de fábrica T no opera antes de 2012)
T trae fechas de arranque fijas del backtest del vendedor: acumula etiquetas «sombra» desde 2010 y entrena el KNN y opera desde 2012
(2 años de calentamiento). Para medirlo en años limpios se corren las tres fechas 6 años: sombra desde 2006, KNN y operación desde 2008.
La ventana limpia de T es **2008-01-02 → 2011-12-30**, con el mismo calentamiento que el diseño. El literal 2010 del entrenamiento del KNN
pasa a ser el parámetro `shadow_min_session_date`, que de fábrica vale lo mismo, así que el comportamiento por defecto no cambia
(`tools/m1_largo.py correr … t2008`). El resto del pre-registro no cambia.
