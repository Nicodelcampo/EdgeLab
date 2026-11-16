# SQX lote 2 — pre-registro (2026-11-16): 8 horas, un proyecto por vez

Estado: VIGENTE, preparado y SIN LANZAR (no se lanza hasta que `StrategyQuantX.config` tenga `-Xmx`; lo controla `tools/sqx_cola.py`).
Etapa EF2. North Star sha256 16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345. Diseño, costos, cierre del viernes, gaps
realistas y evaluación: los del lote 1 (`docs/research/sqx_lote1_20261114/PREREGISTRO.md`, enmiendas 1–4), sin cambios.

## Qué aprendimos del lote 1 y por qué este orden
El Builder de SQX encuentra lo mismo sobre ruido que sobre el mercado (S&P D1 tendencia, S&P H4 reversión: el nulo supera al real); en oro D1
la mejor real apenas supera el máximo del nulo (t 4,28 contra 4,06) con +0,06 R. Por eso el lote 2 no repite activos muertos y prioriza
(1) lo único que asomó (oro, con más operaciones: H4), (2) la clase de activo con menos fricción por operación a largo plazo (FX D1),
(3) la reversión diaria de índices de la literatura (Connors) en el índice más volátil, y (4) el par del crudo que murió por memoria.

## Cola (cada proyecto 1 h; real y su nulo con el mismo presupuesto; orden fijo)
| # | Idea | Activo | TF | Plantilla | Nulo |
|---|---|---|---|---|---|
| 1–2 | LIT-TSMOM | Oro (XAUUSD) | H4 | TrendFollowing | NULO_XAUUSD_M1_dukas_H1_s1 |
| 3–4 | LIT-TSMOM | EURUSD | D1 | TrendFollowing | NULO_EURUSD_M1_dukas_H1_s1 |
| 5–6 | SQX-PLANTILLA-REVERSION | Nasdaq (USATECH) | D1 | Mean-Reversal | NULO_NQ_M1_dukas_H1_s1 |
| 7–8 | LIT-TSMOM | Crudo WTI | H4 | TrendFollowing | NULO_LIGHTCMDUSD_H1_s1 (par del lote 1, pasa de 2 h a 1 h) |

Ids y proyectos: `sqx/cola_lote2_20261116.json` y `sqx/corridas/<id>/manifest.json`. El K de cada proyecto va al contador al terminar.

## Evaluación (fijada antes; la del lote 1)
Umbral = máximo t del nulo (n ≥ 200, `edgelab/sqx_puente.py`). Candidata = real con t > umbral **y** R ≥ 0,10; sólo las candidatas se
exportan y pasan el contrato de calidad (`edgelab/research/sqx_calidad.py`). Sin candidatas: el par queda NO_REPETIR para esa plantilla,
activo y marco.

## Justificación económica y cómo podría refutarse
Fichas LIT-TSMOM y SQX-PLANTILLA-REVERSION (`docs/research/ideas/BANCO_IDEAS.md`). Refutación: ninguna real supera al máximo de su nulo.

## Enmienda 1 (2026-11-16, antes de lanzar nada; pregunta de Nico «¿conviene medir en temporalidades tan altas?»): el lote pasa a INTRADÍA
Para el referente (prop de futuros) H4/D1 rinde poco: (1) la mayoría de las prop de futuros exigen estar planos al cierre de la sesión, y una
regla de tendencia diaria vive de quedarse días; (2) son 2–8 operaciones por mes por activo: una evaluación de 30–60 días no llega al objetivo
y la evidencia tarda años. Los 8 proyectos H4/D1 quedan preparados y SIN LANZAR (sirven para una cuenta CFD swing si algún día hace falta).
Cola nueva (1 h cada proyecto; real y nulo igual; **cierre obligatorio 15:55 NY** con `--intradia`, además del cierre del viernes):
| # | Idea | Activo | TF | Plantilla | Nulo |
|---|---|---|---|---|---|
| 1–2 | SQX-PLANTILLA-TENDENCIA | Nasdaq (USATECH) | M30 | TrendFollowing | NULO_NQ_M1_dukas_M30_s1 |
| 3–4 | SQX-PLANTILLA-REVERSION | Nasdaq | M30 | Mean-Reversal | NULO_NQ_M1_dukas_M30_s1 |
| 5–6 | SQX-PLANTILLA-TENDENCIA | S&P (USA500) | M30 | TrendFollowing | NULO_SP_M1_dukas_M30_s1 |
| 7–8 | SQX-PLANTILLA-TENDENCIA | Oro | M30 | TrendFollowing | NULO_XAUUSD_M1_dukas_M30_s1 |
Nulos M30 por semanas re-encadenadas (conservan hora del día y día de la semana). Lección del intradía en EdgeLab: la fricción se come la
mayor parte de la ventaja bruta; por eso, además del umbral del nulo, una candidata necesita fricción ≤ 0,08 R por operación (contrato).
