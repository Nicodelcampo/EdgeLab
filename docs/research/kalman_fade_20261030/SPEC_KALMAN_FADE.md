# KALMAN-FADE — pre-registro (2026-10-30)

Estado: PRE-REGISTRADO antes de cualquier corrida sobre datos reales. Módulo: `edgelab/research/kalman_fade.py`.
Origen: propuesta de Nico del 2026-10-30 (material de QuantFinanceToGo, «Observed = TRUE + noise»), evaluada en la sala ese día:
de esa lista sólo esta idea aplica a futuros direccionales; los filtros de griegas, delta hedging y paridad put-call se descartaron
porque EdgeLab no tiene libro de opciones.

## Hipótesis
El precio M1 es un nivel que se mueve despacio más ruido de microestructura. Una innovación extrema del filtro (|z| ≥ 2,5 en
unidades de su propio desvío) es en parte ruido transitorio y el precio vuelve hacia el nivel estimado. Si no vuelve, era
información y gana la continuación. El embudo decide entre los dos canales.

## Qué se mide
- Disparo en la vela k: |z_k| ≥ 2,5, con z_k = (c_k − x_{k|k−1}) / sqrt(P_{k|k−1} + R_{k−1}); como mucho uno cada 15 velas por suavidad
  y sesión; el estado se reinicia en cada sesión y espera 30 velas para estimar R. Todo se conoce al cierre de k.
- Perillas: `suavidad` (Q/R = 1e-3, 1e-2, 1e-1), `z_extremo` (≥ 2,5 / ≥ 3 / ≥ 4), `regimen_vol` (terciles causales de RV 30 / RV 390).
- Ejecuciones (8): FADE o CONTINUACION × objetivo NIVEL o MITAD × stop 1 o 2 desvíos de la innovación; entrada en el tick
  siguiente al cierre de k.
- **216 celdas por canal** (`grilla_generica.n_celdas`). Los umbrales son fijos y se eligieron antes de mirar datos reales.

## Períodos y reglas
DESC 2025-08-05..2026-03-31, OOS 2026-04-01..2026-09-30, holdout desde 2026-10-01 (una sola apertura, con acta). Tamiz FDR q ≤ 0,10
en DESC; el Deflated Sharpe ya lo calcula `funnel/escalera.dsr` con el N efectivo de la familia.

## Cómo se refuta
0 celdas nominadas por FDR q ≤ 0,10 en DESC, falla en INTEGRIDAD (placebo ≥ 25 % o latencia de 1 vela destructiva) o media ≤ 0 en OOS
u holdout. Si sólo sobrevive CONTINUACION, la hipótesis de reversión queda refutada aunque la familia siga viva.

## Controles
`tests/research/test_kalman_fade.py`: causalidad, paridad lote/escalar, `test_control_ruido` (sin efecto plantado el fade no gana) y
`test_control_plantado` (con saltos que revierten, `sintetico.bloques(planta=True)`, el fade gana más que sobre ruido).
