# CARRIL2-LOTE2: régimen de volatilidad (pico de VIX, P80, eVRP, z-score de compresión), Dynamic Breakout II y rotación ES/GC (pre-registro, 2026-11-19)

Estado: PRE-REGISTRO — se commitea antes de correr (los conteos de disparos de abajo se miraron sin retornos, chequeo K53).
- **Origen:** catálogo de Antigravity (`../flujos_macro_20261119/CATALOGO_14_ESTRATEGIAS_POST_FRICCION.md` §7, §8, §11, §12, §13) y `DISENO.md` §3
  (pasos 2 y 3). Pedido de Nico: «realizá todos … riguroso en los controles y que pasen por toda la cadena, sin falsos positivos»; objetivo
  nocturno del 19-nov («audita … probá variantes … sé cuidadoso al dar por muertas»).
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Etapas:** EF3 en DESC, EF4 en REP (A5); holdout A5 sellado. **Familia:** `CARRIL2_A5` (ya registrada en `LINAJES.jsonl`; este lote suma 12
  pruebas a las 8 del lote 1).
- **Herramienta:** `tools/carril2.py correr|desc|rep 2` (mismo motor que el lote 1: `sqx_catalogo.simular` con camino M1 —calibración K28—,
  barras D1 de sesión CME, VIX/VXN/VIX9D de `cboe_volatility_daily.parquet` con el último cierre conocido, `holdout.a5_bloque`, `a5.diferencia`,
  `a5.bh`, `a5.plan_lectura`, `libro_lord`, fricción canónica). `registro_global.exigir_contada` al inicio (K51). Corta con SystemExit si una
  definición no dispara (K53).

Antecedentes: CARRIL2-LOTE1 (0/8, SIN_EVIDENCIA, MDE 0,14–0,21 R), F-CONNORS-INDICES-SQX, TURTLES-ORO (canal 55/20 en GC, pista viva), FLUJOS-MACRO
FM1/FM7 (versiones intrasesión de VIX9D/VIX y P80), F-FRECUENCIA-MINIMA, K49.

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v3 — §0–§6 (K36 R con el stop, K40 stops en su nivel y hueco de apertura, K48, K49, K51, K52, K53).

Potencia previa: disparos (barras con señal, 2006–2026, sin retornos) por instrumento: pico de VIX ≈ 360, P80 ≈ 1.000–1.100, eVRP ≈ 2.400–2.700
barras (posiciones de varios días: muchas menos operaciones), z-score ≈ 860–900, DBO ≈ 430–470, rotación ≈ 100 por instrumento (12 por año en
total: la de menor potencia, se declara de antemano probablemente SIN_POTENCIA). En DESC (≈ 7/12 de los meses) quedan ≈ 150–1.500 operaciones por
regla agrupando instrumentos. REP se lee sólo con potencia en días ≥ 0,8 al nivel LORD++ (K49, `a5.plan_lectura`).

## 0. Justificación económica
- **Pico de VIX (BB 2σ):** los saltos de volatilidad implícita fuerzan desapalancamiento (vol-targeting, CTA, margen) que vende índice por debajo
  de su valor y revierte en días. **Control:** comprar con el VIX comprimido (< SMA20 − 1σ), mismo stop y salida.
- **VIX > P80 de 2 años (Bansal-Stivers):** la prima de riesgo esperada sube cuando la incertidumbre es alta. **Control:** VIX < P10.
- **eVRP > 0 con contango (Zarattini-Aziz-Mele 2025):** vender volatilidad implícita cara contra la realizada y estructura normal = régimen de
  compra de índice. **Control:** eVRP > 0 en backwardation (el estado que el paper deja en caja).
- **Z-score de compresión VIX+VIX9D < −1:** la caída rápida de la volatilidad implícita dispara compras de cobertura vanna/vol-control.
  **Control:** z-score > +1 (expansión).
