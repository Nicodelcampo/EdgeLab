# NETO-PISTAS: R (AtrPhase) y Z (ZetaTrend) llevados a R con los controles de T, y el neto de Franklin y SOM (pre-registro, 2026-11-19)

Estado: PRE-REGISTRO — se commitea antes de correr.
- **Pedido de Nico:** «¿Podés traducir a R las estrategias R AtrPhase y Z ZetaTrend? De la manera más rentable posible. Sin look ahead. Con
  los mismos controles que T. También mejorar el neto de Franklin NQ+ES y el de SOM … quizás se puede lograr una paralela de neto.»
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Etapa EF3** (desarrollo ya mirado; ni REP de A5 ni holdout). **Familias:** `FUNDEDSYNC` (parte A), `FRANKLIN` y `SOM` (parte B).
- **Herramienta:** `tools/neto_pistas.py` (reusa `fundedsyncstack.correr_modulo`, el kernel de `m1_largo` (`cargar`, `_kernel_fs`, `atr20`),
  la fricción canónica, `g2.pbo_cscv`, `g2.parameter_sensitivity`, el sup-F de T-REGIMEN y las operaciones versionadas de Franklin y SOM en
  `docs/research/m1_largo_20261117/`). `registro_global.exigir_contada` al inicio (K51).

Antecedentes: «FundedSync AtrPhase ZetaTrend stop catástrofe Franklin SOM neto tamaño» — F-T-REVISADO-EN-R, T-REGIMEN (REGIMEN_ROBUSTO),
F-FUNDEDSYNC-CAPA2-Y-VEREDICTO (stop de catástrofe 0,5 × ATR20 en R: peor −415 → −169 pts, neto casi igual), F-SENALES-ESTABLES-SOM-FRANKLIN,
F-VENTAJA-EN-PUNTOS-NO-ESCALA, F-STOP-CORTO-ES-FRICCION (contrato fijo y salteo de fricción > 0,08 R confirmados como palanca).

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v3 — §0–§6 (K36 unidad R, K38 ajuste del diseñador, K40 stop M1 en su nivel, K48 causalidad,
K49, K50, K51).

Potencia previa: R ≈ 2,8 y Z ≈ 1,9 operaciones por mes en NQ (≈ 670 y ≈ 450 en 20 años); con sd ≈ 1 R el error estándar del R medio es
≈ 0,04–0,05 por variante: alcanza para la forma de la grilla (meseta) pero no para afirmar efectos chicos; F-FRECUENCIA-MINIMA aplica (ambas
operan < 4 veces por mes: no se llevan solas a forward). Franklin NQ+ES ≈ 3.950 y SOM NQ+ES+YM ≈ 14.500 operaciones: potencia sobrada para
comparar esquemas.

## 0. Justificación económica
- R y Z son reglas de tendencia intradía de FundedSync (cruce de un oscilador ATR sobre su EMA en la primera hora y día de tendencia por
  eficiencia de buckets), con bruto positivo estable en NQ. Sin stop no tienen riesgo definido: un stop de catástrofe proporcional a la
  volatilidad previa (ATR20 diario, causal) les da unidad R sin tocar su lógica de entrada. Si su ventaja es un día de tendencia, un stop
  amplio casi no corta ganadoras y el R neto queda positivo.
- Franklin y SOM tienen bruto estable de 20 años y neto ≈ 0 porque la fricción se come las operaciones de stop chico (F-STOP-CORTO,
  FRICCION-RQ §3). Un esquema de tamaño que no sobrepondere esas operaciones (contrato fijo, ∝ 1/√riesgo) o saltearlas (fricción > 0,08 R,
  conocida al entrar) puede dejar un neto paralelo al bruto.

## A. R y Z en R (NQ decide; ES descriptivo)
- **Riesgo inicial:** stop de catástrofe a k × ATR20 diario de la sesión previa (`m1_largo.atr20`, `shift(1)`), k ∈ {0,25; 0,5; 0,75; 1,0}.
  Se aplica con el MAE de la operación (M1): si MAE ≥ k·ATR20 la operación sale en el stop (−k·ATR20, K40: en su nivel; R y Z entran y
  salen dentro de la sesión, sin hueco de apertura intermedio), si no, conserva su salida. R neto = (resultado − fricción) / (k·ATR20).
