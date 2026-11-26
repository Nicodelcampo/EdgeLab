# DIAG-CAIDA-2026: ¿la caída de 2026Q2–Q3 es del sizing o del movimiento del precio? (diagnóstico)

Estado: PRE-REGISTRO  
Fecha: 2026-11-25  
North Star sha256: `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`  
Etapa: EF2 (exploratorio, descriptivo; no promueve ni descarta estrategias; alimenta el pre-registro de EXP-7).  
Familia: `REGIMEN_APERTURA_DIAG` (10 pruebas registradas: 5 rasgos × NQ, ES).  
Antecedentes: «régimen de apertura ruptura continuación ORB eficiencia de tendencia reversión días laterales» — familias parecidas HFT_RUPTURA_OTROS, HFT_RUPTURA, REBOTE_NIVEL_SESION; NO_REPETIR F-GEX-DIA-TENDENCIA, F-SELECTIVIDAD-INVERSA, F-REELS-20261108, F-GAP-Y-RUPTURA-PREVIO-M1; código reutilizado: `edgelab/cartera/regimen.py` (rasgos diarios causales), `edgelab/cartera/afinidad.py`.  
Diferencia respecto a NO_REPETIR: no prueba ningún filtro ni regla de entrada (los descartes citados son filtros de régimen como señal); acá sólo se describe el mercado y se descompone el P&L ya medido.  
Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v4 — §0–§6 (K33 integridad, K40 holdout, K53 sin disparos, K55/K56 diagnóstico).  
Potencia previa: descriptivo; la ventana 2026-04 → 2026-09 tiene ≈ 125 sesiones; cada rasgo se ubica como percentil de su media de 6 meses contra las ventanas móviles de 6 meses de 2018-01 → 2025-12 (≈ 90 ventanas solapadas, ≈ 16 independientes): sólo se lee como «fuera de rango» un percentil < 5 o > 95, sin inferencia formal.  
Diagnóstico de mecanismo: no aplica grilla (no hay perillas); se publican los 10 percentiles, la serie mensual completa de cada rasgo y la descomposición por estrategia en las tres escalas.  
Datos: M1 de NT8 `edgelab-nt8-m1-futuros` (NQ, ES), 2018-01-02 → 2026-09-30 (nunca el holdout terminal); corridas NT8 de `docs/research/candidatas_nt8_20261125/` (1 contrato fijo).  
Pedido de Nico (2026-11-25): «ver si la forma de asignar el riesgo es un factor que influye en la curva por los cambios de precios del mercado y su volatilidad, o si es un factor puramente el movimiento del precio, con menos rupturas».

## Justificación económica
Las estrategias que más cayeron en 2026Q2–Q3 (T, RQ5, ES5N, Franklin) entran en la apertura de NY apostando a que el
movimiento inicial continúa. Si el flujo de la apertura cambió (más reversión después de romper el rango, más movimiento de
noche y menos en sesión, menos eficiencia de tendencia), todas pierden a la vez aunque su sizing sea correcto. Si en cambio la
caída aparece sólo en dólares y no en R por operación, el problema es cómo se asigna el riesgo frente a stops más grandes.

## Parte A — Descomposición sizing vs precio (por estrategia, sin pruebas)
Para cada corrida NT8 (1 contrato fijo): por trimestre 2020Q1 → 2026Q3,
- `R/op` = pnl_pts / riesgo_pts (no depende del sizing: mide el movimiento del precio relativo al stop);
- `USD/op` con 1 contrato fijo (depende de la volatilidad de la época);
- `USD/op` con riesgo constante (= R × 1R; el sizing ideal sin redondeo);
- stop mediano en puntos y en % del precio.
Lectura: si la caída aparece en `R/op`, es del precio; si sólo en `USD/op` con 1 contrato, es del sizing.

## Parte B — Rasgos de la apertura (las 10 pruebas)
Por sesión RTH (09:30–16:00 NY), NQ y ES:
1. `cont_orb`: rompe el rango 09:30–09:45 antes de 11:00 y el cierre de 16:00 queda del lado de la ruptura (1/0).
2. `ef_manana`: |c(11:30) − o(09:30)| / Σ|Δc| de 1 minuto entre 09:30 y 11:30.
3. `frac_noche`: |o(09:30) − c(16:00 previo)| / (|o(09:30) − c(16:00 previo)| + |c(16:00) − o(09:30)|).
4. `rv_rel`: rasgo de `edgelab/cartera/regimen.py` (rango 5 d / rango 60 d).
5. `ac5_manana`: autocorrelación de retornos de 5 minutos entre 09:30 y 11:30 (positiva = continuación).
Cada rasgo: media 2026-04 → 2026-09 como percentil de las medias de 6 meses de 2018–2025.

## Cómo podría refutarse
- La hipótesis «menos rupturas que continúan» queda refutada si `cont_orb` y `ac5_manana` de 2026Q2–Q3 están entre los
  percentiles 20 y 80 en NQ y en ES.
- La hipótesis «es el sizing» queda refutada si la caída de 2026Q2–Q3 se ve igual en `R/op` que en `USD/op` (riesgo constante).