- **Dynamic Breakout II (Pruitt):** ruptura con ventana que se alarga con la volatilidad (tendencia en oro e índices). **Control:** la misma
  regla con ventana fija de 20 (mide si la adaptación agrega).
- **Rotación ES/GC:** momentum relativo entre activos de riesgo y refugio a 20 meses. **Control:** la asignación opuesta.
- **Cómo podría refutarse:** ninguna pasa BH en DESC; o las nominadas no confirman en REP con potencia; o el contraste contra el control es ≤ 0
  (el efecto no es del mecanismo sino de estar comprado en índices que suben).

## 1. Reglas (fijas; barras D1 de sesión CME, señal al cierre de la barra con el cierre CBOE del día —16:15 NY, antes del cierre de la barra a
las 17:00—, entrada a mercado en la apertura siguiente; largos salvo DBO)
| Regla | Instrumentos | Entrada | Stop | Salida | Control |
|---|---|---|---|---|---|
| C2_VBB | ES, NQ, YM | IV > SMA20(IV) + 2 σ20 (IV = VIX; VXN en NQ) | 2,0 × ATR20 | dos cierres alcistas seguidos; tope 10 | C2_VBBN: IV < SMA20 − 1 σ20 |
| C2_P80 | ES, NQ, YM | IV > percentil 80 de 504 barras | 2,0 × ATR20 | IV ≤ P80; tope 10 | C2_P80N: IV < P10 (sale al dejar de serlo) |
| C2_EVRP | ES, NQ | IV − RV10 > 0 y VIX9D/VIX < 1 (RV10 = desvío de 10 retornos log del instrumento × √252 × 100) | 2,0 × ATR20 | sale del estado; tope 20 | C2_EVRPN: eVRP > 0 y VIX9D/VIX ≥ 1 |
| C2_VZ | ES, NQ | media de z-score de 6 barras de IV y VIX9D < −1 | 1,25 × ATR20 | z ≥ −1; tope 10 | C2_VZN: z > +1 |
| C2_DBO | GC, ES, NQ | largo: cierre > SMA(lb) + 2 σ(lb) y > máximo de las lb barras previas; corto simétrico; lb = clip(round(lb₋₁ × (1 + Δσ30/σ30)), 20, 60) | 1,5 × ATR20 | cruce de la SMA(lb) | C2_DBON: lb fijo 20 |
| C2_ROT | ES, GC | última barra del mes: razón ES/GC (cierres de fin de mes) > SMA de 20 meses → largo ES; si no → largo GC | 3,0 × ATR20 (catástrofe) | última barra del mes siguiente; tope 30 | C2_ROTN: la asignación opuesta |
- **Desvíos declarados:** entrada a la apertura de las 18:00 NY (no al cierre de las 15:55); eVRP en NQ usa VXN y su RV10; el paper de eVRP y la
  rotación son de cartera (sin stop): aquí llevan stop de catástrofe para medir en R.
- **No entran en este lote (con motivo):** overnight largo de Concretum (entrada 15:59 y salida 09:31: el motor de barras no la soporta sin una
  calibración nueva) y pre-FOMC (≈ 8 eventos por año, entrada 14:00: sin potencia sola; sólo como parte de una canasta de calendario).
- **R** = (salida − entrada)/(entrada − stop inicial) − fricción canónica/(entrada − stop inicial). Partición: bloque A5 de la entrada; se
  descarta la operación si su salida cae en HOLDOUT o EMBARGO (assert en la herramienta).

## 2. Decisión
- 12 pruebas en DESC (6 reglas en R neto > 0 y 6 contrastes regla − control), agrupando instrumentos, bootstrap por sesión, BH q 0,10 entre las
  12; nominación como en el lote 1 (contraste, o R neto > 0 con fricción mediana ≤ 0,08 R). REP una vez con LORD++ sólo con potencia en días
  ≥ 0,8 (K49). Todo nulo publica su MDE: SIN_EVIDENCIA no es REFUTADA.
- **Contador:** 12 pruebas en `CARRIL2_A5`.
