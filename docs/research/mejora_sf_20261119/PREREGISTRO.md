# MEJORA-SF: mejorar la curva de SOM y Franklin con filtros causales con mecanismo, elegidos en DESC y confirmados en REP (pre-registro, 2026-11-19)

Estado: PRE-REGISTRO — se commitea antes de correr.
- **Pedido de Nico:** «Me refiero a mejorar la curva siendo el edge real y válido» (SOM y Franklin: señal bruta robusta confirmada en
  `regimen_som_franklin_20261119/RESULTADO.md`).
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Etapas:** EF3 en DESC (meses DESC de A5), EF4 en REP (meses REP de A5; estos contrastes nunca se miraron en REP), holdout A5 sellado.
  **Familias:** `SOM` y `FRANKLIN`. Reglas fijas: SOM de fábrica (`sin_finde`, NQ + ES + YM) y Franklin `1000|rango|ninguno` (NQ + ES).
- **Herramienta:** `tools/mejora_sf.py` (reusa `quantlab_mt5_medir.ops_som` — ahora con la columna `lado`, sin cambio de cálculo —, las
  operaciones versionadas de Franklin, `m1_largo.cargar`, `holdout.a5_bloque`, `a5.diferencia`, `a5.bh`, `a5.plan_lectura`, `libro_lord`
  y el VIX de `cboe_volatility_daily.parquet`). `registro_global.exigir_contada` al inicio (K51).

Antecedentes: «SOM Franklin filtro volatilidad VIX tendencia fricción concordancia» — F-SENALES-ESTABLES-SOM-FRANKLIN, NETO-PISTAS B (S3 no
confirmó en EMD+RTY), F-GEX-DIA-TENDENCIA y ANCLAJE-PROXY (filtro de gamma: NO_REPETIR; acá el VIX entra como estado de volatilidad, una sola
prueba direccional), F-STOP-CORTO-ES-FRICCION, papel_regimen (vol20, tend60), K48 (variables conocidas antes de entrar).

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v3 — §0–§6 (K48 causalidad, K49 potencia en días, K51, K52).

Potencia previa: DESC ≈ 7/12 de 2006–2025: SOM ≈ 8.400 operaciones, Franklin ≈ 2.300; REP ≈ 2/12: SOM ≈ 2.400, Franklin ≈ 650. Con
sd ≈ 1,1 R, un contraste de +0,05 R entre mitades tiene error estándar ≈ 0,025 (SOM) y ≈ 0,045 (Franklin) en DESC. La lectura de REP se
decide con `a5.plan_lectura` en DÍAS al nivel LORD++ (K49): sólo se lee lo que llegue a potencia ≥ 0,8; el resto queda `SIN_POTENCIA_PREVIA`.

## 0. Justificación económica (un mecanismo por filtro, dirección fijada antes)
- **M2 fricción** (SOM, Franklin): saltear operaciones con fricción > 0,08 R (fricción / riesgo, conocida al entrar). Mecanismo: la fricción
  fija pesa más en stops chicos; el bruto no depende del tamaño del stop (F-STOP-CORTO). Dirección: sin ellas, mejor.
- **M3 volatilidad** (SOM, Franklin): ATR20 diario del instrumento en el tercio superior de sus 250 sesiones previas. Mecanismo: el impulso de
  apertura recorre más en días volátiles y la fricción fija pesa menos. Dirección: tercio alto, mejor.
- **M6 VIX** (SOM, Franklin): percentil 252 del VIX al cierre previo (`vix_ivp_252_prev_close`) en el tercio superior. Mecanismo: más
  volatilidad implícita → más cobertura de gamma corta y más momentum intradía (Baltussen et al. 2021). Dirección: tercio alto, mejor.
- **M8 tendencia** (SOM, Franklin): operar a favor del signo del cierre previo contra el de 60 sesiones antes. Mecanismo: el impulso de
  apertura alineado con la tendencia de mediano plazo continúa más. Dirección: alineadas, mejor.
- **M1 concordancia** (sólo Franklin): ese día SOM ya entró del mismo lado en ese instrumento (SOM entra a las 09:30, Franklin a las 10:00:
  causal). Mecanismo: dos lecturas del sesgo del día que coinciden. Dirección: concordantes, mejor. (SOM condicionado a Franklin no es causal.)

## 1. Prueba y decisión
- Para cada filtro y estrategia, el contraste es R neto(dentro) − R neto(fuera), unilateral en la dirección declarada, bootstrap por sesión
  (`a5.diferencia`), sólo meses DESC. 9 pruebas: SOM {M2, M3, M6, M8}, Franklin {M1, M2, M3, M6, M8}. **Nominación:** BH q 0,10 sobre las 9.
- **REP:** las nominadas con potencia ≥ 0,8 en días (K49) se prueban una vez con LORD++ de su familia. **Mejora confirmada** si REP rechaza y
  el R neto de la regla filtrada en REP es > 0.
- **Descriptivo:** R neto de la regla filtrada por bloque y desde 2020; curvas de la regla con y sin las mejoras confirmadas.
- **Cómo podría refutarse:** ningún contraste pasa BH en DESC, o los nominados no se confirman en REP → las curvas no se mejoran con estos
  estados; un filtro que en REP da contraste ≤ 0 se descarta.
- **Contador:** 4 pruebas en `SOM` y 5 en `FRANKLIN`.