- **Grilla del motor (cerrada):**
  - R: `ema_period` {14, 21, 30} × `upper_threshold = −lower_threshold` {80, 100, 120} × `vwap_atr_mult` {2,0; 2,5; 3,0} ×
    `entry_end_min_et` {630, 660, 720} = 81 (fábrica 21 / 100 / 2,5 / 660).
  - Z: `bucket_minutes` {10, 15, 30} × `ema_period` {10, 20, 30} × `min_efficiency_pct` {35, 45, 55} = 27 (fábrica 15 / 20 / 45).
- **«La más rentable» sin elegir el pico:** se elige el k cuya MEDIANA de la grilla en NQ (2008–2026-09) es mayor; la fábrica del motor no se
  cambia. La elección de k es una selección entre 4 (se cuenta).
- **Controles de T, con el k elegido:** fracción de variantes con R neto > 0, mediana de la grilla ≥ 50 % de la fábrica, vecinos ±1 paso > 0
  (`parameter_sensitivity`), PBO (`g2.pbo_cscv`, S = 16, meses × variantes), quiebre propio de la fábrica (sup-F con recorte 15 % y
  permutación de meses, como en T) y años positivos antes y después. **Veredicto** como en T: `REGIMEN_ROBUSTO` (≥ 70 % positivas, mediana
  ≥ 50 % de fábrica, vecinos > 0 y PBO < 0,3), `SOBREAJUSTE_PROBABLE` (PBO > 0,5 o < 50 % positivas), `INTERMEDIO`.
- **Sin look-ahead:** prueba de causalidad por prefijo — las operaciones de la fábrica con datos cortados en 2015-06-30 coinciden con las de
  la corrida completa hasta esa fecha (entrada, lado y resultado), y el ATR20 usado es de la sesión anterior.

## A2. A20 (Absorb 20 min, sólo cortos) — enmienda de Nico del 2026-11-19, antes de correr A20
- «También A20 … son grandes ganadoras desde 2020». A20 tiene stop duro a `hard_stop_atr_mult` × ATR14 (velas de 20 min) fijado al entrar:
  R neto = (resultado − fricción) / |entrada − stop|; no necesita stop de catástrofe.
- **Grilla (cerrada):** `st_period` {5, 7, 10} × `st_mult` {1,5; 2,0; 2,5} × `absorb_vol_mult` {2,0; 2,5; 3,0} × `hard_stop_atr_mult`
  {1,0; 1,5; 2,0} = 81 (fábrica 7 / 2,0 / 2,5 / 1,5). NQ decide, ES descriptivo.
- **Controles y veredicto:** los mismos de A (meseta, vecinos, PBO, quiebre propio con sup-F, años positivos, prefijo). Se cuenta 1 prueba
  más en `FUNDEDSYNC`.

## B. Neto de Franklin (NQ + ES) y SOM (NQ + ES + YM, celda `sin_finde`)
- **Esquemas (cerrados), sobre las operaciones versionadas:** S0 riesgo constante (R medio, la medida actual); S1 contrato fijo (R como
  cociente de sumas Σ neto / Σ riesgo); S2 tamaño ∝ 1/√riesgo; S3 = S0 salteando fricción > 0,08 R (conocida al entrar); S4 = S2 salteando
  fricción > 0,08 R.
- **Elección en NQ + ES (+ YM para SOM), confirmación en EMD + RTY** (operaciones de esos índices ya existen; el esquema no se miró ahí):
  se elige el esquema de mayor neto en la elección; **mejora real** si en EMD + RTY también supera a S0 en neto (diferencia > 0 con su
  error estándar por sesión) y el neto 2006–2019 no es peor que con S0.
- **Curvas paralelas:** se publican bruto y neto acumulados por esquema (la «paralela de neto» que pide Nico).

## Cómo podría refutarse
- A: PBO > 0,5, < 50 % de variantes positivas o vecinos ≤ 0 → la traducción a R está sobreajustada; o ningún k da mediana > 0 → R y Z no
  pagan la fricción en R aunque su bruto en ATR sea positivo; o la prueba de prefijo encuentra diferencias → hay look-ahead en el motor.
- B: ningún esquema mejora a S0 en EMD + RTY → la mejora de NQ + ES es selección.
- **Contador:** A = 8 en FUNDEDSYNC (k entre 4 × 2 reglas); B = 5 en FRANKLIN y 5 en SOM.
