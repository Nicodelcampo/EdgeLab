# Manifiesto: IVC de horizonte largo con historia de años (IVC-L), proxies ETF, 2026-09-26

**North Star:** `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`
**Estado:** escrito antes de medir. Autorización: Nico, chat 26/09 («Hacé lo necesario ahora», después de aprobar
la línea de horizonte largo propuesta en `docs/research/IVC_RESULTADOS_20260926.md`).
**Herramienta:** `tools/ivc_largo.py`. **Cerebro:** ledger `artifacts/hippocampus/ivc_20260926.jsonl`, partición nueva
`P-IVCL-EXP`.

## 1. Por qué

El mapa IVC (ES/NQ/YM, 9 meses) mostró que en horizonte corto la información no paga el costo y que en horizonte largo
(cierre, última media hora, gap) el borde bruto se acerca al costo pero **sin potencia** (MDE del IC 0,04–0,24 con
~80 sesiones). Lo que falta es historia. Los futuros de años no están en el proyecto; los ETF de los mismos índices sí
se consiguen con décadas de datos. El ETF cotiza la misma exposición en la sesión regular, así que sirve para medir
**si hay información** en esos horizontes. El costo operable se mide después, en el futuro, con datos de NT8.

**Justificación económica:** el gap nocturno y el primer tramo del día concentran la reacción a información
overnight y al flujo de apertura; el cierre concentra rebalanceo y cobertura. Son mecanismos con literatura (cierre
del gap; momentum intradía de la última media hora) y de horizonte suficiente para que ~1–1,5 pb de costo pesen poco.
**Cómo podría refutarse:** que con miles de días ninguna de las celdas tenga IC significativo contra el nulo, o que el
borde no supere el costo en descubrimiento y validación.

## 2. Datos (procedencia)

| Fuente | Contenido | Período usado | Custodia |
|---|---|---|---|
| Yahoo Finance chart API, diario | SPY, QQQ, DIA: apertura y cierre de sesión regular | desde el inicio de cada ETF hasta 2026-03-31 | JSON crudo con sha256 en el reporte |
| Kaggle `rockinbrock/spy-1-minute-data` (público, tercero, licencia no declarada) | SPY 1 min, sesión regular, reloj de montaña (7:30 = 9:30 ET) | 2008-01-22 a 2021-05-06 | sha256 `81d936c7…c49b`; sólo exploración, no se republica |

Abr–jun 2026 y el holdout (>= 2026-07-01) no están en los datos. Los días ex-dividendo se excluyen del gap (el
precio cae por el dividendo, no por información).

## 3. Celdas (fijas ahora, 8)

| # | Fuente | Estado (predictor) | Objetivo |
|---|---|---|---|
| 1–3 | diario SPY / QQQ / DIA | gap = apertura / cierre previo − 1 | apertura → cierre del mismo día |
| 4 | SPY 1 min | primera media hora (9:30 → 10:00) | última media hora (15:30 → 16:00) |
| 5 | SPY 1 min | gap | última media hora |
| 6 | SPY 1 min | primera media hora | 10:00 → 15:30 |
| 7 | SPY 1 min | gap | primera media hora |
| 8 | SPY 1 min | gap | 10:00 → cierre |

## 4. Medida

- IC de Spearman; borde por apuesta = media de sign(IC)·sign(predictor)·retorno, en puntos básicos (operar todos los
  días en la dirección que indica el predictor), y también en los quintiles extremos.
- **Costo:** 1,5 pb por ida y vuelta (conservador frente a ES ≈ 1,0, NQ ≈ 0,8, YM ≈ 1,1 pb con el costo agresivo
  medido en IVC); sensibilidad a 3 pb.
- **Nulo:** el predictor desplazado circularmente ≥ 20 días (2.000 réplicas). **IC por bootstrap por bloques de un mes.**
- **Partición:** diario, descubrimiento hasta 2012-12-31 y validación 2013–2026-03; 1 min, descubrimiento 2008–2014 y
  validación 2015–2021. El signo de validación se fija en descubrimiento.
- BH-FDR q = 0,10 sobre las 8 celdas. **Prometedora** = FDR + margen con IC inferior > 0 en descubrimiento + margen > 0
  con IC inferior > 0 y mismo signo en validación. Canal no direccional: |retorno| contra |gap|, como descriptivo.

## 5. Riesgos

- Proxy ETF ≠ futuro: el gap del ETF equivale al movimiento 16:00→9:30 del futuro, que el futuro opera de noche. Una
  celda prometedora exige re-medirse en ES/NQ/YM con datos de NT8 antes de cualquier regla.
- Datos de tercero sin licencia declarada (1 min): exploración interna, no se publica ni se sube.
- Cambios de régimen en 30 años: se reporta también por década.
