# CARRIL2-LOTE1: IBS + VIX, Double Seven, Turnaround Tuesday y cambio de mes sobre el motor de barras calibrado (pre-registro, 2026-11-19)

Estado: PRE-REGISTRO — se commitea antes de correr.
- **Origen:** catálogo de Antigravity (`../flujos_macro_20261119/CATALOGO_14_ESTRATEGIAS_POST_FRICCION.md` §1, §2, §5, §6) y diseño
  `DISENO.md`. Pedido de Nico: «realizá todos … riguroso en los controles y que pasen por toda la cadena, sin falsos positivos».
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Etapas:** EF3 en DESC, EF4 en REP (A5); holdout A5 sellado. **Familia:** `CARRIL2_A5` (nueva; padres `SQX_CATALOGO`, porque Double 7 ya se
  midió ahí con stop 3 × ATR14, y `FLUJOS_MACRO_A5`, porque FM3/FM4 son las versiones intrasesión de IBS y Turnaround Tuesday).
- **Herramienta:** `tools/carril2.py` (motor `sqx_catalogo.simular` con camino M1 `indices_m1` — calibración registrada K28 —, barras
  `barras_desde_m1(D, "D1")` de sesión CME, `m1_largo.cargar`, VIX de `cboe_volatility_daily.parquet`, `holdout.a5_bloque`, `a5.diferencia`,
  `a5.bh`, `a5.plan_lectura`, `libro_lord`, fricción canónica). `registro_global.exigir_contada` al inicio (K51).

Antecedentes: F-CONNORS-INDICES-SQX (Double 7 y buy-dips RSI5 en índices D1: pista viva), FLUJOS-MACRO FM3/FM4 (versiones intrasesión, en curso),
F-FRECUENCIA-MINIMA (≥ 4 por mes o canasta), K49.

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v3 — §0–§6 (K36 R con el stop, K40 stops en su nivel y hueco de apertura, K48, K49, K51, K52, K53).

Potencia previa: frecuencias esperadas por instrumento: IBS+VIX ≈ 2–4 por mes, Double Seven ≈ 0,5–0,7, Turnaround Tuesday ≈ 1–2, cambio de mes
= 1. Agrupando ES+NQ+YM+RTY (+GC en Double Seven) cada regla tiene ≈ 400–2.500 operaciones en DESC. La lectura de REP se decide con
`a5.plan_lectura` en días al nivel LORD++ (K49); es probable que varias queden `SIN_POTENCIA_PREVIA`: no se fuerzan.

## 0. Justificación económica
- **IBS + VIX:** un cierre en el 20 % inferior del rango del día refleja ventas forzadas al cierre (rebalanceo, coberturas); con VIX sobre su
  media de 100 días esas ventas son más grandes y revierten más. **Control:** comprar cierres fuertes (IBS > 0,8).
- **Double Seven:** retroceso de 7 días dentro de una tendencia de 200 días (compra de debilidad en tendencia). **Control:** el mismo mínimo de
  7 días debajo de la SMA200.
- **Turnaround Tuesday:** sobre-reacción del lunes (cierre bajo el viernes con IBS < 0,5) que revierte en la semana. **Control:** lunes alcista
  (IBS > 0,8).
- **Cambio de mes:** flujos de nómina, 401(k) y rebalanceo entre T−5 y T+3. **Control:** el tramo del medio del mes (T+4 → T−6).

## 1. Reglas (fijas; barras D1 de sesión CME, señal al cierre de la barra, entrada a mercado en la apertura de la siguiente)
| Regla | Instrumentos | Entrada (largos) | Stop | Salida | Control |
|---|---|---|---|---|---|
| C2_IBS | ES, NQ, YM, RTY | IBS < 0,20 y VIX(t−1) > SMA100 del VIX (t−1) | 1,50 × ATR20 | IBS > 0,80 o cierre > máximo previo; tope 10 barras | C2_IBSN: IBS > 0,80 (mismo filtro de VIX) |
| C2_D7 | ES, NQ, YM, RTY, GC | cierre > SMA200 y cierre = mínimo de 7 | 1,75 × ATR20 | cierre = máximo de 7 | C2_D7N: mínimo de 7 bajo la SMA200 |
| C2_TT | ES, NQ, YM, RTY | lunes, cierre < cierre del viernes e IBS < 0,50 | 1,50 × ATR20 | cierre > máximo previo; tope 4 barras | C2_TTN: lunes con IBS > 0,80 |
| C2_TOM | ES, NQ, YM, RTY | cierre del 5.º día hábil antes de fin de mes | 2,00 × ATR20 | tope 8 barras (≈ T+3) | C2_TOMN: entrada el 4.º día hábil del mes, tope 8 |
- **Desvío declarado de las reglas publicadas:** entran a la apertura de las 18:00 tras el cierre de sesión (no a las 15:55): QS documenta que
  entrar más tarde reduce el retorno de IBS (0,41 → 0,31 %); el sesgo es en contra de las reglas, no a favor.
- **R** = (salida − entrada) / (entrada − stop inicial) − fricción canónica / (entrada − stop inicial). Una fricción por operación.
- **Partición:** cada operación va al bloque A5 de su entrada y **se descarta si su salida cae en un mes HOLDOUT o EMBARGO** (test en la
  herramienta: ninguna operación evaluada tiene salida ahí).

## 2. Decisión
- 8 pruebas en DESC (4 reglas en R neto > 0 y 4 contrastes regla − control), agrupando instrumentos, bootstrap por sesión, BH q 0,10;
  nominación sólo si además el R neto es > 0 y la fricción mediana ≤ 0,08 R. REP una vez con LORD++ sólo con potencia en días ≥ 0,8 (K49).
- **Cómo podría refutarse:** ninguna pasa BH en DESC; o las nominadas no confirman en REP con potencia.
- **Contador:** 8 pruebas en `CARRIL2_A5`.
